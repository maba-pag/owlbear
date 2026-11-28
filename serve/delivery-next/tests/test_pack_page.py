"""The Impeccable update on Updates ▸ Impeccable in a real browser (TD-193, TD-220, TD-256)."""

from __future__ import annotations

import contextlib
import dataclasses
import os
import re
import socket
import subprocess
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from playwright.sync_api import Error, expect, sync_playwright

from owlbear_delivery_next.change_contracts.round_records import PACK, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.git.git_executable import resolve_git_executable
from owlbear_delivery_next.impeccable_runs import (
    machine_lock,
    pack_activation,
    pack_job,
    pack_progress,
    pack_publish,
    pack_rounds,
    pack_run,
    pack_state,
)
from owlbear_delivery_next.local_system import git_run, local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.machine_host import app, update_jobs
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import pack_run_record, registry, update_home
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

NOW = datetime(2026, 10, 17, 2, tzinfo=UTC)


def waiting(store: update_jobs.Source, lp: RoundLoop | None = None) -> pack_job.Job:
    """A run waiting for the owner; by default on two findings the challenger upheld against the updater."""
    found = [
        RoundFinding(id=f"F{i}", text=f"owlbear-design-review: glow {i} - fix: say so", raised=1, state="escalated",
                     reason="upstream dropped it", judgement="upstream still names it")
        for i in (1, 2)
    ]  # fmt: skip
    lp = lp or RoundLoop(subject=PACK, policy=RoundPolicy(), round=2, findings=found)
    job = pack_job.Job(store, pack_job.Live())
    context = {
        "tag": "skill-v4.6.0", "why": "Impeccable", "diff": "", "golden": "as expected", "pins": {},
        "manifest": "{}", "notice": "", "baseline": {}, "checkout": {}, "start": {}, "sid": "pack-update-1",
        "next": "wait",
    }  # fmt: skip
    questions, invocations = pack_rounds.questions(lp, "r1", "x"), []
    pack_progress.asked(invocations, "challenger", questions)
    job.state = pack_job._blank() | {  # noqa: SLF001 - a run as the job leaves it waiting
        "state": "waiting", "started_at": NOW.isoformat(), "run": "r1", "loop": lp.model_dump(mode="json"),
        "questions": questions, "invocations": invocations, "context": context,
    }  # fmt: skip
    job._save()  # noqa: SLF001
    return job


@pytest.fixture
def served(monkeypatch) -> Iterator[Callable[..., tuple[pack_job.Job, str]]]:
    servers = []

    def serve(lp: RoundLoop | None = None, job: pack_job.Job | None = None) -> tuple[pack_job.Job, str]:
        job = job or waiting(update_jobs.Source(), lp)
        sock = socket.socket()
        try:
            sock.bind(("127.0.0.1", 0))
            base = f"http://127.0.0.1:{sock.getsockname()[1]}"
            monkeypatch.setattr(update_home, "root", lambda: job.store.root)
            machine = Machine(HostRecord(url=base + "/", token="tok", pid=1, started_at=NOW, code=CURRENT))  # noqa: S106
            machine.updates.pack = job
            server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning"))
            thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
            thread.start()
        except BaseException:
            sock.close()
            raise
        servers.append((server, thread, sock))
        while not server.started:
            assert thread.is_alive(), "the owned page server stopped before startup"
            time.sleep(0.05)
        return job, f"http://127.0.0.1:{sock.getsockname()[1]}"

    try:
        yield serve
    finally:
        for server, _thread, _sock in servers:
            server.should_exit = True
        with contextlib.ExitStack() as cleanup:
            for _server, thread, sock in reversed(servers):
                cleanup.callback(sock.close)
                cleanup.callback(thread.join, 5)
        for _server, thread, _sock in servers:
            assert not thread.is_alive(), "the owned page server did not stop"


@contextlib.contextmanager
def holding() -> Iterator[None]:
    """The machine's Impeccable lock, as a run's thread holds it while it runs; a running record without it is left."""
    fd = machine_lock.take(local_home.root() / pack_state.MACHINE_LOCK, "tests", lambda: None)
    try:
        yield
    finally:
        os.close(fd)


def answers(page: Any) -> list[str]:
    """The answers the waiting questions offer, as one-click buttons or as choices to send, in page order."""
    return page.locator("#pack-questions").evaluate("""(el) => [...el.querySelectorAll(
      "p-button, p-radio-group-option")].map((o) => o.getAttribute("label") ?? o.textContent.trim())
      .filter((t) => t !== "Send answer")""")


@contextlib.contextmanager
def opened(base: str, pds: Any, *, clock: bool = False) -> Iterator[Any]:
    """Updates ▸ Impeccable in a real browser: only the test host and the PDS CDN answer; a page clock on request."""
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Error as exc:
            pytest.skip(f"no Playwright Chromium: {exc}")
        page = browser.new_page()
        pds.only(page, base)
        page.add_init_script("sessionStorage.setItem('token', 'tok');")
        if clock:
            page.clock.install()
        page.goto(f"{base}/updates/impeccable")
        yield page
        browser.close()


@pytest.mark.browser
def test_the_owner_answers_each_upheld_finding_with_his_note_on_the_impeccable_page(served, pds) -> None:
    job, base = served()
    with opened(base, pds) as page:
        ask = page.locator("#pack-ask")
        expect(ask).to_be_visible()
        state = page.locator("#pack-state")
        expect(state).to_contain_text("The update waits for your answers. Started ")
        expect(state).not_to_contain_text("ended")
        expect(page.locator("#pack-progress .pack-step-head")).to_have_text("Your answer waiting for you")
        expect(page.locator("#pack-next")).to_contain_text("Your answer decides what runs next")
        expect(page.locator("#pack-state")).to_contain_text("The update waits for your answers.")
        expect(page.get_by_role("button", name="Update Impeccable")).to_be_disabled()
        expect(page.locator("#pack-update")).to_have_attribute("variant", "secondary")  # the answer leads instead
        first, second = ask.locator(".pack-question").first, ask.locator(".pack-question").last
        facts = first.locator(".pack-facts dd")  # from the finding's record, not the host's sentence
        expect(facts).to_have_text(["owlbear-design-review: glow 1 - fix: say so", "upstream dropped it",
                                    "upstream still names it"])  # fmt: skip
        expect(page.locator("#pack-todo")).to_have_text("Answer the 2 questions in 'Waiting for you'.")
        sent: list[str] = []
        page.on("request", lambda r: sent.append(r.url) if r.url.endswith("/impeccable/update/answer") else None)
        expect(page.locator('#pack p-button[variant="primary"]')).to_have_text(["Send answer"])  # the first's
        first.get_by_role("button", name="Send answer").click()
        expect(first.locator("p-radio-group")).to_have_attribute("message", "Choose an answer first.")
        first.get_by_label("Ask the challenger to reconsider").check()  # nothing is preselected for him
        first.get_by_role("button", name="Send answer").click()
        note = first.locator("p-textarea")
        expect(note).to_have_attribute("message", "Asking the challenger to reconsider needs your note.")
        # the note to give takes focus, once PDS has rendered it
        page.wait_for_function("document.activeElement?.dataset.note === 'r1:dispute:F1'", timeout=5000)
        assert sent == []  # checked here, before anything is sent
        second.get_by_label("Your note", exact=False).fill("a draft for F2")
        first.get_by_label("Your note", exact=False).fill("the halo is upstream's own example")
        first.get_by_label("Drop it").check()
        first.get_by_role("button", name="Send answer").click()
        left = ask.locator(".pack-question")
        expect(left).to_have_count(1)  # the other finding still waits; nothing ran yet
        expect(left.get_by_label("Your note", exact=False)).to_have_value("a draft for F2")  # its draft is kept
        expect(page.locator("#pack-findings li").first).to_contain_text("F1 (round 1), you dropped it")
        assert job.read()["state"] == "waiting"
        discard_waiting(page, pds, job, "Discard the update")
    assert len(sent) == 1  # only the Drop it went out
    kept = RoundLoop.model_validate(job.read()["loop"])
    assert [(f.id, f.state, f.note) for f in kept.findings] == [
        ("F1", "owner-drop", "the halo is upstream's own example"), ("F2", "escalated", "")
    ]  # fmt: skip
    assert job.read()["state"] == "discarded"


@pytest.mark.browser
def test_the_activation_dialog_lists_the_unreviewed_repair_and_what_was_not_changed_for(served, pds) -> None:
    job, base = served(ENDED)
    before = job.path.read_bytes()
    with opened(base, pds) as page:
        expect(page.locator("#pack-ask")).to_contain_text("The updater's last repair (r1) was not reviewed")
        expect(page.locator('#pack p-button[variant="primary"]')).to_have_text(["Activate the unreviewed repair"])
        expect(page.locator("#pack-ask").get_by_role("button", name=re.compile("Discard"))).to_have_count(1)
        page.get_by_role("button", name="Activate the unreviewed repair").click()
        dialog = page.get_by_role("dialog")
        expect(dialog).to_be_visible()
        said = pds.modal(page)
        expect(said).to_contain_text("Repair r1: no challenger reviewed it.")
        expect(said).to_contain_text("F2 not changed for (rejected by the updater; the challenger accepted that)")
        said.get_by_role("button", name="Keep it waiting").click()
        expect(dialog).to_be_hidden()
        page.locator("#pack-discard").click()
        pds.answer(page, "Keep it waiting")
        expect(page.get_by_role("dialog")).to_have_count(0)
    assert job.read()["state"] == "waiting"  # declining activates nothing
    assert job.path.read_bytes() == before


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


def discard_waiting(page, pds, job, discard) -> None:
    """The two native discard dispatches share the same modal and accessibility contract."""
    before = (job.store.root / pack_job.FILE).read_bytes()
    sent = []
    endpoint = (
        "answer" if any(o["id"] == "discard" for q in job.read()["questions"] for o in q["options"]) else "discard"
    )
    page.on(
        "request",
        lambda r: (
            sent.append(r.url.rsplit("/", 1)[-1]) if r.method == "POST" and "/impeccable/update/" in r.url else None
        ),
    )
    expect(page.locator("#pack-ask").get_by_role("button", name=re.compile("Discard"))).to_have_count(1)
    expect(page.locator("#pack-discard")).to_have_text(discard)
    primary = page.locator("#pack-questions p-button[variant=primary]")
    expect(primary).to_have_count(1)
    expect(primary).to_contain_text("Send answer")
    offered = [o["label"] for q in job.read()["questions"] for o in q["options"] if o["id"] != "discard"]
    assert answers(page) == offered
    page.locator("#pack-discard").click()
    expect(pds.modal(page)).to_contain_text("Nothing is activated")
    inside = "document.activeElement?.closest('p-modal') !== null"
    assert page.evaluate(inside)
    where = []
    for _ in range(6):
        page.keyboard.press("Tab")
        where.append(page.evaluate(f"{inside} ? 'dialog' : document.activeElement === document.body ? '' : 'page'"))
    assert "page" not in where
    assert where[-1] == "dialog"
    pds.answer(page, "Keep it waiting")
    assert page.evaluate("document.activeElement?.id") == "pack-discard"
    expect(page.locator("#pack-ask")).to_be_visible()
    assert (job.store.root / pack_job.FILE).read_bytes() == before
    page.locator("#pack-discard").click()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    page.wait_for_function("document.activeElement?.id === 'pack-discard'", timeout=5000)
    assert (job.store.root / pack_job.FILE).read_bytes() == before
    page.locator("#pack-discard").click()
    pds.answer(page, discard)
    expect(page.locator("#pack-state")).to_contain_text("discarded")
    assert job.read()["state"] == "discarded"
    assert sent == [endpoint]


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
def test_progress_and_ended_run_polling_show_current_evidence(served, pds) -> None:
    job, base = served()
    job.state["invocations"] = history()
    job._save()  # noqa: SLF001
    with opened(base, pds, clock=True) as page:
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
        job.state |= {"state": "running", "questions": []}
        pack_progress.opened(job.state["invocations"], "challenger", "full-challenge", round_=2, identity="b")
        job._save()  # noqa: SLF001
        with holding():
            page.reload()
            expect(page.locator("#pack-now")).to_have_text("Challenge round 2, Challenger on the whole pack…")
            expect(page.locator("#pack-next")).to_contain_text("Decided by the verdict")
            expect(page.locator("#pack-todo")).to_contain_text("Nothing for now")
            expect(page.locator("#pack-ask")).to_be_hidden()  # no Discard while it runs
        page.clock.run_for(2000)
        expect(page.locator("#pack-state")).to_contain_text("The machine host stopped during the update.")
        job.state |= {
            "state": "passed",
            "questions": [],
            "ended_at": NOW.isoformat(),
            "published": PUBLISHED | {"merged": "m" * 40},
        }
        job._save()  # noqa: SLF001
        page.reload()
        expect(page.locator("#pack-tag")).to_have_text("passed")
        expect(page.locator("#pack-todo")).to_contain_text("reaches each machine as it takes the OwlBear version")
        expect(page.locator("#pack-run")).not_to_contain_text("installed")
        expect(page.locator("#pack-pushed")).to_contain_text("merged into main as mmmmmmmmmmmm")
        expect(page.locator("#pack-update")).to_be_enabled()
        expect(page.locator("#pack-notice")).to_contain_text("Upstream:")
        expect(page.locator("#pack-ask")).to_be_hidden()
        job.state["state"] = "discarded"
        job._save()  # noqa: SLF001
        page.clock.run_for(15000)
        expect(page.locator("#pack-state")).to_contain_text("Last run discarded")


REPLAY_NONE = "0 decided rounds, 0 left out; the design judge agreed with the owner 0% as recorded, 0% with this pack"


@pytest.mark.browser
def test_a_ci_failed_publish_stop_fits_a_phone_and_says_no_calibration_evidence_instead_of_0(served, pds) -> None:
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
        expect(page.locator("#pack-questions p-radio-group-option")).to_have_count(2)
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
        small = page.evaluate("""[...document.querySelectorAll('#pack p-button, #pack summary')]
            .filter((b) => b.offsetParent).map((b) => b.getBoundingClientRect()).filter((r) => r.height < 24
              || r.width < 24).length""")
        assert small == 0  # every target at least 24px
        discard_waiting(page, pds, job, "Discard the update (the pull request stays open)")


@pytest.mark.browser
def test_failed_stage_reaches_record_page_and_log_whole(served, pds, tmp_path, monkeypatch, whole_error) -> None:
    """A refused push holds the publication: git's whole words, both streams, are its reason, its stage's and its log's
    (#895, #971)."""
    real, pushed, out = subprocess.run, [], "what git printed"

    def refusing(args, *rest, **kw):
        if "push" in args:  # after the account's -c options
            pushed.append(args)
            return subprocess.CompletedProcess(args, 1, f"{out}\n", f"{whole_error}\n")
        return real(args, *rest, **kw)

    repo, origin = tmp_path / "source", tmp_path / "origin"
    for args in (
        ["init", "-q", "--bare", str(origin)],
        ["init", "-q", "-b", "main", str(repo)],
        ["-C", str(repo), "commit", "-q", "--allow-empty", "-m", "precommitted candidate"],
        ["-C", str(repo), "remote", "add", "origin", str(origin)],
    ):
        real(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)
    commit = subprocess.check_output(  # noqa: S603 - Fixture Git rev-parse argv with repo operands; no shell.
        [resolve_git_executable(), "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    job = waiting(Store(tmp_path / "store"))
    job.live = dataclasses.replace(job.live, github=lambda _root: SimpleNamespace())
    ctx = pack_run.Context.model_validate(job.state["context"])
    ctx.publication = pack_publish.Publication(
        root=str(repo), repository="maba-pag/owlbear", base=commit, branch="pack/r1", commit=commit
    )
    lp = RoundLoop.model_validate(job.state["loop"])
    job.state |= {"state": "running", "questions": [], "invocations": []}
    job.keep(ctx, lp)
    monkeypatch.setattr(git_run.subprocess, "run", refusing)
    assert pack_activation.republish(job, ctx, lp) is None
    state = job.read()

    said = (
        f"PackError: git push failed: CalledProcessError: Command '{pushed[0]}' returned non-zero exit status 1.\n"
        f"stderr:\n{whole_error}\nstdout:\n{out}"
    )
    assert (state["state"], state["reason"]) == ("waiting", said)
    assert next(s for s in state["stages"] if s["name"] == "push")["detail"] == said
    assert [i["detail"] for i in state["invocations"] if i["operation"] == "push"] == [said]
    logged = [line.split(" ", 1)[1] for line in state["log"]]
    assert logged[-3:] == ["push: running", f"push: failed: {said}", f"waiting for you: {said}"]
    _job, base = served(job=job)
    with opened(base, pds) as page:
        reason = page.locator("#pack-reason")
        expect(reason).to_be_visible()
        assert reason.text_content() == said
        page.get_by_text("Log of the run").click()
        log = page.locator("#pack-log")
        expect(log).to_be_visible()
        assert log.text_content() == "\n".join(state["log"])


@pytest.mark.browser
def test_an_unreadable_registry_shows_whole_but_does_not_disable_start(served, pds, monkeypatch, whole_error) -> None:
    """The old-runs advisory reports registry errors without blocking the machine's update."""
    job, base = served()
    job.state |= {"state": "passed", "questions": [], "ended_at": NOW.isoformat()}
    job._save()  # noqa: SLF001
    error = registry.RegistryError(whole_error)
    error.add_note("a note added on the way up")

    def unreadable() -> registry.Machine:
        raise error

    monkeypatch.setattr(registry, "load", unreadable)
    whole = f"RegistryError: {whole_error}\na note added on the way up"
    with opened(base, pds) as page:
        page.reload()
        expect(page.get_by_text("the machine's registry cannot be read", exact=False)).to_contain_text(whole)
        expect(page.locator("#pack-published")).to_contain_text("Nothing yet")
        expect(page.get_by_role("button", name="Update Impeccable")).to_be_enabled()


@pytest.mark.browser
def test_an_unreadable_machine_run_record_shows_whole_and_disables_start(served, pds, monkeypatch, whole_error) -> None:
    job, base = served()
    error = OSError(whole_error)
    error.add_note("a note added on the way up")
    real = pack_run_record.observed

    def unreadable(root, *rest):
        if root != job.store.root:
            return real(root, *rest)
        raise error

    monkeypatch.setattr(pack_run_record, "observed", unreadable)
    with opened(base, pds) as page:
        page.reload()
        shown = page.locator("#pack-runs-error")
        expect(shown).to_contain_text(f"OSError: {whole_error}\na note added on the way up")
        expect(page.get_by_role("button", name="Update Impeccable")).to_be_disabled()


@pytest.mark.browser
def test_an_unreadable_section_says_what_could_not_be_read(served, pds) -> None:
    _job, base = served()
    with opened(base, pds) as page:
        expect(page.locator("#pack-ask")).to_be_visible()
        page.route("**/maintenance/pack/runs", lambda r: r.fulfill(status=500, json={"detail": "the disk said no"}))
        page.route("**/maintenance/pack", lambda r: r.fulfill(status=500, json={"detail": "no pin today"}))
        page.reload()
        said = "Could not read the Impeccable update: the disk said no"
        expect(page.locator("#pack-runs-error")).to_contain_text(said)
        expect(page.locator("#pack-read-error")).to_contain_text("Could not read Impeccable: no pin today")
        expect(page.locator("#pack-run")).to_have_count(0)  # nothing made up in its place


@pytest.mark.browser
def test_a_start_admitted_after_its_timeout_shows_its_run_without_a_reload_or_a_second_post(served, pds) -> None:
    """I1-3: admission may look up GitHub for longer than the start waits; the section keeps looking, never resends."""
    job, base = served()
    job.state |= {"state": "passed", "questions": [], "ended_at": NOW.isoformat()}
    job._save()  # noqa: SLF001

    requested, release, saved = threading.Event(), threading.Event(), threading.Event()

    def slow_start() -> dict[str, Any]:
        requested.set()
        assert release.wait(5), "the test did not release admission after the browser timeout"
        job.state = pack_job._blank() | {"state": "waiting", "run": "r2", "started_at": datetime.now(UTC).isoformat(),  # noqa: SLF001
                                         "questions": [CI_FAILED | {"id": "r2-publish"}],
                                         "invocations": []}  # fmt: skip
        job._save()  # noqa: SLF001
        saved.set()
        return job.read()

    job.start = slow_start
    with opened(base, pds, clock=True) as page:
        posts: list[str] = []
        page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
        expect(page.locator("#pack-tag")).to_have_text("passed")
        page.get_by_role("button", name="Update Impeccable").click()
        pds.answer(page, "Update")
        assert requested.wait(5)
        page.clock.run_for(10001)
        expect(page.locator("#pack-admitting")).to_contain_text("It was not sent again")
        release.set()
        assert saved.wait(5)
        page.clock.run_for(2500)
        expect(page.locator("#pack-tag")).to_have_text("waiting for you")
        expect(page.locator("#pack-admitting")).to_have_count(0)
        expect(page.locator("#pack-start-unknown")).to_have_count(0)
        expect(page.locator("#pack-discard")).to_be_visible()
    assert [u for u in posts if u.endswith("/impeccable/update")] == [f"{base}/api/next/impeccable/update"]
