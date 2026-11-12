"""Live MCP contract tests for memory server registration."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import mcp
import pytest
from mcp.types import CallToolResult
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.models import AssessmentReceipt

from owlbear_memory_mcp import git as memory_git
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


def _payload(result: CallToolResult) -> dict:
    assert not result.is_error
    return json.loads(_text(result))


def _recall_revision(result: CallToolResult, entry_id: str) -> str:
    text = _text(result)
    marker = f"Entry ID: `{entry_id}`\nRevision: `"
    assert not result.is_error
    assert marker in text
    return text.partition(marker)[2].partition("`")[0]


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _bound_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A project folder of a shared repository whose global settings hold the memory values, as the server runs."""
    root = tmp_path / "common"
    held = {
        "outstanding_boost": 0.1,
        "unremarkable_penalty": 0.01,
        "stale_factor": 50,
        "recall_limit": 20,
        "explore_slots": 2,
        "challenge_slots": 2,
    }
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    (root / "config.json").write_text(json.dumps({"format": 21, "memory": held}), encoding="utf-8")
    store = root / "shop" / "memory"
    monkeypatch.setenv("OWLBEAR_MEMORY_DIR", str(store))
    monkeypatch.setenv("OWLBEAR_MEMORY_GLOBAL_DIR", str(root / "memory"))
    return store


@pytest.mark.asyncio
async def test_live_curator_mutations_bind_to_read_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Fresh curator actions follow read content across approval, sessions, edits and deletion."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = memory_entry(memory_dir, title="Curate pending", state=MemoryState.PENDING)
    discarded = memory_entry(memory_dir, title="Delete pending", state=MemoryState.PENDING)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OWLBEAR_MEMORY_AGENTS", "planner, builder,reviewer")

    async with mcp.Client(memory_mcp) as client:
        pending_revision = _payload(await client.call_tool("read_memory", {"entry_id": entry.id}))["revision"]
        curated_payload = _payload(
            await client.call_tool(
                "curate_memory",
                {"entry_id": entry.id, "revision": pending_revision, "scope_agents": ["builder"]},
            )
        )
        assert curated_payload["state"] == "curated"
        revision = curated_payload["revision"]
        assert revision != pending_revision
        read_payload = _payload(await client.call_tool("read_memory", {"entry_id": entry.id}))
        list_result = await client.call_tool("list_memories", {"states": ["curated"]})
        assert not list_result.is_error
        listed_payload = [json.loads(item.text) for item in list_result.content if hasattr(item, "text")]
        assert read_payload["revision"] == revision
        assert len(revision) == 16
        assert all(character in "0123456789abcdef" for character in revision)
        assert len(listed_payload) == 1
        assert listed_payload[0]["revision"] == revision

        approved = _payload(
            await client.call_tool(
                "approve_memory",
                {"entry_id": entry.id, "revision": revision},
            )
        )
        assert approved["state"] == "approved"
        assert approved["revision"] == revision

    async with mcp.Client(memory_mcp) as client:
        reloaded_read = _payload(await client.call_tool("read_memory", {"entry_id": entry.id}))
        reloaded_list = await client.call_tool("list_memories", {"states": ["approved"]})
        assert not reloaded_list.is_error
        assert reloaded_read["revision"] == revision
        reloaded_payload = [json.loads(item.text) for item in reloaded_list.content if hasattr(item, "text")]
        assert reloaded_payload[0]["revision"] == revision
        edited_payload = _payload(
            await client.call_tool(
                "curate_memory",
                {"entry_id": entry.id, "revision": revision, "content": "Updated through MCP."},
            )
        )
        assert edited_payload["state"] == "curated"
        assert edited_payload["revision"] != revision
        changed = MemoryEngine(memory_dir).edit(
            entry.id,
            {"content": "Changed by a second engine."},
            expected_revision=edited_payload["revision"],
        )
        assert changed.revision != edited_payload["revision"]
        changed_read = _payload(await client.call_tool("read_memory", {"entry_id": entry.id}))
        assert changed_read["revision"] == changed.revision

        soft_deleted = _payload(
            await client.call_tool("delete_memory", {"entry_id": entry.id, "revision": changed.revision})
        )
        assert soft_deleted["state"] == "deleted"
        assert (memory_dir / f"{entry.id}.md").exists()
        pending_read = _payload(await client.call_tool("read_memory", {"entry_id": discarded.id}))
        _payload(
            await client.call_tool(
                "delete_memory",
                {"entry_id": discarded.id, "revision": pending_read["revision"]},
            )
        )
        assert not (memory_dir / f"{discarded.id}.md").exists()


@pytest.mark.asyncio
async def test_live_server_rejects_stale_revisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Stale curator mutations name both revisions and preserve the changed entry."""
    memory_dir = tmp_path / ".owlbear/memory"
    entries = {
        "approve_memory": memory_entry(memory_dir, title="Stale approve", state=MemoryState.CURATED),
        "curate_memory": memory_entry(memory_dir, title="Stale curate", state=MemoryState.CURATED),
        "delete_memory": memory_entry(memory_dir, title="Stale delete", state=MemoryState.CURATED),
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
async def test_live_server_rejects_missing_and_malformed_revisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Revision schema failures do not mutate entries through the live server."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = memory_entry(memory_dir, title="Invalid revisions", state=MemoryState.CURATED)
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
async def test_live_assessments_reject_stale_revision_and_apply_sibling_item(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """A stale recalled item is byte-stable while a current sibling is applied."""
    memory_dir = _bound_store(monkeypatch, tmp_path)
    stale_entry = memory_entry(memory_dir, title="Stale assessment", state=MemoryState.APPROVED)
    current_entry = memory_entry(memory_dir, title="Current assessment", state=MemoryState.APPROVED)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        recalled = await client.call_tool("recall_memory", {"agent": "test-agent"})
        stale_revision = _recall_revision(recalled, stale_entry.id)
        current_revision = _recall_revision(recalled, current_entry.id)

        second_engine = MemoryEngine(memory_dir)
        edited = second_engine.edit(
            stale_entry.id,
            {"content": "Changed after recall."},
            expected_revision=stale_revision,
        )
        current = second_engine.approve(stale_entry.id, expected_revision=edited.revision)
        stale_path = memory_dir / f"{stale_entry.id}.md"
        stale_bytes = stale_path.read_bytes()

        result = await client.call_tool(
            "assess_memories",
            {
                "assessments": [
                    {"entry_id": stale_entry.id, "revision": stale_revision, "bucket": "outstanding"},
                    {"entry_id": current_entry.id, "revision": current_revision, "bucket": "outstanding"},
                ],
                "task_id": "stale-batch-task",
            },
        )

    assert not result.is_error
    by_id = {item["entry_id"]: item for item in json.loads(_text(result))["results"]}
    stale_result = by_id[stale_entry.id]
    assert stale_result["success"] is False
    assert "changed since recall" in stale_result["error"].lower()
    assert current.revision in stale_result["error"]
    assert "feedback was not applied" in stale_result["error"].lower()
    assert stale_path.read_bytes() == stale_bytes

    current_result = by_id[current_entry.id]
    assert current_result["success"] is True
    assert current_result["already_applied"] is False
    assert current_result["recorded_bucket"] == "outstanding"
    persisted = MemoryEngine(memory_dir).get_entry(current_entry.id)
    assert persisted.outstanding_count == 1
    assert len(persisted.assessment_receipts) == 1


@pytest.mark.asyncio
async def test_live_rating_replay_keeps_the_first_bucket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Same-task retries retain the first bucket; a different task is applied."""
    memory_dir = _bound_store(monkeypatch, tmp_path)
    entry = memory_entry(memory_dir, title="Receipt replay", state=MemoryState.APPROVED)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        recalled = await client.call_tool("recall_memory", {"agent": "test-agent"})
        revision = _recall_revision(recalled, entry.id)

        first = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": revision, "bucket": "outstanding"}],
                "task_id": "assessment-task-one",
            },
        )
        replay = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": revision, "bucket": "unremarkable"}],
                "task_id": "assessment-task-one",
            },
        )
        other_task = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": revision, "bucket": "unremarkable"}],
                "task_id": "assessment-task-two",
            },
        )
        read = await client.call_tool("read_memory", {"entry_id": entry.id})
        listed = await client.call_tool("list_memories", {})
        assert not read.is_error
        assert not listed.is_error
        assert "challenges" not in json.loads(_text(read))
        assert all("challenges" not in json.loads(item.text) for item in listed.content if hasattr(item, "text"))

    first_result = json.loads(_text(first))["results"][0]
    replay_result = json.loads(_text(replay))["results"][0]
    other_result = json.loads(_text(other_task))["results"][0]
    assert not first.is_error
    assert not replay.is_error
    assert not other_task.is_error
    assert first_result["success"] is True
    assert first_result["already_applied"] is False
    assert first_result["recorded_bucket"] == "outstanding"
    assert replay_result["success"] is True
    assert replay_result["already_applied"] is True
    assert replay_result["recorded_bucket"] == "outstanding"
    assert other_result["success"] is True
    assert other_result["already_applied"] is False
    assert other_result["recorded_bucket"] == "unremarkable"
    for result in (first_result, replay_result, other_result):
        assert "challenges" not in result
        assert "state" not in result

    persisted = MemoryEngine(memory_dir).get_entry(entry.id)
    assert persisted.outstanding_count == 1
    assert persisted.unremarkable_count == 1
    assert len(persisted.assessment_receipts) == 2


@pytest.mark.asyncio
async def test_live_challenge_replay_preserves_ordered_history(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Challenges and replays expose the same ordered public history in each exceptional state."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = memory_entry(memory_dir, title="Challenge replay", state=MemoryState.APPROVED)
    monkeypatch.chdir(tmp_path)
    task_ids = ("challenge-task-a", "challenge-task-b")

    async with mcp.Client(memory_mcp) as client:
        history = []
        for task_id, state in zip(task_ids, ("contested", "disputed"), strict=True):
            assessment = await client.call_tool(
                "assess_memories",
                {
                    "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "factually_wrong"}],
                    "task_id": task_id,
                },
            )
            assert not assessment.is_error
            result = json.loads(_text(assessment))["results"][0]
            assert result["success"] is True
            assert result["already_applied"] is False
            assert result["state"] == state
            challenges = result["challenges"]
            assert len(challenges) == len(history) + 1
            assert challenges[:-1] == history
            history = challenges
            assert [challenge["task_id"] for challenge in history] == list(task_ids[: len(history)])
            assert all(challenge["revision"] == entry.revision for challenge in history)
            assert all(challenge["recorded_at"] for challenge in history)
            assert all(set(challenge) == {"task_id", "revision", "recorded_at"} for challenge in history)
            replay = await client.call_tool(
                "assess_memories",
                {
                    "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "factually_wrong"}],
                    "task_id": task_id,
                },
            )
            assert not replay.is_error
            assert json.loads(_text(replay))["results"][0] == result | {"already_applied": True}
            read = await client.call_tool("read_memory", {"entry_id": entry.id})
            listed = await client.call_tool("list_memories", {})
            assert not read.is_error
            assert not listed.is_error
            read_payload = json.loads(_text(read))
            listed_payload = [json.loads(item.text) for item in listed.content if hasattr(item, "text")]
            assert len(listed_payload) == 1
            for payload in (read_payload, listed_payload[0], result):
                assert payload["state"] == state
                assert payload["challenges"] == history
                assert "contested" + "_by_task" not in payload
                assert "assessment_receipts" not in payload
            assert read_payload["revision"] == entry.revision


@pytest.mark.asyncio
async def test_live_assessments_reject_malformed_batches_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Malformed items or task IDs reject the whole registered-tool batch."""
    memory_dir = tmp_path / ".owlbear/memory"
    first_entry = memory_entry(memory_dir, title="Valid batch item", state=MemoryState.APPROVED)
    second_entry = memory_entry(memory_dir, title="Malformed batch item", state=MemoryState.APPROVED)
    first_path = memory_dir / f"{first_entry.id}.md"
    second_path = memory_dir / f"{second_entry.id}.md"
    before = {first_entry.id: first_path.read_bytes(), second_entry.id: second_path.read_bytes()}
    valid_item = {"entry_id": first_entry.id, "revision": first_entry.revision, "bucket": "outstanding"}
    malformed_items = [
        {"entry_id": second_entry.id, "bucket": "outstanding"},
        {"entry_id": second_entry.id, "revision": "a" * 15, "bucket": "outstanding"},
        {"entry_id": second_entry.id, "revision": "A" + "a" * 15, "bucket": "outstanding"},
        {
            "entry_id": second_entry.id,
            "revision": second_entry.revision,
            "bucket": "outstanding",
            "unexpected": True,
        },
    ]
    invalid_task_ids = ("", "x" * 129, "task 1", "task-1\n", "task-\u00e9")
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        for malformed_item in malformed_items:
            result = await client.call_tool(
                "assess_memories",
                {
                    "assessments": [valid_item, malformed_item],
                    "task_id": "valid-task-id",
                },
            )
            assert result.is_error
            assert first_path.read_bytes() == before[first_entry.id]
            assert second_path.read_bytes() == before[second_entry.id]

        for task_id in invalid_task_ids:
            result = await client.call_tool(
                "assess_memories",
                {"assessments": [valid_item], "task_id": task_id},
            )
            assert result.is_error
            assert first_path.read_bytes() == before[first_entry.id]
            assert second_path.read_bytes() == before[second_entry.id]


@pytest.mark.asyncio
async def test_live_assessment_replay_survives_transition_to_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """An idempotent replay is returned before the now-stale state guard."""
    memory_dir = _bound_store(monkeypatch, tmp_path)
    entry = memory_entry(memory_dir, title="Stale replay", state=MemoryState.APPROVED)
    entry = entry.model_copy(update={"didnt_use_count": 50})
    path = memory_dir / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=memory_dir)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        first = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "didnt_use"}],
                "task_id": "stale-transition-task",
            },
        )
        first_result = json.loads(_text(first))["results"][0]
        assert not first.is_error
        assert first_result["success"] is True
        assert first_result["already_applied"] is False
        assert MemoryEngine(memory_dir).get_entry(entry.id).state == MemoryState.STALE
        before_replay = path.read_bytes()

        replay = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "outstanding"}],
                "task_id": "stale-transition-task",
            },
        )

    replay_result = json.loads(_text(replay))["results"][0]
    assert not replay.is_error
    assert replay_result["success"] is True
    assert replay_result["already_applied"] is True
    assert replay_result["recorded_bucket"] == "didnt_use"
    assert path.read_bytes() == before_replay


@pytest.mark.asyncio
async def test_live_assessment_capacity_refusal_preserves_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The registered tool reports an unstorable receipt without changing entry bytes or state."""
    memory_dir = _bound_store(monkeypatch, tmp_path)
    entry = MemoryEntry(
        id="550e8400-e29b-41d4-a716-446655440000",
        title="t" * 6700,
        content="c" * 1024,
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        state=MemoryState.APPROVED,
        scope_agents=["test-agent"],
        source_agent="test-agent",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        approved_at="2026-01-01T00:00:00+00:00",
    )
    receipt = AssessmentReceipt(task_id="capacity-task", revision=entry.revision, bucket="outstanding")
    updated_base = entry.model_copy(
        update={
            "outstanding_count": 1,
            "score": 0.9,
            "updated_at": "2026-10-09T12:34:56.123456+00:00",
            "assessment_receipts": [receipt],
        }
    )
    assert storage.serialized_entry_size(entry) <= storage.MAX_ENTRY_FILE_SIZE_BYTES
    assert storage.serialized_entry_size(updated_base) > storage.MAX_ENTRY_FILE_SIZE_BYTES
    path = memory_dir / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=memory_dir)
    before = path.read_bytes()
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        result = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "outstanding"}],
                "task_id": "capacity-task",
            },
        )

    item = json.loads(_text(result))["results"][0]
    persisted = MemoryEngine(memory_dir).get_entry(entry.id)
    assert not result.is_error
    assert item["success"] is False
    assert "newest assessment receipt" in item["error"]
    assert path.read_bytes() == before
    assert persisted == entry


@pytest.mark.asyncio
async def test_live_server_accepts_optional_recall_and_open_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Registered tools accept guided recall and any nonblank string provenance."""
    _bound_store(monkeypatch, tmp_path)
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
                "where": "global",
            },
        )
        unrecommended = await client.call_tool(
            "save_memory",
            {"title": "No scope", "content": "x", "categories": ["process"], "confidence": 0.8, "source_agent": "*"},
        )
        invalid = await client.call_tool("recall_memory", {"agent": 1})

    assert not recall.is_error
    assert "Known agents: none discovered." in _text(recall)
    assert not saved.is_error
    assert unrecommended.is_error  # the saver always recommends a scope (TD-293)
    assert invalid.is_error


@pytest.mark.asyncio
@pytest.mark.parametrize("hook_refuses", [False, True], ids=["commit-and-noop", "hook-refusal"])
async def test_live_review_batch_reports_commit_noop_or_hook_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    *,
    hook_refuses: bool,
) -> None:
    """The registered batch tool exposes real Git success, no-op or logged hook refusal."""
    (tmp_path / ".owlbear/memory").mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / ".owlbear/memory/reviewed.md").write_text(_REVIEWED_MEMORY, encoding="utf-8")
    if hook_refuses:
        hook = tmp_path / ".git/hooks/pre-commit"
        hook.write_text(
            "#!/bin/sh\nprintf '%s\\n' 'HOOKFAIL: review hook rejected this commit' >&2\nexit 1\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
    monkeypatch.chdir(tmp_path)

    caplog.set_level(logging.ERROR, logger="owlbear_memory_mcp.tools")
    async with mcp.Client(memory_mcp) as client:
        committed = await client.call_tool("commit_memory_batch", {"session_type": "review"})
        if hook_refuses:
            message = _text(committed)
            assert committed.is_error
            assert message.startswith(
                "Error executing tool commit_memory_batch: memory batch commit failed: "
                "git commit -m 'chore: memory review batch (memory-mcp, memory-reviewer)'"
            )
            assert "exited with status 1" in message
            assert "HOOKFAIL: review hook rejected this commit" in message
            assert "Memory paths may remain staged after this failure" in message
            records = [record for record in caplog.records if record.name == "owlbear_memory_mcp.tools"]
            assert len(records) == 1
            assert "HOOKFAIL: review hook rejected this commit" in records[0].getMessage()
            assert "exited with status 1" in records[0].getMessage()
            assert records[0].exc_info is not None
            return
        empty = await client.call_tool("commit_memory_batch", {"session_type": "review"})

    committed_payload = json.loads(_text(committed))
    empty_payload = json.loads(_text(empty))
    assert not committed.is_error
    assert committed_payload["committed"] is True
    assert committed_payload["deferred_deletions"] == []
    assert committed_payload["commit_sha"] == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "log", "-1", "--format=%s") == ("chore: memory review batch (memory-mcp, memory-reviewer)")
    assert not empty.is_error
    assert empty_payload == {
        "session_type": "review",
        "commit_sha": None,
        "committed": False,
        "deferred_deletions": [],
        "hint": "No memory changes to commit.",
    }


@pytest.mark.asyncio
async def test_live_server_reports_deferred_duplicate_deletions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    memory_dir = tmp_path / ".owlbear/memory"
    memory_dir.mkdir(parents=True)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")

    engine = MemoryEngine(memory_dir)
    pending = engine.save(
        title="Tracked memory",
        content="Approved memory content.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=[],
    )
    curated = engine.edit(pending.id, {"scope_agents": ["test-agent"]}, pending.updated_at)
    approved = engine.approve(curated.id, curated.updated_at)
    tracked_path = memory_dir / f"{approved.id}.md"
    tracked_relative = tracked_path.relative_to(tmp_path).as_posix()
    _git(tmp_path, "add", "--", tracked_relative)
    _git(tmp_path, "commit", "-m", "initial memory")
    initial_head = _git(tmp_path, "rev-parse", "HEAD")

    storage.write_entry(
        memory_dir / "newer-pending-copy.md",
        approved.model_copy(
            update={
                "title": "Newer pending copy",
                "content": "Pending memory content.",
                "state": MemoryState.PENDING,
                "approved_at": None,
                "updated_at": "2099-08-30T00:00:00+00:00",
            },
        ),
        memory_dir=memory_dir,
    )
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        result = await client.call_tool("commit_memory_batch", {"session_type": "review"})

    payload = json.loads(_text(result))
    assert not result.is_error
    assert payload["session_type"] == "review"
    assert payload["commit_sha"] is None
    assert payload["committed"] is False
    assert payload["deferred_deletions"] == [tracked_relative]
    assert "curate the surviving pending entry" in payload["hint"].lower()
    assert _git(tmp_path, "rev-parse", "HEAD") == initial_head
    head_paths = _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory").splitlines()
    assert head_paths == [tracked_relative]
    head_entry = storage.read_entry_bytes_strict(_git(tmp_path, "show", f"HEAD:{tracked_relative}").encode())
    assert head_entry.id == approved.id


@pytest.mark.asyncio
@pytest.mark.parametrize("discovery", ["explicit", "claimed"])
async def test_live_project_store_reads_late_global_memory_without_writing_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    discovery: str,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """Both discovery paths read late Global entries in one session but write only their project."""
    store = _bound_store(monkeypatch, tmp_path)
    data = store.parent.parent
    work = tmp_path
    title = "Shared store"
    if discovery == "claimed":
        title = "Claimed store"
        store.parent.mkdir(parents=True, exist_ok=True)
        (data / "shop" / "repository").write_text("github.com/acme/shop\n", encoding="utf-8")
        work = tmp_path / "work"
        (work / ".owlbear").mkdir(parents=True)
        _git(work, "init", "-q")
        _git(work, "remote", "add", "origin", "git@github.com:acme/shop.git")
        monkeypatch.delenv("OWLBEAR_MEMORY_DIR")
        monkeypatch.delenv("OWLBEAR_MEMORY_GLOBAL_DIR")
        monkeypatch.setenv("OWLBEAR_DATA", str(data))
    own = memory_entry(
        store, title="Run the shop's tests", state=MemoryState.APPROVED, scope_agents=["*"], source_agent="*"
    )
    monkeypatch.chdir(work)
    args = {
        "title": title,
        "content": "Saved into the shared repository's project folder.",
        "categories": ["process"],
        "confidence": 0.8,
        "source_agent": "builder",
        "where": "project",
    }

    async with mcp.Client(memory_mcp) as client:
        initial = await client.call_tool("list_memories", {})
        assert not initial.is_error
        assert [json.loads(item.text)["id"] for item in initial.content if hasattr(item, "text")] == [own.id]
        shared = data / "memory"
        common = memory_entry(
            shared, title="Global habit", state=MemoryState.APPROVED, scope_agents=["*"], source_agent="*"
        )
        listed = await client.call_tool("list_memories", {})
        recalled = await client.call_tool("recall_memory", {"agent": "test-agent"})
        universal = await client.call_tool("recall_memory", {"agent": "*"})
        assert not listed.is_error
        assert {
            json.loads(item.text)["id"]: json.loads(item.text)["where"]
            for item in listed.content
            if hasattr(item, "text")
        } == {own.id: "project", common.id: "global"}
        assert "Global habit" in _text(recalled)
        assert not universal.is_error
        assert "Global habit" in _text(universal)
        for entry, where in ((own, "project"), (common, "global")):
            payload = _payload(await client.call_tool("read_memory", {"entry_id": entry.id}))
            assert (payload["where"], payload["title"]) == (where, entry.title)
        before = {path.name: path.read_bytes() for path in shared.iterdir()}
        refused = await client.call_tool(
            "approve_memory", {"entry_id": common.id, "revision": _recall_revision(recalled, common.id)}
        )
        assert refused.is_error
        assert "not found" in _text(refused)
        saved = _payload(await client.call_tool("save_memory", args))
        recommendation = _payload(
            await client.call_tool(
                "save_memory", args | {"title": "New", "content": "new", "source_agent": "*", "where": "global"}
            )
        )

    assert f"title: {title}" in (store / f"{saved['id']}.md").read_text(encoding="utf-8")
    assert (recommendation["recommended"], recommendation["state"]) == ("global", "pending")
    assert (store / f"{recommendation['id']}.md").is_file()
    assert {path.name: path.read_bytes() for path in shared.iterdir()} == before
    assert not (work / ".owlbear" / "memory").exists()
    if discovery == "explicit":
        assert not (work / ".owlbear").exists()


def _whole_error() -> str:
    """A long error with a distinct beginning, middle and end, as delivery-next's ``whole_error`` fixture builds it."""
    words = [f"w{i:04d}" for i in range(700)]
    lines = [" ".join(words[i : i + 20]) for i in range(0, 700, 20)]
    return "\n".join(['BEGIN <a & "b">', *lines[:17], "MIDDLE", *lines[17:], "END"])


def _refusal_logged(caplog: pytest.LogCaptureFixture, tool: str) -> list[str]:
    """The MCP server's own log line for a tool's refusal: its answer, repr'd onto one line."""
    prefix = f"Tool {tool!r} failed: "
    return [record.getMessage() for record in caplog.records if record.getMessage().startswith(prefix)]


@pytest.mark.asyncio
async def test_unreadable_global_settings_reach_the_tool_answer_whole(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A settings read failing with a long error is answered with its type and every line of its message (#971)."""
    store = _bound_store(monkeypatch, tmp_path)
    config = store.parent.parent / "config.json"
    error = _whole_error()
    read_text = Path.read_text

    def unreadable(path: Path, *args: object, **kwargs: object) -> str:
        if path == config:
            raise OSError(error)
        return read_text(path, *args, **kwargs)

    caplog.set_level(logging.INFO)
    async with mcp.Client(memory_mcp) as client:
        monkeypatch.setattr(Path, "read_text", unreadable)
        result = await client.call_tool("recall_memory", {"agent": "builder", "limit": 5})

    refusal = f"the global settings {config} can't be read, so no memory value is known: OSError: {error}"
    expected = f"Error executing tool recall_memory: {refusal}"
    assert result.is_error
    assert _text(result) == expected
    assert _refusal_logged(caplog, "recall_memory") == [f"Tool 'recall_memory' failed: {expected!r}"]


@pytest.mark.asyncio
async def test_an_unreadable_memory_file_reaches_the_batch_answer_whole(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    memory_entry: Callable[..., MemoryEntry],
) -> None:
    """A memory file whose read fails names the file, the validation and the read error whole in the answer (#971)."""
    store = _bound_store(monkeypatch, tmp_path)
    entry = memory_entry(store, title="Unreadable habit", state=MemoryState.APPROVED)
    target = store / f"{entry.id}.md"
    error = _whole_error()
    opened = os.open

    def refused(path: object, *args: object, **kwargs: object) -> int:
        if Path(os.fsdecode(path)) == target:  # type: ignore[arg-type]
            raise OSError(error)
        return opened(path, *args, **kwargs)  # type: ignore[arg-type]

    caplog.set_level(logging.INFO)
    monkeypatch.setattr(memory_git.os, "open", refused)
    async with mcp.Client(memory_mcp) as client:
        result = await client.call_tool("commit_memory_batch", {"session_type": "review"})

    inner = f"memory batch validation failed: unsafe or unreadable memory path {target.name}: OSError: {error}"
    refusal = f"memory batch validation failed:\n- shop/memory/{target.name}: ValueError: {inner}"
    expected = f"Error executing tool commit_memory_batch: {refusal}"
    assert result.is_error
    assert _text(result) == expected
    assert _refusal_logged(caplog, "commit_memory_batch") == [f"Tool 'commit_memory_batch' failed: {expected!r}"]
