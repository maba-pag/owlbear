from __future__ import annotations

import pytest

from owlbear_kanban import AttemptEventDiagnosticCode, parse_attempt_event_mapping


def _event_mapping(kind: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "attempt_id": "attempt-001",
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


@pytest.mark.parametrize("kind", ["started", "released", "failed", "crashed", "succeeded"])
def test_public_attempt_event_parser_round_trips_frozen_records(kind: str) -> None:
    value = _event_mapping(kind)

    result = parse_attempt_event_mapping(value)

    assert result.diagnostics == ()
    assert result.event is not None
    assert result.event.model_dump(mode="json") == value
    assert parse_attempt_event_mapping(result.event.model_dump(mode="json")).event == result.event
    with pytest.raises((TypeError, ValueError)):
        result.event.sequence = 2


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("unexpected", True, AttemptEventDiagnosticCode.UNKNOWN_FIELD),
        ("attempt_id", "", AttemptEventDiagnosticCode.IDENTITY_INVALID),
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
