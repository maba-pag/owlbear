"""The deletion refusal has an independent adapter translation contract."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_memory_mcp import tools


@pytest.mark.asyncio
async def test_commit_memory_batch_routes_deletion_refusal_to_tool_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    message = (
        "memory batch validation failed: physical deletion is only allowed for "
        "pending or deleted entries .owlbear/memory/approved.md; HEAD state is approved. "
        "Restore the file from HEAD with `git restore --source=HEAD -- .owlbear/memory/approved.md`, "
        "soft-delete it, commit the batch, then purge."
    )

    def refuse_commit(*_args: object, **_kwargs: object) -> None:
        raise ValueError(message)

    monkeypatch.setattr(tools, "commit_batch", refuse_commit)

    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(memory_dir=tmp_path),
        ),
    )

    with pytest.raises(ToolError) as raised:
        await tools.commit_memory_batch(context, session_type="review")

    assert str(raised.value) == message
