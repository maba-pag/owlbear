"""The design pack update's questions on the Settings page in a real browser (TD-193, TD-220, TD-256)."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next import api, pack_job, pack_rounds
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.round_records import PACK, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

NOW = datetime(2026, 10, 17, 2, tzinfo=UTC)


class Host:
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106


def waiting(store: Store, lp: RoundLoop | None = None) -> pack_job.Job:
    """A run waiting for the owner; by default on two findings the challenger upheld against the updater."""
    found = [
        RoundFinding(id=f"F{i}", text=f"owlbear-design-review: glow {i} - fix: say so", raised=1, state="escalated",
                     reason="upstream dropped it", judgement="upstream still names it")
        for i in (1, 2)
    ]  # fmt: skip
    lp = lp or RoundLoop(subject=PACK, policy=RoundPolicy(), round=2, findings=found)
    job = pack_job.Job(store, pack_job.Live())
    context = {
        "tag": "skill-v4.6.0", "why": "design pack", "diff": "", "golden": "as expected", "pins": {},
        "manifest": "{}", "notice": "", "baseline": {}, "checkout": {}, "start": {}, "sid": "pack-update-1",
        "next": "wait",
    }  # fmt: skip
    job.state = pack_job._blank() | {  # noqa: SLF001 - a run as the job leaves it waiting
        "state": "waiting", "started_at": NOW.isoformat(), "run": "r1", "loop": lp.model_dump(mode="json"),
        "questions": pack_rounds.questions(lp, "r1", "x"), "context": context,
    }  # fmt: skip
    job._save()  # noqa: SLF001
    return job


@pytest.fixture
def served(tmp_path: Path) -> Iterator[Callable[[RoundLoop | None], tuple[pack_job.Job, str]]]:
    servers = []

    def serve(lp: RoundLoop | None = None) -> tuple[pack_job.Job, str]:
        job = waiting(Store(tmp_path), lp)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(api.create_app(job.store, "tok", Host(), pack=job), log_level="warning"))
        threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
        while not server.started:
            time.sleep(0.05)
        servers.append(server)
        return job, f"http://127.0.0.1:{sock.getsockname()[1]}"

    yield serve
    for server in servers:
        server.should_exit = True


@contextlib.contextmanager
def opened(base: str) -> Iterator[Any]:
    """The Settings page in a real browser, offline: only the test host answers, so the plain controls show."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/config")
        yield page
        browser.close()


@pytest.mark.browser
def test_the_owner_answers_each_upheld_finding_with_his_note_on_the_settings_page(served) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    with opened(base) as page:
        ask = page.locator("#pack-ask")
        expect(ask).to_be_visible()
        state = page.locator("#pack-state")
        expect(state).to_contain_text("The update waits for your answers below. Started ")
        expect(state).not_to_contain_text("ended")
        expect(page.get_by_role("button", name="Update design pack")).to_be_disabled()
        first, second = ask.locator(".pack-question").first, ask.locator(".pack-question").last
        expect(first).to_contain_text("Updater: upstream dropped it Challenger: upstream still names it")
        first.get_by_role("button", name="Ask the challenger to reconsider").click()
        expect(page.locator("#error")).to_have_text("Asking the challenger to reconsider needs your note")
        second.get_by_label("Your note", exact=False).fill("a draft for F2")
        first.get_by_label("Your note", exact=False).fill("the halo is upstream's own example")
        first.get_by_role("button", name="Drop it").click()
        left = ask.locator(".pack-question")
        expect(left).to_have_count(1)  # the other finding still waits; nothing ran yet
        expect(left.get_by_label("Your note", exact=False)).to_have_value("a draft for F2")  # its draft is kept
        expect(page.locator("#pack-findings li").first).to_contain_text("F1 (round 1), you dropped it")
    kept = RoundLoop.model_validate(job.read()["loop"])
    assert [(f.id, f.state, f.note) for f in kept.findings] == [
        ("F1", "owner-drop", "the halo is upstream's own example"), ("F2", "escalated", "")
    ]  # fmt: skip
    assert job.read()["state"] == "waiting"


@pytest.mark.browser
def test_the_activation_dialog_lists_the_unreviewed_repair_and_what_was_not_changed_for(served) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    found = [
        RoundFinding(id="F1", text="a: b - fix: c", raised=1, state="fixed", repair="r1"),
        RoundFinding(id="F2", text="d: e - fix: f", raised=1, state="standing", reason="it holds"),
    ]
    lp = RoundLoop(subject=PACK, policy=RoundPolicy(), round=1, findings=found, unreviewed=["r1"], ended="count")
    job, base = served(lp)
    with opened(base) as page:
        expect(page.locator("#pack-ask")).to_contain_text("The updater's last repair (r1) was not reviewed")
        page.get_by_role("button", name="Activate the unreviewed repair").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_contain_text("Repair r1: no challenger reviewed it.")
        expect(dialog).to_contain_text("F2 not changed for (rejected by the updater; the challenger accepted that)")
        dialog.get_by_role("button", name="Keep it waiting").click()
        expect(dialog).to_be_hidden()
    assert job.read()["state"] == "waiting"  # declining activates nothing
