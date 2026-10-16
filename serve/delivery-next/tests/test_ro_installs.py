"""Read-only sessions find the Change's dependencies installed in its read-only worktree, as the Builder would."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next import sdk_adapter, sessions, tools
from owlbear_delivery_next.models import Brief, Change, Step, StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.steps import ro_installs
from owlbear_delivery_next.store import Lock, Store

INSTALL = "sh -c 'mkdir -p node_modules && echo x >> node_modules/count'"


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def commit(repo: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
        git(repo, "add", name)
    git(repo, "commit", "-qm", "files")


def store_with(tmp_path: Path, command: str) -> tuple[Store, Change]:
    store = Store(tmp_path / "store")
    change = Change(slug="c1", brief=Brief(version=1, scope=["app/src"]), step=Step(kind=StepKind.REVIEW))
    store.write(Lock("c1"), change)
    entries = {
        "install:app": ProfileEntry(state="known", value=command, evidence="t"),
        "install:other": ProfileEntry(state="known", value="sh -c 'exit 9'", evidence="outside the Change's scope"),
    }
    store.write_profile(Profile(entries=entries))
    return store, change


@pytest.fixture
def app(change_repo) -> Path:
    commit(change_repo, {".gitignore": "node_modules/\n", "app/package.json": "{}\n", "app/package-lock.json": "1\n"})
    return change_repo


def session(store: Store, change: Change, repo: Path, act=lambda _at: None) -> sdk_adapter.Session:
    """Run one read-only session in the read-only worktree; the session it was given."""
    seen = []

    def make(at: Path) -> list[sdk_adapter.Session]:
        cfg = sdk_adapter.Session(
            kind=StepKind.REVIEW, worktree=at, session_id="s", message="review", resume=False,
            policy=Policy(at, write=False), observe=tools.Worktree, checks=(), fresh="review",
        )  # fmt: skip
        return [cfg]

    def go(cfgs: list[sdk_adapter.Session]) -> list[Run]:
        seen.extend(cfgs)
        act(cfgs[0].worktree)
        return [Run(c.session_id, "result", termination=Termination(confirmed=True)) for c in cfgs]

    sessions.isolated(store, Lock("c1"), change, repo, make, go)
    return seen[0]


def installs(store: Store) -> list[dict]:
    return [e for e in store.events("c1") if e["event"] == "ro-install"]


def test_dependencies_are_installed_once_and_reused_while_their_inputs_are_unchanged(tmp_path, app):
    store, change = store_with(tmp_path, INSTALL)
    first = session(store, change, app)
    at = first.worktree
    assert (at / "app" / "node_modules" / "count").read_text() == "x\n"
    second = session(store, change, app)
    assert (at / "app" / "node_modules" / "count").read_text() == "x\n"
    assert [(e["package"], e["command"], e["ok"]) for e in installs(store)] == [("app", INSTALL, True)]
    assert isinstance(installs(store)[0]["seconds"], float)
    assert (first.message, second.message) == ("review", "review")


def test_dependencies_are_installed_again_when_the_lockfile_changes(tmp_path, app):
    store, change = store_with(tmp_path, INSTALL)
    at = session(store, change, app).worktree
    commit(app, {"app/package-lock.json": "2\n"})
    session(store, change, app)
    assert (at / "app" / "node_modules" / "count").read_text() == "x\nx\n"
    assert len(installs(store)) == 2


def test_the_reset_keeps_ignored_files_and_discards_session_files_and_tracked_edits(tmp_path, app):
    store, change = store_with(tmp_path, INSTALL)

    def act(at: Path) -> None:
        (at / "a.txt").write_text("changed\n")
        (at / "new.txt").write_text("new\n")
        (at / "app" / "node_modules" / "built").write_text("kept\n")

    at = session(store, change, app, act).worktree
    session(store, change, app)
    assert (at / "a.txt").read_text() == "a\n"
    assert not (at / "new.txt").exists()
    assert (at / "app" / "node_modules" / "built").read_text() == "kept\n"
    assert git(at, "status", "--porcelain") == ""


def test_a_failed_install_is_noted_for_the_session_and_tried_again_next_time(tmp_path, app):
    store, change = store_with(tmp_path, "sh -c 'echo tsc: command not found >&2; exit 3'")
    first = session(store, change, app)
    note = "Dependencies could not be installed in app: `sh -c 'echo tsc: command not found >&2; exit 3'` failed: "
    assert first.message == f"review\n\n{note}tsc: command not found"
    assert first.fresh == first.message
    session(store, change, app)
    assert [e["ok"] for e in installs(store)] == [False, False]


def test_a_new_read_only_worktree_forgets_earlier_installs(tmp_path, app):
    store, change = store_with(tmp_path, INSTALL)
    at = session(store, change, app).worktree
    git(app, "worktree", "remove", "--force", str(at))
    session(store, change, app)
    assert (at / "app" / "node_modules" / "count").read_text() == "x\n"
    assert len(installs(store)) == 2
    assert (store.root / "changes" / "c1" / ro_installs.STATE).is_file()
