"""Exercise the shipped offline fixture, contract checks and shared retest format."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "skills/linsist-agent"
ASSETS = SKILL / "assets"
sys.path.insert(0, str(ASSETS))
sys.path.insert(0, str(REPO_ROOT / "skills/linsist-coach/scripts"))
import agent_lab
import check_agent_lab
import scan_retest


class TestAgentOffline(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, "-S", str(script), *map(str, args)],
                              text=True, capture_output=True, timeout=5)

    def test_fake_llm_is_finite_and_copies_script_data(self):
        script = [{"type": "final", "answer": {"value": 5}}]
        llm = agent_lab.FakeLLM(script)
        script[0]["answer"]["value"] = 99
        reply = llm.next()
        self.assertEqual(reply["answer"]["value"], 5)
        reply["answer"]["value"] = 10
        self.assertEqual(llm.replies[0]["answer"]["value"], 5)
        with self.assertRaises(RuntimeError):
            llm.next()
        self.assertEqual(llm.calls, 1)

    def test_smoke_needs_no_site_packages_and_does_not_claim_exercise_pass(self):
        result = self.run_cli(ASSETS / "agent_lab.py", "--smoke")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "fixture_ready")
        self.assertEqual(report["calls"], 2)
        self.assertFalse(report["exercises_passed"])

    def test_all_unwritten_exercises_fail_honestly(self):
        self.assertEqual(set(check_agent_lab.CHECKS), {f"A{i:02d}" for i in range(1, 14)})
        for exercise in check_agent_lab.CHECKS:
            with self.subTest(exercise=exercise):
                result = self.run_cli(ASSETS / "check_agent_lab.py", "--exercise", exercise,
                                      "--submission", ASSETS / "agent_lab.py")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NotImplementedError", result.stderr)
                self.assertNotIn('"status": "passed"', result.stdout)

    def test_checker_rejects_a_submission_that_leaks_private_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            student = Path(temp) / "student.py"
            student.write_text("def redact_event(event):\n    return dict(event)\n", encoding="utf-8")
            result = self.run_cli(ASSETS / "check_agent_lab.py", "--exercise", "A11", "--submission", student)
            self.assertEqual(result.returncode, 1)
            self.assertIn("AssertionError", result.stderr)

    def test_checker_positive_control_accepts_expected_observations(self):
        # Calibrate the checker without shipping a worked student solution.
        metadata = {"trace_id": "t1", "step": 1, "tool": "add", "status": "ok", "duration_ms": 5}
        projection = Mock(side_effect=[metadata, {}])
        check_agent_lab.check_trace(SimpleNamespace(redact_event=projection), self)
        self.assertEqual(projection.call_count, 2)

    def test_new_card_uses_existing_two_stage_scanner(self):
        source = (SKILL / "references/records.md").read_text(encoding="utf-8")
        card = re.search(r"```markdown\n(.*?)\n```", source, re.S).group(1)
        card = card.replace("YYYY-MM-DD", "2000-01-03")
        card = card.replace("第 2 轮建议复测日期 (168h)：`2000-01-03`", "第 2 轮建议复测日期 (168h)：`2000-01-08`")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            notes = root / ".linsist/notes"
            notes.mkdir(parents=True)
            note = notes / "agent.md"
            note.write_text(card, encoding="utf-8")
            items = scan_retest.scan_workspace(root)
            self.assertEqual(len(items), 4)
            self.assertEqual(sum(item.is_due() for item in items), 2)
            self.assertFalse(any(item.is_passed() for item in items))
            note.write_text(card.replace("复测状态：待复测", "复测状态：第1轮已通过"), encoding="utf-8")
            items = scan_retest.scan_workspace(root)
            self.assertEqual(sum(item.is_due() and item.stage == 2 for item in items), 2)
            self.assertEqual(sum(item.is_passed() for item in items), 2)

    def test_installed_skill_assets_run_outside_checkout(self):
        with tempfile.TemporaryDirectory(prefix="agent installed ") as temp:
            root = Path(temp)
            dest = root / "client/skills"
            result = self.run_cli(REPO_ROOT / "scripts/install.py", "--dest", dest)
            self.assertEqual(result.returncode, 0, result.stderr)
            assets = dest / "linsist-agent/assets"
            result = self.run_cli(assets / "agent_lab.py", "--smoke")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli(assets / "check_agent_lab.py", "--exercise", "A01",
                                  "--submission", assets / "agent_lab.py")
            self.assertEqual(result.returncode, 1)
            self.assertIn("NotImplementedError", result.stderr)

    def test_standalone_offline_assets_do_not_depend_on_other_skills(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            standalone = Path(temp) / "linsist-agent"
            shutil.copytree(SKILL, standalone)
            result = self.run_cli(standalone / "assets/agent_lab.py", "--smoke")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "fixture_ready")
            result = self.run_cli(standalone / "assets/check_agent_lab.py", "--exercise", "A01",
                                  "--submission", standalone / "assets/agent_lab.py")
            self.assertEqual(result.returncode, 1)
            self.assertIn("NotImplementedError", result.stderr)


if __name__ == "__main__":
    unittest.main()
