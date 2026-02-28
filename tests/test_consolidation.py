"""Tests for owlbear.memory.consolidation — memory consolidation via LLM."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from owlbear.memory.consolidation import ConsolidationResult, MemoryConsolidator
from owlbear.memory.context import ContextManager
from owlbear.memory.session import SessionStore

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _populate_session(store: SessionStore, n_turns: int) -> None:
    """Append *n_turns* request/response pairs (2 messages per turn)."""
    for i in range(n_turns):
        store.append(ModelRequest(parts=[UserPromptPart(content=f"q{i}")]))
        store.append(ModelResponse(parts=[TextPart(content=f"a{i}")]))


def _mock_consolidation_run(summary: str, key_facts: list[str]) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning a ConsolidationResult."""
    output = ConsolidationResult(summary=summary, key_facts=key_facts)
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


# ---------------------------------------------------------------------------
# ConsolidationResult model
# ---------------------------------------------------------------------------


class TestConsolidationResult:
    """ConsolidationResult is a Pydantic model for structured LLM output."""

    def test_fields(self) -> None:
        r = ConsolidationResult(summary="test summary", key_facts=["a", "b"])
        assert r.summary == "test summary"
        assert r.key_facts == ["a", "b"]

    def test_empty_key_facts(self) -> None:
        r = ConsolidationResult(summary="s", key_facts=[])
        assert r.key_facts == []


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestMemoryConsolidatorCreate:
    """MemoryConsolidator accepts workspace_root, model, and threshold."""

    def test_default_threshold(self, tmp_path: Path) -> None:
        mc = MemoryConsolidator(tmp_path)
        assert mc._threshold == 20

    def test_custom_threshold(self, tmp_path: Path) -> None:
        mc = MemoryConsolidator(tmp_path, threshold=10)
        assert mc._threshold == 10

    def test_accepts_model_string(self, tmp_path: Path) -> None:
        mc = MemoryConsolidator(tmp_path, model="test")
        assert mc is not None


# ---------------------------------------------------------------------------
# Threshold gating
# ---------------------------------------------------------------------------


class TestConsolidationThreshold:
    """Consolidation only fires when unconsolidated messages exceed threshold."""

    def test_no_consolidation_below_threshold(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 5)  # 10 messages < threshold 20
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)

        result = asyncio.run(mc.consolidate(store))

        assert result is False
        assert not (tmp_path / "MEMORY.md").exists()

    def test_no_consolidation_at_threshold(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 10)  # 20 messages == threshold 20
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)

        result = asyncio.run(mc.consolidate(store))

        assert result is False

    def test_consolidation_triggered_above_threshold(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)  # 30 messages > threshold 20
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run("Summary", ["fact1"])

        result = asyncio.run(mc.consolidate(store))

        assert result is True


# ---------------------------------------------------------------------------
# MEMORY.md written with structured output
# ---------------------------------------------------------------------------


class TestMemoryMdWritten:
    """consolidate() writes a MEMORY.md with summary + key facts."""

    def test_memory_md_created(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run(
            "We discussed testing strategies", ["TDD matters", "Use pytest"]
        )

        asyncio.run(mc.consolidate(store))

        memory = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
        assert "# Memory" in memory
        assert "## Summary" in memory
        assert "We discussed testing strategies" in memory
        assert "## Key Facts" in memory
        assert "- TDD matters" in memory
        assert "- Use pytest" in memory

    def test_memory_md_overwritten_on_second_consolidation(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)

        # First consolidation
        mc._agent.run = _mock_consolidation_run("First summary", ["fact1"])
        asyncio.run(mc.consolidate(store))

        # Add more messages for second consolidation
        _populate_session(store, 15)
        mc._agent.run = _mock_consolidation_run("Second summary", ["fact2"])
        asyncio.run(mc.consolidate(store))

        memory = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
        # MEMORY.md is overwritten, not appended
        assert "Second summary" in memory
        assert "First summary" not in memory


# ---------------------------------------------------------------------------
# HISTORY.md is append-only
# ---------------------------------------------------------------------------


class TestHistoryMdAppendOnly:
    """consolidate() appends timestamped entries to HISTORY.md."""

    def test_history_md_created_on_first_consolidation(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run("First summary", ["fact1"])

        asyncio.run(mc.consolidate(store))

        history = (tmp_path / "HISTORY.md").read_text(encoding="utf-8")
        assert "First summary" in history
        assert "---" in history

    def test_history_md_append_only(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)

        # First consolidation
        mc._agent.run = _mock_consolidation_run("First summary", ["fact1"])
        asyncio.run(mc.consolidate(store))

        # Add more messages
        _populate_session(store, 15)

        # Second consolidation
        mc._agent.run = _mock_consolidation_run("Second summary", ["fact2"])
        asyncio.run(mc.consolidate(store))

        history = (tmp_path / "HISTORY.md").read_text(encoding="utf-8")
        assert "First summary" in history
        assert "Second summary" in history
        # Both entries separated by ---
        assert history.count("---") >= 2

    def test_history_md_contains_timestamp(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)
        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run("Summary", ["fact"])

        asyncio.run(mc.consolidate(store))

        history = (tmp_path / "HISTORY.md").read_text(encoding="utf-8")
        # ISO timestamp header: ## 2026-...
        assert "## 20" in history


# ---------------------------------------------------------------------------
# last_consolidated pointer updated
# ---------------------------------------------------------------------------


class TestLastConsolidatedUpdated:
    """consolidate() updates session.last_consolidated after success."""

    def test_pointer_updated_after_consolidation(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)  # 30 messages
        assert store.last_consolidated is None

        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run("Summary", ["fact"])

        asyncio.run(mc.consolidate(store))

        assert store.last_consolidated == 30

    def test_pointer_persists_across_reload(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 15)  # 30 messages

        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        mc._agent.run = _mock_consolidation_run("Summary", ["fact"])
        asyncio.run(mc.consolidate(store))

        # Reload from disk
        store2 = SessionStore(tmp_path / "s.jsonl")
        store2.load()  # triggers meta load
        assert store2.last_consolidated == 30

    def test_pointer_not_updated_when_below_threshold(self, tmp_path: Path) -> None:
        store = SessionStore(tmp_path / "s.jsonl")
        _populate_session(store, 5)  # 10 messages < 20

        mc = MemoryConsolidator(tmp_path, model="test", threshold=20)
        asyncio.run(mc.consolidate(store))

        assert store.last_consolidated is None


# ---------------------------------------------------------------------------
# ContextManager injects MEMORY.md into instructions
# ---------------------------------------------------------------------------


class TestContextManagerMemoryInjection:
    """ContextManager.instructions includes MEMORY.md content when present."""

    def test_instructions_include_memory_md(self, tmp_path: Path) -> None:
        (tmp_path / "context.md").write_text("Be helpful.", encoding="utf-8")
        (tmp_path / "MEMORY.md").write_text(
            "# Memory\n\n## Summary\nPrior context.", encoding="utf-8"
        )
        mgr = ContextManager(tmp_path)
        inst = mgr.instructions
        assert "Be helpful." in inst
        assert "Prior context." in inst

    def test_instructions_without_memory_md(self, tmp_path: Path) -> None:
        (tmp_path / "context.md").write_text("Be helpful.", encoding="utf-8")
        mgr = ContextManager(tmp_path)
        assert mgr.instructions == "Be helpful."

    def test_instructions_memory_md_only_no_context(self, tmp_path: Path) -> None:
        (tmp_path / "MEMORY.md").write_text(
            "# Memory\n\n## Summary\nStored context.", encoding="utf-8"
        )
        mgr = ContextManager(tmp_path)
        inst = mgr.instructions
        assert "Stored context." in inst

    def test_instructions_neither_file_returns_empty(self, tmp_path: Path) -> None:
        mgr = ContextManager(tmp_path)
        assert mgr.instructions == ""
