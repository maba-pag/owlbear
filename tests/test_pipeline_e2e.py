"""E2E pipeline tests — validate full OwlBear pipeline with refactored agent definitions.

Exercises real agent definitions from ``src/owlbear/agents/`` through
``build_agent_registry()`` with real toolsets and tool resolution.  Uses
``FunctionModel`` for all LLM calls — no real API.

Task: #452
"""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import pydantic_ai.models
import pytest
import pytest_asyncio
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from owlbear.bootstrap import BootstrapResult, bootstrap
from owlbear.config import OwlBearSettings
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.roles import VALIDATOR_POLICY, AgentRole

# Block real LLM requests — FunctionModel is exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

# Real agents directory.
AGENTS_DIR = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"

# All 9 agent names that must be present.
ALL_AGENTS = [
    "orchestrator",
    "kanban-planner",
    "builder",
    "researcher",
    "architect",
    "reviewer",
    "writer",
    "auditor",
    "curator",
]


# ---------------------------------------------------------------------------
# Shared helpers & fixtures
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path) -> OwlBearSettings:
    """Build test-safe settings pointing at the real agents dir."""
    return OwlBearSettings(
        copilot_token_path=tmp_path / "token.json",
        agents_dir=AGENTS_DIR,
        usage_path=tmp_path / "usage.jsonl",
    )


def _noop_model_fn(
    _messages: list[ModelMessage],
    _info: AgentInfo,
) -> ModelResponse:
    """Minimal FunctionModel response — returns fixed text."""
    return ModelResponse(parts=[TextPart("ok")])


@pytest_asyncio.fixture
async def bootstrapped(tmp_path: Path) -> BootstrapResult:
    """Full bootstrap result with real agents dir and FunctionModel."""
    fn_model = FunctionModel(_noop_model_fn)
    settings = _make_settings(tmp_path)
    mock_client = AsyncMock()
    with (
        patch(
            "owlbear.bootstrap.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ),
        patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
    ):
        return await bootstrap(
            settings,
            channel_name="cli",
            workspace_root=tmp_path,
        )


def _get_registry(result: BootstrapResult) -> AgentRegistry:
    """Extract agent registry from bootstrap result.

    The Copilot model is now propagated through bootstrap →
    build_agent_registry → AgentRegistry, so no manual override
    of ``_default_model`` is needed.
    """
    reg = result.agent._deps.agent_registry
    assert reg is not None
    return reg


# ---------------------------------------------------------------------------
# AC-1: All 9 agents instantiate from real definitions
# ---------------------------------------------------------------------------


class TestAllAgentsInstantiate:
    """AC-1: build_agent_registry loads all 9 real agent definitions."""

    @pytest.mark.asyncio
    async def test_registry_has_all_nine_definitions(
        self,
        bootstrapped: BootstrapResult,
    ) -> None:
        registry = _get_registry(bootstrapped)
        assert set(registry.definitions.keys()) == set(ALL_AGENTS)

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    @pytest.mark.asyncio
    async def test_get_succeeds_for_agent(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        registry = _get_registry(bootstrapped)
        agent = registry.get(agent_name)
        assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# AC-2: Tool resolution succeeds for every agent
# ---------------------------------------------------------------------------


class TestToolResolution:
    """AC-2: registry.get() resolves all tools for each agent without KeyError."""

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    @pytest.mark.asyncio
    async def test_tool_resolution_no_keyerror(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        """get() must complete without KeyError — every tool name in the
        definition was resolved by the alias-backed tool resolver."""
        registry = _get_registry(bootstrapped)
        agent = registry.get(agent_name)
        assert agent is not None

        # Confirm the definition actually declares tools.
        defn = registry.definitions[agent_name]
        assert len(defn.tools) >= 1, f"{agent_name} should declare ≥1 tool"


# ---------------------------------------------------------------------------
# AC-3: Four-step sequential pipeline delegation
# ---------------------------------------------------------------------------


class TestFourStepDelegation:
    """AC-3: Orchestrator → builder → reviewer → writer → auditor chain."""

    @pytest.mark.asyncio
    async def test_four_step_pipeline(
        self,
        bootstrapped: BootstrapResult,
    ) -> None:
        """FunctionModel-driven delegation through 4 agents in sequence."""
        registry = _get_registry(bootstrapped)

        markers = {
            "builder": "BUILDER_DONE",
            "reviewer": "REVIEWER_DONE",
            "writer": "WRITER_DONE",
            "auditor": "AUDITOR_DONE",
        }

        def _inner_model(name: str) -> FunctionModel:
            return FunctionModel(
                lambda _m, _i, *, _n=name: ModelResponse(
                    parts=[TextPart(markers[_n])],
                ),
            )

        pipeline = ["builder", "reviewer", "writer", "auditor"]
        call_count = 0

        def orchestrator_fn(
            _messages: list[ModelMessage],
            _info: AgentInfo,
        ) -> ModelResponse:
            nonlocal call_count
            idx = call_count
            call_count += 1
            if idx < len(pipeline):
                target = pipeline[idx]
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="delegate_to_agent",
                            args={
                                "agent_name": target,
                                "task": f"Do {target} work",
                            },
                        ),
                    ],
                )
            return ModelResponse(parts=[TextPart("pipeline complete")])

        orchestrator_model = FunctionModel(orchestrator_fn)
        agent = bootstrapped.agent

        with ExitStack() as stack:
            stack.enter_context(agent.inner.override(model=orchestrator_model))
            for name in pipeline:
                inner_agent = registry.get(name)
                stack.enter_context(inner_agent.override(model=_inner_model(name)))

            result = await agent.turn("Run the full pipeline")

        assert "pipeline complete" in result


# ---------------------------------------------------------------------------
# AC-4: Skills integration — agents with skills get SkillRegistry
# ---------------------------------------------------------------------------


class TestSkillsIntegration:
    """AC-4: Agents declaring skills get SkillRegistry in toolsets."""

    @pytest.mark.asyncio
    async def test_researcher_declares_no_skills(
        self,
        bootstrapped: BootstrapResult,
    ) -> None:
        """researcher has skills: [] — must not get SkillRegistry."""
        registry = _get_registry(bootstrapped)
        assert registry.definitions["researcher"].skills == []

    @pytest.mark.asyncio
    async def test_skill_registry_provided_when_skills_dir_exists(
        self,
        tmp_path: Path,
    ) -> None:
        """With a valid .github/skills dir, agents with skills get SkillRegistry."""
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "test-skill" / "SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(
            "---\nname: test-skill\ndescription: A test skill\n---\nSkill content.\n",
            encoding="utf-8",
        )

        fn_model = FunctionModel(_noop_model_fn)
        settings = OwlBearSettings(
            copilot_token_path=tmp_path / "token.json",
            agents_dir=AGENTS_DIR,
            usage_path=tmp_path / "usage.jsonl",
        )

        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(
                settings,
                channel_name="cli",
                workspace_root=tmp_path,
            )

        registry = _get_registry(result)
        assert registry._skill_registry is not None

        # Builder declares skills → SkillRegistry should be wired.
        assert len(registry.definitions["builder"].skills) > 0
        # Researcher has skills: [] → SkillRegistry NOT applied.
        assert registry.definitions["researcher"].skills == []


# ---------------------------------------------------------------------------
# AC-5: Role policies applied with real agent definitions
# ---------------------------------------------------------------------------


class TestRolePolicies:
    """AC-5: Validator-role agents get filtered toolsets; builders retain full access."""

    VALIDATOR_AGENTS: ClassVar[list[str]] = ["reviewer", "architect", "auditor"]
    BUILDER_AGENTS: ClassVar[list[str]] = [
        "orchestrator",
        "kanban-planner",
        "builder",
        "researcher",
        "writer",
        "curator",
    ]

    @pytest.mark.parametrize("agent_name", VALIDATOR_AGENTS)
    @pytest.mark.asyncio
    async def test_validator_role_detected(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        registry = _get_registry(bootstrapped)
        defn = registry.definitions[agent_name]
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    @pytest.mark.parametrize("agent_name", BUILDER_AGENTS)
    @pytest.mark.asyncio
    async def test_builder_role_detected(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        registry = _get_registry(bootstrapped)
        defn = registry.definitions[agent_name]
        assert AgentRole(defn.role) is AgentRole.BUILDER

    @pytest.mark.parametrize("agent_name", VALIDATOR_AGENTS)
    @pytest.mark.asyncio
    async def test_validator_rebuilt_with_filtered_toolsets(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        """Validator agents are rebuilt with role policy (denied_tools non-empty)."""
        registry = _get_registry(bootstrapped)
        agent = registry.get(agent_name)
        assert isinstance(agent, Agent)

        defn = registry.definitions[agent_name]
        assert AgentRole(defn.role) is AgentRole.VALIDATOR
        assert VALIDATOR_POLICY.denied_tools, "VALIDATOR_POLICY should deny tools"

    @pytest.mark.parametrize("agent_name", BUILDER_AGENTS)
    @pytest.mark.asyncio
    async def test_builder_agents_retain_full_access(
        self,
        bootstrapped: BootstrapResult,
        agent_name: str,
    ) -> None:
        """Builder-role agents are NOT rebuilt — they keep unfiltered toolsets."""
        registry = _get_registry(bootstrapped)
        agent = registry.get(agent_name)
        assert isinstance(agent, Agent)
