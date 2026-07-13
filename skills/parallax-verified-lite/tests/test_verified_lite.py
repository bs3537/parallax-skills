import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_parallax_verified_lite.py"


class VerifiedLiteDryRunTests(unittest.TestCase):
    def run_cli(self, *extra):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        command = [
            sys.executable,
            str(SCRIPT),
            "TEST",
            "--dry-run",
            "--profile",
            "quick",
            "--run-base",
            tmpdir.name,
            *extra,
        ]
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
        runs = sorted((Path(tmpdir.name) / "TEST" / "runs").glob("*"))
        self.assertEqual(len(runs), 1, result.stderr)
        manifest = json.loads((runs[0] / "manifest.json").read_text())
        return result, manifest, runs[0]

    def test_verified_policy_and_budgets(self):
        result, manifest, run_dir = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["workflow"], "parallax-verified-lite")
        self.assertEqual(manifest["policy"], "verified")
        self.assertEqual(manifest["budgets"]["lane_timeout"], 240)
        self.assertEqual(manifest["budgets"]["max_verifications"], 4)
        self.assertEqual(manifest["retry_policy"], "none")
        self.assertTrue((run_dir / "merged_answer.md").exists())

    def test_verified_single_lane_disclosure(self):
        result, manifest, run_dir = self.run_cli("--dry-run-fail", "claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["status"], "complete_partial_single_lane")
        self.assertTrue((run_dir / "merged_answer.md").read_text().startswith("> **PARTIAL SINGLE-LANE RESULT:**"))


if __name__ == "__main__":
    unittest.main()
