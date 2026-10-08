"""Live MCP contract tests for memory server registration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import mcp
import pytest
from mcp.types import CallToolResult
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry, MemoryState, storage
from owlbear_memory.models import AssessmentReceipt

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
async def test_live_assessments_reject_stale_revision_and_apply_sibling_item(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A stale recalled item is byte-stable while a current sibling is applied."""
    memory_dir = tmp_path / ".owlbear/memory"
    stale_entry = _create_entry(memory_dir, title="Stale assessment", state=MemoryState.APPROVED)
    current_entry = _create_entry(memory_dir, title="Current assessment", state=MemoryState.APPROVED)
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
async def test_live_assessments_replay_first_bucket_and_allow_different_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Same-task retries retain the first bucket; a different task is applied."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = _create_entry(memory_dir, title="Receipt replay", state=MemoryState.APPROVED)
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

    persisted = MemoryEngine(memory_dir).get_entry(entry.id)
    assert persisted.outstanding_count == 1
    assert persisted.unremarkable_count == 1
    assert len(persisted.assessment_receipts) == 2


@pytest.mark.asyncio
async def test_live_assessments_reject_malformed_batches_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Malformed items or task IDs reject the whole registered-tool batch."""
    memory_dir = tmp_path / ".owlbear/memory"
    first_entry = _create_entry(memory_dir, title="Valid batch item", state=MemoryState.APPROVED)
    second_entry = _create_entry(memory_dir, title="Malformed batch item", state=MemoryState.APPROVED)
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
) -> None:
    """An idempotent replay is returned before the now-stale state guard."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = _create_entry(memory_dir, title="Stale replay", state=MemoryState.APPROVED)
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
    memory_dir = tmp_path / ".owlbear/memory"
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
async def test_live_agent_lifecycle_writes_drop_obsolete_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Registered rename and delete tools discard receipts when their scope changes revision."""
    memory_dir = tmp_path / ".owlbear/memory"
    entry = _create_entry(memory_dir, title="Lifecycle receipts", state=MemoryState.APPROVED)
    monkeypatch.chdir(tmp_path)

    async with mcp.Client(memory_mcp) as client:
        first = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": entry.revision, "bucket": "outstanding"}],
                "task_id": "before-rename",
            },
        )
        renamed = await client.call_tool(
            "rename_agent_memories",
            {"old_name": "test-agent", "new_name": "renamed-agent"},
        )
        renamed_entry = MemoryEngine(memory_dir).get_entry(entry.id)
        second = await client.call_tool(
            "assess_memories",
            {
                "assessments": [{"entry_id": entry.id, "revision": renamed_entry.revision, "bucket": "outstanding"}],
                "task_id": "after-rename",
            },
        )
        deleted = await client.call_tool("delete_agent_memories", {"agent": "renamed-agent"})

    assert not first.is_error
    assert not renamed.is_error
    assert not second.is_error
    assert not deleted.is_error
    assert json.loads(_text(first))["results"][0]["success"] is True
    assert renamed_entry.scope_agents == ["renamed-agent"]
    assert renamed_entry.assessment_receipts == []
    assert json.loads(_text(second))["results"][0]["success"] is True
    deleted_entry = MemoryEngine(memory_dir).get_entry(entry.id)
    assert deleted_entry.state == MemoryState.DELETED
    assert deleted_entry.scope_agents == []
    assert deleted_entry.assessment_receipts == []


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
