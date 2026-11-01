"""The real session opening with a synthetic client: a replacement's CHECK input carries the owner's answer first."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from copilot.rpc import InstructionLocation, ShellInitScriptShell

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
from owlbear_delivery_next.runtimes import command_marks, sdk_adapter, step_input
from owlbear_delivery_next.settings.roles import UserConfig

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

    async def create_session(self, session_id, **opts):  # noqa: ARG002 - the id is the replacement's
        self.opts = opts
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


def test_the_sources_outside_the_worktree_are_off_before_the_first_message(tmp_path, monkeypatch):
    order = []

    async def scoped(_session, worktree, _user, _log):
        order.append(("scoped", worktree))

    monkeypatch.setattr(sdk_adapter, "session_options", scoped)
    _open(tmp_path, _Session(order), order, monkeypatch)

    assert [step[0] for step in order] == ["scoped", "send", "delivered"]
    assert order[0][1] == tmp_path


class _Listing(_Session):
    """A session whose runtime lists instruction sources and records what Delivery sets before the send."""

    def __init__(self, order, sources, *, answer=True):
        super().__init__(order)
        self.answer = answer
        self.sources = [SimpleNamespace(id=i, source_path=p, location=at) for i, p, at in sources]
        self.rpc = SimpleNamespace(instructions=SimpleNamespace(get_sources=self._listed),
                                   options=SimpleNamespace(update=self._update))  # fmt: skip

    async def _listed(self):
        return SimpleNamespace(sources=self.sources)

    async def _update(self, params):
        if params.shell is None:
            self.order.append(("off", params.disabled_instruction_sources))
            return SimpleNamespace(success=True)
        self.order.append(("shell", [(s.path, s.shell) for s in params.shell.init_scripts]))
        if isinstance(self.answer, Exception):
            raise self.answer
        return SimpleNamespace(success=self.answer)

    async def get_events(self):
        return []


class _Resuming(_Client):
    async def get_session_metadata(self, _sid):
        return object()

    async def resume_session(self, _sid, **opts):
        self.opts = opts
        return self.session


def _user_home(tmp_path):
    """A Copilot home whose instruction file is a link, as an agent-home install makes it; and a plugin's file."""
    home, linked = tmp_path / "copilot", tmp_path / "agent-home" / "core.instructions.md"
    (home / "instructions").mkdir(parents=True)
    linked.parent.mkdir()
    linked.write_text("# mine")
    (home / "instructions" / "core.instructions.md").symlink_to(linked)
    (home / "copilot-instructions.md").write_text("# mine too")
    (tmp_path / "plugin.instructions.md").write_text("# a plugin's")
    user, plugin = InstructionLocation.USER, InstructionLocation.PLUGIN
    return home, [
        ("linked", str(linked), user),
        ("root", str(home / "copilot-instructions.md"), user),
        ("plugin", str(tmp_path / "plugin.instructions.md"), plugin),
        ("repo", ".github/copilot-instructions.md", InstructionLocation.REPOSITORY),
    ]


def _opened(tmp_path, monkeypatch, session, *, resume=False, on=False, events=None):  # noqa: PLR0913 - fixtures and scenario
    """The real opening of *session* inside a runner's marking, with the real instruction scope and command marks."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(sdk_adapter, "session_options", command_marks.opened)  # undo conftest's no-op
    monkeypatch.setattr(sdk_adapter, "usage_read", lambda *_a: asyncio.sleep(0, {}))
    cfg = sdk_adapter.Session(
        kind=StepKind.CHECK, worktree=work, session_id="sid", message="check", resume=resume, policy=Policy(work),
        observe=Worktree, checks=(), model="gpt-6-luna", user=UserConfig(instructions=on, skills=False, memory=not on),
        journal=sdk_adapter.Journal(event=(events if events is not None else []).append,
                                    delivered=lambda: session.order.append(("delivered",))),
    )  # fmt: skip
    store = SimpleNamespace(root=tmp_path / "data", log=lambda *_a: None)
    (store.root / "changes" / "c1").mkdir(parents=True)  # as Store.lock makes it
    client = (_Resuming if resume else _Client)(session)

    async def scenario():
        st = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001 - the real opening under test
        return await sdk_adapter._open(client, st)  # noqa: SLF001

    with command_marks.marking(store, object(), "c1"):
        asyncio.run(scenario())
    return store.root / "changes" / "c1" / command_marks.SCRIPT, client


@pytest.mark.parametrize("resume", [False, True])
@pytest.mark.parametrize("on", [True, False])
def test_the_real_scope_keeps_the_owners_files_only_with_his_switch_on_before_the_first_message(
    tmp_path, monkeypatch, resume, on
):
    home, sources = _user_home(tmp_path)
    monkeypatch.setenv("COPILOT_HOME", str(home))
    order, events = [], []
    script, client = _opened(tmp_path, monkeypatch, _Listing(order, sources), resume=resume, on=on, events=events)

    assert client.opts["memory"] == {"enabled": not on}  # the owner's switch, never the runtime's default

    off = ["plugin"] if on else ["linked", "root", "plugin"]
    assert [step[0] for step in order] == ["off", "shell", "send", "delivered"]
    assert order[0][1] == off
    assert order[1][1] == [(str(script), ShellInitScriptShell.BASH)]  # every command marks its group (#752)
    logged = {e["event"]: e["sources"] for e in events if e["event"].startswith("instructions-")}
    assert logged == ({"instructions-off": off, "instructions-user": ["linked", "root"]} if on
                      else {"instructions-off": off})  # fmt: skip


@pytest.mark.parametrize("answer", [False, RuntimeError("the runtime is gone")])
def test_a_refused_or_failed_update_sends_nothing(tmp_path, monkeypatch, answer):
    order = []
    with pytest.raises(RuntimeError, match=r"refused the shell init script|the runtime is gone"):
        _opened(tmp_path, monkeypatch, _Listing(order, [], answer=answer))

    assert [step[0] for step in order] == ["shell"]  # _run ends the step with this error, before any message
