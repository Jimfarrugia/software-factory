"""Hermetic tests for the dispatch eligibility decision."""
import json
import runpy
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

frontier = runpy.run_path(str(Path(__file__).with_name("factory-frontier")))
verdict = frontier["dispatch_verdict"]
lint = frontier["lint_issues"]
main = frontier["main"]


def issue(number, body="", labels=(), state="OPEN", **extra):
    return {"number": number, "body": body, "labels": list(labels), "state": state,
            "title": f"Issue {number}", **extra}


def run_main(arguments):
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return main(arguments)


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.parent = issue(1, labels=["factory:type:feature", "factory:spec-approved"])
        self.ticket = issue(2, "Parent: #1\nBlocked by: None",
                            ["factory:type:implementation", "factory:ready"])

    def check(self, ticket=None, others=()):
        return verdict(ticket or self.ticket, [self.parent, *(others)])

    def test_dispatchable_flat_relationships(self):
        self.assertTrue(self.check()["dispatchable"])
        with_blank = self.ticket | {"body": "Parent: #1\n\nBlocked by: None"}
        self.assertTrue(self.check(with_blank)["dispatchable"])

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

    def assert_parent_ineligible(self, body):
        result = verdict(self.ticket | {"body": body}, [self.parent])
        self.assertFalse(result["dispatchable"])
        self.assertTrue(any("parent" in reason.casefold() for reason in result["reasons"]))

    def test_only_leading_column_zero_flat_fields_resolve(self):
        for body in (
            "    Parent: #1\nBlocked by: None",
            "Description first.\nParent: #1\nBlocked by: None",
            "## Introduction\nParent: #1\nBlocked by: None",
            "```text\nParent: #1\nBlocked by: None\n```",
            "See docs; the convention is Parent: #1 for children.\n",
        ):
            with self.subTest(body=body):
                self.assert_parent_ineligible(body)

    def test_leading_flat_fields_win_over_later_example_content(self):
        body = ("Parent: #1\nBlocked by: None\n\nDescription.\n\n"
                "```\nParent: #99\nBlocked by: #98\n```\n### Parent feature\n#97\n")
        self.assertTrue(self.check(self.ticket | {"body": body})["dispatchable"])

    def test_leading_parent_malformed_value_fails_closed(self):
        self.assert_parent_ineligible("Parent: nope\nBlocked by: None")

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
        native_warning = lint([
            issue(8, labels=["factory:type:implementation", "factory:ready"], blockedBy={"nodes": [{"number": 9}]}),
            issue(9, labels=["factory:type:implementation", "factory:wontfix"]),
        ])
        self.assertTrue(any("referenced as a blocker" in message for message in native_warning))

    def test_bulk_native_shape_and_verdict_metadata(self):
        ticket = self.ticket | {
            "parent": {"number": 1}, "blockedBy": {"nodes": []},
            "title": "Ready issue", "url": "https://example.invalid/issues/2",
        }
        result = verdict(ticket, [self.parent, ticket])
        self.assertTrue(result["dispatchable"])
        self.assertEqual(result["title"], "Ready issue")
        self.assertEqual(result["url"], "https://example.invalid/issues/2")

    def test_one_bulk_invocation_for_candidate_in_bare_mode(self):
        data = [
            self.parent,
            self.ticket,
        ]
        calls = []

        def run(command, **_kwargs):
            calls.append(command)
            return type("Result", (), {"stdout": json.dumps(data)})()

        with patch.object(frontier["subprocess"], "run", side_effect=run):
            self.assertEqual(run_main([]), 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ["gh", "issue", "list"])
        self.assertEqual(calls[0][-1], "number,title,url,body,labels,state,blockedBy,parent,comments")

    def test_only_missing_relationships_use_individual_issue_reads(self):
        ticket = self.ticket | {"body": "Parent: #1\nBlocked by: #3"}
        calls = []

        def run(command, **_kwargs):
            calls.append(command)
            return type("Result", (), {"stdout": json.dumps(issue(3, state="CLOSED"))})()

        with patch.object(frontier["subprocess"], "run", side_effect=run):
            frontier["enrich"](ticket, [self.parent, ticket])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:4], ["gh", "issue", "view", "3"])

    def test_json_command_fetches_metadata_for_issue_absent_from_batch(self):
        target = self.ticket | {"url": "https://example.invalid/issues/2"}
        calls = []

        def gh(*args):
            calls.append(args)
            self.assertEqual(args[:3], ("issue", "view", "2"))
            return json.dumps(target)

        output = StringIO()
        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stdout(output):
            self.assertEqual(main(["--json", "2"]), 0)
        result, = json.loads(output.getvalue())
        self.assertEqual(result["url"], target["url"])
        self.assertEqual(result["title"], target["title"])
        self.assertIn("title,url", calls[0][-1])

    def test_gate_exit_codes_and_infrastructure_failure(self):
        namespace = main.__globals__
        with patch.dict(namespace, {"fetch": lambda: [self.parent, self.ticket],
                                   "enrich": lambda *_: None}):
            self.assertEqual(run_main(["--check", "2"]), 0)
            blocked = self.ticket | {"body": "Parent: #1\nBlocked by: #99"}
            with patch.dict(namespace, {"fetch": lambda: [self.parent, blocked]}):
                self.assertEqual(run_main(["--check", "2"]), 1)
        with patch.object(frontier["subprocess"], "run", side_effect=FileNotFoundError("gh")):
            self.assertEqual(run_main(["--check", "2"]), 2)

    def test_reporting_modes_do_not_use_ineligibility_exit_codes(self):
        namespace = main.__globals__
        with patch.dict(namespace, {"fetch": lambda: [self.parent, self.ticket],
                                   "enrich": lambda *_: None}):
            self.assertEqual(run_main([]), 0)
            self.assertEqual(run_main(["--json"]), 0)
            self.assertEqual(run_main(["--lint"]), 0)


if __name__ == "__main__":
    unittest.main()
