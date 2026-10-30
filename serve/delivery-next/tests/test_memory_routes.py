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

from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.project_host import api, memory_routes
from owlbear_delivery_next.project_host.host import HostRecord
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
def shared(tmp_path: Path, monkeypatch) -> tuple[Path, Path, Path]:
    remote, root, repo = tmp_path / "remote.git", tmp_path / "owlbear-data", tmp_path / "shop"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
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


def test_the_memory_tab_lists_the_projects_memory_with_what_the_filters_need(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    seed(folder, "Run ruff first", curated=True)
    seed(folder, "Ask before merging", agent="shaper")

    got = client(store).get("/api/next/memory").json()

    assert (got["available"], got["parse_errors"]) == (True, 0)
    assert {(e["title"], e["state"], tuple(e["scope_agents"])) for e in got["entries"]} == {
        ("Run ruff first", "curated", ("builder",)),
        ("Ask before merging", "pending", ()),
    }
    assert all(e["updated_at"] for e in got["entries"])
    assert "deleted" in got["states"]
    assert "pitfall" in got["categories"]


def test_the_owner_approves_edits_and_deletes_and_each_action_is_committed(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated, pending = seed(folder, "Run ruff first", curated=True), seed(folder, "Ask before merging")
    c = client(store)

    approved = c.post(f"/api/next/memory/{curated.id}/approve", json={"updated_at": curated.updated_at}).json()
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
    log = git(remote, "log", "--format=%s", "main", "--", f"{store.name}/memory/{curated.id}.md").splitlines()
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
    assert c.post("/api/next/memory/purge", json={"min_age_days": -1}).status_code == 422


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
    assert got["reason"].startswith("memory curation's runs could not be read, so they are not counted")


def test_refused_memory_actions_say_why(shared):
    root, _, repo = shared
    store = Store.open(repo)
    pending = seed(root / store.name / "memory", "Ask before merging")
    c = client(store)

    calls = [
        c.post(f"/api/next/memory/{pending.id}/approve", json={"updated_at": pending.updated_at}),
        c.post("/api/next/memory/no-such-entry/delete", json={"updated_at": pending.updated_at}),
        c.post(f"/api/next/memory/{pending.id}/edit", json={"updated_at": pending.updated_at, "categories": []}),
        c.post(f"/api/next/memory/{pending.id}/edit", json={"updated_at": pending.updated_at, "content": "x" * 1025}),
        c.post("/api/next/memory/..%2F..%2Fconfig/delete", json={"updated_at": pending.updated_at}),
    ]

    assert [r.status_code for r in calls] == [409, 404, 422, 422, 404]
    assert "pending" in calls[0].json()["detail"]


def test_an_action_publishes_the_file_the_entry_lives_in_and_nothing_else(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    curated = seed(folder, "Run ruff first", curated=True)
    (folder / f"{curated.id}.md").rename(folder / "run-ruff-first.md")
    unpublished = seed(folder, "Written by an agent, not yet published")

    approved = client(store).post(f"/api/next/memory/{curated.id}/approve", json={"updated_at": curated.updated_at})

    assert approved.json()["entry"]["state"] == "approved"
    assert not (folder / f"{curated.id}.md").exists()
    committed = git(remote, "show", "--name-only", "--format=", "main").splitlines()
    assert committed == [f"{store.name}/memory/run-ruff-first.md"]
    assert git(root, "status", "--porcelain") == f"?? {store.name}/memory/{unpublished.id}.md"


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


def test_global_memory_is_listed_and_acted_on_beside_the_projects(shared):
    """TD-241: ``?where=global`` reads and changes the shared repository's Global memory, committed as Global."""
    root, remote, repo = shared
    store = Store.open(repo)
    common = seed(root / "memory", "Sign every commit", curated=True)
    seed(root / store.name / "memory", "Run ruff first")
    c = client(store)

    listed = c.get("/api/next/memory", params={"where": "global"}).json()
    approved = c.post(
        f"/api/next/memory/{common.id}/approve", params={"where": "global"}, json={"updated_at": common.updated_at}
    )
    elsewhere = c.post(f"/api/next/memory/{common.id}/approve", json={"updated_at": common.updated_at})

    assert ([e["title"] for e in listed["entries"]], listed["project"], listed["repository"]) == (
        ["Sign every commit"], store.name, str(root)
    )  # fmt: skip
    assert (approved.json()["entry"]["state"], elsewhere.status_code) == ("approved", 404)
    assert git(remote, "log", "-1", "--format=%s", "main") == "memory global: approve Sign every commit"


def test_make_global_moves_the_entry_and_publishes_both_folders(shared):
    root, remote, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    git(root, "add", "--", f"{store.name}/memory/{entry.id}.md")
    git(root, "commit", "-qm", "seed")
    git(root, "push", "-q")
    c = client(store)

    stale = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": "2000-01-01T00:00:00Z"})
    moved = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})
    again = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})

    assert (stale.status_code, moved.status_code, again.status_code) == (409, 200, 404)
    assert (not (folder / f"{entry.id}.md").exists(), (root / "memory" / f"{entry.id}.md").is_file()) == (True, True)
    committed = sorted(git(remote, "show", "--no-renames", "--name-only", "--format=", "main").splitlines())
    assert committed == sorted([f"{store.name}/memory/{entry.id}.md", f"memory/{entry.id}.md"])
    assert git(remote, "log", "-1", "--format=%s", "main") == f"memory {store.name}: make global Pin the runtime"
    assert [e.id for e in MemoryEngine(root / "memory").get_entries()] == [entry.id]


def test_a_global_entry_moves_back_only_to_the_project_it_came_from(shared):
    """TD-292: Make global records the project; only it takes the entry back, and one without a record stays."""
    root, remote, repo = shared
    store = Store.open(repo)
    folder, common = root / store.name / "memory", root / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    c = client(store)
    globalized = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()
    theirs, unknown = seed(common, "Their habit", curated=True), seed(common, "An older global", curated=True)
    theirs = theirs.model_copy(update={"origin": "docs-site"})
    storage.write_entry(common / f"{theirs.id}.md", theirs, memory_dir=common)

    refused = [
        c.post(f"/api/next/memory/{e.id}/move-back", json={"updated_at": e.updated_at}) for e in (theirs, unknown)
    ]
    back = c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": globalized["entry"]["updated_at"]})

    assert globalized["entry"]["origin"] == store.name
    said = [(r.status_code, w in r.json()["detail"]) for r, w in zip(refused, ("docs-site", "recorded"), strict=True)]
    assert said == [(409, True), (409, True)]
    assert (back.status_code, back.json()["entry"]["origin"]) == (200, None)
    assert [e.id for e in MemoryEngine(folder).get_entries()] == [entry.id]
    assert "origin" not in (folder / f"{entry.id}.md").read_text()
    assert git(remote, "log", "-1", "--format=%s", "main") == f"memory {store.name}: move back Pin the runtime"


def test_a_move_that_fails_keeps_the_entry_where_it_was_with_its_origin_and_can_be_tried_again(shared, monkeypatch):
    root, _, repo = shared
    store = Store.open(repo)
    folder, common = root / store.name / "memory", root / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    c = client(store)
    shown = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()["entry"]
    real = Path.replace

    def refuse(self, target):  # only the move into the project's folder fails; atomic writes still work
        if Path(target).parent == folder and Path(target).suffix == ".md":
            raise PermissionError(13, "Permission denied")
        return real(self, target)

    monkeypatch.setattr(Path, "replace", refuse)
    failed = c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": shown["updated_at"]})
    monkeypatch.setattr(Path, "replace", real)
    again = c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": shown["updated_at"]})

    assert (failed.status_code, "try again" in failed.json()["detail"]) == (409, True)
    assert again.status_code == 200
    assert [e.id for e in MemoryEngine(folder).get_entries()] == [entry.id]
    assert MemoryEngine(common).get_entries() == []


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
def memory_page(store: Store, pds: Any) -> Iterator[Any]:
    """The Memory page in a real browser: only the test host and the PDS CDN answer."""
    import socket  # noqa: PLC0415
    import time  # noqa: PLC0415

    import uvicorn  # noqa: PLC0415
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host()), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page()
            pds.only(page, base)
            page.goto(f"{base}/memory#token=tok")
            yield page
            browser.close()
    finally:
        server.should_exit = True


def refreshed(page: Any) -> None:
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")


@pytest.mark.browser
def test_a_memory_edit_survives_the_entries_before_it_disappearing_and_is_saved(shared, pds):
    """TD-264: the draft lives in page state, so a filter that removes the cards above it keeps what was typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    engine = MemoryEngine(folder)
    above = seed(folder, "Name the release", agent="shaper")
    engine.edit(above.id, {"categories": [MemoryCategory.PROCESS]}, expected_revision=above.revision)
    seed(folder, "Ask before merging", agent="shaper")  # newer, so listed above it in the same group
    with memory_page(store, pds) as page:
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
    assert {e.id: e.title for e in MemoryEngine(folder).get_entries()}[above.id] == "Name the release after its tag"


@pytest.mark.browser
def test_the_deleted_section_removes_entries_deleted_long_ago(shared, pds):
    """TD-416: the Memory page's purge; only entries deleted 30 days ago or earlier go."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    engine = MemoryEngine(folder)
    for title in ("Old lesson", "Old process", "Recent lesson"):
        entry = seed(folder, title, curated=True)
        if title == "Old process":  # hidden by the category filter below, but removed all the same
            entry = engine.edit(entry.id, {"categories": [MemoryCategory.PROCESS]}, expected_revision=entry.revision)
        approved = engine.approve(entry.id, entry.updated_at)
        engine.delete(entry.id, approved.updated_at)
    for title in ("Old lesson", "Old process"):
        old = next(p for p in folder.glob("*.md") if f"title: {title}" in p.read_text())
        stamp = next(e.updated_at for e in MemoryEngine(folder).get_entries() if e.title == title)
        old.write_text(old.read_text().replace(stamp, "2020-01-01T00:00:00+00:00"))
    with memory_page(store, pds) as page:
        pds.pick(page, "State", "any")
        pds.pick(page, "Category", "pitfall")
        deleted = page.locator("section", has_text="Deleted (history kept)")
        expect(deleted.locator(".entry")).to_have_count(2)
        deleted.get_by_role("button", name=f"Remove 2 deleted entries older than 30 days from {store.name}").click()
        expect(pds.modal(page).locator('p-button[variant="primary"]')).to_have_text(["Keep them"])  # never removing
        pds.answer(page, "Remove them")
        expect(page.locator("#status")).to_contain_text(f"Removed 2 deleted entries from {store.name}.")
        expect(deleted.locator(".entry")).to_have_count(1)
    assert [e.title for e in MemoryEngine(folder).get_entries()] == ["Recent lesson"]


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


@pytest.mark.browser
def test_a_filter_whose_choice_vanished_shows_everything_again(shared, pds):
    """Sol, TD-264: the filter falls back to Any before the list is computed, so the count and list agree."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    builder = seed(folder, "Run ruff first", curated=True)
    seed(folder, "Ask before merging", agent="shaper")
    with memory_page(store, pds) as page:
        pds.pick(page, "Agent", "builder")
        expect(page.locator("#shown")).to_have_text("1 of 2 shown")
        engine = MemoryEngine(folder)
        now = next(e for e in engine.get_entries() if e.id == builder.id)
        engine.edit(builder.id, {"scope_agents": ["reviewer"]}, expected_revision=now.revision)
        refreshed(page)
        expect(pds.select(page, "Agent")).to_have_js_property("value", "any")
        expect(page.locator("#shown")).to_have_text("2 of 2 shown")
        expect(page.locator(".entry")).to_have_count(2)


def test_a_moved_entry_refuses_the_page_that_showed_it_before_and_one_too_large_with_its_origin(shared, monkeypatch):
    """Copilot on #585: each move is a change, so replaying an older request is stale; an oversized entry is a 422."""
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry, big = seed(folder, "Pin the runtime", curated=True), seed(folder, "Too large", curated=True)
    c = client(store)
    made = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()["entry"]
    c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": made["updated_at"]})
    replayed = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})

    def too_large(*_a, **_k):
        too = "serialized entry exceeds 8192 bytes"
        raise ValueError(too)

    monkeypatch.setattr(memory_routes.storage, "write_entry", too_large)
    refused = c.post(f"/api/next/memory/{big.id}/make-global", json={"updated_at": big.updated_at})

    assert (replayed.status_code, refused.status_code, "8192" in refused.json()["detail"]) == (409, 422, True)
    assert sorted(e.id for e in MemoryEngine(folder).get_entries()) == sorted([entry.id, big.id])


def test_a_move_back_whose_write_at_home_fails_stays_global_with_its_origin(shared, monkeypatch):
    """CodeRabbit on #585: the origin is cleared only at home, so Global never keeps an entry without it."""
    root, _, repo = shared
    store = Store.open(repo)
    folder, common = root / store.name / "memory", root / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    c = client(store)
    made = c.post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at}).json()["entry"]
    real = memory_routes.storage.write_entry

    def failing(path, written, *, memory_dir):
        if memory_dir == folder:
            raise OSError(28, "No space left on device")
        return real(path, written, memory_dir=memory_dir)

    monkeypatch.setattr(memory_routes.storage, "write_entry", failing)
    failed = c.post(f"/api/next/memory/{entry.id}/move-back", json={"updated_at": made["updated_at"]})

    assert (failed.status_code, MemoryEngine(common).get_entry(entry.id).origin) == (409, store.name)
    assert MemoryEngine(folder).get_entries() == []
