from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "flaky_issues", Path(__file__).parents[1] / ".github/scripts/flaky_issues.py"
)
flaky_issues = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(flaky_issues)


def test_only_issues_github_reports_open_get_reruns() -> None:
    def fetch(number: int) -> dict[str, object]:
        if number == 4:
            msg = "rate limited"
            raise OSError(msg)
        return {1: {"state": "open"}, 2: {"state": "closed"}, 3: {"state": "open", "pull_request": {}}}[number]

    found, notes = flaky_issues.open_issues([1, 2, 3, 4], fetch)

    assert found == [1]
    assert [note.split()[0] for note in notes] == ["#2", "#3", "#4:"]


def test_an_issue_is_read_through_gh_and_its_error_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if argv[-1].endswith("/2"):
            raise subprocess.CalledProcessError(1, argv, stderr="HTTP 403: Resource not accessible\n")
        return subprocess.CompletedProcess(argv, 0, stdout='{"state": "open"}')

    monkeypatch.setattr(flaky_issues.subprocess, "run", run)

    assert flaky_issues.fetch_issue("owner/repo", 1) == {"state": "open"}
    with pytest.raises(RuntimeError, match="HTTP 403: Resource not accessible"):
        flaky_issues.fetch_issue("owner/repo", 2)
    assert calls[0] == ["gh", "api", "repos/owner/repo/issues/1"]


def test_ci_env_lists_the_open_issues_named_by_tracked_flaky_marks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "test_a.py").write_text(
        "@pytest.mark.flaky(issue=795)\n@pytest.mark.flaky(  # known timeout\n    issue=1_742,  # see the issue\n)\n"
    )
    (tmp_path / "test_b.py").write_text("@pytest.mark.flaky(issue=805)\n")  # untracked
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    subprocess.run(["git", "add", "test_a.py"], cwd=tmp_path, check=True)  # noqa: S607
    env, summary = tmp_path / "env", tmp_path / "summary"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_ENV", str(env))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    asked: list[tuple[str, int]] = []

    def fetch(repository: str, number: int) -> dict[str, object]:
        asked.append((repository, number))
        return {"state": "open" if number == 795 else "closed"}

    monkeypatch.setattr(flaky_issues, "fetch_issue", fetch)

    assert flaky_issues.main() == 0
    assert asked == [("owner/repo", 795), ("owner/repo", 1742)]
    assert env.read_text() == "OWLBEAR_FLAKY_OPEN_ISSUES=795\n"
    assert "open: #795." in summary.read_text()
