"""Cross-process identity allocation shared by shaping and test-review creation."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_delivery_next.change_flow import brief_tools, worktree
from owlbear_delivery_next.state_store import briefs, identities
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import curation

if TYPE_CHECKING:
    from pathlib import Path

NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)
_CHILD = """
import json
import sys
import traceback
from datetime import datetime, UTC
from pathlib import Path
from owlbear_delivery_next.change_flow import brief_tools, worktree
from owlbear_delivery_next.state_store import briefs
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import curation
action, repo, arg = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
try:
    store = Store.open(repo)
    if action == "curation":
        worktree.data_root = lambda: Path(arg)
    print("ready", flush=True)
    sys.stdin.readline()
    if action == "host":
        draft = brief_tools.BriefDraft(
            title=arg, outcome="The page finds people by name.", criteria=["Searching Ada lists Ada"],
            scope=["web"], ui=False, visual=[], steps=[],
        )
        code, body = briefs.save_brief(store, draft.model_dump())
    else:
        c = curation.start(store, repo, ["web"], datetime.now(UTC))
        code, body = 200, {"change": c.handle, "slug": c.slug}
    print(json.dumps([code, body]), flush=True)
except Exception:
    traceback.print_exc()
    sys.exit(1)
"""


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@t"]
    return subprocess.run(  # noqa: S603 - fixed Git executable and synthetic arguments
        [worktree.GIT, *who, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    files = {
        "pyproject.toml": "", "src/app.py": "x = 1\n", "tests/test_a.py": "a\n" * 3, "tests/data.json": "{}\n",
        "tests/helpers.py": "h\n", "web/package.json": "{}", "web/src/b.test.ts": "b\n" * 2, "web/src/b.ts": "b\n",
    }  # fmt: skip
    for name, text in files.items():
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text(text)
    git(tmp_path, "init", "-q", "-b", "main", str(work))
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    return work


def brief(title: str) -> dict[str, Any]:
    return brief_tools.BriefDraft(
        title=title, outcome="The page finds people by name.", criteria=["Searching Ada lists Ada"], scope=["web"],
        ui=False, visual=[], steps=[],
    ).model_dump()  # fmt: skip


def _spawn(action: str, repo: Path, arg: str) -> subprocess.Popen[str]:
    return subprocess.Popen(  # noqa: S603 - this interpreter runs the fixed synthetic child script
        [sys.executable, "-c", _CHILD, action, str(repo), arg],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _together(*children: subprocess.Popen[str]) -> list[Any]:
    try:
        for child in children:
            assert child.stdout is not None
            ready = child.stdout.readline()
            assert ready.strip() == "ready", child.communicate()[1]
        for child in children:
            assert child.stdin is not None
            child.stdin.write("go\n")
            child.stdin.flush()
        answers = []
        for child in children:
            out, err = child.communicate(timeout=20)
            assert child.returncode == 0, err
            answers.append(json.loads(out))
        return answers
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait()


def test_same_title_creates_in_threads_keep_both_under_distinct_handles(repo):
    store = Store.open(repo)
    store.issued()
    barrier = threading.Barrier(2, timeout=10)

    def create() -> tuple[int, dict[str, Any]]:
        barrier.wait()
        return briefs.save_brief(store, brief("Same title"))

    with ThreadPoolExecutor(max_workers=2) as workers:
        pending = [workers.submit(create) for _ in range(2)]
        results = [future.result(timeout=15) for future in pending]
    assert sorted(code for code, _ in results) == [200, 200]
    assert sorted(body["slug"] for _, body in results) == ["same-title", "same-title-2"]
    assert sorted(body["change"] for _, body in results) == ["c1", "c2"]
    assert all(store.read(body["slug"]).handle == body["change"] for _, body in results)
    assert store.issued() == 2


def test_same_title_creates_in_two_processes_keep_both_under_distinct_handles(repo):
    store = Store.open(repo)
    store.issued()
    answers = _together(_spawn("host", repo, "Same title"), _spawn("host", repo, "Same title"))
    assert sorted(code for code, _ in answers) == [200, 200]
    assert sorted(body["slug"] for _, body in answers) == ["same-title", "same-title-2"]
    assert sorted(body["change"] for _, body in answers) == ["c1", "c2"]
    assert store.issued() == 2


def test_a_curation_start_and_a_host_create_in_two_processes_never_share_a_slug(repo, tmp_path):
    store = Store.open(repo)
    store.issued()
    answers = _together(
        _spawn("host", repo, "Review the tests 1"),
        _spawn("curation", repo, str(tmp_path / "worktrees")),
    )
    assert sorted(code for code, _ in answers) == [200, 200]
    assert len({body["slug"] for _, body in answers}) == 2
    assert len({body["change"] for _, body in answers}) == 2
    assert sorted(store.slugs()) == sorted(body["slug"] for _, body in answers)
    assert all(store.read(body["slug"]).handle == body["change"] for _, body in answers)


def test_a_host_save_runs_during_a_curation_setup_and_never_takes_its_identity(repo, monkeypatch):
    store = Store.open(repo)
    store.issued()
    entered, release, real_ensure = threading.Event(), threading.Event(), worktree.ensure

    def gated(*args: object) -> Path:
        entered.set()
        assert release.wait(timeout=15), "the test never released the curation setup"
        return real_ensure(*args)

    monkeypatch.setattr(worktree, "ensure", gated)
    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(curation.start, store, repo, ["web"], NOW)
        try:
            assert entered.wait(timeout=15), "the curation start never reached its setup"
            code, saved = briefs.save_brief(store, brief("Gated create"))
        finally:
            release.set()
        change = pending.result(timeout=15)
    assert (code, saved["change"], saved["slug"]) == (200, "c2", "gated-create")
    assert (change.handle, change.slug) == ("c1", "review-the-tests-1")
    assert store.issued() == 2


def test_a_failed_curation_setup_keeps_its_handle_and_slug_burned(repo, monkeypatch):
    store = Store.open(repo)

    def broken(*_args: object) -> Path:
        msg = "worktree setup failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(worktree, "ensure", broken)
    with pytest.raises(RuntimeError, match="worktree setup failed"):
        curation.start(store, repo, ["web"], NOW)
    assert store.issued() == 1
    assert store.slugs() == []
    code, saved = briefs.save_brief(store, brief("Review the tests 1"))
    assert (code, saved["change"], saved["slug"]) == (200, "c2", "review-the-tests-1-2")


def test_a_create_that_fails_before_it_publishes_keeps_no_number(repo):
    store = Store.open(repo)

    def refuse(_number: int, _taken: list[str]) -> Any:
        msg = "drafting failed"
        raise ValueError(msg)

    with pytest.raises(ValueError, match="drafting failed"):
        identities.publish_new(store, refuse)
    assert (store.issued(), store.slugs()) == (0, [])
    assert briefs.save_brief(store, brief("First"))[1]["change"] == "c1"
