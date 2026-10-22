"""TD-167, TD-274, TD-139: what a real step session loads, read from the runtime without sending a message.

Run explicitly with ``-m model``: it starts the installed Copilot CLI, opens sessions and runs no model.
"""

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from copilot import CopilotClient, RuntimeConnection
from copilot.generated.rpc import SessionAgentListRequest

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.copilot_cli import cli_path

pytestmark = pytest.mark.model

PROJECT = {
    ".github/agents/proj-agent.agent.md": "---\nname: proj-agent\ndescription: a project agent\n---\nProject agent.\n",
    ".github/skills/proj-skill/SKILL.md": "---\nname: proj-skill\ndescription: a project skill\n---\nProject skill.\n",
    ".github/copilot-instructions.md": "Use tabs.\n",
    "AGENTS.md": "Run make test.\n",
}


def project(root: Path) -> Path:
    for rel, text in PROJECT.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)  # noqa: S603, S607
    return root


def step_options(work: Path) -> dict:
    cfg = sdk_adapter.Session(
        kind=StepKind.BUILD, worktree=work, session_id="probe", message="m", resume=False, policy=Policy(work),
        observe=lambda: Worktree("a" * 40, "b" * 40), checks=(), model=None,
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
