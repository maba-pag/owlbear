from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import (
    AttemptConflictError,
    AttemptDiagnosticCode,
    AttemptEvent,
    AttemptEventDiagnosticCode,
    AttemptStore,
    parse_attempt_event_mapping,
    serialize_attempt_event_mapping,
)


def _event_mapping(kind: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "attempt_id": "attempt-001",
        "claim_id": "claim-001",
        "job_id": 1,
        "change_id": "replace-delivery-pipeline",
        "delivery_digest": "a" * 64,
        "target_node_id": "DN-003",
        "actor_id": "builder",
        "process_id": "process-001",
        "sequence": 1,
        "timestamp": "2026-07-23T12:00:00Z",
        "kind": kind,
        "detail": "completed focused proof",
        "evidence_ids": ["evidence-001"],
    }


def _event(attempt_id: str = "attempt-001", sequence: int = 1) -> AttemptEvent:
    value = _event_mapping("started") | {
        "attempt_id": attempt_id,
        "sequence": sequence,
        "evidence_ids": ("evidence-001",),
    }
    return AttemptEvent.model_validate(value)


@pytest.mark.parametrize("kind", ["started", "released", "failed", "crashed", "succeeded"])
def test_public_attempt_event_parser_round_trips_frozen_records(kind: str) -> None:
    value = _event_mapping(kind)

    result = parse_attempt_event_mapping(value)

    assert result.diagnostics == ()
    assert result.event is not None
    assert serialize_attempt_event_mapping(result.event) == value
    assert parse_attempt_event_mapping(serialize_attempt_event_mapping(result.event)).event == result.event
    with pytest.raises((TypeError, ValueError)):
        result.event.sequence = 2


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("unexpected", True, AttemptEventDiagnosticCode.UNKNOWN_FIELD),
        ("attempt_id", "", AttemptEventDiagnosticCode.IDENTITY_INVALID),
        ("claim_id", "", AttemptEventDiagnosticCode.IDENTITY_INVALID),
        ("job_id", 0, AttemptEventDiagnosticCode.REFERENCE_INVALID),
        ("delivery_digest", "bad", AttemptEventDiagnosticCode.REFERENCE_INVALID),
        ("sequence", 0, AttemptEventDiagnosticCode.SEQUENCE_INVALID),
        ("kind", "complete", AttemptEventDiagnosticCode.KIND_INVALID),
        ("target_node_id", None, AttemptEventDiagnosticCode.REFERENCE_INVALID),
    ],
)
def test_public_attempt_event_parser_returns_stable_diagnostics(
    field: str, value: object, expected: AttemptEventDiagnosticCode
) -> None:
    event = _event_mapping("started")
    event[field] = value

    result = parse_attempt_event_mapping(event)

    assert result.event is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [expected]


def test_public_attempt_event_parser_reports_missing_required_reference() -> None:
    event = _event_mapping("started")
    del event["target_node_id"]

    result = parse_attempt_event_mapping(event)

    assert result.event is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        AttemptEventDiagnosticCode.REQUIRED_REFERENCE_MISSING
    ]


def test_public_attempt_event_parser_rejects_missing_claim_identity() -> None:
    event = _event_mapping("started")
    del event["claim_id"]

    result = parse_attempt_event_mapping(event)

    assert result.event is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [AttemptEventDiagnosticCode.IDENTITY_INVALID]


def test_attempt_store_replays_immutable_events_and_lists_by_identity(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path)
    later = _event("attempt-002", 2)
    first = _event("attempt-001", 1)
    second = _event("attempt-001", 2)

    assert store.create(later).event == later
    assert store.create(second).event == second
    assert store.create(first).event == first
    assert store.create(first).event == first
    assert store.read("attempt-001", 2).event == second
    assert store.list() == (first, second, later)


def test_attempt_store_rejects_conflicts_and_unsafe_paths(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path)
    original = _event()
    conflicting = original.model_copy(update={"kind": "failed"})

    assert store.create(original).event == original
    with pytest.raises(AttemptConflictError) as error:
        store.create(conflicting)
    assert error.value.code == "ERR_ATTEMPT_CONFLICT"
    assert store.read("attempt-001", 1).event == original
    assert store.read("../outside", 1).diagnostics[0].code == AttemptDiagnosticCode.PATH_UNSAFE


def test_attempt_store_rejects_symlink_substitution(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "attempts").symlink_to(outside, target_is_directory=True)

    result = store.create(_event())

    assert result.event is None
    assert result.diagnostics[0].code == AttemptDiagnosticCode.PATH_UNSAFE
    assert list(outside.iterdir()) == []


def test_attempt_store_removes_partial_event_after_write_failure(tmp_path: Path) -> None:
    store = AttemptStore(tmp_path)
    event = _event()

    with patch("owlbear_kanban.attempts.os.fsync", side_effect=OSError("disk failure")):
        result = store.create(event)

    assert result.event is None
    assert result.diagnostics[0].code == AttemptDiagnosticCode.WRITE_FAILED
    assert not (tmp_path / "attempts" / event.attempt_id / f"{event.sequence}.json").exists()
    assert all(not path.name.startswith(".tmp-") for path in (tmp_path / "attempts" / event.attempt_id).iterdir())
