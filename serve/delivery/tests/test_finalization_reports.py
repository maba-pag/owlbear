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
