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

        result = await ts._delegate(ctx, agent_name="builder", task="do stuff")

        assert result == "task completed"

    @pytest.mark.asyncio
    async def test_calls_agent_run_with_task(self) -> None:
        inner_agent = _make_agent(output="ok")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="build feature X")

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

        await ts._delegate(ctx, agent_name="builder", task="do it")

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

        await ts._delegate(ctx, agent_name="builder", task="sub task")

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

        await ts._delegate(ctx, agent_name="builder", task="sub task")

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

        result = await ts._delegate(ctx, agent_name="builder", task="do it")

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
        result = await ts._delegate(ctx, agent_name="nonexistent", task="x")
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

        result = await ts._delegate(ctx, agent_name="builder", task="deep")

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

        await ts._delegate(ctx, agent_name="builder", task="deep")

        inner_agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_error_above_max_depth(self) -> None:
        inner_agent = _make_agent()
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=MAX_DELEGATION_DEPTH + 3, registry=registry)
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        result = await ts._delegate(ctx, agent_name="builder", task="deep")

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

        result = await ts._delegate(ctx, agent_name="builder", task="do it")

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
        result = await ts._delegate(ctx, agent_name="builder", task="x")
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

        result = await ts._delegate(ctx, agent_name="builder", task="do it")

        assert isinstance(result, str)
        assert "error" in result.lower()
        assert "registry" in result.lower()


# ---------------------------------------------------------------------------
# Runtime instructions passthrough
# (AC: _delegate passes task, usage=, depth, AND instructions= together)
# ---------------------------------------------------------------------------


class TestFromAC_RuntimeInstructionsKwarg:
    """_delegate() passes instructions= and metadata= kwargs to agent.run().

    These tests lock the full run-call contract: the delegated task must remain
    the positional first argument, usage= and incremented depth must still be
    forwarded, AND per-run instructions= must be added when a dispatch context
    is present on ctx.deps.
    """

    @pytest.mark.asyncio
    async def test_run_call_has_task_usage_depth_and_instructions(self) -> None:
        """agent.run() receives positional task, usage=, incremented depth, and instructions=."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(depth=0, registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/project"
        dispatch_ctx.channel_name = "slack"
        deps.dispatch_context = dispatch_ctx
        usage = MagicMock()
        ctx = _make_ctx(deps, usage=usage)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="implement feature")

        call = inner_agent.run.call_args
        assert call[0][0] == "implement feature"  # positional task
        assert call[1]["usage"] is usage  # usage= forwarded
        assert call[1]["deps"].delegation_depth == 1  # depth incremented
        assert "instructions" in call[1]  # per-run instructions=

    @pytest.mark.asyncio
    async def test_instructions_kwarg_is_nonempty_string(self) -> None:
        """instructions= kwarg value is a non-empty string."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/my/workspace"
        dispatch_ctx.channel_name = "cli"
        deps.dispatch_context = dispatch_ctx
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="task body")

        call_kwargs = inner_agent.run.call_args[1]
        assert isinstance(call_kwargs["instructions"], str)
        assert len(call_kwargs["instructions"]) > 0

    @pytest.mark.asyncio
    async def test_instructions_contains_workspace_root(self) -> None:
        """instructions= text includes the workspace_root value from dispatch context."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/special/workspace/path"
        dispatch_ctx.channel_name = "slack"
        deps.dispatch_context = dispatch_ctx
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="task")

        call_kwargs = inner_agent.run.call_args[1]
        assert "/special/workspace/path" in call_kwargs["instructions"]

    @pytest.mark.asyncio
    async def test_instructions_contains_channel_name(self) -> None:
        """instructions= text includes the channel_name value from dispatch context."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/project"
        dispatch_ctx.channel_name = "my-special-channel"
        deps.dispatch_context = dispatch_ctx
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="task")

        call_kwargs = inner_agent.run.call_args[1]
        assert "my-special-channel" in call_kwargs["instructions"]

    @pytest.mark.asyncio
    async def test_passes_metadata_kwarg_to_agent_run(self) -> None:
        """agent.run() receives a metadata= kwarg when dispatch context has task fields."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/project"
        dispatch_ctx.channel_name = "slack"
        dispatch_ctx.task_id = "958"
        deps.dispatch_context = dispatch_ctx
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="do work")

        call_kwargs = inner_agent.run.call_args[1]
        assert "metadata" in call_kwargs

    @pytest.mark.asyncio
    async def test_metadata_contains_task_id_when_set(self) -> None:
        """metadata= dict contains task_id when dispatch context has task_id."""
        inner_agent = _make_agent(output="done")
        registry = _make_registry(agents={"builder": inner_agent})
        deps = _make_deps(registry=registry)
        dispatch_ctx = MagicMock()
        dispatch_ctx.workspace_root = "/project"
        dispatch_ctx.channel_name = "slack"
        dispatch_ctx.task_id = "958"
        deps.dispatch_context = dispatch_ctx
        ctx = _make_ctx(deps)
        ts = DelegationToolset()

        await ts._delegate(ctx, agent_name="builder", task="do work")

        call_kwargs = inner_agent.run.call_args[1]
        assert call_kwargs["metadata"].get("task_id") == "958"


# ---------------------------------------------------------------------------
# Dispatch context formatter
# (AC: populated context → deterministic instructions text + metadata)
# ---------------------------------------------------------------------------


class TestFromAC_DispatchContextFormatter:
    """Populated DispatchContext produces deterministic instructions text and metadata dict."""

    def test_workspace_root_in_instructions(self) -> None:
        """workspace_root appears in the formatted instructions string."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/my/workspace", channel_name="slack")
        instructions, _ = format_dispatch_context(ctx)
        assert "/my/workspace" in instructions

    def test_channel_name_in_instructions(self) -> None:
        """channel_name appears in the formatted instructions string."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="my-channel")
        instructions, _ = format_dispatch_context(ctx)
        assert "my-channel" in instructions

    def test_task_id_in_instructions_when_populated(self) -> None:
        """task_id appears in the formatted instructions string when set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="958")
        instructions, _ = format_dispatch_context(ctx)
        assert "958" in instructions

    def test_task_id_in_metadata_when_populated(self) -> None:
        """task_id appears in metadata dict as 'task_id' key when set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="958")
        _, metadata = format_dispatch_context(ctx)
        assert metadata.get("task_id") == "958"

    def test_task_title_in_instructions_when_populated(self) -> None:
        """task_title appears in the formatted instructions string when set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(
            workspace_root="/project", channel_name="slack", task_title="Build widget"
        )
        instructions, _ = format_dispatch_context(ctx)
        assert "Build widget" in instructions

    def test_formatting_is_deterministic(self) -> None:
        """Same DispatchContext always produces identical (instructions, metadata) output."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(
            workspace_root="/project",
            channel_name="slack",
            task_id="42",
            task_title="My Feature",
        )
        assert format_dispatch_context(ctx) == format_dispatch_context(ctx)

    def test_metadata_return_is_dict(self) -> None:
        """format_dispatch_context returns a dict as the second element."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="1")
        _, metadata = format_dispatch_context(ctx)
        assert isinstance(metadata, dict)

    def test_instructions_return_is_string(self) -> None:
        """format_dispatch_context returns a string as the first element."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        instructions, _ = format_dispatch_context(ctx)
        assert isinstance(instructions, str)

    def test_task_status_in_instructions_when_populated(self) -> None:
        """task_status value appears in formatted instructions when set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(
            workspace_root="/project", channel_name="slack", task_status="in-progress"
        )
        instructions, _ = format_dispatch_context(ctx)
        assert "in-progress" in instructions

    def test_task_status_in_metadata_when_populated(self) -> None:
        """task_status appears in metadata dict with key 'task_status' when set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_status="review")
        _, metadata = format_dispatch_context(ctx)
        assert metadata.get("task_status") == "review"


# ---------------------------------------------------------------------------
# Absent task fields omitted
# (AC: interactive delegation does not fabricate kanban labels or metadata)
# ---------------------------------------------------------------------------


class TestFromAC_AbsentTaskFieldsOmitted:
    """Absent or unknown task fields are omitted from formatted context and metadata=."""

    def test_no_task_fields_produces_no_task_id_in_instructions(self) -> None:
        """instructions text does not reference task_id when none is set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        instructions, _ = format_dispatch_context(ctx)
        assert "task_id" not in instructions.lower()

    def test_no_task_fields_produces_no_kanban_keys_in_metadata(self) -> None:
        """metadata contains no kanban task keys when no task fields are provided."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack")
        _, metadata = format_dispatch_context(ctx)
        for key in ("task_id", "task_title", "task_status"):
            assert key not in metadata

    def test_partial_task_fields_only_present_keys_in_metadata(self) -> None:
        """Only provided task fields appear in metadata; absent fields are omitted."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="100")
        _, metadata = format_dispatch_context(ctx)
        assert "task_id" in metadata
        assert "task_title" not in metadata

    def test_absent_task_title_not_fabricated_in_instructions(self) -> None:
        """instructions text does not include task_title label when the field is not set."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(workspace_root="/project", channel_name="slack", task_id="42")
        instructions, _ = format_dispatch_context(ctx)
        assert "task_title" not in instructions.lower()

    def test_workspace_root_not_in_metadata_keys(self) -> None:
        """workspace_root is not included as a metadata key — it belongs in instructions only."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(
            workspace_root="/project",
            channel_name="slack",
            task_id="42",
            task_title="My Task",
            task_status="todo",
        )
        _, metadata = format_dispatch_context(ctx)
        assert "workspace_root" not in metadata

    def test_channel_name_not_in_metadata_keys(self) -> None:
        """channel_name is not included as a metadata key — it belongs in instructions only."""
        from owlbear.core.delegation import (  # type: ignore[attr-defined]
            DispatchContext,
            format_dispatch_context,
        )

        ctx = DispatchContext(
            workspace_root="/project",
            channel_name="slack",
            task_id="42",
            task_title="My Task",
            task_status="todo",
        )
        _, metadata = format_dispatch_context(ctx)
        assert "channel_name" not in metadata
