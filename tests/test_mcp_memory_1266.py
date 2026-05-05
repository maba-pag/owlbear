"""Failing tests for #1266: Restructure mcp-memory to markdown+frontmatter file engine.

AC coverage:
  AC1: File engine reads/writes .owlbear/memory/*.md with YAML frontmatter
  AC2: 5 MCP tools operational: store_learning, query_memory, update_entry,
       delete_entry, approve_entry
  AC3: State transitions enforced (pending→curated→approved→deleted)
  AC4: Mutation access restricted per tool (allowed_agents config)
  AC5: MtimeScanCache skips re-parse when dir mtime unchanged
  AC6: Retrieval returns curated+approved by default, sorted approved-first
       then confidence desc
  AC7: All SQLite code removed
  (AC8: Skills updated — non-testable docs)

All tests FAIL (RED phase) — engine.py does not exist; tools.py exports old
tool names; models.py has legacy SQLite field shape.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from owlbear_mcp_memory.engine import MemoryEngine, MtimeScanCache
from owlbear_mcp_memory.models import MemoryEntry
from owlbear_mcp_memory.tools import (
    approve_entry,
    delete_entry,
    query_memory,
    store_learning,
    update_entry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(**overrides: object) -> MemoryEntry:
    """Return a valid MemoryEntry with new-design fields."""
    defaults: dict[str, object] = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Ruff import sorting pitfall",
        "categories": ["knowledge"],
        "confidence": 0.85,
        "state": "pending",
        "content": "Always run ruff --select I for import sorting.",
        "scope_agents": None,
        "created_at": "2026-05-01T10:00:00Z",
        "updated_at": "2026-05-01T10:00:00Z",
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def _make_ctx(engine: MemoryEngine, caller: str = "any-agent") -> MagicMock:
    """Return a MagicMock MCP context wrapping the given engine and caller."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    ctx.request_context.lifespan_context.caller = caller
    return ctx


def _write_entry_file(memory_dir: Path, entry: MemoryEntry) -> Path:
    """Manually write an entry .md file for pre-seeding tests."""
    frontmatter = {
        "id": entry.id,
        "title": entry.title,
        "categories": entry.categories,
        "confidence": entry.confidence,
        "state": entry.state,
        "scope_agents": entry.scope_agents,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    slug = entry.title.lower().replace(" ", "-")[:40]
    filename = f"{slug}-abc123.md"
    path = memory_dir / filename
    path.write_text(
        f"---\n{yaml.safe_dump(frontmatter, default_flow_style=False)}---\n\n{entry.content}\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# AC1: MemoryEntry model — new field shape
# ---------------------------------------------------------------------------


class TestFromAC_MemoryEntryModel:
    """AC1: MemoryEntry Pydantic model validates new-design YAML frontmatter fields."""

    def test_valid_entry_created_with_new_fields(self) -> None:
        """New MemoryEntry has title, categories (list), state, confidence fields."""
        entry = _make_entry()
        assert entry.title == "Ruff import sorting pitfall"
        assert entry.categories == ["knowledge"]
        assert entry.state == "pending"
        assert entry.confidence == 0.85

    def test_title_is_required(self) -> None:
        """Missing title raises ValidationError."""
        with pytest.raises(ValidationError):
            MemoryEntry(
                id="abc123",
                categories=["knowledge"],
                confidence=0.8,
                state="pending",
                content="body",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )

    def test_categories_accepts_all_nine_enum_values(self) -> None:
        """All 9 category values are valid."""
        valid = [
            "knowledge",
            "behaviour",
            "pitfall",
            "process",
            "tool",
            "goal",
            "personality",
            "preference",
            "context",
        ]
        for cat in valid:
            entry = _make_entry(categories=[cat])
            assert cat in entry.categories

    def test_categories_rejects_unknown_value(self) -> None:
        """Invalid category raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_entry(categories=["unknown"])

    def test_confidence_minimum_boundary_accepted(self) -> None:
        """Confidence of exactly 0.7 is valid (lower bound inclusive)."""
        entry = _make_entry(confidence=0.7)
        assert entry.confidence == 0.7

    def test_confidence_below_minimum_rejected(self) -> None:
        """Confidence below 0.7 raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_entry(confidence=0.69)

    def test_confidence_maximum_accepted(self) -> None:
        """Confidence of exactly 1.0 is valid (upper bound inclusive)."""
        entry = _make_entry(confidence=1.0)
        assert entry.confidence == 1.0

    def test_confidence_above_maximum_rejected(self) -> None:
        """Confidence above 1.0 raises ValidationError."""
        with pytest.raises(ValidationError):
            _make_entry(confidence=1.01)

    def test_state_defaults_to_pending(self) -> None:
        """Omitting state produces a pending entry by default."""
        entry = MemoryEntry(
            id="00000000-0000-4000-8000-000000000001",
            title="Some learning",
            categories=["context"],
            confidence=0.8,
            content="body",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert entry.state == "pending"

    def test_all_four_state_values_valid(self) -> None:
        """All 4 state values are accepted by the model."""
        for state in ("pending", "curated", "approved", "deleted"):
            entry = _make_entry(state=state)
            assert entry.state == state

    def test_scope_agents_is_optional(self) -> None:
        """Omitting scope_agents is valid; model defaults to None or empty."""
        entry = MemoryEntry(
            id="00000000-0000-4000-8000-000000000002",
            title="Test",
            categories=["tool"],
            confidence=0.75,
            content="body",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        assert entry.scope_agents is None or entry.scope_agents == []


# ---------------------------------------------------------------------------
# AC1: File engine — reads and writes .md files with YAML frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_FileEngine:
    """AC1: MemoryEngine reads/writes .owlbear/memory/*.md with YAML frontmatter."""

    def test_write_creates_md_file(self, tmp_path: Path) -> None:
        """write() creates a .md file in the memory directory."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry()
        engine.write(entry)

        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) == 1

    def test_written_file_has_yaml_frontmatter_block(self, tmp_path: Path) -> None:
        """Written .md file starts with --- YAML frontmatter block."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry()
        engine.write(entry)

        md_file = next(tmp_path.glob("*.md"))
        raw = md_file.read_text(encoding="utf-8")
        assert raw.startswith("---"), "File must begin with YAML frontmatter delimiter"
        # Second --- closes the frontmatter block
        parts = raw.split("---", 2)
        assert len(parts) >= 3, "File must contain opening and closing --- delimiters"

    def test_written_file_frontmatter_contains_required_fields(
        self, tmp_path: Path
    ) -> None:
        """YAML frontmatter contains id, title, categories, confidence, state."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry()
        engine.write(entry)

        md_file = next(tmp_path.glob("*.md"))
        raw = md_file.read_text(encoding="utf-8")
        _, fm_block, _ = raw.split("---", 2)
        fm = yaml.safe_load(fm_block)
        assert fm["id"] == entry.id
        assert fm["title"] == entry.title
        assert fm["categories"] == entry.categories
        assert fm["confidence"] == entry.confidence
        assert fm["state"] == entry.state

    def test_written_file_contains_markdown_body(self, tmp_path: Path) -> None:
        """File body (after frontmatter) contains the entry content."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(content="Always run ruff --select I for import sorting.")
        engine.write(entry)

        md_file = next(tmp_path.glob("*.md"))
        raw = md_file.read_text(encoding="utf-8")
        body = raw.split("---", 2)[2]
        assert "Always run ruff --select I for import sorting." in body

    def test_load_returns_entries_from_disk(self, tmp_path: Path) -> None:
        """load() returns one MemoryEntry per .md file in the directory."""
        entry = _make_entry()
        _write_entry_file(tmp_path, entry)

        engine = MemoryEngine(memory_dir=tmp_path)
        entries = engine.load()

        assert len(entries) == 1
        assert entries[0].id == entry.id

    def test_roundtrip_preserves_all_frontmatter_fields(self, tmp_path: Path) -> None:
        """write() then load() preserves id, title, categories, confidence, state."""
        engine = MemoryEngine(memory_dir=tmp_path)
        original = _make_entry(
            title="Roundtrip test",
            categories=["pitfall", "process"],
            confidence=0.92,
            state="curated",
        )
        engine.write(original)
        loaded = engine.load()

        assert len(loaded) == 1
        restored = loaded[0]
        assert restored.id == original.id
        assert restored.title == original.title
        assert set(restored.categories) == set(original.categories)
        assert restored.confidence == original.confidence
        assert restored.state == original.state

    def test_load_ignores_non_md_files(self, tmp_path: Path) -> None:
        """Non-.md files in the directory are silently ignored by load()."""
        (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")
        (tmp_path / "config.yml").write_text("key: value", encoding="utf-8")

        engine = MemoryEngine(memory_dir=tmp_path)
        entries = engine.load()

        assert entries == []

    def test_load_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """load() on an empty directory returns an empty list."""
        engine = MemoryEngine(memory_dir=tmp_path)
        assert engine.load() == []

    def test_filename_slug_derived_from_title(self, tmp_path: Path) -> None:
        """Written filename contains a slug derived from the entry title."""
        engine = MemoryEngine(memory_dir=tmp_path)
        entry = _make_entry(title="Ruff Import Pitfall")
        engine.write(entry)

        filenames = [f.name for f in tmp_path.glob("*.md")]
        assert len(filenames) == 1
        # Slug should be derived from title (kebab-case)
        assert "ruff" in filenames[0] or "import" in filenames[0]


# ---------------------------------------------------------------------------
# AC5: MtimeScanCache — skips re-parse when dir mtime unchanged
# ---------------------------------------------------------------------------


class TestFromAC_MtimeScanCache:
    """AC5: MtimeScanCache detects directory changes and skips reload when unchanged."""

    def test_has_changed_returns_true_on_first_call(self, tmp_path: Path) -> None:
        """First call to has_changed() always returns True (never-scanned state)."""
        cache = MtimeScanCache(tmp_path)
        assert cache.has_changed() is True

    def test_has_changed_returns_false_when_dir_unchanged(self, tmp_path: Path) -> None:
        """Second call with no filesystem changes returns False."""
        cache = MtimeScanCache(tmp_path)
        cache.has_changed()  # prime the cache
        assert cache.has_changed() is False

    def test_has_changed_returns_true_after_new_file_written(
        self, tmp_path: Path
    ) -> None:
        """has_changed() returns True after a new .md file is written."""
        cache = MtimeScanCache(tmp_path)
        cache.has_changed()  # prime

        # Write a new file — updates directory mtime
        (tmp_path / "new-entry-abc123.md").write_text(
            "---\n---\nbody", encoding="utf-8"
        )

        assert cache.has_changed() is True

    def test_engine_reloads_entries_after_cache_invalidation(
        self, tmp_path: Path
    ) -> None:
        """MemoryEngine reloads from disk when MtimeScanCache reports a change."""
        engine = MemoryEngine(memory_dir=tmp_path)
        initial = engine.get_entries()  # empty
        assert initial == []

        # Externally add a file between loads
        entry = _make_entry(title="Post-init entry")
        _write_entry_file(tmp_path, entry)

        reloaded = engine.get_entries()  # should detect change and reload
        assert len(reloaded) == 1
        assert reloaded[0].title == "Post-init entry"


# ---------------------------------------------------------------------------
# AC2: 5 MCP tools operational
# ---------------------------------------------------------------------------


class TestFromAC_MCPTools:
    """AC2: store_learning, query_memory, update_entry, delete_entry, approve_entry callable."""

    @pytest.mark.asyncio
    async def test_store_learning_creates_entry_with_pending_state(
        self, tmp_path: Path
    ) -> None:
        """store_learning creates a new entry with state=pending."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        result = await store_learning(
            ctx,
            title="New learning",
            content="Some important observation.",
            categories=["pitfall"],
            confidence=0.8,
        )

        assert result["state"] == "pending"
        assert result["title"] == "New learning"

    @pytest.mark.asyncio
    async def test_query_memory_returns_list(self, tmp_path: Path) -> None:
        """query_memory returns a list (possibly empty)."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine)

        result = await query_memory(ctx)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_entry_changes_content(self, tmp_path: Path) -> None:
        """update_entry can modify the content of an existing entry."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(
            ctx,
            entry_id=entry.id,
            content="Updated content.",
        )

        assert "Updated content." in result["content"]

    @pytest.mark.asyncio
    async def test_delete_entry_sets_state_to_deleted(self, tmp_path: Path) -> None:
        """delete_entry marks an entry with state=deleted."""
        entry = _make_entry(state="curated")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_entry(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"

    @pytest.mark.asyncio
    async def test_approve_entry_promotes_curated_to_approved(
        self, tmp_path: Path
    ) -> None:
        """approve_entry transitions a curated entry to approved."""
        entry = _make_entry(state="curated")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        result = await approve_entry(ctx, entry_id=entry.id)

        assert result["state"] == "approved"


# ---------------------------------------------------------------------------
# AC3: State transitions enforced
# ---------------------------------------------------------------------------


class TestFromAC_StateTransitions:
    """AC3: State machine allows valid transitions and rejects invalid ones."""

    @pytest.mark.asyncio
    async def test_pending_to_curated_allowed(self, tmp_path: Path) -> None:
        """Curator can promote pending → curated via update_entry."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await update_entry(ctx, entry_id=entry.id, state="curated")

        assert result["state"] == "curated"

    @pytest.mark.asyncio
    async def test_curated_to_approved_allowed(self, tmp_path: Path) -> None:
        """User can approve a curated entry via approve_entry."""
        entry = _make_entry(state="curated")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        result = await approve_entry(ctx, entry_id=entry.id)

        assert result["state"] == "approved"

    @pytest.mark.asyncio
    async def test_pending_to_approved_rejected(self, tmp_path: Path) -> None:
        """Skipping curated state (pending → approved) raises ToolError."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="user")

        with pytest.raises(ToolError):
            await approve_entry(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_pending_to_deleted_allowed(self, tmp_path: Path) -> None:
        """Curator can delete a pending entry directly."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_entry(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"

    @pytest.mark.asyncio
    async def test_curated_to_deleted_allowed(self, tmp_path: Path) -> None:
        """Curator can delete a curated entry."""
        entry = _make_entry(state="curated")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_entry(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"

    @pytest.mark.asyncio
    async def test_approved_to_deleted_allowed(self, tmp_path: Path) -> None:
        """Curator can mark an approved entry deleted."""
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        result = await delete_entry(ctx, entry_id=entry.id)

        assert result["state"] == "deleted"

    @pytest.mark.asyncio
    async def test_deleted_cannot_be_promoted_to_curated(self, tmp_path: Path) -> None:
        """update_entry raises ToolError when attempting to promote a deleted entry."""
        entry = _make_entry(state="deleted")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, state="curated")

    @pytest.mark.asyncio
    async def test_approved_update_with_title_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects ALL mutations on approved entries — field edit raises ToolError.

        Covers AC: 'update_entry rejects ALL calls when current.state == approved'.
        The bug is that _ensure_update_transition short-circuits when current == target,
        so field mutations (title/content/etc.) on approved entries silently succeed.
        """
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, title="Modified title")

    @pytest.mark.asyncio
    async def test_approved_update_with_no_state_change_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects calls on approved entries even when no state param is given.

        Without a state param, target_state = state or current.state == 'approved', which
        causes _ensure_update_transition to return early (current == target). The guard
        must fire BEFORE _ensure_update_transition, not inside it.
        """
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, confidence=0.99)

    @pytest.mark.asyncio
    async def test_approved_update_with_content_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects content mutations on approved entries (ALL calls contract)."""
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, content="Modified content")

    @pytest.mark.asyncio
    async def test_approved_update_with_categories_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects categories mutations on approved entries (ALL calls contract)."""
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, categories=["pitfall"])

    @pytest.mark.asyncio
    async def test_approved_update_with_state_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects state change mutations on approved entries (ALL calls contract)."""
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, state="curated")

    @pytest.mark.asyncio
    async def test_approved_update_with_scope_agents_raises_tool_error(
        self, tmp_path: Path
    ) -> None:
        """update_entry rejects scope_agents mutations on approved entries (ALL calls contract)."""
        entry = _make_entry(state="approved")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")

        with pytest.raises(ToolError, match="approved"):
            await update_entry(ctx, entry_id=entry.id, scope_agents=["builder"])


# ---------------------------------------------------------------------------
# AC4: Mutation access restricted per tool
# ---------------------------------------------------------------------------


class TestFromAC_AccessControl:
    """AC4: Tools enforce allowed_agents config — curator/user-only mutations rejected."""

    @pytest.mark.asyncio
    async def test_store_learning_allows_any_agent(self, tmp_path: Path) -> None:
        """Any caller can invoke store_learning (no restriction)."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="builder")

        # Should not raise
        result = await store_learning(
            ctx,
            title="Some learning",
            content="body",
            categories=["knowledge"],
            confidence=0.75,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_query_memory_allows_any_agent(self, tmp_path: Path) -> None:
        """Any caller can invoke query_memory (no restriction)."""
        engine = MemoryEngine(memory_dir=tmp_path)
        ctx = _make_ctx(engine, caller="researcher")

        result = await query_memory(ctx)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_update_entry_rejects_non_curator(self, tmp_path: Path) -> None:
        """Non-curator caller to update_entry raises ToolError."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="builder")  # not curator

        with pytest.raises(ToolError):
            await update_entry(ctx, entry_id=entry.id, content="hacked")

    @pytest.mark.asyncio
    async def test_delete_entry_rejects_non_curator(self, tmp_path: Path) -> None:
        """Non-curator caller to delete_entry raises ToolError."""
        entry = _make_entry(state="pending")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="researcher")  # not curator

        with pytest.raises(ToolError):
            await delete_entry(ctx, entry_id=entry.id)

    @pytest.mark.asyncio
    async def test_approve_entry_rejects_non_user(self, tmp_path: Path) -> None:
        """Non-user caller to approve_entry raises ToolError."""
        entry = _make_entry(state="curated")
        engine = MemoryEngine(memory_dir=tmp_path)
        engine.write(entry)
        ctx = _make_ctx(engine, caller="curator")  # curator, not user

        with pytest.raises(ToolError):
            await approve_entry(ctx, entry_id=entry.id)


# ---------------------------------------------------------------------------
# AC6: Retrieval returns curated+approved by default, sorted correctly
# ---------------------------------------------------------------------------


class TestFromAC_Retrieval:
    """AC6: query_memory default behavior: curated+approved only, approved first, confidence desc."""

    @pytest.mark.asyncio
    async def test_query_excludes_pending_entries_by_default(
        self, tmp_path: Path
    ) -> None:
        """Default query_memory call does not return pending entries."""
        pending = _make_entry(
            id="10000000-0000-4000-8000-000000000001",
            title="Pending entry",
            state="pending",
            confidence=0.9,
        )
        curated = _make_entry(
            id="20000000-0000-4000-8000-000000000002",
            title="Curated entry",
            state="curated",
            confidence=0.9,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _write_entry_file(tmp_path, pending)
        _write_entry_file(tmp_path, curated)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx)

        ids = [r["id"] for r in results]
        assert "10000000-0000-4000-8000-000000000001" not in ids
        assert "20000000-0000-4000-8000-000000000002" in ids

    @pytest.mark.asyncio
    async def test_query_excludes_deleted_entries_by_default(
        self, tmp_path: Path
    ) -> None:
        """Default query_memory call does not return deleted entries."""
        deleted = _make_entry(
            id="30000000-0000-4000-8000-000000000003",
            title="Deleted entry",
            state="deleted",
            confidence=0.9,
        )
        approved = _make_entry(
            id="40000000-0000-4000-8000-000000000004",
            title="Approved entry",
            state="approved",
            confidence=0.9,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _write_entry_file(tmp_path, deleted)
        _write_entry_file(tmp_path, approved)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx)

        ids = [r["id"] for r in results]
        assert "30000000-0000-4000-8000-000000000003" not in ids
        assert "40000000-0000-4000-8000-000000000004" in ids

    @pytest.mark.asyncio
    async def test_query_approved_sorted_before_curated(self, tmp_path: Path) -> None:
        """Approved entries appear before curated entries regardless of confidence."""
        curated = _make_entry(
            id="20000000-0000-4000-8000-000000000002",
            title="Curated entry",
            state="curated",
            confidence=1.0,  # highest confidence, but curated
        )
        approved = _make_entry(
            id="40000000-0000-4000-8000-000000000004",
            title="Approved entry",
            state="approved",
            confidence=0.7,  # lowest confidence, but approved
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _write_entry_file(tmp_path, curated)
        _write_entry_file(tmp_path, approved)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx)

        assert len(results) == 2
        assert results[0]["id"] == "40000000-0000-4000-8000-000000000004"
        assert results[1]["id"] == "20000000-0000-4000-8000-000000000002"

    @pytest.mark.asyncio
    async def test_query_sorted_by_confidence_desc_within_same_state(
        self, tmp_path: Path
    ) -> None:
        """Within the same state tier, entries are sorted by confidence descending."""
        low = _make_entry(
            id="50000000-0000-4000-8000-000000000005",
            title="Low confidence",
            state="curated",
            confidence=0.75,
        )
        high = _make_entry(
            id="60000000-0000-4000-8000-000000000006",
            title="High confidence",
            state="curated",
            confidence=0.95,
        )
        engine = MemoryEngine(memory_dir=tmp_path)
        _write_entry_file(tmp_path, low)
        _write_entry_file(tmp_path, high)
        ctx = _make_ctx(engine)

        results = await query_memory(ctx)

        assert results[0]["id"] == "60000000-0000-4000-8000-000000000006"
        assert results[1]["id"] == "50000000-0000-4000-8000-000000000005"


# ---------------------------------------------------------------------------
# AC7: All SQLite code removed
# ---------------------------------------------------------------------------


class TestFromAC_SQLiteRemoval:
    """AC7: No sqlite3 usage in server, tools, or engine modules after restructure."""

    def test_server_module_does_not_import_sqlite3(self) -> None:
        """sqlite3 must not be in server.py module namespace after restructure."""
        import owlbear_mcp_memory.server as server_mod

        assert "sqlite3" not in vars(server_mod), (
            "server.py still imports sqlite3 — SQLite code not fully removed"
        )

    def test_tools_module_does_not_import_sqlite3(self) -> None:
        """sqlite3 must not be in tools.py module namespace after restructure."""
        import owlbear_mcp_memory.tools as tools_mod

        assert "sqlite3" not in vars(tools_mod), (
            "tools.py still imports sqlite3 — SQLite code not fully removed"
        )

    def test_engine_module_does_not_import_sqlite3(self) -> None:
        """sqlite3 must not be imported in engine.py."""
        import owlbear_mcp_memory.engine as engine_mod

        assert "sqlite3" not in vars(engine_mod), (
            "engine.py imports sqlite3 — new file engine must not use SQLite"
        )


# ---------------------------------------------------------------------------
# Consumer drift (NEW AC): retire get_knowledge / list_entries references
# ---------------------------------------------------------------------------


class TestFromAC_ConsumerDrift:
    """New AC: consumer files must not reference retired memory API names.

    Covers: share/prompts/agent-broad-audit.prompt.md, share/agents/memory-curator.agent.md,
            serve/mcp-memory/README.md must use current tool names only.
    """

    def test_agent_broad_audit_prompt_does_not_call_get_knowledge(self) -> None:
        """agent-broad-audit.prompt.md must not call retired get_knowledge tool."""
        prompt_path = (
            Path(__file__).parent.parent
            / "share"
            / "prompts"
            / "agent-broad-audit.prompt.md"
        )
        assert prompt_path.exists(), f"prompt file not found: {prompt_path}"
        content = prompt_path.read_text()
        assert "get_knowledge" not in content, (
            "agent-broad-audit.prompt.md still calls retired get_knowledge — "
            "update to query_memory"
        )

    def test_memory_curator_agent_does_not_reference_list_entries(self) -> None:
        """memory-curator.agent.md must not reference retired list_entries tool."""
        agent_path = (
            Path(__file__).parent.parent
            / "share"
            / "agents"
            / "memory-curator.agent.md"
        )
        assert agent_path.exists(), f"agent file not found: {agent_path}"
        content = agent_path.read_text()
        assert "list_entries" not in content, (
            "memory-curator.agent.md still references retired list_entries — "
            "update to query_memory"
        )

    def test_mcp_memory_readme_does_not_list_old_tools(self) -> None:
        """serve/mcp-memory/README.md must not list retired tool names.

        The old tool table includes get_knowledge, record_learning, list_entries.
        All three must be gone and replaced with the current 5-tool API.
        """
        readme_path = (
            Path(__file__).parent.parent / "serve" / "mcp-memory" / "README.md"
        )
        assert readme_path.exists(), f"README not found: {readme_path}"
        content = readme_path.read_text()
        for retired_tool in ("get_knowledge", "record_learning", "list_entries"):
            assert retired_tool not in content, (
                f"serve/mcp-memory/README.md still documents retired tool '{retired_tool}' — "
                "replace table with current 5-tool API"
            )

    def test_agent_broad_audit_prompt_references_query_memory(self) -> None:
        """agent-broad-audit.prompt.md must reference query_memory when memory MCP is audited."""
        prompt_path = (
            Path(__file__).parent.parent
            / "share"
            / "prompts"
            / "agent-broad-audit.prompt.md"
        )
        assert prompt_path.exists(), f"prompt file not found: {prompt_path}"
        content = prompt_path.read_text()
        assert "query_memory" in content, (
            "agent-broad-audit.prompt.md does not reference query_memory — "
            "consumer was not updated to the current API"
        )

    def test_memory_curator_agent_references_query_memory(self) -> None:
        """memory-curator.agent.md must reference query_memory (positive proof)."""
        agent_path = (
            Path(__file__).parent.parent
            / "share"
            / "agents"
            / "memory-curator.agent.md"
        )
        assert agent_path.exists(), f"agent file not found: {agent_path}"
        content = agent_path.read_text()
        assert "query_memory" in content, (
            "memory-curator.agent.md does not reference query_memory — "
            "consumer was not updated to the current API"
        )

    def test_mcp_memory_readme_lists_all_current_tools(self) -> None:
        """serve/mcp-memory/README.md must list all 5 current tool names (positive proof)."""
        readme_path = (
            Path(__file__).parent.parent / "serve" / "mcp-memory" / "README.md"
        )
        assert readme_path.exists(), f"README not found: {readme_path}"
        content = readme_path.read_text()
        for current_tool in (
            "store_learning",
            "query_memory",
            "update_entry",
            "delete_entry",
            "approve_entry",
        ):
            assert current_tool in content, (
                f"serve/mcp-memory/README.md does not list current tool '{current_tool}' — "
                "update README to document the 5-tool API"
            )
