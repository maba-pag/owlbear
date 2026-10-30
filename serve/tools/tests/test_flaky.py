from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

pytest_plugins = ["pytester"]

_TESTS = """
import os
import pathlib

import pytest


def _run(name):
    path = pathlib.Path(__file__).parent / f"{name}.runs"
    runs = int(path.read_text()) + 1 if path.exists() else 1
    path.write_text(str(runs))
    return runs


@pytest.fixture
def breaks_teardown_once():
    yield
    assert (pathlib.Path(__file__).parent / "teardown.runs").read_text() != "1", "teardown broke"


@pytest.mark.flaky(issue=11)
def test_recovers():
    assert _run("recovers") > 1, "first attempt broke"


@pytest.mark.flaky(issue=11)
def test_keeps_failing():
    _run("keeps_failing")
    assert False


@pytest.mark.flaky(issue=11)
def test_crashes_once():
    if _run("crashes") == 1:
        os._exit(1)


@pytest.mark.flaky(issue=11)
def test_skips_on_rerun():
    if _run("skips") > 1:
        pytest.skip("not today")
    assert False


@pytest.mark.flaky(issue=11)
def test_fails_in_call_and_teardown(breaks_teardown_once):
    assert _run("teardown") > 1


@pytest.mark.flaky(issue=12)
def test_closed_issue():
    assert _run("closed_issue") > 1


def test_unmarked():
    assert _run("unmarked") > 1
"""
_NAMES = ("recovers", "keeps_failing", "crashes", "skips", "teardown", "closed_issue", "unmarked")
_ENV = ("OWLBEAR_FLAKY_OPEN_ISSUES", "OWLBEAR_FLAKY_REPORT", "GITHUB_STEP_SUMMARY", "GITHUB_REPOSITORY")


@pytest.fixture
def suite(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> pytest.Pytester:
    for name in _ENV:  # CI sets these for the outer run; the inner run must see only what each test sets
        monkeypatch.delenv(name, raising=False)
    pytester.makepyfile(test_suite=_TESTS)
    return pytester


def _runs(path: Path) -> dict[str, int]:
    return {name: int((path / f"{name}.runs").read_text()) for name in _NAMES}


def test_ci_reruns_once_only_tests_whose_issue_is_open_and_reports_every_attempt(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, summary = suite.path / "out/flaky.json", suite.path / "summary.md"
    monkeypatch.setenv("OWLBEAR_FLAKY_OPEN_ISSUES", "11")
    monkeypatch.setenv("OWLBEAR_FLAKY_REPORT", str(report))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    suite.runpytest_subprocess("-p", "owlbear_tools.flaky", "-n", "2", "--dist", "worksteal")

    assert _runs(suite.path) == {name: 1 if name in {"closed_issue", "unmarked"} else 2 for name in _NAMES}
    rows = {row["nodeid"].split("::")[1]: row for row in json.loads(report.read_text())}
    assert {name: (row["issue"], row["reruns"], row["outcome"]) for name, row in rows.items()} == {
        "test_recovers": (11, 1, "passed"),
        "test_keeps_failing": (11, 1, "failed"),
        "test_crashes_once": (11, 1, "passed"),
        "test_skips_on_rerun": (11, 1, "skipped"),
        "test_fails_in_call_and_teardown": (11, 1, "passed"),
    }
    first = rows["test_recovers"]["attempts"][0]
    assert (first["attempt"], first["outcome"], first["phase"]) == (1, "rerun", "call")
    assert "first attempt broke" in first["message"]
    text = summary.read_text()
    issue = "[#11](https://github.com/owner/repo/issues/11)"
    assert f"| `test_suite.py::test_recovers` | {issue} | passed only on its re-run | call: " in text
    assert f"| `test_suite.py::test_keeps_failing` | {issue} | failed after its re-run |" in text


def test_marked_tests_run_strict_without_the_ci_issue_list(suite: pytest.Pytester) -> None:
    suite.runpytest_subprocess("-p", "owlbear_tools.flaky", "-n", "2")

    assert _runs(suite.path) == dict.fromkeys(_NAMES, 1)


@pytest.mark.parametrize(
    ("module", "function"),
    [
        ("", "flaky"),
        ("", "flaky(7)"),
        ("", "flaky(issue='7')"),
        ("", "flaky(issue=7, reruns=3)"),
        ("pytestmark = pytest.mark.flaky(reruns=3)", "flaky(issue=7)"),
    ],
)
def test_a_flaky_mark_without_exactly_one_issue_number_stops_the_run(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, module: str, function: str
) -> None:
    monkeypatch.setenv("OWLBEAR_FLAKY_OPEN_ISSUES", "7")
    pytester.makepyfile(f"import pytest\n\n{module}\n\n@pytest.mark.{function}\ndef test_marked():\n    pass\n")

    result = pytester.runpytest_subprocess("-p", "owlbear_tools.flaky")

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*a flaky mark must read @pytest.mark.flaky(issue=<open issue number>)*"])
