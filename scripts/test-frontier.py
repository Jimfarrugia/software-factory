"""Hermetic tests for the dispatch eligibility decision."""
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

frontier = runpy.run_path(str(Path(__file__).with_name("factory-frontier")))
verdict = frontier["dispatch_verdict"]
lint = frontier["lint_issues"]
main = frontier["main"]


def issue(number, body="", labels=(), state="OPEN", **extra):
    return {"number": number, "body": body, "labels": list(labels), "state": state,
            "title": f"Issue {number}", **extra}


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.parent = issue(1, labels=["factory:type:feature", "factory:spec-approved"])
        self.ticket = issue(2, "Parent: #1\nBlocked by: None",
                            ["factory:type:implementation", "factory:ready"])

    def check(self, ticket=None, others=()):
        return verdict(ticket or self.ticket, [self.parent, *(others)])

    def test_dispatchable_flat_relationships(self):
        self.assertTrue(self.check()["dispatchable"])

    def test_template_sections_resolve_parent_and_blocker(self):
        blocker = issue(3, state="CLOSED")
        ticket = issue(2, "### Parent feature\n#1\n### Blocked by\n#3",
                       ["factory:type:implementation", "factory:ready"])
        self.assertTrue(verdict(ticket, [self.parent, blocker])["dispatchable"])

    def test_missing_malformed_and_missing_issue_parents_fail_closed(self):
        for body, known in (("Blocked by: None", [self.parent]),
                            ("Parent: nope\nBlocked by: None", [self.parent]),
                            ("Parent: #99\nBlocked by: None", [self.parent])):
            with self.subTest(body=body):
                result = verdict(self.ticket | {"body": body}, known)
                self.assertFalse(result["dispatchable"])
                self.assertTrue(result["reasons"])

    def test_parent_type_approval_wayfinder_and_human(self):
        for parent in (issue(1, labels=["factory:type:decision"]),
                       issue(1, labels=["factory:type:feature"]),
                       issue(1, labels=["factory:type:feature", "factory:spec-approved", "factory:human"]),
                       issue(1, labels=["factory:type:feature", "factory:spec-approved", "wayfinder:map"])):
            self.assertFalse(verdict(self.ticket, [parent])["dispatchable"])

    def test_blockers_body_native_union_and_wontfix(self):
        for blocker in (issue(3), issue(3, labels=["factory:wontfix"]),
                        issue(3, state="CLOSED")):
            ticket = self.ticket | {"body": "Parent: #1\nBlocked by: #3"}
            self.assertEqual(verdict(ticket, [self.parent, blocker])["dispatchable"],
                             blocker["state"] == "CLOSED")
        native_open = issue(4)
        ticket = self.ticket | {"body": "Parent: #1\nBlocked by: None", "blocked_by": [4]}
        self.assertFalse(verdict(ticket, [self.parent, native_open])["dispatchable"])

    def test_native_parent_decision_and_stale_claim(self):
        ticket = self.ticket | {"body": "", "parent": 1}
        self.assertTrue(verdict(ticket, [self.parent])["dispatchable"])
        decision = issue(3, "Parent: #1", ["factory:type:decision"])
        self.assertFalse(verdict(self.ticket, [self.parent, decision])["dispatchable"])
        stale = self.ticket | {"comments": ["<!-- factory-claim issue=2 session=x -->"]}
        self.assertFalse(self.check(stale)["dispatchable"])
        unioned = self.ticket | {"blocked_by": [4]}
        self.assertFalse(verdict(unioned, [self.parent, issue(4)])["dispatchable"])

    def test_strict_state_and_lint_rules(self):
        double = self.ticket | {"labels": ["factory:type:implementation", "factory:ready", "factory:running"]}
        self.assertFalse(self.check(double)["dispatchable"])
        issues = [issue(1, labels=["factory:type:feature", "factory:ready", "factory:running"]),
                  issue(2, labels=["factory:type:implementation", "factory:type:decision", "factory:ready"]),
                  issue(3, labels=["factory:type:decision", "factory:ready"])]
        messages = lint(issues)
        self.assertGreaterEqual(len(messages), 4)
        self.assertEqual(lint([issue(4, state="CLOSED", labels=[])]), [])
        self.assertEqual(lint([issue(5, labels=["factory:type:implementation", "factory:ready"])]), [])
        warning = lint([issue(6, "Blocked by: #7", ["factory:type:implementation", "factory:ready"]),
                        issue(7, labels=["factory:type:implementation", "factory:wontfix"])])
        self.assertTrue(any("referenced as a blocker" in message for message in warning))

    def test_gate_exit_codes_and_infrastructure_failure(self):
        namespace = main.__globals__
        with patch.dict(namespace, {"fetch": lambda: [self.parent, self.ticket],
                                   "enrich": lambda *_: None}):
            self.assertEqual(main(["--check", "2"]), 0)
            blocked = self.ticket | {"body": "Parent: #1\nBlocked by: #99"}
            with patch.dict(namespace, {"fetch": lambda: [self.parent, blocked]}):
                self.assertEqual(main(["--check", "2"]), 1)
        with patch.object(frontier["subprocess"], "run", side_effect=FileNotFoundError("gh")):
            self.assertEqual(main(["--check", "2"]), 2)

    def test_reporting_modes_do_not_use_ineligibility_exit_codes(self):
        namespace = main.__globals__
        with patch.dict(namespace, {"fetch": lambda: [self.parent, self.ticket],
                                   "enrich": lambda *_: None}):
            self.assertEqual(main([]), 0)
            self.assertEqual(main(["--json"]), 0)
            self.assertEqual(main(["--lint"]), 0)


if __name__ == "__main__":
    unittest.main()
