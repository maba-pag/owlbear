"""Fenced migration contracts (N02-B): propose, apply, resume, verify, abort and the format marker."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from serve.delivery.tests.test_draft_pull_request import _Provider
from serve.delivery.tests.test_portfolio_application import (
    _continuation_request,
    _execute_engine,
    _finalizer_settlement,
    _planning_decision_block,
    _seed_loader_composed_completed_change,
    _startup_config,
)

from owlbear_delivery import close_delivery_application, load_delivery_application, state_migration
from owlbear_delivery.application_models import DeliveryUnavailableChangeView
from owlbear_delivery.change_workspace import PortfolioCoordinator
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    DeliveryStateVersionError,
    load_configured_delivery_application,
    load_verification_application,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryBuilderInvocationSettlement,
    DeliveryRuntime,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    RetryDelivery,
)
from owlbear_delivery.finalization_reports import (
    FinalizationFailureCode,
    FinalizationReport,
    ReportFinalizationFailure,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant, write_contained
from owlbear_delivery.state_formats import (
    FORMAT_MARKER,
    RECORD_KINDS,
    format_marker_bytes,
    record_tree_digest,
    scan_capability,
)
from owlbear_delivery.state_migration import MigrationError, MigrationJournal
from owlbear_delivery.storage_io import (
    ReadOnlyStateError,
    acquire_controller_lock,
    atomic_write,
    read_only_state,
    state_is_read_only,
)
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery import PortfolioApplication

_FIXTURES = Path(__file__).with_name("fixtures") / "state_formats"
# Byte copy of the merged N02-A gate (`8d2176927:serve/delivery/src/owlbear_delivery/state_formats.py`).
_N02A_GATE = _FIXTURES / "n02a_state_formats.py.txt"
_N02A_GATE_BLOB = "f28b5f51d1a5bc428c5d0fd313ff8e3372c8e22d"
_N02A_SCAN = """
import importlib.machinery, importlib.util, json, sys
from pathlib import Path
loader = importlib.machinery.SourceFileLoader("n02a_state_formats", sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = module
loader.exec_module(module)
report = module.scan_capability(Path(sys.argv[2]))
print(json.dumps([[refusal.code, refusal.locator] for refusal in report.refusals]))
"""
_STEP = """
import os, sys
from pathlib import Path
from owlbear_delivery import state_migration
operation, root, migration_id, crash = sys.argv[1:5]
def hook(point):
    if point == crash:
        os._exit(17)
kwargs = {"failure": hook}
if operation in {"apply", "resume"}:
    kwargs["batch_size"] = 1
try:
    getattr(state_migration, operation)(Path(root), migration_id, **kwargs)
except state_migration.MigrationError as exc:
    print("REFUSED", exc.code)
    sys.exit(3)
print("OK")
"""
_CRASHED = 17


class _Crash(BaseException):
    """Injected process death at one durable boundary."""


def _crash_at(point: str):
    def hook(observed: str) -> None:
        if observed == point:
            raise _Crash(point)

    return hook


def _n02a_refusals(repository: Path) -> list[list[str]]:
    completed = subprocess.run(  # noqa: S603 - fixed interpreter, vendored gate and argument vector.
        (sys.executable, "-I", "-c", _N02A_SCAN, str(_N02A_GATE), str(repository)),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _step(operation: str, repository: Path, migration_id: str, crash: str = "") -> subprocess.CompletedProcess[str]:
    """Run one migration operation in a fresh process; ``crash`` kills it at that boundary."""
    return subprocess.run(  # noqa: S603 - fixed interpreter and argument vector.
        (sys.executable, "-c", _STEP, operation, str(repository), migration_id, crash),
        check=False,
        capture_output=True,
        text=True,
    )


def _seed(tmp_path: Path, stages: tuple[tuple[str, DeliveryStage], ...] | None = None) -> Path:
    """Seed a D03-format (format 0, no marker) portfolio through the real owners."""
    stages = stages or (("change-a", DeliveryStage.COMPLETED), ("change-b", DeliveryStage.PLANNING))
    repository, _runtime_root = _seed_loader_composed_completed_change(tmp_path, stages, marked=False)
    return repository


def _frontier_path(repository: Path, change_id: str) -> Path:
    return repository / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"


def _make_schema_17(repository: Path, change_id: str) -> bytes:
    path = _frontier_path(repository, change_id)
    payload = json.loads(path.read_bytes())
    payload["schema_version"] = 17
    for binding in payload["bindings"]:
        binding.pop("retry_count", None)
        binding.pop("retry_fingerprint", None)
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    return raw


def _load(repository: Path):
    return load_delivery_application(_startup_config(), workspace_root=repository)


def _assert_refused(repository: Path, code: str) -> DeliveryStateVersionError:
    digests = record_tree_digest(repository)
    with pytest.raises(DeliveryStateVersionError) as refusal:
        load_configured_delivery_application(
            repository, lambda path: DeliveryStartupConfig.model_validate_json(path.read_bytes())
        )
    assert refusal.value.code == code
    assert record_tree_digest(repository) == digests
    return refusal.value


def _available(repository: Path, change_ids: tuple[str, ...]) -> dict[str, object]:
    application = _load(repository)
    try:
        views = {change_id: application.get_change(change_id) for change_id in change_ids}
        assert not [change_id for change_id, view in views.items() if isinstance(view, DeliveryUnavailableChangeView)]
        return {change_id: view.readiness.reason_code for change_id, view in views.items()}  # type: ignore[union-attr]
    finally:
        close_delivery_application(application)


def _migration_dir(repository: Path, migration_id: str) -> Path:
    return repository / ".owlbear/delivery-migrations" / migration_id


def _live_journal(repository: Path, migration_id: str) -> MigrationJournal | None:
    path = repository / ".owlbear/delivery/runtime/migrations" / migration_id / "journal.json"
    return MigrationJournal.model_validate_json(path.read_bytes()) if path.exists() else None


def _pending_manifests(repository: Path) -> list[str]:
    root = repository / ".owlbear/delivery/runtime/transactions"
    return sorted(path.name for path in root.glob("*.yaml")) if root.is_dir() else []


def _listing(root: Path) -> list[str]:
    return sorted(
        f"{path.relative_to(root)}:{'L' if path.is_symlink() else hashlib.sha256(path.read_bytes()).hexdigest()}"
        if path.is_file() or path.is_symlink()
        else str(path.relative_to(root))
        for path in root.rglob("*")
    )


def _write_config(repository: Path) -> None:
    config = repository / ".owlbear/delivery/config.json"
    config.write_text(_startup_config().model_dump_json(), encoding="utf-8")


def _attach_bare_remote(tmp_path: Path, repository: Path) -> None:
    """Resolve the configured GitHub remote to a disposable local bare repository."""
    remote = tmp_path / "remote.git"
    git = (resolve_git_executable(),)
    subprocess.run((*git, "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603
    for arguments in (
        ("config", f"url.{remote}.insteadOf", "https://github.com/example/project.git"),
        ("push", "origin", "HEAD:refs/heads/main"),
    ):
        subprocess.run((*git, "-C", str(repository), *arguments), check=True, capture_output=True)  # noqa: S603


# ---------------------------------------------------------------------------
# First migration (format 0 -> 1) and the format marker
# ---------------------------------------------------------------------------


def test_first_migration_on_format_0_state_writes_only_the_marker(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    pre = record_tree_digest(repository)
    refusal = _assert_refused(repository, "state-migration-required")

    proposal = state_migration.propose(repository)

    assert refusal.locator == FORMAT_MARKER
    assert [(entry.locator, entry.before_sha256) for entry in proposal.entries] == [(FORMAT_MARKER, None)]
    assert record_tree_digest(repository) == pre
    journal = state_migration.apply(repository, proposal.migration_id)
    assert journal.state == "applied"
    _assert_refused(repository, "state-migration-incomplete")
    assert state_migration.verify(repository, proposal.migration_id).state == "verified"
    post = record_tree_digest(repository, exclude_migrations=True)
    assert {locator: digest for locator, digest in post.items() if pre.get(locator) != digest} == {
        FORMAT_MARKER: hashlib.sha256(format_marker_bytes()).hexdigest()
    }
    manifest = json.loads((_migration_dir(repository, proposal.migration_id) / "backup/manifest.json").read_bytes())
    assert manifest["tree"] == pre
    assert manifest["records"] == {}
    _available(repository, ("change-a", "change-b"))
    assert not (repository / ".owlbear/delivery/state").exists()


def test_fresh_workspace_is_stamped_inside_the_fence_and_needs_no_migration(tmp_path: Path) -> None:
    repository = _seed(tmp_path, (("change-a", DeliveryStage.COMPLETED),))
    for path in sorted((repository / ".owlbear/delivery/runtime").rglob("*"), reverse=True):
        if path.is_dir():
            path.rmdir()
        else:
            path.unlink()
    _write_config(repository)
    assert scan_capability(repository).format_absent

    application = _load(repository)
    close_delivery_application(application)

    assert (repository / ".owlbear/delivery" / FORMAT_MARKER).read_bytes() == format_marker_bytes()
    with pytest.raises(MigrationError) as not_required:
        state_migration.propose(repository)
    assert not_required.value.code == "migration-not-required"
    assert ["state-newer-than-controller", FORMAT_MARKER] in _n02a_refusals(repository)


def test_schema_17_frontier_is_rewritten_by_the_registered_rewrite_and_staged_bytes_are_never_authority(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    legacy = _make_schema_17(repository, "change-a")
    pre = record_tree_digest(repository)
    before_scan = scan_capability(repository)

    proposal = state_migration.propose(repository)

    staged = _migration_dir(repository, proposal.migration_id) / "stage/runtime/changes/change-a/frontier.json"
    assert [entry.locator for entry in proposal.entries] == [
        "runtime/changes/change-a/frontier.json",
        FORMAT_MARKER,
    ]
    assert staged.read_bytes() == state_migration.frontier_17_to_18(legacy)
    assert json.loads(staged.read_bytes())["schema_version"] == 18
    assert record_tree_digest(repository) == pre
    assert scan_capability(repository) == before_scan
    _assert_refused(repository, "state-migration-required")
    state_migration.apply(repository, proposal.migration_id)
    state_migration.verify(repository, proposal.migration_id)
    assert _frontier_path(repository, "change-a").read_bytes() == staged.read_bytes()
    _available(repository, ("change-a", "change-b"))


def test_every_registered_rewrite_resolves_to_a_migration_function() -> None:
    names = {name for kind in RECORD_KINDS for _version, name in kind.rewrites}

    assert names == set(state_migration.REWRITES)
    assert names == {
        "owlbear_delivery.state_migration:frontier_17_to_18",
        "owlbear_delivery.state_migration:coordination_1_to_2",
    }


def test_frontier_invalid_at_its_declared_version_is_corruption_and_never_synthesized(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    path = _frontier_path(repository, "change-a")
    _make_schema_17(repository, "change-a")
    payload = json.loads(path.read_bytes())
    payload["bindings"][0]["requests"] = [
        {
            "kind": "action",
            "options": [],
            "outcome_id": "OUT-001",
            "request_id": "REQ-001",
            "summary": "Complete the pilot.",
            "resolution": {"response_text": "free text without provenance", "selected_option_id": None},
        }
    ]
    path.write_bytes(json.dumps(payload).encode())
    pre = record_tree_digest(repository)

    with pytest.raises(MigrationError) as corrupt:
        state_migration.propose(repository)

    assert corrupt.value.code == "record-corrupt"
    assert corrupt.value.locator == "runtime/changes/change-a/frontier.json"
    assert record_tree_digest(repository) == pre
    assert not (repository / ".owlbear/delivery-migrations").exists()


def test_runtime_refuses_a_schema_17_frontier_without_rewriting_it(tmp_path: Path) -> None:
    repository = _seed(tmp_path, (("change-a", DeliveryStage.COMPLETED),))
    legacy = _make_schema_17(repository, "change-a")
    runtime_root = repository / ".owlbear/delivery/runtime"
    contract = DeliveryContract.model_validate_json((runtime_root / "changes/change-a/contract.json").read_bytes())

    with pytest.raises(DeliveryRuntimeReferenceError, match="registered fenced migration"):
        DeliveryRuntime(runtime_root, contract)

    assert _frontier_path(repository, "change-a").read_bytes() == legacy


def _malformed_config(_original: bytes) -> bytes:
    return b'{"schema_version":2}'


def _malformed_admission(original: bytes) -> bytes:
    payload = json.loads(original)
    return json.dumps({"schema_version": payload["schema_version"]}, separators=(",", ":")).encode()


def _malformed_frontier(original: bytes) -> bytes:
    payload = json.loads(original)
    payload["bindings"] = "not-a-binding-list"
    return json.dumps(payload, separators=(",", ":")).encode()


@pytest.mark.parametrize(
    ("locator", "malform"),
    [
        ("config.json", _malformed_config),
        ("runtime/changes/change-a/admission.json", _malformed_admission),
        ("runtime/changes/change-b/frontier.json", _malformed_frontier),
    ],
    ids=["config", "admission", "frontier"],
)
def test_malformed_unchanged_record_at_its_current_version_refuses_propose_and_apply_without_writing(
    tmp_path: Path, locator: str, malform: Callable[[bytes], bytes]
) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    path = repository / ".owlbear/delivery" / locator
    original = path.read_bytes()
    path.write_bytes(malform(original))
    statuses = {record.status for record in scan_capability(repository).records if record.locator == locator}
    assert len(statuses) == 1
    assert statuses <= {"current", "readable-legacy"}
    digests = record_tree_digest(repository)

    with pytest.raises(MigrationError) as at_propose:
        state_migration.propose(repository)

    assert (at_propose.value.code, at_propose.value.locator) == ("record-corrupt", locator)
    assert record_tree_digest(repository) == digests
    assert not (repository / ".owlbear/delivery-migrations").exists()
    path.write_bytes(original)
    proposal = state_migration.propose(repository)
    path.write_bytes(malform(original))
    digests = record_tree_digest(repository)
    with pytest.raises(MigrationError) as at_apply:
        state_migration.apply(repository, proposal.migration_id)
    assert (at_apply.value.code, at_apply.value.locator) == ("record-corrupt", locator)
    assert record_tree_digest(repository) == digests
    assert not (_migration_dir(repository, proposal.migration_id) / "backup").exists()
    assert _live_journal(repository, proposal.migration_id) is None


@pytest.mark.parametrize("shape", ["noncanonical-current-frontier", "legacy-retry-accounting"])
def test_verify_reads_without_canonicalizing_reconciling_or_recovering_records(tmp_path: Path, shape: str) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    frontier = _frontier_path(repository, "change-b")
    payload = json.loads(frontier.read_bytes())
    if shape == "legacy-retry-accounting":
        payload["bindings"][0].update(retry_count=2, retry_fingerprint="a" * 64)
    frontier.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    raw = frontier.read_bytes()
    proposal = state_migration.propose(repository)
    assert [entry.locator for entry in proposal.entries] == [FORMAT_MARKER]
    state_migration.apply(repository, proposal.migration_id)
    applied = record_tree_digest(repository)
    listing = _listing(repository / ".owlbear/delivery/runtime/changes")

    assert state_migration.verify(repository, proposal.migration_id).state == "verified"

    assert frontier.read_bytes() == raw
    verified = record_tree_digest(repository)
    changed = {locator for locator in set(applied) | set(verified) if applied.get(locator) != verified.get(locator)}
    assert changed == {f"runtime/migrations/{proposal.migration_id}/journal.json"}
    assert _listing(repository / ".owlbear/delivery/runtime/changes") == listing


def test_read_only_scope_refuses_every_record_write_primitive_before_any_byte_changes(tmp_path: Path) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    participant = TransactionParticipant(root, Path("record.json"), b"{}\n")

    with read_only_state():
        assert state_is_read_only()
        with pytest.raises(ReadOnlyStateError):
            RuntimeTransaction(root, "read-only", (participant,)).commit()
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with pytest.raises(ReadOnlyStateError):
                write_contained(root_fd, Path("record.json"), b"{}\n")
        finally:
            os.close(root_fd)
        with pytest.raises(ReadOnlyStateError):
            atomic_write(root / "note.md", "text")

    assert not state_is_read_only()
    assert sorted(path.name for path in root.iterdir()) == []


def test_stage_and_backup_publications_fsync_their_parent_before_journal_or_record_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    _make_schema_17(repository, "change-a")
    events: list[tuple[str, object, tuple[str, ...]]] = []
    fsync, journal, commit = (
        state_migration._fsync_directory,  # noqa: SLF001 - the durability barrier under test.
        state_migration._write_live_journal,  # noqa: SLF001 - the journal write it must precede.
        RuntimeTransaction.commit,
    )

    def recorded_fsync(directory: Path) -> None:
        events.append(("fsync", directory.resolve(), tuple(sorted(path.name for path in directory.iterdir()))))
        fsync(directory)

    def recorded_journal(paths: object, written: MigrationJournal) -> None:
        events.append(("journal", written.state, ()))
        journal(paths, written)  # type: ignore[arg-type]

    def recorded_commit(transaction: RuntimeTransaction, **kwargs: object) -> None:
        events.append(("commit", None, ()))
        commit(transaction, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(state_migration, "_fsync_directory", recorded_fsync)
    monkeypatch.setattr(state_migration, "_write_live_journal", recorded_journal)
    monkeypatch.setattr(RuntimeTransaction, "commit", recorded_commit)
    owlbear = (repository / ".owlbear").resolve()

    proposal = state_migration.propose(repository)

    state_root = owlbear / "delivery-migrations"
    migration = state_root / proposal.migration_id
    assert ("fsync", owlbear) in [(kind, path) for kind, path, names in events if "delivery-migrations" in names]
    assert ("fsync", state_root) in [(kind, path) for kind, path, names in events if proposal.migration_id in names]
    events.clear()
    state_migration.apply(repository, proposal.migration_id, batch_size=1)
    published = next(
        index
        for index, (kind, path, names) in enumerate(events)
        if (kind, path) == ("fsync", migration) and "backup" in names
    )
    first_journal = next(index for index, (kind, _path, _names) in enumerate(events) if kind == "journal")
    first_commit = next(index for index, (kind, _path, _names) in enumerate(events) if kind == "commit")
    assert published < first_journal < first_commit


# ---------------------------------------------------------------------------
# Crash injection at each durable boundary, resume and verify (V21)
# ---------------------------------------------------------------------------


def _two_rewrites(tmp_path: Path) -> tuple[Path, state_migration.MigrationProposal]:
    repository = _seed(tmp_path)
    _write_config(repository)
    _make_schema_17(repository, "change-a")
    _make_schema_17(repository, "change-b")
    return repository, state_migration.propose(repository)


_APPLY_CRASHES = (
    "after-backup",
    "batch-0:before-publication",
    "batch-0:after-first-publication",
    "batch-0:before-manifest-cleanup",
    "after-replacement-0",
    "after-replacement-1",
    "before-marker",
    "batch-2:after-first-publication",
    "after-marker",
)


@pytest.mark.parametrize("crash", _APPLY_CRASHES)
def test_crash_at_each_apply_boundary_refuses_start_and_resume_converges(tmp_path: Path, crash: str) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    expected = {
        entry.locator: (_migration_dir(repository, proposal.migration_id) / "stage" / entry.locator).read_bytes()
        for entry in proposal.entries
    }

    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, batch_size=1, failure=_crash_at(crash))

    _assert_refused(repository, "state-migration-incomplete")
    with pytest.raises(MigrationError) as early_verify:
        state_migration.verify(repository, proposal.migration_id)
    assert early_verify.value.code == "journal-state"
    resumed = _step("resume", repository, proposal.migration_id)
    assert resumed.stdout.strip() == "OK", resumed.stderr
    journal = _live_journal(repository, proposal.migration_id)
    assert journal is not None
    assert journal.state == "applied"
    locators = [locator for batch in journal.batches for locator in batch.locators]
    assert sorted(locators) == sorted(expected)
    assert len(locators) == len(set(locators))
    assert _pending_manifests(repository) == []
    for locator, content in expected.items():
        assert (repository / ".owlbear/delivery" / locator).read_bytes() == content
    assert _step("resume", repository, proposal.migration_id).stdout.strip() == "OK"
    _assert_refused(repository, "state-migration-incomplete")
    state_migration.verify(repository, proposal.migration_id)
    _available(repository, ("change-a", "change-b"))


def test_crash_before_the_journal_leaves_state_unmigrated_and_a_retry_keeps_the_stale_backup(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    pre_n02a = _n02a_refusals(repository)
    proposal = state_migration.propose(repository)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, failure=_crash_at("before-journal"))

    _assert_refused(repository, "state-migration-required")
    assert _n02a_refusals(repository) == pre_n02a
    host = repository / ".owlbear/delivery/runtime/host.json"
    host.write_text('{"schema_version":1,"execution_capacity":2}', encoding="utf-8")
    assert state_migration.apply(repository, proposal.migration_id).state == "applied"
    directory = _migration_dir(repository, proposal.migration_id)
    assert len(list(directory.glob("backup-superseded-*/manifest.json"))) == 1
    manifest = json.loads((directory / "backup/manifest.json").read_bytes())
    assert manifest["tree"]["runtime/host.json"] == hashlib.sha256(host.read_bytes()).hexdigest()


def test_applied_journal_is_verified_offline_while_mcp_and_cockpit_loaders_still_refuse(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    state_migration.apply(repository, proposal.migration_id)
    applied = record_tree_digest(repository)

    refusal = _assert_refused(repository, "state-migration-incomplete")
    journal = state_migration.verify(repository, proposal.migration_id)

    assert refusal.locator == f"runtime/migrations/{proposal.migration_id}/journal.json"
    assert journal.state == "verified"
    changed = {locator for locator, digest in record_tree_digest(repository).items() if applied.get(locator) != digest}
    assert changed == {f"runtime/migrations/{proposal.migration_id}/journal.json"}
    assert state_migration.verify(repository, proposal.migration_id) == journal
    # A temporary left by an interrupted atomic journal write does not hide the verified journal.
    journal_directory = repository / ".owlbear/delivery/runtime/migrations" / proposal.migration_id
    (journal_directory / f".tmp-{'0' * 24}").write_bytes(b"{}")
    _available(repository, ("change-a", "change-b"))


def _alter_retry_accounting(repository: Path) -> tuple[Path, bytes]:
    path = _frontier_path(repository, "change-b")
    payload = json.loads(path.read_bytes())
    payload["bindings"][0].update(retry_count=2, retry_fingerprint="a" * 64)
    return path, (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _add_host_record(repository: Path) -> tuple[Path, bytes]:
    return repository / ".owlbear/delivery/runtime/host.json", b'{"schema_version":1,"execution_capacity":2}'


@pytest.mark.parametrize(
    ("alter", "locator"),
    [(_alter_retry_accounting, "runtime/changes/change-b/frontier.json"), (_add_host_record, "runtime/host.json")],
    ids=["altered-frontier", "added-record"],
)
def test_verify_refuses_an_applied_tree_changed_outside_the_journal_without_writing(
    tmp_path: Path, alter: Callable[[Path], tuple[Path, bytes]], locator: str
) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    state_migration.apply(repository, proposal.migration_id)
    path, content = alter(repository)
    original = path.read_bytes() if path.exists() else None
    path.write_bytes(content)
    digests = record_tree_digest(repository)

    with pytest.raises(MigrationError) as refused:
        state_migration.verify(repository, proposal.migration_id)

    assert (refused.value.code, refused.value.locator) == ("verify-tree-mismatch", locator)
    assert record_tree_digest(repository) == digests
    journal = _live_journal(repository, proposal.migration_id)
    assert journal is not None
    assert journal.state == "applied"
    if original is None:
        path.unlink()
    else:
        path.write_bytes(original)
    assert state_migration.verify(repository, proposal.migration_id).state == "verified"


def test_verification_mode_requires_the_exclusive_lock_and_the_named_applied_journal(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    state_migration.apply(repository, proposal.migration_id)
    runtime_root = repository / ".owlbear/delivery/runtime"

    def read_config(path: Path) -> DeliveryStartupConfig:
        return DeliveryStartupConfig.model_validate_json(path.read_bytes())

    shared = acquire_controller_lock(runtime_root)
    try:
        with pytest.raises(DeliveryApplicationLoadError) as fenced:
            load_verification_application(
                repository, read_config, migration_id=proposal.migration_id, controller_lock=shared
            )
    finally:
        shared.release()
    exclusive = acquire_controller_lock(runtime_root, exclusive=True)
    try:
        with pytest.raises(DeliveryStateVersionError) as other:
            load_verification_application(repository, read_config, migration_id="d" * 64, controller_lock=exclusive)
    finally:
        exclusive.release()

    assert fenced.value.code == "controller-fenced"
    assert other.value.code == "state-migration-incomplete"


def test_operations_refuse_without_writing_while_a_controller_holds_the_lock(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    holder = acquire_controller_lock(repository / ".owlbear/delivery/runtime")
    digests = record_tree_digest(repository)
    staged = _listing(repository / ".owlbear/delivery-migrations")
    try:
        for operation in (state_migration.apply, state_migration.verify, state_migration.abort, state_migration.resume):
            with pytest.raises(MigrationError) as refused:
                operation(repository, proposal.migration_id)
            assert refused.value.code == "controller-running"
    finally:
        holder.release()

    assert record_tree_digest(repository) == digests
    assert _listing(repository / ".owlbear/delivery-migrations") == staged


def test_stale_proposal_and_pending_transactions_are_refused_before_any_write(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    frontier = _frontier_path(repository, "change-b")
    original = frontier.read_bytes()
    frontier.write_bytes(original.replace(b'"schema_version":17', b'"schema_version": 17'))
    digests = record_tree_digest(repository)

    with pytest.raises(MigrationError) as stale:
        state_migration.apply(repository, proposal.migration_id)

    assert stale.value.code == "proposal-stale"
    assert stale.value.locator == "runtime/changes/change-b/frontier.json"
    assert record_tree_digest(repository) == digests
    assert not (_migration_dir(repository, proposal.migration_id) / "backup").exists()
    frontier.write_bytes(original)
    manifest = repository / ".owlbear/delivery/runtime/transactions/unrelated.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("schema_version: 1\nparticipants: []\n", encoding="utf-8")
    with pytest.raises(MigrationError) as pending:
        state_migration.apply(repository, proposal.migration_id)
    assert pending.value.code == "transactions-pending"
    assert _live_journal(repository, proposal.migration_id) is None


def test_third_digest_stops_resume_and_abort_as_corruption_preserving_both_copies(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, batch_size=1, failure=_crash_at("after-replacement-0"))
    frontier = _frontier_path(repository, "change-a")
    third = frontier.read_bytes() + b" "
    frontier.write_bytes(third)
    backup = _migration_dir(repository, proposal.migration_id) / "backup/records/runtime/changes/change-a/frontier.json"
    backed_up = backup.read_bytes()
    digests = record_tree_digest(repository)

    for operation in (state_migration.resume, state_migration.abort):
        with pytest.raises(MigrationError) as corrupt:
            operation(repository, proposal.migration_id)
        assert corrupt.value.code == "record-corrupt"

    assert frontier.read_bytes() == third
    assert backup.read_bytes() == backed_up
    journal = _live_journal(repository, proposal.migration_id)
    assert journal is not None
    assert journal.state == "aborting"
    assert record_tree_digest(repository, exclude_migrations=True) == {
        locator: digest for locator, digest in digests.items() if not locator.startswith("runtime/migrations/")
    }


def test_n02a_refuses_the_migrated_format_1_workspace_with_unchanged_hashes(tmp_path: Path) -> None:
    assert (
        hashlib.sha1(  # noqa: S324 - Git blob identity of the vendored N02-A gate.
            b"blob %d\0" % _N02A_GATE.stat().st_size + _N02A_GATE.read_bytes()
        ).hexdigest()
        == _N02A_GATE_BLOB
    )
    repository, proposal = _two_rewrites(tmp_path)
    # N09-A2: the older release already refuses coordination version 2 with its typed version diagnostic.
    assert _n02a_refusals(repository) == [
        ["state-newer-than-controller", f"runtime/coordination/changes/{change_id}.json"]
        for change_id in ("change-a", "change-b")
    ]
    state_migration.apply(repository, proposal.migration_id)
    state_migration.verify(repository, proposal.migration_id)
    digests = record_tree_digest(repository)

    refusals = _n02a_refusals(repository)

    assert ["state-migration-incomplete", "runtime/migrations"] in refusals
    assert ["state-newer-than-controller", FORMAT_MARKER] in refusals
    assert record_tree_digest(repository) == digests


# ---------------------------------------------------------------------------
# Pre-marker abort from durable state (steps a-g) and the D10 namespace
# ---------------------------------------------------------------------------


_ABORT_CRASHES = (
    "abort-after-a",
    "abort-after-b",
    "abort-after-c",
    "abort-after-d",
    "abort-after-e",
    "abort-after-archive",
)


@pytest.mark.parametrize("crash", _ABORT_CRASHES)
def test_pre_marker_abort_from_a_fresh_process_is_restartable_at_every_step(tmp_path: Path, crash: str) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    pre_n02a = _n02a_refusals(repository)
    pre = record_tree_digest(repository)
    with pytest.raises(_Crash):
        state_migration.apply(
            repository, proposal.migration_id, batch_size=1, failure=_crash_at("batch-0:after-first-publication")
        )
    assert _pending_manifests(repository) == [f"migration-{proposal.migration_id[:16]}-0000.yaml"]
    crashed = _step("abort", repository, proposal.migration_id, crash)
    assert crashed.returncode == _CRASHED, crashed.stdout + crashed.stderr
    _assert_refused(repository, "state-migration-incomplete")
    journal = _live_journal(repository, proposal.migration_id)
    assert journal is not None
    if journal.state == "aborting":
        with pytest.raises(MigrationError) as aborting_resume:
            state_migration.resume(repository, proposal.migration_id)
        assert aborting_resume.value.code == "journal-state"

    assert _step("abort", repository, proposal.migration_id).stdout.strip() == "OK"
    assert _step("abort", repository, proposal.migration_id).stdout.strip() == "OK"

    _assert_refused(repository, "state-migration-required")
    assert record_tree_digest(repository) == pre
    assert _pending_manifests(repository) == []
    RuntimeTransaction.recover_all(repository / ".owlbear/delivery/runtime")
    assert record_tree_digest(repository) == pre
    assert not (repository / ".owlbear/delivery/runtime/migrations").exists()
    directory = _migration_dir(repository, proposal.migration_id)
    assert (directory / "backup/manifest.json").is_file()
    assert json.loads((directory / "journal.json").read_bytes())["state"] == "aborted"
    assert (directory / f"retired-transactions/migration-{proposal.migration_id[:16]}-0000.yaml").is_file()
    assert _n02a_refusals(repository) == pre_n02a


def test_resume_of_an_aborting_journal_is_refused(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, batch_size=1, failure=_crash_at("after-replacement-0"))
    with pytest.raises(_Crash):
        state_migration.abort(repository, proposal.migration_id, failure=_crash_at("abort-after-b"))
    digests = record_tree_digest(repository)

    with pytest.raises(MigrationError) as refused:
        state_migration.resume(repository, proposal.migration_id)

    assert refused.value.code == "journal-state"
    assert record_tree_digest(repository) == digests


def test_abort_after_the_marker_is_refused_without_a_write(tmp_path: Path) -> None:
    repository, proposal = _two_rewrites(tmp_path)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, failure=_crash_at("after-marker"))
    digests = record_tree_digest(repository)

    with pytest.raises(MigrationError) as committed:
        state_migration.abort(repository, proposal.migration_id)

    assert committed.value.code == "marker-committed"
    assert record_tree_digest(repository) == digests


def test_namespace_cleanup_after_a_crash_following_the_archive_d10(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    assert not (repository / ".owlbear/delivery/runtime/migrations").exists()
    pre_n02a = _n02a_refusals(repository)
    proposal = state_migration.propose(repository)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, failure=_crash_at("after-backup"))
    with pytest.raises(_Crash):
        state_migration.abort(repository, proposal.migration_id, failure=_crash_at("abort-after-f"))
    namespace = repository / ".owlbear/delivery/runtime/migrations"
    assert namespace.is_dir()
    assert list(namespace.iterdir()) == []
    assert ["state-migration-incomplete", "runtime/migrations"] in _n02a_refusals(repository)

    first = state_migration.abort(repository, proposal.migration_id)
    assert first.namespace_removed
    assert _n02a_refusals(repository) == pre_n02a
    digests = record_tree_digest(repository)
    staged = _listing(repository / ".owlbear/delivery-migrations")
    second = state_migration.abort(repository, proposal.migration_id)

    assert not second.namespace_removed
    assert second.journal.state == "aborted"
    assert record_tree_digest(repository) == digests
    assert _listing(repository / ".owlbear/delivery-migrations") == staged
    for operation in (state_migration.resume, state_migration.verify, state_migration.apply):
        with pytest.raises(MigrationError) as archived:
            operation(repository, proposal.migration_id)
        assert archived.value.code == "migration-archived"
    with pytest.raises(MigrationError) as reproposed:
        state_migration.propose(repository)
    assert reproposed.value.code == "migration-archived"
    assert record_tree_digest(repository) == digests
    assert _listing(repository / ".owlbear/delivery-migrations") == staged


@pytest.mark.parametrize("shape", ["entry", "symlink", "file"])
def test_namespace_cleanup_preserves_anything_but_a_real_empty_directory(tmp_path: Path, shape: str) -> None:
    repository = _seed(tmp_path)
    _write_config(repository)
    proposal = state_migration.propose(repository)
    with pytest.raises(_Crash):
        state_migration.apply(repository, proposal.migration_id, failure=_crash_at("after-backup"))
    with pytest.raises(_Crash):
        state_migration.abort(repository, proposal.migration_id, failure=_crash_at("abort-after-f"))
    namespace = repository / ".owlbear/delivery/runtime/migrations"
    namespace.rmdir()
    target = tmp_path / "elsewhere"
    target.mkdir()
    if shape == "entry":
        namespace.mkdir()
        (namespace / "unrelated").write_text("keep\n", encoding="utf-8")
    elif shape == "symlink":
        namespace.symlink_to(target, target_is_directory=True)
    else:
        namespace.write_text("not a directory\n", encoding="utf-8")
    before = _listing(repository / ".owlbear/delivery/runtime")

    result = state_migration.abort(repository, proposal.migration_id)

    assert not result.namespace_removed
    assert _listing(repository / ".owlbear/delivery/runtime") == before
    assert target.is_dir()
    assert any(code == "state-migration-incomplete" for code, _locator in _n02a_refusals(repository))


# ---------------------------------------------------------------------------
# Custody shapes survive the migration (positive scenario)
# ---------------------------------------------------------------------------


def test_custody_shapes_stay_available_and_unchanged_across_the_migration(tmp_path: Path) -> None:
    stages = (
        ("change-a", DeliveryStage.PLANNING),
        ("change-b", DeliveryStage.IMPLEMENTATION),
        ("change-c", DeliveryStage.COMPLETED),
        ("change-d", DeliveryStage.COMPLETED),
    )
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path, stages)
    _attach_bare_remote(tmp_path, repository)
    application = load_delivery_application(
        _startup_config(), workspace_root=repository, publication_provider=_Provider()
    )
    _pause_planner(application, "change-a")
    _hand_off_builder(application, "change-b")
    _report_finalizer_attention(application, "change-c")
    before = {
        change_id: application.get_change(change_id).readiness.reason_code  # type: ignore[union-attr]
        for change_id, _stage in stages
    }
    close_delivery_application(application)
    coordinator = PortfolioCoordinator(runtime_root)
    assert coordinator.show("change-b").writer.kind == "handoff"  # type: ignore[union-attr]
    assert coordinator.show("change-c").finalization_attention is not None
    (repository / ".owlbear/delivery" / FORMAT_MARKER).unlink()
    _write_config(repository)
    pre = record_tree_digest(repository)
    _assert_refused(repository, "state-migration-required")

    proposal = state_migration.propose(repository)
    state_migration.apply(repository, proposal.migration_id)
    state_migration.verify(repository, proposal.migration_id)

    after = _available(repository, tuple(change_id for change_id, _stage in stages))
    # The Finalizer retry backoff is wall-clock based and may expire while the migration runs.
    assert {**after, "change-c": before["change-c"]} == before
    assert after["change-c"] in {before["change-c"], "ready"}
    post = record_tree_digest(repository, exclude_migrations=True)
    assert {locator for locator, digest in post.items() if pre.get(locator) != digest} == {FORMAT_MARKER}
    assert coordinator.show("change-b").writer.kind == "handoff"  # type: ignore[union-attr]
    assert coordinator.show("change-c").finalization_attention is not None


def _pause_planner(application: PortfolioApplication, change_id: str) -> None:
    planner = application.acquire_change_action(_continuation_request(application, change_id))
    assert planner.launch is not None, planner
    block = _planning_decision_block(planner.launch.claim.claim_id, 0)
    application.transition_delivery(change_id, block)


def _hand_off_builder(application: PortfolioApplication, change_id: str) -> None:
    acquired = application.acquire_change_action(_continuation_request(application, change_id))
    assert acquired.launch is not None, acquired
    builder = acquired.launch
    application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=builder.outcome_id,
            claim_id=builder.claim.claim_id,
            attempt_id=builder.claim.attempt_id,
            task_id=builder.task_id,
            expected_last_reviewed_commit=builder.last_reviewed_commit,
            disposition="normal-return",
            request=RetryDelivery(
                action="retry",
                outcome_id=builder.outcome_id,
                claim_id=builder.claim.claim_id,
                attempt_id=builder.claim.attempt_id,
                abandoned_commit=subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
                    (resolve_git_executable(), "-C", str(builder.worktree_path), "rev-parse", "HEAD"),
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
            ),
        ),
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )


def _report_finalizer_attention(application: PortfolioApplication, change_id: str) -> None:
    acquired = application.acquire_change_action(_continuation_request(application, change_id))
    for _attempt in range(4):
        if acquired.engine_action is None and acquired.kind != "reconciled":
            break
        if acquired.engine_action is not None:
            _execute_engine(application, acquired.engine_action)
        acquired = application.acquire_change_action(_continuation_request(application, change_id))
    assert acquired.finalization is not None, acquired
    attempt = acquired.finalization.attempt
    basis = application.show_finalization_context(change_id).readiness.basis
    report = application.report_finalization_failure(
        ReportFinalizationFailure(
            change_id=change_id,
            expected_contract_digest=basis.contract_digest,
            expected_frontier_digest=basis.frontier_digest,
            expected_change_head=basis.candidate_head,
            expected_reviewed_head=basis.reviewed_head,
            expected_diagnostic_sequence=basis.diagnostic_sequence,
            attempt_key=attempt.writer.attempt_id,
            category="maintained-check",
            code=FinalizationFailureCode.MAINTAINED_CHECK_FAILED,
            checks_state="failed",
        )
    )
    assert isinstance(report, FinalizationReport)
    application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))


def test_format_1_to_2_migration_changes_only_the_marker_and_keeps_every_change_available(tmp_path: Path) -> None:
    """N03-A: format 2 only gates the new record versions; no stored record is rewritten."""
    repository = _seed(tmp_path)
    _write_config(repository)
    (repository / ".owlbear/delivery" / FORMAT_MARKER).write_bytes(b'{"format":1}\n')
    pre = record_tree_digest(repository)
    _assert_refused(repository, "state-migration-required")

    proposal = state_migration.propose(repository)

    assert [(entry.locator, entry.before_sha256) for entry in proposal.entries] == [(FORMAT_MARKER, pre[FORMAT_MARKER])]
    state_migration.apply(repository, proposal.migration_id)
    state_migration.verify(repository, proposal.migration_id)
    post = record_tree_digest(repository, exclude_migrations=True)
    assert {locator: digest for locator, digest in post.items() if pre.get(locator) != digest} == {
        FORMAT_MARKER: hashlib.sha256(format_marker_bytes()).hexdigest()
    }
    assert json.loads(_frontier_path(repository, "change-a").read_bytes())["schema_version"] == 18
    _available(repository, ("change-a", "change-b"))
    assert record_tree_digest(repository, exclude_migrations=True) == post
