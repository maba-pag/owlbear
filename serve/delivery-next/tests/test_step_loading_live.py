"""TD-167, TD-274, TD-139: what a real step session loads, read from the runtime.

Run explicitly with ``-m model``: it starts the installed Copilot CLI and opens sessions; only the instruction tests
send short messages, to read the system prompts the runtime actually built for a step, a resumed step and its subagent.
The owner's user-config switches (D-01M5YE4P5317N1HWD0QN6N05E0) are read the same way, from a fake Copilot home the
runtime gets as its config folder and Delivery as ``preload.copilot_home()``.
"""

import asyncio
import contextlib
import os
import pwd
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot import CopilotClient, RuntimeConnection
from copilot.generated.rpc import SessionAgentListRequest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_contracts.user_config import USER_OFF, UserConfig
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.runtimes import instruction_scope, sdk_adapter
from owlbear_delivery_next.runtimes.copilot_cli import cli_path

pytestmark = pytest.mark.model

PROJECT = {
    ".github/agents/proj-agent.agent.md": "---\nname: proj-agent\ndescription: a project agent\n---\nProject agent.\n",
    ".github/skills/proj-skill/SKILL.md": "---\nname: proj-skill\ndescription: a project skill\n---\nProject skill.\n",
    ".github/copilot-instructions.md": "Use tabs.\n",
    "AGENTS.md": "Run make test.\n",
}
USER = {  # a user's own instruction files, which load even with config discovery off
    "copilot-instructions.md": "Codeword PELICAN-USER.\n",
    "instructions/x.instructions.md": '---\napplyTo: "**"\n---\nCodeword OTTER-USER.\n',
}
REPO_SCOPED = ".github/instructions/y.instructions.md"
CHEAP = "claude-haiku-4.5"


@pytest.fixture(autouse=True)
def _signed_in(monkeypatch) -> None:
    """The runtime's sign-in is the machine's: the conftest's fake HOME and its cleared COPILOT_HOME would hide it.

    The user files a test reads stay fake: each session gets its own config folder.
    """
    monkeypatch.setenv("HOME", pwd.getpwuid(os.getuid()).pw_dir)


def project(root: Path) -> Path:
    for rel, text in PROJECT.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # noqa: S603, S607
    return root


def step_options(work: Path, *, subagents: bool = False, user: UserConfig = USER_OFF) -> dict:
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD, worktree=work, session_id="probe", message="m", resume=False, policy=Policy(work),
        observe=lambda: Worktree("a" * 40, "b" * 40), checks=(), model=None, subagents=subagents, user=user,
    )  # fmt: skip
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    return {k: v for k, v in opts.items() if k not in {"tools", "on_event", "model", "reasoning_effort"}}


async def loaded(work: Path) -> tuple[list[str], list[str], list[str]]:
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    await client.start()
    try:
        session = await client.create_session(session_id=f"probe-{work.name}", **step_options(work))
        try:
            agents = await session.rpc.agent.list(SessionAgentListRequest())
            skills = await session.rpc.skills.list()
            sources = await session.rpc.instructions.get_sources()
        finally:
            await session.disconnect()
            await client.delete_session(session.session_id)
    finally:
        await client.stop()
    return [a.name for a in agents.agents], sorted(s.name for s in skills.skills), [s.label for s in sources.sources]


def test_a_step_session_loads_its_role_and_delivery_skills_and_the_repositorys_instructions(tmp_path) -> None:
    agents, skills, instructions = asyncio.run(loaded(project(tmp_path / "shop")))

    assert agents == ["owlbear-builder"]  # no project or user agent
    assert skills == sorted(preload.required("builder"))  # no project, user or bundled skill
    assert {".github/copilot-instructions.md", "AGENTS.md"} <= set(instructions)  # conventions still apply (TD-139)


CHILD = "Launch exactly one built-in general-purpose subagent that replies OK, then reply OK."


async def prompts(
    work: Path, home: Path, *, resume: bool = False, ask: str = "Reply OK.", user: tuple[bool, ...] = (False, False)
) -> dict[str, str]:
    """The system prompts a step session built after its scope was applied, by agent ("" is the step itself).

    With ``resume`` the step first runs once, its runtime stops, and only the cold-resumed session's prompts count.
    *user* is the "load user instructions" switch of the first run and of the resumed one.
    """
    opts = step_options(work, subagents=ask == CHILD) | {"config_directory": str(home), "model": CHEAP}
    built: dict[str, str] = {}
    for again, mine in zip((False, True) if resume else (False,), user, strict=False):
        client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
        await client.start()
        try:
            if again:
                session = await client.resume_session(f"scope-{work.name}", **opts)
            else:
                session = await client.create_session(session_id=f"scope-{work.name}", **opts)
            built.clear()
            session.on(lambda ev: built.update({ev.agent_id or "": str(ev.data.content)})
                       if ev.type.value == "system.message" else None)  # fmt: skip
            try:
                await instruction_scope.own(session, work, user_instructions=mine, home=home)
                await session.send_and_wait(ask, timeout=300)
            finally:
                await session.disconnect()  # its state stays in the test's own config folder
        finally:
            await client.stop()
    return built


def scoped_project(tmp_path: Path) -> Path:
    work = project(tmp_path / "shop")
    (work / REPO_SCOPED).parent.mkdir(parents=True)
    (work / REPO_SCOPED).write_text('---\napplyTo: "**"\n---\nCodeword WREN-REPO.\n')
    for rel, text in USER.items():
        (tmp_path / "home" / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "home" / rel).write_text(text)
    return work


def only_the_repositorys(built: str) -> None:
    assert "Use tabs." in built
    assert "Run make test." in built
    assert "WREN-REPO" in built
    assert "PELICAN-USER" not in built
    assert "OTTER-USER" not in built


def test_a_step_keeps_the_repositorys_instructions_and_never_the_users(tmp_path) -> None:
    work = scoped_project(tmp_path)

    only_the_repositorys(asyncio.run(prompts(work, tmp_path / "home"))[""])


def test_a_cold_resumed_step_drops_the_users_instructions_again(tmp_path) -> None:
    work = scoped_project(tmp_path)  # a resumed runtime rebuilds the prompt with every source back on

    only_the_repositorys(asyncio.run(prompts(work, tmp_path / "home", resume=True))[""])


def test_a_steps_general_purpose_subagent_inherits_its_scope(tmp_path) -> None:
    work = scoped_project(tmp_path)  # explore gets no instructions at all; general-purpose gets the step's

    built = asyncio.run(prompts(work, tmp_path / "home", ask=CHILD))

    children = [text for agent, text in built.items() if agent]
    assert children, "the step started no subagent"
    for text in [built[""], *children]:
        only_the_repositorys(text)


LINKED = "HERON-LINKED"  # the owner's instruction file, linked in from his agent-home as its install makes it


def linked_home(tmp_path: Path, monkeypatch) -> Path:
    """The fake Copilot home with a linked instruction file; Delivery reads the same folder as the runtime."""
    home = tmp_path / "home"
    target = tmp_path / "agent-home" / "core.instructions.md"
    target.parent.mkdir(parents=True)
    target.write_text(f'---\napplyTo: "**"\n---\nCodeword {LINKED}.\n')
    (home / "instructions").mkdir(parents=True, exist_ok=True)
    (home / "instructions" / "core.instructions.md").symlink_to(target)
    monkeypatch.setattr(preload, "copilot_home", lambda: home)  # never COPILOT_HOME: the runtime's sign-in stays
    return home


def the_repositorys_and_the_owners(built: str) -> None:
    assert "Use tabs." in built
    assert "Run make test." in built
    assert "WREN-REPO" in built
    assert LINKED in built
    assert "PELICAN-USER" in built  # his copilot-instructions.md
    assert "OTTER-USER" in built  # a plain file of his instructions folder


def test_with_his_switch_on_a_step_keeps_the_owners_instruction_files_beside_the_repositorys(
    tmp_path, monkeypatch
) -> None:
    work = scoped_project(tmp_path)
    home = linked_home(tmp_path, monkeypatch)

    the_repositorys_and_the_owners(asyncio.run(prompts(work, home, user=(True,)))[""])


def test_with_his_switch_off_a_step_drops_his_linked_file_too(tmp_path, monkeypatch) -> None:
    work = scoped_project(tmp_path)
    home = linked_home(tmp_path, monkeypatch)

    built = asyncio.run(prompts(work, home, user=(False,)))[""]

    only_the_repositorys(built)
    assert LINKED not in built


def test_a_step_cold_resumed_after_he_switched_off_drops_his_files(tmp_path, monkeypatch) -> None:
    work = scoped_project(tmp_path)
    home = linked_home(tmp_path, monkeypatch)

    built = asyncio.run(prompts(work, home, resume=True, user=(True, False)))[""]

    only_the_repositorys(built)
    assert LINKED not in built


def test_a_steps_general_purpose_subagent_inherits_his_files_with_the_switch_on(tmp_path, monkeypatch) -> None:
    work = scoped_project(tmp_path)
    home = linked_home(tmp_path, monkeypatch)

    built = asyncio.run(prompts(work, home, ask=CHILD, user=(True,)))

    children = [text for agent, text in built.items() if agent]
    assert children, "the step started no subagent"
    for text in [built[""], *children]:
        the_repositorys_and_the_owners(text)


async def offered(work: Path, home: Path, *, skills: bool) -> dict[str, object]:
    """The skills a step session is offered, by name; no message is sent."""
    user = UserConfig(instructions=False, skills=skills)
    opts = step_options(work, user=user) | {"config_directory": str(home)}
    client = CopilotClient(connection=RuntimeConnection.for_stdio(path=cli_path()))
    await client.start()
    try:
        session = await client.create_session(session_id=f"skills-{work.name}-{skills}", **opts)
        try:
            listed = await session.rpc.skills.list()
        finally:
            await session.disconnect()
            with contextlib.suppress(RuntimeError):  # no message was sent, so the runtime kept no session file
                await client.delete_session(session.session_id)
    finally:
        await client.stop()
    return {s.name: s for s in listed.skills}


@pytest.mark.parametrize("on", [True, False])
def test_the_owners_skill_is_offered_by_its_link_path_only_with_his_switch_on(tmp_path, monkeypatch, on) -> None:
    home = linked_home(tmp_path, monkeypatch)
    target = tmp_path / "agent-home" / "ah-probe"
    target.mkdir()
    (target / "SKILL.md").write_text("---\nname: ah-probe\ndescription: the owner's probe skill\n---\nProbe.\n")
    (home / "skills").mkdir()
    link = home / "skills" / "ah-probe"
    link.symlink_to(target)

    skills = asyncio.run(offered(project(tmp_path / "shop"), home, skills=on))

    assert set(preload.required("builder")) <= set(skills)  # the role's own stay
    if on:
        assert str(skills["ah-probe"].path).startswith(str(link))  # by the link path, not agent-home's
    else:
        assert "ah-probe" not in skills
