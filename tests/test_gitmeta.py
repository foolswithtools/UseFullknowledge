import os
import subprocess
import tempfile
import unittest

from kbtool.gitmeta import git_updated_map, reconcile


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


class TestGitUpdatedMap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        run(["git", "init", "-q", "."], self.root)
        run(["git", "config", "user.email", "t@example.com"], self.root)
        run(["git", "config", "user.name", "Test"], self.root)
        os.makedirs(os.path.join(self.root, "kb", "explainer"))

    def tearDown(self):
        self.tmp.cleanup()

    def _commit(self, relpath, text, when):
        full = os.path.join(self.root, relpath)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(text)
        run(["git", "add", "-A"], self.root)
        env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        subprocess.run(
            ["git", "commit", "-q", "-m", f"add {relpath}"],
            cwd=self.root, check=True, capture_output=True, env=env,
        )

    def test_reports_last_commit_time_per_file(self):
        self._commit("kb/explainer/a.md", "one", "2026-08-01T10:00:00-07:00")
        self._commit("kb/explainer/b.md", "two", "2026-08-02T11:00:00-07:00")

        result = git_updated_map(self.root)

        self.assertIn("kb/explainer/a.md", result)
        self.assertTrue(result["kb/explainer/a.md"].startswith("2026-08-01T10:00:00"))
        self.assertTrue(result["kb/explainer/b.md"].startswith("2026-08-02T11:00:00"))

    def test_uses_a_single_git_invocation_for_the_whole_repo(self):
        """Per-file `git log` is ~270x slower; the whole map must come from one pass."""
        self._commit("kb/explainer/a.md", "one", "2026-08-01T10:00:00-07:00")
        self._commit("kb/explainer/b.md", "two", "2026-08-02T11:00:00-07:00")
        self._commit("kb/explainer/c.md", "three", "2026-08-03T12:00:00-07:00")

        calls = []
        real_run = subprocess.run

        def counting_run(cmd, *args, **kwargs):
            if cmd and cmd[0] == "git":
                calls.append(cmd)
            return real_run(cmd, *args, **kwargs)

        git_updated_map(self.root, runner=counting_run)

        self.assertEqual(len(calls), 1, f"expected 1 git call, got {len(calls)}: {calls}")

    def test_reports_the_latest_commit_when_a_file_changes_twice(self):
        self._commit("kb/explainer/a.md", "one", "2026-08-01T10:00:00-07:00")
        self._commit("kb/explainer/a.md", "one edited", "2026-08-05T09:00:00-07:00")

        result = git_updated_map(self.root)

        self.assertTrue(result["kb/explainer/a.md"].startswith("2026-08-05T09:00:00"))

    def test_uncommitted_file_is_absent_rather_than_guessed(self):
        with open(os.path.join(self.root, "kb", "explainer", "new.md"), "w") as handle:
            handle.write("not committed")

        self.assertNotIn("kb/explainer/new.md", git_updated_map(self.root))


class TestReconcile(unittest.TestCase):
    def test_matching_timestamps_produce_no_problem(self):
        self.assertIsNone(
            reconcile("2026-08-14T06:12:00-07:00", "2026-08-14T06:40:00-07:00")
        )

    def test_frontmatter_far_behind_git_is_flagged(self):
        """The agent edited the file and forgot to bump updated_at."""
        problem = reconcile("2026-08-01T06:12:00-07:00", "2026-08-14T06:12:00-07:00")

        self.assertIsNotNone(problem)
        self.assertIn("updated_at", problem)

    def test_future_dated_frontmatter_is_flagged(self):
        problem = reconcile("2026-09-01T06:12:00-07:00", "2026-08-14T06:12:00-07:00")

        self.assertIsNotNone(problem)
        self.assertIn("future", problem.lower())

    def test_timezone_offsets_are_compared_as_instants_not_text(self):
        """Same instant, different offsets, must not be flagged as drift."""
        self.assertIsNone(
            reconcile("2026-08-14T06:12:00-07:00", "2026-08-14T13:12:00+00:00")
        )

    def test_uncommitted_file_is_not_flagged(self):
        self.assertIsNone(reconcile("2026-08-14T06:12:00-07:00", None))


if __name__ == "__main__":
    unittest.main()
