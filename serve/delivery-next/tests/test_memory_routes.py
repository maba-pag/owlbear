import contextlib
import json
import subprocess
import threading
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from owlbear_memory import MemoryBusyError, MemoryCategory, MemoryEngine

from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Store

AUTH = {"authorization": "Bearer t"}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def git(cwd: Path, *args: str) -> str:
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


def test_make_global_refuses_an_entry_global_memory_already_holds(shared):
    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    entry = seed(folder, "Pin the runtime", curated=True)
    (root / "memory").mkdir()
    (root / "memory" / "copy.md").write_bytes((folder / f"{entry.id}.md").read_bytes())

    refused = client(store).post(f"/api/next/memory/{entry.id}/make-global", json={"updated_at": entry.updated_at})

    assert (refused.status_code, "already" in refused.json()["detail"]) == (409, True)
    assert (folder / f"{entry.id}.md").is_file()


def attempt(engine: MemoryEngine, entry) -> type[Exception] | None:
    try:
        engine.edit(entry.id, {"title": "an agent's edit"}, expected_revision=entry.revision)
    except Exception as exc:  # noqa: BLE001 - the test reports what the agent met
        return type(exc)
    return None


@contextlib.contextmanager
def memory_page(store: Store) -> Iterator[Any]:
    """The Memory page in a real browser, offline: only the test host answers, so the plain controls show."""
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
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
            page.goto(f"{base}/memory#token=tok")
            yield page
            browser.close()
    finally:
        server.should_exit = True


def refreshed(page: Any) -> None:
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")


@pytest.mark.browser
def test_a_memory_edit_survives_the_entries_before_it_disappearing_and_is_saved(shared):
    """TD-264: the draft lives in page state, so a filter that removes the cards above it keeps what was typed."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    engine = MemoryEngine(folder)
    above = seed(folder, "Name the release", agent="shaper")
    engine.edit(above.id, {"categories": [MemoryCategory.PROCESS]}, expected_revision=above.revision)
    seed(folder, "Ask before merging", agent="shaper")  # newer, so listed above it in the same group
    with memory_page(store) as page:
        expect(page.locator("#shown")).to_have_text("2 of 2 shown")
        waiting = page.locator("section", has_text="Waiting for the curator").locator(".entry")
        expect(waiting).to_have_count(2)
        expect(waiting.first).to_contain_text("Ask before merging")
        page.locator(".entry", has_text="Name the release").get_by_role("button", name="Edit").click()
        page.get_by_label("Title").fill("Name the release after its tag")
        page.get_by_label("Category").select_option("process")  # the card above it leaves the page
        expect(page.locator("#shown")).to_have_text("1 of 2 shown")
        expect(page.get_by_label("Title")).to_have_value("Name the release after its tag")
        page.get_by_role("button", name="Save").click()
        expect(page.locator("#status")).to_have_text('Saved "Name the release after its tag".')
    assert {e.id: e.title for e in MemoryEngine(folder).get_entries()}[above.id] == "Name the release after its tag"


@pytest.mark.browser
def test_approving_one_memory_leaves_the_next_ones_button_ready(shared):
    """Sol, TD-264: a finished action's busy state never moves to the card that takes its place."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    seed(folder, "Run ruff first", curated=True)
    seed(folder, "Pin the runtime", curated=True)
    with memory_page(store) as page:
        review = page.locator("section", has_text="Needs your review")
        expect(review.locator(".entry")).to_have_count(2)
        review.locator(".entry").first.get_by_role("button", name="Approve").click()
        expect(review.locator(".entry")).to_have_count(1)
        expect(review.get_by_role("button", name="Approve")).to_be_enabled()


@pytest.mark.browser
def test_a_filter_whose_choice_vanished_shows_everything_again(shared):
    """Sol, TD-264: the filter falls back to Any before the list is computed, so the count and list agree."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    root, _, repo = shared
    store = Store.open(repo)
    folder = root / store.name / "memory"
    builder = seed(folder, "Run ruff first", curated=True)
    seed(folder, "Ask before merging", agent="shaper")
    with memory_page(store) as page:
        page.get_by_label("Agent").select_option("builder")
        expect(page.locator("#shown")).to_have_text("1 of 2 shown")
        engine = MemoryEngine(folder)
        now = next(e for e in engine.get_entries() if e.id == builder.id)
        engine.edit(builder.id, {"scope_agents": ["reviewer"]}, expected_revision=now.revision)
        refreshed(page)
        expect(page.get_by_label("Agent")).to_have_value("any")
        expect(page.locator("#shown")).to_have_text("2 of 2 shown")
        expect(page.locator(".entry")).to_have_count(2)
