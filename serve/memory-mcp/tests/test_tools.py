"""Unit tests for memory MCP tool failure handling."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_memory_mcp import tools


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
async def test_commit_memory_batch_reports_and_logs_git_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = subprocess.CalledProcessError(
        1,
        ["git", "commit", "-m", "memory batch"],
        stderr="HOOKFAIL: review hook rejected this commit",
    )

    def fail_commit(*_args: object, **_kwargs: object) -> str:
        raise error

    monkeypatch.setattr(tools, "commit_batch", fail_commit)
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(memory_dir=tmp_path),
        ),
    )

    with (
        caplog.at_level(logging.ERROR, logger="owlbear_memory_mcp.tools"),
        pytest.raises(ToolError) as raised,
    ):
        await tools.commit_memory_batch(context, session_type="review")

    message = str(raised.value)
    assert message.startswith("memory batch commit failed: git commit -m 'memory batch' exited with status 1")
    assert "HOOKFAIL: review hook rejected this commit" in message
    assert "Memory paths may remain staged after this failure" in message
    assert "HOOKFAIL: review hook rejected this commit" in caplog.text


@pytest.mark.asyncio
async def test_commit_memory_batch_routes_deletion_refusal_to_tool_error(tmp_path: Path) -> None:
    memory_dir = tmp_path / ".owlbear" / "memory"
    memory_dir.mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")

    engine = MemoryEngine(memory_dir)
    pending = engine.save(
        title="Approved memory",
        content="An approved entry cannot be physically removed.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=[],
    )
    curated = engine.edit(pending.id, {"scope_agents": ["test-agent"]}, pending.updated_at)
    approved = engine.approve(curated.id, curated.updated_at)
    memory_path = memory_dir / f"{approved.id}.md"
    relative_path = memory_path.relative_to(tmp_path).as_posix()
    _git(tmp_path, "add", "--", relative_path)
    _git(tmp_path, "commit", "-m", "initial memory")
    initial_head = _git(tmp_path, "rev-parse", "HEAD")
    memory_path.unlink()

    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(engine=engine, memory_dir=memory_dir),
        ),
    )

    with pytest.raises(ToolError) as raised:
        await tools.commit_memory_batch(context, session_type="review")

    message = str(raised.value)
    assert "memory batch validation failed" in message
    assert "physical deletion is only allowed" in message
    assert relative_path in message
    assert "Restore the file from HEAD" in message
    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    assert _git(tmp_path, "diff", "--cached", "--name-only") == ""
