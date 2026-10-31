"""A decision save in flight against an interrupted one (#846): readers say a save is in progress while its writer
holds the lock, and recover only once none does; a chat whose answer was lost settles it without a duplicate."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id
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

    def __init__(self, monkeypatch: pytest.MonkeyPatch, module: object, name: str) -> None:
        self.entered, self.release, self.out = threading.Event(), threading.Event(), {}
        real = getattr(module, name)

        def held(*args: object, **kwargs: object) -> object:
            if threading.current_thread() is self.thread:
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
    return lambda: decision_store.save(shared, decision, expected_revision=None, message=f"decisions: held {decision.id}")


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
