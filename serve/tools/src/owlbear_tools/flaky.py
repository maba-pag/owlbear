"""Pytest plugin for OwlBear's flaky-test policy.

A test marked ``@pytest.mark.flaky(issue=N)`` is re-run once by pytest-rerunfailures only when
``OWLBEAR_FLAKY_OPEN_ISSUES`` (set by CI from GitHub) lists issue N as open; everywhere else it runs
strict. When ``OWLBEAR_FLAKY_REPORT`` names a file, the run writes every re-run test there as JSON and,
under GitHub Actions, lists them in the job summary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

OPEN_ISSUES_ENV = "OWLBEAR_FLAKY_OPEN_ISSUES"
REPORT_ENV = "OWLBEAR_FLAKY_REPORT"
_ISSUE_PROPERTY = "flaky_issue"
_MARK_FORM = "@pytest.mark.flaky(issue=<open issue number>)"


def open_issues() -> frozenset[int]:
    """Return the issue numbers CI found open; empty outside CI, so every marked test runs strict."""
    return frozenset(int(word) for word in os.environ.get(OPEN_ISSUES_ENV, "").split() if word.isdigit())


def _issue(item: pytest.Item, mark: pytest.Mark) -> int:
    issue = mark.kwargs.get("issue")
    if mark.args or set(mark.kwargs) != {"issue"} or type(issue) is not int or issue <= 0:
        msg = f"{item.nodeid}: a flaky mark must read {_MARK_FORM}, not {mark}"
        raise pytest.UsageError(msg)
    return issue


def pytest_configure(config: pytest.Config) -> None:
    """Describe the mark and start collecting re-run reports."""
    config.addinivalue_line("markers", f"flaky: {_MARK_FORM}; re-run once in CI while the issue is open")
    config.pluginmanager.register(_Reruns(), "owlbear-flaky-reruns")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Check each flaky mark and give pytest-rerunfailures one re-run only where the issue is open."""
    eligible = open_issues()
    for item in items:
        mark = item.get_closest_marker("flaky")
        if mark is None:
            continue
        issue = _issue(item, mark)
        item.user_properties.append((_ISSUE_PROPERTY, issue))
        # pytest-rerunfailures reads the closest flaky mark; reruns=None makes it leave the test alone.
        item.add_marker(pytest.mark.flaky(reruns=1 if issue in eligible else None), append=False)


class _Reruns:
    """Collects re-run reports; under xdist the controller sees every worker's reports."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        issue = dict(report.user_properties).get(_ISSUE_PROPERTY)
        if issue is None:
            return
        if report.outcome == "rerun":
            row = self.rows.setdefault(report.nodeid, {"issue": issue, "reruns": 0, "outcome": "passed"})
            row["reruns"] = int(row["reruns"]) + 1
        elif report.failed and report.nodeid in self.rows:
            self.rows[report.nodeid]["outcome"] = "failed"

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        target = os.environ.get(REPORT_ENV)
        if not target or hasattr(session.config, "workerinput"):
            return
        rows = [{"nodeid": nodeid, **row} for nodeid, row in sorted(self.rows.items())]
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            lines = summary_lines(rows, os.environ.get("GITHUB_REPOSITORY", ""))
            with Path(summary).open("a", encoding="utf-8") as out:
                out.writelines(f"{line}\n" for line in lines)


def summary_lines(rows: list[dict[str, object]], repository: str) -> Iterator[str]:
    """Markdown for the job summary: each re-run test, its issue and how it ended."""
    if not rows:
        yield "No test needed a re-run."
        return
    yield "### Tests re-run as flaky"
    yield ""
    yield "| Test | Issue | Result |"
    yield "| --- | --- | --- |"
    for row in rows:
        issue = row["issue"]
        link = f"[#{issue}](https://github.com/{repository}/issues/{issue})" if repository else f"#{issue}"
        result = "passed only on its re-run" if row["outcome"] == "passed" else "failed after its re-run"
        yield f"| `{row['nodeid']}` | {link} | {result} |"
