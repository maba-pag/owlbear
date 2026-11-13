"""The held maintenance session is released only after the owner confirms a reboot, by its captured identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from tests.maintenance_page import opened

from owlbear_delivery_next.improvement import case_edits, cases
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.runtimes import spotter_look

if TYPE_CHECKING:
    from pathlib import Path

HELD = {
    "sessions": [
        {
            "id": "s-1",
            "project": "p",
            "kind": "pack",
            "started_at": "2026-10-25T00:00:00+00:00",
            "workspace": "/w/s-1",
            "reason": "no Run returned",
            "state": "held",
            "recoverable": True,
        },
    ],
}


EMPTY = {"sessions": []}


@pytest.mark.browser
@pytest.mark.parametrize("still_held", [True, False], ids=["row-kept", "row-dropped"])
def test_a_held_session_is_released_only_after_a_confirmed_reboot_by_its_captured_id(
    tmp_path: Path, pds, *, still_held: bool
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with opened(tmp_path, pds) as (page, base):
        posted: list[tuple[str, str | None]] = []

        def sessions(route) -> None:
            if route.request.method == "POST":
                posted.append((route.request.url, route.request.post_data))
                route.fulfill(status=409, json={"detail": "this maintenance session is no longer held"})
                return
            route.fulfill(json=HELD if still_held or not posted else EMPTY)

        page.route("**/maintenance/sessions**", sessions)
        page.goto(f"{base}/maintenance#token=tok")
        expect(page.locator("#sessions > li")).to_have_count(1)
        release = page.get_by_role("button", name="Release this session")
        expect(release).to_be_disabled()
        page.get_by_label("The computer has rebooted since this session failed").check()
        expect(release).to_be_enabled()
        release.click()
        page.get_by_role("button", name="Release", exact=True).click()
        expect(page.get_by_text("no longer held")).to_be_visible()
        assert len(posted) == 1
        url, body = posted[0]
        assert url.endswith("/maintenance/sessions/s-1/recover")
        assert body is not None
        assert '"rebooted":true' in body.replace(" ", "")


class Stuck:
    """A session's runtime that neither stops nor can be forced to."""

    async def stop(self) -> None:
        msg = "the runtime does not answer"
        raise RuntimeError(msg)

    force_stop = stop


@pytest.mark.browser
def test_a_held_session_shows_its_whole_reason(tmp_path: Path, monkeypatch, pds, whole_error) -> None:
    names = whole_error.splitlines()  # the sessions whose end was not confirmed: far over 300 characters together

    async def asked(_text: str, _meter: object, _role: object) -> str:
        for name in names:
            await spotter_look.teardown(Stuck(), None, name)
        return "{}"

    monkeypatch.setattr(cases_job, "limits", lambda: {"replay": 10.0, "retro": 5.0, "look": 1.0})
    monkeypatch.setattr(cases_job, "role", lambda _name: cases_job.RoleModel(model="m", effort="medium"))
    said: list[str] = []
    slots = Slots(lambda: 1)
    slots.open()
    job = cases_job.CasesJob(slots, asked=asked, shared=lambda: None, say=said.append)
    cid = cases.freeze({"intent": {"task": "t"}}, {"source": "pilot", "family": "f"})
    entry = {"stage": "candidate", "call": "none", "why": "why", "example": "", "review": None}
    cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
    case_edits.check_request([cid], "t")
    job.tick(0.0)
    reason = f"the end of Spotter cases sessions was not confirmed: {', '.join(names)}"
    assert said == [f"Spotter cases: {reason}; the job waits until Maintenance recovers it"]

    with opened(tmp_path, pds) as (page, base):
        page.route("**/maintenance/sessions**", lambda route: route.fulfill(json=job.maintenance.read()))
        page.goto(f"{base}/maintenance#token=tok")
        shown = page.locator("#sessions > li p-text", has_text="The end of Spotter cases")
        shown.wait_for()
        assert shown.evaluate("e => e.textContent") == f"T{reason[1:]}."
