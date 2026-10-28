"""The design pack update in Maintenance's OwlBear section in a real browser (TD-193, TD-220, TD-256)."""

from __future__ import annotations

import contextlib
import os
import re
import socket
import threading
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

from owlbear_delivery_next.change_contracts.round_records import PACK, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.pack_runs import machine_lock, pack_gates, pack_job, pack_progress, pack_rounds, pack_state
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

NOW = datetime(2026, 10, 17, 2, tzinfo=UTC)


class Host:
    maintenance = None
    wake = type("W", (), {"set": staticmethod(lambda: None)})()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106
    paused = staticmethod(lambda: False)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()


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
def holding() -> Iterator[None]:
    """The machine's design pack lock, as a run's thread holds it while it runs; a running record without it is left."""
    fd = machine_lock.take(local_home.root() / pack_state.MACHINE_LOCK, "tests", lambda: None)
    try:
        yield
    finally:
        os.close(fd)


@contextlib.contextmanager
def opened(base: str, pds: Any) -> Iterator[Any]:
    """The Maintenance page in a real browser: only the test host and the PDS CDN answer."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        page.goto(f"{base}/maintenance")
        yield page
        browser.close()


@pytest.mark.browser
def test_the_owner_answers_each_upheld_finding_with_his_note_in_the_owlbear_section(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    with opened(base, pds) as page:
        ask = page.locator("#pack-ask")
        expect(ask).to_be_visible()
        state = page.locator("#pack-state")
        expect(state).to_contain_text("The update waits for your answers below. Started ")
        expect(state).not_to_contain_text("ended")
        expect(page.get_by_role("button", name="Update design pack")).to_be_disabled()
        first, second = ask.locator(".pack-question").first, ask.locator(".pack-question").last
        facts = first.locator(".pack-facts dd")  # from the finding's record, not the host's sentence
        expect(facts).to_have_text(["owlbear-design-review: glow 1 - fix: say so", "upstream dropped it",
                                    "upstream still names it"])  # fmt: skip
        expect(page.locator("#pack-todo")).to_have_text("Answer the 2 questions below.")
        sent: list[str] = []
        page.on("request", lambda r: sent.append(r.url) if r.url.endswith("/design-pack/update/answer") else None)
        first.get_by_role("button", name="Ask the challenger to reconsider").click()
        note = first.locator("p-textarea")
        expect(note).to_have_attribute("message", "Asking the challenger to reconsider needs your note.")
        assert page.evaluate("document.activeElement?.dataset.note") == "r1:dispute:F1"  # the note to give
        assert sent == []  # checked here, before anything is sent
        second.get_by_label("Your note", exact=False).fill("a draft for F2")
        first.get_by_label("Your note", exact=False).fill("the halo is upstream's own example")
        first.get_by_role("button", name="Drop it").click()
        left = ask.locator(".pack-question")
        expect(left).to_have_count(1)  # the other finding still waits; nothing ran yet
        expect(left.get_by_label("Your note", exact=False)).to_have_value("a draft for F2")  # its draft is kept
        expect(page.locator("#pack-findings li").first).to_contain_text("F1 (round 1), you dropped it")
    assert len(sent) == 1  # only the Drop it went out
    kept = RoundLoop.model_validate(job.read()["loop"])
    assert [(f.id, f.state, f.note) for f in kept.findings] == [
        ("F1", "owner-drop", "the halo is upstream's own example"), ("F2", "escalated", "")
    ]  # fmt: skip
    assert job.read()["state"] == "waiting"


@pytest.mark.browser
def test_the_activation_dialog_lists_the_unreviewed_repair_and_what_was_not_changed_for(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    found = [
        RoundFinding(id="F1", text="a: b - fix: c", raised=1, state="fixed", repair="r1"),
        RoundFinding(id="F2", text="d: e - fix: f", raised=1, state="standing", reason="it holds"),
    ]
    lp = RoundLoop(subject=PACK, policy=RoundPolicy(), round=1, findings=found, unreviewed=["r1"], ended="count")
    job, base = served(lp)
    with opened(base, pds) as page:
        expect(page.locator("#pack-ask")).to_contain_text("The updater's last repair (r1) was not reviewed")
        page.get_by_role("button", name="Activate the unreviewed repair").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        said = pds.modal(page)
        expect(said).to_contain_text("Repair r1: no challenger reviewed it.")
        expect(said).to_contain_text("F2 not changed for (rejected by the updater; the challenger accepted that)")
        said.get_by_role("button", name="Keep it waiting").click()
        expect(dialog).to_be_hidden()
    assert job.read()["state"] == "waiting"  # declining activates nothing


DIFF = "--- a/skills/x.md\n+++ b/skills/x.md\n@@ -1 +1 @@\n-old line\n+new line\n"
ENDED = RoundLoop(subject=PACK, policy=RoundPolicy(), round=1, unreviewed=["r1"], ended="count", findings=[
    RoundFinding(id="F1", text="a: b - fix: c", raised=1, state="fixed", repair="r1"),
    RoundFinding(id="F2", text="d: e - fix: f", raised=1, state="standing", reason="it holds"),
])  # fmt: skip
CI_FAILED = {
    "id": "r1-publish", "kind": "publish", "text": "CI failed on the pull request: unit tests. ",
    "options": [{"id": "retry", "label": "Try again"}, {"id": "repair", "label": "Have an agent fix CI"},
                {"id": "discard", "label": "Discard the update (the pull request stays open)"}],
}  # fmt: skip
PUBLISHED = {"commit": "c" * 40, "branch": "pack/r1", "url": "https://github.com/maba-pag/owlbear/pull/7",
             "number": 7, "merged": ""}  # fmt: skip
# Each stop: its loop, its questions (None: the loop's own), what else the run holds, its Discard, its primaries.
STOPS: dict[str, tuple[RoundLoop | None, list[dict[str, Any]] | None, dict[str, Any], str, list[str]]] = {
    "dispute": (None, None, {}, "Discard the update", []),
    "end": (ENDED, None, {}, "Discard the update", ["Activate the unreviewed repair"]),
    "evidence": (None, [pack_gates.evidence("r1", DIFF, "upstream renamed it", "as expected", "e" * 64)], {},
                 "Discard the update", []),
    "code": (None, [pack_gates.code("r1", DIFF, "c" * 64)], {}, "Discard the update", []),
    "publish": (None, [CI_FAILED], {"published": PUBLISHED}, "Discard the update (the pull request stays open)", []),
}  # fmt: skip


@pytest.mark.browser
@pytest.mark.parametrize("kind", list(STOPS))
def test_each_stop_offers_one_discard_apart_whose_cancel_changes_nothing(served, pds, kind) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    lp, questions, more, discard, primary = STOPS[kind]
    job, base = served(lp)
    if questions is not None:
        job.state |= {"questions": questions} | more
        job._save()  # noqa: SLF001
    before = (job.store.root / pack_job.FILE).read_bytes()
    with opened(base, pds) as page:
        expect(page.locator("#pack-ask").get_by_role("button", name=re.compile("Discard"))).to_have_count(1)
        expect(page.locator("#pack-discard")).to_have_text(discard)
        expect(page.locator("#pack-questions p-button[variant=primary]")).to_have_text(primary)  # none invented
        offered = [o["label"] for q in job.read()["questions"] for o in q["options"] if o["id"] != "discard"]
        expect(page.locator("#pack-questions p-button")).to_have_text(offered)  # each the payload offers, as it says
        page.locator("#pack-discard").click()
        expect(pds.modal(page)).to_contain_text("Nothing is activated")
        inside = "document.activeElement?.closest('p-modal') !== null"
        assert page.evaluate(inside)  # the focus moved into the dialog
        where = []
        for _ in range(6):  # the page behind is inert: Tab cycles the dialog and the browser's own controls only
            page.keyboard.press("Tab")
            where.append(page.evaluate(f"{inside} ? 'dialog' : document.activeElement === document.body ? '' : 'page'"))
        assert "page" not in where
        assert where[-1] == "dialog"
        pds.answer(page, "Keep it waiting")
        assert page.evaluate("document.activeElement?.id") == "pack-discard"  # back where it was
        expect(page.locator("#pack-ask")).to_be_visible()
        assert (job.store.root / pack_job.FILE).read_bytes() == before  # cancel changed nothing
        page.locator("#pack-discard").click()
        pds.answer(page, discard)
        expect(page.locator("#pack-state")).to_contain_text("discarded")
    assert job.read()["state"] == "discarded"


def history() -> list[dict[str, Any]]:
    """Two rounds on two candidates: the first round's evidence stale, the second's replay reused, the owner asked."""
    inv: list[dict[str, Any]] = []
    prepared = [("notice", "passed"), ("candidate", "passed"), ("diff", "passed"), ("initial-golden", "completed")]
    for op, result in prepared:
        pack_progress.closed(inv, pack_progress.opened(inv, op, op), result)
    for round_, identity, judged in [(1, "a", "findings"), (2, "b", "")]:
        update = pack_progress.opened(inv, "update", "update", round_=round_)
        pack_progress.closed(inv, update, "completed", "", identity)
        if judged:
            at = pack_progress.opened(inv, "challenger", "full-challenge", round_=round_, identity=identity)
            pack_progress.closed(inv, at, judged, "2 new finding(s)")
    pack_progress.opened(inv, "replay", "replay", identity="b", result="reused")
    pack_progress.asked(inv, "challenger", [{"kind": "dispute"}])
    return inv


@pytest.mark.browser
def test_the_update_shows_its_phases_with_each_invocation_in_order_and_what_comes_next(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    job.state["invocations"] = history()
    job._save()  # noqa: SLF001
    with opened(base, pds) as page:
        phases = page.locator("#pack-progress .pack-phase")
        expect(phases.locator("h5")).to_have_text(["Prepare", "Challenge round 1", "Challenge round 2"])
        expect(phases.nth(0).locator("li")).to_have_count(4)
        first, second = phases.nth(1).locator("li"), phases.nth(2).locator("li")
        expect(first).to_have_count(2)
        for i in range(2):  # the first candidate's evidence, superseded by the second's: out of date, never done
            expect(first.nth(i).locator(".pack-step-head p-tag")).to_have_text("out of date")
        expect(first.nth(1).locator(".pack-step-head")).to_have_text("Challenger on the whole pack out of date")
        expect(first.nth(1).locator("details")).not_to_have_attribute("open", "")  # its detail folded away
        expect(first.nth(1).locator("details")).to_contain_text("it said: findings")
        expect(second.locator(".pack-step-head")).to_have_text([
            "Updater session session completed", "Calibration replay reused for this identity",
            "Your answer waiting for you",
        ])  # fmt: skip
        expect(second.get_by_text("out of date")).to_have_count(0)
        options = "; ".join(pack_rounds.LABELS[o] for o in ("fix", "reconsider", "drop"))
        expect(page.locator("#pack-next")).to_have_text(f"Your answer decides what runs next ({options})")
        expect(page.locator("#pack-stages")).to_have_count(0)  # no slot per stage beside them
        job.state |= {"state": "running", "questions": []}
        pack_progress.opened(job.state["invocations"], "challenger", "full-challenge", round_=2, identity="b")
        job._save()  # noqa: SLF001
        with holding():
            page.reload()
            expect(page.locator("#pack-now")).to_have_text("Challenge round 2, Challenger on the whole pack…")
            expect(page.locator("#pack-next")).to_contain_text("Decided by the verdict")
            expect(page.locator("#pack-todo")).to_contain_text("Nothing for now")
            expect(page.locator("#pack-ask")).to_be_hidden()  # no Discard while it runs
        expect(page.locator("#pack-state")).to_contain_text("Its host stopped while it ran")  # and the polling ends


@pytest.mark.browser
def test_a_record_from_before_invocations_shows_its_stages_without_made_up_history(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _job, base = served()
    with opened(base, pds) as page:
        expect(page.locator("#pack-stages li")).to_have_count(len(pack_job.STAGES))
        expect(page.locator("#pack-progress")).to_have_count(0)
        expect(page.locator("#pack-next")).to_have_count(0)
        expect(page.locator("#pack-state")).to_contain_text("The update waits for your answers below.")


REPLAY_NONE = "0 decided rounds, 0 left out; the design judge agreed with the owner 0% as recorded, 0% with this pack"


@pytest.mark.browser
def test_a_ci_failed_publish_stop_fits_a_phone_and_says_no_calibration_evidence_instead_of_0(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    inv = history()
    replay = pack_progress.opened(inv, "replay", "replay", round_=2, identity="b")
    pack_progress.closed(inv, replay, "passed", REPLAY_NONE + " (advisory: too few rounds)")
    log = "\n".join(f"line {i}: " + "x" * 200 for i in range(3))
    pack_progress.closed(inv, pack_progress.opened(inv, "merge", "merge"), "failed", log)
    long_diff = DIFF + "+" + "y" * 400 + "\n"
    job.state |= {"invocations": inv, "questions": [CI_FAILED | {"diff": long_diff}], "published": PUBLISHED}
    job._save()  # noqa: SLF001
    with opened(base, pds) as page:
        page.set_viewport_size({"width": 375, "height": 800})
        expect(page.locator("#pack-questions p-button")).to_have_text(["Try again", "Have an agent fix CI"])
        expect(page.locator("#pack-pushed").get_by_role("link")).to_have_text("pull request #7")
        step = page.locator(".pack-step", has_text="Calibration replay").last
        expect(step.locator(".pack-step-head p-tag")).to_have_text("no calibration evidence")
        expect(step).not_to_contain_text("0%")
        ci = page.locator(".pack-step").last
        expect(ci.locator("pre.pack-detail")).to_be_hidden()  # a multi-line detail, folded until asked for
        ci.locator("summary").click()
        expect(ci.locator("pre.pack-detail")).to_be_visible()
        expect(page.locator(".pack-diff .pack-add").first).to_have_text("+new line")  # its markers kept
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        small = page.evaluate("""[...document.querySelectorAll('#owlbear p-button, #owlbear summary')]
            .filter((b) => b.offsetParent).map((b) => b.getBoundingClientRect()).filter((r) => r.height < 24
              || r.width < 24).length""")
        assert small == 0  # every target at least 24px


@pytest.mark.browser
def test_an_unreadable_section_says_what_could_not_be_read(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    _job, base = served()
    with opened(base, pds) as page:
        expect(page.locator("#pack-ask")).to_be_visible()
        page.route("**/maintenance/pack/runs", lambda r: r.fulfill(status=500, json={"detail": "the disk said no"}))
        page.route("**/maintenance/pack", lambda r: r.fulfill(status=500, json={"detail": "no pin today"}))
        page.reload()
        said = "Could not read the design pack runs: the disk said no"
        expect(page.locator("#pack-runs-error")).to_contain_text(said)
        expect(page.locator("#pack-read-error")).to_contain_text("Could not read the design pack: no pin today")
        expect(page.locator("#pack-run")).to_have_count(0)  # nothing made up in its place


@pytest.mark.browser
def test_a_merged_update_says_how_it_reaches_machines_and_a_new_one_stays_available(served, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    job.state |= {"state": "passed", "questions": [], "ended_at": NOW.isoformat(),
                  "published": PUBLISHED | {"merged": "m" * 40}}  # fmt: skip
    job._save()  # noqa: SLF001
    with opened(base, pds) as page:
        expect(page.locator("#pack-tag")).to_have_text("passed")
        expect(page.locator("#pack-todo")).to_contain_text("reaches each machine as it takes the OwlBear version")
        expect(page.locator("#pack-run")).not_to_contain_text("installed")  # nothing claimed of this machine
        expect(page.locator("#pack-pushed")).to_contain_text("merged into main as mmmmmmmmmmmm")
        expect(page.locator("#pack-update")).to_be_enabled()
        expect(page.locator("#pack-notice")).to_contain_text("Upstream:")
        expect(page.locator("#pack-ask")).to_be_hidden()
        job.state["state"] = "discarded"  # changed elsewhere: an ended run is still read again, with no reload
        job._save()  # noqa: SLF001
        expect(page.locator("#pack-state")).to_contain_text("Last run discarded", timeout=25000)


@pytest.mark.browser
def test_a_start_admitted_after_its_timeout_shows_its_run_without_a_reload_or_a_second_post(served, pds) -> None:
    """I1-3: admission may look up GitHub for longer than the start waits; the section keeps looking, never resends."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    job, base = served()
    job.state |= {"state": "passed", "questions": [], "ended_at": NOW.isoformat()}
    job._save()  # noqa: SLF001

    def slow_start() -> dict[str, Any]:
        time.sleep(12)  # beyond the page's 10 s: the pull request lookup before the run is kept
        job.state = pack_job._blank() | {"state": "waiting", "run": "r2", "started_at": datetime.now(UTC).isoformat(),  # noqa: SLF001
                                         "questions": [CI_FAILED | {"id": "r2-publish"}]}  # fmt: skip
        job._save()  # noqa: SLF001
        return job.read()

    job.start = slow_start
    with opened(base, pds) as page:
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        expect(page.locator("#pack-tag")).to_have_text("passed")
        page.get_by_role("button", name="Update design pack").click()
        pds.answer(page, "Update")
        expect(page.locator("#pack-admitting")).to_contain_text("It was not sent again", timeout=15000)
        expect(page.locator("#pack-tag")).to_have_text("waiting for you", timeout=15000)  # read back, no reload
        expect(page.locator("#pack-admitting")).to_have_count(0)
        expect(page.locator("#pack-start-unknown")).to_have_count(0)
        expect(page.locator("#pack-discard")).to_be_visible()
    assert [u for u in posts if u.endswith("/design-pack/update")] == [f"{base}/api/next/design-pack/update"]
