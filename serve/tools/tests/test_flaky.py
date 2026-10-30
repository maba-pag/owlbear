from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

pytest_plugins = ["pytester"]

_TESTS = """
import pathlib

import pytest


def _run(name):
    path = pathlib.Path(__file__).parent / f"{name}.runs"
    runs = int(path.read_text()) + 1 if path.exists() else 1
    path.write_text(str(runs))
    return runs


@pytest.mark.flaky(issue=11)
def test_recovers():
    assert _run("recovers") > 1


@pytest.mark.flaky(issue=11)
def test_keeps_failing():
    _run("keeps_failing")
    assert False


@pytest.mark.flaky(issue=12)
def test_closed_issue():
    assert _run("closed_issue") > 1


def test_unmarked():
    assert _run("unmarked") > 1
"""
_ENV = ("OWLBEAR_FLAKY_OPEN_ISSUES", "OWLBEAR_FLAKY_REPORT", "GITHUB_STEP_SUMMARY", "GITHUB_REPOSITORY")


@pytest.fixture
def suite(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    for name in _ENV:  # CI sets these for the outer run; the inner run must see only what each test sets
        monkeypatch.delenv(name, raising=False)
    pytester.makepyfile(test_suite=_TESTS)
    return pytester


def _runs(path: Path) -> dict[str, int]:
    return {
        name: int((path / f"{name}.runs").read_text())
        for name in ("recovers", "keeps_failing", "closed_issue", "unmarked")
    }


def test_ci_reruns_once_only_tests_whose_issue_is_open_and_reports_them(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, summary = suite.path / "out/flaky.json", suite.path / "summary.md"
    monkeypatch.setenv("OWLBEAR_FLAKY_OPEN_ISSUES", "11")
    monkeypatch.setenv("OWLBEAR_FLAKY_REPORT", str(report))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    result = suite.runpytest_subprocess("-p", "owlbear_tools.flaky", "-n", "2")

    assert result.parseoutcomes() == {"passed": 1, "failed": 3, "rerun": 2}
    assert _runs(suite.path) == {"recovers": 2, "keeps_failing": 2, "closed_issue": 1, "unmarked": 1}
    assert json.loads(report.read_text()) == [
        {"nodeid": "test_suite.py::test_keeps_failing", "issue": 11, "reruns": 1, "outcome": "failed"},
        {"nodeid": "test_suite.py::test_recovers", "issue": 11, "reruns": 1, "outcome": "passed"},
    ]
    text = summary.read_text()
    issue = "[#11](https://github.com/owner/repo/issues/11)"
    assert f"| `test_suite.py::test_recovers` | {issue} | passed only on its re-run |" in text
    assert f"| `test_suite.py::test_keeps_failing` | {issue} | failed after its re-run |" in text


def test_marked_tests_run_strict_without_the_ci_issue_list(suite: pytest.Pytester) -> None:
    result = suite.runpytest_subprocess("-p", "owlbear_tools.flaky")

    assert result.parseoutcomes() == {"failed": 4}
    assert _runs(suite.path) == {"recovers": 1, "keeps_failing": 1, "closed_issue": 1, "unmarked": 1}


@pytest.mark.parametrize("mark", ["flaky", "flaky(7)", "flaky(issue='7')", "flaky(issue=7, reruns=3)"])
def test_a_flaky_mark_without_exactly_one_issue_number_stops_the_run(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, mark: str
) -> None:
    monkeypatch.setenv("OWLBEAR_FLAKY_OPEN_ISSUES", "7")
    pytester.makepyfile(f"import pytest\n\n\n@pytest.mark.{mark}\ndef test_marked():\n    pass\n")

    result = pytester.runpytest_subprocess("-p", "owlbear_tools.flaky")

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*a flaky mark must read @pytest.mark.flaky(issue=<open issue number>)*"])
