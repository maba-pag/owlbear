"""The Improvement page and a Change's Spotter and Retro detail (#716, design §6), in a browser on a machine host."""

from __future__ import annotations

import json
import re
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.improvement import (
    acts,
    case_edits,
    case_replay,
    cases,
    followups,
    improvement_view,
    spotter,
)
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.machine_host import (
    app,
    cases_job,
    chat_acts,
    improvement_routes,
    project,
    retro_job,
)
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.state_store import registry, spotter_test, watch_reports
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.state_store.watch_reports import Report

from .test_machine_pages import page_at, serve

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from playwright.sync_api import Locator, Page

NOW = datetime(2026, 10, 1, 10, tzinfo=UTC)
SLUG = "alpha-1"
DONE = "alpha-2"  # a finished Change: Retro may run on it
TEXT = {"title": "Check the export's week column", "body": "The builder said done before the week held ISO weeks."}
STOPPED = "The Spotter stopped this step for irreversible harm: it would force-push over main"
ALLOW = "Allow it: the brief is amended first, then the step goes on"  # the Spotter's question's first option
PREFILL = "t hand-off-fitness\n\nbash make"
FAILED = "HostError: VS Code's agent host is not running: its published endpoint failed: ConnectionRefusedError"
NOTE = "the runtime said more after the error"  # a note an error carries, which its whole text keeps
# An element's text without its times, which the browser words in its own locale, nor its nested list.
BARE = (
    "e => { const c = e.cloneNode(true); c.querySelectorAll('time, ul').forEach((t) => t.remove()); "
    "return c.textContent; }"
)


class Backlog:
    """The shared backlog, faked: it refuses the next *fail* reads, then keeps what is added."""

    repository = "acme/owlbear-data"

    def __init__(self) -> None:
        self.fail = 0
        self.entries: dict[str, Any] = {}

    def __call__(self, _folder: str) -> Backlog:
        if self.fail:
            self.fail -= 1
            msg = "the backlog cannot be reached"
            raise store.RetroError(msg)
        return self

    def read(self, *, fresh: bool = False) -> tuple[dict[str, Any]]:
        del fresh
        return (self.entries,)

    def add(self, title: str, _body: str, _source: str, *, evidence: list[str]) -> tuple[Any, None]:
        entry = SimpleNamespace(id=len(self.entries) + 1, title=title, evidence=evidence)
        self.entries[str(entry.id)] = entry
        return entry, None


def _clone(path: Path) -> registry.Project:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    (path / ".github" / "agents").mkdir(parents=True)
    (path / ".github" / "agents" / "exporter.agent.md").write_text("# exporter\n")  # the project's own agent
    st = Store.open(path)
    stopped = session_result.Run("s", ending="spotter-ask", detail=STOPPED, termination=Termination(confirmed=True))
    asked = session_result.to_result(stopped, m.StepKind.BUILD, NOW)  # the Spotter stopped its step to ask
    with st.lock(SLUG) as lock:
        st.write(lock, loop.apply(m.Change(slug=SLUG, step=m.Step(kind=m.StepKind.BUILD)), asked, NOW))
    with st.lock(DONE) as lock:
        st.write(lock, m.Change(slug=DONE, step=m.Step(kind=m.StepKind.BUILD), finished_at=NOW))
    return registry.register(path.resolve())


def _outside_writes(path: Path, slugs: tuple[str, ...]) -> None:
    """One outside write the watcher saw in each Change of *slugs* of the project at *path*."""
    with Store.open(path).db.write() as connection:
        for slug in slugs:
            watch_reports.put(slug, Report("s", f"c-{slug}", "2026-10-01T10:00:01.000+00:00", "build", "main", "bash",
                                           f"cp a /x-{slug}", (f"/x-{slug}",), "outside write (not judged yet)", "",
                                           "start"))(connection)  # fmt: skip


def _writes_shown(expect, looks, shown: str, hidden: str) -> None:
    """*looks* lists Change *shown*'s outside write and not Change *hidden*'s, by Playwright's *expect*."""
    expect(looks).to_contain_text(f"cp a /x-{shown}")
    expect(looks).not_to_contain_text(f"cp a /x-{hidden}")


def _records(pid: str) -> None:
    base = {"project": pid, "change": SLUG, "step": "build", "session": "s", "look": "handoff", "call": "c",
            "credits": 0.2, "credits_known": True, "model": "m"}  # fmt: skip
    rows = [
        {"id": "r-note", "at": "2026-10-01T10:00:00+00:00", "category": "hand-off-fitness", "action": "note",
         "note": "It said done with the week column unchecked.", "rationale": "the plan names the column",
         "credits_known": False, "stopped": "unknown"},
        {"id": "r-harm", "at": "2026-10-01T11:00:00+00:00", "category": "irreversible-harm", "action": "stop",
         "acted": "stopped", "note": "A force-push over main."},
        {"id": "r-quiet", "at": "2026-10-01T09:00:00+00:00", "category": "none", "action": ""},
    ]  # fmt: skip
    with (spotter.root() / "records-2026-10-01.jsonl").open("a") as out:
        out.writelines(json.dumps(base | r) + "\n" for r in rows)


def _proposal(kind: str, target: str, findings: list[str], **fields: object) -> str:
    pid = props.file(props.open_key("real", kind, target), findings, kind=kind, target=target, provenance="real",
                     **fields)  # fmt: skip
    review = {"verdict": "survive", "why": "the evidence holds", "risks": ["it may slow small Changes"],
              "publishable": TEXT}  # fmt: skip
    props.reviewed(pid, props.folded()[pid]["evidence"], review)
    return pid


def _checked() -> str:
    for call in ("none", "none", "hand-off-fitness"):
        cid = cases.freeze({"intent": {"task": f"t {call}"}, "recent": [{"tool": "bash", "args": "make"}]},
                           {"source": "pilot", "family": "f"})  # fmt: skip
        entry = {"stage": "candidate", "call": call, "why": "why", "example": "", "review": None}
        cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
        cases.commit(cases.current()["n"], {cid: cases.edited(cid, entry, stage="test", reviewed_by="sol")}, "t", "r")
    return cid


def seeded(pid: str) -> dict[str, str]:
    """Spotter records, a finding, one proposal per destination and a checked case; their ids."""
    _records(pid)
    found = {"id": "f-1", "unit": f"chg:{pid}:{SLUG}", "change": f"{pid}:{SLUG}", "what": "done before the week held"}
    store.add_findings([found | {"cost": "a re-run", "mechanism": "said done early"}])
    return {
        "memory": _proposal("lesson", "agent:builder", ["f-1"]),
        "backlog": _proposal("agent-change", "agent:exporter", ["f-1"], mechanism="m-1"),
        "issue": _proposal("delivery-change", "delivery:review", ["f-1"]),
        "case": _proposal("spotter-case", "look:handoff", ["f-1"], record="r-note", call="hand-off-fitness"),
        "checked": _checked(),
    }


@contextmanager
def machine_page(tmp_path: Path, monkeypatch, pds, *, seed: bool = True) -> Iterator[SimpleNamespace]:
    """A browser on a machine host serving one registered project, with Improvement's stores seeded or empty.

    Retro and the Spotter cases job never run: what is queued stays queued. The shared repository is a folder; its
    backlog is faked.
    """
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    monkeypatch.setattr(retro_job.RetroJob, "tick", lambda _self, _now: None)
    monkeypatch.setattr(cases_job.CasesJob, "tick", lambda _self, _now: None)
    monkeypatch.setattr(app, "_shared", lambda: DataRepo(tmp_path / "shared"))
    backlog = Backlog()
    monkeypatch.setattr(followups, "backlog", backlog)
    registered = _clone(tmp_path / "alpha")
    monkeypatch.setattr(targets, "units_of", lambda: {"f-1": f"chg:{registered.id}:{SLUG}"})
    ids = seeded(registered.id) if seed else {}
    with serve() as (machine, _server, base), page_at(base, pds, (1280, 900), required=True) as page:
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        yield SimpleNamespace(page=page, base=base, pid=registered.id, ids=ids, backlog=backlog, errors=errors,
                              machine=machine)  # fmt: skip
        assert errors == []


def improvement(w: SimpleNamespace, pds) -> Page:
    w.page.goto(f"{w.base}/improvement#token=t")
    w.page.locator("#proposals").wait_for()
    pds.settled(w.page)
    return w.page


def card(page: Page, pid: str):
    return page.locator(f"#proposal-{pid}")


def small(scope) -> list[str]:
    """WCAG 2.5.8: each shown control in *scope* smaller than 24 by 24 CSS pixels once laid out, by its text."""
    found: list[str] = []
    for _ in range(20):
        found = scope.evaluate_all(
            "els => els.filter(e => e.checkVisibility()).filter(e => { const r = e.getBoundingClientRect();"
            " return r.width < 24 || r.height < 24 }).map(e => e.textContent.trim() || e.outerHTML.slice(0, 60))"
        )
        if not found:
            break
        scope.page.wait_for_timeout(250)
    return found


def contained(page: Page) -> None:
    """The focus is in the open dialog and Tab keeps it there: the page behind is inert."""
    inside = "document.activeElement?.closest('p-modal') !== null"
    assert page.evaluate(inside)
    where = []
    for _ in range(6):
        page.keyboard.press("Tab")
        where.append(page.evaluate(f"{inside} ? 'dialog' : document.activeElement === document.body ? '' : 'page'"))
    assert "page" not in where
    assert where[-1] == "dialog"


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_synthetic_retro_is_visible_as_history_without_action_buttons(tmp_path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        store.add_findings([{"id": "f-history", "unit": "syn:old", "what": "An invented finding",
                             "provenance": "synthetic"}])  # fmt: skip
        pid = props.file(props.open_key("synthetic", "lesson", "old"), ["f-history"], kind="lesson",
                         target="agent:builder", provenance="synthetic")  # fmt: skip
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "publishable": TEXT})
        redirected = props.file(props.open_key("synthetic", "agent-change", "old"), ["f-history"], kind="agent-change",
                                target="agent:builder", provenance="synthetic")  # fmt: skip
        props.reviewed(redirected, props.folded()[redirected]["evidence"], {"verdict": "survive", "publishable": TEXT})
        props.transition(redirected, "redirected", "owner", direction="Keep the old direction")
        child = props.redrafted(redirected, {"cause": "c", "target": "agent:builder", "mechanism": "m"}, "old")
        props.reviewed(child, props.folded()[child]["evidence"], {"verdict": "survive", "publishable": TEXT})
        partial = props.file(props.open_key("synthetic", "delivery-change", "old"), ["f-history"],
                             kind="delivery-change", target="delivery:review", provenance="synthetic")  # fmt: skip
        props.reviewed(partial, props.folded()[partial]["evidence"], {"verdict": "survive", "publishable": TEXT})
        snapshot = {"destination": {"kind": "issue", "repository": "o/r", "synthetic": True}}
        props.transition(partial, "accepted", "owner", snapshot=snapshot)
        props.outcome(partial, "applied", step="created", artefact={"kind": "issue", "where": "o/r", "ref": "#2"})
        page = improvement(w, pds)
        old = card(page, pid)
        expect(old).to_contain_text("Historical")
        expect(old).to_contain_text("synthetic Retro is retired")
        expect(old.get_by_role("button")).to_have_count(0)
        expect(page.locator("#finding-f-history")).to_contain_text("An invented finding")
        expect(page.locator("#finding-f-history")).to_contain_text("Synthetic finding: historical only.")
        expect(page.locator("#finding-f-history").get_by_role("button", name="Follow up")).to_have_count(0)
        expect(page.locator("#proposals")).to_contain_text("None waits for you.")
        history = card(page, redirected)
        expect(history).to_contain_text("Redirected")
        expect(history).to_contain_text("Your direction: Keep the old direction")
        expect(history).to_contain_text(f"Redrafted as {child}.")
        expect(history.get_by_role("button")).to_have_count(0)
        expect(card(page, partial)).to_contain_text("Partly made")
        expect(card(page, partial)).not_to_contain_text("closed at once")
        expect(card(page, partial).get_by_role("button")).to_have_count(0)


@pytest.mark.browser
@pytest.mark.timeout(120)  # a journey through every proposal dialog
def test_proposals_are_decided_by_direction_and_each_dialog_says_what_follows(  # noqa: PLR0915 - a journey
    tmp_path, monkeypatch, pds
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        page, ids = improvement(w, pds), w.ids
        assert small(page.locator("#page p-button, #page a, #page p-select")) == []
        memory = card(page, ids["memory"])
        expect(memory).to_contain_text("Seen in alpha \u00b7 alpha-1: done before the week held Cost: a re-run")
        expect(memory).to_contain_text("Risk: it may slow small Changes")
        for kind, says in (("memory", "A pending memory in"), ("issue", "OwlBear opens the issue on GitHub"),
                           ("backlog", "OwlBear adds the entry to the backlog"),
                           ("case", "OwlBear adds the case as a candidate")):  # fmt: skip
            card(page, ids[kind]).get_by_role("button", name="Accept").click()
            expect(pds.modal(page)).to_contain_text(says)
            if kind == "memory":
                contained(page)
                newer = _proposal("lesson", "agent:reviewer", ["f-1"])
                page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
                expect(card(page, newer)).to_have_count(1)
            pds.answer(page, "Cancel")
            if kind == "memory":
                page.wait_for_function("document.activeElement?.closest('#proposal-" + ids[kind] + "') !== null")
        assert {props.folded()[ids[k]]["state"] for k in ("memory", "issue", "backlog", "case")} == {"waiting"}

        memory.get_by_role("button", name="Accept").click()
        pds.answer(page, "Accept")
        expect(page.locator("#notice")).to_contain_text("Accepted and made")
        expect(memory).to_contain_text("Made: memory")
        assert props.folded()[ids["memory"]]["apply_state"] == "done"

        w.backlog.fail = 1  # the backlog cannot be reached once
        backlog = card(page, ids["backlog"])
        backlog.get_by_role("button", name="Accept").click()
        pds.answer(page, "Accept")
        expect(page.locator("#notice")).to_contain_text("making it failed: use Apply again")
        expect(backlog).to_contain_text("Last failure: RetroError: the backlog cannot be reached")
        backlog.get_by_role("button", name="Apply again").click()
        expect(page.locator("#notice")).to_contain_text("Made: Check the export's week column.")
        expect(backlog).to_contain_text("Made: backlog #1 in acme/owlbear-data")
        assert [e.evidence[-1] for e in w.backlog.entries.values()] == [f"retro-proposal:{ids['backlog']}"]

        issue = card(page, ids["issue"])
        issue.get_by_role("button", name="Reject").click()
        expect(pds.modal(page)).to_contain_text("It cannot be reopened.")
        pds.answer(page, "Reject")
        expect(issue).to_contain_text("Rejected")
        assert props.folded()[ids["issue"]]["state"] == "rejected"

        case = card(page, ids["case"])
        case.get_by_role("button", name="Later").click()
        expect(case.get_by_role("button", name="Later")).to_have_count(0)
        assert props.folded()[ids["case"]]["state"] == "later"

        before = store.lines(props.FILE)
        case.get_by_role("button", name="Redirect").click()
        pds.modal(page).get_by_label("What should change").fill("Ask for the column list first")
        pds.answer(page, "Cancel")
        assert (store.lines(props.FILE), store.queued()) == (before, [])  # cancelling wrote nothing
        case.get_by_role("button", name="Redirect").click()
        dialog = pds.modal(page)
        expect(dialog.get_by_role("button", name="Next")).to_be_disabled()  # a redirect says what to change
        dialog.get_by_label("What should change").fill("Ask for the column list first")
        pds.answer(page, "Next")
        read_back = pds.modal(page)
        expect(read_back).to_contain_text("Ask for the column list first")
        expect(read_back).to_contain_text("Retro redrafts it at once")
        pds.answer(page, "Redirect")
        expect(case).to_contain_text("Your direction: Ask for the column list first")
        expect(case).to_contain_text("Retro redrafts it on its next run.")
        snap = props.folded()[ids["case"]]
        assert (snap["state"], snap["direction"]) == ("redirected", "Ask for the column list first")
        (asked,) = store.queued()
        assert asked["redraft"] == ids["case"]
        assert store.take(asked["id"])  # the host that took it stopped before its run opened
        expect(case).to_contain_text("No redraft is queued or running", timeout=15000)  # read again on the bar's poll
        case.get_by_role("button", name="Redraft again").click()
        expect(page.locator("#notice")).to_contain_text("Redraft queued as")
        expect(case).to_contain_text("Retro redrafts it on its next run.")
        (again,) = store.queued()
        assert store.take(again["id"])  # this run files the redraft, then stops before reviewing it
        props.redrafted(ids["case"], {"cause": "review", "target": "look:handoff", "mechanism": "ask first"}, "x")
        expect(case).to_contain_text("its run stopped before reviewing it", timeout=15000)
        case.get_by_role("button", name="Redraft again").click()
        expect(case).to_contain_text("Retro redrafts it on its next run.")


def _case_focus_after_poll(page: Page, pds, cid: str) -> Locator:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    case = page.locator(f"#case-{cid}")
    pds.pick(case, f"Stage of case {cid}", "example")
    case.get_by_role("button", name="Move").click()
    expect(pds.modal(page)).to_be_visible()
    cur = cases.current()
    cases.commit(cur["n"], {cid: cases.edited(cid, cur["cases"][cid], stage="candidate")}, "t", "back")
    page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
    expect(page.locator("#cases")).not_to_contain_text("No candidates.")
    pds.answer(page, "Cancel")
    page.wait_for_function(f"document.activeElement?.closest('#case-{cid}') !== null")
    cur = cases.current()
    cases.commit(cur["n"], {cid: cases.edited(cid, cur["cases"][cid], stage="test", reviewed_by="sol")}, "t", "r")
    page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
    expect(case.locator("p-select-option")).to_have_count(4)
    return case


@pytest.mark.browser
@pytest.mark.timeout(120)  # a journey through each section's dialogs
def test_looks_and_cases_act_through_their_dialogs(tmp_path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        skip = {"id": "r-skip", "at": datetime.now(UTC).isoformat(timespec="seconds"), "project": w.pid,
                "change": SLUG, "step": "build", "session": "s", "look": "sample", "call": "c",
                "skipped": "capacity: 1 sampled looks skipped, looks already running"}  # fmt: skip
        with (spotter.root() / "records-2026-10-01.jsonl").open("a") as out:
            out.write(json.dumps(skip) + "\n")
        _outside_writes(tmp_path / "alpha", (SLUG, DONE))
        page = improvement(w, pds)
        expect(page.locator("#looks")).to_contain_text(f"alpha \u00b7 {DONE} \u00b7 main \u00b7 cp a /x-{DONE}")
        expect(page.locator("#spotter")).to_contain_text("alpha")
        expect(page.locator("#spotter")).to_contain_text("0.00 credits; 1 look skipped before starting.")
        harm = page.locator("#look-r-harm")
        expect(harm).to_contain_text("A force-push over main.")
        note = page.locator("#look-r-note")
        expect(note).to_contain_text("It said done with the week column unchecked.")
        expect(note).to_contain_text("Why: the plan names the column")
        expect(page.locator("#look-r-quiet")).to_contain_text("Nothing found")  # a silent look
        expect(note).to_contain_text("Stopped: its spend was not reported")
        expect(note).not_to_contain_text("credit limit")

        note.get_by_role("button", name="Follow up").click()
        expect(pds.modal(page)).to_contain_text("OwlBear adds one backlog entry for r-note")
        pds.answer(page, "Cancel")
        assert store.queued() == []
        note.get_by_role("button", name="Follow up").click()
        pds.answer(page, "Follow up")
        expect(page.locator("#notice")).to_contain_text("Follow-up queued as")
        expect(note).to_contain_text("Follow-up queued: Retro writes its backlog entry")
        expect(note.get_by_role("button", name="Follow up")).to_have_count(0)
        assert [q.get("followup") for q in store.queued()] == ["r-note"]

        pds.pick(page.locator("#looks"), "Project", w.pid)
        expect(page).to_have_url(f"{w.base}/improvement?in={w.pid}")
        expect(note).to_be_visible()
        pds.pick(page.locator("#looks"), "Change", SLUG)
        expect(note).to_be_visible()
        _writes_shown(expect, page.locator("#looks"), SLUG, DONE)
        page.reload()
        pds.settled(page)
        expect(pds.select(page, "Change").get_by_role("combobox")).to_have_text(SLUG)  # kept in the address

        case = _case_focus_after_poll(page, pds, w.ids["checked"])
        expect(pds.select(case, f"Stage of case {w.ids['checked']}").get_by_role("combobox")).to_have_text("Example")
        with page.expect_request(lambda r: r.url.endswith("/move")) as sent:
            case.get_by_role("button", name="Move").click()
            dialog = pds.modal(page)
            expect(dialog.get_by_label("The example text", exact=False)).to_have_value(PREFILL)
            pds.answer(page, "Move")
        body = sent.value.post_data_json
        assert (body["stage"], body["example"]) == ("example", PREFILL)
        expect(page.locator("#notice")).to_contain_text("queued: the move is written only if it passes")
        expect(page.locator("#cases")).to_contain_text("A replay run is queued or running")
        pds.pick(case, f"Stage of case {w.ids['checked']}", "candidate")
        expect(case.get_by_role("button", name="Move")).to_be_disabled()  # moves wait for the queued run


def _acted(pid: str) -> None:
    """Act lines for two of the seeded records, as the Spotter writes them, and a third record still pending."""
    folder = spotter.place()
    with (folder / "records-2026-10-01.jsonl").open("a") as out:
        out.write(json.dumps({"id": "r-wait", "at": "2026-10-01T12:00:00+00:00", "project": pid, "change": SLUG,
                              "step": "build", "session": "s", "look": "handoff", "call": "c",
                              "category": "outside-state-changes", "action": "steer",
                              "note": "It edited the shared CI file."}) + "\n")  # fmt: skip
    first = {"at": "2026-10-01T10:00:00+00:00", "unit": f"chg:{pid}/{SLUG}", "session": "s", "scope": "build",
             "look": "handoff", "why": "setting"}  # fmt: skip
    acts.write(folder, acts.Act(record="r-note", arm="steered", category="hand-off-fitness", act="refuse-hand-off",
                                delivery="pending", **first))  # fmt: skip
    acts.update(folder, "r-note", delivery="failed", error=FAILED)
    acts.write(folder, acts.Act(record="r-harm", arm="silent", category="irreversible-harm", act="stop-and-ask",
                                harm=True, note="A force-push over main.", delivery="pending", **first))  # fmt: skip
    acts.update(folder, "r-harm", delivery="delivered")
    acts.write(folder, acts.Act(record="r-wait", arm="steered", category="outside-state-changes", act="steer",
                                delivery="pending", **first))  # fmt: skip
    checked = {"decisions": [{"id": "D-7", "title": "CI stays shared", "note": "It governs edits to the CI file."}]}
    acts.update(folder, "r-wait", conflict=json.dumps(checked))


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_each_records_act_the_spotter_test_and_the_chats_not_followed_show(tmp_path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        _acted(w.pid)
        spotter_test.declare("fewer re-runs", "B", "A")
        spotter_test.start({"model": "gpt-5.6-sol", "effort": "high", "context": "", "prompt": "p",
                            "prompt_hash": "ab12cd34", "cases": 7})  # fmt: skip
        work, sessions = tmp_path / "work", tmp_path / "sessions"
        for sid, client in (("term", "github/cli"), ("vs", chat_acts.VSCODE)):
            (sessions / sid).mkdir(parents=True)
            (sessions / sid / "workspace.yaml").write_text(f"cwd: {work}\nclient_name: {client}\n")
        w.machine.chats._found(sorted(sessions.iterdir()), set(), (str(work),))  # noqa: SLF001 - one pass's listing
        page = improvement(w, pds)

        failed = page.locator("#look-r-note")
        expect(failed).to_contain_text("Its act: refuse-hand-off, steered arm, failed")
        expect(failed).to_contain_text(f"Its error: {FAILED}")
        harm = page.locator("#look-r-harm")
        expect(harm).to_contain_text("Stopped the step: irreversible harm")
        expect(harm).to_contain_text("Its act: stop-and-ask, silent arm, delivered")
        expect(harm).to_contain_text("Its question to you: A force-push over main.")
        waiting = page.locator("#look-r-wait")
        expect(waiting).to_contain_text("Its act: steer, steered arm, pending")
        expect(waiting).to_contain_text("Decision check: D-7 CI stays shared (It governs edits to the CI file.)")
        expect(waiting).not_to_contain_text("Its error")
        quiet = page.locator("#look-r-quiet")  # no act: nothing about one
        expect(quiet).to_contain_text("Nothing found")
        expect(quiet).not_to_contain_text("Its act")

        spotted = page.locator("#spotter")
        expect(spotted).to_contain_text("fewer re-runs")
        frozen = "model gpt-5.6-sol, high effort, default context, prompt ab12cd34, cases version 7"
        expect(spotted).to_contain_text(f"Frozen for its looks: {frozen}")
        expect(spotted.locator("#not-followed")).to_contain_text(f"{work}: not followed: terminal chat (session term)")
        expect(spotted.locator("#not-followed")).not_to_contain_text("session vs")


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_reviewed_reserve_case_is_never_offered_as_an_example(tmp_path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        kept = cases.freeze({"intent": {"task": "t kept"}, "recent": [{"tool": "bash", "args": "ls"}]},
                            {"source": "pilot", "family": "f", "reserve": True})  # fmt: skip
        entry = {"stage": "test", "call": "none", "why": "why", "example": ""}
        review = {"by": "t", "at": cases.now(), "note": "", "content": cases.content(kept, entry)}
        cases.commit(cases.current()["n"], {kept: {**entry, "review": review}}, "t", "add")
        assert cases.problems(cases.current()["cases"]) == []
        page = improvement(w, pds)
        stages = page.locator(f"#case-{kept} p-select-option")
        expect(stages).to_have_count(3)
        assert stages.evaluate_all("o => o.map((e) => e.value)") == ["candidate", "test", "removed"]


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_an_unchecked_candidate_only_stays_or_goes_and_says_its_last_check_and_how_another_is_asked(
    tmp_path, monkeypatch, pds
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        new = cases.freeze({"intent": {"task": "t new"}, "recent": [{"tool": "bash", "args": "ls"}]},
                           {"source": "pilot", "family": "f"})  # fmt: skip
        unchecked = {"stage": "candidate", "call": "none", "why": "why", "example": "", "review": None}
        cases.commit(cases.current()["n"], {new: unchecked}, "t", "add")
        with cases.locked():
            long = "tests/test_improvement_page.py::" + "a_check_note_quotes_a_long_test_id_" * 4
            for rid, note in (("r-old", "No test output."), ("r-new", f"Output has no assertion: {long}.")):
                cases.append("runs.jsonl", {"id": rid, "kind": "check", "by": "t", "asked": cases.now(),
                                            "reviews": {new: {"result": "not supported", "note": note}},
                                            "result": "checked", "ended": cases.now()})  # fmt: skip
            for i in range(improvement_view.VERSIONS):  # newer runs of other kinds fill the page's run list
                cases.append("runs.jsonl", {"id": f"p-{i}", "kind": "publication", "result": "nothing due",
                                            "ended": cases.now()})  # fmt: skip
        page = improvement(w, pds)
        fresh = page.locator(f"#case-{new}")
        expect(fresh).to_contain_text("Its last check (r-new")
        line = fresh.locator("p-text", has_text="Its last check (r-new")
        expect(line).to_contain_text("): not supported. Output has no assertion:")
        assert line.evaluate("e => getComputedStyle(e).maxInlineSize") != "none"  # running text, capped
        assert line.evaluate("e => e.scrollWidth <= e.clientWidth")  # a long token wraps inside the cap
        expect(fresh).not_to_contain_text("r-old")
        expect(fresh).to_contain_text(f"once a further paid check supports it: owlbear cases check {new}")
        expect(fresh.locator("p-select-option")).to_have_count(2)  # only stays or goes: the check comes first

        rid = case_edits.check_request([new], "t")
        page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
        expect(fresh).to_contain_text("Its paid check is asked")

        assert case_replay.take(rid)
        case_replay.interrupted()  # the host ended before the check reviewed it: no review of it, only its result
        page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
        expect(fresh).to_contain_text(f"Its last check ({rid}")
        expect(fresh).to_contain_text("stopped: OwlBear ended while it ran; it is not rerun.")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a journey through Retro's dialogs
def test_retro_shows_its_switches_runs_and_findings(tmp_path, monkeypatch, pds) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    switches = {"retro_after_change": "off", "retro_when_idle": "paused"}
    monkeypatch.setattr(improvement_routes, "_switches", lambda: switches)
    with machine_page(tmp_path, monkeypatch, pds) as w:
        store.run_event("run-1", "opened", unit=f"chg:{w.pid}:{DONE}", trigger="button")
        store.run_event("run-1", "ended", result="judged", spent=1.25, credits={"spent": 1.25, "known": True})
        page = improvement(w, pds)
        retro = page.locator("#retro")
        expect(retro.locator("#retro-change")).to_contain_text(DONE)
        retro.get_by_role("button", name="Run Retro").click()
        expect(pds.modal(page)).to_contain_text(f"Run Retro on {DONE}?")
        pds.answer(page, "Run Retro")
        expect(page.locator("#notice")).to_contain_text(f"Retro run of {DONE} queued as")
        assert [q["change"] for q in store.queued() if q["change"]] == [f"{w.pid}:{DONE}"]
        expect(retro).to_contain_text("Run after each finished Change: Off")
        expect(retro).to_contain_text("Run when idle: On, even while paused")
        expect(retro.locator("#run-run-1")).to_contain_text("1.25 credits")
        found = retro.locator("#finding-f-1")
        expect(found).to_contain_text(f"done before the week held alpha \u00b7 {SLUG} \u00b7 How: said done early")
        found.get_by_role("button", name="Follow up").click()
        pds.answer(page, "Follow up")
        expect(found).to_contain_text("Followed up: Check the export's week column")


@pytest.mark.browser
def test_an_empty_machine_says_so_and_an_unread_one_says_why(tmp_path, monkeypatch, pds, whole_error) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        page = improvement(w, pds)
        expect(page.locator("#proposals")).to_contain_text("Retro has proposed nothing yet.")
        expect(page.locator("#looks")).to_contain_text("No look yet here")
        expect(page.locator("#looks")).to_contain_text("No outside write observed here.")
        expect(page.locator("#spotter")).to_contain_text("No Spotter test is declared.")
        expect(page.locator("#not-followed")).to_have_count(0)
        expect(page.locator("#retro")).to_contain_text("No Retro run yet.")
        expect(page.locator("#cases")).to_contain_text("No candidates.")
        page.route(re.compile(r"/api/next/improvement$"), lambda route: route.fulfill(status=500, body="boom"))
        page.reload()
        expect(page.locator("#page")).to_contain_text("The Improvement page could not be read")
        expect(page.locator("#proposals")).to_have_count(0)
        expect(page.locator("#looks")).to_contain_text("No look yet here")  # what was read still shows
        page.unroute(re.compile(r"/api/next/improvement$"))
        monkeypatch.setattr(spotter_test, "current", failing(whole_error))
        monkeypatch.setattr(improvement_view, "looks", failing(whole_error))
        page.reload()
        overview = page.locator('#page p-inline-notification[heading="The Improvement page could not be read"]')
        looks = page.locator('#looks p-inline-notification[heading="The looks could not be read"]')
        looks.wait_for()
        pds.settled(page)
        assert (described(overview), described(looks)) == (f"RuntimeError: {whole_error}",) * 2


def failing(whole_error: str) -> Callable[..., Any]:
    """A read that raises *whole_error*, which no route catches."""

    def read(*_args: object, **_kwargs: object) -> Any:
        raise RuntimeError(whole_error)

    return read


def described(notification: Locator) -> str:
    """The description a notification shows, as its shadow tree renders it."""
    return notification.evaluate("n => n.shadowRoot.querySelector('.notification p').textContent")


@pytest.mark.browser
@pytest.mark.timeout(120)  # a journey through the Change page, the menu and a reload
def test_a_changes_detail_shows_behind_the_details_switch(tmp_path, monkeypatch, pds, whole_error) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with machine_page(tmp_path, monkeypatch, pds) as w:
        page = w.page
        page.goto(f"{w.base}/?project={w.pid}&change={w.pid}%2F{SLUG}#token=t")
        expect(page.get_by_text(STOPPED).first).to_be_visible()  # the stop says why, switch or not
        expect(page.get_by_text(ALLOW).first).to_be_visible()  # and asks the owner
        expect(page.locator("#improvement-detail")).to_have_count(0)
        page.reload()
        expect(page.get_by_text(STOPPED).first).to_be_visible()  # the switch still off: the reason still shows
        expect(page.locator("#improvement-detail")).to_have_count(0)

        page.get_by_role("button", name="Menu").click()
        menu = page.locator("p-drilldown")
        expect(menu.get_by_role("link", name="Changes")).to_be_focused()  # it opens on the Work level, this page's
        expect(menu.locator("p-switch")).to_have_count(0)  # the switch moved to the Change page
        page.keyboard.press("Escape")
        switch = page.locator("#details-switch")
        expect(switch).to_be_visible()
        switch.click()
        detail = page.locator("#improvement-detail")
        expect(detail.locator("#look-r-note")).to_contain_text("It said done with the week column unchecked.")
        finding = detail.locator("#finding-f-1")
        expect(finding).to_contain_text("done before the week held")
        expect(finding).to_contain_text("Cost: a re-run")

        finding.get_by_role("button", name="Follow up").click()
        expect(pds.modal(page)).to_contain_text("OwlBear adds one backlog entry for f-1")
        pds.answer(page, "Follow up")
        said = "Followed up: Check the export's week column (acme/owlbear-data #1)."  # a reviewed proposal's words
        expect(detail).to_contain_text(said)
        expect(finding.get_by_role("link", name=TEXT["title"])).to_be_visible()
        expect(finding.get_by_role("button", name="Follow up")).to_have_count(0)
        assert (store.queued(), [e.evidence for e in w.backlog.entries.values()]) == ([], [[f"{followups.MARK}f-1"]])

        page.reload()
        expect(page.locator("#improvement-detail #finding-f-1")).to_be_visible()  # the switch stays on
        expect(page.get_by_text(STOPPED).first).to_be_visible()

        page.route("**/improvement/change?*", lambda route: route.fulfill(status=500, body="spotter store unreadable"))
        page.reload()
        expect(page.get_by_text("The Spotter's and Retro's detail could not be read")).to_be_visible()
        expect(page.get_by_text(STOPPED).first).to_be_visible()  # the rest of the page still shows
        page.unroute("**/improvement/change?*")
        monkeypatch.setattr(improvement_view, "change_detail", failing(whole_error))
        page.reload()
        shown = page.locator("#improvement-detail p-inline-notification")
        shown.wait_for()
        pds.settled(page)
        assert described(shown) == f"RuntimeError: {whole_error}"
        expect(page.get_by_text(STOPPED).first).to_be_visible()


def _noted(exc: Exception) -> Exception:
    exc.add_note(NOTE)
    return exc


def _run_line(page: Page, kind: str, rid: str):
    return page.locator("#cases ol.meta > li", has_text=f"{kind} {rid}:")


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_failed_retro_run_shows_its_whole_error(tmp_path, monkeypatch, pds, whole_error) -> None:
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        expected = f"failed: RuntimeError: {whole_error}\n{NOTE}"
        store.run_event("run-failed", "opened", unit=f"chg:{w.pid}:{DONE}", trigger="button", provenance="real")
        store.run_event("run-failed", "ended", result=expected)
        [run] = store.run_states().values()
        page = improvement(w, pds)
        shown = page.locator(f"#run-{run['id']} > p.meta").first
        said = f"{run['unit']} \u00b7 by {run['trigger']} \u00b7 0 calls \u00b7 0.00 credits \u00b7 {expected}"
        assert shown.evaluate("e => e.textContent") == said


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_failed_cases_run_shows_its_whole_error(tmp_path, monkeypatch, pds, whole_error) -> None:
    expected = f"failed: RuntimeError: {whole_error}\n{NOTE}"
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        ids = []
        for task in ("t one", "t two"):
            cid = cases.freeze({"intent": {"task": task}, "recent": [{"tool": "bash", "args": "ls"}]},
                               {"source": "pilot", "family": "f"})  # fmt: skip
            entry = {"stage": "candidate", "call": "none", "why": "why", "example": "", "review": None}
            cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
            ids.append(cid)
        requests = ("check-role", "check-answer")
        with cases.locked():
            for cid, rid in zip(ids, requests, strict=True):
                cases.append(
                    "runs.jsonl",
                    {
                        "id": rid,
                        "kind": "check",
                        "by": "t",
                        "asked": cases.now(),
                        "ids": [cid],
                        "result": expected,
                        "ended": cases.now(),
                    },
                )
        page = improvement(w, pds)
        for cid, rid in zip(ids, requests, strict=True):
            assert _run_line(page, "check", rid).evaluate(BARE) == f" \u00b7 check {rid}: {expected}"
            last = page.locator(f"#case-{cid} p-text", has_text="Its last check")
            assert last.evaluate(BARE) == f"Its last check ({rid}, ): {expected}."


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_failed_replay_look_shows_its_whole_note(tmp_path, monkeypatch, pds, whole_error) -> None:
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        failing = "c-failed"
        rid = "replay-failed"
        note = f"RuntimeError: {whole_error}\n{NOTE}"
        with cases.locked():
            cases.append(
                "runs.jsonl",
                {
                    "id": rid,
                    "kind": "regression",
                    "ended": cases.now(),
                    "result": "failed",
                    "answers": {failing: {"before": {"category": "failed", "note": note}}},
                },
            )
        console: list[str] = []
        w.page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page = improvement(w, pds)
        items = _run_line(page, "regression", rid).locator("ul > li")
        assert items.evaluate_all("els => els.map((e) => e.textContent)") == [f"case {failing}, before: {note}"]
        assert console == []


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_failed_chats_pass_shows_its_whole_error_until_a_pass_succeeds(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    error = f"{whole_error}\n/{'x' * 3000}"  # and an unbroken path component, wider than the page

    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        follower = w.machine.chats
        follower.failed = f"RuntimeError: {error}\n{NOTE}"
        page = improvement(w, pds)
        failed = page.locator("#not-followed #follower-failed")
        expect(failed).to_be_visible()
        said = f"All enrolled chats: the last pass failed, and the next one tries again: RuntimeError: {error}\n{NOTE}"
        assert failed.evaluate("e => e.innerText") == said  # as shown, its lines kept
        assert failed.evaluate("e => e.scrollWidth <= e.clientWidth")  # wrapped, not cut off at the page's edge

        follower.failed = ""
        page.evaluate("document.dispatchEvent(new CustomEvent('owlbear-polled'))")
        expect(page.locator("#not-followed")).to_have_count(0)


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_a_follower_that_cannot_open_its_lock_shows_its_whole_error_and_that_it_stopped(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    error = f"{whole_error}\n/{'x' * 3000}"  # and an unbroken path component, wider than the page
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        w.machine.chats.refused = f"its lock cannot be opened: PermissionError: {error}\n{NOTE}"
        page = improvement(w, pds)
        shown = page.locator("#not-followed #follower-refused")
        said = (
            "All enrolled chats: the follower did not start, and none is followed until OwlBear starts again: "
            f"its lock cannot be opened: PermissionError: {error}\n{NOTE}"
        )
        assert shown.evaluate("e => e.innerText") == said  # as shown, its lines kept
        assert shown.evaluate("e => e.scrollWidth <= e.clientWidth")  # wrapped, not cut off at the page's edge


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_failed_cases_or_retro_pass_and_an_unpublished_sync_show_their_whole_error(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        unpublished = f"the credit limits cannot be read: OSError: {whole_error}\n{NOTE}"
        failed = f"CaseError: {whole_error}\n{NOTE}"
        retro_failed = f"RuntimeError: {whole_error}\n{NOTE}"
        w.machine.cases.failed, w.machine.cases.unpublished = failed, unpublished
        w.machine.retro.failed = retro_failed
        console: list[str] = []
        w.page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
        page = improvement(w, pds)
        shown = page.locator("#cases ol.meta > li")
        assert shown.evaluate_all("els => els.map((e) => e.textContent)") == [
            f"The job's last pass failed, and the next one tries again: {failed}",
            f"Not published, and the next sync tries again: {unpublished}",
        ]
        assert page.locator("#cases-failed").evaluate("e => e.scrollWidth <= e.clientWidth")
        said = page.locator("#retro #retro-failed .meta")
        assert (
            said.evaluate("e => e.textContent")
            == f"Retro's last pass failed, and the next one tries again: {retro_failed}"
        )
        assert said.evaluate("e => e.scrollWidth <= e.clientWidth")
        assert console == []


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_publication_that_did_not_go_through_shows_each_cases_whole_reason(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        ids = ["c-failed", "c-pending"]
        refused, unpushed = ids
        warned = f"saved and committed in {tmp_path / 'shared'}, but not pushed: the push failed: {whole_error}"
        reasons = {refused: f"failed: DataRepoError: {whole_error}\n{NOTE}", unpushed: f"pending: {warned}"}
        expected = "\n".join(f"case {cid}, {reasons[cid]}" for cid in sorted(ids))  # in the order they were written
        with cases.locked():
            cases.append(
                "runs.jsonl",
                {
                    "id": "publication-failed",
                    "kind": "publication",
                    "failed": [refused],
                    "pending": [unpushed],
                    "result": expected,
                    "ended": cases.now(),
                },
            )
        page = improvement(w, pds)
        line = _run_line(page, "publication", "publication-failed")
        assert line.evaluate(BARE) == f" \u00b7 publication publication-failed: {expected}"
        said = line.locator(".said")
        assert said.evaluate("e => e.innerText") == expected  # as shown, its lines kept
        assert said.evaluate("e => e.scrollWidth <= e.clientWidth")


SAID = "e => e.shadowRoot.querySelector('p').textContent"  # a notification's description, as its shadow holds it


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_refusal_and_each_part_that_cannot_be_read_show_their_whole_error(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    error = f"{whole_error}\n{NOTE}"
    fact = cases.fact

    def unread_case(cid: str) -> dict[str, Any]:
        if cid == w.ids["checked"]:
            raise _noted(cases.CaseError(whole_error))
        return fact(cid)

    def unread_settings() -> None:
        raise _noted(registry.RegistryError(whole_error))

    def refused(*_args: object) -> None:
        raise _noted(store.RetroError(whole_error))

    with machine_page(tmp_path, monkeypatch, pds) as w:
        monkeypatch.setattr(cases, "fact", unread_case)
        monkeypatch.setattr(improvement_routes.machine_settings, "current", unread_settings)
        monkeypatch.setattr(followups, "request", refused)
        failing = w.ids["backlog"]
        props.transition(failing, "accepted", "owner")
        props.outcome(failing, "failed", step="backlog", error=f"RetroError: {error}")
        page = improvement(w, pds)
        page.locator("#retro #finding-f-1").get_by_role("button", name="Follow up").click()
        pds.answer(page, "Follow up")
        page.locator("#notice").wait_for()
        switches = '#retro p-inline-notification[heading="Retro\'s switches could not be read"]'
        shown = (
            page.locator("#notice").evaluate(SAID),
            page.locator(switches).evaluate(SAID),
            page.locator(f"#case-{w.ids['checked']} p-inline-notification").evaluate(SAID),
            card(page, failing).locator("ul.meta > li", has_text="Last failure").evaluate(BARE),
        )
        assert shown == (
            f"RetroError: {error}",
            f"the machine's settings cannot be read: RegistryError: {error}",
            f"CaseError: {error}",
            f"Last failure (backlog): RetroError: {error}",
        )


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_a_failed_act_conflict_check_and_withdrawal_show_their_whole_error(
    tmp_path, monkeypatch, pds, whole_error
) -> None:
    error = f"{whole_error}\n{NOTE}"
    with machine_page(tmp_path, monkeypatch, pds, seed=False) as w:
        folder = spotter.root()
        harmed, withdrawn, skipped = "r-harm", "r-unfit", "r-skipped"
        for rid, category, note in (
            (harmed, "irreversible-harm", "Deletes the backups."),
            (withdrawn, "hand-off-fitness", "Done too early."),
            (skipped, "failed", ""),
        ):
            record = spotter.Record(
                id=rid,
                at=NOW.isoformat(),
                project=w.pid,
                change=SLUG,
                step="build",
                session=f"s-{rid}",
                look="hand-off",
                call="call-1",
                cutoff=0,
                probability=1,
                category=category,
                note=note,
                skipped=f"RuntimeError: {error}" if rid == skipped else "",
            )
            spotter.store(folder, record, None)
        withdrawal = f"not taken within 60 s; its withdrawal failed: OSError: {error}"
        for rid, arm, action in ((harmed, "silent", "stop-and-ask"), (withdrawn, "steered", "refuse-hand-off")):
            acts.write(
                folder,
                acts.Act(
                    record=rid,
                    at=NOW.isoformat(),
                    unit=f"chg:{w.pid}/{SLUG}",
                    arm=arm,
                    session=f"s-{rid}",
                    scope="build",
                    look="hand-off",
                    category="irreversible-harm" if rid == harmed else "hand-off-fitness",
                    act=action,
                    why="setting",
                    harm=rid == harmed,
                    delivery="failed" if rid == harmed else "unconfirmed",
                    error=f"OSError: {error}" if rid == harmed else withdrawal,
                    conflict=json.dumps({"failed": f"OSError: {error}"}) if rid == harmed else "",
                ),
            )
        page = improvement(w, pds)
        tag = page.locator(f"#look-{skipped} p-tag").first
        assert tag.evaluate("e => e.textContent") == f"Skipped: RuntimeError: {error}"

        def line(rid: str, start: str) -> str:
            return page.locator(f"#look-{rid} p.meta", has_text=start).evaluate(BARE)

        shown = (line(harmed, "Its error:"), line(harmed, "Decision check:"), line(withdrawn, "Its act:"))
        assert shown == (
            f"Its error: OSError: {error}",
            f"Decision check: failed: OSError: {error}",
            f"Its act: refuse-hand-off, steered arm, unconfirmed ({withdrawal})",
        )
