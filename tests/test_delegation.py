"""Tests for DelegationToolset — orchestrator dispatches subtasks to inner agents.

Covers: successful delegation, agent not found, max depth exceeded,
inner agent exception, usage passthrough, depth increment, and
registry=None handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.core.delegation import MAX_DELEGATION_DEPTH, DelegationToolset
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps(
    *,
    depth: int = 0,
    registry: MagicMock | None = None,
) -> OwlBearDeps:
    """Create OwlBearDeps with configurable delegation depth and registry."""
    return OwlBearDeps(
        hooks=HookRegistry(),
        agent_registry=registry,
        delegation_depth=depth,
    )


def _make_ctx(
    deps: OwlBearDeps,
    *,
    usage: MagicMock | None = None,
) -> MagicMock:
    """Create a mock RunContext[OwlBearDeps] with given deps and usage."""
    ctx = MagicMock()
    ctx.deps = deps
    ctx.usage = usage or MagicMock()
    return ctx


def _make_registry(
    agents: dict[str, MagicMock] | None = None,
) -> MagicMock:
    """Create a mock AgentRegistry with configurable get() behavior."""
    registry = MagicMock()

    if agents is None:
        agents = {}

    def _get(name: str) -> MagicMock:
        if name not in agents:
            available = ", ".join(sorted(agents))
            msg = f"Agent '{name}' not found. Available: {available}"
            raise KeyError(msg)
        return agents[name]

    registry.get.side_effect = _get
    registry.definitions = {name: MagicMock() for name in agents}
    return registry


def _make_agent(output: str = "result") -> MagicMock:
    """Create a mock PydanticAI Agent whose run() returns a result with .output."""
    agent = MagicMock()
    result = MagicMock()
    result.output = output
    agent.run = AsyncMock(return_value=result)
    return agent


# ---------------------------------------------------------------------------
# Toolset registration
# ---------------------------------------------------------------------------


class TestDelegationToolsetRegistration:
    """DelegationToolset registers the delegate_to_agent tool."""

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = DelegationToolset()
        assert isinstance(ts, FunctionToolset)

    def test_registers_delegate_to_agent(self) -> None:
        ts = DelegationToolset()
        assert "delegate_to_agent" in ts.tools

    def test_single_tool_registered(self) -> None:
        ts = DelegationToolset()
        assert len(ts.tools) == 1


# ---------------------------------------------------------------------------
# MAX_DELEGATION_DEPTH constant
# ---------------------------------------------------------------------------


class TestMaxDelegationDepth:
    """Module constant for maximum delegation depth."""

    def test_default_value_is_five(self) -> None:
        assert MAX_DELEGATION_DEPTH == 5


# ---------------------------------------------------------------------------
# Successful delegation
# ---------------------------------------------------------------------------


class TestSuccessfulDelegation:
    """delegate_to_agent dispatches to inner agent and returns output."""

    @pytest.mark.asyncio
    async def test_returns_inner_agent_output(self) -> None:
        inner_agent = _make_agent(output="task completed")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="do stuff"))

        assert result == "task completed"

    @pytest.mark.asyncio
    async def test_calls_agent_run_with_task(self) -> None:
        inner_agent = _make_agent(output="ok")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await (ts._delegate(ctx, agent_name="builder", task="build feature X"))

        inner_agent.run.assert_called_once()
        call_args = inner_agent.run.call_args
        assert call_args[0][0] == "build feature X"


# ---------------------------------------------------------------------------
# Usage passthrough
# ---------------------------------------------------------------------------


class TestUsagePassthrough:
    """Usage object is passed through to inner agent via usage= kwarg."""

    @pytest.mark.asyncio
    async def test_passes_ctx_usage_to_inner_agent(self) -> None:
        usage = MagicMock()
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps, usage=usage)
        ts = DelegationToolset()

        await (ts._delegate(ctx, agent_name="builder", task="do it"))

        call_kwargs = inner_agent.run.call_args[1]
        assert call_kwargs["usage"] is usage


# ---------------------------------------------------------------------------
# Depth increment
# ---------------------------------------------------------------------------


class TestDepthIncrement:
    """Delegation increments delegation_depth in inner deps."""

    @pytest.mark.asyncio
    async def test_increments_depth_by_one(self) -> None:
        inner_agent = _make_agent(output="ok")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=2, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await (ts._delegate(ctx, agent_name="builder", task="sub task"))

        call_kwargs = inner_agent.run.call_args[1]
        inner_deps = call_kwargs["deps"]
        assert inner_deps.delegation_depth == 3

    @pytest.mark.asyncio
    async def test_does_not_mutate_original_deps(self) -> None:
        inner_agent = _make_agent(output="ok")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=1, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await (ts._delegate(ctx, agent_name="builder", task="sub task"))

        assert deps.delegation_depth == 1


# ---------------------------------------------------------------------------
# Agent not found
# ---------------------------------------------------------------------------


class TestAgentNotFound:
    """delegate_to_agent returns error string when agent is not found."""

    @pytest.mark.asyncio
    async def test_returns_error_string(self) -> None:
        registry = _make_registry(agents={"reviewer": _make_agent()})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="do it"))

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "builder" in result

    @pytest.mark.asyncio
    async def test_does_not_raise(self) -> None:
        registry = _make_registry(agents={})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        # Should not raise
        result = await (ts._delegate(ctx, agent_name="nonexistent", task="x"))
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Max depth exceeded
# ---------------------------------------------------------------------------


class TestMaxDepthExceeded:
    """delegate_to_agent returns error string when max depth is reached."""

    @pytest.mark.asyncio
    async def test_returns_error_at_max_depth(self) -> None:
        inner_agent = _make_agent()
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=MAX_DELEGATION_DEPTH, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="deep"))

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "depth" in result.lower()

    @pytest.mark.asyncio
    async def test_inner_agent_not_called(self) -> None:
        inner_agent = _make_agent()
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=MAX_DELEGATION_DEPTH, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await (ts._delegate(ctx, agent_name="builder", task="deep"))

        inner_agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_error_above_max_depth(self) -> None:
        inner_agent = _make_agent()
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=MAX_DELEGATION_DEPTH + 3, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="deep"))

        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# Inner agent exception
# ---------------------------------------------------------------------------


class TestInnerAgentException:
    """delegate_to_agent catches inner agent exceptions and returns error string."""

    @pytest.mark.asyncio
    async def test_returns_error_string_on_exception(self) -> None:
        inner_agent = _make_agent()
        inner_agent.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="do it"))

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "LLM timeout" in result

    @pytest.mark.asyncio
    async def test_does_not_raise(self) -> None:
        inner_agent = _make_agent()
        inner_agent.run = AsyncMock(side_effect=ValueError("bad input"))
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        # Should not raise
        result = await (ts._delegate(ctx, agent_name="builder", task="x"))
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Registry is None
# ---------------------------------------------------------------------------


class TestRegistryIsNone:
    """delegate_to_agent returns error when agent_registry is None."""

    @pytest.mark.asyncio
    async def test_returns_error_string(self) -> None:
        deps = _make_deps(registry=None)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await (ts._delegate(ctx, agent_name="builder", task="do it"))

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "registry" in result.lower()
