"""Lifecycle checks using the same API boundary as the live monitor."""
import json
import runpy
import fcntl
import tempfile
import unittest
from pathlib import Path

module = runpy.run_path(str(Path(__file__).with_name("factory-monitor")))
monitor = module["monitor"]
relevance = module["relevance"]


def deliver(_worker, _root):
    return {"decision": "delivered", "reason": "issue open and no merged PR",
            "issue": 24, "branch": "factory/24-monitor-delivery", "pr": None}


class HandoffTests(unittest.TestCase):
    def test_uncertain_worker_submission_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def api(method, path, body=None):
                if method == "post":
                    raise RuntimeError("lost submission response")
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {}}}
            with self.assertRaises(RuntimeError):
                monitor("ses_owner", "ses_worker", root, "work", api, relevance=deliver)
            self.assertIn("lost submission response", (root / "ses_worker.json").read_text())
            with self.assertRaises(ValueError):
                monitor("ses_owner", "ses_worker", root, "work", api, relevance=deliver)

    def test_active_worker_waits_and_lock_excludes_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "ses_worker.lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    monitor("ses_owner", "ses_worker", root, relevance=deliver)
            active = True
            posts = []

            def api(method, path, body=None):
                if method == "post":
                    posts.append(body)
                    return {}
                if path.endswith("/active"):
                    return {"data": {"ses_worker": {"type": "running"}} if active else {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": 1}}}

            def finish(_):
                nonlocal active
                self.assertFalse(posts)
                active = False

            monitor("ses_owner", "ses_worker", root, call=api, sleep=finish, relevance=deliver)
            self.assertEqual(len(posts), 1)

    def test_resume_wait_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            idle = 1
            messages = []

            def api(method, path, body=None):
                nonlocal idle
                if method == "post":
                    messages.append((path, body))
                    if path.endswith("/ses_worker/prompt"):
                        idle = 2
                    return {}
                if path.endswith("/active"):
                    return {"data": {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": idle}, "outcome": "succeeded"}}

            monitor("ses_owner", "ses_worker", root, "fix review", api, relevance=deliver)
            monitor("ses_owner", "ses_worker", root, call=api, relevance=deliver)
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[-1][1]["delivery"], "queue")
            self.assertTrue(messages[-1][1]["resume"])

    def test_pause_and_delivery_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paused = root / "ses_owner.paused"
            paused.touch()
            posts = []

            def api(method, path, body=None):
                if method == "post":
                    posts.append(body)
                    raise RuntimeError("connection lost after submission")
                if path.endswith("/active"):
                    return {"data": {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": 1}, "outcome": "failed"}}

            monitor("ses_owner", "ses_worker", root, call=api, relevance=deliver)
            self.assertFalse(posts)
            paused.unlink()
            with self.assertRaises(RuntimeError):
                monitor("ses_owner", "ses_worker", root, call=api, relevance=deliver)
            with self.assertRaises(ValueError):
                monitor("ses_owner", "ses_worker", root, call=api, relevance=deliver)
            self.assertEqual(len(posts), 1)
            lines = (root / "deliveries.jsonl").read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["decision"], "failed")
            self.assertIn("connection lost", record["reason"])

    def test_suppressed_delivery_is_recorded_and_not_posted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = []

            def api(method, path, body=None):
                if method == "post":
                    posts.append(body)
                    return {}
                if path.endswith("/active"):
                    return {"data": {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": 1}, "outcome": "succeeded"}}

            def suppressed(_worker, _root):
                return {"decision": "suppressed", "reason": "issue #14 is closed",
                        "issue": 14, "branch": "factory/14-gate", "pr": None}

            monitor("ses_owner", "ses_worker", root, call=api, relevance=suppressed)
            monitor("ses_owner", "ses_worker", root, call=api, relevance=suppressed)
            self.assertFalse(posts)
            lines = (root / "deliveries.jsonl").read_text().strip().splitlines()
            self.assertEqual(len(lines), 2)
            entry = json.loads(lines[0])
            self.assertEqual(entry["decision"], "suppressed")
            self.assertEqual(entry["issue"], 14)
            self.assertEqual(entry["branch"], "factory/14-gate")
            self.assertEqual(entry["worker"], "ses_worker")
            self.assertEqual(entry["idle"], 1)
            self.assertEqual(entry["outcome"], "succeeded")
            self.assertIn("closed", entry["reason"])
            self.assertIn("time", entry)

    def test_unknown_state_fails_closed_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = []

            def api(method, path, body=None):
                if method == "post":
                    posts.append(body)
                    return {}
                if path.endswith("/active"):
                    return {"data": {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": 1}, "outcome": "succeeded"}}

            def unknown(_worker, _root):
                return {"decision": "failed", "reason": "issue state unknown: gh: not found",
                        "issue": 14, "branch": "factory/14-gate", "pr": None}

            monitor("ses_owner", "ses_worker", root, call=api, relevance=unknown)
            self.assertFalse(posts)
            entry = json.loads((root / "deliveries.jsonl").read_text().strip())
            self.assertEqual(entry["decision"], "failed")
            self.assertIn("not found", entry["reason"])
            state = json.loads((root / "ses_worker.json").read_text())
            self.assertEqual(state["status"], "failed")

    def test_delivered_notification_names_issue_branch_and_pull_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts = []

            def api(method, path, body=None):
                if method == "post":
                    posts.append((path, body))
                    return {}
                if path.endswith("/active"):
                    return {"data": {}}
                return {"data": {"agent": "factory" if path.endswith("ses_owner") else "worker",
                                 "projectID": "project", "time": {"idle": 7}, "outcome": "succeeded"}}

            def current(_worker, _root):
                return {"decision": "delivered", "reason": "issue open and no merged PR",
                        "issue": 24, "branch": "factory/24-monitor-delivery",
                        "pr": "https://github.com/Jimfarrugia/software-factory/pull/25"}

            monitor("ses_owner", "ses_worker", root, call=api, relevance=current)
            self.assertEqual(len(posts), 1)
            text = posts[0][1]["text"]
            self.assertIn("ses_worker", text)
            self.assertIn("#24", text)
            self.assertIn("factory/24-monitor-delivery", text)
            self.assertIn("https://github.com/Jimfarrugia/software-factory/pull/25", text)
            entry = json.loads((root / "deliveries.jsonl").read_text().strip())
            self.assertEqual(entry["decision"], "delivered")
            self.assertEqual(entry["idle"], 7)


class RelevanceTests(unittest.TestCase):
    def root(self, directory, worker="ses_worker", issue=24, branch="factory/24-x"):
        state = Path(directory) / "handoffs"
        sessions = Path(directory) / "sessions"
        state.mkdir(exist_ok=True)
        sessions.mkdir(exist_ok=True)
        (sessions / f"{worker}.json").write_text(
            json.dumps({"issue": issue, "branch": branch}))
        return state

    def test_open_issue_without_pull_request_is_delivered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            def gh(args):
                return {"state": "OPEN"} if args[0] == "issue" else []
            result = relevance("ses_worker", root, gh=gh)
            self.assertEqual(result["decision"], "delivered")
            self.assertEqual(result["issue"], 24)
            self.assertEqual(result["branch"], "factory/24-x")
            self.assertIsNone(result["pr"])

    def test_closed_issue_is_suppressed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            def gh(args):
                return {"state": "CLOSED"} if args[0] == "issue" else []
            result = relevance("ses_worker", root, gh=gh)
            self.assertEqual(result["decision"], "suppressed")
            self.assertIn("closed", result["reason"])

    def test_merged_pull_request_is_suppressed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            url = "https://github.com/Jimfarrugia/software-factory/pull/5"
            def gh(args):
                return {"state": "OPEN"} if args[0] == "issue" else [{"state": "MERGED", "url": url}]
            result = relevance("ses_worker", root, gh=gh)
            self.assertEqual(result["decision"], "suppressed")
            self.assertEqual(result["pr"], url)
            self.assertIn("merged", result["reason"])

    def test_issue_lookup_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            def gh(args):
                raise RuntimeError("gh: not found")
            result = relevance("ses_worker", root, gh=gh)
            self.assertEqual(result["decision"], "failed")
            self.assertIn("issue state unknown", result["reason"])

    def test_pull_request_lookup_error_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.root(directory)
            def gh(args):
                if args[0] == "issue":
                    return {"state": "OPEN"}
                raise RuntimeError("network unreachable")
            result = relevance("ses_worker", root, gh=gh)
            self.assertEqual(result["decision"], "failed")
            self.assertIn("PR state unknown", result["reason"])

    def test_missing_session_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "handoffs"
            root.mkdir()
            (Path(directory) / "sessions").mkdir()
            result = relevance("ses_worker", root, gh=lambda args: {})
            self.assertEqual(result["decision"], "failed")
            self.assertIn("session metadata unavailable", result["reason"])


if __name__ == "__main__":
    unittest.main()
