"""A pack session waiting for a slot notices a drain while it waits, so a stopping project is not held forever."""

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.project_host import session_slots


class Slots:
    """Grants a slot on the call *grant_on* (0 never), recording each cancelled claim."""

    def __init__(self, grant_on: int, on_call=None) -> None:
        self.grant_on, self.calls, self.cancelled, self.on_call = grant_on, 0, [], on_call

    def take(self, _project, _key, _want, _limit, _waker) -> bool:
        self.calls += 1
        if self.on_call:
            self.on_call(self.calls)
        return self.calls == self.grant_on

    def cancel(self, project, key) -> None:
        self.cancelled.append((project, key))


def host_with(slots: Slots, tmp_path: Path, drained: threading.Event | None = None) -> SimpleNamespace:
    flag = drained or threading.Event()
    return SimpleNamespace(
        record=SimpleNamespace(project="shop"),
        store=SimpleNamespace(root=tmp_path / "store"),
        slots=slots,
        closed=lambda: False,
        stopped=threading.Event(),
        draining=flag.is_set,
    )


@pytest.fixture
def quick_wait(monkeypatch):
    monkeypatch.setattr(session_slots, "WAIT", 0.01)
    monkeypatch.setattr(session_slots, "limit", lambda _host: 0)  # capacity zero: nothing is ever granted


@pytest.mark.usefixtures("quick_wait")
def test_a_drain_that_starts_while_a_session_waits_for_a_slot_cancels_the_wait(tmp_path):
    drained = threading.Event()
    slots = Slots(grant_on=0, on_call=lambda n: drained.set() if n == 2 else None)
    host = host_with(slots, tmp_path, drained)
    with pytest.raises(pack_files.PackError, match="did not get a session slot"):
        session_slots.admit(host, lambda _msg: None)
    assert slots.calls == 2
    assert [project for project, _key in slots.cancelled] == ["shop"]


@pytest.mark.usefixtures("quick_wait")
def test_a_session_granted_a_slot_before_any_drain_is_admitted(tmp_path):
    slots = Slots(grant_on=3)
    key = session_slots.admit(host_with(slots, tmp_path), lambda _msg: None)
    assert key.startswith(session_slots.PACK)
    assert slots.cancelled == []
