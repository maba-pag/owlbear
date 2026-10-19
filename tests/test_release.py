"""The release walk (self-update design section 8; TD-302, TD-306, TD-315) on a disposable repository."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
_SPEC = importlib.util.spec_from_file_location("release", ROOT / ".github/scripts/release.py")
release = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = release  # its dataclass looks itself up there
_SPEC.loader.exec_module(release)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(  # noqa: S603 - fixed git argument vector
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        cwd=cwd, capture_output=True, text=True, check=True,
    )  # fmt: skip
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A clone with v0.1 on its first commit and a floor after it, pushing tags to a bare remote."""
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    git(work, "remote", "add", "origin", str(remote))
    git(work, "commit", "-q", "--allow-empty", "-m", "base")
    git(work, "tag", "-a", "v0.1", "-m", "v0.1")
    git(work, "commit", "-q", "--allow-empty", "-m", "floor")
    monkeypatch.chdir(work)
    return work


def merge(work: Path, name: str) -> str:
    git(work, "switch", "-q", "-c", name)
    git(work, "commit", "-q", "--allow-empty", "-m", name)
    git(work, "switch", "-q", "main")
    git(work, "merge", "-q", "--no-ff", "-m", f"Merge {name}", name)
    return git(work, "rev-parse", "HEAD")


def pr(number: int, *labels: str) -> dict:
    return {"number": number, "title": f"change {number}", "labels": [{"name": n} for n in labels]}


class Fake:
    """GitHub as the walk reads it: each merge's pull request and its CI."""

    def __init__(self) -> None:
        self.prs: dict[str, dict] = {}
        self.runs: dict[str, str] = {}

    def pull(self, sha: str) -> dict | None:
        return self.prs.get(sha)

    def ci(self, sha: str) -> str:
        return self.runs.get(sha, "pending")


def walked(gh: Fake, floor: str) -> list[tuple[str, str, str]]:
    return [(s.sha, s.action, s.tag) for s in release.plan(gh, floor, "HEAD")]


def test_labelled_merges_become_versions_in_order_and_the_walk_waits_at_one_whose_ci_has_not_passed(repo: Path):
    floor, gh = git(repo, "rev-parse", "HEAD"), Fake()
    a, b, c = merge(repo, "a"), merge(repo, "b"), merge(repo, "c")
    git(repo, "commit", "-q", "--allow-empty", "-m", "direct")
    direct = git(repo, "rev-parse", "HEAD")
    d, e, f = merge(repo, "d"), merge(repo, "e"), merge(repo, "f")
    gh.prs = {a: pr(1, "release:minor"), b: pr(2, "dependencies"), c: pr(3, "release:minor", "release:major"),
              e: pr(5, "release:minor"), f: pr(6, "release:minor")}  # fmt: skip
    gh.runs = {a: "success", b: "failure", c: "success", d: "success", f: "success"}  # e's CI still runs
    assert walked(gh, floor) == [
        (a, "tag", "v0.2"), (b, "pass", ""), (c, "tag", "v1.0"), (direct, "pass", ""), (d, "pass", ""), (e, "stop", "")
    ]  # fmt: skip
    for step in release.plan(gh, floor, "HEAD"):
        if step.action == "tag":
            release.tag(step)
    assert [(git(repo, "cat-file", "-t", n), git(repo, "rev-parse", f"{n}^{{commit}}")) for n in ("v1.0", "v1")] == [
        ("tag", c), ("tag", c)
    ]  # fmt: skip
    remote = git(repo, "ls-remote", "--tags", "origin")
    assert all(f"refs/tags/{n}\n" in f"{remote}\n" for n in ("v0.2", "v1.0", "v1"))
    assert walked(gh, floor) == [(direct, "pass", ""), (d, "pass", ""), (e, "stop", "")]  # after the frontier only
    gh.runs[e] = "success"
    assert walked(gh, floor) == [(direct, "pass", ""), (d, "pass", ""), (e, "tag", "v1.1"), (f, "tag", "v1.2")]


def test_a_version_tag_before_the_floor_counts_for_numbering_but_not_as_the_frontier(repo: Path):
    git(repo, "tag", "-a", "v0.9", "-m", "v0.9", "HEAD~1")
    floor, gh = git(repo, "rev-parse", "HEAD"), Fake()
    a = merge(repo, "a")
    gh.prs, gh.runs = {a: pr(1, "release:minor")}, {a: "success"}
    assert walked(gh, floor) == [(a, "tag", "v0.10")]


def test_a_tag_name_taken_meanwhile_fails_the_run_instead_of_moving(repo: Path, capsys: pytest.CaptureFixture[str]):
    floor, gh = git(repo, "rev-parse", "HEAD"), Fake()
    a = merge(repo, "a")
    gh.prs, gh.runs = {a: pr(1, "release:minor")}, {a: "success"}
    (step,) = release.plan(gh, floor, "HEAD")
    git(repo, "tag", "v0.2", "HEAD~1")
    with pytest.raises(subprocess.CalledProcessError):
        release.tag(step)
    assert "already exists" in capsys.readouterr().err
    assert git(repo, "rev-parse", "v0.2^{commit}") == git(repo, "rev-parse", "HEAD~1")


def test_without_the_switch_the_run_only_reports_and_with_it_tags(repo: Path, monkeypatch, tmp_path):
    """TD-315: dry run until the owner sets the repository variable RELEASE_TAGS to on."""
    floor, gh = git(repo, "rev-parse", "HEAD"), Fake()
    a = merge(repo, "a")
    gh.prs, gh.runs = {a: pr(1, "release:minor")}, {a: "success"}
    summary = tmp_path / "summary.md"
    monkeypatch.setattr(release, "FLOOR", floor)
    monkeypatch.setattr(release, "Api", lambda *_a: gh)
    for name, value in (("GITHUB_REPOSITORY", "o/r"), ("GH_TOKEN", "t"), ("GITHUB_STEP_SUMMARY", str(summary))):
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("RELEASE_TAGS", raising=False)
    assert release.main() == 0
    assert (f"would tag {a[:9]} as v0.2: #1 change 1" in summary.read_text(), git(repo, "tag", "-l", "v0.2")) == (
        True, ""
    )  # fmt: skip
    monkeypatch.setenv("RELEASE_TAGS", "on")
    release.main()
    assert (f"tagged {a[:9]} as v0.2" in summary.read_text(), git(repo, "rev-parse", "v0.2^{commit}")) == (True, a)


@pytest.mark.parametrize(
    ("runs", "said"),
    [([], "pending"),
     ([{"id": 1, "path": ".github/workflows/release.yml", "status": "completed", "conclusion": "success"}], "pending"),
     ([{"id": 2, "path": release.CI, "status": "in_progress", "conclusion": None}], "pending"),
     ([{"id": 3, "path": release.CI, "status": "completed", "conclusion": "failure"},
       {"id": 4, "path": release.CI, "status": "completed", "conclusion": "success"}], "success"),
     ([{"id": 6, "path": release.CI, "status": "completed", "conclusion": "failure"},
       {"id": 5, "path": release.CI, "status": "completed", "conclusion": "success"}], "failure"),
     ([{"id": 7, "path": release.CI, "status": "completed", "conclusion": "success"},
       {"id": 8, "path": release.CI, "status": "queued", "conclusion": None}], "pending")],
)  # fmt: skip
def test_the_api_takes_the_pull_request_merged_with_this_commit_and_its_newest_push_ci(monkeypatch, runs, said):
    answers = {
        "https://api.test/repos/o/r/commits/s/pulls": [
            {"number": 6, "merge_commit_sha": "other", "base": {"ref": "main"}},
            {"number": 8, "merge_commit_sha": "s", "base": {"ref": "release"}},
            {"number": 7, "merge_commit_sha": "s", "base": {"ref": "main"}},
        ],
        "https://api.test/repos/o/r/actions/runs?head_sha=s&event=push&branch=main&per_page=100": {
            "workflow_runs": runs
        },
    }
    asked = []

    def urlopen(request, timeout):
        asked.append((request.full_url, request.get_header("Authorization"), timeout))
        return io.BytesIO(json.dumps(answers[request.full_url]).encode())

    monkeypatch.setattr(release.urllib.request, "urlopen", urlopen)
    api = release.Api("o/r", "tok", "https://api.test")
    assert (api.pull("s")["number"], api.ci("s")) == (7, said)
    assert asked[0][1:] == ("Bearer tok", 30)


def test_the_workflow_drains_after_ci_on_main_or_a_label_change_and_runs_mains_code_only():
    document = yaml.safe_load((ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"))
    on = document.get("on", document.get(True))
    assert (on["workflow_run"], on["pull_request_target"]) == (
        {"workflows": ["CI"], "types": ["completed"]}, {"types": ["labeled", "unlabeled"], "branches": ["main"]}
    )  # fmt: skip
    assert (document["permissions"], "concurrency" in document) == ({}, False)
    job = document["jobs"]["release"]
    assert job["concurrency"] == {"group": "release", "cancel-in-progress": False}  # skipped runs never queue
    for needed in (
        "workflow_run.event == 'push'", "workflow_run.head_branch == 'main'", "workflow_run.conclusion == 'success'",
        "pull_request.merged", "label.name, 'release:'",
    ):  # fmt: skip
        assert needed in job["if"]
    assert job["permissions"] == {"contents": "write", "actions": "read", "pull-requests": "read"}
    checkout, walk = job["steps"]
    assert (checkout["with"]["ref"], checkout["with"]["fetch-depth"]) == ("main", 0)  # never a PR's own code
    assert (walk["env"]["RELEASE_TAGS"], walk["run"]) == (
        "${{ vars.RELEASE_TAGS }}",
        "python3 .github/scripts/release.py",
    )
