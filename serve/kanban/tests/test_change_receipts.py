from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

import owlbear_kanban
from owlbear_kanban import (
    ChangeRevision,
    ReceiptConflictError,
    ReceiptDiagnosticCode,
    ReceiptStore,
    change_health,
    load_change,
)

from .test_change_revision import _documents, _write_package

_RECEIPT_KINDS = ("admission", "shape", "build", "accept", "audit", "supersession")


def _load_revision(tmp_path: Path, change_id: str = "receipt-change") -> tuple[Path, ChangeRevision]:
    changes_dir = tmp_path / "changes"
    _write_package(changes_dir, change_id)
    result = load_change(changes_dir, change_id)
    assert result.revision is not None
    return changes_dir, result.revision


def _receipt(revision: ChangeRevision, receipt_id: str, kind: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": kind,
        "receipt_id": receipt_id,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "issued_at": "2026-07-22T00:00:00Z",
        "status": "valid",
        "tested_baseline": {"revision": "a" * 40, "commands": ["focused proof"]},
        "evidence": {"kind": kind, "passed": True},
    }


def test_package_exports_receipt_and_health_boundary() -> None:
    expected = {
        "ChangeHealthFinding",
        "ChangeHealthResult",
        "ReceiptConflictError",
        "ReceiptDiagnostic",
        "ReceiptDiagnosticCode",
        "ReceiptRecord",
        "ReceiptResult",
        "ReceiptStore",
        "change_health",
    }

    assert expected <= set(owlbear_kanban.__all__)
    assert all(hasattr(owlbear_kanban, name) for name in expected)


def test_receipt_store_round_trips_all_kinds_and_preserves_existing_bytes(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)

    for index, kind in enumerate(_RECEIPT_KINDS, start=1):
        receipt_id = f"{kind}-{index:03d}"
        value = _receipt(revision, receipt_id, kind)

        created = store.create(receipt_id, value)
        read_back = store.read(receipt_id)

        assert created.diagnostics == ()
        assert created.receipt is not None
        assert read_back.receipt is not None
        assert read_back.receipt.to_mapping() == value
        assert read_back.receipt.payload["evidence"] == {"kind": kind, "passed": True}

    first_id = "admission-001"
    first_path = revision.source_dir / "receipts" / f"{first_id}.yaml"
    original = first_path.read_bytes()
    with pytest.raises(ReceiptConflictError) as exc_info:
        store.create(first_id, _receipt(revision, first_id, "admission"))

    assert exc_info.value.code == "ERR_RECEIPT_CONFLICT"
    assert first_path.read_bytes() == original
    assert list(first_path.parent.glob(".tmp-*")) == []


@pytest.mark.parametrize("receipt_id", ["/absolute", "../escape", "nested/path", "bad\\path", "bad\x00id"])
def test_receipt_store_rejects_unsafe_ids_without_filesystem_mutation(tmp_path: Path, receipt_id: str) -> None:
    _changes_dir, revision = _load_revision(tmp_path)

    result = ReceiptStore(revision).create(receipt_id, {})

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert result.diagnostics[0].path is None
    assert result.diagnostics[0].target is None
    assert not (revision.source_dir / "receipts").exists()


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda value: value.update(schema_version=2), ReceiptDiagnosticCode.SCHEMA_INVALID),
        (lambda value: value.update(kind="deploy"), ReceiptDiagnosticCode.SCHEMA_INVALID),
        (lambda value: value.update(receipt_id="different-001"), ReceiptDiagnosticCode.ID_MISMATCH),
    ],
)
def test_receipt_store_rejects_invalid_envelopes_without_residue(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    expected_code: ReceiptDiagnosticCode,
) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    receipt_id = "build-001"
    value = _receipt(revision, receipt_id, "build")
    mutation(value)

    result = ReceiptStore(revision).create(receipt_id, value)

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [expected_code]
    receipts_dir = revision.source_dir / "receipts"
    assert not (receipts_dir / f"{receipt_id}.yaml").exists()
    assert list(receipts_dir.glob(".tmp-*")) == [] if receipts_dir.exists() else True


def test_receipt_store_rejects_malformed_and_symlinked_receipt_files(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    receipts_dir = revision.source_dir / "receipts"
    receipts_dir.mkdir()
    malformed = receipts_dir / "build-001.yaml"
    malformed.write_text("[unclosed", encoding="utf-8")

    malformed_result = ReceiptStore(revision).read("build-001")

    assert [item.code for item in malformed_result.diagnostics] == [ReceiptDiagnosticCode.YAML_PARSE]
    assert malformed_result.diagnostics[0].path == "receipts/build-001.yaml"

    target = tmp_path / "outside.yaml"
    target.write_text("outside\n", encoding="utf-8")
    linked = receipts_dir / "audit-001.yaml"
    try:
        linked.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")

    linked_result = ReceiptStore(revision).read("audit-001")

    assert [item.code for item in linked_result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert target.read_text(encoding="utf-8") == "outside\n"


def _admitted_package(tmp_path: Path) -> tuple[Path, Path, ChangeRevision]:
    change_id = "health-change"
    changes_dir = tmp_path / "changes"
    decisions, graph = _documents(change_id)
    change_dir = _write_package(changes_dir, change_id, authority=(decisions, graph))
    initial = load_change(changes_dir, change_id)
    assert initial.revision is not None
    receipt_id = "admission-health-001"
    graph["state"] = "admitted"
    graph["admission"] = {
        "state": "admitted",
        "delivery_digest": initial.revision.delivery_digest,
        "receipt": f"receipts/{receipt_id}.yaml",
        "limits": [],
    }
    (change_dir / "graph.yaml").write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    loaded = load_change(changes_dir, change_id)
    assert loaded.revision is not None
    created = ReceiptStore(loaded.revision).create(
        receipt_id,
        _receipt(loaded.revision, receipt_id, "admission"),
    )
    assert created.receipt is not None
    return changes_dir, change_dir, loaded.revision


def _snapshot(paths: list[Path]) -> dict[Path, tuple[bytes, int]]:
    return {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}


def test_change_health_accepts_matching_admission_without_mutation(tmp_path: Path) -> None:
    changes_dir, change_dir, _revision = _admitted_package(tmp_path)
    paths = sorted(path for path in change_dir.rglob("*") if path.is_file())
    before = _snapshot(paths)

    result = change_health(changes_dir, "health-change")

    assert result.findings == ()
    assert result.checked_paths == (
        "intent.md",
        "design.md",
        "decisions.yaml",
        "graph.yaml",
        "receipts/admission-health-001.yaml",
    )
    assert _snapshot(paths) == before


def test_change_health_reports_digest_mismatch_deterministically_without_mutation(tmp_path: Path) -> None:
    changes_dir, change_dir, _revision = _admitted_package(tmp_path)
    receipt_path = change_dir / "receipts" / "admission-health-001.yaml"
    value = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
    value["delivery_digest"] = "0" * 64
    receipt_path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    paths = sorted(path for path in change_dir.rglob("*") if path.is_file())
    before = _snapshot(paths)

    first = change_health(changes_dir, "health-change")
    second = change_health(changes_dir, "health-change")

    assert first == second
    assert [(item.code, item.path, item.target) for item in first.findings] == [
        (
            ReceiptDiagnosticCode.REVISION_MISMATCH.value,
            "receipts/admission-health-001.yaml",
            "admission-health-001",
        )
    ]
    assert _snapshot(paths) == before


@pytest.mark.parametrize(
    ("defect", "expected_code", "expected_path"),
    [
        (lambda change_dir: (change_dir / "design.md").unlink(), "ERR_CHANGE_FILE_MISSING", "design.md"),
        (
            lambda change_dir: (change_dir / "graph.yaml").write_text("[unclosed", encoding="utf-8"),
            "ERR_CHANGE_YAML_PARSE",
            "graph.yaml",
        ),
        (
            lambda change_dir: (change_dir / "receipts").write_text("not a directory\n", encoding="utf-8"),
            ReceiptDiagnosticCode.PATH_UNSAFE.value,
            "receipts",
        ),
    ],
)
def test_change_health_reports_authority_defects_without_mutation(
    tmp_path: Path,
    defect: Callable[[Path], object],
    expected_code: str,
    expected_path: str,
) -> None:
    changes_dir = tmp_path / "changes"
    change_dir = _write_package(changes_dir, "defective-health")
    defect(change_dir)
    paths = sorted(path for path in change_dir.rglob("*") if path.is_file())
    before = _snapshot(paths)

    result = change_health(changes_dir, "defective-health")

    assert [(item.code, item.path) for item in result.findings] == [(expected_code, expected_path)]
    assert result.checked_paths == ("intent.md", "design.md", "decisions.yaml", "graph.yaml")
    assert _snapshot(paths) == before
