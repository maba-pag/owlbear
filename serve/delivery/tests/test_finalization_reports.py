from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizationReportError,
    FinalizationReportStore,
    MaintainedProofProcedure,
    ProofAttemptBasis,
    ProofAttemptObservation,
    ProofAttemptStore,
    ReportFinalizationFailure,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction

_LEGACY_REPORT_JSON = (
    b'{"check_id":null,"exit_status":null,"observed_at":"2026-08-02T00:00:00Z","producer":"finalization-diagnostic",'
    b'"report_id":"f3da20d3c7ab272ca417f31828759d5b3e1f0d1ac627c3e74cb48273087dc86a",'
    b'"request":{"attempt_key":"legacy-report","category":"maintained-check","change_id":"change-a","check_id":null,'
    b'"checks_state":"failed","code":"maintained-check-failed","exit_status":null,'
    b'"expected_change_head":"cccccccccccccccccccccccccccccccccccccccc",'
    b'"expected_contract_digest":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"expected_diagnostic_sequence":0,'
    b'"expected_frontier_digest":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
    b'"expected_reviewed_head":"cccccccccccccccccccccccccccccccccccccccc","expected_workspace_fingerprint":null,'
    b'"paths":[]},"sequence":1,"summary":"A maintained verification check failed."}\n'
)
_LEGACY_REPORT_POINTER_JSON = (
    b'{"report_id":"f3da20d3c7ab272ca417f31828759d5b3e1f0d1ac627c3e74cb48273087dc86a","sequence":1}\n'
)


def _request(**updates):
    return ReportFinalizationFailure(
        **{
            "change_id": "change-a",
            "expected_contract_digest": "a" * 64,
            "expected_frontier_digest": "b" * 64,
            "expected_change_head": "c" * 40,
            "expected_reviewed_head": "c" * 40,
            "expected_diagnostic_sequence": 0,
            "attempt_key": "first",
            "category": "maintained-check",
            "code": FinalizationFailureCode.MAINTAINED_CHECK_FAILED,
            "checks_state": "failed",
            **updates,
        }
    )


def test_legacy_report_fixture_reads_replays_and_rejects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "finalization-reports" / "change-a"
    reports = root / "reports"
    reports.mkdir(parents=True)
    report_id = "f3da20d3c7ab272ca417f31828759d5b3e1f0d1ac627c3e74cb48273087dc86a"
    (reports / f"{report_id}.json").write_bytes(_LEGACY_REPORT_JSON)
    (root / "current.json").write_bytes(_LEGACY_REPORT_POINTER_JSON)

    store = FinalizationReportStore(tmp_path, "change-a")
    report = store.read().reports[0]
    assert report.report_id == report_id
    assert store.record(
        _request(attempt_key="legacy-report"),
        datetime.now(UTC),
        lambda: pytest.fail("legacy replay must not validate a new basis"),
    ) == report

    tampered = _LEGACY_REPORT_JSON.replace(b'"checks_state":"failed"', b'"checks_state":"unknown"')
    (reports / f"{report_id}.json").write_bytes(tampered)
    with pytest.raises(FinalizationReportError, match="report-store-unavailable"):
        FinalizationReportStore(tmp_path, "change-a").read()


def test_report_replay_restart_and_matching_pointer_retirement(tmp_path: Path) -> None:
    store = FinalizationReportStore(tmp_path, "change-a")
    assert store.read().reports == ()
    assert not (tmp_path / "finalization-reports").exists()
    first = store.record(_request(), datetime.now(UTC), lambda: None)
    second = store.record(
        _request(attempt_key="second", expected_diagnostic_sequence=1), datetime.now(UTC), lambda: None
    )
    restarted = FinalizationReportStore(tmp_path, "change-a")
    assert (
        restarted.record(_request(), datetime.now(UTC), lambda: pytest.fail("replay must not validate a newer basis"))
        == first
    )
    assert restarted.read().current_report_id == second.report_id
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        restarted.record(_request(checks_state="unknown"), datetime.now(UTC), lambda: None)
    restarted.retire("d" * 40, "a" * 64)
    assert restarted.read().current_report_id == second.report_id
    restarted.retire("c" * 40, "a" * 64)
    assert restarted.read().current_report_id is None
    assert restarted.read().reports == (first, second)


@pytest.mark.parametrize(
    "relative", ["finalization-reports", "finalization-reports/change-a", "finalization-reports/change-a/reports"]
)
def test_report_store_rejects_symlink_components(tmp_path: Path, relative: str) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"unchanged")
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(outside, target_is_directory=True)
    with pytest.raises(FinalizationReportError, match="report-store-unavailable"):
        FinalizationReportStore(tmp_path, "change-a").record(_request(), datetime.now(UTC), lambda: None)
    assert tuple(outside.iterdir()) == (sentinel,)
    assert sentinel.read_bytes() == b"unchanged"


def test_capacity_keeps_original_replay_and_rejects_new_attempt(tmp_path: Path) -> None:
    store = FinalizationReportStore(tmp_path, "change-a")
    first = store.record(_request(), datetime.now(UTC), lambda: None)
    for sequence in range(1, 256):
        store.record(
            _request(attempt_key=f"attempt-{sequence}", expected_diagnostic_sequence=sequence),
            datetime.now(UTC),
            lambda: None,
        )
    with pytest.raises(FinalizationReportError, match="diagnostic-capacity"):
        store.record(
            _request(attempt_key="overflow", expected_diagnostic_sequence=256), datetime.now(UTC), lambda: None
        )
    assert store.record(_request(), datetime.now(UTC), lambda: pytest.fail("replay checked basis")) == first
    assert len(store.read().reports) == 256


@pytest.mark.parametrize(
    "field", ["summary", "command", "url", "logs", "environment", "observer", "observations", "review"]
)
def test_report_input_rejects_undeclared_payloads(field: str) -> None:
    with pytest.raises(ValidationError):
        _request(**{field: "untrusted"})


@pytest.mark.parametrize(
    "updates",
    [
        {"attempt_key": "x" * 129},
        {"attempt_key": "not ascii \u00e9"},
        {"checks_state": "passed"},
        {"paths": tuple(f"file-{index}" for index in range(33))},
        {"paths": ("../outside",)},
        {"paths": ("/outside",)},
        {"paths": ("nested/../outside",)},
    ],
)
def test_report_input_rejects_invalid_structural_bounds(updates: dict) -> None:
    with pytest.raises(ValidationError):
        _request(
            category="custody-preflight",
            code=FinalizationFailureCode.WORKSPACE_DIRTY,
            expected_workspace_fingerprint="a" * 64,
            **updates,
        )


def test_wrong_sequence_and_empty_pointer_fail_without_repair(tmp_path: Path) -> None:
    store = FinalizationReportStore(tmp_path, "change-a")
    with pytest.raises(FinalizationReportError, match="diagnostic-conflict"):
        store.record(_request(expected_diagnostic_sequence=1), datetime.now(UTC), lambda: pytest.fail("stale sequence"))
    pointer = tmp_path / "finalization-reports/change-a/current.json"
    pointer.write_bytes(b"")
    with pytest.raises(FinalizationReportError, match="report-store-unavailable"):
        store.read()
    assert pointer.read_bytes() == b""


def test_encoded_capacity_is_checked_before_persistence(tmp_path: Path) -> None:
    request = _request(
        category="custody-preflight",
        code=FinalizationFailureCode.WORKSPACE_DIRTY,
        expected_workspace_fingerprint="a" * 64,
        paths=tuple(f"{index}" + "\u00e9" * 230 for index in range(32)),
    )
    with pytest.raises(FinalizationReportError, match="report-store-unavailable"):
        FinalizationReportStore(tmp_path, "change-a").record(request, datetime.now(UTC), lambda: None)
    assert not (tmp_path / "finalization-reports/change-a/current.json").exists()
    assert not (tmp_path / "finalization-reports/change-a/reports").exists()


def test_interrupted_report_recovers_and_corruption_preserves_bytes(tmp_path: Path) -> None:
    store = FinalizationReportStore(tmp_path, "change-a")
    original = RuntimeTransaction.commit_contained

    def interrupted(transaction, descriptor):
        def fail(stage):
            if stage == "after-first-publication":
                msg = "injected storage failure"
                raise OSError(msg)

        original(transaction, descriptor, failure=fail)

    with patch.object(RuntimeTransaction, "commit_contained", interrupted), pytest.raises(FinalizationReportError):
        store.record(_request(), datetime.now(UTC), lambda: None)
    restarted = FinalizationReportStore(tmp_path, "change-a")
    snapshot = restarted.read()
    assert len(snapshot.reports) == 1
    assert snapshot.current_report_id == snapshot.reports[0].report_id
    path = tmp_path / "finalization-reports/change-a/reports" / f"{snapshot.current_report_id}.json"
    path.write_bytes(b"corrupt report")
    with pytest.raises(FinalizationReportError, match="report-store-unavailable"):
        restarted.read()
    assert path.read_bytes() == b"corrupt report"


def _proof_procedure() -> MaintainedProofProcedure:
    return MaintainedProofProcedure(procedure_id="maintained-check", registration_digest="e" * 64)


def _proof_observation(**updates) -> ProofAttemptObservation:
    values = {
        "proof_fingerprint_before": "a" * 64,
        "proof_fingerprint_after": "b" * 64,
        "paths": ("generated.txt",),
        "observed_at": datetime.now(UTC),
    }
    values.update(updates)
    return ProofAttemptObservation(
        **values,
    )


def _proof_basis() -> ProofAttemptBasis:
    return ProofAttemptBasis(
        expected_contract_digest="c" * 64,
        expected_frontier_digest="d" * 64,
        expected_change_head="e" * 40,
        expected_reviewed_head="f" * 40,
    )


def test_proof_attempt_store_binds_registered_owner_observation_and_replays(tmp_path: Path) -> None:
    procedure = _proof_procedure()
    other = MaintainedProofProcedure(procedure_id="other", registration_digest="f" * 64)
    store = ProofAttemptStore(tmp_path, "change-a", (procedure, other))
    calls = 0

    def observe() -> ProofAttemptObservation:
        nonlocal calls
        calls += 1
        return _proof_observation()

    first = store.record("attempt-1", procedure, _proof_basis(), observe)
    assert calls == 1
    assert first.procedure_id == procedure.procedure_id
    assert first.registration_digest == procedure.registration_digest
    assert first.proof_fingerprint_before != first.proof_fingerprint_after
    assert store.record("attempt-1", procedure, _proof_basis(), lambda: pytest.fail("replay must not observe")) == first
    with pytest.raises(FinalizationReportError, match="proof-attempt-conflict"):
        store.record(
            "attempt-1",
            procedure,
            _proof_basis().model_copy(update={"expected_change_head": "1" * 40}),
            lambda: pytest.fail("conflicting replay must not observe"),
        )
    with pytest.raises(FinalizationReportError, match="proof-attempt-conflict"):
        store.record(
            "attempt-1",
            other,
            _proof_basis(),
            _proof_observation,
        )
    restarted = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    assert restarted.read() == (first,)


def test_proof_attempt_store_rejects_unregistered_or_tampered_records(tmp_path: Path) -> None:
    procedure = _proof_procedure()
    store = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    attempt = store.record("attempt-1", procedure, _proof_basis(), _proof_observation)
    path = tmp_path / "proof-attempts/change-a/attempts" / f"{attempt.attempt_id}.json"
    tampered = path.read_bytes().replace(b'"registration_digest":"' + b"e" * 64, b'"registration_digest":"' + b"f" * 64)
    path.write_bytes(tampered)
    with pytest.raises(FinalizationReportError, match="proof-attempt-store-unavailable"):
        ProofAttemptStore(tmp_path, "change-a", (procedure,)).read()

    with pytest.raises(FinalizationReportError, match="not maintained"):
        store.record(
            "attempt-2",
            MaintainedProofProcedure(procedure_id="unregistered", registration_digest="f" * 64),
            _proof_basis(),
            _proof_observation,
        )


def test_proof_attempt_store_preserves_history_across_registration_rotation(tmp_path: Path) -> None:
    original = _proof_procedure()
    original_store = ProofAttemptStore(tmp_path, "change-a", (original,))
    first = original_store.record("attempt-1", original, _proof_basis(), _proof_observation)
    first_bytes = (tmp_path / "proof-attempts/change-a/attempts" / f"{first.attempt_id}.json").read_bytes()

    rotated = MaintainedProofProcedure(procedure_id=original.procedure_id, registration_digest="f" * 64)
    rotated_store = ProofAttemptStore(tmp_path, "change-a", (rotated,))
    assert rotated_store.read() == (first,)
    assert not rotated_store.is_current(first)
    second = rotated_store.record("attempt-2", rotated, _proof_basis(), _proof_observation)
    assert rotated_store.read() == (first, second)
    assert rotated_store.is_current(second)
    assert (tmp_path / "proof-attempts/change-a/attempts" / f"{first.attempt_id}.json").read_bytes() == first_bytes


@pytest.mark.parametrize("stage", ["after-first-publication", "before-manifest-cleanup"])
def test_proof_attempt_store_recovers_interrupted_publication_and_replays(tmp_path: Path, stage: str) -> None:
    procedure = _proof_procedure()
    basis = _proof_basis()
    store = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    calls = 0
    original = RuntimeTransaction.commit_contained

    def read_observation() -> ProofAttemptObservation:
        nonlocal calls
        calls += 1
        return _proof_observation()

    def interrupted(transaction, descriptor):
        def fail(point):
            if point == stage:
                message = "injected proof-attempt interruption"
                raise OSError(message)

        original(transaction, descriptor, failure=fail)

    with (
        patch.object(RuntimeTransaction, "commit_contained", interrupted),
        pytest.raises(FinalizationReportError, match="proof-attempt-store-unavailable"),
    ):
        store.record("attempt-1", procedure, basis, read_observation)
    assert calls == 1

    restarted = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    history = restarted.read()
    assert len(history) == 1
    record_path = tmp_path / "proof-attempts/change-a/attempts" / f"{history[0].attempt_id}.json"
    record_bytes = record_path.read_bytes()
    assert restarted.record("attempt-1", procedure, basis, lambda: pytest.fail("replay must not observe")) == history[0]
    assert calls == 1
    assert record_path.read_bytes() == record_bytes


def test_proof_attempt_store_rejects_encoded_overcapacity_before_persistence(tmp_path: Path) -> None:
    procedure = _proof_procedure()
    store = ProofAttemptStore(tmp_path, "change-a", (procedure,))
    exact_path = "é" * 240
    store.record(
        "at-capacity-by-path",
        procedure,
        _proof_basis(),
        lambda: _proof_observation(paths=(exact_path,)),
    )
    oversized_paths = tuple(f"{index}-" + ("é" * 237) for index in range(32))
    with pytest.raises(FinalizationReportError, match="proof-attempt-store-unavailable"):
        store.record(
            "over-encoded-capacity",
            procedure,
            _proof_basis(),
            lambda: _proof_observation(paths=oversized_paths),
        )
    attempts = tuple((tmp_path / "proof-attempts/change-a/attempts").glob("*.json"))
    assert len(attempts) == 1
