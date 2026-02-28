"""Tests for agent_registry — AgentRegistry scan, get, list."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
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
