"""The Maintenance page rendered by lit-html in a real browser (TD-264)."""

from __future__ import annotations

import socket
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.models import Brief, Change, StepKind
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import codebase, data_place, local_home
from owlbear_delivery_next.machine_host import app, curation, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import api, pack_routes
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.store import Lock, Store

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.browser
def test_the_maintenance_page_lists_each_action_and_says_when_delivery_stops(tmp_path: Path, pds) -> None:
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    store = Store(tmp_path)
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", None), log_level="warning"))
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
            page.goto(f"{base}/maintenance#token=tok")
            actions = page.locator("#actions > li")
            expect(actions).to_have_count(5)
            expect(actions.nth(1)).to_contain_text("Impeccable update")
            expect(page.get_by_role("link", name="Open Memory curation in Memory")).to_have_attribute("href", "/memory")
            expect(actions.nth(2)).to_contain_text("No run record kept.")
            expect(page.locator("#use-none")).to_have_text("No step has run in this project yet.")
            store.write(Lock("a"), Change(slug="a", brief=Brief(version=1)))
            ran = [{"agent": "explore", "credits": 1.25, "credits_known": True}]
            store.log(Lock("a"), "a", {"event": "step", "session": "s1", "kind": "build", "subagents": ran})
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#use p-table-cell")).to_have_text(["builder", "1", "1", "1", "1.25", "explore 1"])
            expect(page.locator("#error")).to_be_hidden()
            assert page.evaluate("location.hash") == ""  # the token left the address bar
            held = []  # what Delivery takes but never answers: up, yet busy

            def hold(route) -> None:
                held.append(route)

            page.route("**/api/next/maintenance/subagents", hold)
            page.route("**/api/next/project", lambda r: r.abort("connectionrefused"))
            caught = page.evaluate("""async () => {
              const ui = await import("/assets/ui.mjs"), caught = [];
              for (const [path, method] of [["/maintenance/subagents", "GET"], ["/maintenance/subagents", "POST"],
                ["/project", "GET"]]) {
                await ui.call(path, { method, timeout: 200 }).catch((e) => caught.push({ slow: e instanceof ui.Slow,
                  down: e instanceof ui.HostDown, sent: e.sent ?? null, said: e.message }));
              }
              return caught;
            }""")
            unsure = "Delivery did not answer within 0.2 s, so this may have been done or not. It was not sent again;"
            assert caught == [
                {"slow": True, "down": False, "sent": False,
                 "said": "Delivery is slow to answer: no reply within 0.2 s. Try again in a moment."},
                {"slow": True, "down": False, "sent": True,
                 "said": f"{unsure} reload the page to see which before you try again."},
                {"slow": False, "down": True, "sent": None,
                 "said": "Delivery is not running. Start it, then reload this page."},
            ]  # fmt: skip
            assert [r.request.method for r in held].count("POST") == 1  # a timed-out write is never sent again
            page.route("**/api/next/**", lambda r: r.abort())
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator("#error")).to_have_text("Delivery is not running. Start it, then reload this page.")
            expect(actions).to_have_count(5)  # what it showed stays
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_memory_curation_says_whether_its_last_run_was_the_curator_or_the_owner(tmp_path: Path, pds) -> None:
    """N1 (D-01M63CF1XKCCF6TP60734BTMWD): it said "Never run." after a curation run, and never said who ran it."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    ran = datetime.now(UTC) - timedelta(hours=1)
    run = curation.FolderRun(state="done", started_at=ran - timedelta(minutes=1), ended_at=ran)
    (local_home.root() / curation.STATE).write_text(curation.Runs(folders={"shop": run}).model_dump_json())
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    # longer than the pages' polls: route.fetch() reuses a pooled socket, which uvicorn's 5 s default closes
    server = uvicorn.Server(
        uvicorn.Config(
            api.create_app(Store(tmp_path, name="shop"), "tok", None), log_level="warning", timeout_keep_alive=60
        )
    )
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
            page.goto(f"{base}/maintenance#token=tok")
            memory = page.locator("#actions > li", has_text="Memory curation")
            expect(memory).to_contain_text("Last run (memory curator): done, ")
            expect(memory).not_to_contain_text("Never run.")
            action = {"by": "owner", "state": "done", "action": "approve Run ruff first", "ended_at": ran.isoformat()}

            def owned(route) -> None:
                body = route.fetch().json()
                route.fulfill(json=[a | {"last": action} if a["name"] == "Memory curation" else a for a in body])

            page.route("**/api/next/maintenance", owned)
            page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
            expect(memory).to_contain_text("Last run (your memory action): approve Run ruff first, ")
            expect(memory).not_to_contain_text("memory curator")
            browser.close()
    finally:
        server.should_exit = True


@pytest.mark.browser
def test_unreadable_curation_runs_show_whole_on_memory_curation(tmp_path: Path, pds, monkeypatch, whole_error) -> None:
    """#971: why memory curation's runs are not counted shows whole under its last run."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    run = curation.FolderRun(state="done", started_at=datetime.now(UTC), ended_at=datetime.now(UTC))
    (local_home.root() / curation.STATE).write_text(curation.Runs(folders={"shop": run}).model_dump_json())
    error = ValueError(whole_error)
    error.add_note("a note added on the way up")

    def unreadable(_text: str):
        raise error

    monkeypatch.setattr(pack_routes.curation_runs.Runs, "model_validate_json", unreadable)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(
        uvicorn.Config(api.create_app(Store(tmp_path, name="shop"), "tok", None), log_level="warning")
    )
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
            page.goto(f"{base}/maintenance#token=tok")
            reason = page.locator("#actions > li", has_text="Memory curation").locator("p-text[size='xs']")
            expect(reason).to_have_count(1)
            assert reason.text_content() == (
                "memory curation's runs could not be read, so they are not counted: "
                f"ValueError: {whole_error}\na note added on the way up"
            )
            browser.close()
    finally:
        server.should_exit = True


@pytest.fixture
def owner_history_page(tmp_path: Path, pds, shared_repo, monkeypatch, whole_error):
    from playwright.sync_api import sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setenv(data_place.VIEW, str(shared_repo[0]))
    monkeypatch.setattr(project.readiness, "ready", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda *_args: False)
    work = tmp_path / "shop"
    for args in (
        ["init", "-q", "-b", "main", str(work)],
        ["-C", str(work), "commit", "-q", "--allow-empty", "-m", "start"],
    ):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    entry = registry.register(work)
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    machine.load_all()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    error = subprocess.TimeoutExpired(["git", "log"], 10, output=whole_error.encode(), stderr=b"owner history stderr")
    error.add_note("owner history note")
    real = subprocess.run

    def history(args, **kwargs):
        if args[:2] == ["git", "log"]:
            raise error
        return real(args, **kwargs)

    monkeypatch.setattr(pack_routes.subprocess, "run", history)
    notice = f"the owner's memory history could not be read, so it is not counted: {failure(error)}"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            said = []
            page.on("pageerror", lambda e: said.append(str(e)))
            page.on("console", lambda m: said.append(m.text) if m.type == "error" else None)
            pds.only(page, base)
            yield page, base, entry.id, notice
            assert said == []
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


@pytest.mark.browser
@pytest.mark.parametrize("scope", ["project", "all"])
def test_owner_history_qualifies_every_curation_state_in_both_maintenance_views(
    owner_history_page, tmp_path: Path, monkeypatch, scope
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    page, base, pid, notice = owner_history_page
    path = f"/maintenance?project={pid}" if scope == "project" else "/maintenance"
    curation_error = ValueError("the curation history is unreadable too")
    curation_error.add_note("curation history note")

    def unreadable(_name):
        raise curation_error

    for state in ("running", "failed", "done", "unknown"):
        reason = "the curator's result stays intact\nwith its detail"
        if state == "unknown":
            monkeypatch.setattr(pack_routes, "curation_last", unreadable)
        else:
            run = curation.FolderRun(state=state, started_at=datetime.now(UTC), reason=reason)
            (local_home.root() / curation.STATE).write_text(curation.Runs(folders={"shop": run}).model_dump_json())
        if state == "running":
            page.goto(f"{base}{path}#token=tok")
        else:
            page.reload()
        surface = (
            page.locator("#actions > li", has_text="Memory curation")
            if scope == "project"
            else (page.locator(f'#projects .scope[data-key="{pid}"] .runs > li', has_text="Memory curation"))
        )
        expect(surface).to_contain_text("Memory curation")
        if state != "unknown":
            expect(surface).to_contain_text(f"(memory curator): {state}, ")
        page.screenshot(path=str(tmp_path / f"maintenance-{scope}-{state}.png"), full_page=True)
        expect(surface).to_contain_text(notice)
        assert notice in surface.text_content()
        expect(surface).not_to_contain_text("never run")
        expect(surface).not_to_contain_text("Never run")
        if state == "unknown":
            assert f"ValueError: {curation_error}\ncuration history note" in surface.text_content()
        elif scope == "project" or state == "done":
            assert reason in surface.text_content()
        else:
            expect(surface).not_to_contain_text(reason)  # tagged runs' detail stays on the project page


@pytest.mark.browser
def test_the_test_review_starts_from_the_chosen_packages_once_confirmed(tmp_path: Path, pds) -> None:
    """TD-370, TD-390: every package is chosen, the dialog says what runs, and the Start opens one Change."""
    from playwright.sync_api import Error, expect, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    work = tmp_path / "work"
    for name in ("pyproject.toml", "tests/test_a.py", "web/package.json", "web/src/b.test.ts"):
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        (work / name).write_text("x\n")
    who = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run([*who, *args], cwd=work, check=True, capture_output=True)  # noqa: S603
    store = Store.open(work)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(api.create_app(store, "tok", Host(store, work)), log_level="warning"))
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
            page.goto(f"{base}/maintenance#token=tok")
            tests = page.locator("#tests")
            expect(tests.get_by_role("checkbox")).to_have_count(2)
            expect(page.locator("#tests-runs")).to_contain_text("2 reviewer sessions on gpt-6.1-sol at medium effort")
            tests.get_by_label("the repository's root: 1 files, 1 lines, 1 share").uncheck()
            expect(page.locator("#tests-runs")).to_contain_text("1 reviewer session on")
            page.get_by_role("button", name="Review tests").click()
            expect(page.get_by_role("dialog", name="Review the tests?")).to_be_visible()
            expect(pds.modal(page)).to_contain_text("which your Start approves")
            pds.answer(page, "Cancel")
            expect(page.get_by_role("dialog")).to_be_hidden()
            assert store.slugs() == []  # declined: nothing starts
            page.get_by_role("button", name="Review tests").click()
            pds.answer(page, "Start the test review")
            expect(page.locator("#status")).to_contain_text("Started test review c1")
            expect(tests).to_contain_text("Test review c1 has not finished")
            c = store.read(store.slugs()[0])
            assert (c.step.kind, c.tests.packages) == (StepKind.TESTS, ["web"])
            browser.close()
    finally:
        server.should_exit = True
