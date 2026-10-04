"""Offline repair contracts (N08-A): classify, fenced proposals, apply, resume, verify (I9) and abort."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
import pytest
from serve.delivery.tests.test_portfolio_application import (
    _git,
    _seed_loader_composed_completed_change,
    _startup_config,
)
from serve.delivery.tests.test_state_migration import (
    _N02A_SCAN,
    _assert_refused,
    _available,
    _Crash,
    _crash_at,
    _live_journal,
    _migration_dir,
    _n02a_refusals,
)

import owlbear_delivery
from owlbear_delivery import close_delivery_application, load_delivery_application, state_migration, state_repair
from owlbear_delivery.delivery_runtime import DeliveryStage
from owlbear_delivery.design_package import DesignPackageManifest, DesignPackageStore
from owlbear_delivery.runtime_models import (
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryChangeStage,
)
from owlbear_delivery.runtime_transaction import (
    MoveTransactionParticipant,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)
from owlbear_delivery.state_formats import (
    SUPPORTED_FORMAT,
    TRANSACTION_ROOTS,
    controller_process_record_bytes,
    format_marker_bytes,
    record_tree_digest,
    scan_capability,
)
from owlbear_delivery.state_migration import MigrationError
from owlbear_delivery.state_repair import CANONICAL_HOST_LOCAL
from owlbear_delivery.storage_io import acquire_controller_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_FIXTURES = Path(__file__).with_name("fixtures") / "state_formats"
# Byte copy of the merged N02-B gate (`7e6510de4:serve/delivery/src/owlbear_delivery/state_formats.py`).
_N02B_GATE = _FIXTURES / "n02b_state_formats.py.txt"
_N02B_GATE_BLOB = "f5b0a26f3d682c09a8a0ab836db53fabb7dbecd7"
_N02A_GATE = _FIXTURES / "n02a_state_formats.py.txt"
_CHANGES = ("change-a", "change-b")
_SENTINEL = "SENTINEL-RECORD-VALUE-7f3a"
_C01 = "C01:runtime/host.local.json"
_STEP = """
import os, sys
from pathlib import Path
from owlbear_delivery import state_repair
operation, root, proposal_id, crash = sys.argv[1:5]
def hook(point):
    if point == crash:
        os._exit(17)
try:
    getattr(state_repair, operation)(Path(root), proposal_id, processes=lambda: (), failure=hook)
except state_repair.MigrationError as exc:
    print("REFUSED", exc.code)
    sys.exit(3)
print("OK")
"""
_CRASHED = 17


def _none() -> tuple[()]:
    return ()


def _step(operation: str, repository: Path, proposal_id: str, crash: str = "") -> subprocess.CompletedProcess[str]:
    """Run one repair operation in a fresh process; ``crash`` kills it at that boundary."""
    return subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _STEP, operation, str(repository), proposal_id, crash),
        check=False,
        capture_output=True,
        text=True,
    )


def _repository(tmp_path: Path, *, marked: bool = True) -> Path:
    stages = (("change-a", DeliveryStage.COMPLETED), ("change-b", DeliveryStage.PLANNING))
    repository, _runtime = _seed_loader_composed_completed_change(tmp_path, stages, marked=marked)
    delivery = repository / ".owlbear/delivery"
    (delivery / "config.json").write_text(_startup_config().model_dump_json(), encoding="utf-8")
    (delivery / "runtime/host.json").write_bytes(b'{"execution_capacity":2,"schema_version":1}\n')
    return repository


def _commit_tracked(repository: Path) -> None:
    _git(repository, "add", "-f", ".owlbear/delivery/config.json", ".owlbear/delivery/runtime/host.json")
    _git(repository, "add", "-f", *(str(path) for path in (repository / ".owlbear/delivery/packages").rglob("*.*")))
    _git(repository, "commit", "-q", "-m", "tracked Delivery records")


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _admit_checkpoint(repository: Path, change_id: str) -> None:
    """Bind the admission receipt to a real package checkpoint commit, as admission does."""
    delivery = _delivery(repository)
    store = DesignPackageStore(delivery / "packages", repository, transaction_root=delivery / "runtime")
    admission = delivery / f"runtime/changes/{change_id}/admission.json"
    receipt = json.loads(admission.read_bytes())
    receipt["checkpoint_commit"] = store.checkpoint(change_id).commit
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt["receipt_id"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    admission.write_bytes(_canonical_json(receipt))


def _delivery(repository: Path) -> Path:
    return repository / ".owlbear/delivery"


def _namespace(repository: Path) -> Path:
    return _delivery(repository) / "runtime/migrations"


def _ids(report: state_repair.RepairReport) -> list[str]:
    return [finding.finding_id for finding in report.findings]


def _corrupt_host_local(repository: Path) -> bytes:
    content = f'{{"schema_version":1,"execution_capacity":"{_SENTINEL}"}}'.encode()
    (_delivery(repository) / "runtime/host.local.json").write_bytes(content)
    return content


def _refused(code: str, call: Callable[[], object]) -> MigrationError:
    with pytest.raises(MigrationError) as refused:
        call()
    assert refused.value.code == code, refused.value
    return refused.value


def _c01(repository: Path) -> state_migration.RepairProposal:
    _corrupt_host_local(repository)
    return state_repair.propose(repository, _C01)


def _apply(repository: Path, proposal: state_migration.RepairProposal, **kwargs: object) -> object:
    confirm = proposal.proposal_id if proposal.policy == "user-confirmed" else None
    return state_repair.apply(repository, proposal.proposal_id, confirm=confirm, processes=_none, **kwargs)


def _n02b_refusals(repository: Path) -> list[list[str]]:
    completed = subprocess.run(  # noqa: S603 - fixed interpreter, vendored gate and argument vector.
        (sys.executable, "-I", "-c", _N02A_SCAN, str(_N02B_GATE), str(repository)),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _downgrade_coordination(repository: Path) -> None:
    """Rewrite the seed's coordination records to version 1, the format-0 shape every N02 release reads."""
    for path in sorted((_delivery(repository) / "runtime/coordination/changes").glob("*.json")):
        payload = json.loads(path.read_bytes())
        assert "pause_request" not in payload
        payload["schema_version"] = 1
        path.write_bytes((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode())


@pytest.fixture
def forbid_application(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """R2: no repair operation may load or construct the Delivery application."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        msg = "repair constructed the Delivery application"
        raise AssertionError(msg)

    monkeypatch.setattr("owlbear_delivery.delivery_application_loader.load_delivery_application", refuse)
    monkeypatch.setattr("owlbear_delivery.load_delivery_application", refuse)
    monkeypatch.setattr("owlbear_delivery.portfolio_application.PortfolioApplication.__init__", refuse)
    yield
    monkeypatch.undo()


# ---------------------------------------------------------------------------
# Classification and routes
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("forbid_application")
def test_classify_of_a_healthy_portfolio_finds_nothing_and_writes_nothing(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    tree = record_tree_digest(repository)

    report = state_repair.classify(repository)

    assert report.findings == ()
    assert record_tree_digest(repository) == tree
    assert not (repository / ".owlbear/delivery-migrations").exists()


def test_routes_name_their_owner_and_write_nothing(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    frontier = _delivery(repository) / "runtime/changes/change-b/frontier.json"
    payload = json.loads(frontier.read_bytes())
    payload["bindings"][0]["requests"] = [
        {
            "request_id": "REQ-1",
            "kind": "decision",
            "outcome_id": payload["bindings"][0]["outcome_id"],
            "summary": "Pick one",
            "options": [],
            "resolution": {"response_text": "free text", "selected_option_id": None, "provenance": None},
        }
    ]
    frontier.write_bytes(json.dumps(payload).encode())
    tree = record_tree_digest(repository)

    report = state_repair.classify(repository)

    routes = {finding.finding_id: (finding.route, finding.operation) for finding in report.findings}
    assert routes == {
        "C04:state-migration-required": ("migrate", "delivery-migrate propose, apply, verify"),
        "C06:runtime/changes/change-b/frontier.json": ("online", "repair_stranded_frontier"),
    }
    assert all(finding.owner and finding.resume_condition for finding in report.findings)
    assert [finding.finding_id for finding in state_repair.classify(repository, "change-a").findings] == [
        "C04:state-migration-required"
    ]
    for finding_id in routes:
        _refused("repair-not-supported", lambda finding_id=finding_id: state_repair.propose(repository, finding_id))
    assert record_tree_digest(repository) == tree


def test_newer_format_routes_to_upgrade_before_any_typed_read(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (_delivery(repository) / "runtime/format.json").write_bytes(format_marker_bytes(SUPPORTED_FORMAT + 1))
    _corrupt_host_local(repository)
    tree = record_tree_digest(repository)

    report = state_repair.classify(repository)

    assert [(finding.finding_id, finding.operation) for finding in report.findings] == [
        ("C05:runtime/format.json", "/upgrade-delivery")
    ]
    _refused("repair-format-unsupported", lambda: state_repair.propose(repository, _C01))
    assert record_tree_digest(repository) == tree


# ---------------------------------------------------------------------------
# C01 host-local reset (user-confirmed)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("forbid_application")
def test_c01_host_local_reset_is_proposed_confirmed_applied_verified_and_archived(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    original = _corrupt_host_local(repository)
    assert _ids(state_repair.classify(repository)) == [_C01]
    tree = record_tree_digest(repository)

    proposal = state_repair.propose(repository, _C01)

    assert record_tree_digest(repository) == tree
    assert proposal.policy == "user-confirmed"
    assert [item.finding_id for item in proposal.findings] == [_C01]
    assert [(entry.locator, entry.after_sha256) for entry in proposal.entries] == [
        ("runtime/host.local.json", hashlib.sha256(CANONICAL_HOST_LOCAL).hexdigest())
    ]
    staged = _migration_dir(repository, proposal.proposal_id) / "stage/runtime/host.local.json"
    assert staged.read_bytes() == CANONICAL_HOST_LOCAL
    for confirm in (None, "0" * 64):
        _refused(
            "repair-confirmation-required",
            lambda confirm=confirm: state_repair.apply(
                repository, proposal.proposal_id, confirm=confirm, processes=_none
            ),
        )
    assert record_tree_digest(repository) == tree
    assert not (_migration_dir(repository, proposal.proposal_id) / "backup").exists()

    journal = _apply(repository, proposal)

    assert (journal.state, journal.kind, journal.confirmed) == ("applied", "repair", proposal.proposal_id)
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == CANONICAL_HOST_LOCAL
    backup = _migration_dir(repository, proposal.proposal_id) / "backup/records/runtime/host.local.json"
    assert backup.read_bytes() == original
    _assert_refused(repository, "state-migration-incomplete")
    verified = state_repair.verify(repository, proposal.proposal_id, processes=_none)
    assert verified.state == "verified"
    assert not _namespace(repository).exists()
    archived = json.loads((_migration_dir(repository, proposal.proposal_id) / "journal.json").read_bytes())
    assert (archived["state"], archived["kind"], archived["schema_version"]) == ("verified", "repair", 2)
    assert state_repair.classify(repository).findings == ()
    assert state_repair.verify(repository, proposal.proposal_id, processes=_none).state == "verified"


def test_c01_repaired_portfolio_loads_every_change(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    _apply(repository, proposal)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    _available(repository, _CHANGES)


# ---------------------------------------------------------------------------
# C02 tracked-record restore (user-confirmed)
# ---------------------------------------------------------------------------


def test_c02_restores_a_verifying_head_config_and_leaves_the_path_clean(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _commit_tracked(repository)
    config = _delivery(repository) / "config.json"
    config.write_text("{}", encoding="utf-8")
    finding = "C02:config.json"
    assert _ids(state_repair.classify(repository)) == [finding]

    proposal = state_repair.propose(repository, finding)
    _apply(repository, proposal)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    assert _git(repository, "status", "--porcelain", "--", ".owlbear/delivery/config.json") == ""
    _available(repository, _CHANGES)


def test_c02_restores_a_tampered_admitted_package_and_the_portfolio_lists_again(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _admit_checkpoint(repository, "change-a")
    _commit_tracked(repository)
    design = _delivery(repository) / "packages/change-a/design.md"
    original = design.read_bytes()
    design.write_bytes(original + f"\n{_SENTINEL}\n".encode())
    finding = "C02:packages/change-a"
    assert _ids(state_repair.classify(repository)) == [finding]

    proposal = state_repair.propose(repository, finding)
    assert [entry.locator for entry in proposal.entries] == ["packages/change-a/design.md"]
    _apply(repository, proposal)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    assert design.read_bytes() == original
    application = load_delivery_application(_startup_config(), workspace_root=repository)
    try:
        listed = application.list_changes().model_dump(mode="json")
    finally:
        close_delivery_application(application)
    assert "change-a" in json.dumps(listed)


@pytest.mark.parametrize("head", ["invalid", "absent", "other-admission"])
def test_c02_without_a_verifying_matching_head_is_contained_and_never_proposed(tmp_path: Path, head: str) -> None:
    repository = _repository(tmp_path)
    if head == "invalid":
        (_delivery(repository) / "config.json").write_text("{}", encoding="utf-8")
        _commit_tracked(repository)
        locator = "config.json"
    elif head == "absent":
        locator = "config.json"
    else:
        authority = _delivery(repository) / "packages/change-a/authority.json"
        _commit_tracked(repository)
        admission = _delivery(repository) / "runtime/changes/change-a/admission.json"
        receipt = json.loads(admission.read_bytes())
        receipt["contract_digest"] = "e" * 64
        payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
        receipt["receipt_id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        admission.write_bytes(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode())
        authority.write_bytes(authority.read_bytes() + b" ")
        locator = "packages/change-a"
    if head != "other-admission":
        (_delivery(repository) / "config.json").write_text("{}", encoding="utf-8")
    tree = record_tree_digest(repository)

    findings = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}

    assert f"C07:{locator}" in findings
    assert not any(finding_id.startswith("C02") for finding_id in findings)
    _refused("repair-not-supported", lambda: state_repair.propose(repository, f"C07:{locator}"))
    assert record_tree_digest(repository) == tree


def test_c02_never_restores_a_head_package_other_than_the_admitted_one(tmp_path: Path) -> None:
    """``HEAD`` keeps the admitted ``authority.json`` but carries a different design and its own manifest."""
    repository = _repository(tmp_path)
    _admit_checkpoint(repository, "change-a")
    package = _delivery(repository) / "packages/change-a"
    original = {name: (package / name).read_bytes() for name in ("intent.md", "design.md", "authority.json")}
    design = original["design.md"] + b"\nnot the admitted design\n"
    manifest = DesignPackageManifest.from_content("change-a", original["intent.md"], design, original["authority.json"])
    (package / "design.md").write_bytes(design)
    (package / "manifest.json").write_bytes(manifest.canonical_bytes())
    _commit_tracked(repository)
    (package / "design.md").write_bytes(design + f"{_SENTINEL}\n".encode())
    tree = record_tree_digest(repository)

    findings = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}

    assert findings["C07:packages/change-a"].route == "contained"
    assert "C02:packages/change-a" not in findings
    _refused("repair-not-supported", lambda: state_repair.propose(repository, "C02:packages/change-a"))
    assert record_tree_digest(repository) == tree


# ---------------------------------------------------------------------------
# Two startup faults and retained migration history
# ---------------------------------------------------------------------------


def test_two_startup_faults_are_repaired_one_verified_proposal_at_a_time(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _commit_tracked(repository)
    _corrupt_host_local(repository)
    (_delivery(repository) / "runtime/host.json").write_bytes(b"not json")
    assert _ids(state_repair.classify(repository)) == [_C01, "C02:runtime/host.json"]

    first = state_repair.propose(repository, _C01)
    _apply(repository, first)
    state_repair.verify(repository, first.proposal_id, processes=_none)
    assert _ids(state_repair.classify(repository)) == ["C02:runtime/host.json"]
    second = state_repair.propose(repository, "C02:runtime/host.json")
    assert [item.finding_id for item in second.findings] == ["C02:runtime/host.json"]
    _apply(repository, second)
    state_repair.verify(repository, second.proposal_id, processes=_none)

    assert state_repair.classify(repository).findings == ()
    _available(repository, _CHANGES)


def test_retained_verified_migration_history_is_recorded_and_survives_the_repair(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    migration = state_migration.propose(repository)
    state_migration.apply(repository, migration.migration_id)
    state_migration.verify(repository, migration.migration_id)
    migration_journal = _namespace(repository) / migration.migration_id / "journal.json"
    retained = migration_journal.read_bytes()

    proposal = _c01(repository)
    journal = _apply(repository, proposal)

    assert [(item.migration_id, item.sha256) for item in journal.retained] == [
        (migration.migration_id, hashlib.sha256(retained).hexdigest())
    ]
    state_repair.verify(repository, proposal.proposal_id, processes=_none)
    assert migration_journal.read_bytes() == retained
    assert sorted(path.name for path in _namespace(repository).iterdir()) == [migration.migration_id]
    _available(repository, _CHANGES)


@pytest.mark.parametrize("change", ["second-open", "unreadable", "added-verified", "changed-retained"])
def test_verify_refuses_a_changed_journal_set_and_abort_still_restores(tmp_path: Path, change: str) -> None:
    repository = _repository(tmp_path, marked=False)
    migration = state_migration.propose(repository)
    state_migration.apply(repository, migration.migration_id)
    state_migration.verify(repository, migration.migration_id)
    original = _corrupt_host_local(repository)
    proposal = state_repair.propose(repository, _C01)
    _apply(repository, proposal)
    retained = _namespace(repository) / migration.migration_id / "journal.json"
    other = _namespace(repository) / ("f" * 64)
    if change == "changed-retained":
        retained.write_bytes(retained.read_bytes().replace(b'"applied"', b'"applied" ').replace(b"}\n", b"} \n"))
    else:
        other.mkdir()
        body = json.loads(retained.read_bytes())
        body["migration_id"] = "f" * 64
        body["state"] = {"second-open": "applying", "added-verified": "verified"}.get(change, "verified")
        content = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
        (other / "journal.json").write_bytes(b"\x00garbage" if change == "unreadable" else content)
    tree = record_tree_digest(repository)

    _refused("repair-verify-mismatch", lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none))

    assert record_tree_digest(repository) == tree
    assert _live_journal(repository, proposal.proposal_id).state == "applied"  # type: ignore[union-attr]
    state_repair.abort(repository, proposal.proposal_id, processes=_none)
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original


def test_a_finding_new_after_apply_is_a_verify_mismatch_and_the_journal_stays_applied(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    _apply(repository, proposal)
    (_delivery(repository) / "runtime/changes/change-a/admission.json").write_bytes(b"{}")

    refused = _refused(
        "repair-verify-mismatch", lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none)
    )

    assert refused.locator is None or "admission" in refused.locator
    assert _live_journal(repository, proposal.proposal_id).state == "applied"  # type: ignore[union-attr]


def test_a_changed_failure_at_the_same_finding_id_is_a_verify_mismatch(tmp_path: Path) -> None:
    """I9 compares complete fingerprints: a replay leaving contract.json invalid in a new way is not 'unchanged'."""
    repository = _repository(tmp_path, marked=False)
    runtime = _delivery(repository) / "runtime"
    contract = Path("changes/change-a/contract.json")
    (runtime / contract).write_bytes(b"{}")
    transaction = RuntimeTransaction(
        runtime, "contract-rewrite", (ReplacementTransactionParticipant(runtime, contract, b"{}", b'{"a":1}'),)
    )
    with pytest.raises(_Pending):
        transaction.commit(failure=_stop)
    finding_id = "C07:runtime/changes/change-a/contract.json"
    before = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}
    proposal = state_repair.propose(repository, "C03:transactions")
    state_repair.apply(repository, proposal.proposal_id, processes=_none)

    _refused("repair-verify-mismatch", lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none))
    assert _live_journal(repository, proposal.proposal_id).state == "applied"  # type: ignore[union-attr]
    after = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}
    assert after[finding_id].code == before[finding_id].code
    assert after[finding_id].fingerprint() != before[finding_id].fingerprint()
    state_repair.abort(repository, proposal.proposal_id, processes=_none)
    assert (runtime / contract).read_bytes() == b"{}"


def test_an_equal_sized_changed_failure_above_one_mebibyte_is_a_verify_mismatch(tmp_path: Path) -> None:
    """A3: evidence hashes every byte, so different invalid bytes of the same size above 1 MiB still differ."""
    repository = _repository(tmp_path, marked=False)
    runtime = _delivery(repository) / "runtime"
    contract = Path("changes/change-a/contract.json")
    size = (1 << 20) + 4096
    before, after = b"{}".ljust(size), b'{"a":1}'.ljust(size)
    (runtime / contract).write_bytes(before)
    transaction = RuntimeTransaction(
        runtime, "contract-rewrite", (ReplacementTransactionParticipant(runtime, contract, before, after),)
    )
    with pytest.raises(_Pending):
        transaction.commit(failure=_stop)
    finding_id = "C07:runtime/changes/change-a/contract.json"
    proposal = state_repair.propose(repository, "C03:transactions")
    state_repair.apply(repository, proposal.proposal_id, processes=_none)
    assert (runtime / contract).read_bytes() == after

    _refused("repair-verify-mismatch", lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none))

    assert _live_journal(repository, proposal.proposal_id).state == "applied"  # type: ignore[union-attr]
    proposed = {item.finding_id: item for item in proposal.findings}[finding_id]
    observed = {item.finding_id: item for item in state_repair.classify(repository).fingerprints}[finding_id]
    assert (proposed.evidence, observed.evidence) == ("complete", "complete")
    assert (observed.code, observed.locator) == (proposed.code, proposed.locator)
    assert observed != proposed
    state_repair.abort(repository, proposal.proposal_id, processes=_none)
    assert (runtime / contract).read_bytes() == before


def test_a_directory_finding_past_the_entry_bound_is_incomplete_and_verify_refuses(tmp_path: Path) -> None:
    """A3: an overflowing directory is never truncated; its finding is incomplete and verify fails closed."""
    repository = _repository(tmp_path)
    stray = _delivery(repository) / "packages/change-x"
    stray.mkdir()
    for index in range(300):
        (stray / f"note-{index:03}.txt").write_bytes(b"0")
    original = _corrupt_host_local(repository)
    proposal = state_repair.propose(repository, _C01)
    _apply(repository, proposal)

    refused = _refused(
        "repair-verify-mismatch", lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none)
    )

    assert refused.locator == "C07:packages/change-x"
    assert _live_journal(repository, proposal.proposal_id).state == "applied"  # type: ignore[union-attr]
    proposed = {item.finding_id: item.evidence for item in proposal.findings}
    assert proposed == {_C01: "complete", "C07:packages/change-x": "incomplete"}
    state_repair.abort(repository, proposal.proposal_id, processes=_none)
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original


# ---------------------------------------------------------------------------
# C03 transaction replay (engine replay)
# ---------------------------------------------------------------------------


class _Pending(BaseException):
    """Stops a transaction commit after its manifest is durable and before publication."""


def _stop(stage: str) -> None:
    if stage == "before-publication":
        raise _Pending(stage)


def _pending_runtime_and_packages(repository: Path) -> dict[str, bytes | None]:
    """Mixed participants across two registered roots, left pending by their real commit path."""
    runtime, packages = _delivery(repository) / "runtime", _delivery(repository) / "packages"
    notes = runtime / "notes"
    notes.mkdir()
    (notes / "source.json").write_bytes(b'{"moved":true}\n')
    host = runtime / "host.json"
    replacement = b'{"execution_capacity":3,"schema_version":1}\n'
    (packages / ".notes").mkdir()
    first = RuntimeTransaction(
        runtime,
        "repair-fixture-a",
        (
            TransactionParticipant(runtime, Path("notes/created.json"), b'{"created":true}\n'),
            ReplacementTransactionParticipant(runtime, Path("host.json"), host.read_bytes(), replacement),
            MoveTransactionParticipant(
                runtime, Path("notes/source.json"), Path("notes/moved.json"), b'{"moved":true}\n', b'{"moved":true}\n'
            ),
        ),
    )
    second = RuntimeTransaction(
        packages, "repair-fixture-b", (TransactionParticipant(packages, Path(".notes/package.txt"), b"note\n"),)
    )
    for transaction in (first, second):
        with pytest.raises(_Pending):
            transaction.commit(failure=_stop)
    return {
        "runtime/notes/created.json": b'{"created":true}\n',
        "runtime/host.json": replacement,
        "runtime/notes/moved.json": b'{"moved":true}\n',
        "runtime/notes/source.json": None,
        "packages/.notes/package.txt": b"note\n",
        "runtime/transactions/repair-fixture-a.yaml": None,
        "packages/transactions/repair-fixture-b.yaml": None,
    }


def _state(repository: Path, locators: dict[str, bytes | None]) -> dict[str, bytes | None]:
    return {
        locator: (_delivery(repository) / locator).read_bytes() if (_delivery(repository) / locator).exists() else None
        for locator in locators
    }


def test_c03_replays_mixed_participants_in_two_roots_then_the_migration_proceeds(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    expected = _pending_runtime_and_packages(repository)
    report = state_repair.classify(repository)
    assert _ids(report) == ["C03:transactions", "C04:state-migration-required"]
    _refused(
        "transactions-pending",
        lambda: state_migration.apply(repository, state_migration.propose(repository).migration_id),
    )

    proposal = state_repair.propose(repository, "C03:transactions")

    assert proposal.policy == "engine-replay"
    assert [manifest.locator for manifest in proposal.manifests] == [
        "packages/transactions/repair-fixture-b.yaml",
        "runtime/transactions/repair-fixture-a.yaml",
    ]
    assert {(item.kind, item.destination, item.source) for item in proposal.participants} == {
        ("immutable", "runtime/notes/created.json", None),
        ("replacement", "runtime/host.json", None),
        ("move", "runtime/notes/moved.json", "runtime/notes/source.json"),
        ("immutable", "packages/.notes/package.txt", None),
    }
    journal = state_repair.apply(repository, proposal.proposal_id, processes=_none)
    assert journal.steps == tuple(manifest.locator for manifest in proposal.manifests)
    assert _state(repository, expected) == expected
    state_repair.verify(repository, proposal.proposal_id, processes=_none)
    assert _ids(state_repair.classify(repository)) == ["C04:state-migration-required"]
    migration = state_migration.propose(repository)
    state_migration.apply(repository, migration.migration_id)
    state_migration.verify(repository, migration.migration_id)
    _available(repository, _CHANGES)


def _contained_manifest(repository: Path, *, extra: bool = False) -> Path:
    root = _delivery(repository) / "runtime/finalization-reports/change-a"
    root.mkdir(parents=True)
    root = root.resolve()
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        transaction = RuntimeTransaction(
            root, "report-fixture", (TransactionParticipant(root, Path("notes/report.json"), b'{"r":1}\n'),)
        )
        with pytest.raises(_Pending):
            transaction.commit_contained(descriptor, failure=_stop)
    finally:
        os.close(descriptor)
    manifest = root / "transactions/report-fixture.yaml"
    if extra:
        import yaml  # noqa: PLC0415

        value = yaml.safe_load(manifest.read_bytes())
        value["unexpected"] = True
        manifest.write_text(yaml.safe_dump(value, sort_keys=True), encoding="utf-8")
    return manifest


def test_c03_replays_a_contained_root_through_the_contained_publish_path(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    manifest = _contained_manifest(repository)

    proposal = state_repair.propose(repository, "C03:transactions")
    assert [(item.root, item.validator) for item in proposal.manifests] == [
        ("runtime/finalization-reports/change-a", "contained")
    ]
    state_repair.apply(repository, proposal.proposal_id, processes=_none)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    assert not manifest.exists()
    assert (manifest.parent.parent / "notes/report.json").read_bytes() == b'{"r":1}\n'


@pytest.mark.parametrize("shape", ["garbage", "unexpected-field", "unmapped-root"])
def test_manifests_failing_their_owner_validator_are_contained_and_never_replayed(tmp_path: Path, shape: str) -> None:
    repository = _repository(tmp_path, marked=False)
    _pending_runtime_and_packages(repository)
    if shape == "garbage":
        bad = _delivery(repository) / "runtime/transactions/zz-garbage.yaml"
        bad.write_text(f"{_SENTINEL}: [\n", encoding="utf-8")
    elif shape == "unexpected-field":
        bad = _contained_manifest(repository, extra=True)
    else:
        bad = _delivery(repository) / "runtime/changes/change-a/transactions/legacy.yaml"
        bad.parent.mkdir()
        bad.write_text("schema_version: 1\nparticipants: []\n", encoding="utf-8")
    tree = record_tree_digest(repository)
    manifests = sorted(path.read_bytes() for path in _delivery(repository).rglob("transactions/*.yaml"))

    report = state_repair.classify(repository)

    assert not any(finding.catalogue == "C03" for finding in report.findings)
    contained = [finding.locator for finding in report.findings if finding.catalogue == "C07"]
    assert bad.relative_to(_delivery(repository)).as_posix() in contained
    assert "runtime/transactions/repair-fixture-a.yaml" in contained
    _refused("repair-not-supported", lambda: state_repair.propose(repository, "C03:transactions"))
    assert record_tree_digest(repository) == tree
    assert sorted(path.read_bytes() for path in _delivery(repository).rglob("transactions/*.yaml")) == manifests


@pytest.mark.parametrize("drift", ["added", "removed", "altered", "participant"])
def test_c03_drift_after_propose_is_stale_without_a_write(tmp_path: Path, drift: str) -> None:
    repository = _repository(tmp_path, marked=False)
    _pending_runtime_and_packages(repository)
    proposal = state_repair.propose(repository, "C03:transactions")
    runtime = _delivery(repository) / "runtime"
    if drift == "added":
        extra = RuntimeTransaction(runtime, "added", (TransactionParticipant(runtime, Path("notes/x.json"), b"x"),))
        with pytest.raises(_Pending):
            extra.commit(failure=_stop)
    elif drift == "removed":
        (_delivery(repository) / "packages/transactions/repair-fixture-b.yaml").unlink()
    elif drift == "altered":
        manifest = runtime / "transactions/repair-fixture-a.yaml"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
    else:
        (runtime / "notes/created.json").write_bytes(b'{"created":true}\n')
    tree = record_tree_digest(repository)

    _refused("repair-proposal-stale", lambda: state_repair.apply(repository, proposal.proposal_id, processes=_none))

    assert record_tree_digest(repository) == tree
    assert _live_journal(repository, proposal.proposal_id) is None


@pytest.mark.parametrize("participant", ["replacement", "move"])
def test_c03_binds_participants_already_at_their_after_state_and_stops_on_their_drift(
    tmp_path: Path, participant: str
) -> None:
    """A participant published before the crash, or a move source already gone, is bound and backed up (I4)."""
    repository = _repository(tmp_path, marked=False)
    expected = _pending_runtime_and_packages(repository)
    runtime = _delivery(repository) / "runtime"
    original_host = (runtime / "host.json").read_bytes()
    if participant == "replacement":
        locator, drift = "runtime/host.json", original_host
        (runtime / "host.json").write_bytes(expected["runtime/host.json"])  # type: ignore[arg-type]
    else:
        locator, drift = "runtime/notes/source.json", b'{"moved":true}\n'
        (runtime / "notes/moved.json").write_bytes(b'{"moved":true}\n')
        (runtime / "notes/source.json").unlink()
    proposal = state_repair.propose(repository, "C03:transactions")
    bound = {entry.locator: (entry.before_sha256, entry.after_sha256) for entry in proposal.entries}
    before, after = bound[locator]
    assert before == after
    with pytest.raises(_Crash):
        state_repair.apply(repository, proposal.proposal_id, processes=_none, failure=_crash_at("after-backup"))
    (_delivery(repository) / locator).write_bytes(drift)
    tree = record_tree_digest(repository, exclude_migrations=True)

    for operation in (state_repair.resume, state_repair.abort):
        _refused(
            "repair-corruption-stop",
            lambda operation=operation: operation(repository, proposal.proposal_id, processes=_none),
        )

    assert (_delivery(repository) / locator).read_bytes() == drift
    assert record_tree_digest(repository, exclude_migrations=True) == tree
    backup = _migration_dir(repository, proposal.proposal_id) / "backup/records" / locator
    assert backup.exists() is (before is not None)


def test_a_pending_replacement_of_invalid_host_local_bytes_is_replayed_before_c01(tmp_path: Path) -> None:
    """C01 never runs over a pending manifest; the loader's read-only refusal makes C03 eligible (U1)."""
    repository = _repository(tmp_path)
    invalid = _corrupt_host_local(repository)
    early = state_repair.propose(repository, _C01)
    runtime = _delivery(repository) / "runtime"
    replacement = b'{"execution_capacity":2,"schema_version":1}\n'
    transaction = RuntimeTransaction(
        runtime,
        "host-local-tuning",
        (ReplacementTransactionParticipant(runtime, Path("host.local.json"), invalid, replacement),),
    )
    with pytest.raises(_Pending):
        transaction.commit(failure=_stop)
    assert _ids(state_repair.classify(repository)) == [_C01, "C03:transactions"]
    tree = record_tree_digest(repository)

    _refused("repair-proposal-stale", lambda: _apply(repository, early))
    _refused("repair-not-supported", lambda: state_repair.propose(repository, _C01))
    assert record_tree_digest(repository) == tree

    proposal = state_repair.propose(repository, "C03:transactions")
    state_repair.apply(repository, proposal.proposal_id, processes=_none)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    assert (runtime / "host.local.json").read_bytes() == replacement
    assert state_repair.classify(repository).findings == ()
    _available(repository, _CHANGES)


_C03_CRASHES = (
    "before-replay-0",
    "batch-0:after-first-publication",
    "batch-1:before-manifest-cleanup",
    "after-replay-1",
)


@pytest.mark.parametrize("crash", _C03_CRASHES)
def test_c03_crash_then_fresh_process_resume_reaches_the_exact_after_state(tmp_path: Path, crash: str) -> None:
    repository = _repository(tmp_path, marked=False)
    expected = _pending_runtime_and_packages(repository)
    proposal = state_repair.propose(repository, "C03:transactions")

    assert _step("apply", repository, proposal.proposal_id, crash).returncode == _CRASHED
    _assert_refused(repository, "state-migration-incomplete")
    resumed = _step("resume", repository, proposal.proposal_id)

    assert resumed.stdout.strip() == "OK", resumed.stdout + resumed.stderr
    assert _state(repository, expected) == expected
    assert _step("resume", repository, proposal.proposal_id).stdout.strip() == "OK"
    assert _step("verify", repository, proposal.proposal_id).stdout.strip() == "OK"


_ABORT_CRASHES = ("abort-after-a", "abort-after-b", "abort-after-c", "abort-after-d", "abort-after-archive")


@pytest.mark.parametrize("crash", _ABORT_CRASHES)
def test_c03_abort_from_a_fresh_process_restores_the_exact_before_state_at_every_step(
    tmp_path: Path, crash: str
) -> None:
    repository = _repository(tmp_path, marked=False)
    locators = _pending_runtime_and_packages(repository)
    before = _state(repository, locators)
    tree = record_tree_digest(repository)
    proposal = state_repair.propose(repository, "C03:transactions")
    assert _step("apply", repository, proposal.proposal_id, "batch-1:before-manifest-cleanup").returncode == _CRASHED

    assert _step("abort", repository, proposal.proposal_id, crash).returncode == _CRASHED
    assert _step("abort", repository, proposal.proposal_id).stdout.strip() == "OK"
    assert _step("abort", repository, proposal.proposal_id).stdout.strip() == "OK"

    assert _state(repository, locators) == before
    assert record_tree_digest(repository) == tree
    assert not _namespace(repository).exists()
    assert _ids(state_repair.classify(repository)) == ["C03:transactions", "C04:state-migration-required"]


def test_abort_after_verified_is_refused_without_a_write(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    _apply(repository, proposal)
    with pytest.raises(_Crash):
        state_repair.verify(repository, proposal.proposal_id, processes=_none, failure=_crash_at("after-verified"))
    tree = record_tree_digest(repository)

    _refused("repair-journal-open", lambda: state_repair.abort(repository, proposal.proposal_id, processes=_none))

    assert record_tree_digest(repository) == tree


# ---------------------------------------------------------------------------
# Crash injection, resume, abort and the third digest (V21)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("crash", ["after-backup", "after-replacement-0", "before-applied"])
def test_c01_crash_refuses_start_and_resume_converges_byte_identically(tmp_path: Path, crash: str) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    confirm = proposal.proposal_id

    with pytest.raises(_Crash):
        state_repair.apply(repository, confirm, confirm=confirm, processes=_none, failure=_crash_at(crash))

    _assert_refused(repository, "state-migration-incomplete")
    _refused("repair-journal-open", lambda: state_repair.verify(repository, confirm, processes=_none))
    assert _step("resume", repository, confirm).stdout.strip() == "OK"
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == CANONICAL_HOST_LOCAL
    assert _live_journal(repository, confirm).state == "applied"  # type: ignore[union-attr]
    assert _step("resume", repository, confirm).stdout.strip() == "OK"
    assert _step("verify", repository, confirm).stdout.strip() == "OK"
    _available(repository, _CHANGES)


@pytest.mark.parametrize("crash", [*_ABORT_CRASHES, "abort-after-e"])
@pytest.mark.parametrize("applied", ["after-backup", "applied"])
def test_c01_abort_restores_every_path_from_a_fresh_process(tmp_path: Path, crash: str, applied: str) -> None:
    repository = _repository(tmp_path)
    original = _corrupt_host_local(repository)
    tree = record_tree_digest(repository)
    proposal = state_repair.propose(repository, _C01)
    confirm = proposal.proposal_id
    if applied == "applied":
        _apply(repository, proposal)
    else:
        with pytest.raises(_Crash):
            state_repair.apply(repository, confirm, confirm=confirm, processes=_none, failure=_crash_at(applied))

    assert _step("abort", repository, confirm, crash).returncode == _CRASHED
    assert _step("abort", repository, confirm).stdout.strip() == "OK"

    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original
    assert record_tree_digest(repository) == tree
    assert not _namespace(repository).exists()
    archived = json.loads((_migration_dir(repository, confirm) / "journal.json").read_bytes())
    assert archived["state"] == "aborted"


def test_a_third_digest_stops_resume_and_abort_with_every_copy_preserved(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    original = _corrupt_host_local(repository)
    proposal = state_repair.propose(repository, _C01)
    with pytest.raises(_Crash):
        _apply(repository, proposal, failure=_crash_at("after-backup"))
    host_local = _delivery(repository) / "runtime/host.local.json"
    host_local.write_bytes(b'{"schema_version":1}')
    tree = record_tree_digest(repository)

    for operation in (state_repair.resume, state_repair.abort):
        _refused(
            "repair-corruption-stop",
            lambda operation=operation: operation(repository, proposal.proposal_id, processes=_none),
        )

    assert host_local.read_bytes() == b'{"schema_version":1}'
    backup = _migration_dir(repository, proposal.proposal_id) / "backup/records/runtime/host.local.json"
    assert backup.read_bytes() == original
    assert record_tree_digest(repository, exclude_migrations=True) == {
        locator: digest for locator, digest in tree.items() if not locator.startswith("runtime/migrations/")
    }


def test_stale_bytes_after_propose_are_refused_without_a_write(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    (_delivery(repository) / "runtime/host.local.json").write_bytes(b"other invalid bytes")
    tree = record_tree_digest(repository)

    _refused("repair-proposal-stale", lambda: _apply(repository, proposal))

    assert record_tree_digest(repository) == tree


# ---------------------------------------------------------------------------
# Shared journal rule (I2) with migrations
# ---------------------------------------------------------------------------


def test_a_migration_journal_blocks_repairs_and_a_repair_journal_blocks_migrations(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    repository = _repository(tmp_path / "a", marked=False)
    migration = state_migration.propose(repository)
    with pytest.raises(_Crash):
        state_migration.apply(repository, migration.migration_id, failure=_crash_at("after-backup"))
    _corrupt_host_local(repository)
    _refused("repair-journal-open", lambda: state_repair.propose(repository, _C01))
    _refused("repair-not-supported", lambda: state_repair.verify(repository, migration.migration_id, processes=_none))

    repository = _repository(tmp_path / "b", marked=False)
    migration = state_migration.propose(repository)
    proposal = _c01(repository)
    with pytest.raises(_Crash):
        _apply(repository, proposal, failure=_crash_at("after-backup"))

    _refused("repair-journal-open", lambda: state_migration.propose(repository))
    _refused("repair-journal-open", lambda: state_migration.apply(repository, migration.migration_id))
    _refused("proposal-unknown", lambda: state_migration.resume(repository, proposal.proposal_id))
    finding = next(item for item in state_repair.classify(repository).findings if item.catalogue == "C04")
    assert finding.operation == f"delivery-repair resume or abort {proposal.proposal_id}"


def test_a_controller_holding_the_lock_shared_refuses_every_writing_repair_command(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    holder = acquire_controller_lock(_delivery(repository) / "runtime")
    tree = record_tree_digest(repository)
    try:
        for call in (
            lambda: _apply(repository, proposal),
            lambda: state_repair.resume(repository, proposal.proposal_id, processes=_none),
            lambda: state_repair.verify(repository, proposal.proposal_id, processes=_none),
            lambda: state_repair.abort(repository, proposal.proposal_id, processes=_none),
        ):
            _refused("repair-controller-running", call)
    finally:
        holder.release()
    assert record_tree_digest(repository) == tree


# ---------------------------------------------------------------------------
# Journal-state table and namespace cleanup (I3)
# ---------------------------------------------------------------------------


def _repair_at(repository: Path, state: str) -> str:
    """Drive one C01 repair to ``state`` and return its proposal ID."""
    proposal = _c01(repository)
    confirm = proposal.proposal_id
    apply_crash = {"backed-up": "after-backup", "applying": "after-replacement-0"}.get(state)
    if apply_crash:
        with pytest.raises(_Crash):
            state_repair.apply(repository, confirm, confirm=confirm, processes=_none, failure=_crash_at(apply_crash))
        return confirm
    _apply(repository, proposal)
    crash = {
        "aborting": ("abort", "abort-after-b"),
        "verified": ("verify", "after-verified"),
        "archived-verified": ("verify", "after-live-removed"),
        "archived-aborted": ("abort", "abort-after-e"),
    }.get(state)
    if crash is not None:
        operation, point = crash
        with pytest.raises(_Crash):
            getattr(state_repair, operation)(repository, confirm, processes=_none, failure=_crash_at(point))
    return confirm


_REPAIR_ROWS = {
    # state: (normal gate refuses, classify operation prefix, command that converges)
    "backed-up": (True, "delivery-repair resume or abort", "resume"),
    "applying": (True, "delivery-repair resume or abort", "resume"),
    "applied": (True, "delivery-repair verify or abort", "verify"),
    "aborting": (True, "delivery-repair abort", "abort"),
    "verified": (False, "delivery-repair verify", "verify"),
    "archived-verified": (False, "delivery-repair verify", "verify"),
    "archived-aborted": (False, "delivery-repair abort", "abort"),
}


@pytest.mark.parametrize("state", list(_REPAIR_ROWS))
def test_every_repair_journal_state_has_its_commands_gates_and_route(tmp_path: Path, state: str) -> None:
    repository = _repository(tmp_path)
    proposal_id = _repair_at(repository, state)
    refuses, operation, command = _REPAIR_ROWS[state]

    refusals = [refusal.code for refusal in scan_capability(repository).refusals]
    findings = [finding for finding in state_repair.classify(repository).findings if finding.catalogue == "C04"]

    assert ("state-migration-incomplete" in refusals) is refuses
    assert [finding.operation for finding in findings] == [f"{operation} {proposal_id}"]
    if state.startswith("archived"):
        assert list(_namespace(repository).iterdir()) == []
        assert ["state-migration-incomplete", "runtime/migrations"] in _n02a_refusals(repository)
        other = "abort" if command == "verify" else "verify"
        tree = record_tree_digest(repository)
        _refused("repair-archived", lambda: getattr(state_repair, other)(repository, proposal_id, processes=_none))
        assert record_tree_digest(repository) == tree
    if state in {"backed-up", "applying", "applied", "aborting", "verified"}:
        _refused("repair-journal-open", lambda: state_repair.propose(repository, _C01))
        _refused("repair-journal-open", lambda: state_migration.propose(repository))
    if state == "aborting":
        _refused("repair-journal-open", lambda: state_repair.resume(repository, proposal_id, processes=_none))
    getattr(state_repair, command)(repository, proposal_id, processes=_none)
    if command != "resume":
        assert not _namespace(repository).exists()
        assert not any(finding.catalogue == "C04" for finding in state_repair.classify(repository).findings)
        tree = record_tree_digest(repository)
        getattr(state_repair, command)(repository, proposal_id, processes=_none)
        assert record_tree_digest(repository) == tree


def test_an_invalid_repair_journal_is_contained_verify_refuses_and_digest_checked_abort_restores(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    original = _corrupt_host_local(repository)
    proposal_id = state_repair.propose(repository, _C01).proposal_id
    state_repair.apply(repository, proposal_id, confirm=proposal_id, processes=_none)
    journal = _namespace(repository) / proposal_id / "journal.json"
    journal.write_bytes(b'{"schema_version":9,' + _SENTINEL.encode())
    tree = record_tree_digest(repository)

    findings = state_repair.classify(repository).findings

    assert [(finding.catalogue, finding.code) for finding in findings] == [("C07", "journal-invalid")]
    assert "state-migration-incomplete" in [refusal.code for refusal in scan_capability(repository).refusals]
    _refused("repair-verify-mismatch", lambda: state_repair.verify(repository, proposal_id, processes=_none))
    _refused("repair-corruption-stop", lambda: state_repair.resume(repository, proposal_id, processes=_none))
    assert record_tree_digest(repository) == tree
    state_repair.abort(repository, proposal_id, processes=_none)
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original
    assert not _namespace(repository).exists()


def test_a_verified_repair_pending_its_archive_still_lets_the_controller_start(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal_id = _repair_at(repository, "verified")

    _available(repository, _CHANGES)

    state_repair.verify(repository, proposal_id, processes=_none)
    assert not _namespace(repository).exists()


def test_rollback_releases_read_a_verified_repair_on_format_0_state_as_before(tmp_path: Path) -> None:
    assert (
        hashlib.sha1(  # noqa: S324 - Git blob identity of the vendored N02-B gate.
            b"blob %d\0" % _N02B_GATE.stat().st_size + _N02B_GATE.read_bytes()
        ).hexdigest()
        == _N02B_GATE_BLOB
    )
    repository = _repository(tmp_path, marked=False)
    _downgrade_coordination(repository)
    assert _n02a_refusals(repository) == []
    pre_n02b = _n02b_refusals(repository)
    _namespace(repository).mkdir()
    assert _n02a_refusals(repository) == [["state-migration-incomplete", "runtime/migrations"]]
    _namespace(repository).rmdir()

    proposal = _c01(repository)
    _apply(repository, proposal)
    state_repair.verify(repository, proposal.proposal_id, processes=_none)

    assert not _namespace(repository).exists()
    assert _n02a_refusals(repository) == []
    assert _n02b_refusals(repository) == pre_n02b


def test_abort_of_a_first_repair_on_format_0_state_leaves_every_release_reading_it_as_before(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    _downgrade_coordination(repository)
    original = _corrupt_host_local(repository)
    pre_n02a, pre_n02b = _n02a_refusals(repository), _n02b_refusals(repository)
    proposal = state_repair.propose(repository, _C01)
    _apply(repository, proposal)

    state_repair.abort(repository, proposal.proposal_id, processes=_none)

    assert _n02a_refusals(repository) == pre_n02a
    assert _n02b_refusals(repository) == pre_n02b
    assert not _namespace(repository).exists()
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original


def test_a_migration_abort_archive_pending_cleanup_routes_to_delivery_migrate(tmp_path: Path) -> None:
    repository = _repository(tmp_path, marked=False)
    _downgrade_coordination(repository)
    migration = state_migration.propose(repository)
    with pytest.raises(_Crash):
        state_migration.apply(repository, migration.migration_id, failure=_crash_at("after-backup"))
    with pytest.raises(_Crash):
        state_migration.abort(repository, migration.migration_id, failure=_crash_at("abort-after-f"))
    tree = record_tree_digest(repository)

    findings = [
        finding
        for finding in state_repair.classify(repository).findings
        if finding.code == "migration-namespace-cleanup"
    ]

    assert [finding.operation for finding in findings] == [f"delivery-migrate abort {migration.migration_id}"]
    for operation in (state_repair.verify, state_repair.abort):
        _refused(
            "repair-not-supported",
            lambda operation=operation: operation(repository, migration.migration_id, processes=_none),
        )
    assert record_tree_digest(repository) == tree
    state_migration.abort(repository, migration.migration_id)
    assert not _namespace(repository).exists()
    assert _n02a_refusals(repository) == []


@pytest.mark.parametrize("shape", ["retained-journal", "entry", "symlink", "file"])
@pytest.mark.parametrize("command", ["verify", "abort"])
def test_namespace_cleanup_preserves_anything_but_a_real_empty_directory(
    tmp_path: Path, shape: str, command: str
) -> None:
    repository = _repository(tmp_path)
    proposal_id = _repair_at(repository, "archived-verified" if command == "verify" else "archived-aborted")
    namespace = _namespace(repository)
    namespace.rmdir()
    target = tmp_path / "elsewhere"
    target.mkdir()
    if shape == "retained-journal":
        (namespace / ("d" * 64)).mkdir(parents=True)
        journal = state_migration.MigrationJournal(
            migration_id="d" * 64, state="verified", source_format=0, target_format=1, backup_manifest_sha256="e" * 64
        )
        (namespace / ("d" * 64) / "journal.json").write_bytes(journal.canonical_bytes())
    elif shape == "entry":
        namespace.mkdir()
        (namespace / "unrelated").write_text("keep\n", encoding="utf-8")
    elif shape == "symlink":
        namespace.symlink_to(target, target_is_directory=True)
    else:
        namespace.write_text("not a directory\n", encoding="utf-8")
    before = os.lstat(namespace)
    tree = record_tree_digest(repository)

    getattr(state_repair, command)(repository, proposal_id, processes=_none)

    after = os.lstat(namespace)
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert record_tree_digest(repository) == tree
    if shape == "retained-journal":
        assert not [refusal for refusal in scan_capability(repository).refusals if "migrations" in refusal.locator]


# ---------------------------------------------------------------------------
# Controller exclusion (I1) with real processes and D12 records
# ---------------------------------------------------------------------------


_SLEEP = "import time; time.sleep(60)"


def _stand_in(repository: Path, form: str, tmp_path: Path) -> subprocess.Popen[bytes]:
    """Start a process that only sleeps but has the argument vector of one supported controller form."""
    python = sys.executable
    if form in {"module-mcp", "module-cockpit"}:
        module = "owlbear_delivery_mcp" if form == "module-mcp" else "owlbear_cockpit"
        package = repository / module
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "__main__.py").write_text(_SLEEP + "\n", encoding="utf-8")
        argv = [python, "-m", module]
    elif form == "cockpit-script":
        argv = ["bash", "-c", f'exec -a {tmp_path}/venv/bin/cockpit "{python}" -c "{_SLEEP}"']
    elif form == "uv-run":
        argv = [
            "bash",
            "-c",
            f'exec -a uv "{python}" -c "{_SLEEP}" run --project /clone python -m owlbear_delivery_mcp',
        ]
    else:
        launcher = repository / ".owlbear/controller/bin/delivery-mcp"
        launcher.parent.mkdir(parents=True)
        launcher.write_text("#!/bin/sh\nsleep 60\n", encoding="utf-8")
        launcher.chmod(0o755)
        argv = [str(launcher)]
    process = subprocess.Popen(argv, cwd=repository)  # noqa: S603 - fixed stand-in argument vectors.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if state_migration.supported_controller_form(tuple(psutil.Process(process.pid).cmdline())):
                return process
        except psutil.Error:
            pass
        time.sleep(0.05)
    process.kill()
    pytest.fail(f"stand-in {form} did not start")


def _only(pid: int) -> Callable[[], list[object]]:
    return lambda: [view for view in state_migration.psutil_controller_processes() if view.pid == pid]


@pytest.mark.parametrize("form", ["module-mcp", "module-cockpit", "cockpit-script", "uv-run", "launcher"])
def test_every_supported_controller_form_in_the_workspace_refuses_every_writing_command(
    tmp_path: Path, form: str
) -> None:
    repository = _repository(tmp_path, marked=False)
    proposal_id = _repair_at(repository, "applied")
    tree = record_tree_digest(repository)
    journal = _live_journal(repository, proposal_id)
    process = _stand_in(repository, form, tmp_path)
    try:
        for command in ("resume", "verify", "abort"):
            _refused(
                "repair-controller-running",
                lambda command=command: getattr(state_repair, command)(
                    repository, proposal_id, processes=_only(process.pid)
                ),
            )
        _refused(
            "repair-controller-running",
            lambda: state_repair.apply(repository, proposal_id, confirm=proposal_id, processes=_only(process.pid)),
        )
    finally:
        process.kill()
        process.wait()
    assert record_tree_digest(repository) == tree
    assert _live_journal(repository, proposal_id) == journal


def test_an_unreadable_candidate_cmdline_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository = _repository(tmp_path)
    proposal_id = _repair_at(repository, "applied")
    process = _stand_in(repository, "module-mcp", tmp_path)
    original = psutil.Process.cmdline

    def cmdline(self: psutil.Process) -> list[str]:
        if self.pid == process.pid:
            raise psutil.AccessDenied(self.pid)
        return original(self)

    monkeypatch.setattr(psutil.Process, "cmdline", cmdline)
    try:
        _refused(
            "repair-controller-unknown",
            lambda: state_repair.verify(repository, proposal_id, processes=_only(process.pid)),
        )
    finally:
        process.kill()
        process.wait()
    assert _live_journal(repository, proposal_id).state == "applied"  # type: ignore[union-attr]


def _publish_record(repository: Path, pid: int, create_time: float, cmdline: list[str]) -> Path:
    path = _delivery(repository) / f"runtime/controller-processes/{pid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(controller_process_record_bytes(pid, create_time, cmdline))
    return path


@pytest.mark.parametrize("record", ["other-pid", "other-create-time", "other-cmdline", "unreadable", "matching"])
def test_no_d12_record_exempts_a_running_controller(tmp_path: Path, record: str) -> None:
    """Process metadata is same-user writable: even an exactly matching record never exempts (I1, D12 deferred)."""
    repository = _repository(tmp_path)
    proposal_id = _repair_at(repository, "applied")
    process = _stand_in(repository, "module-cockpit", tmp_path)
    try:
        observed = psutil.Process(process.pid)
        pid, created, argv = process.pid, observed.create_time(), observed.cmdline()
        if record == "other-pid":
            _publish_record(repository, pid + 100_000, created, argv)
        elif record == "other-create-time":
            _publish_record(repository, pid, created + 5, argv)
        elif record == "other-cmdline":
            _publish_record(repository, pid, created, [*argv, "--extra"])
        elif record == "unreadable":
            _publish_record(repository, pid, created, argv).write_bytes(b"{" + _SENTINEL.encode())
        else:
            _publish_record(repository, pid, created, argv)
        _refused(
            "repair-controller-running",
            lambda: state_repair.verify(repository, proposal_id, processes=_only(process.pid)),
        )
    finally:
        process.kill()
        process.wait()
    assert _live_journal(repository, proposal_id).state == "applied"  # type: ignore[union-attr]


def test_a_controller_started_after_the_fence_scan_is_refused_before_the_next_write(tmp_path: Path) -> None:
    """The pre-write scan closes the window an ungated controller started after the fence scan would use."""
    repository = _repository(tmp_path)
    original = _corrupt_host_local(repository)
    proposal = state_repair.propose(repository, _C01)
    started: list[subprocess.Popen[bytes]] = []

    def start_controller(point: str) -> None:
        if point == "after-backup":
            started.append(_stand_in(repository, "module-mcp", tmp_path))

    def processes() -> list[object]:
        pids = {process.pid for process in started}
        return [view for view in state_migration.psutil_controller_processes() if view.pid in pids]

    try:
        _refused(
            "repair-controller-running",
            lambda: state_repair.apply(
                repository,
                proposal.proposal_id,
                confirm=proposal.proposal_id,
                processes=processes,
                failure=start_controller,
            ),
        )
        assert started
        assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == original
        assert _live_journal(repository, proposal.proposal_id).state == "backed-up"  # type: ignore[union-attr]
    finally:
        for process in started:
            process.kill()
            process.wait()
    state_repair.resume(repository, proposal.proposal_id, processes=processes)
    assert (_delivery(repository) / "runtime/host.local.json").read_bytes() == CANONICAL_HOST_LOCAL


class _UngatedController:
    """An ungated controller as the process scan sees it: supported form, cwd in the workspace."""

    pid = 4_000_000
    name = "python3"

    def __init__(self, cwd: Path) -> None:
        self._cwd = cwd

    @staticmethod
    def cmdline() -> tuple[str, ...]:
        return ("python3", "-m", "owlbear_delivery_mcp")

    def cwd(self) -> Path:
        return self._cwd


class _StartsWhen:
    """Process source of the pre-write guard: the controller appears once ``condition`` holds, until stopped."""

    def __init__(self, repository: Path, condition: Callable[[], bool]) -> None:
        self._repository, self._condition, self.stopped = repository, condition, False

    def __call__(self) -> list[object]:
        if self.stopped or not self._condition():
            return []
        return [_UngatedController(self._repository)]


@pytest.mark.parametrize("point", ["second-participant", "move-source", "manifest-cleanup", "contained-cleanup"])
def test_a_controller_started_between_replay_writes_is_refused_before_the_next_one(tmp_path: Path, point: str) -> None:
    """A1: C03 rescans before every participant write, move-source removal and manifest cleanup of a replay."""
    repository = _repository(tmp_path, marked=False)
    runtime = _delivery(repository) / "runtime"
    if point == "contained-cleanup":
        manifest = _contained_manifest(repository)
        report = manifest.parent.parent / "notes/report.json"
        expected: dict[str, bytes | None] = {}
        condition = report.exists
    else:
        host = (runtime / "host.json").read_bytes()
        expected = _pending_runtime_and_packages(repository)
        manifest = runtime / "transactions/repair-fixture-a.yaml"
        source, moved = runtime / "notes/source.json", runtime / "notes/moved.json"
        condition = {
            "second-participant": (runtime / "notes/created.json").exists,
            "move-source": moved.exists,
            "manifest-cleanup": lambda: moved.exists() and not source.exists(),
        }[point]
    proposal = state_repair.propose(repository, "C03:transactions")
    processes = _StartsWhen(repository, condition)

    _refused(
        "repair-controller-running",
        lambda: state_repair.apply(repository, proposal.proposal_id, processes=processes),
    )

    assert manifest.exists()
    assert _live_journal(repository, proposal.proposal_id).state == "applying"  # type: ignore[union-attr]
    if point == "second-participant":
        assert (runtime / "host.json").read_bytes() == host
        assert not moved.exists()
    elif point == "move-source":
        assert source.read_bytes() == b'{"moved":true}\n'
    processes.stopped = True
    state_repair.resume(repository, proposal.proposal_id, processes=processes)
    state_repair.verify(repository, proposal.proposal_id, processes=processes)
    assert not manifest.exists()
    assert _state(repository, expected) == expected
    if point == "contained-cleanup":
        assert report.read_bytes() == b'{"r":1}\n'


def test_supported_forms_are_recognized_and_others_are_not() -> None:
    supported = (
        ("python3", "-m", "owlbear_delivery_mcp"),
        ("/x/.venv/bin/python", "-m", "owlbear_cockpit.main"),
        ("uv", "run", "python", "-m", "owlbear_delivery_mcp"),
        ("uv", "--project", "/clone", "run", "python", "-m", "owlbear_delivery_mcp"),
        ("uv", "run", "cockpit"),
        ("/x/.venv/bin/cockpit",),
        ("/x/.venv/bin/python", "/x/.venv/bin/cockpit"),
        ("/bin/sh", "/w/.owlbear/controller/bin/delivery-mcp"),
        ("/w/.owlbear/controller/bin/cockpit",),
    )
    unsupported = (
        ("python3", "-m", "pytest"),
        ("uv", "run", "delivery-repair", "apply"),
        ("grep", "cockpit"),
        ("python3", "script.py", "cockpit"),
        (),
    )

    assert all(state_migration.supported_controller_form(argv) for argv in supported)
    assert not any(state_migration.supported_controller_form(argv) for argv in unsupported)


# ---------------------------------------------------------------------------
# Registry, source scan and V20 guards
# ---------------------------------------------------------------------------


_RECOVERY_CALLS = frozenset({"recover_all", "recover_contained"})


def recovery_call_sites(module: str, source: str) -> set[str]:
    """Return ``module:Class.method`` for every ``RuntimeTransaction`` recovery call in one module."""
    sites: set[str] = set()

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                visit(child, (*scope, child.name))
                continue
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr in _RECOVERY_CALLS
            ):
                sites.add(f"{module}:{'.'.join(scope)}")
            visit(child, scope)

    visit(ast.parse(source), ())
    return sites


def _delivery_call_sites() -> set[str]:
    package = Path(owlbear_delivery.__file__).parent
    sites: set[str] = set()
    for path in sorted(package.glob("*.py")):
        if path.name == "runtime_transaction.py":
            continue
        sites |= recovery_call_sites(f"owlbear_delivery.{path.stem}", path.read_text(encoding="utf-8"))
    return sites


def test_every_transaction_recovery_call_site_is_in_the_root_map() -> None:
    mapped = {site for root in TRANSACTION_ROOTS for site in root.call_sites}

    assert _delivery_call_sites() == mapped


def test_the_source_scan_reports_an_unmapped_recovery_call_site() -> None:
    synthetic = textwrap.dedent(
        """
        class Store:
            def read(self):
                RuntimeTransaction.recover_contained(self._root, descriptor)
        """
    )
    mapped = {site for root in TRANSACTION_ROOTS for site in root.call_sites}

    assert recovery_call_sites("owlbear_delivery.synthetic", synthetic) - mapped == {
        "owlbear_delivery.synthetic:Store.read"
    }


def test_a_receipt_whose_stored_id_does_not_match_its_bytes_is_contained(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    admission = _delivery(repository) / "runtime/changes/change-a/admission.json"
    receipt = json.loads(admission.read_bytes())
    receipt["integration_target"] = "other"
    admission.write_bytes(json.dumps(receipt).encode())
    tree = record_tree_digest(repository)

    findings = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}

    assert findings["C07:runtime/changes/change-a/admission.json"].route == "contained"
    assert all(finding.catalogue == "C07" for finding in findings.values())
    _refused(
        "repair-not-supported",
        lambda: state_repair.propose(repository, "C07:runtime/changes/change-a/admission.json"),
    )
    assert record_tree_digest(repository) == tree


@pytest.mark.parametrize("identity", ["valid", "renamed", "altered"])
def test_a_completion_receipt_with_an_invalid_identity_is_contained(tmp_path: Path, identity: str) -> None:
    repository = _repository(tmp_path)
    completions = _delivery(repository) / "runtime/completions/delivery-runtime"
    shutil.copytree(_FIXTURES / "golden/runtime/completions/delivery-runtime", completions)
    (receipt,) = (path for path in completions.glob("*.json") if path.name != "display.json")
    if identity == "renamed":
        receipt.rename(receipt.with_name(f"{'e' * 64}.json"))
    elif identity == "altered":
        payload = json.loads(receipt.read_bytes())
        payload["accepted_target_ref"] = "refs/heads/other"
        receipt.write_bytes(_canonical_json(payload))
    tree = record_tree_digest(repository)

    findings = {finding.finding_id: finding for finding in state_repair.classify(repository).findings}

    if identity == "valid":
        assert findings == {}
        return
    assert findings["C07:runtime/completions/delivery-runtime"].scope == "delivery-runtime"
    assert all(finding.catalogue == "C07" for finding in findings.values())
    _refused(
        "repair-not-supported", lambda: state_repair.propose(repository, "C07:runtime/completions/delivery-runtime")
    )
    assert record_tree_digest(repository) == tree


def test_a_missing_change_worktree_routes_to_its_online_recovery_without_a_write(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    shutil.rmtree(_delivery(repository) / "worktrees/change-b")
    tree = record_tree_digest(repository)

    report = state_repair.classify(repository)

    assert [(item.finding_id, item.route, item.operation, item.scope) for item in report.findings] == [
        ("C06:worktrees/change-b", "online", "recover_change_worktree", "change-b")
    ]
    assert [item.finding_id for item in state_repair.classify(repository, "change-a").findings] == []
    _refused("repair-not-supported", lambda: state_repair.propose(repository, "C06:worktrees/change-b"))
    assert record_tree_digest(repository) == tree


def _recording_git(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []
    original = subprocess.run

    def run(argv: tuple[str, ...], *args: object, **kwargs: object) -> object:
        calls.append(tuple(str(item) for item in argv))
        return original(argv, *args, **kwargs)  # type: ignore[call-overload]

    monkeypatch.setattr(state_repair.subprocess, "run", run)
    return calls


def _no_remote_git(calls: list[tuple[str, ...]]) -> bool:
    return not any({"fetch", "ls-remote", "push", "pull"} & set(call) for call in calls)


def test_an_out_of_band_change_head_routes_to_its_online_recovery_without_a_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    coordination = json.loads((_delivery(repository) / "runtime/coordination/changes/change-b.json").read_bytes())
    branch, reviewed = coordination["branch"], coordination["last_reviewed_commit"]
    head_tree = _git(repository, "rev-parse", f"{reviewed}^{{tree}}")
    moved = _git(repository, "commit-tree", head_tree, "-p", reviewed, "-m", "out of band")
    _git(repository, "update-ref", f"refs/heads/{branch}", moved, reviewed)
    tree = record_tree_digest(repository)
    calls = _recording_git(monkeypatch)

    report = state_repair.classify(repository)

    assert [(item.finding_id, item.route, item.operation, item.scope) for item in report.findings] == [
        ("C06:change-b/out-of-band-head", "online", "recover_out_of_band_head", "change-b")
    ]
    assert _no_remote_git(calls)
    assert state_repair.classify(repository, "change-a").findings == ()
    _refused("repair-not-supported", lambda: state_repair.propose(repository, "C06:change-b/out-of-band-head"))
    assert record_tree_digest(repository) == tree
    assert _git(repository, "rev-parse", f"refs/heads/{branch}") == moved
    monkeypatch.undo()
    application = load_delivery_application(_startup_config(), workspace_root=repository)
    try:
        reasons = {(item.change_id, item.reason) for item in application.delivery_health().diagnostics}
    finally:
        close_delivery_application(application)
    assert ("change-b", "local-change-head-out-of-band") in reasons


def test_an_unknown_publication_baseline_routes_to_its_online_recovery_without_a_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _repository(tmp_path)
    frontier = _delivery(repository) / "runtime/changes/change-b/frontier.json"
    payload = json.loads(frontier.read_bytes())
    disposition = DeliveryChangeDisposition.create(
        kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
        change_id="change-b",
        entered_from=DeliveryChangeStage.BUILDING,
        recorded_at=datetime(2026, 10, 4, tzinfo=UTC),
        diagnostics=("publication-baseline-unavailable", f"exact-head:{'a' * 40}"),
    )
    payload["change_disposition"] = disposition.model_dump(mode="json")
    frontier.write_bytes(json.dumps(payload).encode())
    tree = record_tree_digest(repository)
    calls = _recording_git(monkeypatch)

    report = state_repair.classify(repository)

    assert [(item.finding_id, item.route, item.operation, item.scope) for item in report.findings] == [
        ("C06:change-b/publication-baseline", "online", "recover_publication_baseline", "change-b")
    ]
    assert _no_remote_git(calls)
    _refused("repair-not-supported", lambda: state_repair.propose(repository, "C06:change-b/publication-baseline"))
    assert record_tree_digest(repository) == tree


def test_remote_only_attention_is_named_as_an_online_check_without_a_remote_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Snapshot quarantine, frontier mismatch, remote head mismatch and target-sync publication need remote reads."""
    repository = _repository(tmp_path)
    calls = _recording_git(monkeypatch)

    report = state_repair.classify(repository)

    assert report.findings == ()
    assert {(check.condition, check.operation) for check in report.online_checks} == {
        ("remote-snapshot-quarantined", "repair_quarantined_delivery_state_snapshot"),
        ("local-frontier-mismatch", "repair_delivery_state_snapshot"),
        ("remote-change-head-mismatch", "recover_out_of_band_head"),
        ("target-sync-publication", "repair_target_sync_publication"),
    }
    assert all(check.reason.startswith("needs online check:") for check in report.online_checks)
    assert _no_remote_git(calls)
    shutil.rmtree(_delivery(repository) / "runtime/changes")
    assert state_repair.classify(repository).online_checks == ()


def test_an_explicit_unsupported_host_local_version_is_contained_before_any_proposal(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (_delivery(repository) / "runtime/host.local.json").write_bytes(b'{"schema_version":0}\n')
    tree = record_tree_digest(repository)

    report = state_repair.classify(repository)

    assert [(item.finding_id, item.code) for item in report.findings] == [
        ("C07:runtime/host.local.json", "record-unknown-version")
    ]
    for finding_id in (_C01, "C07:runtime/host.local.json"):
        _refused("repair-not-supported", lambda finding_id=finding_id: state_repair.propose(repository, finding_id))
    assert record_tree_digest(repository) == tree
    assert not (repository / ".owlbear/delivery-migrations").exists()


@pytest.mark.parametrize("version", [1, 2])
def test_a_truncated_supported_version_verified_journal_refuses_start(tmp_path: Path, version: int) -> None:
    repository = _repository(tmp_path)
    journal_id = "c" * 64
    payload = {"schema_version": version, "migration_id": journal_id, "state": "verified"}
    if version == 2:
        payload["kind"] = "repair"
    journal = _namespace(repository) / journal_id / "journal.json"
    journal.parent.mkdir(parents=True)
    journal.write_bytes(_canonical_json(payload) + b"\n")

    refusals = [(refusal.code, refusal.locator) for refusal in scan_capability(repository).refusals]

    assert refusals == [("state-migration-incomplete", f"runtime/migrations/{journal_id}/journal.json")]
    assert [finding.code for finding in state_repair.classify(repository).findings] == ["journal-invalid"]
    complete = state_migration.MigrationJournal(
        migration_id=journal_id, state="verified", source_format=0, target_format=1, backup_manifest_sha256="e" * 64
    )
    journal.write_bytes(complete.canonical_bytes())
    assert scan_capability(repository).refusals == ()


def test_no_repair_path_writes_request_provenance() -> None:
    for module in (state_repair, state_migration):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        writes = [
            node
            for node in ast.walk(tree)
            if (isinstance(node, ast.keyword) and node.arg == "provenance")
            or (
                isinstance(node, ast.Subscript)
                and isinstance(node.ctx, ast.Store)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == "provenance"
            )
            or (
                isinstance(node, ast.Dict)
                and any(isinstance(key, ast.Constant) and key.value == "provenance" for key in node.keys)
            )
        ]
        assert writes == [], module.__name__


def test_repair_modules_never_construct_the_application() -> None:
    for module in (state_repair,):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "load_delivery_application" not in source.replace("``load_delivery_application``", "")
        assert "PortfolioApplication(" not in source


def test_output_has_no_record_value_or_absolute_path(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    proposal = _c01(repository)
    rendered = json.dumps(
        [
            [finding.as_dict() for finding in state_repair.classify(repository).findings],
            proposal.model_dump(mode="json"),
        ]
    )

    assert _SENTINEL not in rendered
    assert str(tmp_path) not in rendered
    assert str(tmp_path.resolve()) not in rendered
