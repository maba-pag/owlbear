"""Fenced, copy-first migration of persisted Delivery state between registered formats.

``propose`` stages rewritten bytes outside authoritative state. ``apply`` takes the exclusive
controller lock, backs up every affected record with a record-tree hash manifest, journals
``backed-up → applying → applied`` and commits the format marker last. ``resume`` replays from
durable state, ``verify`` is the offline verifier (journal ``verified``), and ``abort`` restores
the backup before the marker from durable state only (never ``RuntimeTransaction.abort``).
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import secrets
import shutil
import stat
from dataclasses import dataclass
from itertools import batched
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery import state_formats
from owlbear_delivery.application_models import DeliveryUnavailableChangeView
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    load_verification_application,
)
from owlbear_delivery.delivery_state import parse_delivery_state_snapshot
from owlbear_delivery.runtime_support import parse_delivery_frontier
from owlbear_delivery.runtime_transaction import (
    ContainedWriteLimits,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
    TransactionPathError,
    read_contained,
    write_contained,
)
from owlbear_delivery.state_formats import (
    DELIVERY_STATE_ROOT,
    FORMAT_MARKER,
    MAX_RECORD_BYTES,
    MIGRATION_JOURNAL,
    MIGRATIONS_ROOT,
    SUPPORTED_FORMAT,
    CapabilityReport,
    RecordKind,
    classify_kind,
    format_marker_bytes,
    format_migration_steps,
    record_tree_digest,
    scan_capability,
)
from owlbear_delivery.storage_io import (
    ControllerFencedError,
    ControllerLock,
    ReadOnlyStateError,
    acquire_controller_lock,
    read_only_state,
)
from owlbear_delivery.workspace_models import ChangeCoordination

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from owlbear_delivery.portfolio_application import PortfolioApplication

MIGRATION_STATE_ROOT = ".owlbear/delivery-migrations"
MARKER_REWRITE = "format-marker"
DEFAULT_BATCH_SIZE = 32
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_LIMITS = ContainedWriteLimits(max_content_bytes=MAX_RECORD_BYTES, max_temporary_bytes=MAX_RECORD_BYTES * 4)
_REFUSING_STATUSES = frozenset({"newer", "unknown-version", "unreadable"})
_JOURNAL_TEMPORARY = re.compile(r"\.tmp-[0-9a-f]{24}")
# The archive keeps the backup and aborted journal; retrying the identical migration is a user decision.
_ARCHIVED_DETAIL = (
    "this migration was aborted; its archive under .owlbear/delivery-migrations/<id> is kept, "
    "and only abort (namespace cleanup) accepts its ID"
)

type MigrationErrorCode = Literal[
    "controller-running",
    "transactions-pending",
    "migration-not-required",
    "migration-in-progress",
    "proposal-unknown",
    "proposal-invalid",
    "proposal-stale",
    "state-unsupported",
    "record-corrupt",
    "backup-invalid",
    "journal-missing",
    "journal-state",
    "marker-committed",
    "migration-archived",
    "verification-failed",
    "verify-tree-mismatch",
]
type JournalState = Literal["backed-up", "applying", "applied", "verified", "aborting", "aborted"]
type FailureHook = Callable[[str], None]


class MigrationError(RuntimeError):
    """A migration step refused; ``locator`` names the Delivery-root-relative record when one is at fault."""

    __slots__ = ("code", "detail", "locator")

    def __init__(self, *, code: MigrationErrorCode, detail: str, locator: str | None = None) -> None:
        self.code: MigrationErrorCode = code
        self.detail = detail
        self.locator = locator
        super().__init__(f"{code}: {detail}" + (f" ({locator})" if locator else ""))


class _MigrationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MigrationEntry(_MigrationModel):
    """One record replacement; an absent ``before_sha256`` means the record does not exist yet."""

    locator: str = Field(min_length=1)
    rewrite: str = Field(min_length=1)
    before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class MigrationProposal(_MigrationModel):
    """Staged migration whose identity binds every entry, both formats, its format steps and the release.

    ``steps`` names the registered format migrations from ``source_format`` to ``target_format`` in order;
    their record rewrites precede the format marker, which commits last at the target format.
    """

    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_format: int = Field(ge=0)
    target_format: int = Field(ge=0)
    steps: tuple[str, ...]
    release: str = Field(min_length=1)
    entries: tuple[MigrationEntry, ...] = Field(min_length=1)

    @property
    def records(self) -> tuple[MigrationEntry, ...]:
        """Return record rewrites (every entry except the format marker)."""
        return tuple(entry for entry in self.entries if entry.rewrite != MARKER_REWRITE)

    @property
    def marker(self) -> MigrationEntry | None:
        """Return the format marker entry, which commits last."""
        return next((entry for entry in self.entries if entry.rewrite == MARKER_REWRITE), None)


class MigrationBatch(_MigrationModel):
    """One migration-owned ``RuntimeTransaction``, journaled before its commit."""

    transaction_id: str = Field(pattern=r"^migration-[0-9a-f]{16}-[0-9]{4}$")
    locators: tuple[str, ...] = Field(min_length=1)


class MigrationJournal(_MigrationModel):
    """Durable migration progress under ``runtime/migrations/<id>/journal.json``."""

    schema_version: Literal[1] = 1
    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: JournalState
    source_format: int = Field(ge=0)
    target_format: int = Field(ge=0)
    backup_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    batches: tuple[MigrationBatch, ...] = ()


class MigrationBackupManifest(_MigrationModel):
    """Before bytes of every affected record and the full record-tree hash manifest at backup time."""

    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    records: dict[str, str]
    tree: dict[str, str]


@dataclass(frozen=True, slots=True)
class AbortResult:
    """Outcome of one ``abort``: the archived journal and whether step (g) removed the namespace."""

    journal: MigrationJournal
    namespace_removed: bool


def frontier_17_to_18(content: bytes) -> bytes:
    """Registered rewrite ``frontier-17-to-18``: canonical strict schema-18 bytes, never synthesized fields."""
    payload = json.loads(content)
    if not isinstance(payload, dict) or payload.get("schema_version") != 17:  # noqa: PLR2004 - registered source.
        msg = "frontier-17-to-18 applies only to schema-17 frontiers"
        raise ValueError(msg)
    return parse_delivery_frontier(content)[1]


def coordination_1_to_2(content: bytes) -> bytes:
    """Registered rewrite ``coordination-1-to-2``: the same record at version 2, without a Pause request.

    Version 2 only adds the optional ``pause_request`` (omitted when absent), so the K4 recovery
    authority digest of the rewritten record equals the digest of its version-1 bytes.
    """
    payload = json.loads(content)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or "pause_request" in payload:
        msg = "coordination-1-to-2 applies only to schema-1 coordination records"
        raise ValueError(msg)
    payload["schema_version"] = 2
    return _canonical_coordination(json.dumps(payload).encode())


def _canonical_coordination(content: bytes) -> bytes:
    return _canonical(ChangeCoordination.model_validate_json(content, strict=True))


REWRITES: dict[str, Callable[[bytes], bytes]] = {
    "owlbear_delivery.state_migration:frontier_17_to_18": frontier_17_to_18,
    "owlbear_delivery.state_migration:coordination_1_to_2": coordination_1_to_2,
}
# Target-release strict parsers; each staged record must parse back to its own bytes.
_TARGET_PARSERS: dict[str, Callable[[bytes], bytes]] = {
    "frontier": lambda content: parse_delivery_frontier(content)[1],
    "coordination": _canonical_coordination,
}
# Owners whose strict read is a parser function rather than one model (frontier strict JSON, snapshot upcast).
_OWNER_PARSERS: dict[str, Callable[[bytes], object]] = {
    "frontier": parse_delivery_frontier,
    "snapshot": parse_delivery_state_snapshot,
}


def controller_release() -> str:
    """Return this controller's identity: distribution version plus a digest of its format registry."""
    try:
        version = importlib.metadata.version("owlbear-delivery")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    registry = hashlib.sha256()
    for module_file in (state_formats.__file__, __file__):
        registry.update(Path(module_file).read_bytes())
    return f"owlbear-delivery {version} registry:{registry.hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class _Paths:
    workspace: Path
    delivery: Path
    runtime: Path
    state: Path

    @classmethod
    def of(cls, workspace_root: Path) -> _Paths:
        workspace = workspace_root.resolve()
        owlbear = workspace / ".owlbear"
        for path in (owlbear, workspace / DELIVERY_STATE_ROOT, workspace / MIGRATION_STATE_ROOT):
            if path.is_symlink():
                raise MigrationError(code="state-unsupported", detail="Delivery state parents must not be symlinks")
        delivery = workspace / DELIVERY_STATE_ROOT
        return cls(workspace, delivery, delivery / "runtime", workspace / MIGRATION_STATE_ROOT)

    def migration(self, migration_id: str) -> Path:
        return self.state / migration_id

    def live_journal(self, migration_id: str) -> Path:
        return self.delivery / MIGRATIONS_ROOT / migration_id / MIGRATION_JOURNAL


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _fail(failure: FailureHook | None, point: str) -> None:
    if failure is not None:
        failure(point)


def _runtime_relative(locator: str) -> Path:
    relative = Path(locator).relative_to("runtime")
    if not relative.parts or ".." in relative.parts:
        raise MigrationError(
            code="proposal-invalid", detail="migration entry escapes the runtime root", locator=locator
        )
    return relative


@contextlib.contextmanager
def _open_directory(path: Path) -> Iterator[int]:
    descriptor = os.open(path, _DIRECTORY_FLAGS)
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _read_file(root: Path, relative: str | Path) -> bytes | None:
    """Read one contained regular file without following links; ``None`` when absent."""
    try:
        with _open_directory(root) as root_fd:
            return read_contained(root_fd, Path(relative), limit=MAX_RECORD_BYTES)
    except FileNotFoundError:
        return None
    except (OSError, TransactionPathError) as exc:
        locator = Path(relative).as_posix()
        raise MigrationError(
            code="record-corrupt", detail="record is not a readable regular file", locator=locator
        ) from exc


def _write_file(root: Path, relative: str | Path, content: bytes) -> None:
    """Atomically replace or create one contained file (no link is followed), then fsync."""
    _ensure_directory(root)
    with _open_directory(root) as root_fd:
        current = read_contained(root_fd, Path(relative), limit=MAX_RECORD_BYTES) if _exists(root, relative) else None
        write_contained(root_fd, Path(relative), content, expected=current, limits=_LIMITS)


def _exists(root: Path, relative: str | Path) -> bool:
    try:
        (root / relative).lstat()
    except FileNotFoundError:
        return False
    return True


def _ensure_directory(path: Path) -> None:
    """Create each missing directory and fsync its parent, so the new entry survives a crash."""
    missing: list[Path] = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        with contextlib.suppress(FileExistsError):
            directory.mkdir(mode=0o700)
        _fsync_directory(directory.parent)


def _publish_directory(temporary: Path, destination: Path) -> None:
    """Rename a fully written directory into place and fsync the parent before any later write."""
    temporary.rename(destination)
    _fsync_directory(destination.parent)


def _record_digest(paths: _Paths, locator: str) -> str | None:
    content = _read_file(paths.delivery, locator)
    return None if content is None else _sha256(content)


# ---------------------------------------------------------------------------
# Propose
# ---------------------------------------------------------------------------


def propose(workspace_root: Path) -> MigrationProposal:
    """Stage every registered rewrite and the format marker outside authoritative state; write no record."""
    paths = _Paths.of(workspace_root)
    report = scan_capability(paths.workspace)
    _require_migratable(report)
    steps = _format_steps(report.format)
    _validate_baseline_records(paths, report)
    entries: list[MigrationEntry] = []
    staged: dict[str, bytes] = {}
    for record in report.records:
        if record.status != "migration-required":
            continue
        entry, after = _rewrite_entry(paths, record.locator, record.kind_id, record.version)
        entries.append(entry)
        staged[entry.locator] = after
    marker_before = _read_file(paths.delivery, FORMAT_MARKER)
    marker_after = format_marker_bytes(SUPPORTED_FORMAT)
    if marker_before != marker_after:
        before_digest = None if marker_before is None else _sha256(marker_before)
        entries.append(
            MigrationEntry(
                locator=FORMAT_MARKER,
                rewrite=MARKER_REWRITE,
                before_sha256=before_digest,
                after_sha256=_sha256(marker_after),
            )
        )
        staged[FORMAT_MARKER] = marker_after
    if not entries:
        raise MigrationError(code="migration-not-required", detail="Delivery state already has the supported format")
    proposal = _proposal(report.format, tuple(entries), steps=steps)
    _write_stage(paths, proposal, staged)
    return proposal


def _format_steps(source_format: int) -> tuple[str, ...]:
    try:
        return format_migration_steps(source_format)
    except ValueError as exc:
        raise MigrationError(code="state-unsupported", detail=str(exc), locator=FORMAT_MARKER) from exc


def _require_migratable(report: CapabilityReport) -> None:
    if report.journals and any(journal.state != "verified" for journal in report.journals):
        raise MigrationError(
            code="migration-in-progress", detail="an unfinished migration journal exists", locator=MIGRATIONS_ROOT
        )
    if not report.complete:
        raise MigrationError(
            code="state-unsupported", detail=report.incomplete_detail or "Delivery state is not fully classified"
        )
    if report.format_status not in {"current", "migration-required"}:
        raise MigrationError(
            code="state-unsupported", detail="Delivery state format is not supported", locator=FORMAT_MARKER
        )
    for record in report.records:
        if record.status in _REFUSING_STATUSES:
            code = "record-corrupt" if record.status == "unreadable" else "state-unsupported"
            raise MigrationError(code=code, detail=f"record is {record.status}", locator=record.locator)


def _resolve_owner(name: str) -> Callable[..., object]:
    module, attribute = name.split(":")
    return getattr(importlib.import_module(module), attribute)


def _owner_parse(kind: RecordKind, status: str, content: bytes) -> None:
    """Strictly parse one record with its registered owner, at its declared version; never write."""
    if kind.allow_empty and not content:
        return
    special = _OWNER_PARSERS.get(kind.kind_id)
    if special is not None:
        special(content)
        return
    if status == "readable-legacy":
        version = json.loads(content).get("schema_version")
        _resolve_owner(dict(kind.read_upcasts)[version])(content)
        return
    if kind.envelope is not None:
        payload = json.loads(content)
        if not isinstance(payload, dict) or kind.envelope not in payload:
            msg = f"record has no {kind.envelope} envelope"
            raise ValueError(msg)
        content = json.dumps(payload[kind.envelope]).encode()
    errors: list[ValidationError] = []
    for owner in kind.owners:
        model = _resolve_owner(owner)
        try:
            model.model_validate_json(content, strict=True)  # type: ignore[attr-defined]
        except ValidationError as exc:
            errors.append(exc)
        else:
            return
    raise errors[0]


def _validate_baseline_records(paths: _Paths, report: CapabilityReport) -> None:
    """Owner-parse every readable registered record the migration keeps, before any stage or write.

    Records needing a rewrite are validated by their rewrite; historical (H), opaque (O), transient (L)
    and unread kinds, and kinds without an owner model, stay outside this check as in the registry.
    """
    for record in report.records:
        kind = classify_kind(record.locator) if record.kind_id is not None else None
        if kind is None or not kind.read or not kind.owners or kind.mutability in {"H", "O", "L"}:
            continue
        if record.status not in {"current", "readable-legacy"}:
            continue
        content = _read_file(paths.delivery, record.locator)
        if content is None:
            detail = "record disappeared while validating"
            raise MigrationError(code="proposal-stale", detail=detail, locator=record.locator)
        try:
            _owner_parse(kind, record.status, content)
        except (KeyError, TypeError, ValueError) as exc:
            raise MigrationError(
                code="record-corrupt",
                detail="record does not parse with its owner at its declared version",
                locator=record.locator,
            ) from exc


def _rewrite_entry(
    paths: _Paths, locator: str, kind_id: str | None, version: int | None
) -> tuple[MigrationEntry, bytes]:
    kind = classify_kind(locator)
    rewrite = dict(kind.rewrites).get(version) if kind is not None and version is not None else None
    function = REWRITES.get(rewrite) if rewrite is not None else None
    parser = _TARGET_PARSERS.get(kind_id or "")
    if function is None or parser is None or not locator.startswith("runtime/"):
        raise MigrationError(code="state-unsupported", detail="record has no registered rewrite", locator=locator)
    before = _read_file(paths.delivery, locator)
    if before is None:
        raise MigrationError(code="proposal-stale", detail="record disappeared while proposing", locator=locator)
    try:
        after = function(before)
        reparsed = parser(after)
    except (TypeError, ValueError) as exc:
        # Invalid at its declared version: corruption, never repaired or rehashed (V20).
        raise MigrationError(
            code="record-corrupt", detail="record is invalid at its declared version", locator=locator
        ) from exc
    if reparsed != after:
        raise MigrationError(code="record-corrupt", detail="rewrite is not canonical for its target", locator=locator)
    entry = MigrationEntry(locator=locator, rewrite=rewrite, before_sha256=_sha256(before), after_sha256=_sha256(after))
    return entry, after


def _proposal(
    source_format: int,
    entries: tuple[MigrationEntry, ...],
    *,
    steps: tuple[str, ...],
    release: str | None = None,
    target_format: int = SUPPORTED_FORMAT,
) -> MigrationProposal:
    release = controller_release() if release is None else release
    identity = {
        "entries": [[entry.locator, entry.before_sha256, entry.after_sha256] for entry in entries],
        "release": release,
        "source_format": source_format,
        "steps": list(steps),
        "target_format": target_format,
    }
    migration_id = _sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    return MigrationProposal(
        migration_id=migration_id,
        source_format=source_format,
        target_format=target_format,
        steps=steps,
        release=release,
        entries=entries,
    )


def _write_stage(paths: _Paths, proposal: MigrationProposal, staged: dict[str, bytes]) -> None:
    directory = paths.migration(proposal.migration_id)
    if directory.exists() or directory.is_symlink():
        existing, _staged = _load_proposal(paths, proposal.migration_id)
        if existing != proposal:  # pragma: no cover - the identity binds every field.
            raise MigrationError(code="proposal-invalid", detail="staged proposal differs from its identity")
        if _read_journal(directory / MIGRATION_JOURNAL) is not None:
            raise MigrationError(code="migration-archived", detail=_ARCHIVED_DETAIL)
        return
    _ensure_directory(paths.state)
    temporary = paths.state / f".tmp-{secrets.token_hex(12)}"
    temporary.mkdir(mode=0o700)
    try:
        for locator, content in staged.items():
            _write_file(temporary / "stage", locator, content)
        _write_file(temporary, "proposal.json", _canonical(proposal))
        _publish_directory(temporary, directory)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _load_proposal(paths: _Paths, migration_id: str) -> tuple[MigrationProposal, dict[str, bytes]]:
    if not migration_id or Path(migration_id).name != migration_id or migration_id in {".", ".."}:
        raise MigrationError(code="proposal-unknown", detail="migration ID is invalid")
    directory = paths.migration(migration_id)
    content = _read_file(directory, "proposal.json") if directory.is_dir() and not directory.is_symlink() else None
    if content is None:
        raise MigrationError(code="proposal-unknown", detail="no staged proposal has this migration ID")
    try:
        proposal = MigrationProposal.model_validate_json(content, strict=True)
    except ValidationError as exc:
        raise MigrationError(code="proposal-invalid", detail="staged proposal is malformed") from exc
    rebuilt = _proposal(
        proposal.source_format,
        proposal.entries,
        steps=proposal.steps,
        release=proposal.release,
        target_format=proposal.target_format,
    )
    if proposal.migration_id != migration_id or rebuilt != proposal:
        raise MigrationError(code="proposal-invalid", detail="staged proposal does not match its identity")
    staged = {}
    for entry in proposal.entries:
        after = _read_file(directory / "stage", entry.locator)
        if after is None or _sha256(after) != entry.after_sha256:
            raise MigrationError(
                code="proposal-invalid", detail="staged record does not match its digest", locator=entry.locator
            )
        _runtime_relative(entry.locator)
        staged[entry.locator] = after
    return proposal, staged


# ---------------------------------------------------------------------------
# Apply and resume
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _exclusive(paths: _Paths) -> Iterator[ControllerLock]:
    try:
        lock = acquire_controller_lock(paths.runtime, exclusive=True)
    except ControllerFencedError as exc:
        raise MigrationError(
            code="controller-running", detail="a Delivery controller holds the workspace lock"
        ) from exc
    try:
        yield lock
    finally:
        lock.release()


def apply(
    workspace_root: Path,
    migration_id: str,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Back up, journal and replace every proposed record under the exclusive lock; the marker commits last."""
    paths = _Paths.of(workspace_root)
    proposal, staged = _load_proposal(paths, migration_id)
    with _exclusive(paths):
        if _read_journal(paths.live_journal(migration_id)) is not None:
            raise MigrationError(
                code="migration-in-progress", detail="this migration is journaled; use resume or abort"
            )
        if _read_journal(paths.migration(migration_id) / MIGRATION_JOURNAL) is not None:
            raise MigrationError(code="migration-archived", detail=_ARCHIVED_DETAIL)
        pending = _pending_transaction_manifests(paths)
        if pending:
            raise MigrationError(
                code="transactions-pending", detail="a RuntimeTransaction manifest is pending", locator=pending[0]
            )
        report = scan_capability(paths.workspace)
        _require_migratable(report)
        _require_proposal_current(paths, proposal, report)
        _validate_baseline_records(paths, report)
        manifest_digest = _write_backup(paths, proposal)
        _fail(failure, "before-journal")
        journal = MigrationJournal(
            migration_id=migration_id,
            state="backed-up",
            source_format=proposal.source_format,
            target_format=proposal.target_format,
            backup_manifest_sha256=manifest_digest,
        )
        _write_live_journal(paths, journal)
        _fail(failure, "after-backup")
        return _drive(paths, proposal, staged, journal, batch_size, failure)


def resume(
    workspace_root: Path,
    migration_id: str,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Continue a crashed apply from durable state; never rehash a record with an unknown digest."""
    paths = _Paths.of(workspace_root)
    with _exclusive(paths):
        journal = _require_live_journal(paths, migration_id)
        if journal.state == "aborting":
            raise MigrationError(code="journal-state", detail="an aborting migration accepts only abort")
        if journal.state in {"applied", "verified"}:
            return journal
        proposal, staged = _load_proposal(paths, migration_id)
        _require_same_release(proposal)
        _verify_backup(paths, proposal, journal)
        return _drive(paths, proposal, staged, journal, batch_size, failure)


def _require_same_release(proposal: MigrationProposal) -> None:
    if (
        proposal.release != controller_release()
        or proposal.target_format != SUPPORTED_FORMAT
        or proposal.steps != _format_steps(proposal.source_format)
    ):
        raise MigrationError(code="proposal-stale", detail="the proposal was made by another controller release")


def _require_proposal_current(paths: _Paths, proposal: MigrationProposal, report: CapabilityReport) -> None:
    _require_same_release(proposal)
    if report.format != proposal.source_format:
        raise MigrationError(code="proposal-stale", detail="the workspace format changed since the proposal")
    required = {record.locator for record in report.records if record.status == "migration-required"}
    if required != {entry.locator for entry in proposal.records}:
        raise MigrationError(code="proposal-stale", detail="the set of records requiring migration changed")
    for entry in proposal.entries:
        if _record_digest(paths, entry.locator) != entry.before_sha256:
            raise MigrationError(
                code="proposal-stale", detail="record changed since the proposal", locator=entry.locator
            )


def _require_no_pending_transactions(paths: _Paths) -> None:
    pending = _pending_transaction_manifests(paths)
    if pending:
        raise MigrationError(
            code="transactions-pending", detail="a RuntimeTransaction manifest is pending", locator=pending[0]
        )


def _pending_transaction_manifests(paths: _Paths) -> list[str]:
    pending: list[str] = []
    for directory, directory_names, file_names in os.walk(paths.delivery):
        relative = Path(directory).relative_to(paths.delivery)
        if relative == Path():
            directory_names[:] = [name for name in directory_names if name != "worktrees"]
        if Path(directory).name == "transactions":
            pending.extend((relative / name).as_posix() for name in sorted(file_names) if name.endswith(".yaml"))
    return sorted(pending)


def _write_backup(paths: _Paths, proposal: MigrationProposal) -> str:
    """Copy affected before bytes and the full record-tree manifest; reuse only an identical backup."""
    directory = paths.migration(proposal.migration_id)
    records = {}
    for entry in proposal.entries:
        if entry.before_sha256 is not None:
            records[entry.locator] = entry.before_sha256
    manifest = MigrationBackupManifest(
        migration_id=proposal.migration_id,
        records=records,
        tree=record_tree_digest(paths.workspace, exclude_migrations=True),
    )
    content = _canonical(manifest)
    backup = directory / "backup"
    if backup.exists() or backup.is_symlink():
        if _read_file(backup, "manifest.json") == content:
            _verify_backup_records(backup, manifest)
            return _sha256(content)
        # Without a journal an earlier backup is not authoritative; keep it aside rather than reuse or delete it.
        _publish_directory(backup, directory / f"backup-superseded-{secrets.token_hex(6)}")
    temporary = directory / f".tmp-backup-{secrets.token_hex(12)}"
    try:
        for locator, digest in records.items():
            before = _read_file(paths.delivery, locator)
            if before is None or _sha256(before) != digest:
                raise MigrationError(code="proposal-stale", detail="record changed during backup", locator=locator)
            _write_file(temporary / "records", locator, before)
        _write_file(temporary, "manifest.json", content)
        _publish_directory(temporary, backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return _sha256(content)


def _read_backup_manifest(paths: _Paths, journal: MigrationJournal) -> MigrationBackupManifest:
    backup = paths.migration(journal.migration_id) / "backup"
    content = _read_file(backup, "manifest.json")
    if content is None or _sha256(content) != journal.backup_manifest_sha256:
        raise MigrationError(code="backup-invalid", detail="the backup manifest is missing or altered")
    return MigrationBackupManifest.model_validate_json(content, strict=True)


def _verify_backup_records(backup: Path, manifest: MigrationBackupManifest) -> None:
    for locator, digest in manifest.records.items():
        content = _read_file(backup / "records", locator)
        if content is None or _sha256(content) != digest:
            raise MigrationError(
                code="backup-invalid", detail="a backed-up record is missing or altered", locator=locator
            )


def _verify_backup(paths: _Paths, proposal: MigrationProposal, journal: MigrationJournal) -> MigrationBackupManifest:
    manifest = _read_backup_manifest(paths, journal)
    expected = {entry.locator: entry.before_sha256 for entry in proposal.entries if entry.before_sha256 is not None}
    if manifest.records != expected or manifest.migration_id != proposal.migration_id:
        raise MigrationError(code="backup-invalid", detail="the backup manifest does not match the proposal")
    _verify_backup_records(paths.migration(journal.migration_id) / "backup", manifest)
    return manifest


def _classify_entries(paths: _Paths, proposal: MigrationProposal) -> dict[str, Literal["before", "after"]]:
    """Return each entry's position; a third digest stops as corruption with both copies preserved (V20)."""
    positions: dict[str, Literal["before", "after"]] = {}
    for entry in proposal.entries:
        digest = _record_digest(paths, entry.locator)
        if digest == entry.after_sha256:
            positions[entry.locator] = "after"
        elif digest == entry.before_sha256:
            positions[entry.locator] = "before"
        else:
            raise MigrationError(
                code="record-corrupt",
                detail="record matches neither its backed-up nor its migrated digest; both copies are preserved",
                locator=entry.locator,
            )
    return positions


def _drive(  # noqa: PLR0913, PLR0917 - one replay binds proposal, staged bytes, journal and test hooks.
    paths: _Paths,
    proposal: MigrationProposal,
    staged: dict[str, bytes],
    journal: MigrationJournal,
    batch_size: int,
    failure: FailureHook | None,
) -> MigrationJournal:
    backup = paths.migration(proposal.migration_id) / "backup" / "records"
    entries = {entry.locator: entry for entry in proposal.entries}
    before = {locator: _read_file(backup, locator) for locator in entries}
    _classify_entries(paths, proposal)
    if journal.state == "backed-up":
        journal = _transition(paths, journal, "applying")
    for index, batch in enumerate(journal.batches):
        if _manifest_path(paths, batch.transaction_id).exists() or any(
            _record_digest(paths, locator) != entries[locator].after_sha256 for locator in batch.locators
        ):
            _replay_batch(paths, _batch_transaction(paths, batch, entries, before, staged), batch, index, failure)
    positions = _classify_entries(paths, proposal)
    batched_locators = {locator for batch in journal.batches for locator in batch.locators}
    remaining = [
        entry.locator
        for entry in proposal.records
        if positions[entry.locator] == "before" and entry.locator not in batched_locators
    ]
    for chunk in batched(remaining, max(batch_size, 1), strict=False):
        journal = _journal_batch(paths, journal, chunk)
        index = len(journal.batches) - 1
        _commit_batch(paths, journal.batches[index], entries, before, staged, index, failure)
        _fail(failure, f"after-replacement-{index}")
    marker = proposal.marker
    if marker is not None and marker.locator not in batched_locators and positions[marker.locator] == "before":
        _fail(failure, "before-marker")
        journal = _journal_batch(paths, journal, (marker.locator,))
        index = len(journal.batches) - 1
        _commit_batch(paths, journal.batches[index], entries, before, staged, index, failure)
        _fail(failure, "after-marker")
    if set(_classify_entries(paths, proposal).values()) != {"after"}:  # pragma: no cover - replay invariant.
        raise MigrationError(code="record-corrupt", detail="migration replay did not converge")
    return _transition(paths, journal, "applied")


def _journal_batch(paths: _Paths, journal: MigrationJournal, locators: tuple[str, ...]) -> MigrationJournal:
    transaction_id = f"migration-{journal.migration_id[:16]}-{len(journal.batches):04d}"
    batch = MigrationBatch(transaction_id=transaction_id, locators=locators)
    updated = journal.model_copy(update={"batches": (*journal.batches, batch)})
    _write_live_journal(paths, updated)
    return updated


def _batch_transaction(
    paths: _Paths,
    batch: MigrationBatch,
    entries: dict[str, MigrationEntry],
    before: dict[str, bytes | None],
    staged: dict[str, bytes],
) -> RuntimeTransaction:
    participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
    for locator in batch.locators:
        relative = _runtime_relative(locator)
        previous = before[locator] if entries[locator].before_sha256 is not None else None
        if previous is None:
            participants.append(TransactionParticipant(paths.runtime, relative, staged[locator]))
        else:
            participants.append(ReplacementTransactionParticipant(paths.runtime, relative, previous, staged[locator]))
    return RuntimeTransaction(paths.runtime, batch.transaction_id, tuple(participants))


def _manifest_path(paths: _Paths, transaction_id: str) -> Path:
    return paths.runtime / "transactions" / f"{transaction_id}.yaml"


def _replay_batch(
    paths: _Paths,
    transaction: RuntimeTransaction,
    batch: MigrationBatch,
    index: int,
    failure: FailureHook | None,
) -> None:
    """Complete one journaled batch: roll a pending manifest forward, or commit a batch that never started."""
    try:
        if _manifest_path(paths, batch.transaction_id).exists():
            transaction.recover()
        else:
            transaction.commit(failure=_batch_hook(failure, index))
    except TransactionConflictError as exc:
        raise MigrationError(code="record-corrupt", detail="a journaled batch conflicts with current bytes") from exc


def _commit_batch(  # noqa: PLR0913, PLR0917 - one batch commit binds its journal row and staged bytes.
    paths: _Paths,
    batch: MigrationBatch,
    entries: dict[str, MigrationEntry],
    before: dict[str, bytes | None],
    staged: dict[str, bytes],
    index: int,
    failure: FailureHook | None,
) -> None:
    transaction = _batch_transaction(paths, batch, entries, before, staged)
    try:
        transaction.commit(failure=_batch_hook(failure, index))
    except TransactionConflictError as exc:
        raise MigrationError(code="record-corrupt", detail="a record changed under the exclusive lock") from exc


def _batch_hook(failure: FailureHook | None, index: int) -> FailureHook | None:
    if failure is None:
        return None
    return lambda point: failure(f"batch-{index}:{point}")


# ---------------------------------------------------------------------------
# Journal I/O
# ---------------------------------------------------------------------------


def _read_journal(path: Path) -> MigrationJournal | None:
    content = _read_file(path.parent, path.name) if path.parent.is_dir() and not path.parent.is_symlink() else None
    if content is None:
        return None
    try:
        return MigrationJournal.model_validate_json(content, strict=True)
    except ValidationError as exc:
        raise MigrationError(code="journal-state", detail="the migration journal is malformed") from exc


def _require_live_journal(paths: _Paths, migration_id: str) -> MigrationJournal:
    _load_proposal(paths, migration_id)
    journal = _read_journal(paths.live_journal(migration_id))
    if journal is not None:
        return journal
    if _read_journal(paths.migration(migration_id) / MIGRATION_JOURNAL) is not None:
        raise MigrationError(code="migration-archived", detail=_ARCHIVED_DETAIL)
    raise MigrationError(code="journal-missing", detail="this migration has no journal; run apply")


def _write_live_journal(paths: _Paths, journal: MigrationJournal) -> None:
    relative = Path(MIGRATIONS_ROOT).relative_to("runtime") / journal.migration_id / MIGRATION_JOURNAL
    _write_file(paths.runtime, relative, _canonical(journal))


def _transition(paths: _Paths, journal: MigrationJournal, state: JournalState) -> MigrationJournal:
    updated = journal.model_copy(update={"state": state})
    _write_live_journal(paths, updated)
    return updated


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def _read_startup_config(path: Path) -> DeliveryStartupConfig:
    return DeliveryStartupConfig.model_validate_json(path.read_bytes(), strict=True)


def verify(
    workspace_root: Path,
    migration_id: str,
    *,
    read_config: Callable[[Path], DeliveryStartupConfig] = _read_startup_config,
) -> MigrationJournal:
    """Offline verifier: a write-free verification load must list every Change as available.

    Before loading, the backup must be intact and the record tree must equal its manifest with each
    proposed entry at its target digest, so an unjournaled change is refused rather than verified.
    Every verification read runs in ``read_only_state``: transaction recovery, frontier
    canonicalization and retry reconciliation are disabled, and any other record write raises
    before it changes a byte. The record-tree comparison remains a second, detecting check.
    """
    paths = _Paths.of(workspace_root)
    with _exclusive(paths) as lock:
        journal = _require_live_journal(paths, migration_id)
        if journal.state == "verified":
            return journal
        if journal.state != "applied":
            raise MigrationError(
                code="journal-state", detail=f"verify requires an applied journal, not {journal.state}"
            )
        _require_no_pending_transactions(paths)
        proposal, _staged = _load_proposal(paths, migration_id)
        _require_applied_tree(paths, proposal, _verify_backup(paths, proposal, journal))
        before = record_tree_digest(paths.workspace)
        try:
            with read_only_state():
                application = load_verification_application(
                    paths.workspace, read_config, migration_id=migration_id, controller_lock=lock
                )
                unavailable = [
                    change_id
                    for change_id in _change_ids(paths, application)
                    if isinstance(application.get_change(change_id), DeliveryUnavailableChangeView)
                ]
        except DeliveryApplicationLoadError as exc:
            raise MigrationError(code="verification-failed", detail=f"verification load refused: {exc.detail}") from exc
        except ReadOnlyStateError as exc:
            raise MigrationError(code="verification-failed", detail="the verification load attempted a write") from exc
        if record_tree_digest(paths.workspace) != before:
            raise MigrationError(code="verification-failed", detail="the verification load changed Delivery records")
        if unavailable:
            raise MigrationError(
                code="verification-failed", detail=f"Changes are unavailable: {', '.join(sorted(unavailable))}"
            )
        return _transition(paths, journal, "verified")


def _require_applied_tree(paths: _Paths, proposal: MigrationProposal, manifest: MigrationBackupManifest) -> None:
    """The record tree must be the backed-up tree with exactly the proposed entries at their target digests."""
    expected = {**manifest.tree, **{entry.locator: entry.after_sha256 for entry in proposal.entries}}
    actual = record_tree_digest(paths.workspace, exclude_migrations=True)
    differing = sorted(
        locator for locator in expected.keys() | actual.keys() if expected.get(locator) != actual.get(locator)
    )
    if differing:
        raise MigrationError(
            code="verify-tree-mismatch",
            detail=f"{len(differing)} record(s) differ from what the journaled migration produced",
            locator=differing[0],
        )


def _change_ids(paths: _Paths, application: PortfolioApplication) -> list[str]:
    listed = application.list_changes().model_dump(mode="json")
    found = {
        item["change_id"]
        for value in listed.values()
        if isinstance(value, list)
        for item in value
        if isinstance(item, dict) and isinstance(item.get("change_id"), str)
    }
    changes = paths.runtime / "changes"
    if changes.is_dir():
        found.update(child.name for child in changes.iterdir() if child.is_dir() and not child.is_symlink())
    return sorted(found)


# ---------------------------------------------------------------------------
# Abort
# ---------------------------------------------------------------------------


def abort(workspace_root: Path, migration_id: str, *, failure: FailureHook | None = None) -> AbortResult:
    """Restore the backup before the marker from durable state; restartable at every step (a) to (g)."""
    paths = _Paths.of(workspace_root)
    with _exclusive(paths):
        proposal, staged = _load_proposal(paths, migration_id)
        journal = _read_journal(paths.live_journal(migration_id))
        archived_path = paths.migration(migration_id) / MIGRATION_JOURNAL
        if journal is None:
            archived = _read_journal(archived_path)
            if archived is None or archived.state != "aborted":
                raise MigrationError(code="journal-missing", detail="this migration has no journal to abort")
            return AbortResult(archived, _remove_empty_namespace(paths))
        if journal.state in {"applied", "verified"}:
            raise MigrationError(
                code="marker-committed", detail="the format marker is committed; restoring is a user decision"
            )
        marker = proposal.marker
        if (
            marker is not None
            and marker.before_sha256 != marker.after_sha256
            and _record_digest(paths, marker.locator) == marker.after_sha256
        ):
            raise MigrationError(
                code="marker-committed", detail="the format marker is committed; restoring is a user decision"
            )
        manifest = _verify_backup(paths, proposal, journal)
        _fail(failure, "abort-after-a")
        if journal.state != "aborting":
            journal = _transition(paths, journal, "aborting")
        _fail(failure, "abort-after-b")
        _retire_manifests(paths, journal)
        _fail(failure, "abort-after-c")
        _restore_records(paths, proposal, staged)
        _fail(failure, "abort-after-d")
        _verify_restored(paths, proposal, manifest)
        _fail(failure, "abort-after-e")
        archived = journal.model_copy(update={"state": "aborted"})
        _write_file(archived_path.parent, archived_path.name, _canonical(archived))
        _fail(failure, "abort-after-archive")
        _remove_live_journal(paths, migration_id)
        _fail(failure, "abort-after-f")
        return AbortResult(archived, _remove_empty_namespace(paths))


def _retire_manifests(paths: _Paths, journal: MigrationJournal) -> None:
    """Step (c): move migration-owned manifests aside so no recovery rolls them forward over restored bytes."""
    retired = paths.migration(journal.migration_id) / "retired-transactions"
    for batch in journal.batches:
        source = _manifest_path(paths, batch.transaction_id)
        if not source.exists() and not source.is_symlink():
            continue
        content = _read_file(source.parent, source.name)
        if content is None:  # pragma: no cover - checked above under the exclusive lock.
            continue
        _write_file(retired, source.name, content)
        source.unlink()
        _fsync_directory(source.parent)


def _restore_records(paths: _Paths, proposal: MigrationProposal, staged: dict[str, bytes]) -> None:
    """Step (d): after digest → backup bytes; before digest → keep; anything else stops as corruption."""
    backup = paths.migration(proposal.migration_id) / "backup" / "records"
    positions = _classify_entries(paths, proposal)
    for entry in reversed(proposal.entries):
        if positions[entry.locator] != "after" or entry.before_sha256 == entry.after_sha256:
            continue
        relative = _runtime_relative(entry.locator)
        with _open_directory(paths.runtime) as runtime_fd:
            if entry.before_sha256 is None:
                if read_contained(runtime_fd, relative, limit=MAX_RECORD_BYTES) == staged[entry.locator]:
                    _unlink_contained(paths.runtime, relative)
                continue
            previous = _read_file(backup, entry.locator)
            if previous is None:  # pragma: no cover - verified in step (a).
                raise MigrationError(
                    code="backup-invalid", detail="a backed-up record is missing", locator=entry.locator
                )
            write_contained(runtime_fd, relative, previous, expected=staged[entry.locator], limits=_LIMITS)


def _verify_restored(paths: _Paths, proposal: MigrationProposal, manifest: MigrationBackupManifest) -> None:
    """Step (e): every affected record equals its backup and the record tree equals the backup manifest."""
    if any(position != "before" for position in _classify_entries(paths, proposal).values()):
        raise MigrationError(code="backup-invalid", detail="a record was not restored to its backup bytes")
    if record_tree_digest(paths.workspace, exclude_migrations=True) != manifest.tree:
        raise MigrationError(code="backup-invalid", detail="the restored record tree differs from the backup manifest")


def _unlink_contained(root: Path, relative: Path) -> None:
    parent = root / relative.parent
    with _open_directory(parent) as parent_fd:
        os.unlink(relative.name, dir_fd=parent_fd)
        os.fsync(parent_fd)


def _remove_live_journal(paths: _Paths, migration_id: str) -> None:
    namespace = paths.delivery / MIGRATIONS_ROOT
    with _open_directory(namespace) as namespace_fd:
        with contextlib.suppress(FileNotFoundError), _open_directory_at(namespace_fd, migration_id) as directory_fd:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(MIGRATION_JOURNAL, dir_fd=directory_fd)
            with os.scandir(directory_fd) as entries:
                temporaries = [entry.name for entry in entries if _JOURNAL_TEMPORARY.fullmatch(entry.name)]
            for name in temporaries:
                os.unlink(name, dir_fd=directory_fd)
            os.fsync(directory_fd)
        with contextlib.suppress(FileNotFoundError):
            os.rmdir(migration_id, dir_fd=namespace_fd)
        os.fsync(namespace_fd)


@contextlib.contextmanager
def _open_directory_at(parent_fd: int, name: str) -> Iterator[int]:
    descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    try:
        yield descriptor
    finally:
        os.close(descriptor)


def _remove_empty_namespace(paths: _Paths) -> bool:
    """Step (g): remove ``runtime/migrations`` only when it is a real directory with no entry (D10)."""
    try:
        with _open_directory(paths.runtime) as runtime_fd:
            info = os.stat("migrations", dir_fd=runtime_fd, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode):
                return False
            os.rmdir("migrations", dir_fd=runtime_fd)
            os.fsync(runtime_fd)
    except FileNotFoundError:
        return False
    except OSError as exc:
        if exc.errno in {errno.ENOTEMPTY, errno.EEXIST, errno.ENOTDIR}:
            return False
        raise
    return True


def _fsync_directory(directory: Path) -> None:
    with _open_directory(directory) as descriptor:
        os.fsync(descriptor)


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "MARKER_REWRITE",
    "MIGRATION_STATE_ROOT",
    "REWRITES",
    "AbortResult",
    "MigrationBackupManifest",
    "MigrationBatch",
    "MigrationEntry",
    "MigrationError",
    "MigrationJournal",
    "MigrationProposal",
    "abort",
    "apply",
    "controller_release",
    "coordination_1_to_2",
    "frontier_17_to_18",
    "propose",
    "resume",
    "verify",
]
