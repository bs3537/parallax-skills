import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_parallax_lite.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_parallax_lite", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class UnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_complexity_profiles(self):
        self.assertEqual(self.mod.classify_complexity("What changed in Q2 revenue?")[0], "quick")
        standard = "Compare the product, competitors, recent earnings, valuation, and key risks."
        self.assertEqual(self.mod.classify_complexity(standard)[0], "standard")
        complex_prompt = " ".join(
            [
                "Build a multi-year chronology across filings, clinical trials, competitors,",
                "institutional ownership, insider transactions, capital raises, valuation,",
                "regulatory events, and scenario analysis with primary-source verification.",
            ]
            * 8
        )
        self.assertEqual(self.mod.classify_complexity(complex_prompt)[0], "complex")

    def test_codex_parser_extracts_session_checkpoint_and_searches(self):
        parser = self.mod.CodexEventParser()
        events = [
            {"type": "thread.started", "thread_id": "019f-test-thread"},
            {
                "type": "item.completed",
                "item": {"id": "m1", "type": "agent_message", "text": "Provisional answer with evidence."},
            },
            {"type": "item.completed", "item": {"id": "s1", "type": "web_search"}},
            {"type": "turn.completed"},
        ]
        for event in events:
            parser.feed(json.dumps(event))
        self.assertEqual(parser.session_id, "019f-test-thread")
        self.assertEqual(parser.checkpoint, "Provisional answer with evidence.")
        self.assertEqual(parser.final_text, "Provisional answer with evidence.")
        self.assertEqual(parser.searches, 1)

    def test_claude_parser_extracts_session_and_result(self):
        parser = self.mod.ClaudeEventParser()
        parser.feed(json.dumps({"type": "system", "subtype": "init", "session_id": "claude-session"}))
        parser.feed(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": "Checkpoint answer."}]},
                }
            )
        )
        parser.feed(json.dumps({"type": "result", "session_id": "claude-session", "result": "Final answer."}))
        self.assertEqual(parser.session_id, "claude-session")
        self.assertEqual(parser.checkpoint, "Final answer.")
        self.assertEqual(parser.final_text, "Final answer.")

    def test_word_cap_is_enforced_and_disclosed(self):
        text = " ".join(f"word{i}" for i in range(40))
        capped, was_capped = self.mod.cap_words(text, 12)
        self.assertTrue(was_capped)
        self.assertLessEqual(len(capped.split()), 20)
        self.assertIn("TRUNCATED", capped)

    def test_persistent_argv_omits_ephemeral_flags(self):
        codex = self.mod.build_codex_argv("model", "high", Path("/tmp"))
        claude = self.mod.build_claude_argv("model", "high", Path("/tmp"), "session-id")
        self.assertNotIn("--ephemeral", codex)
        self.assertNotIn("--no-session-persistence", claude)
        self.assertIn("--session-id", claude)

    def test_streaming_timeout_salvages_checkpoint_and_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            emitter = textwrap.dedent(
                """
                import json, time
                print(json.dumps({"type":"thread.started","thread_id":"resume-me"}), flush=True)
                print(json.dumps({"type":"item.completed","item":{"id":"m1","type":"agent_message","text":"A usable provisional answer with a cited decisive fact and explicit uncertainty."}}), flush=True)
                time.sleep(5)
                """
            )
            result = self.mod.run_streaming_component(
                argv=[sys.executable, "-c", emitter],
                prompt="test",
                parser=self.mod.CodexEventParser(),
                timeout=1,
                max_searches=3,
                raw_path=tmp_path / "raw.jsonl",
                stderr_path=tmp_path / "stderr.log",
                checkpoint_path=tmp_path / "checkpoint.md",
                env=dict(**__import__("os").environ),
            )
            self.assertEqual(result["status"], "timeout")
            self.assertEqual(result["text_kind"], "checkpoint")
            self.assertEqual(result["session_id"], "resume-me")
            self.assertIn("usable provisional answer", result["text"])
            self.assertTrue((tmp_path / "checkpoint.md").exists())

    def test_search_budget_stops_component_and_preserves_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            emitter = textwrap.dedent(
                """
                import json, time
                events = [
                    {"type":"thread.started","thread_id":"budget-session"},
                    {"type":"item.completed","item":{"id":"m1","type":"agent_message","text":"Checkpoint before excess research with enough content to remain useful."}},
                    {"type":"item.completed","item":{"id":"s1","type":"web_search"}},
                    {"type":"item.completed","item":{"id":"s2","type":"web_search"}},
                ]
                for event in events:
                    print(json.dumps(event), flush=True)
                time.sleep(5)
                """
            )
            result = self.mod.run_streaming_component(
                argv=[sys.executable, "-c", emitter],
                prompt="test",
                parser=self.mod.CodexEventParser(),
                timeout=10,
                max_searches=1,
                raw_path=tmp_path / "raw.jsonl",
                stderr_path=tmp_path / "stderr.log",
                checkpoint_path=tmp_path / "checkpoint.md",
                env=dict(**__import__("os").environ),
            )
            self.assertEqual(result["status"], "search-budget")
            self.assertTrue(result["budget_exceeded"])
            self.assertEqual(result["searches"], 2)
            self.assertIn("Checkpoint before excess research", result["text"])


class DryRunTests(unittest.TestCase):
    def run_cli(self, *extra):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        cmd = [
            sys.executable,
            str(SCRIPT),
            "TEST",
            "--dry-run",
            "--run-base",
            tmpdir.name,
            *extra,
        ]
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
        runs = sorted((Path(tmpdir.name) / "TEST" / "runs").glob("*"))
        self.assertEqual(len(runs), 1, completed.stderr)
        manifest = json.loads((runs[0] / "manifest.json").read_text())
        return completed, manifest, runs[0]

    def test_dual_lane_dry_run_publishes_complete_answer_without_retries(self):
        completed, manifest, run_dir = self.run_cli("--profile", "quick")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["retry_policy"], "none")
        self.assertEqual(manifest["stages"]["lanes"]["claude"]["attempts"], 1)
        self.assertEqual(manifest["stages"]["lanes"]["codex"]["attempts"], 1)
        self.assertTrue((run_dir / "merged_answer.md").exists())
        self.assertIn("ANSWER LINKS", completed.stdout)

    def test_one_failed_lane_still_gets_disclosed_partial_merge(self):
        completed, manifest, run_dir = self.run_cli(
            "--profile",
            "quick",
            "--dry-run-fail",
            "codex",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(manifest["status"], "complete_partial_single_lane")
        self.assertEqual(manifest["stages"]["merge"]["mode"], "single_lane")
        merged = (run_dir / "merged_answer.md").read_text()
        self.assertTrue(merged.startswith("> **PARTIAL SINGLE-LANE RESULT:**"))
        self.assertIn("Codex lane failed", merged)

    def test_both_failed_lanes_do_not_fabricate_a_merge(self):
        completed, manifest, run_dir = self.run_cli(
            "--dry-run-fail",
            "both",
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(manifest["status"], "failed_no_usable_lanes")
        self.assertFalse((run_dir / "merged_answer.md").exists())


if __name__ == "__main__":
    unittest.main()
