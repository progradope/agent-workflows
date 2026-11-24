"""Exercise real CLI behavior in temporary projects and home directories."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "skills/deliver/scripts/checkpoint.py"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="deliver test ' spaces ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Workflow Test")
        self.git("config", "user.email", "workflow@example.invalid")
        self.plan = self.project / "plan.md"
        self.plan.write_text("Fix retries; add a regression test.\n")
        self.git("add", "plan.md")
        self.git("commit", "-qm", "test: initial plan")
        self.head = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.project), *args],
                              text=True, capture_output=True, check=True)

    def cp(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(CHECKPOINT), "--project", str(self.project),
             "--task", "retry-fix", "--state-root", str(self.base / "state"), *args],
            text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return json.loads(result.stdout) if ok and args[0] != "path" else result

    def init(self):
        return self.cp("init", "--plan", str(self.plan), "--thread-ref", "test-thread")

    def approve(self):
        self.cp("approve", "--user-ref", "user-message-approval")

    def advance_to_publishing(self):
        for phase in ["validating", "documenting", "reviewing"]:
            self.cp("phase", phase)
        self.cp("phase", "awaiting_output_review", "--head", self.head,
                "--evidence", "qa-evidence.md: all rows PASS")
        return self.cp("signoff", "--user-ref", "user-message-output-ok")

    def advance_to_watching(self):
        self.advance_to_publishing()
        return self.cp("phase", "watching", "--head", self.head,
                       "--pr", "https://github.com/example/project/pull/1",
                       "--evidence", "PR created; remote checks pending")

    def test_approval_snapshot_and_private_state(self):
        state = self.init()
        self.assertEqual(state["phase"], "awaiting_approval")
        self.cp("phase", "implementing", ok=False)
        self.approve()
        path = Path(self.cp("path").stdout.strip())
        self.assertEqual((path / "approved-plan.md").read_bytes(), self.plan.read_bytes())
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((path / "checkpoint.json").stat().st_mode & 0o777, 0o600)
        self.cp("init", "--plan", str(self.plan), "--thread-ref", "other", ok=False)

    def test_unrecorded_plan_change_and_scope_amendments(self):
        self.init()
        self.approve()
        self.cp("phase", "validating")
        self.plan.write_text("Fix retries with a shared guard and regression test.\n")
        self.assertFalse(self.cp("status")["plan_matches"])
        self.cp("phase", "documenting", ok=False)
        state = self.cp("amend", "--within-scope", "--reason", "Reviewer found a second retry path")
        self.assertEqual(state["phase"], "implementing")
        self.assertIsNotNone(state["approval"])
        self.cp("phase", "validating")
        state = self.cp("amend", "--reason", "Now requires a new persistent data model")
        self.assertIsNone(state["approval"])
        self.assertEqual(state["phase"], "awaiting_approval")
        self.cp("phase", "implementing", ok=False)

    def test_review_repair_and_latest_head_requirements(self):
        self.init()
        self.approve()
        self.cp("phase", "ready", ok=False)
        self.advance_to_watching()
        self.cp("phase", "ready", "--head", "0" * 40, "--evidence", "old checks", ok=False)
        self.cp("phase", "implementing", "--evidence", "Remote review found a retry bug")
        self.advance_to_watching()
        state = self.cp("phase", "ready", "--head", self.head,
                        "--evidence", "Fresh checks and required reviews verified")
        self.assertEqual(state["phase"], "ready")
        self.assertEqual(state["head"], self.head)
        self.assertEqual(state["history"][-1]["action"], "phase")

    def test_block_resume_and_plan_changes(self):
        self.init()
        self.cp("block", "--reason", "Waiting for plan approval")
        self.cp("resume")
        self.approve()
        self.cp("block", "--reason", "External service unavailable")
        self.plan.write_text("A changed plan needs an amendment.\n")
        self.cp("resume", ok=False)
        self.cp("amend", "--reason", "Scope changed")
        self.approve()

    def test_ready_remains_repairable_until_a_confirmed_merge(self):
        self.init()
        self.approve()
        self.advance_to_watching()
        self.cp("phase", "ready", "--head", self.head, "--evidence", "Checks green")
        self.cp("phase", "implementing", "--evidence", "Late reviewer suggestion")
        self.advance_to_watching()
        state = self.cp("complete", "--outcome", "merged", "--head", self.head,
                        "--evidence", "Fresh GitHub state is MERGED")
        self.assertEqual(state["phase"], "merged")
        self.assertEqual(self.cp("status")["phase"], "merged")
        self.cp("phase", "implementing", ok=False)
        self.cp("block", "--reason", "Old event", ok=False)
        self.cp("amend", "--within-scope", "--reason", "Old suggestion", ok=False)

    def test_remote_closure_is_recordable_while_blocked_with_a_stale_checkout(self):
        self.init()
        self.approve()
        self.advance_to_watching()
        self.cp("block", "--reason", "Waiting for a scope decision")
        self.plan.write_text("A revised scope is still awaiting a user decision.\n")
        remote_head = "b" * 40
        state = self.cp("complete", "--outcome", "closed", "--head", remote_head,
                        "--evidence", "Fresh GitHub state is CLOSED without merge")
        self.assertEqual(state["phase"], "closed")
        self.assertEqual(state["head"], remote_head)
        self.assertNotIn("resume_phase", state)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.head)
        self.cp("resume", ok=False)

    def test_completion_requires_a_tracked_pr_and_explicit_evidence(self):
        self.init()
        self.cp("complete", "--outcome", "merged", "--head", self.head,
                "--evidence", "No PR has been tracked", ok=False)
        self.approve()
        self.advance_to_watching()
        self.cp("complete", "--outcome", "merged", "--head", self.head, ok=False)
        self.cp("complete", "--outcome", "merged", "--head", "bad",
                "--evidence", "Malformed head", ok=False)
        self.assertEqual(self.cp("status")["phase"], "watching")

    def test_terminal_status_remains_readable_after_the_plan_is_archived(self):
        self.init()
        self.approve()
        self.advance_to_watching()
        self.cp("complete", "--outcome", "merged", "--head", self.head,
                "--evidence", "Fresh GitHub merge observed")
        self.plan.unlink()
        state = self.cp("status")
        self.assertEqual(state["phase"], "merged")
        self.assertIsNone(state["plan_matches"])

    def test_first_publication_requires_output_signoff_of_current_head(self):
        self.init()
        self.approve()
        for phase in ["validating", "documenting", "reviewing"]:
            self.cp("phase", phase)
        self.cp("phase", "publishing", ok=False)
        self.cp("signoff", "--user-ref", "too-early", ok=False)
        self.cp("phase", "awaiting_output_review", "--head", self.head, ok=False)
        self.cp("phase", "awaiting_output_review", "--head", "0" * 40,
                "--evidence", "packet", ok=False)
        state = self.cp("phase", "awaiting_output_review", "--head", self.head,
                        "--evidence", "qa-evidence.md")
        self.assertEqual(state["phase"], "awaiting_output_review")
        self.cp("phase", "publishing", ok=False)
        # Requested change goes back to implementation; sign-off is for a new head.
        self.cp("phase", "implementing", "--evidence", "User asked for a copy change")
        (self.project / "fix.txt").write_text("fix\n")
        self.git("add", "fix.txt")
        self.git("commit", "-qm", "fix: copy change")
        new_head = self.git("rev-parse", "HEAD").stdout.strip()
        for phase in ["validating", "documenting", "reviewing"]:
            self.cp("phase", phase)
        self.cp("phase", "awaiting_output_review", "--head", new_head,
                "--evidence", "qa-evidence.md refreshed")
        state = self.cp("signoff", "--user-ref", "user-message-output-ok")
        self.assertEqual(state["phase"], "publishing")
        self.assertEqual(state["output_signoff"]["head"], new_head)
        self.assertEqual(state["history"][-1]["evidence"], "user-message-output-ok")

    def test_in_scope_repairs_after_publication_need_no_new_signoff(self):
        self.init()
        self.approve()
        self.advance_to_watching()
        self.cp("phase", "implementing", "--evidence", "CI failure")
        (self.project / "repair.txt").write_text("repair\n")
        self.git("add", "repair.txt")
        self.git("commit", "-qm", "fix: ci repair")
        for phase in ["validating", "documenting", "reviewing", "publishing"]:
            self.cp("phase", phase)
        self.assertEqual(self.cp("status")["phase"], "publishing")

    def test_scope_change_clears_output_signoff(self):
        self.init()
        self.approve()
        self.advance_to_publishing()
        self.plan.write_text("Fix retries and redesign the queue.\n")
        state = self.cp("amend", "--reason", "Scope grew")
        self.assertNotIn("output_signoff", state)
        self.assertEqual(state["phase"], "awaiting_approval")

    def test_pr_url_accepts_normal_names_and_rejects_whitespace(self):
        self.init()
        self.approve()
        self.advance_to_publishing()
        for bad in ["https://git hub.com/acme/widget/pull/17",
                    "https://github.com/acme/wid get/pull/17",
                    "https://github.com/acme/wid\\get/pull/17"]:
            self.cp("phase", "watching", "--head", self.head, "--pr", bad,
                    "--evidence", "Pending", ok=False)
        state = self.cp("phase", "watching", "--head", self.head,
                        "--pr", "https://github.com/acme/widgets/pull/17",
                        "--evidence", "Pending")
        self.assertEqual(state["pr"], "https://github.com/acme/widgets/pull/17")

    def test_state_rejects_path_traversal_and_blank_evidence(self):
        bad = subprocess.run(
            [sys.executable, str(CHECKPOINT), "--project", str(self.project),
             "--task", "../escape", "path"], capture_output=True)
        self.assertNotEqual(bad.returncode, 0)
        self.init()
        self.cp("approve", "--user-ref", " ", ok=False)
        self.cp("amend", "--within-scope", "--reason", "No approval exists", ok=False)

    def installer(self, home, *args, ok=True):
        result = subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--home", str(home),
             "--targets", "shared,cursor,claude", *args],
            text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result

    def test_install_idempotence_preservation_and_uninstall(self):
        home = self.base / "home"
        existing = home / ".agents/skills/audit"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("User's existing audit")
        self.installer(home)
        self.installer(home)
        self.installer(home, "--check")
        for folder in [".agents", ".cursor", ".claude"]:
            self.assertEqual((home / folder / "skills/deliver").resolve(),
                             ROOT / "skills/deliver")
        self.installer(home, "--uninstall")
        self.assertEqual((existing / "SKILL.md").read_text(), "User's existing audit")
        self.assertFalse((home / ".agents/skills/deliver").exists())

    def test_install_conflict_is_preflighted_without_partial_changes(self):
        home = self.base / "conflict-home"
        conflict = home / ".claude/skills/deliver"
        conflict.mkdir(parents=True)
        (conflict / "SKILL.md").write_text("Existing deliver")
        self.installer(home, ok=False)
        self.assertFalse((home / ".agents").exists())
        self.assertEqual((conflict / "SKILL.md").read_text(), "Existing deliver")

    def test_installer_check_detects_missing_and_broken_skills(self):
        home = self.base / "check-home"
        self.installer(home, "--check", ok=False)
        self.installer(home)
        (home / ".cursor/skills/test").unlink()
        (home / ".cursor/skills/test").symlink_to(home / "missing")
        self.installer(home, "--check", ok=False)


if __name__ == "__main__":
    unittest.main()
