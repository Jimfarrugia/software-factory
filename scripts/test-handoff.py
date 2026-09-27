"""Lifecycle checks using the same API boundary as the live monitor."""
import runpy
import fcntl
import tempfile
import unittest
from pathlib import Path

monitor = runpy.run_path(str(Path(__file__).with_name("factory-monitor")))["monitor"]


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
                monitor("ses_owner", "ses_worker", root, "work", api)
            self.assertIn("lost submission response", (root / "ses_worker.json").read_text())
            with self.assertRaises(ValueError):
                monitor("ses_owner", "ses_worker", root, "work", api)

    def test_active_worker_waits_and_lock_excludes_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "ses_worker.lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    monitor("ses_owner", "ses_worker", root)
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

            monitor("ses_owner", "ses_worker", root, call=api, sleep=finish)
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

            monitor("ses_owner", "ses_worker", root, "fix review", api)
            monitor("ses_owner", "ses_worker", root, call=api)
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

            monitor("ses_owner", "ses_worker", root, call=api)
            self.assertFalse(posts)
            paused.unlink()
            with self.assertRaises(RuntimeError):
                monitor("ses_owner", "ses_worker", root, call=api)
            with self.assertRaises(ValueError):
                monitor("ses_owner", "ses_worker", root, call=api)
            self.assertEqual(len(posts), 1)


if __name__ == "__main__":
    unittest.main()
