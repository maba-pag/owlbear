"""A decision save in flight against an interrupted one (#846): readers say a save is in progress while its writer
holds the lock, and recover only once none does; a chat whose answer was lost settles it without a duplicate."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from sys import _getframe
from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id
from owlbear_decisions.snapshot import Snapshot
from owlbear_decisions.validate import Entry, Layer
from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.commands import chat_client
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.decision_routes import _linked, _row
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_batch, decision_errors, decision_store, decision_sync
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

PROJECT = "shop-site"
AUTH = {"authorization": "Bearer t"}  # the app's token below
SAVING_SAID = "a decision save is in progress"
ADMIT = chat_client.ADMIT_BY


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    repo = None
    maintenance = None


def make(**changes: object) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": datetime(2026, 10, 21, 9, tzinfo=UTC),
    }  # fmt: skip
    return Decision(**{**fields, **changes})


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    repo = DataRepo(shared_repo[0])
    repo.claim(PROJECT, "github.com/acme/shop-site")
    return repo


@pytest.fixture
def owner(tmp_path, shared) -> TestClient:
    return TestClient(api.create_app(Store(tmp_path / "store", shared, PROJECT), "t", Host()),
                      base_url="http://127.0.0.1", headers=AUTH)  # fmt: skip


class Held:
    """A real save of one decision in a thread, held inside *where* until released."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, module: object, name: str,
                 when: Callable[[], bool] | None = None) -> None:  # fmt: skip
        """Hold the first call that *when* allows, by default the first from this save's own thread."""
        self.entered, self.release, self.out = threading.Event(), threading.Event(), {}
        real, when = getattr(module, name), when or (lambda: threading.current_thread() is self.thread)

        def held(*args: object, **kwargs: object) -> object:
            if not self.entered.is_set() and when():
                self.entered.set()
                assert self.release.wait(30)
            return real(*args, **kwargs)

        monkeypatch.setattr(module, name, held)
        self.thread: threading.Thread | None = None

    def start(self, work: Callable[[], object]) -> Held:
        self.thread = threading.Thread(target=lambda: self.out.setdefault("done", work()))
        self.thread.start()
        assert self.entered.wait(30)
        return self

    def finish(self) -> object:
        self.release.set()
        assert self.thread is not None
        self.thread.join(60)
        return self.out["done"]


@pytest.fixture
def held_publish(monkeypatch) -> Iterator[Held]:
    held = Held(monkeypatch, decision_sync, "publish")
    yield held
    held.release.set()


def saving(shared: DataRepo, decision: Decision) -> Callable[[], object]:
    said = f"decisions: held {decision.id}"
    return lambda: decision_store.save(shared, decision, expected_revision=None, message=said)


def test_a_save_held_in_publish_reads_as_in_progress_never_as_interrupted(shared, owner, held_publish):
    rule = make()
    held_publish.start(saving(shared, rule))

    for read in (decision_store.load, decision_store.file_snapshot):
        with pytest.raises(decision_store.DecisionsUnavailable) as exc:
            read(shared, PROJECT)
        assert exc.value.action != decision_store.RECOVER, str(exc.value)
        assert exc.value.action == decision_store.SAVING
        assert SAVING_SAID in str(exc.value)
    listed = owner.get("/api/next/decisions").json()
    assert (listed["available"], SAVING_SAID in listed["reason"]) == (False, True)
    assert decision_store.SAVING in listed["reason"]
    assert decision_store.RECOVER not in listed["reason"]
    answer, _ = lookup.chat(shared, PROJECT, "Where do notes live?", None)
    assert SAVING_SAID in answer["failed"]
    assert owner.get("/api/next/decisions/recovery").json()["interrupted"] is False

    receipt = held_publish.finish()

    assert (receipt.saved, receipt.committed) == (True, True)
    assert [e.decision.id for e in decision_store.load(shared, PROJECT).snapshot.entries] == [rule.id]
    assert decision_batch.pending(shared) is None


def crashed(shared: DataRepo) -> str:
    """A batch journalled and never ended, as a writer that died leaves it; its generation."""
    decision_id = new_id()
    rows = [(f"{PROJECT}/decisions/{decision_id}.md", None, b"crashed\n")]
    return decision_batch.begin(shared, PROJECT, decision_store.head(shared), "decisions: crashed", [decision_id], rows)


def action(shared: DataRepo) -> str:
    with pytest.raises(decision_store.DecisionsUnavailable) as exc:
        decision_store.load(shared, PROJECT)
    return exc.value.action


def test_a_save_held_before_its_journal_leaves_the_decisions_readable_as_they_are(shared, monkeypatch):
    old = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    assert saving(shared, old)().saved
    held = Held(monkeypatch, decision_sync, "prepare").start(saving(shared, make()))

    assert [e.decision.id for e in decision_store.load(shared, PROJECT).snapshot.entries] == [old.id]
    assert held.finish().saved


def test_a_save_that_ends_between_the_read_and_the_probe_is_read_again_settled(shared, monkeypatch):
    generation, real, probed = crashed(shared), DataRepo.quiet, []

    @contextmanager
    def ended(self: DataRepo) -> Iterator[bool]:
        decision_batch.complete(shared, generation)  # its writer finished just before the lock was probed
        probed.append(generation)
        with real(self) as quiet:
            yield quiet

    monkeypatch.setattr(DataRepo, "quiet", ended)
    assert list(decision_store.load(shared, PROJECT).snapshot.entries) == []
    assert probed == [generation]


def test_a_rebase_is_a_save_in_progress_while_a_writer_holds_the_lock_and_a_repair_after(shared, writing):
    (git_folder(shared) / "rebase-merge").mkdir()
    with writing(shared):
        assert action(shared) == decision_store.SAVING
    assert action(shared) == decision_store.REPAIR


def test_an_unreadable_journal_is_a_save_in_progress_while_a_writer_holds_the_lock_and_its_whole_error_after(
    shared, monkeypatch, writing, whole_error
):
    def unreadable(_shared: DataRepo) -> None:
        raise decision_batch.JournalError(whole_error)

    monkeypatch.setattr(decision_batch, "pending", unreadable)
    with writing(shared), pytest.raises(decision_store.DecisionsUnavailable) as saving_now:
        decision_store.load(shared, PROJECT)
    with pytest.raises(decision_store.DecisionsUnavailable) as after:
        decision_store.load(shared, PROJECT)
    assert (str(saving_now.value), saving_now.value.action) == (decision_errors.IN_PROGRESS, decision_store.SAVING)
    assert (str(after.value), after.value.action) == (f"JournalError: {whole_error}", decision_store.RECOVER)


def test_a_writer_that_reads_under_its_own_lock_meets_an_interrupted_batch(shared):
    crashed(shared)
    with shared.locked():
        assert action(shared) == decision_store.RECOVER


def test_a_probe_where_no_writer_has_made_the_lock_yet_keeps_the_first_one_out(shared):
    lock = git_folder(shared) / data_repo.LOCK
    lock.unlink(missing_ok=True)
    with shared.quiet() as quiet:
        assert quiet is True
        with pytest.raises(data_repo.DataRepoError), shared.locked(wait=0):
            pass
    with shared.locked(wait=0):
        pass


def test_a_probe_of_a_damaged_lock_never_waits(shared):
    lock = git_folder(shared) / data_repo.LOCK
    lock.unlink(missing_ok=True)
    os.mkfifo(lock)
    said: list[object] = []

    def probe() -> None:
        try:
            with shared.quiet() as quiet:
                said.append(quiet)
        except OSError as error:
            said.append(error)

    thread = threading.Thread(target=probe, daemon=True)
    thread.start()
    thread.join(10)
    waited = thread.is_alive()
    if waited:  # a writer frees the probe, so the old code's thread ends
        os.close(os.open(lock, os.O_WRONLY | os.O_NONBLOCK))
    assert (waited, len(said)) == (False, 1)


def test_a_chat_server_and_its_host_read_one_clock():
    before = chat_client._now()  # noqa: SLF001
    code = "import time; print(repr(time.clock_gettime(time.CLOCK_MONOTONIC)))"
    said = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout  # noqa: S603
    assert before <= float(said) <= decision_batch._now()  # noqa: SLF001


def git_folder(shared: DataRepo) -> Path:
    return Path(shared.git("rev-parse", "--absolute-git-dir").stdout.strip())


TITLE = "Notes live in Postgres"
PROPOSAL = {"title": TITLE, "topic": "", "statement": "Notes live in one Postgres table.", "scope": "here",
            "confirmed": True, "rationale": "", "origin": "decided"}  # fmt: skip
REFUSED = PROPOSAL | {"confirmed": False, "origin": "approved"}  # the host refuses it before any save starts
CHAT = AUTH | {"x-owlbear-use": "chat"}


def titled(shared: DataRepo) -> list[str]:
    return [e.decision.id for e in decision_store.load(shared, PROJECT).snapshot.entries if e.decision.title == TITLE]


def state(shared: DataRepo) -> tuple[str, str]:
    return shared.git("rev-parse", "HEAD").stdout, shared.git("status", "--porcelain", "-uall").stdout


def untouched(shared: DataRepo, was: tuple[str, str]) -> None:
    assert state(shared) == was
    assert (decision_batch.pending(shared), titled(shared)) == (None, [])


@pytest.mark.parametrize(
    "case",
    [(-1.0, False), (60.0, True), (None, True), ("soon", False), ("crossing", False)],
    ids=["past", "ahead", "page", "malformed", "crossing-journal-lock"],
)
def test_initial_admission_checks_deadline_at_the_journal_boundary(shared, owner, clock, monkeypatch, case):
    after, saved = case
    was = state(shared)
    if after == "soon":
        assert (
            owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=CHAT | {ADMIT: "soon"}).status_code == 422
        )
        untouched(shared, was)
        return
    if after == "crossing":
        begin = Held(monkeypatch, decision_batch, "_locked", lambda: _getframe(2).f_code.co_name == "begin")
        sent = CHAT | {ADMIT: repr(clock.t + 10)}
        begin.start(lambda: owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=sent))
        clock.t += 11
        assert titled(shared) == []
        out = begin.finish().json()
        assert (out["saved"], out["receipts"][0]["notice"]) == (False, decision_store.LATE)
        untouched(shared, was)
        return
    sent = {} if after is None else {ADMIT: repr(decision_batch._now() + after)}  # noqa: SLF001
    out = owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=CHAT | sent).json()
    assert out["saved"] is saved
    if saved:
        assert titled(shared) == [out["receipts"][0]["id"]]
    else:
        assert out["receipts"][0]["notice"] == decision_store.LATE
        untouched(shared, was)


class Clock:
    """The machine's monotonic clock, as the host's fence and the chat read it; a chat's pause moves it on."""

    def __init__(self) -> None:
        self.t, self.paused = 1000.0, lambda: None

    def __call__(self) -> float:
        return self.t

    def pause(self, seconds: float) -> None:
        self.paused()
        self.t += seconds


@pytest.fixture
def clock(monkeypatch) -> Clock:
    now = Clock()
    for module in (decision_batch, chat_client):
        monkeypatch.setattr(module, "_now", now)
    monkeypatch.setattr(chat_client, "_pause", now.pause)
    return now


def test_admitted_save_can_complete_conflict_flags_after_its_deadline(shared, clock, monkeypatch):
    source = make(state=State.REPLACED)
    rival = make(title="Narrow", links=(Link(type=LinkType.REPLACES, target=source.id),))
    for d in (source, rival):
        assert saving(shared, d)().saved
    real = decision_batch.complete

    def complete(*args: object) -> object:
        clock.t += 100  # the deadline passes once the save's own batch has ended
        return real(*args)

    monkeypatch.setattr(decision_batch, "complete", complete)
    mine = make(title="Wide", links=(Link(type=LinkType.REPLACES, target=source.id),))
    with decision_batch.ADMIT_BY.set(clock.t + 10):
        receipt = saving(shared, mine)()

    assert (receipt.saved, receipt.conflict) == (True, True)
    assert decision_store.load(shared, PROJECT).snapshot.get(rival.id).decision.conflict
    assert "decisions: conflict on" in shared.git("log", "-1", "--format=%s").stdout
    assert decision_batch.pending(shared) is None


class Answer(io.BytesIO):
    status = 200


class Loop:
    """The chat's real requests answered by the real routes; a propose is sent, then its answer is lost to a reset.

    *held* is the save the propose is held in, *after* runs once its request is sent, *served* answers the contract.
    """

    def __init__(self, http: TestClient, *, lose: bool = True, held: Held | None = None,
                 after: Callable[[], object] | None = None, served: dict[str, int] | None = None) -> None:  # fmt: skip
        self.http, self.lose, self.held, self.after, self.served = http, lose, held, after, served
        self.seen, self.got, self.answer = [], [], {}
        self.thread: threading.Thread | None = None

    def open(self, request: urllib.request.Request, timeout: float) -> Answer:
        method, path = request.get_method(), "/" + request.full_url.split("/", 3)[3]
        headers = {k.lower(): v for k, v in request.header_items()}
        self.seen.append((method, path, timeout, headers))
        if path.endswith("/chat/contract") and self.served is not None:
            return Answer(json.dumps(self.served).encode())

        def go() -> httpx.Response:
            return self.http.request(method, path, content=request.data, headers=headers)

        if method == "POST" and self.lose:
            self.thread = threading.Thread(target=lambda: self.answer.setdefault("out", go()))
            self.thread.start()
            if self.held is None:
                self.thread.join(60)
            else:
                assert self.held.entered.wait(30)
            if self.after:
                self.after()
            raise ConnectionResetError(54, "Connection reset by peer")  # after sending: the host may have done it
        r = go()
        self.got.append((path, r.json()))
        if r.status_code != chat_client.OK:
            raise urllib.error.HTTPError(request.full_url, r.status_code, "", Message(), io.BytesIO(r.content))
        return Answer(r.content)


@pytest.fixture
def wire(tmp_path, shared, clock, monkeypatch) -> Callable[..., tuple[chat_client.Chat, Loop]]:  # noqa: ARG001
    """A chat server of this code whose host is the real app, over its real `send`; nothing but the socket is faked."""
    app = api.create_app(Store(tmp_path / "store", shared, PROJECT), "t", Host())
    http = TestClient(app, base_url="http://127.0.0.1")
    found = Host.record.model_copy(update={"token": "t"})

    def chat(**kw: object) -> tuple[chat_client.Chat, Loop]:
        loop = Loop(http, **kw)
        monkeypatch.setattr(chat_client, "_LOCAL", loop)
        made = chat_client.Chat(Path("shop"), tmp_path)
        monkeypatch.setattr(made, "record", lambda: found)
        return made, loop

    return chat


@pytest.mark.parametrize("kind", ["answered", "lost-after-publication", "late-before-admission"])
def test_chat_save_is_sent_once_and_settles_saved_or_late(shared, wire, clock, monkeypatch, kind):
    if kind == "answered":
        chat, loop = wire(lose=False)
        out = chat.propose(PROPOSAL)
        assert (out["saved"], titled(shared)) == (True, [out["receipts"][0]["id"]])
        (_, _, timeout, headers), = [s for s in loop.seen if s[0] == "POST"]  # fmt: skip
        assert (timeout, float(headers[ADMIT.lower()])) == (chat_client.WRITE, clock.t + chat_client.ADMIT)
        return
    if kind == "late-before-admission":
        held = Held(monkeypatch, decision_sync, "prepare", lambda: True)
        chat, loop = wire(held=held)
        admit_by, times = clock.t + chat_client.ADMIT, []
        clock.paused = lambda: times.append(clock.t)
        out = chat.propose(PROPOSAL)
        assert (out["saved"], out["error"]) == (False, chat_client.NOT_SAVED)
        assert len(times) > chat_client.ADMIT // chat_client.POLL
        assert max(times) <= admit_by < clock.t
        held.release.set()
        loop.thread.join(60)
        answered = loop.answer["out"].json()
        assert (answered["saved"], answered["receipts"][0]["notice"]) == (False, decision_store.LATE)
        assert titled(shared) == []
        assert len([s for s in loop.seen if s[0] == "POST"]) == 1
        return
    held = Held(monkeypatch, decision_sync, "publish", lambda: True)
    chat, loop = wire(held=held)
    admit_by = clock.t + chat_client.ADMIT
    clock.paused = lambda: (held.release.set(), loop.thread.join(60))

    out = chat.propose(PROPOSAL)

    assert out["saved"] is True
    assert len(titled(shared)) == 1
    assert out["receipts"] == [{"id": titled(shared)[0], "saved": True}]
    assert out["notice"] == chat_client.SAVED.format(id=titled(shared)[0])
    first = next(out for path, out in loop.got if path.startswith("/api/next/decisions?"))
    assert (first["available"], decision_store.SAVING in first["reason"]) == (False, True)
    (_, _, timeout, headers), = [s for s in loop.seen if s[0] == "POST"]  # fmt: skip
    assert (timeout, float(headers[ADMIT.lower()])) == (chat_client.WRITE, admit_by)
    assert (headers["authorization"], headers["x-owlbear-use"]) == ("Bearer t", "chat")
    assert headers[chat_contract.HEADER.lower()] == str(chat_contract.CHAT)
    assert not [s for s in loop.seen if "recovery" in s[1]]


def shown(decision, root):
    """The route's actual row and linked-detail producers, without a host or publication."""
    entry = Entry(root / f"{decision.id}.md", Layer(root, decision.scope, decision.project, decision.change), decision)
    view = decision_store.DataView(Snapshot(root, PROJECT, (), (entry,), ()), "a" * 40)
    row = _row(view, entry)
    return row | {"links": _linked(view, entry)[0], "rationale": decision.rationale}


@pytest.mark.parametrize("kind", ["global", "change", "older", "clock-back", "edited-draft", "equal", "newer"])
def test_lost_answer_matching_distinguishes_layer_age_and_changed_rows(tmp_path, monkeypatch, clock, kind):
    started = datetime(2026, 10, 21, 9, tzinfo=UTC)
    body = PROPOSAL | ({"confirmed": False} if kind == "edited-draft" else {})
    fields = {"title": TITLE, "statement": PROPOSAL["statement"], "origin": Origin.DECIDED, "created_at": started}
    if kind in {"global", "change"}:
        fields |= (
            {"scope": Scope.GLOBAL, "project": ""}
            if kind == "global"
            else {"scope": Scope.CHANGE, "change": "notes-move", "state": State.DRAFT}
        )
    elif kind == "older":
        fields["created_at"] = started - timedelta(days=1)
    elif kind == "clock-back":
        started += timedelta(hours=1)
    elif kind == "edited-draft":
        fields |= {"title": "Notes in two tables", "state": State.DRAFT, "origin": Origin.AUTONOMOUS}
    elif kind == "newer":
        fields["created_at"] += timedelta(seconds=1)
    row = shown(make(**fields), tmp_path)
    chat, calls = chat_client.Chat(Path("shop"), tmp_path), []

    def read(method, path):
        calls.append((method, path))
        return (200, {"available": True, "decisions": [row]}) if path.startswith("/decisions?") else (200, row)

    monkeypatch.setattr(chat, "call", read)
    method = "_settled"
    out = getattr(chat, method)(body, started, clock.t - 1, fenced=True)
    assert calls[0] == ("GET", "/decisions?where=all&retired=true")
    if kind in {"global", "change"}:
        assert out == {"saved": False, "error": chat_client.NOT_SAVED}
    elif kind in {"older", "clock-back", "edited-draft"}:
        why = chat_client.CHANGED if kind == "edited-draft" else chat_client.OLDER
        assert out == {"saved": None, "error": chat_client.UNCLEAR.format(why=why.format(ids=row["id"]))}
    else:
        assert out["saved"] is True
        assert out["receipts"] == [{"id": row["id"], "saved": True}]
        assert calls[1] == ("GET", f"/decisions/{row['id']}")


@pytest.mark.parametrize(
    "kind", ["matching", "wrong-link", "wrong-state", "wrong-origin", "withdrawn", "reworded-draft"]
)
def test_found_decision_requires_current_matching_detail(tmp_path, monkeypatch, kind):
    body = PROPOSAL | ({"confirmed": False} if kind in {"wrong-link", "reworded-draft"} else {})
    decision = make(title=TITLE, statement=PROPOSAL["statement"], origin=Origin.DECIDED)
    if not body["confirmed"]:
        decision = decision.model_copy(update={"state": State.DRAFT, "origin": Origin.AUTONOMOUS})
    row = shown(decision, tmp_path)
    changes = {
        "matching": {},
        "wrong-link": {"links": (Link(type=LinkType.REPLACES, target=new_id()),)},
        "wrong-state": {"state": State.DRAFT},
        "wrong-origin": {"origin": Origin.APPROVED},
        "withdrawn": {"state": State.WITHDRAWN},
        "reworded-draft": {"statement": "Notes live in two Postgres tables."},
    }[kind]
    detail = shown(decision.model_copy(update=changes), tmp_path)
    chat, calls = chat_client.Chat(Path("shop"), tmp_path), []

    def read(method, path):
        calls.append((method, path))
        return 200, detail

    monkeypatch.setattr(chat, "call", read)
    method = "_found"
    out = getattr(chat, method)(body, [row])
    assert calls == [("GET", f"/decisions/{row['id']}")]
    assert detail["id"] == row["id"]
    if kind == "matching":
        assert out["saved"] is True
    else:
        assert out == {
            "saved": None,
            "error": chat_client.UNCLEAR.format(why=f"{row['id']} matches it in part; ask the owner"),
        }


def test_a_host_without_the_fence_never_has_a_lost_save_called_not_saved(wire):
    chat, _ = wire(served={"supported": [chat_contract.CHAT]})
    out = chat.propose(REFUSED)
    assert (out["saved"], out["error"]) == (None, chat_client.UNCLEAR.format(why=chat_client.UNFENCED))
    assert chat.fenced is False


def test_a_crash_or_a_save_that_never_ends_is_unclear(shared, wire, clock, writing):
    chat, _ = wire(after=lambda: crashed(shared))
    out = chat.propose(REFUSED)
    assert (out["saved"], "ask the owner" in out["error"]) == (None, True)
    assert decision_store.RECOVER in out["error"]

    chat, _ = wire()
    started = clock.t
    with writing(shared):
        out = chat.propose(REFUSED)
    assert (out["saved"], out["error"]) == (None, chat_client.UNCLEAR.format(why=chat_client.STILL_SAVING))
    assert clock.t > started + chat_client.ADMIT + chat_client.SETTLE
