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
CLAIM = "<!-- factory-claim issue=2 session=ses_test branch=factory/2-test worktree=/tmp/work claimed-at=2026-09-29T12:00:00Z -->"


def issue(number, body="", labels=(), state="OPEN", **extra):
    return {"number": number, "title": f"Issue {number}",
            "url": f"https://example.invalid/issues/{number}", "body": body,
            "labels": list(labels), "state": state, "comments": [],
            "parent": None, "blockedBy": {"nodes": []}, **extra}


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

    def assert_could_not_evaluate(self, issues, fallback=None):
        error = StringIO()
        result = {"number": 2, "title": None, "url": None,
                  "dispatchable": True, "reasons": []}

        def gh(*_args):
            return json.dumps(fallback or self.ticket)

        with patch.dict(main.__globals__, {
                "fetch": lambda: issues,
                "gh": gh,
                "evaluate": lambda *_args: result,
        }), redirect_stderr(error), redirect_stdout(StringIO()):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("could not evaluate", error.getvalue().casefold())
        self.assertNotIn("traceback", error.getvalue().casefold())

    def test_dispatchable_flat_relationships(self):
        self.assertTrue(self.check()["dispatchable"])
        with_blank = self.ticket | {"body": "Parent: #1\n\nBlocked by: None"}
        self.assertTrue(self.check(with_blank)["dispatchable"])

    def test_template_sections_resolve_parent_and_blocker(self):
        blocker = issue(3, state="CLOSED")
        ticket = issue(2, "### Parent feature\n#1\n### Blocked by\n#3",
                       ["factory:type:implementation", "factory:ready"])
        self.assertTrue(verdict(ticket, [self.parent, blocker])["dispatchable"])

    def test_section_heading_names_match_exactly(self):
        extra_text = self.ticket | {"body": "### Parent feature notes\n#1\n### Blocked by\nNone"}
        exact_name = self.ticket | {"body": "### Parent feature\n#1\n### Blocked by\nNone"}
        exact_parent = self.ticket | {"body": "### Parent\n#1\n### Blocked by\nNone"}
        self.assertFalse(verdict(extra_text, [self.parent])["dispatchable"])
        self.assertTrue(verdict(exact_name, [self.parent])["dispatchable"])
        self.assertTrue(verdict(exact_parent, [self.parent])["dispatchable"])

    def test_heading_closing_hashes_require_preceding_whitespace(self):
        cases = (
            ("Parent feature", True, "#1"),
            ("Parent feature ###", True, "#1"),
            ("Parent feature #", True, "#1"),
            ("Parent feature#", False, "#1"),
            ("Parent#", False, "#1"),
            ("Parent ###", True, "#1"),
            ("Blocked by", True, "None"),
            ("Blocked by ###", True, "None"),
            ("Blocked by #", True, "None"),
            ("Blocked by#", False, "None"),
        )
        for heading, accepted, value in cases:
            with self.subTest(heading=heading):
                if heading.startswith("Parent"):
                    body = f"### {heading}\n{value}\n### Blocked by\nNone"
                else:
                    body = f"### Parent feature\n#1\n### {heading}\n{value}"
                result = verdict(self.ticket | {"body": body}, [self.parent])
                self.assertEqual(result["dispatchable"], accepted)
                if not accepted:
                    self.assertTrue(result["reasons"])

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
                "```\nParent: #99\nBlocked by: #98\n```\n")
        self.assertTrue(self.check(self.ticket | {"body": body})["dispatchable"])

    def test_leading_parent_malformed_value_fails_closed(self):
        self.assert_parent_ineligible("Parent: nope\nBlocked by: None")

    def test_missing_blocker_field_fails_closed(self):
        result = verdict(self.ticket | {"body": "Parent: #1"}, [self.parent])
        self.assertFalse(result["dispatchable"])
        self.assertTrue(any("blocker" in reason.casefold() for reason in result["reasons"]))

    def test_duplicate_leading_fields_fail_closed(self):
        cases = (
            ("Parent: #1\nParent: #1\nBlocked by: None", "parent"),
            ("Parent: #1\nBlocked by: None\nBlocked by: #99", "blocker"),
        )
        for body, relationship in cases:
            with self.subTest(relationship=relationship):
                result = verdict(self.ticket | {"body": body}, [self.parent])
                self.assertFalse(result["dispatchable"])
                self.assertTrue(any(relationship in reason.casefold() for reason in result["reasons"]))

    def test_duplicate_section_headings_fail_closed(self):
        ticket = self.ticket | {
            "body": "### Parent feature\n#1\n### Parent\n#1\n### Blocked by\nNone"
        }
        result = verdict(ticket, [self.parent])
        self.assertFalse(result["dispatchable"])
        self.assertTrue(any("parent" in reason.casefold() for reason in result["reasons"]))

    def test_undeclared_or_ambiguous_relationships_never_dispatch(self):
        missing = (
            ("", {}),
            ("Parent: #1", {}),
            ("Blocked by: None", {}),
            ("", {"parent": 1}),
            ("", {"blockedBy": {"nodes": [{"number": 3}]}}),
        )
        for body, native in missing:
            with self.subTest(body=body, native=native):
                result = verdict(self.ticket | {"body": body, **native}, [self.parent, issue(3, state="CLOSED")])
                self.assertFalse(result["dispatchable"])
                self.assertTrue(result["reasons"])

        ambiguous = (
            ("Parent: #1\nParent: #1\nBlocked by: None", "parent"),
            ("Parent: #1\nBlocked by: None\nBlocked by: #99", "blocker"),
            ("### Parent\n#1\n### Parent feature\n#1\n### Blocked by\nNone", "parent"),
            ("### Parent feature\n#1\n### Blocked by\nNone\n### Blocked by\n#99", "blocker"),
            ("Parent: #1\n### Parent feature\n#99\n### Blocked by\nNone", "parent"),
            ("Parent: #1\nBlocked by: None\n### Blocked by\n#99", "blocker"),
        )
        for body, relationship in ambiguous:
            with self.subTest(body=body):
                result = verdict(self.ticket | {"body": body}, [self.parent, issue(99)])
                self.assertFalse(result["dispatchable"])
                self.assertTrue(any(relationship in reason.casefold() for reason in result["reasons"]))

        valid_native = self.ticket | {
            "body": "", "parent": 1, "blockedBy": {"nodes": [{"number": 3}]}
        }
        self.assertTrue(verdict(valid_native, [self.parent, issue(3, state="CLOSED")])["dispatchable"])
        self.assertTrue(self.check()["dispatchable"])

    def test_multiple_type_labels_never_dispatch(self):
        for extra in ("factory:type:other", "factory:type:feature", "factory:type:decision"):
            with self.subTest(extra_type=extra):
                ticket = self.ticket | {"labels": ["factory:type:implementation", extra, "factory:ready"]}
                result = verdict(ticket, [self.parent])
                self.assertFalse(result["dispatchable"])
                self.assertTrue(result["reasons"])
        no_type = self.ticket | {"labels": ["factory:ready"]}
        self.assertFalse(verdict(no_type, [self.parent])["dispatchable"])

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
        ticket = self.ticket | {"body": "Blocked by: None", "parent": 1}
        self.assertTrue(verdict(ticket, [self.parent])["dispatchable"])
        native_only = self.ticket | {
            "body": "", "parent": {"number": 1}, "blockedBy": {"nodes": [{"number": 4}]}
        }
        self.assertTrue(verdict(native_only, [self.parent, issue(4, state="CLOSED")])["dispatchable"])
        decision = issue(3, "Parent: #1", ["factory:type:decision"])
        self.assertFalse(verdict(self.ticket, [self.parent, decision])["dispatchable"])
        stale = self.ticket | {"comments": [{"body": CLAIM}]}
        self.assertFalse(self.check(stale)["dispatchable"])
        mentioned = self.ticket | {"comments": [{"body": "The factory-claim marker is discussed here, not posted."}]}
        self.assertTrue(self.check(mentioned)["dispatchable"])
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
        self.assertEqual(calls[0][-1], frontier["ISSUE_FIELDS"])

    def test_truncated_bulk_view_cannot_be_evaluated_in_any_mode(self):
        full_view = [issue(number) for number in range(1, frontier["ISSUE_LIMIT"] + 1)]
        with patch.dict(main.__globals__, {"fetch": lambda: full_view}):
            error = StringIO()
            with redirect_stderr(error):
                self.assertEqual(main(["--check", "2"]), 2)
            self.assertIn("could not evaluate", error.getvalue())
            for arguments in ([], ["--json"], ["--lint"]):
                with self.subTest(arguments=arguments):
                    self.assertEqual(run_main(arguments), 2)

    def test_required_issue_fields_are_validated_before_verdict(self):
        missing_body = self.ticket | {
            "parent": 1, "blockedBy": {"nodes": [{"number": 3}]},
        }
        del missing_body["body"]
        wrong_title_type = self.ticket | {"title": 2}
        for bad_ticket, records in (
                (missing_body, [self.parent, missing_body, issue(3, state="CLOSED")]),
                (wrong_title_type, [self.parent, wrong_title_type])):
            with self.subTest(ticket=bad_ticket):
                error = StringIO()
                with patch.dict(main.__globals__, {"fetch": lambda: records}), \
                     redirect_stderr(error), redirect_stdout(StringIO()):
                    self.assertEqual(main(["--check", "2"]), 2)
                self.assertIn("could not evaluate", error.getvalue().casefold())
                self.assertNotIn("traceback", error.getvalue().casefold())

    def test_fallback_comments_still_detect_a_stale_claim(self):
        target = self.ticket | {
            "url": "https://example.invalid/issues/2",
            "comments": [{"body": CLAIM}],
        }

        def gh(*_args):
            return json.dumps(target)

        output = StringIO()
        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stdout(output):
            self.assertEqual(main(["--check", "2"]), 1)
        self.assertIn("claim", output.getvalue().casefold())

    def test_capped_comments_are_completed_before_stale_claim_verdict(self):
        limit = frontier["COMMENT_LIMIT"]
        ticket = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}
        full_history = ticket["comments"] + [{"body": CLAIM}]
        pages = [full_history[index:index + 30] for index in range(0, len(full_history), 30)]
        calls = []

        def gh(*args):
            calls.append(args)
            return json.dumps(pages)

        with patch.dict(main.__globals__, {"gh": gh}):
            result = frontier["evaluate"](ticket, [self.parent, ticket])
        self.assertFalse(result["dispatchable"])
        self.assertTrue(any("claim" in reason.casefold() for reason in result["reasons"]))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ("api", "--paginate", "--slurp"))
        self.assertEqual(calls[0][-1], "repos/{owner}/{repo}/issues/2/comments")

    def test_capped_comments_without_claim_remain_dispatchable(self):
        limit = frontier["COMMENT_LIMIT"]
        ticket = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}

        def gh(*_args):
            return json.dumps([[{"body": f"discussion {index}"} for index in range(limit)]])

        with patch.dict(main.__globals__, {"gh": gh}):
            result = frontier["evaluate"](ticket, [self.parent, ticket])
        self.assertTrue(result["dispatchable"])

    def test_comment_followup_is_skipped_below_cap(self):
        ticket = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(frontier["COMMENT_LIMIT"] - 1)]}
        calls = []

        def gh(*args):
            calls.append(args)
            raise AssertionError("uncapped comments must not trigger another request")

        with patch.dict(main.__globals__, {"gh": gh}):
            result = frontier["evaluate"](ticket, [self.parent, ticket])
        self.assertTrue(result["dispatchable"])
        self.assertEqual(calls, [])

    def test_capped_fallback_comments_complete_stale_claim_history(self):
        limit = frontier["COMMENT_LIMIT"]
        target = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}
        full_history = target["comments"] + [{"body": CLAIM}]
        calls = []

        def gh(*args):
            calls.append(args)
            if args[0] == "issue":
                return json.dumps(target)
            return json.dumps([full_history[index:index + 30] for index in range(0, len(full_history), 30)])

        output = StringIO()
        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stdout(output):
            self.assertEqual(main(["--check", "2"]), 1)
        self.assertIn("claim", output.getvalue().casefold())
        self.assertEqual([call[0] for call in calls], ["issue", "api"])

    def test_malformed_paginated_comments_fail_closed(self):
        limit = frontier["COMMENT_LIMIT"]
        target = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}
        for response in ({}, ["x"], [None], [["not a comment"]], [[{"body": None}]], None):
            with self.subTest(response=response):
                error = StringIO()

                def gh(*args):
                    return json.dumps(target if args[0] == "issue" else response)

                with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stderr(error):
                    self.assertEqual(main(["--check", "2"]), 2)
                self.assertIn("could not evaluate", error.getvalue().casefold())

    def test_short_paginated_history_fails_closed(self):
        limit = frontier["COMMENT_LIMIT"]
        target = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}
        short_pages = [[{"body": f"discussion {index}"} for index in range(limit - 1)]]
        error = StringIO()

        def gh(*args):
            return json.dumps(target if args[0] == "issue" else short_pages)

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stderr(error):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("shorter than the capped list", error.getvalue().casefold())

    def test_malformed_capped_comment_field_fails_closed(self):
        target = self.ticket | {"comments": {str(index): "not a comment object" for index in range(frontier["COMMENT_LIMIT"])}}
        error = StringIO()

        def gh(*args):
            return json.dumps(target)

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stderr(error):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("issue record has invalid comments", error.getvalue().casefold())

    def test_malformed_bulk_issue_records_fail_closed(self):
        missing_comments = self.ticket.copy()
        del missing_comments["comments"]
        malformed = (
            missing_comments,
            self.ticket | {"comments": None},
            self.ticket | {"comments": "not a list"},
            self.ticket | {"comments": {"body": CLAIM}},
            self.ticket | {"comments": [None]},
            self.ticket | {"comments": [{"body": None}]},
            self.ticket | {"number": "2"},
            self.ticket | {"state": None},
            self.ticket | {"labels": None},
            self.ticket | {"body": 2},
        )
        for bad_issue in malformed:
            with self.subTest(record=bad_issue):
                error = StringIO()

                def gh(*_args):
                    return json.dumps(bad_issue)

                with patch.dict(main.__globals__, {"fetch": lambda: [self.parent, bad_issue]}), \
                     patch.dict(main.__globals__, {"gh": gh}), \
                     redirect_stderr(error), redirect_stdout(StringIO()):
                    self.assertEqual(main(["--check", "2"]), 2)
                self.assertIn("could not evaluate", error.getvalue().casefold())
                self.assertNotIn("traceback", error.getvalue().casefold())
                if bad_issue is missing_comments:
                    self.assertIn("issue record is missing a required field", error.getvalue().casefold())

    def test_empty_comment_history_is_a_valid_dispatchable_record(self):
        output = StringIO()

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent, self.ticket]}), \
             redirect_stdout(output):
            self.assertEqual(main(["--check", "2"]), 0)
        self.assertEqual(output.getvalue().strip(), "dispatchable")

    def test_malformed_individually_fetched_records_fail_closed(self):
        absent_batch_target = self.ticket | {
            "parent": 1, "blockedBy": {"nodes": [{"number": 3}]},
        }
        del absent_batch_target["body"]
        error = StringIO()

        def gh(*_args):
            return json.dumps(absent_batch_target)

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent, issue(3, state="CLOSED")], "gh": gh}), \
             redirect_stderr(error), redirect_stdout(StringIO()):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("could not evaluate", error.getvalue().casefold())
        self.assertIn("issue record is missing a required field", error.getvalue().casefold())

        ticket = self.ticket | {"body": "Parent: #1\nBlocked by: #3"}
        absent_blocker_comments = issue(3, state="CLOSED")
        del absent_blocker_comments["comments"]
        error = StringIO()

        def fetch_blocker(*_args):
            return json.dumps(absent_blocker_comments)

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent, ticket], "gh": fetch_blocker}), \
             redirect_stderr(error), redirect_stdout(StringIO()):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("could not evaluate", error.getvalue().casefold())

    def test_issue_record_boundary_guards_fail_closed(self):
        # These fixtures isolate validation: if a malformed record passes its
        # boundary, the mocked evaluator returns a dispatchable result.
        for value in (None, 7):
            with self.subTest(record=value):
                self.assert_could_not_evaluate([value])

        missing = self.ticket.copy()
        del missing["body"]
        self.assert_could_not_evaluate([missing])

        for number in (False, 0, -1, "2"):
            with self.subTest(number=number):
                bad = self.ticket | {"number": number}
                self.assert_could_not_evaluate([bad], fallback=bad)

        for changes in ({"title": 2}, {"url": None}):
            with self.subTest(changes=changes):
                self.assert_could_not_evaluate([self.ticket | changes])

        self.assert_could_not_evaluate([self.ticket | {"body": 2}])
        for state in (None, "MERGED"):
            with self.subTest(state=state):
                self.assert_could_not_evaluate([self.ticket | {"state": state}])

        for labels in (("factory:type:implementation", "factory:ready"),
                       ["factory:type:implementation", 2],
                       ["factory:type:implementation", {"name": None}]):
            with self.subTest(labels=labels):
                self.assert_could_not_evaluate([self.ticket | {"labels": labels}])

        for comments in (({"body": "discussion"},), [None], [{"body": None}]):
            with self.subTest(comments=comments):
                self.assert_could_not_evaluate([self.ticket | {"comments": comments}])

        for parent in (True, "1", {"number": "1"}):
            with self.subTest(parent=parent):
                self.assert_could_not_evaluate([self.ticket | {"parent": parent}])

        for blocked_by in ([3], {}, {"nodes": (3,)}):
            with self.subTest(blockedBy=blocked_by):
                self.assert_could_not_evaluate([self.ticket | {"blockedBy": blocked_by}])

        for node in (3, {}, {"number": "3"}, {"number": 0}, {"number": True}):
            with self.subTest(blockedByNode=node):
                self.assert_could_not_evaluate([
                    self.ticket | {"blockedBy": {"nodes": [node]}}
                ])

    def test_bulk_issue_listing_must_be_a_list(self):
        for bulk in (None, 7):
            with self.subTest(bulk=bulk):
                self.assert_could_not_evaluate(bulk)

    def test_failed_paginated_comment_request_fails_closed(self):
        limit = frontier["COMMENT_LIMIT"]
        target = self.ticket | {"comments": [{"body": f"discussion {index}"} for index in range(limit)]}
        error = StringIO()

        def gh(*args):
            if args[0] == "issue":
                return json.dumps(target)
            raise frontier["subprocess"].CalledProcessError(1, args, stderr="HTTP 403 rate limit")

        with patch.dict(main.__globals__, {"fetch": lambda: [self.parent], "gh": gh}), redirect_stderr(error):
            self.assertEqual(main(["--check", "2"]), 2)
        self.assertIn("could not evaluate", error.getvalue().casefold())

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
