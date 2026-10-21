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


def _approved(engine: MemoryEngine, title: str) -> str:
    saved = engine.save(
        title=title,
        content=f"{title}: what every agent should know.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.9,
        source_agent="*",
        scope_agents=[],
    )
    curated = engine.edit(saved.id, {"scope_agents": ["*"]}, saved.updated_at)
    return engine.approve(curated.id, curated.updated_at).id


@pytest.mark.asyncio
async def test_agents_read_global_memory_beside_their_projects_and_write_only_their_projects(tmp_path: Path) -> None:
    """TD-241: the store and Global memory are both read; a save goes to the store."""
    mine, shared_dir = MemoryEngine(tmp_path / "shop" / "memory"), tmp_path / "memory"
    own = _approved(mine, "Run the shop's tests")
    context = SimpleNamespace(
        request_context=SimpleNamespace(
            lifespan_context=SimpleNamespace(
                engine=mine, memory_dir=tmp_path / "shop" / "memory", global_dir=shared_dir
            )
        )
    )
    before_any = {entry["id"] for entry in await tools.list_memories(context)}
    common = _approved(MemoryEngine(shared_dir), "Every project signs commits")  # the first Make global, mid-session
    listed = {entry["id"] for entry in await tools.list_memories(context)}
    recalled = await tools.recall_memory(context, agent="*")
    read = await tools.read_memory(context, entry_id=common)
    assert (before_any, listed, "Every project signs commits" in recalled, read["title"]) == (
        {own}, {own, common}, True, "Every project signs commits"
    )  # fmt: skip
    before = sorted(p.name for p in (tmp_path / "memory").iterdir())
    saved = await tools.save_memory(
        context, title="New", content="new", categories=["process"], confidence=0.8, source_agent="*"
    )
    assert sorted(p.name for p in (tmp_path / "memory").iterdir()) == before
    assert (tmp_path / "shop" / "memory" / f"{saved['id']}.md").is_file()


@pytest.mark.asyncio
async def test_disputed_entry_answers_carry_both_challenges_and_unchallenged_ones_omit_them(tmp_path: Path) -> None:
    """A curator sees both reports and the challenged revision; an unchallenged entry's answer stays small."""
    engine = MemoryEngine(tmp_path)
    disputed, quiet = _approved(engine, "Disputed guidance"), _approved(engine, "Quiet guidance")
    revision = engine.get_entry(disputed).revision
    context = SimpleNamespace(request_context=SimpleNamespace(lifespan_context=SimpleNamespace(engine=engine)))

    answers = [
        (await tools.assess_memories(context, assessments=[item], task_id=task))["results"][0]
        for task, item in (
            ("task-a", {"entry_id": disputed, "revision": revision, "bucket": "factually_wrong"}),
            ("task-b", {"entry_id": disputed, "revision": revision, "bucket": "factually_wrong"}),
            ("task-c", {"entry_id": quiet, "revision": engine.get_entry(quiet).revision, "bucket": "outstanding"}),
        )
    ]
    read = await tools.read_memory(context, entry_id=disputed)
    listed = {entry["id"]: entry for entry in await tools.list_memories(context)}

    history = [(c["task_id"], c["revision"]) for c in read["challenges"]]
    assert history == [("task-a", revision), ("task-b", revision)]
    assert listed[disputed]["challenges"] == read["challenges"]
    assert (answers[0]["state"], answers[1]["state"]) == ("contested", "disputed")
    assert [(c["task_id"], c["revision"]) for c in answers[1]["challenges"]] == history
    assert "challenges" not in answers[2]
    assert "state" not in answers[2]
    assert "challenges" not in listed[quiet]
    assert "challenges" not in await tools.read_memory(context, entry_id=quiet)
