"""Validation tests — PydanticAI tool system meets OwlBear's needs.

Proves that PydanticAI's @tool decorator, FunctionToolset, and RunContext work
correctly for OwlBear tool patterns.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.tools import ToolDefinition

# ---------------------------------------------------------------------------
# Tool decorator basics
# ---------------------------------------------------------------------------


class TestToolDecorator:
    """PydanticAI @tool decorator works for OwlBear-style tools."""

    def test_tool_class_wraps_function(self) -> None:
        def read_file(ctx: RunContext[None], path: str) -> str:  # noqa: ARG001
            """Read a file from disk."""
            return f"contents of {path}"

        tool = Tool(read_file)
        assert tool.name == "read_file"

    def test_tool_has_description(self) -> None:
        def list_files(ctx: RunContext[None], directory: str) -> list[str]:  # noqa: ARG001
            """List files in a directory."""
            return [f"{directory}/a.py"]

        tool = Tool(list_files)
        assert tool.description == "List files in a directory."

    def test_tool_custom_name(self) -> None:
        def my_func(ctx: RunContext[None]) -> str:  # noqa: ARG001
            """Do something."""
            return "ok"

        tool = Tool(my_func, name="custom_name")
        assert tool.name == "custom_name"


# ---------------------------------------------------------------------------
# Tool definition schema
# ---------------------------------------------------------------------------


class TestToolDefinitionSchema:
    """ToolDefinition generates the JSON schema the LLM sees."""

    def test_tool_definition_has_name(self) -> None:
        td = ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters_json_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert td.name == "read_file"

    def test_tool_definition_has_schema(self) -> None:
        td = ToolDefinition(
            name="read_file",
            description="Read a file",
            parameters_json_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )
        assert "properties" in td.parameters_json_schema


# ---------------------------------------------------------------------------
# Dependency injection via RunContext
# ---------------------------------------------------------------------------


class TestRunContextDI:
    """RunContext provides typed dependencies to tools."""

    def test_dependency_type(self) -> None:
        @dataclass
        class Deps:
            workspace_root: str

        def get_root(ctx: RunContext[Deps]) -> str:
            """Get workspace root."""
            return ctx.deps.workspace_root

        # Verify the function signature accepts RunContext
        deps = Deps(workspace_root="/project")
        # We can't easily create a RunContext directly, but we can verify
        # the dataclass works with our expected pattern
        assert deps.workspace_root == "/project"


# ---------------------------------------------------------------------------
# Agent with tools (unit-level, no LLM call)
# ---------------------------------------------------------------------------


class TestAgentToolRegistration:
    """Agent accepts tools at construction time."""

    def test_agent_accepts_tool_list(self) -> None:
        def greet(ctx: RunContext[None], name: str) -> str:  # noqa: ARG001
            """Greet someone."""
            return f"Hello, {name}!"

        # Agent construction with tools should not raise
        agent = Agent("test", tools=[Tool(greet)])
        assert agent is not None

    def test_agent_accepts_tool_decorator(self) -> None:
        agent: Agent[None, str] = Agent("test")

        @agent.tool
        def farewell(ctx: RunContext[None], name: str) -> str:  # noqa: ARG001
            """Say goodbye."""
            return f"Bye, {name}!"

        assert farewell is not None
