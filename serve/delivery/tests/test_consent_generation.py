"""Single-use consent generations: exclusive create, one CAS answer, replay of the recorded disposition."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from owlbear_delivery.consent_generation import (
    ConsentGenerationStore,
    DeliveryConsentDisposition,
    consent_binding_digest,
)
from owlbear_delivery.runtime_transaction import TransactionConflictError

AT = datetime(2026, 10, 4, 12, tzinfo=UTC)
BINDING = consent_binding_digest({"request_id": "REQ-1", "expected_frontier_digest": "a" * 64})


def _store(tmp_path: Path) -> ConsentGenerationStore:
    root = tmp_path / "runtime"
    (root / "changes" / "consent-change").mkdir(parents=True)
    return ConsentGenerationStore(root, "consent-change")


def test_generations_are_created_before_asking_with_a_per_change_sequence(tmp_path: Path) -> None:
    store = _store(tmp_path)

    first, _ = store.create(use="waive", subject_id="REQ-1", binding_digest=BINDING, created_at=AT)
    second, _ = store.create(use="confirm-check", subject_id="REQ-2", binding_digest=BINDING, created_at=AT)

    assert (first.sequence, second.sequence) == (1, 2)
    assert first.generation_id != second.generation_id
    assert first.state == "open"
    assert store.latest("waive", "REQ-1") == store.read(1)
    assert store.latest("waive", "REQ-2") is None
    assert (tmp_path / "runtime/changes/consent-change/consent-generations/00000001.json").is_file()


def test_first_answer_consumes_the_generation_and_a_competing_answer_conflicts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    generation, content = store.create(use="waive", subject_id="REQ-1", binding_digest=BINDING, created_at=AT)

    store.record_answer(generation, content, DeliveryConsentDisposition(outcome="declined"))

    answered, _ = store.read(1)
    assert answered.state == "answered"
    assert answered.disposition == DeliveryConsentDisposition(outcome="declined")
    with pytest.raises(TransactionConflictError):
        store.record_answer(
            generation,
            content,
            DeliveryConsentDisposition(outcome="accepted", confirmation_id="b" * 64, record_id="REQ-1"),
        )
    assert store.read(1)[0].disposition == DeliveryConsentDisposition(outcome="declined")
    with pytest.raises(ValueError, match="already answered"):
        answered.answered(DeliveryConsentDisposition(outcome="cancelled"))


def test_a_later_generation_supersedes_an_answered_one_for_its_subject(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first, content = store.create(use="waive", subject_id="REQ-1", binding_digest=BINDING, created_at=AT)
    store.record_answer(first, content, DeliveryConsentDisposition(outcome="cancelled"))

    second, _ = store.create(use="waive", subject_id="REQ-1", binding_digest=BINDING, created_at=AT)

    latest = store.latest("waive", "REQ-1")
    assert latest is not None
    assert latest[0].generation_id == second.generation_id
    assert store.read(1)[0].disposition == DeliveryConsentDisposition(outcome="cancelled")


@pytest.mark.parametrize(
    "values",
    [
        {"outcome": "accepted"},
        {"outcome": "declined", "confirmation_id": "b" * 64},
        {"outcome": "refused"},
        {"outcome": "declined", "code": "frontier-changed"},
    ],
)
def test_dispositions_are_typed(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DeliveryConsentDisposition(**values)


def test_tampered_or_foreign_generation_records_are_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create(use="waive", subject_id="REQ-1", binding_digest=BINDING, created_at=AT)
    path = tmp_path / "runtime/changes/consent-change/consent-generations/00000001.json"
    original = path.read_bytes()
    path.write_bytes(original.replace(b'"open"', b'"answered"'))

    with pytest.raises(ValueError, match="disposition"):
        store.read(1)

    foreign = ConsentGenerationStore(tmp_path / "runtime", "other-change")
    (tmp_path / "runtime/changes/other-change/consent-generations").mkdir(parents=True)
    (tmp_path / "runtime/changes/other-change/consent-generations/00000001.json").write_bytes(original)
    with pytest.raises(ValueError, match="record is invalid"):
        foreign.read(1)
