"""The real session opening with a synthetic client: a replacement's CHECK input carries the owner's answer first."""

import asyncio
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Change,
    Option,
    PersonCheck,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.runtimes import sdk_adapter, step_input

AT = datetime(2026, 10, 24, tzinfo=UTC)
ANSWER = "Which language should the page use?"


class _Session:
    def __init__(self, order, *, refuse=False):
        self.order, self.refuse = order, refuse

    async def send(self, message, **_extra):
        self.order.append(("send", message))
        if self.refuse:
            msg = "send refused"
            raise RuntimeError(msg)


class _Client:
    """Reports no session for the resumed id, so the opening replaces it with a fresh one."""

    def __init__(self, session):
        self.session = session

    async def get_session_metadata(self, _sid):
        return None

    async def list_models(self):
        return []

    async def create_session(self, session_id, **_opts):  # noqa: ARG002 - the id is the replacement's
        return self.session


def _check_change():
    question = Question(
        id="q1",
        step=StepKind.CHECK,
        text=ANSWER,
        options=[Option(id="en", label="English")],
        answer=Answer(option="en", at=AT),
    )
    return Change(
        slug="greet",
        questions=[question],
        checks=[PersonCheck(id="p1", steps=["open the page"])],
        plan=Plan(tasks=[Task(id="p1", title="Check the page")]),
        step=Step(kind=StepKind.CHECK, task="p1"),
    )


def _open(tmp_path, session, order, monkeypatch):
    monkeypatch.setattr(sdk_adapter.preload, "missing", lambda *_a, **_k: [])
    told = step_input.session(_check_change(), Profile(), tmp_path, {}).message
    journal = sdk_adapter.Journal(delivered=lambda: order.append(("delivered",)), replaced=lambda: "fresh-sid")
    cfg = sdk_adapter.Session(
        kind=StepKind.CHECK,
        worktree=tmp_path,
        session_id="old-sid",
        message="check",
        resume=True,
        policy=Policy(tmp_path),
        observe=Worktree,
        checks=(),
        model="gpt-6-luna",
        fresh=told,
        journal=journal,
    )

    async def scenario():
        st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001 - the real opening under test
        return await sdk_adapter._open(_Client(session), st)  # noqa: SLF001

    return asyncio.run(scenario())


def test_a_replacement_check_sends_the_pending_owner_answer_before_it_is_acknowledged(tmp_path, monkeypatch):
    order = []
    _open(tmp_path, _Session(order), order, monkeypatch)

    assert [step[0] for step in order] == ["send", "delivered"]
    sent = order[0][1]
    assert f"- {ANSWER}: English" in sent


def test_a_refused_first_send_is_never_acknowledged_as_delivered(tmp_path, monkeypatch):
    order = []
    with pytest.raises(RuntimeError, match="send refused"):
        _open(tmp_path, _Session(order, refuse=True), order, monkeypatch)

    assert [step[0] for step in order] == ["send"]
