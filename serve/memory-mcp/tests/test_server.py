"""Live MCP contract tests for memory server registration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import mcp
import pytest
from mcp.types import CallToolResult

from owlbear_memory_mcp.server import mcp as memory_mcp


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
    (tmp_path / ".owlbear/memory/reviewed.md").write_text(
        "---\nstate: approved\n---\n\n# Reviewed\n",
        encoding="utf-8",
    )
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
