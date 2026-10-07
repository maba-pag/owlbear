"""Live MCP contract tests for memory server registration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import mcp
import pytest
from mcp.types import CallToolResult
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry, MemoryState

from owlbear_memory_mcp.server import mcp as memory_mcp

_REVIEWED_MEMORY = """---
id: 550e8400-e29b-41d4-a716-446655440000
title: Reviewed memory
categories: [process]
confidence: 0.8
state: approved
source_agent: test-agent
created_at: '2026-08-29T00:00:00+00:00'
updated_at: '2026-08-29T00:00:00+00:00'
approved_at: '2026-08-29T00:00:00+00:00'
---

Reviewed memory.
"""


def _text(result: CallToolResult) -> str:
    """Extract the text payload from one MCP tool result."""
    return "".join(item.text for item in result.content if hasattr(item, "text"))


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _create_entry(memory_dir: Path, *, title: str, state: MemoryState) -> MemoryEntry:
    engine = MemoryEngine(memory_dir)
    entry = engine.save(
        title=title,
        content=f"{title} content.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=[],
    )
    if state == MemoryState.PENDING:
        return entry
    if state not in {MemoryState.CURATED, MemoryState.APPROVED}:
        msg = f"unsupported fixture state: {state}"
        raise ValueError(msg)

    entry = engine.edit(
        entry.id,
        {"scope_agents": ["test-agent"]},
        expected_revision=entry.revision,
    )
    if state == MemoryState.CURATED:
        return entry
    return engine.approve(entry.id, expected_revision=entry.revision)


@pytest.mark.asyncio
async def test_live_server_revisions_are_stable_and_content_sensitive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Read and list expose one stable token until a revision-covered field changes."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = _create_entry(memory_dir, title="Stable revision", state=MemoryState.CURATED)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        read_result = await client.call_tool("read_memory", {"entry_id": entry.id})
        list_result = await client.call_tool("list_memories", {})
        assert not read_result.is_error
        assert not list_result.is_error
        read_payload = json.loads(_text(read_result))
        listed_payload = [json.loads(item.text) for item in list_result.content if hasattr(item, "text")]
        revision = read_payload["revision"]
        assert len(revision) == 16
        assert all(character in "0123456789abcdef" for character in revision)
        assert len(listed_payload) == 1
        assert listed_payload[0]["revision"] == revision

        approved = await client.call_tool(
            "approve_memory",
            {"entry_id": entry.id, "revision": revision},
        )
        assert not approved.is_error
        assert json.loads(_text(approved))["revision"] == revision

    async with mcp.Client(memory_mcp) as client:
        reloaded_read = await client.call_tool("read_memory", {"entry_id": entry.id})
        reloaded_list = await client.call_tool("list_memories", {})

    assert not reloaded_read.is_error
    assert not reloaded_list.is_error
    assert json.loads(_text(reloaded_read))["revision"] == revision
    reloaded_payload = [json.loads(item.text) for item in reloaded_list.content if hasattr(item, "text")]
    assert reloaded_payload[0]["revision"] == revision

    changed = MemoryEngine(memory_dir).edit(
        entry.id,
        {"content": "Changed by a second engine."},
        expected_revision=revision,
    )
    assert changed.revision != revision

    async with mcp.Client(memory_mcp) as client:
        changed_read = await client.call_tool("read_memory", {"entry_id": entry.id})

    assert not changed_read.is_error
    assert json.loads(_text(changed_read))["revision"] == changed.revision


@pytest.mark.asyncio
async def test_live_server_rejects_stale_revisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stale curator mutations name both revisions and preserve the changed entry."""
    memory_dir = tmp_path / ".owlbear/memory"
    entries = {
        "approve_memory": _create_entry(memory_dir, title="Stale approve", state=MemoryState.CURATED),
        "curate_memory": _create_entry(memory_dir, title="Stale curate", state=MemoryState.CURATED),
        "delete_memory": _create_entry(memory_dir, title="Stale delete", state=MemoryState.CURATED),
    }
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        for operation, entry in entries.items():
            expected_revision = entry.revision
            current = MemoryEngine(memory_dir).edit(
                entry.id,
                {"content": f"Changed externally for {operation}."},
                expected_revision=expected_revision,
            )
            path = memory_dir / f"{entry.id}.md"
            before_call = path.read_bytes()
            result = await client.call_tool(
                operation,
                {"entry_id": entry.id, "revision": expected_revision},
            )
            message = _text(result)

            assert result.is_error
            assert "changed since it was read" in message.lower()
            assert f"expected revision {expected_revision!r}" in message
            assert f"current revision {current.revision!r}" in message
            assert "re-read before retrying" in message.lower()
            assert path.read_bytes() == before_call


@pytest.mark.asyncio
async def test_live_server_mutations_accept_fresh_revisions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fresh revisions permit the supported curator lifecycle mutations."""
    memory_dir = tmp_path / ".owlbear/memory"
    to_approve = _create_entry(memory_dir, title="Approve", state=MemoryState.CURATED)
    to_curate = _create_entry(memory_dir, title="Curate pending", state=MemoryState.PENDING)
    to_edit = _create_entry(memory_dir, title="Edit approved", state=MemoryState.APPROVED)
    to_hard_delete = _create_entry(memory_dir, title="Delete pending", state=MemoryState.PENDING)
    to_soft_delete = _create_entry(memory_dir, title="Delete curated", state=MemoryState.CURATED)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:

        async def read_revision(entry_id: str) -> str:
            result = await client.call_tool("read_memory", {"entry_id": entry_id})
            assert not result.is_error
            return json.loads(_text(result))["revision"]

        approve_revision = await read_revision(to_approve.id)
        approved = await client.call_tool(
            "approve_memory",
            {"entry_id": to_approve.id, "revision": approve_revision},
        )
        assert not approved.is_error
        approved_payload = json.loads(_text(approved))
        assert approved_payload["state"] == "approved"
        assert approved_payload["revision"] == approve_revision

        curate_revision = await read_revision(to_curate.id)
        curated = await client.call_tool(
            "curate_memory",
            {"entry_id": to_curate.id, "revision": curate_revision, "scope_agents": ["builder"]},
        )
        assert not curated.is_error
        curated_payload = json.loads(_text(curated))
        assert curated_payload["state"] == "curated"

        edit_revision = await read_revision(to_edit.id)
        edited = await client.call_tool(
            "curate_memory",
            {"entry_id": to_edit.id, "revision": edit_revision, "content": "Updated through MCP."},
        )
        assert not edited.is_error
        edited_payload = json.loads(_text(edited))
        assert edited_payload["state"] == "curated"
        assert edited_payload["revision"] != edit_revision

        hard_delete_revision = await read_revision(to_hard_delete.id)
        hard_deleted = await client.call_tool(
            "delete_memory",
            {"entry_id": to_hard_delete.id, "revision": hard_delete_revision},
        )
        assert not hard_deleted.is_error
        assert not (memory_dir / f"{to_hard_delete.id}.md").exists()

        soft_delete_revision = await read_revision(to_soft_delete.id)
        soft_deleted = await client.call_tool(
            "delete_memory",
            {"entry_id": to_soft_delete.id, "revision": soft_delete_revision},
        )
        assert not soft_deleted.is_error
        assert json.loads(_text(soft_deleted))["state"] == "deleted"
        assert (memory_dir / f"{to_soft_delete.id}.md").exists()


@pytest.mark.asyncio
async def test_live_server_rejects_missing_and_malformed_revisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Revision schema failures do not mutate entries through the live server."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = _create_entry(memory_dir, title="Invalid revisions", state=MemoryState.CURATED)
    path = memory_dir / f"{entry.id}.md"
    before_calls = path.read_bytes()
    monkeypatch.chdir(tmp_path)
    invalid_revisions = ("A" + "a" * 15, "a" * 15, "g" * 16)

    async with mcp.Client(memory_mcp) as client:
        for operation in ("approve_memory", "curate_memory", "delete_memory"):
            missing = await client.call_tool(operation, {"entry_id": entry.id})
            assert missing.is_error
            assert path.read_bytes() == before_calls

            for revision in invalid_revisions:
                malformed = await client.call_tool(
                    operation,
                    {"entry_id": entry.id, "revision": revision},
                )
                assert malformed.is_error
                assert path.read_bytes() == before_calls


@pytest.mark.asyncio
async def test_live_server_accepts_optional_recall_and_open_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Registered tools accept guided recall and any nonblank string provenance."""
    (tmp_path / ".owlbear").mkdir()
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        recall = await client.call_tool("recall_memory", {})
        saved = await client.call_tool(
            "save_memory",
            {
                "title": "Wildcard provenance",
                "content": "Curator assigns the audience.",
                "categories": ["process"],
                "confidence": 0.8,
                "source_agent": "*",
            },
        )
        invalid = await client.call_tool("recall_memory", {"agent": 1})

    assert not recall.is_error
    assert "Known agents: none discovered." in _text(recall)
    assert not saved.is_error
    assert invalid.is_error


@pytest.mark.asyncio
async def test_live_server_commits_reviewed_memory_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The public batch tool commits reviewed entries and reports a no-op afterward."""
    (tmp_path / ".owlbear/memory").mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".owlbear/memory/reviewed.md").write_text(_REVIEWED_MEMORY, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        committed = await client.call_tool("commit_memory_batch", {"session_type": "review"})
        empty = await client.call_tool("commit_memory_batch", {"session_type": "review"})

    committed_payload = json.loads(_text(committed))
    empty_payload = json.loads(_text(empty))
    assert not committed.is_error
    assert committed_payload["committed"] is True
    assert committed_payload["commit_sha"] == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "log", "-1", "--format=%s") == ("chore: memory review batch (memory-mcp, memory-reviewer)")
    assert not empty.is_error
    assert empty_payload == {
        "session_type": "review",
        "commit_sha": None,
        "committed": False,
        "hint": "No memory changes to commit.",
    }


@pytest.mark.asyncio
async def test_live_server_reports_git_hook_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The public batch tool reports output from a failing Git hook."""
    (tmp_path / ".owlbear/memory").mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".owlbear/memory/reviewed.md").write_text(_REVIEWED_MEMORY, encoding="utf-8")
    hook = tmp_path / ".git/hooks/pre-commit"
    hook.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'HOOKFAIL: review hook rejected this commit' >&2\nexit 1\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        result = await client.call_tool("commit_memory_batch", {"session_type": "review"})

    message = _text(result)
    assert result.is_error
    assert "Error executing tool commit_memory_batch: memory batch commit failed:" in message
    assert "git commit" in message
    assert "exited with status 1" in message
    assert "HOOKFAIL: review hook rejected this commit" in message
    assert "Memory paths may remain staged after this failure" in message
