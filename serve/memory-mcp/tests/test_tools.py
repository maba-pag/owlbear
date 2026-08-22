"""Unit tests for memory MCP tool failure handling."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_memory_mcp import tools


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
