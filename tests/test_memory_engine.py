"""Protect canonical MemoryEngine malformed-file accounting."""

from __future__ import annotations

import hashlib
import json
import re
from functools import partial
from pathlib import Path
from unittest.mock import patch

import pytest
from owlbear_memory import LifecycleRecoveryError, MemoryEngine, storage
from owlbear_memory.errors import ConcurrencyError, ValidationError
from owlbear_memory.models import AssessmentReceipt, MemoryEntry, MemoryState

_VALID_ID = "550e8400-e29b-41d4-a716-446655440000"


def _valid_entry_data() -> dict:
    return {
        "id": _VALID_ID,
        "title": "Test Entry",
        "content": "Some content",
        "categories": ["domain-knowledge"],
        "confidence": 0.9,
        "state": "pending",
        "scope_agents": [],
        "source_agent": "test-agent",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "approved_at": None,
    }


def test_memory_entry_revision_is_unpersisted_sha256_digest() -> None:
    entry = MemoryEntry(**_valid_entry_data())
    serialized = json.dumps(
        {
            "title": entry.title,
            "content": entry.content,
            "categories": entry.categories,
            "confidence": entry.confidence,
            "scope_agents": entry.scope_agents,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    assert re.fullmatch(r"[0-9a-f]{16}", entry.revision) is not None
    assert entry.revision == hashlib.sha256(serialized).hexdigest()[:16]
    assert "revision" not in entry.model_dump()


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("title", "Changed title"),
        ("content", "Changed content"),
        ("categories", ["pitfall"]),
        ("confidence", 0.8),
        ("scope_agents", ["other-agent"]),
    ],
)
def test_memory_entry_revision_changes_for_each_content_field(field: str, replacement: object) -> None:
    entry = MemoryEntry(**_valid_entry_data())
    changed = MemoryEntry.model_validate({**entry.model_dump(), field: replacement})

    assert changed.revision != entry.revision


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("categories", ["pitfall", "domain-knowledge"]),
        ("scope_agents", ["second", "first"]),
    ],
)
def test_memory_entry_revision_preserves_list_order(field: str, replacement: list[str]) -> None:
    data = {
        **_valid_entry_data(),
        "categories": ["domain-knowledge", "pitfall"],
        "scope_agents": ["first", "second"],
    }
    entry = MemoryEntry(**data)
    changed = MemoryEntry.model_validate({**entry.model_dump(), field: replacement})

    assert changed.revision != entry.revision


def test_engine_revision_survives_reads_approval_and_assessment(tmp_path: Path) -> None:
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Revision entry",
        content="Stable content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    initial_revision = entry.revision
    entry_path = tmp_path / f"{entry.id}.md"

    assert engine.get_entry(entry.id).revision == initial_revision
    assert MemoryEngine(tmp_path).get_entry(entry.id).revision == initial_revision
    assert "revision:" not in entry_path.read_text(encoding="utf-8")

    curated = engine.edit(entry.id, {"scope_agents": ["test-agent"]}, expected_revision=initial_revision)
    curated_revision = curated.revision
    with patch.object(
        engine,
        "_now_iso",
        side_effect=["2026-02-01T00:00:00+00:00", "2026-02-02T00:00:00+00:00"],
    ):
        approved = engine.approve(entry.id, expected_revision=curated_revision)
        assessed = engine.record_assessment(
            entry.id,
            "outstanding",
            task_id="engine-assessment",
            expected_revision=approved.revision,
        ).entry

    assert curated.state == MemoryState.CURATED
    assert approved.state == MemoryState.APPROVED
    assert approved.updated_at != curated.updated_at
    assert approved.revision == curated_revision
    assert assessed.outstanding_count == 1
    assert assessed.updated_at != approved.updated_at
    assert assessed.revision == curated_revision
    assert MemoryEngine(tmp_path).get_entry(entry.id).revision == curated_revision


@pytest.mark.parametrize("operation", ["approve", "edit", "delete"])
def test_revision_mutations_reject_stale_tokens_without_writing(tmp_path: Path, operation: str) -> None:
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Revision entry",
        content="Initial content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    stale_revision = entry.revision
    if operation == "approve":
        current = engine.edit(entry.id, {"scope_agents": ["test-agent"]}, expected_revision=stale_revision)
    else:
        current = engine.edit(entry.id, {"content": "Current content"}, expected_revision=stale_revision)
    entry_path = tmp_path / f"{entry.id}.md"
    previous_bytes = entry_path.read_bytes()
    if operation == "approve":
        invoke_mutation = partial(engine.approve, entry.id, expected_revision=stale_revision)
    elif operation == "edit":
        invoke_mutation = partial(engine.edit, entry.id, {"title": "Rejected title"}, expected_revision=stale_revision)
    else:
        invoke_mutation = partial(engine.delete, entry.id, expected_revision=stale_revision)

    with pytest.raises(ConcurrencyError) as exc_info:
        invoke_mutation()

    message = str(exc_info.value)
    assert entry.id in message
    assert f"expected revision {stale_revision!r}" in message
    assert f"current revision {current.revision!r}" in message
    assert entry_path.read_bytes() == previous_bytes


@pytest.mark.parametrize("operation", ["approve", "edit", "delete"])
@pytest.mark.parametrize("argument_case", ["none", "both"])
def test_revision_mutations_require_exactly_one_token(
    tmp_path: Path,
    operation: str,
    argument_case: str,
) -> None:
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Revision entry",
        content="Initial content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    tokens = (
        {"expected_updated_at": entry.updated_at, "expected_revision": entry.revision}
        if argument_case == "both"
        else {}
    )
    entry_path = tmp_path / f"{entry.id}.md"
    previous_bytes = entry_path.read_bytes()
    if operation == "approve":
        invoke_mutation = partial(engine.approve, entry.id, **tokens)
    elif operation == "edit":
        invoke_mutation = partial(engine.edit, entry.id, {}, **tokens)
    else:
        invoke_mutation = partial(engine.delete, entry.id, **tokens)

    with pytest.raises(ValidationError):
        invoke_mutation()

    assert entry_path.read_bytes() == previous_bytes


def test_load_counts_malformed_files_without_raising(tmp_path: Path) -> None:
    """Canonical loading skips malformed files and reports their count."""
    (tmp_path / "bad-yaml.md").write_text(
        "---\nkey: {unclosed bracket\n---\n\nsome body\n",
        encoding="utf-8",
    )
    (tmp_path / "missing-fields.md").write_text(
        "---\ntitle: Some Title\n---\n\nsome body\n",
        encoding="utf-8",
    )

    engine = MemoryEngine(tmp_path)

    assert engine.load() == []
    assert engine.parse_errors == 2


@pytest.mark.parametrize(
    ("title", "content", "source_agent", "challenges"),
    [
        ("x" * 7828, "Some content", "test-agent", []),
        ("é" * 3909 + "x" * 10, "Some content", "test-agent", []),
        (
            "x" * 3645,
            "😀" * 1024,
            "test-agent",
            [
                {
                    "task_id": "boundary-task",
                    "revision": "0123456789abcdef",
                    "recorded_at": "2026-02-01T00:00:00+00:00",
                }
            ],
        ),
        ("Test Entry", "Some content", "é" * 3909 + "x" * 10, []),
    ],
    ids=["ascii-title", "multibyte-title", "multibyte-content", "multibyte-metadata"],
)
def test_fresh_engine_reads_each_successful_boundary_write(
    tmp_path: Path,
    title: str,
    content: str,
    source_agent: str,
    challenges: list[dict[str, str]],
) -> None:
    """Successful boundary writes remain readable by a fresh MemoryEngine."""
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "title": title,
            "content": content,
            "source_agent": source_agent,
            "challenges": challenges,
        }
    )
    target = tmp_path / "boundary.md"
    storage.write_entry(target, entry, memory_dir=tmp_path)
    assert target.stat().st_size == storage.MAX_ENTRY_FILE_SIZE_BYTES

    fresh_engine = MemoryEngine(tmp_path)

    entries = fresh_engine.load()
    assert entries == [entry]
    assert fresh_engine.parse_errors == 0


def test_rejected_engine_edit_preserves_previous_file(tmp_path: Path) -> None:
    """An oversized edit fails before replacement and leaves the prior entry readable."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Original title",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="test-agent",
        scope_agents=[],
    )
    target = tmp_path / f"{entry.id}.md"
    original_bytes = target.read_bytes()

    with pytest.raises(ValueError, match=r"serialized entry exceeds 8192 bytes \(got \d+\)"):
        engine.edit(
            entry.id,
            {"title": "x" * 9000},
            expected_updated_at=entry.updated_at,
        )

    assert target.read_bytes() == original_bytes
    fresh_engine = MemoryEngine(tmp_path)
    loaded = fresh_engine.get_entry(entry.id)
    assert loaded.title == "Original title"
    assert fresh_engine.parse_errors == 0


def test_assessment_receipt_window_keeps_only_the_twenty_most_recent(tmp_path: Path) -> None:
    """Assessments keep the newest twenty receipts for the unchanged revision."""
    entry = MemoryEntry(**{**_valid_entry_data(), "state": "approved"})
    storage.write_entry(tmp_path / f"{entry.id}.md", entry, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    engine.load()

    for index in range(21):
        engine.record_assessment(
            entry.id,
            "outstanding",
            task_id=f"task-{index}",
            expected_revision=entry.revision,
        )

    persisted = MemoryEngine(tmp_path).get_entry(entry.id)
    assert [receipt.task_id for receipt in persisted.assessment_receipts] == [f"task-{index}" for index in range(1, 21)]


def test_standard_entry_fits_twenty_maximum_length_receipts(tmp_path: Path) -> None:
    """A standard maximum-content entry stores twenty 128-character task IDs within the file cap."""
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "title": "t" * 120,
            "content": "c" * 1024,
            "state": "approved",
        }
    )
    path = tmp_path / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    engine.load()

    for index in range(20):
        engine.record_assessment(
            entry.id,
            "outstanding",
            task_id=f"{index:03d}" + "x" * 125,
            expected_revision=entry.revision,
        )

    persisted = MemoryEngine(tmp_path).get_entry(entry.id)
    assert len(persisted.assessment_receipts) == 20
    assert len(path.read_bytes()) <= storage.MAX_ENTRY_FILE_SIZE_BYTES


def test_assessment_receipts_are_evicted_oldest_first_to_fit_file_limit(tmp_path: Path) -> None:
    """A new receipt evicts the oldest receipt when the current file size is near its cap."""
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "title": "t" * 3009,
            "content": "c" * 1024,
            "state": "approved",
        }
    )
    receipts = [
        AssessmentReceipt(
            task_id=f"{index:03d}" + "x" * 125,
            revision=entry.revision,
            bucket="outstanding",
        )
        for index in range(19)
    ]
    entry = entry.model_copy(update={"assessment_receipts": receipts})
    path = tmp_path / f"{entry.id}.md"
    storage.write_entry(path, entry, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    engine.load()

    engine.record_assessment(
        entry.id,
        "outstanding",
        task_id="019" + "x" * 125,
        expected_revision=entry.revision,
    )

    persisted = MemoryEngine(tmp_path).get_entry(entry.id)
    assert [receipt.task_id for receipt in persisted.assessment_receipts] == [
        f"{index:03d}" + "x" * 125 for index in range(1, 20)
    ]
    assert len(path.read_bytes()) <= storage.MAX_ENTRY_FILE_SIZE_BYTES


def test_content_edit_discards_receipts_for_previous_revision(tmp_path: Path) -> None:
    """A content edit persists no receipt bound to the replaced revision."""
    entry = MemoryEntry(**{**_valid_entry_data(), "state": "approved"})
    receipt = AssessmentReceipt(task_id="old-task", revision=entry.revision, bucket="outstanding")
    entry = entry.model_copy(update={"assessment_receipts": [receipt]})
    storage.write_entry(tmp_path / f"{entry.id}.md", entry, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    engine.load()

    updated = engine.edit(
        entry.id,
        {"content": "Changed content."},
        expected_revision=entry.revision,
    )

    assert updated.revision != entry.revision
    assert updated.assessment_receipts == []
    assert MemoryEngine(tmp_path).get_entry(entry.id).assessment_receipts == []


@pytest.mark.parametrize(
    ("operation", "state", "didnt_use_count"),
    [
        ("approve", MemoryState.CURATED, 0),
        ("resolve", MemoryState.STALE, 0),
        ("delete", MemoryState.APPROVED, 0),
        ("stale", MemoryState.APPROVED, 51),
    ],
)
def test_revision_preserving_single_entry_writes_keep_receipts(
    tmp_path: Path,
    operation: str,
    state: MemoryState,
    didnt_use_count: int,
) -> None:
    """State-only writes retain receipts while the editable revision remains unchanged."""
    entry = MemoryEntry(
        **{
            **_valid_entry_data(),
            "state": state,
            "didnt_use_count": didnt_use_count,
        }
    )
    receipt = AssessmentReceipt(task_id="current-task", revision=entry.revision, bucket="outstanding")
    entry = entry.model_copy(update={"assessment_receipts": [receipt]})
    storage.write_entry(tmp_path / f"{entry.id}.md", entry, memory_dir=tmp_path)
    engine = MemoryEngine(tmp_path)
    engine.load()

    if operation == "approve":
        updated = engine.approve(entry.id, expected_revision=entry.revision)
    elif operation == "resolve":
        updated = engine.resolve(entry.id, expected_updated_at=entry.updated_at)
    elif operation == "delete":
        updated = engine.delete(entry.id, expected_revision=entry.revision)
    else:
        updated = engine.try_stale_transition(engine.get_entry(entry.id))

    assert updated.revision == entry.revision
    assert updated.assessment_receipts == [receipt]
    assert MemoryEngine(tmp_path).get_entry(entry.id).assessment_receipts == [receipt]


def test_lifecycle_rollback_failure_preserves_both_errors_and_reloads_cache(tmp_path: Path) -> None:
    """A partial lifecycle recovery reports both failures and reflects disk state."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    unrelated = engine.save(
        title="Unrelated",
        content="Original unrelated",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["other"],
    )
    unrelated_path = tmp_path / f"{unrelated.id}.md"
    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_error = OSError("rollback write failed")
    calls = 0
    written_paths: list[Path] = []

    def failing_write(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        written_paths.append(path)
        if calls == 2:
            raise initial_error
        if calls == 3:
            raise rollback_error
        original_write(path, *args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].error is rollback_error
    assert error.rollback_errors[0].entry_id in str(error)
    assert str(error.rollback_errors[0].path) not in str(error)
    assert error.cache_error is None
    assert unrelated_path not in written_paths
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",), ("new",), ("other",)}
    health = engine.health()
    assert health.healthy is True
    assert health.unreadable_paths == []
    assert health.duplicate_paths == {}


def test_lifecycle_recovery_status_is_uncertain_for_unreadable_affected_record(tmp_path: Path) -> None:
    """An unreadable affected file cannot be classified from a lenient reload."""
    engine = MemoryEngine(tmp_path)
    entry = engine.save(
        title="Original",
        content="Original content",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.get_entries()

    entry_path = tmp_path / f"{entry.id}.md"
    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_error = OSError("rollback write failed")
    calls = 0

    def failing_write(path: Path, *args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise initial_error
        if calls == 2:
            path.write_text("not markdown", encoding="utf-8")
            raise rollback_error
        original_write(path, *args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "uncertain"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].error is rollback_error
    assert error.cache_error is None
    assert "OSError" in str(error)
    assert str(entry_path) not in str(error)
    health = engine.health()
    assert health.healthy is False
    assert health.unreadable_paths == [entry_path.name]


def test_lifecycle_recovery_status_uses_reloaded_originals(tmp_path: Path) -> None:
    """A rollback error does not imply partial disk state when reload finds originals."""
    engine = MemoryEngine(tmp_path)
    for title in ("First", "Second"):
        engine.save(
            title=title,
            content=f"Original {title.lower()}",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="source",
            scope_agents=["old"],
        )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_error = OSError("rollback write failed")
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise initial_error
        if calls == 2:
            raise rollback_error
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "complete"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].error is rollback_error
    assert error.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert engine.health().healthy is True


def test_lifecycle_recovery_status_uses_partial_reload_when_all_rollbacks_fail(tmp_path: Path) -> None:
    """A successful reload identifies partial disk state even when no rollback call succeeds."""
    engine = MemoryEngine(tmp_path)
    for title in ("First", "Second"):
        engine.save(
            title=title,
            content=f"Original {title.lower()}",
            categories=["domain-knowledge"],
            confidence=0.9,
            source_agent="source",
            scope_agents=["old"],
        )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    rollback_errors = (OSError("first rollback failed"), OSError("second rollback failed"))
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        if calls in (3, 4):
            raise rollback_errors[calls - 3]
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert tuple(failure.error for failure in error.rollback_errors) == rollback_errors
    assert error.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",), ("new",)}
    assert engine.health().healthy is True


def test_lifecycle_cache_reload_failure_resets_cache_until_subsequent_reload(tmp_path: Path) -> None:
    """A failed recovery reload clears the cache and permits a later reload from disk."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.get_entries()

    original_write = storage.write_entry
    original_load = engine._load  # noqa: SLF001
    initial_error = OSError("initial write failed")
    reload_error = OSError("cache reload failed")
    calls = 0
    load_calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        original_write(*args, **kwargs)

    def failing_load() -> list[MemoryEntry]:
        nonlocal load_calls
        load_calls += 1
        if load_calls in (1, 2):
            raise reload_error
        return original_load()

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        patch.object(engine, "_load", side_effect=failing_load),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    error = exc_info.value
    assert error.recovery_status == "uncertain"
    assert error.operation_error is initial_error
    assert error.rollback_errors == ()
    assert error.cache_error is reload_error
    assert engine._entries == []  # noqa: SLF001
    assert engine._id_to_path == {}  # noqa: SLF001
    health = engine.health()
    assert health.healthy is True
    assert health.unreadable_paths == []
    assert health.duplicate_paths == {}

    with (
        patch.object(engine, "_load", side_effect=failing_load),
        pytest.raises(
            OSError,
            match="cache reload failed",
        ) as second_reload,
    ):
        engine.get_entries()
    assert second_reload.value is reload_error

    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert load_calls == 2
    assert engine.parse_errors == 0


def test_lifecycle_operation_failure_with_successful_rollback_reraises_original_error(tmp_path: Path) -> None:
    """A fully successful rollback preserves the ordinary operation exception."""
    engine = MemoryEngine(tmp_path)
    engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )

    original_write = storage.write_entry
    initial_error = OSError("initial write failed")
    calls = 0

    def failing_write(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise initial_error
        original_write(*args, **kwargs)

    with (
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.rename_agent("old", "new")

    assert exc_info.value.operation_error is initial_error
    assert exc_info.value.recovery_status == "complete"
    assert exc_info.value.rollback_errors == ()
    assert exc_info.value.cache_error is None
    assert {tuple(entry.scope_agents) for entry in engine.get_entries()} == {("old",)}
    assert engine.health().healthy is True


def test_delete_lifecycle_rollback_failure_restores_only_recoverable_files(tmp_path: Path) -> None:
    """A failed delete rollback reports the missing entry and reloads the remaining files."""
    engine = MemoryEngine(tmp_path)
    first = engine.save(
        title="First",
        content="Original first",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    second = engine.save(
        title="Second",
        content="Original second",
        categories=["domain-knowledge"],
        confidence=0.9,
        source_agent="source",
        scope_agents=["old"],
    )
    engine.get_entries()

    first_path = tmp_path / f"{first.id}.md"
    second_path = tmp_path / f"{second.id}.md"
    original_delete = storage.delete_entry
    original_write = storage.write_entry
    initial_error = OSError("delete failed")
    rollback_error = OSError("rollback write failed")
    delete_calls = 0

    def failing_delete(path: Path, *, memory_dir: Path) -> None:
        nonlocal delete_calls
        delete_calls += 1
        original_delete(path, memory_dir=memory_dir)
        if delete_calls == 2:
            raise initial_error

    def failing_write(path: Path, *args: object, **kwargs: object) -> None:
        if path == second_path:
            raise rollback_error
        original_write(path, *args, **kwargs)

    with (
        patch.object(storage, "delete_entry", side_effect=failing_delete),
        patch.object(storage, "write_entry", side_effect=failing_write),
        pytest.raises(LifecycleRecoveryError) as exc_info,
    ):
        engine.delete_agent("old")

    error = exc_info.value
    assert error.recovery_status == "partial"
    assert error.operation_error is initial_error
    assert len(error.rollback_errors) == 1
    assert error.rollback_errors[0].entry_id == second.id
    assert error.rollback_errors[0].path == second_path
    assert error.rollback_errors[0].error is rollback_error
    assert error.cache_error is None
    assert first_path.is_file()
    assert not second_path.exists()
    assert [entry.id for entry in engine.get_entries()] == [first.id]
    assert "OSError" in str(error)
    assert str(second_path) not in str(error)
    assert engine.health().healthy is True
