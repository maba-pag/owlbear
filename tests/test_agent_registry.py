"""Tests for agent_registry — AgentRegistry scan, get, list."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.agent_def import AgentDefinition  # noqa: F401
from owlbear.core.agent_registry import AgentRegistry

# Block real LLM calls in the test suite.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


def _write_agent_md(path: Path, name: str, description: str, *, body: str = "") -> None:
    """Helper — write a minimal agent .md definition file."""
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}",
        encoding="utf-8",
    )


def _dummy_resolver(_tool_name: str) -> FunctionToolset:
    """Return an empty FunctionToolset for any tool name."""
    return FunctionToolset()


_TEST_MODEL = "test"
"""Use PydanticAI's built-in test model to avoid provider initialization."""


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    """Temp dir with two valid agent definitions."""
    _write_agent_md(
        tmp_path / "builder.md",
        "builder",
        "Builds code",
        body="You are a builder.\n",
    )
    _write_agent_md(
        tmp_path / "reviewer.md",
        "reviewer",
        "Reviews code",
        body="You are a reviewer.\n",
    )
    return tmp_path


class TestAgentRegistryScan:
    """Tests for scan() and list_agents()."""

    def test_scan_finds_valid_definitions(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        assert len(registry.definitions) == 2
        assert "builder" in registry.definitions
        assert "reviewer" in registry.definitions

    def test_list_agents_returns_all(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agents = registry.list_agents()
        assert len(agents) == 2
        names = {a.name for a in agents}
        assert names == {"builder", "reviewer"}

    def test_scan_empty_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        registry = AgentRegistry(empty, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        assert registry.definitions == {}
        assert registry.list_agents() == []

    def test_scan_invalid_file_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        bad = tmp_path / "bad.md"
        bad.write_text("---\nname: [unclosed\n---\nBody.\n", encoding="utf-8")
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        with caplog.at_level(logging.WARNING):
            registry.scan()
        assert registry.definitions == {}
        assert any("bad.md" in r.message for r in caplog.records)

    def test_definitions_is_read_only_copy(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        defs = registry.definitions
        defs["injected"] = MagicMock()  # type: ignore[assignment]
        assert "injected" not in registry.definitions


class TestAgentRegistryGet:
    """Tests for get() — lazy Agent instantiation."""

    def test_get_returns_agent(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)

    def test_get_caches_instance(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        first = registry.get("builder")
        second = registry.get("builder")
        assert first is second

    def test_get_unknown_raises_keyerror(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        with pytest.raises(KeyError, match="missing") as exc_info:
            registry.get("missing")
        # Error message should list available agent names.
        msg = str(exc_info.value)
        assert "builder" in msg
        assert "reviewer" in msg

    def test_tool_resolver_called_for_each_tool(self, tmp_path: Path) -> None:
        md = tmp_path / "tooled.md"
        md.write_text(
            "---\nname: tooled\ndescription: Has tools\n"
            "tools:\n  - file_read\n  - file_write\n---\nBody.\n",
            encoding="utf-8",
        )
        resolver = MagicMock(return_value=FunctionToolset())
        registry = AgentRegistry(tmp_path, resolver, default_model=_TEST_MODEL)
        registry.scan()
        registry.get("tooled")
        resolver.assert_any_call("file_read")
        resolver.assert_any_call("file_write")
        assert resolver.call_count == 2

    def test_get_applies_role_policy_for_non_builder(self, tmp_path: Path) -> None:
        md = tmp_path / "validator.md"
        md.write_text(
            "---\nname: val\ndescription: Validates\nrole: validator\n---\nBody.\n",
            encoding="utf-8",
        )
        registry = AgentRegistry(tmp_path, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        # Should not raise — role policy is applied internally.
        agent = registry.get("val")
        assert isinstance(agent, Agent)

    def test_get_uses_default_model_when_none(self, agents_dir: Path) -> None:
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=_TEST_MODEL)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)

    def test_get_accepts_model_object_as_default(self, agents_dir: Path) -> None:
        """default_model can be a PydanticAI Model instance (e.g. Copilot model)."""
        fn_model = FunctionModel(lambda _messages, _info: "ok")
        registry = AgentRegistry(agents_dir, _dummy_resolver, default_model=fn_model)
        registry.scan()
        agent = registry.get("builder")
        assert isinstance(agent, Agent)


class TestBuildAgentMissingTools:
    """Tests that _build_agent degrades gracefully when tools are missing."""

    def test_build_agent_skips_unavailable_tool(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Agent def with tools=['a','b'], resolver raises KeyError for 'b'.

        Expected: agent created with 1 toolset (only 'a'), warning logged, no exception.
        """
        md = tmp_path / "partial.md"
        md.write_text(
            "---\nname: partial\ndescription: Has two tools\ntools:\n  - a\n  - b\n---\nBody.\n",
            encoding="utf-8",
        )

        good_toolset = FunctionToolset()

        def selective_resolver(name: str) -> FunctionToolset:
            if name == "b":
                raise KeyError(name)
            return good_toolset

        registry = AgentRegistry(tmp_path, selective_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("partial")

        assert isinstance(agent, Agent)
        # Should have logged a warning about the missing tool 'b'.
        assert any("b" in r.message for r in caplog.records)

    def test_build_agent_skips_mcp_tool_when_missing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Agent def has tools=['mcp:missing'], no MCP registry configured.

        Expected: KeyError caught, agent still created (0 toolsets), warning logged.
        """
        md = tmp_path / "mcp_agent.md"
        md.write_text(
            "---\nname: mcp_agent\ndescription: Uses MCP tool\n"
            "tools:\n  - mcp:missing\n---\nBody.\n",
            encoding="utf-8",
        )

        registry = AgentRegistry(
            tmp_path, _dummy_resolver, default_model=_TEST_MODEL, mcp_registry=None
        )
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("mcp_agent")

        assert isinstance(agent, Agent)
        # Should have logged a warning about the missing MCP tool.
        assert any("mcp:missing" in r.message for r in caplog.records)

    def test_build_agent_logs_warning_for_skipped_tool(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Warning message must include both the agent name and the tool name."""
        md = tmp_path / "test_agent.md"
        md.write_text(
            "---\nname: test_agent\ndescription: Agent for log test\n"
            "tools:\n  - good_tool\n  - bad_tool\n---\nBody.\n",
            encoding="utf-8",
        )

        def selective_resolver(name: str) -> FunctionToolset:
            if name == "bad_tool":
                raise KeyError(name)
            return FunctionToolset()

        registry = AgentRegistry(tmp_path, selective_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            registry.get("test_agent")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) >= 1
        msg = warnings[0].message
        assert "test_agent" in msg
        assert "bad_tool" in msg

    def test_build_agent_all_tools_present_unchanged(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When all tools resolve, agent gets the full toolset with no warnings."""
        md = tmp_path / "full.md"
        md.write_text(
            "---\nname: full\ndescription: All tools resolve\n"
            "tools:\n  - x\n  - y\n  - z\n---\nBody.\n",
            encoding="utf-8",
        )

        resolved: list[str] = []

        def tracking_resolver(name: str) -> FunctionToolset:
            resolved.append(name)
            return FunctionToolset()

        registry = AgentRegistry(tmp_path, tracking_resolver, default_model=_TEST_MODEL)
        registry.scan()

        with caplog.at_level(logging.WARNING):
            agent = registry.get("full")

        assert isinstance(agent, Agent)
        # All three tools were resolved.
        assert resolved == ["x", "y", "z"]
        # No warnings logged.
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == []
