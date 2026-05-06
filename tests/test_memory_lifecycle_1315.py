"""Integration tests for #1315: Full lifecycle — save → curate → approve → recall.

AC coverage:
  AC1 (td:2): Full lifecycle: save_memory -> list_memories -> read_memory
              -> curate_memory (with scope_agents) -> approve_memory -> recall_memory
  AC2 (td:1): Persisted state verified via engine re-read at each step (pending → curated → approved)
  AC3 (td:1): recall_memory(agent="scoped-agent") returns "## {title}\\n{content}" body-only format
  AC4 (td:1): recall_memory(agent="other-agent") returns empty string for non-scoped agents
  AC5 (td:2): Git semantics — no commit after save_memory; exactly +1 after commit_batch(curation);
              exactly +1 more after commit_batch(review)
  AC6 (td:1): Uses real async tool handlers from tools.py with MemoryEngine on git-init'd tmp_path
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.git import commit_batch
from owlbear_mcp_memory.tools import (
    approve_memory,
    curate_memory,
    list_memories,
    read_memory,
    recall_memory,
    save_memory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(engine: MemoryEngine) -> MagicMock:
    """Return a mock MCP context with the engine wired into the lifespan context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _git(*args: str, cwd: Path) -> str:
    """Run a git command in cwd and return stripped stdout."""
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
    )
    return result.stdout.strip()


def _commit_count(repo_dir: Path) -> int:
    """Return total number of commits reachable from HEAD."""
    return int(_git("rev-list", "--count", "HEAD", cwd=repo_dir))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Return tmp_path initialised as a git repo with one empty initial commit."""
    subprocess.run(  # noqa: S603
        ["git", "init", str(tmp_path)],  # noqa: S607
        capture_output=True,
        check=True,
    )
    for key, val in [
        ("user.email", "test@owlbear.test"),
        ("user.name", "OwlBear Test"),
    ]:
        subprocess.run(  # noqa: S603
            ["git", "config", key, val],  # noqa: S607
            capture_output=True,
            check=True,
            cwd=tmp_path,
        )
    subprocess.run(  # noqa: S603
        ["git", "commit", "--allow-empty", "-m", "chore: initial (test)"],  # noqa: S607
        capture_output=True,
        check=True,
        cwd=tmp_path,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# AC1 (td:2): Full lifecycle exercise
# ---------------------------------------------------------------------------


class TestFromAC_FullLifecycle:
    """AC1: Full lifecycle using real tool handlers from tools.py."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_save_to_recall(self, tmp_path: Path) -> None:
        """save → list → read → curate → approve → recall in sequence."""
        engine = MemoryEngine(memory_dir=tmp_path / "memory")
        ctx = _make_ctx(engine)

        # save_memory: creates pending entry
        saved = await save_memory(
            ctx,
            title="Builder pitfalls",
            content="Always read existing code before writing new code.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="builder",
        )
        entry_id = saved["id"]
        assert saved["state"] == "pending"

        # list_memories: entry is visible in pending list
        listed = await list_memories(ctx)
        assert any(e["id"] == entry_id for e in listed)

        # read_memory: full entry accessible by id
        read = await read_memory(ctx, entry_id=entry_id)
        assert read["id"] == entry_id
        assert read["title"] == "Builder pitfalls"

        # curate_memory: promotes to curated, sets scope_agents
        curated = await curate_memory(ctx, entry_id=entry_id, scope_agents=["scoped-agent"])
        assert curated["state"] == "curated"
        assert "scoped-agent" in curated["scope_agents"]

        # approve_memory: promotes to approved
        approved = await approve_memory(ctx, entry_id=entry_id)
        assert approved["state"] == "approved"

        # recall_memory: approved entry is recalled for scoped-agent
        recalled = await recall_memory(ctx, agent="scoped-agent")
        assert "Builder pitfalls" in recalled
        assert "Always read existing code before writing new code." in recalled

    @pytest.mark.asyncio
    async def test_list_memories_reflects_state_change(self, tmp_path: Path) -> None:
        """list_memories returns pending entry before curation, approved entry after."""
        engine = MemoryEngine(memory_dir=tmp_path / "memory")
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Lifecycle list test",
            content="Some content.",
            categories=["domain-knowledge"],
            confidence=0.8,
            source_agent="test-agent",
        )
        entry_id = saved["id"]

        pending_list = await list_memories(ctx, states=["pending"])
        assert any(e["id"] == entry_id for e in pending_list)

        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])
        await approve_memory(ctx, entry_id=entry_id)

        approved_list = await list_memories(ctx, states=["approved"])
        assert any(e["id"] == entry_id for e in approved_list)


# ---------------------------------------------------------------------------
# AC2 (td:1): Persisted state verified via engine re-read
# ---------------------------------------------------------------------------


class TestFromAC_PersistedState:
    """AC2: State verified via engine re-read after each operation, not just return values."""

    @pytest.mark.asyncio
    async def test_state_transitions_via_engine_reread(self, tmp_path: Path) -> None:
        """After each tool call, engine.get_entry(id).state reflects the persisted state."""
        engine = MemoryEngine(memory_dir=tmp_path / "memory")
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="State transition test",
            content="Content for state verification.",
            categories=["domain-knowledge"],
            confidence=0.85,
            source_agent="test-agent",
        )
        entry_id = saved["id"]

        # After save: persisted state must be pending
        assert engine.get_entry(entry_id).state == "pending"

        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])

        # After curate: persisted state must be curated
        assert engine.get_entry(entry_id).state == "curated"

        await approve_memory(ctx, entry_id=entry_id)

        # After approve: persisted state must be approved
        assert engine.get_entry(entry_id).state == "approved"


# ---------------------------------------------------------------------------
# AC3 (td:1): recall returns body-only format "## {title}\n{content}"
# ---------------------------------------------------------------------------


class TestFromAC_RecallScopedFormat:
    """AC3: recall_memory returns body-only format for scoped agent."""

    @pytest.mark.asyncio
    async def test_recall_returns_body_only_markdown_format(self, tmp_path: Path) -> None:
        """Approved entry recalled for scoped-agent returns '## Title\\nContent' exactly."""
        engine = MemoryEngine(memory_dir=tmp_path / "memory")
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Recall Format Test",
            content="Body content only.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["scoped-agent"])
        await approve_memory(ctx, entry_id=entry_id)

        result = await recall_memory(ctx, agent="scoped-agent")

        assert result == "## Recall Format Test\nBody content only."


# ---------------------------------------------------------------------------
# AC4 (td:1): recall returns empty string for non-scoped agent
# ---------------------------------------------------------------------------


class TestFromAC_RecallExclusion:
    """AC4: recall_memory returns empty string for agents not in scope_agents."""

    @pytest.mark.asyncio
    async def test_recall_other_agent_returns_empty_string(self, tmp_path: Path) -> None:
        """Entry scoped to 'scoped-agent' returns empty string for 'other-agent'."""
        engine = MemoryEngine(memory_dir=tmp_path / "memory")
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Scoped Entry",
            content="Scoped content.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["scoped-agent"])
        await approve_memory(ctx, entry_id=entry_id)

        result = await recall_memory(ctx, agent="other-agent")

        assert result == ""


# ---------------------------------------------------------------------------
# AC5 (td:2): Git semantics across full lifecycle phases
# ---------------------------------------------------------------------------


class TestFromAC_GitSemantics:
    """AC5: Git commit counts are precise at each lifecycle phase boundary."""

    @pytest.mark.asyncio
    async def test_save_memory_does_not_create_commit(self, git_repo: Path) -> None:
        """save_memory writes to disk but does NOT trigger a git commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        initial_count = _commit_count(git_repo)

        await save_memory(
            ctx,
            title="Uncommitted entry",
            content="This should not be committed.",
            categories=["domain-knowledge"],
            confidence=0.8,
            source_agent="test-agent",
        )

        assert _commit_count(git_repo) == initial_count

    @pytest.mark.asyncio
    async def test_curation_batch_creates_exactly_one_new_commit(
        self, git_repo: Path
    ) -> None:
        """Explicit commit_batch(session_type='curation') after curate produces exactly +1 commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Curation commit test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])

        before = _commit_count(git_repo)
        commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert after - before == 1

    @pytest.mark.asyncio
    async def test_review_batch_creates_exactly_one_more_commit(
        self, git_repo: Path
    ) -> None:
        """After curation commit, commit_batch(session_type='review') adds exactly +1 more commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Review commit test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])
        commit_batch(memory_dir, session_type="curation")
        await approve_memory(ctx, entry_id=entry_id)

        before_review = _commit_count(git_repo)
        commit_batch(memory_dir, session_type="review")
        after_review = _commit_count(git_repo)

        assert after_review - before_review == 1

    @pytest.mark.asyncio
    async def test_curate_memory_does_not_create_commit(self, git_repo: Path) -> None:
        """curate_memory writes state to disk but does NOT create a git commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Curate no-commit test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]

        before = _commit_count(git_repo)
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])
        after = _commit_count(git_repo)

        assert after == before

    @pytest.mark.asyncio
    async def test_approve_memory_does_not_create_commit(self, git_repo: Path) -> None:
        """approve_memory writes state to disk but does NOT create a git commit."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Approve no-commit test",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="test-agent",
        )
        entry_id = saved["id"]
        await curate_memory(ctx, entry_id=entry_id, scope_agents=["builder"])

        before = _commit_count(git_repo)
        await approve_memory(ctx, entry_id=entry_id)
        after = _commit_count(git_repo)

        assert after == before

    @pytest.mark.asyncio
    async def test_no_commit_when_only_pending_entries_present(
        self, git_repo: Path
    ) -> None:
        """commit_batch with only pending files on disk produces no commit and returns ''."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        await save_memory(
            ctx,
            title="Pending only",
            content="Content.",
            categories=["domain-knowledge"],
            confidence=0.8,
            source_agent="test-agent",
        )

        before = _commit_count(git_repo)
        result = commit_batch(memory_dir, session_type="curation")
        after = _commit_count(git_repo)

        assert result == ""
        assert after == before


# ---------------------------------------------------------------------------
# AC6 (td:1): Real async tool handlers on git-init'd tmp_path
# ---------------------------------------------------------------------------


class TestFromAC_RealHandlers:
    """AC6: Integration smoke — all 6 tool handlers are real async functions from tools.py."""

    @pytest.mark.asyncio
    async def test_real_tool_handlers_on_git_repo(self, git_repo: Path) -> None:
        """Full lifecycle with real tool handlers; MemoryEngine on git-init'd tmp_path."""
        memory_dir = git_repo / "memory"
        engine = MemoryEngine(memory_dir=memory_dir)
        ctx = _make_ctx(engine)

        saved = await save_memory(
            ctx,
            title="Real handler smoke test",
            content="Verifies real tool handlers are used.",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="integration-test",
        )
        entry_id = saved["id"]

        await curate_memory(ctx, entry_id=entry_id, scope_agents=["integration-agent"])
        await approve_memory(ctx, entry_id=entry_id)

        listed = await list_memories(ctx, states=["approved"])
        read = await read_memory(ctx, entry_id=entry_id)
        recalled = await recall_memory(ctx, agent="integration-agent")

        assert any(e["id"] == entry_id for e in listed)
        assert read["state"] == "approved"
        assert "Real handler smoke test" in recalled
