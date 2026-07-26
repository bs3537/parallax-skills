from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "run_parallax.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_parallax", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ParallelGauntletFastContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def test_model_and_effort_contract(self):
        self.assertEqual(self.runner.CLAUDE_LEAD_MODEL, "claude-opus-5")
        self.assertEqual(self.runner.CLAUDE_LEAD_EFFORT, "high")
        self.assertEqual(self.runner.CLAUDE_WORKER_MODEL, "claude-sonnet-5")
        self.assertEqual(self.runner.CLAUDE_WORKER_EFFORT, "xhigh")
        self.assertEqual(self.runner.CODEX_LEAD_MODEL, "gpt-5.6-sol")
        self.assertEqual(self.runner.CODEX_LEAD_EFFORT, "high")
        self.assertEqual(self.runner.CODEX_WORKER_MODEL, "gpt-5.6-sol")
        self.assertEqual(self.runner.CODEX_WORKER_EFFORT, "high")
        self.assertEqual(len(self.runner.WORKER_LANES), 4)

    def test_model_contract_cannot_be_overridden_by_environment(self):
        env = os.environ.copy()
        env.update(
            {
                "PARALLAX_CLAUDE_LEAD_MODEL": "wrong-lead",
                "PARALLAX_CLAUDE_WORKER_EFFORT": "low",
                "PARALLAX_CODEX_LEAD_MODEL": "wrong-codex",
                "PARALLAX_CODEX_WORKER_EFFORT": "low",
            }
        )
        code = (
            "import json, runpy; "
            f"m=runpy.run_path({str(SCRIPT)!r}); "
            "print(json.dumps([m['CLAUDE_LEAD_MODEL'], m['CLAUDE_WORKER_EFFORT'], "
            "m['CODEX_LEAD_MODEL'], m['CODEX_WORKER_EFFORT']]))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout),
            ["claude-opus-5", "xhigh", "gpt-5.6-sol", "high"],
        )

    def test_cli_argv_preserves_each_runtime_tool_configuration(self):
        cwd = Path("/tmp/parallax-contract-test")
        claude = self.runner.build_claude_argv(
            self.runner.CLAUDE_WORKER_MODEL,
            self.runner.CLAUDE_WORKER_EFFORT,
            cwd,
        )
        self.assertEqual(claude[:2], ["claude", "-p"])
        self.assertIn("claude-sonnet-5", claude)
        self.assertIn("xhigh", claude)
        self.assertNotIn("--strict-mcp-config", claude)

        codex = self.runner.build_codex_argv(
            self.runner.CODEX_WORKER_MODEL,
            self.runner.CODEX_WORKER_EFFORT,
            cwd,
        )
        self.assertEqual(codex[:2], ["codex", "exec"])
        self.assertIn("gpt-5.6-sol", codex)
        self.assertIn('model_reasoning_effort="high"', codex)
        self.assertIn("tools.web_search=true", codex)
        self.assertNotIn("--ignore-user-config", codex)

    def test_search_plans_are_ultradeep_and_branch_local(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            claude_dir = root / "claude_research"
            codex_dir = root / "codex_research"
            claude = self.runner.build_search_plan(
                "TEST",
                "Research TEST independently.",
                claude_dir / "search_as_code",
            )
            codex = self.runner.build_search_plan(
                "TEST",
                "Research TEST independently.",
                codex_dir / "search_as_code",
            )
            self.assertEqual(claude["mode"], "ultradeep")
            self.assertEqual(codex["mode"], "ultradeep")
            self.assertGreaterEqual(len(claude["queries"]), 10)
            self.assertGreaterEqual(len(codex["queries"]), 10)
            self.assertIn("claude_research", claude["output_dir"])
            self.assertNotIn("codex_research", claude["output_dir"])
            self.assertIn("codex_research", codex["output_dir"])
            self.assertNotIn("claude_research", codex["output_dir"])

    def test_timeout_capture_preserves_partial_text(self):
        result = self.runner.run_capture(
            [
                sys.executable,
                "-c",
                "import time; print('partial', flush=True); time.sleep(2)",
            ],
            timeout=1,
        )
        self.assertEqual(result["returncode"], 124)
        self.assertEqual(result["status"], "timeout")
        self.assertIn("partial", result["stdout"])

    def run_dry(self, project_dir: Path, *, fail: str | None = None):
        env = os.environ.copy()
        if fail is not None:
            env["PARALLAX_DRY_RUN_FAIL"] = fail
        else:
            env.pop("PARALLAX_DRY_RUN_FAIL", None)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "TEST",
                "--dry-run",
                "--project-dir",
                str(project_dir),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=60,
            check=False,
        )

    def assert_branch_package(self, branch_dir: Path, branch: str):
        required = [
            "01_scope_and_assumptions.md",
            "02_source_manifest.csv",
            "03_evidence_ledger.csv",
            "04_catalyst_and_pos_model.py",
            "05_valuation_model.py",
            "06_model_outputs.csv",
            "07_working_research.md",
            "08_preliminary_report.md",
            "FINAL_REPORT.md",
            "FINAL_REPORT.html",
            "VERIFICATION_LOG.md",
            "sources.jsonl",
            "evidence.jsonl",
            "audit_manifest.json",
            "run_manifest.json",
            "PARALLAX_BRANCH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((branch_dir / name).is_file(), f"missing {branch}/{name}")

        workbooks = list(branch_dir.glob("*_Model.xlsx"))
        self.assertEqual(len(workbooks), 1)
        self.assertTrue(zipfile.is_zipfile(workbooks[0]))

        lane_dirs = sorted((branch_dir / "lanes").glob("lane_*"))
        self.assertEqual(len(lane_dirs), 4)
        for lane_dir in lane_dirs:
            self.assertTrue((lane_dir / "prompt.md").is_file())
            self.assertTrue((lane_dir / "report.md").is_file())

        search_plan = json.loads(
            (branch_dir / "search_as_code" / "search_plan.json").read_text(encoding="utf-8")
        )
        self.assertEqual(search_plan["mode"], "ultradeep")
        self.assertGreaterEqual(len(search_plan["queries"]), 10)

    def test_dual_dry_run_produces_two_isolated_packages_and_no_merge(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            result = self.run_dry(project)
            self.assertEqual(result.returncode, 0, result.stderr)

            root_dirs = sorted(path.name for path in project.iterdir() if path.is_dir())
            self.assertEqual(root_dirs, ["claude_research", "codex_research"])
            self.assert_branch_package(project / "claude_research", "claude")
            self.assert_branch_package(project / "codex_research", "codex")

            root_names = [path.name.lower() for path in project.rglob("*")]
            forbidden = ("merged", "verdict", "claim_matrix", "final_answer")
            for token in forbidden:
                self.assertFalse(
                    any(token in name for name in root_names),
                    f"forbidden merge artifact token found: {token}",
                )

            manifest = json.loads((project / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["workflow"], "parallax")
            self.assertEqual(manifest["topology"], "dual_gauntlet_fast_no_merge")
            self.assertEqual(manifest["status"], "complete_both")
            self.assertEqual(manifest["topology_gate"]["status"], "pass")
            self.assertEqual(set(manifest["branches"]), {"claude", "codex"})
            self.assertEqual(len(manifest["branches"]["claude"]["workers"]), 4)
            self.assertEqual(len(manifest["branches"]["codex"]["workers"]), 4)

            claude_prompts = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (project / "claude_research").rglob("prompt.md")
            )
            codex_prompts = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (project / "codex_research").rglob("prompt.md")
            )
            self.assertNotIn(str(project / "codex_research"), claude_prompts)
            self.assertNotIn(str(project / "claude_research"), codex_prompts)

            forbidden = project / "claude_research" / "merged_verdict.md"
            forbidden.write_text("must be rejected\n", encoding="utf-8")
            valid, errors = self.runner.validate_branch_package(
                project / "claude_research", 3000
            )
            self.assertFalse(valid)
            self.assertTrue(
                any("forbidden merger artifact path" in error for error in errors),
                errors,
            )
            topology_valid, topology_errors = self.runner.validate_project_topology(project)
            self.assertFalse(topology_valid)
            self.assertTrue(
                any("forbidden merger artifact path" in error for error in topology_errors),
                topology_errors,
            )

    def test_one_branch_failure_preserves_other_and_returns_partial(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            result = self.run_dry(project, fail="claude")
            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertFalse((project / "claude_research" / "FINAL_REPORT.md").exists())
            self.assert_branch_package(project / "codex_research", "codex")
            manifest = json.loads((project / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "partial_codex")
            self.assertEqual(manifest["branches"]["claude"]["status"], "failed")
            self.assertEqual(manifest["branches"]["codex"]["status"], "complete")

    def test_search_failure_stops_branch_before_lead(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            result = self.run_dry(project, fail="claude_search")
            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertFalse((project / "claude_research" / "FINAL_REPORT.md").exists())
            self.assert_branch_package(project / "codex_research", "codex")
            manifest = json.loads((project / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
            claude = manifest["branches"]["claude"]
            self.assertEqual(manifest["status"], "partial_codex")
            self.assertEqual(claude["status"], "failed")
            self.assertEqual(claude["search_as_code"]["status"], "failed")
            self.assertEqual(claude["lead"]["status"], "not_run")

    def test_both_branch_failure_never_fabricates_reports(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            result = self.run_dry(project, fail="both")
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse((project / "claude_research" / "FINAL_REPORT.md").exists())
            self.assertFalse((project / "codex_research" / "FINAL_REPORT.md").exists())
            manifest = json.loads((project / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "failed_both")

    def test_nonempty_project_is_refused_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            project.mkdir()
            sentinel = project / "user-owned.txt"
            sentinel.write_text("preserve me\n", encoding="utf-8")
            result = self.run_dry(project)
            self.assertEqual(result.returncode, 5)
            self.assertIn("project directory is not empty", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse((project / "RUN_MANIFEST.json").exists())

    def test_preferred_or_combined_outputs_fail_no_merge_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "TEST_Parallax"
            result = self.run_dry(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            branch = project / "claude_research"

            preferred = branch / "preferred_model.md"
            preferred.write_text("forbidden comparison output\n", encoding="utf-8")
            valid, errors = self.runner.validate_branch_package(branch, 3000)
            self.assertFalse(valid)
            self.assertTrue(
                any("forbidden merger artifact path" in error for error in errors),
                errors,
            )
            preferred.unlink()

            report = branch / "FINAL_REPORT.md"
            original_report = report.read_text(encoding="utf-8")
            report.write_text(
                original_report + "\n## Combined verdict\nForbidden.\n",
                encoding="utf-8",
            )
            valid, errors = self.runner.validate_branch_package(branch, 3000)
            self.assertFalse(valid)
            self.assertTrue(
                any("forbidden comparison phrase" in error for error in errors),
                errors,
            )
            report.write_text(original_report, encoding="utf-8")

            html_report = branch / "FINAL_REPORT.html"
            html_report.write_text(
                html_report.read_text(encoding="utf-8")
                + "\n<h2>Combined verdict</h2><p>Prefer Claude.</p>\n",
                encoding="utf-8",
            )
            valid, errors = self.runner.validate_branch_package(branch, 3000)
            self.assertFalse(valid)
            self.assertTrue(
                any(
                    "FINAL_REPORT.html contains forbidden comparison phrase" in error
                    for error in errors
                ),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
