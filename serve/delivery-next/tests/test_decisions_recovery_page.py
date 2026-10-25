"""The interrupted decision batch on the Decisions page: reachable while the list is blocked, finished or
abandoned by its generation after the owner's confirmation, refused when stale, and diagnosed without any
action when the journal is corrupt (DEC-01). Synthetic journal and provider only."""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_batch, decision_recovery
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

PROJECT = "shop-site"
AT = datetime(2026, 10, 21, 9, tzinfo=UTC)


class Host:
    wake = SimpleNamespace(set=lambda: None)
    repo = None  # the impact report then says it cannot read the clone
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


CRASH_CODE = """
import os
from pathlib import Path
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import decision_actions, decision_store, decision_sync
shared = DataRepo(Path(os.environ["REPRO_DATA"]))
point = os.environ["REPRO_POINT"]
real_write = decision_store.write
def write(*args, **kwargs):
    if point == "before-first":
        os._exit(73)
    real_write(*args, **kwargs)
    if point == "after-first":
        os._exit(73)
decision_store.write = write
real_publish = decision_sync.publish
def publish(*args, **kwargs):
    sent = real_publish(*args, **kwargs)
    if point == "after-publish":
        os._exit(73)
    return sent
decision_sync.publish = publish
decision_actions.replace(
    shared, "shop-site", os.environ["REPRO_ID"], os.environ["REPRO_REV"],
    title="Notes store", statement="Notes live in Postgres.", rationale="",
    reason="SQLite no longer meets the requirement.", redecided=False,
)
"""


def _seed(picking: Any) -> Decision:
    old = picking.put(make(statement="Notes live in SQLite."))
    picking.shared.git("add", "-A")
    picking.shared.git("commit", "-qm", "seed")
    picking.shared.git("push", "-q")
    return old


def _crash(picking: Any, old: Decision, point: str) -> None:
    env = os.environ | {
        "REPRO_DATA": str(picking.shared.root),
        "REPRO_ID": old.id,
        "REPRO_REV": old.revision,
        "REPRO_POINT": point,
    }
    process = subprocess.run(  # noqa: S603 - fixed interpreter and code string, no untrusted input
        [sys.executable, "-c", CRASH_CODE], env=env, capture_output=True, text=True, check=False
    )
    assert process.returncode == 73, process.stderr


@contextlib.contextmanager
def decisions_page(store: Store, pds: Any) -> Iterator[Any]:
    """The Decisions page in a real browser: only the test host and the PDS CDN answer."""
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
            page.goto(f"{base}/decisions#token=tok")
            yield page
            browser.close()
    finally:
        server.should_exit = True


def _interrupt(picking: Any) -> tuple[Any, str]:
    """A batch interrupted after its first write: its seeded decision and its generation."""
    old = _seed(picking)
    _crash(picking, old, "after-first")
    return old, decision_batch.pending(picking.shared).generation


def _store(picking: Any, tmp_path: Path) -> Store:
    return Store(tmp_path / "store", picking.shared, PROJECT)


def test_recovery_is_served_while_the_decision_list_is_blocked(picking, tmp_path):
    _, generation = _interrupt(picking)
    client = TestClient(
        api.create_app(_store(picking, tmp_path), "tok", Host()),
        base_url="http://127.0.0.1",
        headers={"authorization": "Bearer tok"},
    )
    assert client.get("/api/next/decisions").json()["available"] is False
    shown = client.get("/api/next/decisions/recovery").json()
    assert shown["interrupted"]
    assert shown["generation"] == generation
    assert shown["project"] == PROJECT


@pytest.mark.browser
def test_the_interrupted_batch_is_reachable_while_the_list_is_blocked(picking, tmp_path, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _, generation = _interrupt(picking)
    with decisions_page(_store(picking, tmp_path), pds) as page:
        expect(page.locator("#recovery")).to_be_visible()
        expect(page.locator(".recovery-project")).to_have_text(PROJECT)
        expect(page.locator(".recovery-generation")).to_have_text(generation)
        expect(page.locator("#unavailable")).to_be_visible()
        expect(page.get_by_role("button", name="Finish batch")).to_be_visible()
        expect(page.get_by_role("button", name="Abandon batch")).to_be_visible()


@pytest.mark.browser
def test_finish_publishes_only_after_the_owner_confirms_the_generation(picking, tmp_path, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _, generation = _interrupt(picking)
    with decisions_page(_store(picking, tmp_path), pds) as page:
        expect(page.locator(".recovery-generation")).to_have_text(generation)
        page.get_by_role("button", name="Finish batch").click()
        dialog = pds.modal(page)
        expect(dialog).to_contain_text("Finish the interrupted decision batch?")
        expect(dialog).to_contain_text("Nothing in Git or the index is undone.")
        with page.expect_request(lambda r: "/decisions/recovery/finish" in r.url) as sent:
            dialog.get_by_role("button", name="Finish").click()
        assert sent.value.post_data_json["generation"] == generation
        assert sent.value.post_data_json["confirmed"] is True
        expect(page.locator("#recovery-notice")).to_contain_text(f"Finished batch {generation}")
        expect(page.locator("#recovery")).to_have_count(0)
        expect(page.locator("#unavailable")).to_be_hidden()
    assert decision_batch.pending(picking.shared) is None


@pytest.mark.browser
def test_cancel_keeps_the_batch_and_abandon_is_confirmed_by_its_generation(picking, tmp_path, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _, generation = _interrupt(picking)
    with decisions_page(_store(picking, tmp_path), pds) as page:
        expect(page.locator(".recovery-generation")).to_have_text(generation)
        page.get_by_role("button", name="Abandon batch").click()
        pds.modal(page).get_by_role("button", name="Cancel").click()
        expect(page.locator(".recovery-generation")).to_have_text(generation)
        assert decision_batch.pending(picking.shared).generation == generation

        page.get_by_role("button", name="Abandon batch").click()
        with page.expect_request(lambda r: "/decisions/recovery/abandon" in r.url) as sent:
            pds.modal(page).get_by_role("button", name="Abandon").click()
        assert sent.value.post_data_json["generation"] == generation
        expect(page.locator("#recovery-notice")).to_contain_text(f"Abandoned batch {generation}")
        expect(page.locator("#recovery")).to_have_count(0)
    assert decision_batch.pending(picking.shared) is None


@pytest.mark.browser
def test_a_stale_answer_is_refused_and_leaves_the_newer_batch_interrupted(picking, tmp_path, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    old, old_generation = _interrupt(picking)
    with decisions_page(_store(picking, tmp_path), pds) as page:
        expect(page.locator(".recovery-generation")).to_have_text(old_generation)
        # Meanwhile the owner's batch is abandoned elsewhere and another one is interrupted.
        decision_recovery.abandon(picking.shared, old_generation)
        _crash(picking, old, "after-first")
        new_generation = decision_batch.pending(picking.shared).generation
        assert new_generation != old_generation

        page.get_by_role("button", name="Finish batch").click()
        with page.expect_request(lambda r: "/decisions/recovery/finish" in r.url) as sent:
            pds.modal(page).get_by_role("button", name="Finish").click()
        assert sent.value.post_data_json["generation"] == old_generation
        expect(page.locator("#recovery-error")).to_be_visible()
        expect(page.locator("#recovery-notice")).to_have_count(0)
        expect(page.locator(".recovery-generation")).to_have_text(new_generation)
    assert decision_batch.pending(picking.shared).generation == new_generation


@pytest.mark.browser
def test_a_corrupt_journal_is_diagnosed_and_offers_no_action(picking, tmp_path, pds):
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _interrupt(picking)
    journal = decision_batch.journal_path(picking.shared)
    journal.write_text("{not json")
    with decisions_page(_store(picking, tmp_path), pds) as page:
        expect(page.locator("#recovery-corrupt")).to_be_visible()
        expect(page.get_by_role("button", name="Finish batch")).to_have_count(0)
        expect(page.get_by_role("button", name="Abandon batch")).to_have_count(0)
    assert journal.read_text() == "{not json"
