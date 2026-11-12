import contextlib
import json
import subprocess
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from owlbear_memory import MemoryBusyError, MemoryCategory, MemoryEngine, storage

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import curation_apply, data_repo, local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.project_host import api, memory_routes, pack_routes
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(shared_repo, tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    root, remote = shared_repo
    repo = tmp_path / "shop"
    home = tmp_path / "home"
    home.mkdir()
    (home / "data.json").write_text(json.dumps({"repository": str(root)}))
    monkeypatch.setattr(local_home, "root", lambda: home)
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "commit", "--allow-empty", "-qm", "start")
    return root, remote, repo


def client(store: Store, headers=AUTH) -> TestClient:
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=headers)


def seed(folder: Path, title: str, *, curated: bool = False, agent: str = "builder"):
    engine = MemoryEngine(folder)
    entry = engine.save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PITFALL], confidence=0.8,
        source_agent=agent, scope_agents=[],
    )  # fmt: skip
    return engine.edit(entry.id, {"scope_agents": [agent]}, expected_revision=entry.revision) if curated else entry


def test_without_a_shared_repository_the_memory_tab_says_so(tmp_path):
    c = client(Store(tmp_path / "store"))
    got = c.get("/api/next/memory").json()
    assert (got["available"], got["entries"]) == (False, [])
    assert "shared repository" in got["reason"]
    assert c.post("/api/next/memory/x/approve", json={"updated_at": "x"}).status_code == 409
    assert client(Store(tmp_path / "store"), headers={}).get("/api/next/memory").status_code == 401


def test_owner_lifecycle_lists_public_fields_and_publishes_only_the_entries_actual_path(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated = seed(folder, "Run ruff first", curated=True)
    pending = seed(folder, "Ask before merging", agent="shaper")
    (folder / f"{curated.id}.md").rename(folder / "run-ruff-first.md")
    c = client(store)
    got = c.get("/api/next/memory").json()
    assert (got["available"], got["parse_errors"]) == (True, 0)
    assert {(e["title"], e["state"], tuple(e["scope_agents"])) for e in got["entries"]} == {
        ("Run ruff first", "curated", ("builder",)),
        ("Ask before merging", "pending", ()),
    }
    assert all(e["updated_at"] and not {"score", "assessment_receipts"} & e.keys() for e in got["entries"])
    assert "deleted" in got["states"]
    assert "pitfall" in got["categories"]
    unpublished = seed(folder, "Written by an agent, not yet published")

    approved = c.post(f"/api/next/memory/{curated.id}/approve", json={"updated_at": curated.updated_at}).json()
    assert git(remote, "show", "--name-only", "--format=", "main").splitlines() == [
        f"{store.name}/memory/run-ruff-first.md"
    ]
    stale = c.post(f"/api/next/memory/{curated.id}/edit", json={"updated_at": curated.updated_at, "title": "x"})
    edit = {"updated_at": approved["entry"]["updated_at"], "title": "Run ruff before tests", "categories": ["process"]}
    edited = c.post(f"/api/next/memory/{curated.id}/edit", json=edit).json()
    deleted = c.post(f"/api/next/memory/{pending.id}/delete", json={"updated_at": pending.updated_at})

    assert (approved["entry"]["state"], approved["notice"]) == ("approved", "")
    assert stale.status_code == 409
    assert (edited["entry"]["title"], edited["entry"]["categories"], edited["entry"]["state"]) == (
        "Run ruff before tests",
        ["process"],
        "curated",
    )
    assert (deleted.status_code, deleted.json()["notice"]) == (200, "")
    assert not (folder / f"{pending.id}.md").exists()
    assert not (folder / f"{curated.id}.md").exists()
    assert git(root, "status", "--porcelain") == f"?? {store.name}/memory/{unpublished.id}.md"
    log = git(remote, "log", "--format=%s", "main", "--", f"{store.name}/memory/run-ruff-first.md").splitlines()
    assert log == [f"memory {store.name}: edit Run ruff before tests", f"memory {store.name}: approve Run ruff first"]


def test_purge_removes_only_old_deleted_entries_and_publishes_their_removal(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    gone, kept = seed(folder, "Old lesson", curated=True), seed(folder, "Still used", curated=True)
    c = client(store)
    approved = c.post(f"/api/next/memory/{gone.id}/approve", json={"updated_at": gone.updated_at}).json()["entry"]
    c.post(f"/api/next/memory/{gone.id}/delete", json={"updated_at": approved["updated_at"]})

    recent = c.post("/api/next/memory/purge", json={}).json()
    purged = c.post("/api/next/memory/purge", json={"min_age_days": 0}).json()

    assert (recent["purged"], recent["skipped"], recent["notice"]) == (0, 1, "")
    assert (purged["purged"], purged["skipped"], purged["failed"]) == (1, 0, 0)
    assert [p.stem for p in folder.glob("*.md")] == [kept.id]
    assert git(remote, "log", "-1", "--format=%s", "main") == f"memory {store.name}: purge 1 deleted"


def deleted_days_ago(folder: Path, title: str, days: int, *, category: MemoryCategory | None = None) -> str:
    """An entry the owner deleted *days* ago: its file's updated_at is when it was deleted."""
    engine = MemoryEngine(folder)
    entry = seed(folder, title, curated=True)
    if category is not None:
        entry = engine.edit(entry.id, {"categories": [category]}, expected_revision=entry.revision)
    gone = engine.delete(entry.id, engine.approve(entry.id, entry.updated_at).updated_at)
    stamp = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    storage.write_entry(folder / f"{gone.id}.md", gone.model_copy(update={"updated_at": stamp}), memory_dir=folder)
    return gone.id


def owner_holds(root: Path, **values: object) -> None:
    """The owner's memory values in the shared repository's global settings."""
    (root / "config.json").write_text(json.dumps({"format": 21, "memory": values}))


def test_purge_applies_the_owners_age_unless_one_is_sent_and_the_page_is_told_it(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    old, recent = deleted_days_ago(folder, "Old lesson", 21), deleted_days_ago(folder, "Recent lesson", 7)
    owner_holds(root, purge_days=14)
    c = client(store)

    assert c.get("/api/next/memory").json()["purge_days"] == 14
    first = c.post("/api/next/memory/purge", json={}).json()  # the server applies the setting: no age is sent
    assert (first["purged"], first["skipped"]) == (1, 1)
    assert [p.stem for p in folder.glob("*.md")] == [recent]
    assert old not in {p.stem for p in folder.glob("*.md")}

    second = c.post("/api/next/memory/purge", json={"min_age_days": 0}).json()  # an age sent overrides it
    assert (second["purged"], second["skipped"]) == (1, 0)


def test_purge_without_an_age_and_without_the_setting_is_refused_and_the_page_is_told_why(shared, monkeypatch):
    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)  # production: no layer under the owner's own
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    deleted_days_ago(folder, "Old lesson", 400)
    c = client(store)

    listed = c.get("/api/next/memory").json()
    assert (listed["purge_days"], "purge age is unset" in listed["purge_why"]) == (None, True)
    refused = c.post("/api/next/memory/purge", json={})
    assert (refused.status_code, "purge age is unset" in refused.json()["detail"]) == (409, True)
    assert len(list(folder.glob("*.md"))) == 1  # nothing was removed
    assert c.post("/api/next/memory/purge", json={"min_age_days": 0}).json()["purged"] == 1  # an age sent still works


def test_unreadable_settings_reach_the_purge_line_and_its_refusal_whole(shared, monkeypatch, whole_error):
    root, _, repo = shared
    store = Store.open(repo)
    deleted_days_ago(root / store.name / "memory", "Old lesson", 400)
    c = client(store)
    error = StoreError(whole_error)
    error.add_note("a note added on the way up")

    def unreadable(_store):
        raise error

    monkeypatch.setattr(Store, "settings", unreadable)
    listed = c.get("/api/next/memory").json()
    refused = c.post("/api/next/memory/purge", json={})

    why = f"the settings can't be read: StoreError: {whole_error}\na note added on the way up"
    assert (listed["purge_days"], listed["purge_why"]) == (None, why)
    assert (refused.status_code, refused.json()["detail"]) == (409, why)


def curated(name: str, state: str, at: datetime) -> None:
    run = curation.FolderRun(
        state=state, started_at=at - timedelta(minutes=1), ended_at=at if state == "done" else None
    )
    (local_home.root() / curation.STATE).write_text(curation.Runs(folders={name: run}).model_dump_json())


def test_memorys_last_run_is_the_later_of_a_curation_run_and_the_owners_action(shared):
    """N1 (D-01M63CF1XKCCF6TP60734BTMWD): Maintenance read only the owner's actions, so it said "Never run" after a
    curation run, and it never said which of the two it showed."""
    root, _, repo = shared
    store = Store.open(repo)
    entry = seed(root / store.name / "memory", "Run ruff first", curated=True)
    c = client(store)

    def last() -> dict | None:
        return {a["name"]: a for a in c.get("/api/next/maintenance").json()}["Memory curation"]["last"]

    assert last() is None
    ran = datetime.now(UTC) - timedelta(hours=1)
    curated(store.name, "done", ran)
    assert last() == {"by": "curation", "state": "done", "started_at": (ran - timedelta(minutes=1)).isoformat(),
                      "ended_at": ran.isoformat(), "reason": ""}  # fmt: skip
    c.post(f"/api/next/memory/{entry.id}/approve", json={"updated_at": entry.updated_at}).raise_for_status()
    got = last()
    assert (got["by"], got["state"], got["action"]) == ("owner", "done", "approve Run ruff first")
    assert datetime.fromisoformat(got["ended_at"]) > ran
    curated(store.name, "running", datetime.now(UTC) + timedelta(minutes=2))  # started after the action
    assert (last()["by"], last()["state"]) == ("curation", "running")
    curated("another-project", "done", datetime.now(UTC) + timedelta(hours=1))  # another folder's run never counts
    assert last()["by"] == "owner"
    (local_home.root() / curation.STATE).write_text("{")
    got = last()
    assert (got["by"], got["action"]) == ("owner", "approve Run ruff first")
    assert got["history_notice"].startswith("memory curation's runs could not be read, so they are not counted")


@pytest.mark.parametrize(("broken", "state"), [("spawn", "running"), ("timeout", "failed"), ("exit", None)])
def test_unreadable_owner_history_qualifies_the_readable_run_without_replacing_its_reason(
    shared, monkeypatch, whole_error, broken, state
):
    _root, _, repo = shared
    store = Store.open(repo)
    if state:
        run = curation.FolderRun(state=state, started_at=datetime.now(UTC), reason="curation's own detail")
        (local_home.root() / curation.STATE).write_text(curation.Runs(folders={store.name: run}).model_dump_json())
    command = ["git", "log"]
    error = {
        "spawn": OSError(whole_error),
        "timeout": subprocess.TimeoutExpired(command, 10, output=whole_error.encode(), stderr=b"history stderr"),
        "exit": subprocess.CalledProcessError(128, command, output=whole_error, stderr="history stderr"),
    }[broken]
    error.add_note("history command note")
    real = subprocess.run

    def unreadable(args, **kwargs):
        if args[:2] != command:
            return real(args, **kwargs)
        if broken == "exit":
            return subprocess.CompletedProcess(args, error.returncode, error.output, error.stderr)
        raise error

    monkeypatch.setattr(pack_routes.subprocess, "run", unreadable)
    got = {a["name"]: a for a in client(store).get("/api/next/maintenance").json()}["Memory curation"]["last"]
    if broken == "exit":
        error = subprocess.CalledProcessError(
            128,
            [
                "git",
                "log",
                "-1",
                "--format=%cI%x00%s",
                "--fixed-strings",
                f"--grep=memory {store.name}: ",
                "--",
                str(store.shared.memory_path(store.name)),
            ],
            output=whole_error,
            stderr="history stderr",
        )
    assert got["history_notice"] == (
        f"the owner's memory history could not be read, so it is not counted: {failure(error)}"
    )
    assert (got["by"], got["state"]) == ("curation", state or "unknown")
    assert got.get("reason", "") == ("curation's own detail" if state else "")


def test_unreadable_curation_runs_qualify_memorys_last_run_whole(shared, monkeypatch, whole_error):
    _root, _, repo = shared
    store = Store.open(repo)
    curated(store.name, "done", datetime.now(UTC))
    error = ValueError(whole_error)
    error.add_note("a note added on the way up")

    def unreadable(_text: str):
        raise error

    monkeypatch.setattr(pack_routes.curation_runs.Runs, "model_validate_json", unreadable)
    got = {a["name"]: a for a in client(store).get("/api/next/maintenance").json()}["Memory curation"]["last"]

    why = f"ValueError: {whole_error}\na note added on the way up"
    unread = f"memory curation's runs could not be read, so they are not counted: {why}"
    assert got == {"by": "curation", "state": "unknown", "history_notice": unread}
    owner_error = OSError("the owner's history is unreadable too")
    owner_error.add_note("owner history note")

    def no_history(_store):
        raise owner_error

    monkeypatch.setattr(pack_routes, "owner_last", no_history)
    got = pack_routes.memory_last(store)
    assert got == {
        "by": "curation",
        "state": "unknown",
        "history_notice": f"the owner's memory history could not be read, so it is not counted: "
        f"{failure(owner_error)}\n{unread}",
    }


def test_refused_memory_actions_say_why(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    pending = seed(folder, "Ask before merging")
    c = client(store)

    shown = {"updated_at": pending.updated_at}
    calls = []
    for path, body, status in [
        (f"{pending.id}/approve", shown, 409),
        ("no-such-entry/delete", shown, 404),
        (f"{pending.id}/edit", shown | {"categories": []}, 422),
        (f"{pending.id}/edit", shown | {"content": "x" * 1025}, 422),
        ("..%2F..%2Fconfig/delete", shown, 404),
        ("purge", {"min_age_days": -1}, 422),
    ]:
        before = (
            {p.name: p.read_bytes() for p in folder.glob("*.md")},
            git(root, "rev-parse", "HEAD"),
            git(root, "status", "--porcelain"),
        )
        calls.append(c.post(f"/api/next/memory/{path}", json=body))
        assert calls[-1].status_code == status
        assert (
            {p.name: p.read_bytes() for p in folder.glob("*.md")},
            git(root, "rev-parse", "HEAD"),
            git(root, "status", "--porcelain"),
        ) == before
    assert "pending" in calls[0].json()["detail"]


def test_a_duplicate_repair_publishes_every_file_it_touched(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated = seed(folder, "Run ruff first", curated=True)
    other = seed(folder, "Written by an agent, not yet published")
    (folder / "copy.md").write_bytes((folder / f"{curated.id}.md").read_bytes())
    git(root, "add", "--", f"{store.name}/memory/{curated.id}.md", f"{store.name}/memory/copy.md")
    git(root, "commit", "-qm", "duplicate")
    git(root, "push", "-q")

    approved = client(store).post(f"/api/next/memory/{curated.id}/approve", json={"updated_at": curated.updated_at})

    assert approved.status_code == 200
    assert len(git(root, "show", "--name-only", "--format=", "HEAD").splitlines()) > 1
    assert git(root, "status", "--porcelain") == f"?? {store.name}/memory/{other.id}.md"


def test_a_purge_publishes_what_its_duplicate_repair_touched(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated = seed(folder, "Run ruff first", curated=True)
    (folder / "copy.md").write_text((folder / f"{curated.id}.md").read_text().replace("what to know", "a twin"))
    git(root, "add", "--", f"{store.name}/memory")
    git(root, "commit", "-qm", "differing duplicates")
    git(root, "push", "-q")

    purged = client(store).post("/api/next/memory/purge", json={})

    assert purged.status_code == 200
    assert git(root, "status", "--porcelain") == ""  # the repair's files are published with it


def test_no_agent_can_write_the_memory_until_the_owners_action_is_published(shared, monkeypatch):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated, other = seed(folder, "Run ruff first", curated=True), seed(folder, "Ask before merging")
    real, raced = data_repo.DataRepo.publish, []

    def publish(self, paths, message, until=None):
        agent = MemoryEngine(folder, writer_lock_timeout=0.2)
        write = threading.Thread(target=lambda: raced.append(attempt(agent, other)))
        write.start()
        write.join()
        return real(self, paths, message, until)

    monkeypatch.setattr(data_repo.DataRepo, "publish", publish)
    approved = client(store).post(f"/api/next/memory/{curated.id}/approve", json={"updated_at": curated.updated_at})

    assert approved.status_code == 200
    assert raced == [MemoryBusyError]


def test_global_listing_actions_and_round_trip_publish_both_paths_and_refuse_stale_replays(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    common = seed(root / "memory", "Sign every commit", curated=True)
    seed(folder, "Run ruff first")
    git(root, "add", "--", f"{store.name}/memory/{entry.id}.md")
    git(root, "commit", "-qm", "seed")
    git(root, "push", "-q")
    c = client(store)
    listed = c.get("/api/next/memory", params={"where": "global"}).json()
    approved = c.post(
        f"/api/next/memory/{common.id}/approve", params={"where": "global"}, json={"updated_at": common.updated_at}
    )
    elsewhere = c.post(f"/api/next/memory/{common.id}/approve", json={"updated_at": common.updated_at})
    assert ([e["title"] for e in listed["entries"]], listed["project"], listed["repository"]) == (
        ["Sign every commit"],
        store.name,
        str(root),
    )
    assert (approved.json()["entry"]["state"], elsewhere.status_code) == ("approved", 404)
    assert git(remote, "log", "-1", "--format=%s", "main") == "memory global: approve Sign every commit"

    stale = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": "2000-01-01T00:00:00Z"})
    moved = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})
    again = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})

    assert (stale.status_code, moved.status_code, again.status_code) == (409, 200, 404)
    assert (not (folder / f"{entry.id}.md").exists(), (root / "memory" / f"{entry.id}.md").is_file()) == (True, True)
    committed = sorted(git(remote, "show", "--no-renames", "--name-only", "--format=", "main").splitlines())
    assert committed == sorted([f"{store.name}/memory/{entry.id}.md", f"memory/{entry.id}.md"])
    assert git(remote, "log", "-1", "--format=%s", "main") == f"memory {store.name}: make global Pin the runtime"
    assert {e.id for e in MemoryEngine(root / "memory").get_entries()} == {entry.id, common.id}
    assert moved.json()["entry"]["origin"] == store.name
    globalized = moved.json()
    theirs = seed(root / "memory", "Their habit", curated=True)
    unknown = seed(root / "memory", "An older global", curated=True)
    theirs = theirs.model_copy(update={"origin": "docs-site"})
    storage.write_entry(root / "memory" / f"{theirs.id}.md", theirs, memory_dir=root / "memory")

    refused = [
        c.post(f"/api/next/memory/{e.id}/move-back", json={"updated_at": e.updated_at}) for e in (theirs, unknown)
    ]
    back = c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": globalized["entry"]["updated_at"]})

    assert globalized["entry"]["origin"] == store.name
    said = [(r.status_code, w in r.json()["detail"]) for r, w in zip(refused, ("docs-site", "recorded"), strict=True)]
    assert said == [(409, True), (409, True)]
    assert (back.status_code, back.json()["entry"]["origin"]) == (200, None)
    assert entry.id in {e.id for e in MemoryEngine(folder).get_entries()}
    assert "origin" not in (folder / f"{entry.id}.md").read_text()
    assert git(remote, "log", "-1", "--format=%s", "main") == f"memory {store.name}: move back Pin the runtime"
    replayed = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})
    assert replayed.status_code == 409


@pytest.mark.parametrize(
    "phase",
    ["origin-value", "origin-permission", "rename-home", "write-home"],
)
def test_failed_moves_preserve_source_bytes_origin_and_git_and_can_retry(shared, monkeypatch, whole_error, phase):
    root, remote, repo = shared
    store = Store.open(repo)
    folder, common = root / store.name / "memory", root / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    c = client(store)
    back = phase in {"rename-home", "write-home"}
    shown = (
        c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()["entry"]
        if back
        else {"updated_at": entry.updated_at}
    )
    source, target = (common, folder) if back else (folder, common)
    before = (source / f"{entry.id}.md").read_bytes()
    heads = git(root, "rev-parse", "HEAD"), git(remote, "rev-parse", "main")
    raised = {
        "origin-value": ValueError(whole_error),
        "origin-permission": PermissionError(13, whole_error, "entry.md"),
        "rename-home": PermissionError(13, "Permission denied"),
        "write-home": OSError(28, "No space left on device"),
    }[phase]
    if not back:
        raised.add_note("a note added on the way up")
    real_write, real_replace = storage.write_entry, Path.replace

    def refusing(path, written, *, memory_dir):
        if (phase.startswith("origin") and getattr(written, "origin", None)) or (
            phase == "write-home" and memory_dir == folder
        ):
            raise raised
        return real_write(path, written, memory_dir=memory_dir)

    def refuse_rename(self, destination):
        if phase == "rename-home" and Path(destination).parent == folder and Path(destination).suffix == ".md":
            raise raised
        return real_replace(self, destination)

    action = "move-back" if back else "make-global"
    monkeypatch.setattr(storage, "write_entry", refusing)
    monkeypatch.setattr(Path, "replace", refuse_rename)
    failed = c.post(f"/api/next/memory/{entry.id}/{action}", json={"updated_at": shown["updated_at"]})
    status = 422 if phase == "origin-value" else 409
    said = "cannot move" if status == 422 else "could not move"
    suffix = "" if status == 422 else "; try again"
    assert (failed.status_code, failed.json()["detail"]) == (
        status,
        f"Pin the runtime {said}: {failure(raised)}{suffix}",
    )
    assert (source / f"{entry.id}.md").read_bytes() == before
    assert not (target / f"{entry.id}.md").exists()
    assert MemoryEngine(source).get_entry(entry.id).origin == (store.name if back else None)
    assert (git(root, "rev-parse", "HEAD"), git(remote, "rev-parse", "main")) == heads
    monkeypatch.setattr(storage, "write_entry", real_write)
    monkeypatch.setattr(Path, "replace", real_replace)
    again = c.post(f"/api/next/memory/{entry.id}/{action}", json={"updated_at": shown["updated_at"]})
    assert again.status_code == 200
    assert [e.id for e in MemoryEngine(target).get_entries()] == [entry.id]
    assert MemoryEngine(source).get_entries() == []


def test_no_entry_moves_while_a_curation_runs_apply_is_cut_short(shared):
    """#875: the cut-short set names its files where they are, so neither Make global nor Move back moves one."""
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry, other = seed(folder, "Pin the runtime", curated=True), seed(folder, "Sign every commit", curated=True)
    c = client(store)
    made = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()["entry"]
    curation_apply.write(data_repo.DataRepo(root), curation_apply.Apply(store.name, {}))
    head = git(root, "rev-parse", "HEAD")

    refused = [
        c.post(f"/api/next/memory/{other.id}/make-global", json={"updated_at": other.updated_at}),
        c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": made["updated_at"]}),
    ]

    cut = f"stays: the memory curation of {store.name} was cut short while its files were copied in"
    assert [(r.status_code, cut in r.json()["detail"]) for r in refused] == [(409, True), (409, True)]
    assert ((folder / f"{other.id}.md").is_file(), (root / "memory" / f"{entry.id}.md").is_file()) == (True, True)
    assert git(root, "rev-parse", "HEAD") == head


def test_make_global_refuses_an_entry_global_memory_holds_or_the_curator_has_not_scoped(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    (root / "memory").mkdir()
    (root / "memory" / "copy.md").write_bytes((folder / f"{entry.id}.md").read_bytes())

    pending = seed(folder, "Written by an agent")
    c = client(store)
    refused = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})
    unscoped = c.post(f"/api/next/memory/{pending.id}/make-global", json={"updated_at": pending.updated_at})

    assert (refused.status_code, "already" in refused.json()["detail"]) == (409, True)
    assert (unscoped.status_code, "curator" in unscoped.json()["detail"]) == (409, True)  # Global has no curator
    assert ((folder / f"{entry.id}.md").is_file(), (folder / f"{pending.id}.md").is_file()) == (True, True)


def attempt(engine: MemoryEngine, entry) -> type[Exception] | None:
    try:
        engine.edit(entry.id, {"title": "an agent's edit"}, expected_revision=entry.revision)
    except Exception as exc:  # noqa: BLE001 - the test reports what the agent met
        return type(exc)
    return None


@contextlib.contextmanager
def memory_page(store: Store, pds: Any, query: str = "") -> Iterator[Any]:
    """The Memory page in a real browser: only the test host and the PDS CDN answer."""
    import socket  # noqa: PLC0415
    import time  # noqa: PLC0415

    import uvicorn  # noqa: PLC0415
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            while not server.started:
                assert thread.is_alive(), "the owned page server stopped before startup"
                time.sleep(0.05)
            base = f"http://127.0.0.1:{sock.getsockname()[1]}"
            with sync_playwright() as pw:
                try:
                    browser = pw.chromium.launch()
                except Error as exc:
                    pytest.skip(f"no Playwright Chromium: {exc}")
                page = browser.new_page()
                pds.only(page, base)
                page.goto(f"{base}/memory{query}#token=tok")
                yield page
                browser.close()
        finally:
            server.should_exit = True
            thread.join(5)
            assert not thread.is_alive(), "the owned page server did not stop"


def refreshed(page: Any) -> None:
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")


@pytest.mark.browser
def test_browser_edit_filter_and_settings_navigation_preserve_drafts_and_project(shared, pds):
    """TD-264: the draft lives in page state, so a filter that removes the cards above it keeps what was typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    engine = MemoryEngine(folder)
    above = seed(folder, "Name the release", agent="shaper")
    engine.edit(above.id, {"categories": [MemoryCategory.PROCESS]}, expected_revision=above.revision)
    seed(folder, "Ask before merging", agent="shaper")  # newer, so listed above it in the same group
    with memory_page(store, pds, query="?project=shop") as page:
        expect(page.get_by_role("link", name="Memory settings")).to_have_attribute(
            "href", "/config?project=shop&layer=global#memory"
        )
        expect(page.locator("#shown")).to_have_text("2 of 2 shown")
        waiting = page.locator("section", has_text="Waiting for the curator").locator(".entry")
        expect(waiting).to_have_count(2)
        expect(waiting.first).to_contain_text("Ask before merging")
        page.locator(".entry", has_text="Name the release").get_by_role("button", name="Edit").click()
        page.get_by_label("Title").fill("Name the release after its tag")
        pds.pick(page, "Category", "process")  # the card above it leaves the page
        expect(page.locator("#shown")).to_have_text("1 of 2 shown")
        expect(page.get_by_label("Title")).to_have_value("Name the release after its tag")
        page.get_by_role("button", name="Save").click()
        expect(page.locator("#status")).to_have_text('Saved "Name the release after its tag".')
        builder = seed(folder, "Run ruff first", curated=True)
        refreshed(page)
        pds.pick(page, "Category", "any")
        pds.pick(page, "Agent", "builder")
        expect(page.locator("#shown")).to_have_text("1 of 3 shown")
        now = engine.get_entry(builder.id)
        engine.edit(builder.id, {"scope_agents": ["reviewer"]}, expected_revision=now.revision)
        refreshed(page)
        expect(pds.select(page, "Agent")).to_have_js_property("value", "any")
        expect(page.locator("#shown")).to_have_text("3 of 3 shown")
        expect(page.locator(".entry")).to_have_count(3)
    assert {e.id: e.title for e in MemoryEngine(folder).get_entries()}[above.id] == "Name the release after its tag"


@pytest.mark.browser
def test_the_deleted_section_removes_entries_deleted_before_the_owners_purge_age(shared, pds):
    """TD-416: the Memory page's purge; only entries deleted as long ago as the owner's age, here 14 days, go."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    owner_holds(root, purge_days=14)
    deleted_days_ago(folder, "Old lesson", 21)
    deleted_days_ago(folder, "Old process", 21, category=MemoryCategory.PROCESS)  # hidden by the filter below
    deleted_days_ago(folder, "Recent lesson", 7)  # 7 days: kept under 14, though under today's 30 as well
    with memory_page(store, pds) as page:
        pds.pick(page, "State", "any")
        pds.pick(page, "Category", "pitfall")
        deleted = page.locator("section", has_text="Deleted (history kept)")
        expect(deleted.locator(".entry")).to_have_count(2)
        deleted.get_by_role("button", name=f"Remove 2 deleted entries older than 14 days from {store.name}").click()
        expect(pds.modal(page).locator('p-button[variant="primary"]')).to_have_text(["Keep them"])  # never removing
        expect(pds.modal(page)).to_contain_text("deleted 14 days ago or earlier")
        owner_holds(root, purge_days=0)  # the owner changes the age while the dialog is open: it removes what it said
        pds.answer(page, "Remove them")
        expect(page.locator("#status")).to_contain_text(f"Removed 2 deleted entries from {store.name}.")
        expect(deleted.locator(".entry")).to_have_count(1)
    assert [e.title for e in MemoryEngine(folder).get_entries()] == ["Recent lesson"]


@pytest.mark.browser
def test_an_unset_purge_age_disables_the_removal_and_says_why_with_a_link_to_the_setting(shared, pds, monkeypatch):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    from owlbear_delivery_next.settings import config  # noqa: PLC0415

    monkeypatch.setattr(config, "BASE", None)  # production: no layer under the owner's own
    root, _, repo = shared
    store = Store.open(repo)
    deleted_days_ago(root / store.name / "memory", "Old lesson", 400)
    with memory_page(store, pds) as page:
        pds.pick(page, "State", "any")
        deleted = page.locator("section", has_text="Deleted (history kept)")
        expect(deleted.locator(".entry")).to_have_count(1)
        button = deleted.get_by_role("button", name=f"Remove old deleted entries from {store.name}")
        expect(button).to_be_disabled()
        expect(deleted).to_contain_text("purge age is unset")
        expect(deleted.get_by_role("link", name="Set the purge age")).to_have_attribute(
            "href", "/config?layer=global#memory"
        )


@pytest.mark.browser
def test_approving_one_memory_leaves_the_next_ones_button_ready(shared, pds):
    """Sol, TD-264: a finished action's busy state never moves to the card that takes its place."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    seed(folder, "Run ruff first", curated=True)
    seed(folder, "Pin the runtime", curated=True)
    with memory_page(store, pds) as page:
        review = page.locator("section", has_text="Needs your review")
        expect(review.locator(".entry")).to_have_count(2)
        expect(review.locator('p-button[variant="primary"]')).to_have_text(["Approve"])  # the first entry's only
        expect(review.locator(".entry").first.locator('p-button[variant="primary"]')).to_have_count(1)
        leading = 'p-button:not([variant]), p-button[variant="primary"]'  # PDS renders a p-button without one primary
        review.locator(".entry").nth(1).get_by_role("button", name="Edit").click()
        expect(review.locator(leading)).to_have_text(["Save"])  # the open editor leads, not another entry's Approve
        review.get_by_role("button", name="Cancel").click()
        expect(review.locator(leading)).to_have_text(["Approve"])
        review.locator(".entry").first.get_by_role("button", name="Approve").click()
        expect(review.locator(".entry")).to_have_count(1)
        expect(review.get_by_role("button", name="Approve")).to_be_enabled()
        expect(review.locator('p-button[variant="primary"]')).to_have_text(["Approve"])  # the next one leads


def test_an_entry_too_large_with_its_origin_is_refused_without_writes(shared, monkeypatch):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    big = seed(folder, "Too large", curated=True)
    c = client(store)
    before = (folder / f"{big.id}.md").read_bytes()
    head = git(root, "rev-parse", "HEAD")

    def too_large(*_a, **_k):
        too = "serialized entry exceeds 8192 bytes"
        raise ValueError(too)

    monkeypatch.setattr(memory_routes.storage, "write_entry", too_large)
    refused = c.post(f"/api/next/memory/{big.id}/make-global", json={"updated_at": big.updated_at})

    assert (refused.status_code, "8192" in refused.json()["detail"]) == (422, True)
    assert [e.id for e in MemoryEngine(folder).get_entries()] == [big.id]
    assert ((folder / f"{big.id}.md").read_bytes(), git(root, "rev-parse", "HEAD")) == (before, head)
    assert not list((root / "memory").glob("*.md"))
