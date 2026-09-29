"""Hermetic wrapper checks for factory-status failure handling and rendering."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

STATUS = Path(__file__).with_name("factory-status")
FRONTIER_STUB = '''#!/usr/bin/env bash
case "$1" in
  --json)
    case "$JSON_MODE" in
      fail) echo "could not evaluate dispatch eligibility: test failure" >&2; exit 2 ;;
      invalid) echo "not json"; exit 0 ;;
      success) echo '[{"number":8,"title":"Ready work","url":"https://example.invalid/8","dispatchable":false,"reasons":["parent is missing"]}]' ;;
    esac
    ;;
  --lint)
    if [[ "$LINT_MODE" == fail ]]; then
      echo "could not evaluate dispatch eligibility: test failure" >&2
      exit 2
    fi
    echo "#9: exactly one factory:type label is required"
    ;;
esac
'''
GH_STUB = '''#!/usr/bin/env bash
if [[ "$1 $2" == "repo view" ]]; then
  echo "example/project"
elif [[ "$1 $2" == "issue list" ]]; then
  :
else
  exit 1
fi
'''
SECTIONS = (
    "## Ready frontier candidates",
    "## Running",
    "## Human queue",
    "## Review",
    "## Blocked",
)


class FactoryStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scripts = self.root / "scripts"
        self.bin = self.root / "bin"
        self.scripts.mkdir()
        self.bin.mkdir()
        self.status = self.scripts / "factory-status"
        shutil.copy2(STATUS, self.status)
        frontier = self.scripts / "factory-frontier"
        frontier.write_text(FRONTIER_STUB)
        frontier.chmod(0o755)
        gh = self.bin / "gh"
        gh.write_text(GH_STUB)
        gh.chmod(0o755)
        self.env = os.environ | {"PATH": f"{self.bin}:{os.environ['PATH']}"}

    def tearDown(self):
        self.temp.cleanup()

    def report(self, json_mode="success", lint_mode="success", status=None):
        return subprocess.run(
            [str(status or self.status)], cwd=self.root,
            capture_output=True, text=True,
            env=os.environ | self.env | {"JSON_MODE": json_mode, "LINT_MODE": lint_mode},
            check=False,
        )

    def assert_report(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr)
        for section in SECTIONS:
            self.assertIn(section, result.stdout)
        self.assertIn(expected, result.stdout)

    def test_frontier_nonzero_is_reported_without_failing_snapshot(self):
        result = self.report(json_mode="fail")
        self.assert_report(result, "Unable to evaluate (factory-frontier failed)")
        self.assertIn("could not evaluate dispatch eligibility: test failure", result.stderr)

    def test_invalid_json_is_reported_without_traceback(self):
        result = self.report(json_mode="invalid")
        self.assert_report(result, "Unable to evaluate (frontier returned invalid JSON)")
        self.assertNotIn("Traceback", result.stderr)

    def test_lint_nonzero_is_reported_without_failing_snapshot(self):
        result = self.report(lint_mode="fail")
        self.assert_report(result, "Unable to evaluate (factory-frontier lint failed)")

    def test_verdict_and_lint_findings_render(self):
        result = self.report()
        self.assert_report(result, "ineligible: parent is missing")
        self.assertIn("- #9: exactly one factory:type label is required", result.stdout)

    def test_frontier_failure_guard_mutation_is_detected(self):
        original = "if output=$(scripts/factory-frontier --json); then"
        self.assertIn(original, self.status.read_text())
        mutated = self.status.read_text().replace(
            original,
            "output=$(scripts/factory-frontier --json) || exit $?\n  if true; then",
            1,
        )
        self.status.write_text(mutated)
        result = self.report(json_mode="fail")
        with self.assertRaises(AssertionError):
            self.assert_report(result, "Unable to evaluate (factory-frontier failed)")


if __name__ == "__main__":
    unittest.main()
