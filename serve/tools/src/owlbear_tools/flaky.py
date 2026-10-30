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
    """Check every flaky mark and give pytest-rerunfailures one re-run only where the issue is open."""
    eligible = open_issues()
    for item in items:
        marks = list(item.iter_markers("flaky"))
        if not marks:
            continue
        issue = _issue(item, marks[0])
        for mark in marks[1:]:
            _issue(item, mark)
        item.user_properties.append((_ISSUE_PROPERTY, issue))
        # pytest-rerunfailures reads the closest flaky mark; reruns=None makes it leave the test alone.
        item.add_marker(pytest.mark.flaky(reruns=1 if issue in eligible else None), append=False)


_PRECEDENCE = ("rerun", "failed", "skipped", "passed")


def _message(report: pytest.TestReport) -> str:
    crash = getattr(report.longrepr, "reprcrash", None)
    if crash is not None:
        text = str(crash.message)
    elif isinstance(report.longrepr, tuple):
        text = str(report.longrepr[-1])
    else:
        lines = report.longreprtext.strip().splitlines()
        text = lines[-1] if lines else ""
    return text[:1000]


class _Reruns:
    """Collects every attempt of a re-run test; under xdist the controller sees every worker's reports.

    A worker crash reaches the controller as a report without the test's properties, so attempts are kept by node
    id and the issue is taken from whichever report carries it.
    """

    def __init__(self) -> None:
        self.issues: dict[str, int] = {}
        self.attempts: dict[str, dict[int, dict[str, object]]] = {}
        self.rerun: set[str] = set()

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        issue = dict(report.user_properties).get(_ISSUE_PROPERTY)
        if issue is not None:
            self.issues[report.nodeid] = issue
        elif report.nodeid not in self.issues and report.outcome != "rerun":
            return
        if report.outcome == "rerun":
            self.rerun.add(report.nodeid)
        index = int(getattr(report, "rerun", 0) or 0)
        attempt = self.attempts.setdefault(report.nodeid, {}).setdefault(
            index, {"attempt": index + 1, "outcome": "passed", "phase": None, "duration": 0.0, "message": ""}
        )
        attempt["duration"] = round(float(attempt["duration"]) + report.duration, 3)
        if _PRECEDENCE.index(report.outcome) < _PRECEDENCE.index(str(attempt["outcome"])):
            attempt.update(outcome=report.outcome, phase=report.when, message=_message(report))

    def rows(self) -> list[dict[str, object]]:
        """One row per re-run test: its issue, every attempt, and how its last attempt ended."""
        rows = []
        for nodeid in sorted(self.rerun):
            attempts = [self.attempts[nodeid][index] for index in sorted(self.attempts[nodeid])]
            last = str(attempts[-1]["outcome"])
            rows.append(
                {
                    "nodeid": nodeid,
                    "issue": self.issues.get(nodeid),
                    "reruns": sum(attempt["outcome"] == "rerun" for attempt in attempts),
                    "outcome": "incomplete" if last == "rerun" else last,
                    "attempts": attempts,
                }
            )
        return rows

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        target = os.environ.get(REPORT_ENV)
        if not target or hasattr(session.config, "workerinput"):
            return
        rows = self.rows()
        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            lines = summary_lines(rows, os.environ.get("GITHUB_REPOSITORY", ""))
            with Path(summary).open("a", encoding="utf-8") as out:
                out.writelines(f"{line}\n" for line in lines)


_RESULTS = {
    "passed": "passed only on its re-run",
    "failed": "failed after its re-run",
    "skipped": "skipped on its re-run",
    "incomplete": "its re-run never finished",
}


def summary_lines(rows: list[dict[str, object]], repository: str) -> Iterator[str]:
    """Markdown for the job summary: each re-run test, its issue, how it ended and its first failure."""
    if not rows:
        yield "No test needed a re-run."
        return
    yield "### Tests re-run as flaky"
    yield ""
    yield "| Test | Issue | Result | First failure |"
    yield "| --- | --- | --- | --- |"
    for row in rows:
        issue = row["issue"]
        if issue is None:
            link = "unknown"
        elif repository:
            link = f"[#{issue}](https://github.com/{repository}/issues/{issue})"
        else:
            link = f"#{issue}"
        first = row["attempts"][0]
        failure = f"{first['phase']}: {first['message']}".replace("|", "\\|").replace("\n", " ")
        yield f"| `{row['nodeid']}` | {link} | {_RESULTS[str(row['outcome'])]} | {failure} |"
