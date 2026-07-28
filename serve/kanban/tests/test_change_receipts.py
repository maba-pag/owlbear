from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

import owlbear_kanban
import owlbear_kanban.receipt as receipt_module
from owlbear_kanban import (
    ChangeRevision,
    GitRepositoryHistory,
    ImpactClosureError,
    ReceiptConflictError,
    ReceiptDiagnosticCode,
    ReceiptParseDiagnosticCode,
    ReceiptStore,
    ReceiptValidityCode,
    change_health,
    compute_node_plan_digest,
    discover_admission,
    evaluate_receipt_currentness,
    evaluate_code_revision_currency,
    load_change,
    parse_receipt_mapping,
    parse_impact_closure,
    parse_repository_path,
)

from .test_change_revision import _documents, _write_modular_package

_RECEIPT_KINDS = ("admission", "plan", "build", "accept", "audit", "supersession")


def _load_revision(tmp_path: Path, change_id: str = "receipt-change") -> tuple[Path, ChangeRevision]:
    changes_dir = tmp_path / "changes"
    _write_modular_package(changes_dir, change_id)
    result = load_change(changes_dir, change_id)
    assert result.revision is not None
    return changes_dir, result.revision


def _receipt(revision: ChangeRevision, receipt_id: str, kind: str) -> dict[str, object]:
    value: dict[str, object] = {
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
    if kind != "admission":
        value["impact_closure"] = {"paths": ["src/"], "authority_targets": ["REQ-001"]}
    return value


def _parser_receipt(kind: str) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": 1,
        "kind": kind,
        "receipt_id": f"{kind}-001",
        "change_id": "receipt-change",
        "delivery_digest": "a" * 64,
        "issued_at": "2026-07-22T00:00:00Z",
        "target_node_id": "DN-001",
        "node_plan_digest": "b" * 64,
        "predecessor_receipt_ids": ["predecessor-001"],
        "evidence": {"passed": True},
        "code_revision": "c" * 40,
    }
    if kind != "admission":
        value["impact_closure"] = {"paths": ["src/"], "authority_targets": ["REQ-001"]}
    return value


def _current_receipt(revision: ChangeRevision) -> dict[str, object]:
    node = revision.graph.nodes[0]
    proof = revision.resolve(node.proof)
    return {
        **_parser_receipt("build"),
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_node_id": node.id,
        "node_plan_digest": compute_node_plan_digest(revision, node.id),
        "evidence": {"methods": list(proof.method)},
    }


def test_package_exports_receipt_and_health_boundary() -> None:
    expected = {
        "ChangeHealthFinding",
        "ChangeHealthResult",
        "ImpactClosure",
        "ImpactClosureError",
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


def test_impact_closure_parser_canonicalizes_paths_and_validates_authority_targets() -> None:
    closure = parse_impact_closure(
        {"paths": ["docs/", "README.md", "docs/"], "authority_targets": ["REQ-002", "REQ-001", "REQ-001"]},
        declared_authority_targets={"REQ-001", "REQ-002"},
    )

    assert closure.paths == ("README.md", "docs/")
    assert closure.authority_targets == ("REQ-001", "REQ-002")
    assert parse_repository_path("/") == "/"


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments], check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repository: Path, path: str, content: str, message: str) -> str:
    file_path = repository / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    _git(repository, "add", "-A")
    _git(repository, "commit", "-m", message)
    return _git(repository, "rev-parse", "HEAD")


def test_code_revision_currency_classifies_real_git_history_and_history_failures(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "Receipt Test")
    _git(repository, "config", "user.email", "receipt@example.test")
    tested = _commit(repository, "src/app.py", "base\n", "base")
    history = GitRepositoryHistory(repository)
    src_closure = parse_impact_closure({"paths": ["src/"], "authority_targets": []})
    docs_candidate = _commit(repository, "docs/readme.md", "unrelated\n", "docs")

    assert evaluate_code_revision_currency(history, tested, tested, src_closure).code is ReceiptValidityCode.CURRENT
    assert (
        evaluate_code_revision_currency(history, tested, docs_candidate, src_closure).code
        is ReceiptValidityCode.CURRENT
    )

    stale_candidate = _commit(repository, "src/app.py", "changed\n", "source")
    stale = evaluate_code_revision_currency(history, tested, stale_candidate, src_closure)
    assert stale.code is ReceiptValidityCode.CODE_PATH_STALE
    assert (stale.path, stale.selector) == ("src/app.py", "src/")

    assert (
        evaluate_code_revision_currency(history, "f" * 40, stale_candidate, src_closure).code
        is ReceiptValidityCode.CODE_REVISION_MISSING
    )
    assert (
        evaluate_code_revision_currency(history, tested, "e" * 40, src_closure).code
        is ReceiptValidityCode.CODE_REVISION_MISSING
    )

    _git(repository, "checkout", "-b", "side", tested)
    non_descendant = _commit(repository, "docs/side.md", "side\n", "side")
    assert (
        evaluate_code_revision_currency(history, stale_candidate, non_descendant, src_closure).code
        is ReceiptValidityCode.CODE_REVISION_NOT_DESCENDANT
    )
    _git(repository, "checkout", "-")

    (repository / "lib").mkdir()
    _git(repository, "mv", "src/app.py", "lib/app.py")
    renamed = _commit(repository, "lib/app.py", "changed\n", "rename")
    renamed_result = evaluate_code_revision_currency(
        history,
        stale_candidate,
        renamed,
        parse_impact_closure({"paths": ["src/app.py"], "authority_targets": []}),
    )
    assert (renamed_result.code, renamed_result.path) == (ReceiptValidityCode.CODE_PATH_STALE, "src/app.py")

    (repository / "src").mkdir(exist_ok=True)
    (repository / "src" / "app.py").write_text("changed\n")
    copied = _commit(repository, "src/app.py", "changed\n", "copy")
    copied_result = evaluate_code_revision_currency(
        history,
        renamed,
        copied,
        parse_impact_closure({"paths": ["lib/app.py"], "authority_targets": []}),
    )
    assert (copied_result.code, copied_result.path) == (ReceiptValidityCode.CODE_PATH_STALE, "lib/app.py")

    class BrokenHistory:
        def revisions_exist(self, _tested: str, _candidate: str) -> bool:
            return True

        def is_descendant(self, _tested: str, _candidate: str) -> bool:
            return True

        def name_status(self, _tested: str, _candidate: str) -> bytes:
            return b"R100\0src/old.py\0\xff\0"

    unavailable = evaluate_code_revision_currency(BrokenHistory(), tested, stale_candidate, src_closure)
    assert unavailable.code is ReceiptValidityCode.CODE_HISTORY_UNAVAILABLE

    class QueryFailureHistory(BrokenHistory):
        def revisions_exist(self, _tested: str, _candidate: str) -> bool:
            raise receipt_module.RepositoryHistoryError

    class StaticHistory(BrokenHistory):
        def __init__(self, name_status: bytes) -> None:
            self._name_status = name_status

        def name_status(self, _tested: str, _candidate: str) -> bytes:
            return self._name_status

    assert (
        evaluate_code_revision_currency(QueryFailureHistory(), tested, stale_candidate, src_closure).code
        is ReceiptValidityCode.CODE_HISTORY_UNAVAILABLE
    )
    assert (
        evaluate_code_revision_currency(
            StaticHistory(b"M\0"),
            tested,
            stale_candidate,
            src_closure,
        ).code
        is ReceiptValidityCode.CODE_HISTORY_UNAVAILABLE
    )
    assert (
        evaluate_code_revision_currency(
            StaticHistory(b"M\0../unsafe\0"),
            tested,
            stale_candidate,
            src_closure,
        ).code
        is ReceiptValidityCode.CODE_HISTORY_UNAVAILABLE
    )


@pytest.mark.parametrize("target", ["not-a-stable-id", "REQ-01", "req-001"])
def test_impact_closure_parser_rejects_malformed_authority_targets(target: str) -> None:
    with pytest.raises(ImpactClosureError) as exc_info:
        parse_impact_closure({"paths": ["src/"], "authority_targets": [target]})

    assert exc_info.value.code == "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"


def test_impact_closure_parser_rejects_undeclared_canonical_authority_target() -> None:
    with pytest.raises(ImpactClosureError) as exc_info:
        parse_impact_closure(
            {"paths": ["src/"], "authority_targets": ["REQ-999"]},
            declared_authority_targets={"REQ-001"},
        )

    assert exc_info.value.code == "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"


@pytest.mark.parametrize("selector", ["/src", ".", "src/../secret", "src//file", "src\\file", "src\x00file"])
def test_impact_closure_parser_rejects_noncanonical_selectors(selector: str) -> None:
    with pytest.raises(ImpactClosureError) as exc_info:
        parse_impact_closure({"paths": [selector], "authority_targets": []})

    assert exc_info.value.code == "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"


@pytest.mark.parametrize(
    ("kind", "impact_closure", "expected"),
    [
        ("build", None, ReceiptParseDiagnosticCode.IMPACT_CLOSURE_MISSING),
        ("build", {"paths": [], "authority_targets": []}, ReceiptParseDiagnosticCode.IMPACT_CLOSURE_INVALID),
    ],
)
def test_receipt_parser_requires_a_valid_impact_closure(
    kind: str, impact_closure: object, expected: ReceiptParseDiagnosticCode
) -> None:
    value = _parser_receipt(kind)
    if impact_closure is None:
        del value["impact_closure"]
    else:
        value["impact_closure"] = impact_closure

    result = parse_receipt_mapping(value)

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [expected]


def test_receipt_parser_rejects_malformed_impact_closure_authority_target() -> None:
    value = _parser_receipt("build")
    value["impact_closure"] = {"paths": ["src/"], "authority_targets": ["not-a-stable-id"]}

    result = parse_receipt_mapping(value)

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [ReceiptParseDiagnosticCode.IMPACT_CLOSURE_INVALID]


@pytest.mark.parametrize("kind", _RECEIPT_KINDS)
def test_public_receipt_parser_round_trips_all_receipt_kinds(kind: str) -> None:
    value = _parser_receipt(kind)

    result = parse_receipt_mapping(value)

    assert result.diagnostics == ()
    assert result.receipt is not None
    assert result.receipt.to_mapping() == value


@pytest.mark.parametrize("kind", ["plan", "build", "accept"])
def test_public_receipt_parser_requires_node_plan_digest_for_node_scoped_receipts(kind: str) -> None:
    value = _parser_receipt(kind)
    del value["node_plan_digest"]

    result = parse_receipt_mapping(value)

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [ReceiptParseDiagnosticCode.NODE_PLAN_DIGEST_MISSING]


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda value: value.update(delivery_digest="d" * 64), ReceiptValidityCode.DELIVERY_DIGEST_STALE),
        (lambda value: value.update(node_plan_digest="e" * 64), ReceiptValidityCode.NODE_PLAN_DIGEST_STALE),
        (lambda value: value.update(target_node_id="DN-999"), ReceiptValidityCode.TARGET_MISSING),
        (lambda value: value.update(evidence={"methods": []}), ReceiptValidityCode.PROOF_UNSATISFIED),
        (lambda value: value.update(evidence={"methods": None}), ReceiptValidityCode.PROOF_UNSATISFIED),
    ],
)
def test_receipt_currentness_evaluates_local_authority_and_proof(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    expected: ReceiptValidityCode,
) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    value = _current_receipt(revision)
    mutation(value)
    parsed = parse_receipt_mapping(value)

    assert parsed.receipt is not None
    assert evaluate_receipt_currentness(revision, parsed.receipt).code is expected


def test_receipt_currentness_accepts_admission_without_node_plan_or_evidence(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    parsed = parse_receipt_mapping(_receipt(revision, "admission-current", "admission"))

    assert parsed.receipt is not None
    result = evaluate_receipt_currentness(revision, parsed.receipt)
    assert result.code is ReceiptValidityCode.CURRENT
    assert result.current


def test_receipt_currentness_rejects_unsupported_schema(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    value = _current_receipt(revision)
    value["schema_version"] = 2
    parsed = parse_receipt_mapping(value)

    assert parsed.receipt is not None
    assert evaluate_receipt_currentness(revision, parsed.receipt).code is ReceiptValidityCode.SCHEMA_UNSUPPORTED


def test_receipt_currentness_rejects_undeclared_impact_closure_authority_target(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    value = _current_receipt(revision)
    value["impact_closure"] = {"paths": ["src/"], "authority_targets": ["REQ-999"]}
    parsed = parse_receipt_mapping(value)

    assert parsed.receipt is not None
    result = evaluate_receipt_currentness(revision, parsed.receipt)
    assert result.code is ReceiptValidityCode.IMPACT_CLOSURE_INVALID
    assert result.target == "REQ-999"


def test_receipt_store_evaluates_complete_currentness_without_mutation(tmp_path: Path) -> None:
    class CurrentHistory:
        def __init__(self) -> None:
            self.name_status_calls = 0
            self.changed_paths: dict[str, bytes] = {}

        def revisions_exist(self, _tested: str, _candidate: str) -> bool:
            return True

        def is_descendant(self, _tested: str, _candidate: str) -> bool:
            return True

        def name_status(self, tested: str, _candidate: str) -> bytes:
            self.name_status_calls += 1
            return self.changed_paths.get(tested, b"")

    def complete_receipt(receipt_id: str, predecessors: list[str]) -> dict[str, object]:
        value = _current_receipt(revision)
        value["receipt_id"] = receipt_id
        value["predecessor_receipt_ids"] = predecessors
        return value

    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    records = {
        "shared-001": complete_receipt("shared-001", []),
        "left-001": complete_receipt("left-001", ["shared-001"]),
        "right-001": complete_receipt("right-001", ["shared-001"]),
        "current-001": complete_receipt("current-001", ["left-001", "right-001"]),
        "missing-001": complete_receipt("missing-001", ["not-found-001"]),
        "stale-001": complete_receipt("stale-001", []),
        "invalid-001": complete_receipt("invalid-001", ["stale-001"]),
        "cycle-a-001": complete_receipt("cycle-a-001", ["cycle-b-001"]),
        "cycle-b-001": complete_receipt("cycle-b-001", ["cycle-a-001"]),
        "superseded-001": complete_receipt("superseded-001", []),
        "covered-stale-001": complete_receipt("covered-stale-001", []),
        "covered-current-001": complete_receipt("covered-current-001", ["covered-stale-001"]),
        "uncovered-stale-001": complete_receipt("uncovered-stale-001", []),
        "uncovered-invalid-001": complete_receipt("uncovered-invalid-001", ["uncovered-stale-001"]),
    }
    records["stale-001"]["evidence"] = {"methods": []}
    records["covered-stale-001"]["code_revision"] = "e" * 40
    records["uncovered-stale-001"]["code_revision"] = "f" * 40
    records["uncovered-stale-001"]["impact_closure"] = {
        "paths": ["docs/"],
        "authority_targets": ["REQ-001"],
    }
    for receipt_id, value in records.items():
        assert store.create(receipt_id, value).receipt is not None
    supersession = _receipt(revision, "supersession-001", "supersession")
    supersession["invalidated_receipt_ids"] = ["superseded-001"]
    assert store.create("supersession-001", supersession).receipt is not None
    before = {path: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}
    history = CurrentHistory()
    history.changed_paths = {
        "e" * 40: b"M\0src/app.py\0",
        "f" * 40: b"M\0docs/readme.md\0",
    }

    current = store.evaluate_currentness("current-001", history, "d" * 40)
    repeated = store.evaluate_currentness("current-001", history, "d" * 40)
    missing = store.evaluate_currentness("missing-001", history, "d" * 40)
    invalid = store.evaluate_currentness("invalid-001", history, "d" * 40)
    cycle = store.evaluate_currentness("cycle-a-001", history, "d" * 40)
    superseded = store.evaluate_currentness("superseded-001", history, "d" * 40)
    covered = store.evaluate_currentness("covered-current-001", history, "d" * 40)
    uncovered = store.evaluate_currentness("uncovered-invalid-001", history, "d" * 40)

    assert current.code is ReceiptValidityCode.CURRENT
    assert repeated == current
    assert history.name_status_calls >= 4
    assert (missing.code, missing.target) == (ReceiptValidityCode.PREDECESSOR_MISSING, "not-found-001")
    assert (invalid.code, invalid.target) == (ReceiptValidityCode.PREDECESSOR_INVALID, "stale-001")
    assert (cycle.code, cycle.target) == (ReceiptValidityCode.PREDECESSOR_CYCLE, "cycle-a-001")
    assert (superseded.code, superseded.target) == (ReceiptValidityCode.SUPERSEDED, "superseded-001")
    assert covered.code is ReceiptValidityCode.CURRENT
    assert (uncovered.code, uncovered.target) == (
        ReceiptValidityCode.PREDECESSOR_INVALID,
        "uncovered-stale-001",
    )
    assert {path: path.read_bytes() for path in before} == before


def test_receipt_store_round_trips_all_kinds_and_preserves_existing_bytes(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)

    for index, kind in enumerate(_RECEIPT_KINDS, start=1):
        receipt_id = f"{kind}-{index:03d}"
        value = _receipt(revision, receipt_id, kind)
        if kind != "admission":
            value["impact_closure"] = {
                "paths": ["src/", "docs/", "src/"],
                "authority_targets": ["REQ-002", "REQ-001", "REQ-002"],
            }
        expected_mapping = {
            **value,
            "impact_closure": (
                {
                    "paths": ["docs/", "src/"],
                    "authority_targets": ["REQ-001", "REQ-002"],
                }
                if kind != "admission"
                else None
            ),
        }
        if kind == "admission":
            del expected_mapping["impact_closure"]

        created = store.create(receipt_id, value)
        read_back = store.read(receipt_id)

        assert created.diagnostics == ()
        assert created.receipt is not None
        assert read_back.receipt is not None
        assert read_back.receipt.to_mapping() == expected_mapping
        assert read_back.receipt.payload["evidence"] == {"kind": kind, "passed": True}
        if kind != "admission":
            assert read_back.receipt.impact_closure is not None
            assert read_back.receipt.impact_closure.paths == ("docs/", "src/")
            assert read_back.receipt.impact_closure.authority_targets == ("REQ-001", "REQ-002")

    first_id = "admission-001"
    first_path = revision.source_dir / "receipts" / f"{first_id}.yaml"
    original = first_path.read_bytes()
    with pytest.raises(ReceiptConflictError) as exc_info:
        store.create(first_id, _receipt(revision, first_id, "admission"))

    assert exc_info.value.code == "ERR_RECEIPT_CONFLICT"
    assert first_path.read_bytes() == original
    assert list(first_path.parent.glob(".tmp-*")) == []


def test_receipt_store_rejects_undeclared_impact_closure_authority_target_without_publication(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    receipt_id = "build-undeclared-001"
    value = _receipt(revision, receipt_id, "build")
    value["impact_closure"] = {"paths": ["src/"], "authority_targets": ["REQ-999"]}

    result = ReceiptStore(revision).create(receipt_id, value)

    assert result.receipt is None
    assert [item.code for item in result.diagnostics] == [ReceiptDiagnosticCode.IMPACT_CLOSURE_INVALID]
    receipts_dir = revision.source_dir / "receipts"
    assert not (receipts_dir / f"{receipt_id}.yaml").exists()
    assert list(receipts_dir.glob(".tmp-*")) == [] if receipts_dir.exists() else True


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


def test_receipt_store_confines_publish_when_directory_is_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    receipt_id = "build-race-001"
    filename = f"{receipt_id}.yaml"
    receipts_dir = revision.source_dir / "receipts"
    pinned_dir = revision.source_dir / "receipts-pinned"
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    real_link = os.link
    raced = False

    def replace_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal raced
        raced = True
        receipts_dir.rename(pinned_dir)
        receipts_dir.symlink_to(outside_dir, target_is_directory=True)
        (outside_dir / source).write_text("attacker\n", encoding="utf-8")
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(receipt_module.os, "link", replace_then_link)

    result = store.create(receipt_id, _receipt(revision, receipt_id, "build"))

    assert raced
    assert result.receipt is not None
    assert (pinned_dir / filename).is_file()
    assert not (outside_dir / filename).exists()
    assert list(pinned_dir.glob(".tmp-*")) == []


def test_receipt_store_rejects_temporary_file_substitution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    receipt_id = "build-temp-race-001"
    receipt_path = revision.source_dir / "receipts" / f"{receipt_id}.yaml"
    real_link = os.link
    raced = False

    def replace_then_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal raced
        assert src_dir_fd is not None
        raced = True
        os.unlink(source, dir_fd=src_dir_fd)
        attacker_fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=src_dir_fd)
        try:
            os.write(attacker_fd, b"attacker\n")
        finally:
            os.close(attacker_fd)
        real_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(receipt_module.os, "link", replace_then_link)

    result = store.create(receipt_id, _receipt(revision, receipt_id, "build"))

    assert raced
    assert [item.code for item in result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert not receipt_path.exists()
    assert list(receipt_path.parent.glob(".tmp-*")) == []


def test_receipt_store_rejects_final_substitution_before_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    receipt_id = "build-final-race-001"
    receipt_path = revision.source_dir / "receipts" / f"{receipt_id}.yaml"
    real_fsync = os.fsync
    raced = False

    def replace_after_validation(file_fd: int) -> None:
        nonlocal raced
        if not raced and receipt_path.exists():
            raced = True
            receipt_path.unlink()
            receipt_path.write_text("attacker\n", encoding="utf-8")
        real_fsync(file_fd)

    monkeypatch.setattr(receipt_module.os, "fsync", replace_after_validation)

    result = store.create(receipt_id, _receipt(revision, receipt_id, "build"))

    assert raced
    assert [item.code for item in result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert not receipt_path.exists()
    assert list(receipt_path.parent.glob(".tmp-*")) == []


def test_receipt_store_rejects_file_substitution_at_open(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    receipt_id = "audit-race-001"
    filename = f"{receipt_id}.yaml"
    assert store.create(receipt_id, _receipt(revision, receipt_id, "audit")).receipt is not None
    receipt_path = revision.source_dir / "receipts" / filename
    outside_path = tmp_path / "outside.yaml"
    outside_path.write_bytes(receipt_path.read_bytes())
    outside_before = outside_path.read_bytes()
    real_open = os.open
    raced = False

    def replace_then_open(path: str | Path, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal raced
        if path == filename and dir_fd is not None:
            raced = True
            receipt_path.unlink()
            receipt_path.symlink_to(outside_path)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(receipt_module.os, "open", replace_then_open)

    result = store.read(receipt_id)

    assert raced
    assert [item.code for item in result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert outside_path.read_bytes() == outside_before


def test_receipt_store_rejects_change_directory_replacement(tmp_path: Path) -> None:
    _changes_dir, revision = _load_revision(tmp_path)
    store = ReceiptStore(revision)
    original_dir = revision.source_dir.with_name("receipt-change-original")
    replacement_dir = revision.source_dir
    revision.source_dir.rename(original_dir)
    replacement_receipts = replacement_dir / "receipts"
    replacement_receipts.mkdir(parents=True)
    receipt_id = "build-replaced-001"

    create_result = store.create(receipt_id, _receipt(revision, receipt_id, "build"))
    read_result = store.read(receipt_id)

    assert [item.code for item in create_result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert [item.code for item in read_result.diagnostics] == [ReceiptDiagnosticCode.PATH_UNSAFE]
    assert list(replacement_receipts.iterdir()) == []
    assert not (original_dir / "receipts").exists()


def test_change_health_rejects_change_directory_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changes_dir = tmp_path / "changes"
    _write_modular_package(changes_dir, "health-replaced")
    real_load_change = receipt_module.load_change

    def load_then_replace(candidate_dir: Path, change_id: str) -> owlbear_kanban.ChangeLoadResult:
        result = real_load_change(candidate_dir, change_id)
        assert result.revision is not None
        source_dir = result.revision.source_dir
        source_dir.rename(source_dir.with_name("health-replaced-original"))
        source_dir.mkdir()
        return result

    monkeypatch.setattr(receipt_module, "load_change", load_then_replace)

    result = change_health(changes_dir, "health-replaced")

    assert [(item.code, item.detail, item.path) for item in result.findings] == [
        (
            ReceiptDiagnosticCode.PATH_UNSAFE.value,
            "change directory identity has changed",
            "receipts",
        )
    ]
    assert not (changes_dir / "health-replaced" / "receipts").exists()


def _admitted_package(tmp_path: Path) -> tuple[Path, Path, ChangeRevision]:
    change_id = "health-change"
    changes_dir = tmp_path / "changes"
    decisions, graph = _documents(change_id)
    change_dir = _write_modular_package(changes_dir, change_id, authority=(decisions, graph))
    initial = load_change(changes_dir, change_id)
    assert initial.revision is not None
    receipt_id = f"admission-{initial.revision.delivery_digest[:12]}"
    nodes_path = change_dir / "delivery" / "nodes.yaml"
    nodes = yaml.safe_load(nodes_path.read_text(encoding="utf-8"))
    nodes["state"] = "admitted"
    nodes["admission"] = {
        "state": "admitted",
        "delivery_digest": initial.revision.delivery_digest,
        "receipt": f"receipts/{receipt_id}.yaml",
        "limits": [],
    }
    nodes_path.write_text(yaml.safe_dump(nodes, sort_keys=False), encoding="utf-8")
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
        "delivery/contracts.yaml",
        "delivery/nodes.yaml",
        "delivery/obligations.yaml",
        f"receipts/admission-{_revision.delivery_digest[:12]}.yaml",
    )
    assert _snapshot(paths) == before


def test_admission_discovery_selects_digest_path_and_preserves_stale_history(tmp_path: Path) -> None:
    changes_dir, change_dir, revision = _admitted_package(tmp_path)
    stale_id = "admission-000000000000"
    stale_value = _receipt(revision, stale_id, "admission")
    stale_value["delivery_digest"] = "0" * 64
    stale_path = change_dir / "receipts" / f"{stale_id}.yaml"
    stale_path.write_text(yaml.safe_dump(stale_value, sort_keys=False), encoding="utf-8")
    paths = sorted(path for path in change_dir.rglob("*") if path.is_file())
    before = _snapshot(paths)

    discovery = discover_admission(revision)
    health = change_health(changes_dir, "health-change")

    assert discovery.current is not None
    assert discovery.current.receipt_id == f"admission-{revision.delivery_digest[:12]}"
    assert [item.receipt_id for item in discovery.stale_history] == [stale_id]
    assert discovery.findings == ()
    assert health.findings == ()
    assert _snapshot(paths) == before


@pytest.mark.parametrize("defect", ["absent", "ambiguous"])
def test_change_health_reports_unresolved_current_admission(tmp_path: Path, defect: str) -> None:
    changes_dir, change_dir, revision = _admitted_package(tmp_path)
    expected_id = f"admission-{revision.delivery_digest[:12]}"
    expected_path = change_dir / "receipts" / f"{expected_id}.yaml"
    if defect == "absent":
        expected_path.unlink()
    else:
        duplicate_id = "admission-current-copy"
        duplicate = _receipt(revision, duplicate_id, "admission")
        (change_dir / "receipts" / f"{duplicate_id}.yaml").write_text(
            yaml.safe_dump(duplicate, sort_keys=False),
            encoding="utf-8",
        )

    result = change_health(changes_dir, "health-change")

    assert len(result.findings) == 1
    assert result.findings[0].code == (
        ReceiptDiagnosticCode.FILE_MISSING.value if defect == "absent" else ReceiptDiagnosticCode.SCHEMA_INVALID.value
    )


@pytest.mark.parametrize(
    ("defect", "expected_code", "expected_path"),
    [
        (lambda change_dir: (change_dir / "design.md").unlink(), "ERR_CHANGE_FILE_MISSING", "design.md"),
        (
            lambda change_dir: (change_dir / "delivery/nodes.yaml").write_text("[unclosed", encoding="utf-8"),
            "ERR_CHANGE_YAML_PARSE",
            "nodes.yaml",
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
    change_dir = _write_modular_package(changes_dir, "defective-health")
    defect(change_dir)
    paths = sorted(path for path in change_dir.rglob("*") if path.is_file())
    before = _snapshot(paths)

    result = change_health(changes_dir, "defective-health")

    assert [(item.code, item.path) for item in result.findings] == [(expected_code, expected_path)]
    assert result.checked_paths == (
        "intent.md",
        "design.md",
        "decisions.yaml",
        "delivery/contracts.yaml",
        "delivery/nodes.yaml",
        "delivery/obligations.yaml",
    )
    assert _snapshot(paths) == before


def test_change_health_locates_unsafe_receipt_filename(tmp_path: Path) -> None:
    changes_dir = tmp_path / "changes"
    change_dir = _write_modular_package(changes_dir, "unsafe-receipt-health")
    receipts_dir = change_dir / "receipts"
    receipts_dir.mkdir()
    receipt_path = receipts_dir / "bad..id.yaml"
    receipt_path.write_text("not: a receipt\n", encoding="utf-8")
    before = _snapshot([receipt_path])

    result = change_health(changes_dir, "unsafe-receipt-health")

    assert [(item.code, item.path, item.target) for item in result.findings] == [
        (ReceiptDiagnosticCode.PATH_UNSAFE.value, "receipts/bad..id.yaml", None)
    ]
    assert result.checked_paths[-1] == "receipts/bad..id.yaml"
    assert _snapshot([receipt_path]) == before
