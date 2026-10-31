"""A decision save in flight against an interrupted one (#846): readers say a save is in progress while its writer
holds the lock, and recover only once none does; a chat whose answer was lost settles it without a duplicate."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts import chat_contract
from owlbear_delivery_next.commands import chat_client
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_batch, decision_store, decision_sync
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


def made_now(shared: DataRepo, **changes: object) -> Callable[[], None]:
    """Save a decision made when it is called: after the chat's propose started."""

    def save() -> None:
        assert saving(shared, make(**changes, created_at=datetime.now(UTC)))().saved

    return save


def withdraw(shared: DataRepo) -> None:
    """The owner withdraws the one decision titled like the chat's."""
    made = decision_store.load(shared, PROJECT).snapshot.get(titled(shared)[0]).decision
    gone = made.model_copy(update={"state": State.WITHDRAWN})
    assert decision_store.save(shared, gone, expected_revision=made.revision, message="decisions: gone").saved


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


def test_a_writer_that_reads_under_its_own_lock_meets_an_interrupted_batch(shared):
    crashed(shared)
    with shared.locked():
        assert action(shared) == decision_store.RECOVER


def test_probing_the_lock_makes_no_lock_file(shared):
    lock = git_folder(shared) / data_repo.LOCK
    lock.unlink(missing_ok=True)
    with shared.quiet() as quiet:
        assert quiet is True
    assert not lock.exists()


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


@pytest.mark.parametrize(("after", "saved"), [(-1.0, False), (60.0, True), (None, True)], ids=["past", "ahead", "page"])
def test_a_save_past_its_chats_deadline_is_refused_before_anything_is_written(shared, owner, after, saved):
    was = state(shared)
    sent = {} if after is None else {ADMIT: repr(decision_batch._now() + after)}  # noqa: SLF001
    out = owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=CHAT | sent).json()
    assert out["saved"] is saved
    if saved:
        assert titled(shared) == [out["receipts"][0]["id"]]
    else:
        assert out["receipts"][0]["notice"] == decision_store.LATE
        untouched(shared, was)


def test_a_deadline_that_is_not_a_time_is_refused(shared, owner):
    was = state(shared)
    assert owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=CHAT | {ADMIT: "soon"}).status_code == 422
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


def test_a_save_that_reaches_its_journal_after_the_deadline_writes_nothing(shared, owner, clock, monkeypatch):
    was = state(shared)
    begin = Held(monkeypatch, decision_batch, "_locked", lambda: sys._getframe(2).f_code.co_name == "begin")  # noqa: SLF001
    sent = CHAT | {ADMIT: repr(clock.t + 10)}
    begin.start(lambda: owner.post("/api/next/decisions/propose", json=PROPOSAL, headers=sent))
    clock.t += 11

    assert titled(shared) == []  # read past the deadline, while the save holds the lock before its journal
    out = begin.finish().json()

    assert (out["saved"], out["receipts"][0]["notice"]) == (False, decision_store.LATE)
    untouched(shared, was)


def test_a_save_admitted_in_time_still_flags_its_competitors_after_the_deadline(shared, clock, monkeypatch):
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


def test_an_answered_save_waits_for_its_answer_and_names_its_deadline(shared, wire, clock):
    chat, loop = wire(lose=False)
    out = chat.propose(PROPOSAL)
    assert (out["saved"], titled(shared)) == (True, [out["receipts"][0]["id"]])
    (_, _, timeout, headers), = [s for s in loop.seen if s[0] == "POST"]  # fmt: skip
    assert (timeout, float(headers[ADMIT.lower()])) == (chat_client.WRITE, clock.t + chat_client.ADMIT)


def test_a_save_whose_answer_was_lost_is_found_saved_once_it_settles(shared, wire, clock, monkeypatch):
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


def test_a_save_held_past_its_deadline_is_refused_and_the_chat_says_not_saved_only_after_it(
    shared, wire, clock, monkeypatch
):
    held = Held(monkeypatch, decision_sync, "prepare", lambda: True)
    chat, loop = wire(held=held)
    admit_by, times = clock.t + chat_client.ADMIT, []
    clock.paused = lambda: times.append(clock.t)

    out = chat.propose(PROPOSAL)

    assert (out["saved"], out["error"]) == (False, chat_client.NOT_SAVED)
    assert len(times) > chat_client.ADMIT // chat_client.POLL  # read again until the deadline, answered only after it
    assert max(times) <= admit_by < clock.t
    held.release.set()
    loop.thread.join(60)
    answered = loop.answer["out"].json()
    assert (answered["saved"], answered["receipts"][0]["notice"]) == (False, decision_store.LATE)
    assert titled(shared) == []
    assert len([s for s in loop.seen if s[0] == "POST"]) == 1


def test_a_decision_like_it_in_another_layer_is_never_taken_for_it(shared, wire):
    chat, _ = wire(after=made_now(shared, title=TITLE, statement=PROPOSAL["statement"], scope=Scope.GLOBAL, project=""))

    out = chat.propose(REFUSED)

    assert (out["saved"], out["error"]) == (False, chat_client.NOT_SAVED)


def test_a_decision_like_it_made_before_it_was_sent_is_never_taken_for_it_nor_called_not_saved(shared, wire):
    older = make(title=TITLE, statement=PROPOSAL["statement"])
    assert saving(shared, older)().saved
    chat, _ = wire()
    out = chat.propose(REFUSED)
    assert (out["saved"], out["error"]) == (None, unclear(older.id))


def unclear(ids: str) -> str:
    return chat_client.UNCLEAR.format(why=chat_client.OLDER.format(ids=ids))


def test_a_save_that_reads_as_made_before_it_was_sent_after_the_clock_went_back_is_unclear(shared, wire, monkeypatch):
    back = SimpleNamespace(now=lambda tz: datetime.now(tz) + timedelta(hours=1), fromisoformat=datetime.fromisoformat)
    monkeypatch.setattr(chat_client, "datetime", back)  # the propose started an hour "after" its save
    chat, _ = wire()
    out = chat.propose(PROPOSAL)
    (made,) = titled(shared)
    assert (out["saved"], out["error"]) == (None, unclear(made))


def test_a_found_decision_that_is_not_the_one_sent_is_unclear_never_saved(shared, wire):
    chat, _ = wire(after=lambda: withdraw(shared))
    out = chat.propose(PROPOSAL)
    assert out["saved"] is None
    assert decision_store.load(shared, PROJECT).snapshot.entries[0].decision.id in out["error"]

    other = make(title="Notes use UTC", statement="All note timestamps use UTC.")
    assert saving(shared, other)().saved
    rival, link = new_id(), (Link(type=LinkType.REPLACES, target=other.id),)
    chat, _ = wire(after=made_now(shared, id=rival, title=TITLE, statement=PROPOSAL["statement"], state=State.DRAFT,
                                  links=link))  # fmt: skip
    out = chat.propose(REFUSED)
    assert (out["saved"], rival in out["error"]) == (None, True)


def test_a_found_decision_the_owner_withdraws_before_its_detail_is_read_is_unclear(shared, wire, monkeypatch):
    chat, _ = wire()
    read = chat.call

    def call(method: str, path: str, *args: object, **kwargs: object) -> object:
        if method == "GET" and path.startswith("/decisions/"):  # the list found it; its detail is read next
            withdraw(shared)
        return read(method, path, *args, **kwargs)

    monkeypatch.setattr(chat, "call", call)
    out = chat.propose(PROPOSAL)
    assert (out["saved"], titled(shared)[0] in out["error"]) == (None, True)


def test_a_host_without_the_fence_never_has_a_lost_save_called_not_saved(wire):
    chat, _ = wire(served={"supported": [2]})
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
