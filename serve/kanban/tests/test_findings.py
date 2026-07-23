from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import (
    FindingConflictError,
    FindingDiagnosticCode,
    FindingStore,
    ReceiptDiagnosticCode,
    ReceiptStore,
    parse_finding_mapping,
)
import owlbear_kanban.finding as finding_module

from .test_change_receipts import _load_revision, _receipt


def _finding(finding_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "finding_id": finding_id,
        "source_attempt_id": "attempt-001",
        "source_job_id": 1,
        "change_id": "replace-delivery-pipeline",
        "delivery_digest": "a" * 64,
        "target_kind": "requirement",
        "target_id": "REQ-008",
        "finding_class": "implementation-defect",
        "detail": "contract was not preserved",
        "created_at": "2026-07-23T00:00:00Z",
    }


def test_public_finding_parser_and_store_preserve_immutable_contained_records(tmp_path: Path) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = FindingStore(work_root)
    value = _finding("finding-002")

    parsed = parse_finding_mapping(value)
    created = store.create("finding-002", value)
    replayed = store.create("finding-002", value)
    second = store.create("finding-001", _finding("finding-001"))

    assert parsed.finding is not None
    assert created.finding is not None
    assert replayed == created
    assert second.finding is not None
    assert [result.finding.finding_id for result in store.list() if result.finding] == ["finding-001", "finding-002"]
    with pytest.raises(FindingConflictError) as exc_info:
        store.create("finding-002", {**value, "detail": "different"})
    assert exc_info.value.code == "ERR_FINDING_CONFLICT"
    assert store.read("../escape").diagnostics[0].code == FindingDiagnosticCode.PATH_UNSAFE


def test_finding_parser_reports_public_contract_errors() -> None:
    unknown = parse_finding_mapping({**_finding("finding-001"), "unexpected": True})
    invalid_target = parse_finding_mapping({**_finding("finding-001"), "target_kind": "task"})
    invalid_class = parse_finding_mapping({**_finding("finding-001"), "finding_class": "bug"})

    assert [item.code for item in unknown.diagnostics] == [FindingDiagnosticCode.UNKNOWN_FIELD]
    assert [item.code for item in invalid_target.diagnostics] == [FindingDiagnosticCode.TARGET_INVALID]
    assert [item.code for item in invalid_class.diagnostics] == [FindingDiagnosticCode.CLASS_INVALID]


def test_finding_store_rejects_symlink_substitution_and_cleans_failed_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work_root = tmp_path / "work"
    work_root.mkdir()
    store = FindingStore(work_root)
    findings_dir = work_root / "findings"
    findings_dir.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("outside\n", encoding="utf-8")
    try:
        (findings_dir / "finding-001.yaml").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")

    linked = store.create("finding-001", _finding("finding-001"))

    assert [item.code for item in linked.diagnostics] == [FindingDiagnosticCode.PATH_UNSAFE]
    assert outside.read_text(encoding="utf-8") == "outside\n"
    (findings_dir / "finding-001.yaml").unlink()
    monkeypatch.setattr(finding_module.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError("write failed")))

    failed = store.create("finding-001", _finding("finding-001"))

    assert failed.diagnostics
    assert not (findings_dir / "finding-001.yaml").exists()
    assert list(findings_dir.glob(".tmp-*")) == []


def test_receipt_store_lists_canonical_receipts_without_touching_work_root(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    assert store.create("build-002", _receipt(revision, "build-002", "build")).receipt is not None
    assert store.create("audit-001", _receipt(revision, "audit-001", "audit")).receipt is not None
    (revision.source_dir / "receipts" / "bad-003.yaml").write_text("[unclosed", encoding="utf-8")

    listed = store.list()

    assert [item.receipt.receipt_id for item in listed if item.receipt] == ["audit-001", "build-002"]
    assert [item.diagnostics[0].code for item in listed if item.diagnostics] == [ReceiptDiagnosticCode.YAML_PARSE]
    assert not (tmp_path / "work" / "receipts").exists()
