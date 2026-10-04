"""Fenced, copy-first migration of persisted Delivery state between registered formats.

``propose`` stages rewritten bytes outside authoritative state. ``apply`` takes the exclusive
controller lock, backs up every affected record with a record-tree hash manifest, journals
``backed-up → applying → applied`` and commits the format marker last. ``resume`` replays from
durable state, ``verify`` is the offline verifier (journal ``verified``), and ``abort`` restores
the backup before the marker from durable state only (never ``RuntimeTransaction.abort``).
"""

from __future__ import annotations

import contextlib
import contextvars
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
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a declared dependency; absence fails closed (I1).
    psutil = None

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
    PendingTransaction,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionManifestError,
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
    record_tree_digest,
    scan_capability,
    transaction_root,
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
    from collections.abc import Callable, Iterable, Iterator

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
    "repair-controller-running",
    "repair-controller-unknown",
    "repair-journal-open",
    "repair-proposal-stale",
    "repair-confirmation-required",
    "repair-not-supported",
    "repair-format-unsupported",
    "repair-corruption-stop",
    "repair-verify-mismatch",
    "repair-archived",
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
    """Staged migration whose identity binds every entry, both formats and the controller release."""

    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_format: int = Field(ge=0)
    target_format: int = Field(ge=0)
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


class RetainedJournal(_MigrationModel):
    """One retained ``verified`` migration journal a repair recorded at ``apply`` (N08 I9)."""

    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


_REPAIR_FIELDS = frozenset({"kind", "confirmed", "retained", "steps"})


class MigrationJournal(_MigrationModel):
    """Durable progress under ``runtime/migrations/<id>/journal.json``.

    Version 1 is a migration journal (its bytes stay readable by every N02 release); version 2 is a
    same-format repair journal (N08): ``confirmed`` is the operator's proposal confirmation (D9, never
    request provenance), ``retained`` the verified migration history recorded at ``apply`` and ``steps``
    the transaction manifests a replay journaled before publishing them.
    """

    schema_version: Literal[1, 2] = 1
    kind: Literal["migration", "repair"] = "migration"
    migration_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: JournalState
    source_format: int = Field(ge=0)
    target_format: int = Field(ge=0)
    backup_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    batches: tuple[MigrationBatch, ...] = ()
    confirmed: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    retained: tuple[RetainedJournal, ...] = ()
    steps: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _kind_matches_version(self) -> MigrationJournal:
        if self.schema_version == 1 and (
            self.kind != "migration" or _REPAIR_FIELDS & self.model_fields_set or self.retained or self.steps
        ):
            msg = "version 1 journals are migrations without repair fields"
            raise ValueError(msg)
        if self.schema_version == 2 and (  # noqa: PLR2004 - the repair journal version.
            self.kind != "repair" or self.batches or self.source_format != self.target_format
        ):
            msg = "version 2 journals are same-format repairs"
            raise ValueError(msg)
        return self

    def canonical_bytes(self) -> bytes:
        """Return the persisted bytes; a version-1 journal omits every repair field."""
        payload = self.model_dump(mode="json")
        if self.schema_version == 1:
            payload = {key: value for key, value in payload.items() if key not in _REPAIR_FIELDS}
        return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def upcast_migration_journal_v1(content: bytes) -> MigrationJournal:
    """Registered read-upcast: a version-1 journal is a migration journal with no repair fields."""
    journal = MigrationJournal.model_validate_json(content, strict=True)
    if journal.schema_version != 1:
        msg = "upcast applies only to version-1 journals"
        raise ValueError(msg)
    return journal


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
    _guard_write()
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
    _guard_write()
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
    proposal = _proposal(report.format, tuple(entries))
    _write_stage(paths, proposal, staged)
    return proposal


def _require_migratable(report: CapabilityReport) -> None:
    repair = next((journal for journal in report.journals if journal.kind == "repair"), None)
    if repair is not None:
        raise MigrationError(
            code="repair-journal-open",
            detail="a repair journal is open; finish it with delivery-repair",
            locator=repair.locator,
        )
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


def _owner_checked(report: CapabilityReport) -> Iterator[tuple[RecordKind, str, str]]:
    """Readable registered records with an owner model; H, O and L kinds stay outside as in the registry."""
    for record in report.records:
        kind = classify_kind(record.locator) if record.kind_id is not None else None
        if kind is None or not kind.read or not kind.owners or kind.mutability in {"H", "O", "L"}:
            continue
        if record.status in {"current", "readable-legacy"}:
            yield kind, record.locator, record.status


def owner_rejections(
    workspace_root: Path, report: CapabilityReport, *, skip: frozenset[str] = frozenset()
) -> tuple[str, ...]:
    """Locators of readable records their registered owner rejects at their declared version; never writes."""
    paths = _Paths.of(workspace_root)
    rejected = []
    for kind, locator, status in _owner_checked(report):
        if kind.kind_id in skip:
            continue
        try:
            content = _read_file(paths.delivery, locator)
            if content is not None:
                _owner_parse(kind, status, content)
        except KeyError, TypeError, ValueError, MigrationError:
            content = None
        if content is None:
            rejected.append(locator)
    return tuple(rejected)


def _validate_baseline_records(paths: _Paths, report: CapabilityReport) -> None:
    """Owner-parse every readable registered record the migration keeps, before any stage or write.

    Records needing a rewrite are validated by their rewrite; historical (H), opaque (O), transient (L)
    and unread kinds, and kinds without an owner model, stay outside this check as in the registry.
    """
    for kind, locator, status in _owner_checked(report):
        content = _read_file(paths.delivery, locator)
        if content is None:
            detail = "record disappeared while validating"
            raise MigrationError(code="proposal-stale", detail=detail, locator=locator)
        try:
            _owner_parse(kind, status, content)
        except (KeyError, TypeError, ValueError) as exc:
            raise MigrationError(
                code="record-corrupt",
                detail="record does not parse with its owner at its declared version",
                locator=locator,
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
    release: str | None = None,
    target_format: int = SUPPORTED_FORMAT,
) -> MigrationProposal:
    release = controller_release() if release is None else release
    identity = {
        "entries": [[entry.locator, entry.before_sha256, entry.after_sha256] for entry in entries],
        "release": release,
        "source_format": source_format,
        "target_format": target_format,
    }
    migration_id = _sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    return MigrationProposal(
        migration_id=migration_id,
        source_format=source_format,
        target_format=target_format,
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
        if _is_repair_proposal(content):
            raise MigrationError(code="proposal-unknown", detail="this ID names a repair; use delivery-repair") from exc
        raise MigrationError(code="proposal-invalid", detail="staged proposal is malformed") from exc
    rebuilt = _proposal(
        proposal.source_format, proposal.entries, release=proposal.release, target_format=proposal.target_format
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
        manifest_digest = _write_backup(paths, proposal.migration_id, proposal.entries)
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
    if proposal.release != controller_release() or proposal.target_format != SUPPORTED_FORMAT:
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


def _write_backup(paths: _Paths, migration_id: str, entries: tuple[MigrationEntry | RepairEntry, ...]) -> str:
    """Copy affected before bytes and the full record-tree manifest; reuse only an identical backup."""
    directory = paths.migration(migration_id)
    records = {}
    for entry in entries:
        if entry.before_sha256 is not None:
            records[entry.locator] = entry.before_sha256
    manifest = MigrationBackupManifest(
        migration_id=migration_id,
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
    _write_file(paths.runtime, relative, journal.canonical_bytes())


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
        _write_file(archived_path.parent, archived_path.name, archived.canonical_bytes())
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
    _guard_write()
    parent = root / relative.parent
    with _open_directory(parent) as parent_fd:
        os.unlink(relative.name, dir_fd=parent_fd)
        os.fsync(parent_fd)


def _remove_live_journal(paths: _Paths, migration_id: str) -> None:
    _guard_write()
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
    _guard_write()
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


# ---------------------------------------------------------------------------
# Repairs (N08-A): same-format operations of this engine (D1)
# ---------------------------------------------------------------------------
#
# A repair is a version-2 journal of kind ``repair`` in the shared namespace (I2): one fence (I1), one
# open journal, one backup. It never changes the format (I3) and commits at ``verified`` (I9), after
# which it is archived and the empty namespace is removed. ``abort`` restores the complete before-state
# from ``backed-up``, ``applying``, ``applied`` or ``aborting``.

REPAIR_OPERATIONS = ("host-local-reset", "tracked-record-restore", "transaction-replay")
type RepairOperation = Literal["host-local-reset", "tracked-record-restore", "transaction-replay"]
type RepairPolicy = Literal["engine-replay", "user-confirmed"]
type ParticipantKind = Literal["immutable", "replacement", "move"]
_REPAIR_JOURNAL_VERSION = 2
_RESERVED_PREFIXES = ("runtime/migrations", "worktrees")
_MIGRATION_ID = re.compile(r"[0-9a-f]{64}")


class RepairEntry(_MigrationModel):
    """One Delivery-root-relative path at an exact before and after digest; ``None`` means absent (D3)."""

    locator: str = Field(min_length=1)
    role: Literal["record", "participant", "manifest"] = "record"
    manifest: str | None = None
    before_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    after_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _changes_one_path(self) -> RepairEntry:
        # A C03 participant already at its after-state (or an absent move source) stays bound unchanged (I4).
        if self.before_sha256 == self.after_sha256 and self.role != "participant":
            msg = "a repair entry must change its path"
            raise ValueError(msg)
        _delivery_relative(self.locator)
        return self


class RepairManifest(_MigrationModel):
    """One pending ``RuntimeTransaction`` manifest of a registered root, bound by digest (C03)."""

    locator: str = Field(min_length=1)
    root: str = Field(min_length=1)
    validator: Literal["generic", "contained"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RepairParticipant(_MigrationModel):
    """One participant of a pending manifest: its kind, destination and move source (C03)."""

    manifest: str = Field(min_length=1)
    kind: ParticipantKind
    destination: str = Field(min_length=1)
    source: str | None = None


class RepairFindingPrint(_MigrationModel):
    """One classified finding as I9 compares it: ID, code, explicit locator and a digest of everything else."""

    finding_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    detail_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def identity(self) -> tuple[str, str, str, str]:
        """Return the fields in canonical order."""
        return (self.finding_id, self.code, self.locator, self.detail_sha256)


class RepairProposal(_MigrationModel):
    """Staged repair whose identity binds every path digest, the manifest set, the format and the release."""

    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation: RepairOperation
    operation_version: Literal[1] = 1
    finding_id: str = Field(min_length=1)
    format: int = Field(ge=0)
    release: str = Field(min_length=1)
    policy: RepairPolicy
    consequence: str = Field(min_length=1)
    entries: tuple[RepairEntry, ...] = Field(min_length=1)
    manifests: tuple[RepairManifest, ...] = ()
    participants: tuple[RepairParticipant, ...] = ()
    findings: tuple[RepairFindingPrint, ...] = ()

    @property
    def migration_id(self) -> str:
        """Return the journal ID, which is the proposal ID."""
        return self.proposal_id


def repair_proposal(  # noqa: PLR0913 - the identity binds each field explicitly.
    *,
    operation: RepairOperation,
    finding_id: str,
    format_value: int,
    policy: RepairPolicy,
    consequence: str,
    entries: tuple[RepairEntry, ...],
    manifests: tuple[RepairManifest, ...] = (),
    participants: tuple[RepairParticipant, ...] = (),
    findings: tuple[RepairFindingPrint, ...] = (),
    release: str | None = None,
) -> RepairProposal:
    """Build a proposal whose ID is the SHA-256 of its canonical identity."""
    release = controller_release() if release is None else release
    findings = tuple(sorted(findings, key=RepairFindingPrint.identity))
    identity = {
        "entries": sorted(
            [entry.locator, entry.before_sha256 or "absent", entry.after_sha256 or "absent"] for entry in entries
        ),
        "finding_id": finding_id,
        "findings": [list(item.identity()) for item in findings],
        "format": format_value,
        "manifests": [[manifest.locator, manifest.sha256] for manifest in manifests],
        "operation": operation,
        "operation_version": 1,
        "participants": [[item.kind, item.destination, item.source] for item in participants],
        "policy": policy,
        "release": release,
    }
    proposal_id = _sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    return RepairProposal(
        proposal_id=proposal_id,
        operation=operation,
        finding_id=finding_id,
        format=format_value,
        release=release,
        policy=policy,
        consequence=consequence,
        entries=entries,
        manifests=manifests,
        participants=participants,
        findings=findings,
    )


def _delivery_relative(locator: str) -> Path:
    relative = Path(locator)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
        or any(locator == prefix or locator.startswith(f"{prefix}/") for prefix in _RESERVED_PREFIXES)
    ):
        msg = "repair path escapes the Delivery root"
        raise ValueError(msg)
    return relative


def _is_repair_proposal(content: bytes) -> bool:
    try:
        RepairProposal.model_validate_json(content, strict=True)
    except ValidationError:
        return False
    return True


def _repair_error(*, code: MigrationErrorCode, detail: str, locator: str | None = None) -> MigrationError:
    return MigrationError(code=code, detail=detail, locator=locator)


def write_repair_stage(workspace_root: Path, proposal: RepairProposal, staged: dict[str, bytes]) -> None:
    """Stage after bytes and the proposal outside authoritative state; an identical stage is reused."""
    paths = _Paths.of(workspace_root)
    directory = paths.migration(proposal.proposal_id)
    if directory.exists() or directory.is_symlink():
        existing, _staged = load_repair_proposal(workspace_root, proposal.proposal_id)
        if existing != proposal:  # pragma: no cover - the identity binds every field.
            raise _repair_error(code="repair-proposal-stale", detail="staged proposal differs from its identity")
        if _read_journal(directory / MIGRATION_JOURNAL) is not None:
            raise _repair_error(
                code="repair-archived", detail="this repair is archived; its ID accepts only verify or abort"
            )
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


def load_repair_proposal(workspace_root: Path, proposal_id: str) -> tuple[RepairProposal, dict[str, bytes]]:
    """Load one staged repair, verifying its identity and every staged after digest."""
    paths = _Paths.of(workspace_root)
    if _MIGRATION_ID.fullmatch(proposal_id) is None:
        raise _repair_error(code="repair-not-supported", detail="the repair ID is invalid")
    directory = paths.migration(proposal_id)
    content = _read_file(directory, "proposal.json") if directory.is_dir() and not directory.is_symlink() else None
    if content is None:
        raise _repair_error(code="repair-not-supported", detail="no staged repair has this ID")
    try:
        proposal = RepairProposal.model_validate_json(content, strict=True)
    except ValidationError as exc:
        raise _repair_error(
            code="repair-not-supported",
            detail="this ID is not a repair; repair commands never operate on migration IDs",
        ) from exc
    rebuilt = repair_proposal(
        operation=proposal.operation,
        finding_id=proposal.finding_id,
        format_value=proposal.format,
        policy=proposal.policy,
        consequence=proposal.consequence,
        entries=proposal.entries,
        manifests=proposal.manifests,
        participants=proposal.participants,
        findings=proposal.findings,
        release=proposal.release,
    )
    if proposal.proposal_id != proposal_id or rebuilt != proposal:
        raise _repair_error(code="repair-proposal-stale", detail="staged repair does not match its identity")
    staged = {}
    for entry in proposal.entries:
        if entry.role != "record" or entry.after_sha256 is None:
            continue
        after = _read_file(directory / "stage", entry.locator)
        if after is None or _sha256(after) != entry.after_sha256:
            raise _repair_error(
                code="repair-proposal-stale", detail="staged bytes do not match their digest", locator=entry.locator
            )
        staged[entry.locator] = after
    return proposal, staged


# --- Controller exclusion (I1) ----------------------------------------------


_CONTROLLER_MODULES = ("owlbear_delivery_mcp", "owlbear_cockpit")
_CONTROLLER_SCRIPTS = frozenset({"cockpit", "delivery-mcp"})
_WRAPPERS = frozenset({"sh", "bash", "zsh", "dash", "fish", "env"})
_UV_VALUE_OPTIONS = frozenset(
    {"--project", "--directory", "--python", "-p", "--with", "--package", "--env-file", "--group", "--extra"}
)


class ControllerProcessUnreadableError(RuntimeError):
    """One process attribute could not be read; I1 fails closed on it."""


class ControllerProcessVanishedError(RuntimeError):
    """The process exited while it was observed."""


class ControllerProcess(Protocol):
    """One same-user process as I1 judges it; methods raise the two errors above."""

    @property
    def pid(self) -> int:
        """Return the process ID."""
        ...

    @property
    def name(self) -> str:
        """Return the process name."""
        ...

    def cmdline(self) -> tuple[str, ...]:
        """Return the argument vector, for local judgement only."""
        ...

    def cwd(self) -> Path | None:
        """Return the working directory."""
        ...


type ControllerProcessSource = Callable[[], Iterable[ControllerProcess]]


class _PsutilControllerProcess:
    def __init__(self, process: psutil.Process, name: str) -> None:
        self._process = process
        self._name = name

    @property
    def pid(self) -> int:
        return int(self._process.pid)

    @property
    def name(self) -> str:
        return self._name

    def _read[T](self, read: Callable[[], T]) -> T:
        try:
            return read()
        except psutil.NoSuchProcess as exc:  # Includes zombies.
            raise ControllerProcessVanishedError from exc
        except (psutil.Error, OSError) as exc:
            raise ControllerProcessUnreadableError(type(exc).__name__) from exc

    def cmdline(self) -> tuple[str, ...]:
        return tuple(self._read(self._process.cmdline))

    def cwd(self) -> Path | None:
        cwd = self._read(self._process.cwd)
        return Path(cwd) if cwd else None


def psutil_controller_processes() -> Iterator[ControllerProcess]:
    """Yield every process of the current user except this one; owner-unknown ones are unreadable."""
    if psutil is None:
        msg = "process table is unavailable"
        raise ControllerProcessUnreadableError(msg)
    own_pid, own_uid = os.getpid(), os.getuid()
    try:
        processes = tuple(psutil.process_iter(("pid", "name", "uids")))
    except (psutil.Error, OSError) as exc:
        raise ControllerProcessUnreadableError(type(exc).__name__) from exc
    for process in processes:
        info = process.info
        uids = info.get("uids")
        if info.get("pid") == own_pid or (uids is not None and uids.real != own_uid):
            continue
        yield (
            _UnknownOwnerProcess(process, info.get("name") or "")
            if uids is None
            else _PsutilControllerProcess(process, info.get("name") or "")
        )


class _UnknownOwnerProcess(_PsutilControllerProcess):
    def cmdline(self) -> tuple[str, ...]:
        msg = "process owner is unknown"
        raise ControllerProcessUnreadableError(msg)


def _executable(argument: str) -> str:
    return Path(argument).name.lower()


def _controller_module(module: str) -> bool:
    return any(module == name or module.startswith(f"{name}.") for name in _CONTROLLER_MODULES)


def _uv_command(argv: tuple[str, ...]) -> tuple[str, ...]:
    """Return the command ``uv run`` executes, after its options; empty when it is not ``uv run``."""
    if "run" not in argv:
        return ()
    index = argv.index("run") + 1
    while index < len(argv) and argv[index].startswith("-"):
        index += 2 if argv[index] in _UV_VALUE_OPTIONS else 1
    return argv[index:]


def _runs_controller_module(argv: tuple[str, ...]) -> bool:
    """``-m owlbear_delivery_mcp`` or ``-m owlbear_cockpit`` (or a submodule), separate or joined."""
    for index, argument in enumerate(argv):
        if argument == "-m" and index + 1 < len(argv) and _controller_module(argv[index + 1]):
            return True
        if argument.startswith("-m") and len(argument) > 2 and _controller_module(argument[2:]):  # noqa: PLR2004
            return True
    return False


def supported_controller_form(argv: tuple[str, ...]) -> bool:
    """Return whether an argument vector runs a Delivery controller in a supported form (I1)."""
    if not argv or _runs_controller_module(argv):
        return bool(argv)
    first = _executable(argv[0])
    if first in _CONTROLLER_SCRIPTS:
        return True
    if first in {"uv", "uvx"}:
        command = _uv_command(argv)
        return bool(command) and supported_controller_form(command)
    if (first.startswith("python") or first in _WRAPPERS) and len(argv) > 1:
        return _executable(argv[1]) in _CONTROLLER_SCRIPTS
    return False


def _candidate_name(name: str) -> bool:
    normalized = name.lower()
    return normalized.startswith("python") or normalized in {"uv", "uvx", *_CONTROLLER_SCRIPTS}


def _within(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved == root or resolved.is_relative_to(root)


def _controller_verdict(paths: _Paths, process: ControllerProcess) -> Literal["running", "unknown"] | None:
    """No process is exempt: process metadata is same-user writable, so it cannot prove a gated controller."""
    candidate = _candidate_name(process.name)
    if not candidate and process.name.lower() not in _WRAPPERS:
        return None
    try:
        argv = process.cmdline()
        if not supported_controller_form(argv):
            return None
        cwd = process.cwd()
    except ControllerProcessVanishedError:
        return None
    except ControllerProcessUnreadableError:
        return "unknown" if candidate else None
    if cwd is None or not _within(cwd, paths.workspace):
        return None
    return "running"


def require_no_controller_process(workspace_root: Path, source: ControllerProcessSource | None = None) -> None:
    """Refuse while any controller-like process runs in the workspace (I1; no process is exempt)."""
    paths = _Paths.of(workspace_root)
    try:
        processes = tuple((source or psutil_controller_processes)())
    except ControllerProcessUnreadableError as exc:
        raise _repair_error(code="repair-controller-unknown", detail="the process table could not be scanned") from exc
    verdicts = {_controller_verdict(paths, process) for process in processes}
    if "running" in verdicts:
        raise _repair_error(
            code="repair-controller-running", detail="a Delivery controller runs in this workspace; stop it"
        )
    if "unknown" in verdicts:
        raise _repair_error(
            code="repair-controller-unknown",
            detail="a Python, uv or controller process could not be inspected; stop it",
        )


@contextlib.contextmanager
def _repair_fence(paths: _Paths, source: ControllerProcessSource | None) -> Iterator[ControllerLock]:
    """Exclusive lock plus a process scan now and immediately before every repair write (I1)."""
    try:
        lock = acquire_controller_lock(paths.runtime, exclusive=True)
    except ControllerFencedError as exc:
        raise _repair_error(
            code="repair-controller-running", detail="a Delivery controller holds the workspace lock"
        ) from exc
    token = None
    try:
        require_no_controller_process(paths.workspace, source)
        token = _WRITE_GUARD.set(lambda: require_no_controller_process(paths.workspace, source))
        yield lock
    finally:
        if token is not None:
            _WRITE_GUARD.reset(token)
        lock.release()


# Ungated (format-0) controllers take no lock, so a repair rescans before each write; migrations leave it unset.
_WRITE_GUARD: contextvars.ContextVar[Callable[[], None] | None] = contextvars.ContextVar(
    "repair_write_guard", default=None
)


def _guard_write() -> None:
    guard = _WRITE_GUARD.get()
    if guard is not None:
        guard()


# --- Journal set (I2, I9) ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class LiveJournal:
    """One entry of ``runtime/migrations``: its parsed journal and exact bytes, or ``None`` when invalid."""

    locator: str
    migration_id: str | None
    journal: MigrationJournal | None
    sha256: str | None


def live_journals(workspace_root: Path) -> tuple[LiveJournal, ...]:
    """Read every entry of the shared journal namespace; anything that is not a journal is invalid."""
    paths = _Paths.of(workspace_root)
    namespace = paths.delivery / MIGRATIONS_ROOT
    if not namespace.exists() and not namespace.is_symlink():
        return ()
    if namespace.is_symlink() or not namespace.is_dir():
        return (LiveJournal(MIGRATIONS_ROOT, None, None, None),)
    journals = []
    for child in sorted(namespace.iterdir()):
        locator = f"{MIGRATIONS_ROOT}/{child.name}"
        valid_directory = _MIGRATION_ID.fullmatch(child.name) and child.is_dir() and not child.is_symlink()
        names = (
            [name.name for name in child.iterdir() if not _JOURNAL_TEMPORARY.fullmatch(name.name)]
            if valid_directory
            else []
        )
        content = _read_raw(child, MIGRATION_JOURNAL) if names == [MIGRATION_JOURNAL] else None
        journal = _parse_journal(content, child.name) if content is not None else None
        sha256 = _sha256(content) if content is not None and journal is not None else None
        journals.append(LiveJournal(locator, child.name if valid_directory else None, journal, sha256))
    return tuple(journals)


def _read_raw(directory: Path, name: str) -> bytes | None:
    try:
        return _read_file(directory, name)
    except MigrationError:
        return None


def _parse_journal(content: bytes, migration_id: str) -> MigrationJournal | None:
    try:
        journal = MigrationJournal.model_validate_json(content, strict=True)
    except ValidationError, ValueError:
        return None
    return journal if journal.migration_id == migration_id and journal.canonical_bytes() == content else None


def require_no_open_journal(workspace_root: Path) -> tuple[RetainedJournal, ...]:
    """Refuse ``repair-journal-open`` unless every journal is retained verified migration history."""
    retained = []
    for entry in live_journals(workspace_root):
        journal = entry.journal
        if journal is None or journal.kind != "migration" or journal.state != "verified" or entry.sha256 is None:
            raise _repair_error(
                code="repair-journal-open", detail="an unfinished or invalid journal is open", locator=entry.locator
            )
        retained.append(RetainedJournal(migration_id=journal.migration_id, sha256=entry.sha256))
    return tuple(retained)


def _require_journal_set(workspace_root: Path, journal: MigrationJournal) -> None:
    """I9: every journal other than J is valid verified migration history that ``apply`` recorded in J."""
    others = set()
    for entry in live_journals(workspace_root):
        if entry.migration_id == journal.migration_id:
            continue
        current = entry.journal
        if current is None or current.kind != "migration" or current.state != "verified" or entry.sha256 is None:
            raise _repair_error(
                code="repair-verify-mismatch", detail="another journal is open, invalid or added", locator=entry.locator
            )
        others.add((current.migration_id, entry.sha256))
    if others != {(item.migration_id, item.sha256) for item in journal.retained}:
        raise _repair_error(code="repair-verify-mismatch", detail="retained migration history changed since apply")


# --- Path digests and writes ----------------------------------------------------


def _path_digest(paths: _Paths, locator: str) -> str | None:
    try:
        content = _read_file(paths.delivery, _delivery_relative(locator))
    except MigrationError as exc:
        raise _repair_error(
            code="repair-corruption-stop", detail="a repair path is not a readable regular file", locator=locator
        ) from exc
    return None if content is None else _sha256(content)


def path_digest(workspace_root: Path, locator: str) -> str | None:
    """Return the SHA-256 of one Delivery-root-relative regular file (no link followed), ``None`` when absent."""
    return _path_digest(_Paths.of(workspace_root), locator)


def _position(paths: _Paths, entry: RepairEntry) -> Literal["before", "after"]:
    digest = _path_digest(paths, entry.locator)
    if digest == entry.after_sha256:
        return "after"
    if digest == entry.before_sha256:
        return "before"
    raise _repair_error(
        code="repair-corruption-stop",
        detail="path matches neither its before nor its after digest; every copy is preserved",
        locator=entry.locator,
    )


def _put(paths: _Paths, locator: str, content: bytes, expected: bytes | None) -> None:
    _guard_write()
    relative = _delivery_relative(locator)
    with _open_directory(paths.delivery) as delivery_fd:
        write_contained(delivery_fd, relative, content, expected=expected, limits=_LIMITS)


def _remove(paths: _Paths, locator: str) -> None:
    _unlink_contained(paths.delivery, _delivery_relative(locator))


def _backup_bytes(paths: _Paths, proposal: RepairProposal, locator: str) -> bytes:
    content = _read_file(paths.migration(proposal.proposal_id) / "backup" / "records", locator)
    if content is None:
        raise _repair_error(code="repair-corruption-stop", detail="a backed-up path is missing", locator=locator)
    return content


def _verify_repair_backup(
    paths: _Paths, proposal: RepairProposal, journal: MigrationJournal
) -> MigrationBackupManifest:
    try:
        manifest = _read_backup_manifest(paths, journal)
        _verify_backup_records(paths.migration(proposal.proposal_id) / "backup", manifest)
    except (MigrationError, ValidationError) as exc:
        raise _repair_error(code="repair-corruption-stop", detail="the repair backup is missing or altered") from exc
    expected = {entry.locator: entry.before_sha256 for entry in proposal.entries if entry.before_sha256}
    if manifest.records != expected or manifest.migration_id != proposal.proposal_id:
        raise _repair_error(code="repair-corruption-stop", detail="the backup manifest does not match the repair")
    return manifest


# --- Apply and resume ---------------------------------------------------------


def apply_repair(  # noqa: PLR0913 - fence inputs and test hooks are explicit keywords.
    workspace_root: Path,
    proposal_id: str,
    *,
    confirm: str | None = None,
    current: Callable[[Path, RepairProposal], RepairProposal] | None = None,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Back up, journal and apply one staged repair under the fence (I1, I4); never changes the format.

    ``current`` re-derives the proposal from disk; any difference is ``repair-proposal-stale`` (I4).
    """
    paths = _Paths.of(workspace_root)
    proposal, staged = load_repair_proposal(paths.workspace, proposal_id)
    if proposal.policy == "user-confirmed" and confirm != proposal.proposal_id:
        raise _repair_error(
            code="repair-confirmation-required",
            detail="this repair replaces user-owned or tracked bytes; confirm its ID",
        )
    with _repair_fence(paths, processes):
        if _read_journal(paths.migration(proposal_id) / MIGRATION_JOURNAL) is not None:
            raise _repair_error(
                code="repair-archived", detail="this repair is archived; its ID accepts only verify or abort"
            )
        retained = require_no_open_journal(paths.workspace)
        _require_repair_current(paths, proposal, current)
        try:
            manifest_digest = _write_backup(paths, proposal.proposal_id, proposal.entries)
        except MigrationError as exc:
            raise _repair_error(code="repair-proposal-stale", detail=exc.detail, locator=exc.locator) from exc
        _fail(failure, "before-journal")
        journal = MigrationJournal(
            schema_version=_REPAIR_JOURNAL_VERSION,
            kind="repair",
            migration_id=proposal.proposal_id,
            state="backed-up",
            source_format=proposal.format,
            target_format=proposal.format,
            backup_manifest_sha256=manifest_digest,
            confirmed=confirm if proposal.policy == "user-confirmed" else None,
            retained=retained,
        )
        _write_live_journal(paths, journal)
        _fail(failure, "after-backup")
        return _drive_repair(paths, proposal, staged, journal, failure)


def _require_repair_current(
    paths: _Paths, proposal: RepairProposal, current: Callable[[Path, RepairProposal], RepairProposal] | None
) -> None:
    report = scan_capability(paths.workspace)
    if report.format_status == "newer":
        raise _repair_error(
            code="repair-format-unsupported",
            detail="Delivery state is newer than this controller",
            locator=FORMAT_MARKER,
        )
    if report.format != proposal.format:
        raise _repair_error(code="repair-proposal-stale", detail="the workspace format changed since the proposal")
    if proposal.operation != "transaction-replay" and (pending := _pending_transaction_manifests(paths)):
        raise _repair_error(
            code="repair-proposal-stale",
            detail="a RuntimeTransaction manifest is pending; only transaction-replay (C03) may run first",
            locator=pending[0],
        )
    for entry in proposal.entries:
        if _path_digest(paths, entry.locator) != entry.before_sha256:
            raise _repair_error(
                code="repair-proposal-stale", detail="a path changed since the proposal", locator=entry.locator
            )
    if current is not None:
        try:
            observed = current(paths.workspace, proposal)
        except MigrationError as exc:
            raise _repair_error(code="repair-proposal-stale", detail=exc.detail, locator=exc.locator) from exc
        if observed != proposal:
            raise _repair_error(code="repair-proposal-stale", detail="the repaired state changed since the proposal")


def resume_repair(
    workspace_root: Path,
    proposal_id: str,
    *,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Continue a crashed repair apply from durable state; ``applied`` and ``verified`` converge unchanged."""
    paths = _Paths.of(workspace_root)
    with _repair_fence(paths, processes):
        journal = _require_repair_journal(paths, proposal_id)
        if journal.state == "aborting":
            raise _repair_error(code="repair-journal-open", detail="an aborting repair accepts only abort")
        if journal.state in {"applied", "verified"}:
            return journal
        proposal, staged = load_repair_proposal(paths.workspace, proposal_id)
        _verify_repair_backup(paths, proposal, journal)
        return _drive_repair(paths, proposal, staged, journal, failure)


def _require_repair_journal(
    paths: _Paths, proposal_id: str, *, invalid: MigrationErrorCode = "repair-corruption-stop"
) -> MigrationJournal:
    journal = _repair_journal_or_invalid(paths, proposal_id)
    if journal is None:
        raise _repair_error(code=invalid, detail="the repair journal is unreadable or invalid")
    return journal


def _repair_journal_or_invalid(paths: _Paths, proposal_id: str) -> MigrationJournal | None:
    """Return the live repair journal, or ``None`` when it exists but is unreadable or invalid."""
    load_repair_proposal(paths.workspace, proposal_id)
    try:
        journal = _read_journal(paths.live_journal(proposal_id))
    except MigrationError:
        return None
    if journal is None:
        if _read_journal(paths.migration(proposal_id) / MIGRATION_JOURNAL) is not None:
            raise _repair_error(
                code="repair-archived", detail="this repair is archived; its ID accepts only verify or abort"
            )
        raise _repair_error(code="repair-not-supported", detail="this repair has no journal; run apply")
    if journal.kind != "repair" or journal.migration_id != proposal_id:
        return None
    return journal


def _rebuilt_aborting_journal(paths: _Paths, proposal: RepairProposal) -> MigrationJournal:
    """An invalid J is replaced by an ``aborting`` journal bound to the existing backup (digest-checked abort)."""
    content = _read_file(paths.migration(proposal.proposal_id) / "backup", "manifest.json")
    if content is None:
        raise _repair_error(code="repair-corruption-stop", detail="the repair backup is missing")
    journal = MigrationJournal(
        schema_version=_REPAIR_JOURNAL_VERSION,
        kind="repair",
        migration_id=proposal.proposal_id,
        state="aborting",
        source_format=proposal.format,
        target_format=proposal.format,
        backup_manifest_sha256=_sha256(content),
    )
    try:
        _write_live_journal(paths, journal)
    except (OSError, TransactionPathError, TransactionConflictError) as exc:
        raise _repair_error(code="repair-corruption-stop", detail="the repair journal path is unsafe") from exc
    return journal


def _drive_repair(
    paths: _Paths,
    proposal: RepairProposal,
    staged: dict[str, bytes],
    journal: MigrationJournal,
    failure: FailureHook | None,
) -> MigrationJournal:
    for entry in proposal.entries:
        _position(paths, entry)
    if journal.state == "backed-up":
        journal = _transition(paths, journal, "applying")
    if proposal.operation == "transaction-replay":
        journal = _replay_manifests(paths, proposal, journal, failure)
    else:
        for index, entry in enumerate(proposal.entries):
            if _position(paths, entry) == "before":
                expected = _backup_bytes(paths, proposal, entry.locator) if entry.before_sha256 else None
                _put(paths, entry.locator, staged[entry.locator], expected)
                _fail(failure, f"after-replacement-{index}")
    if any(_position(paths, entry) != "after" for entry in proposal.entries):  # pragma: no cover - invariant.
        raise _repair_error(code="repair-corruption-stop", detail="the repair did not converge")
    _fail(failure, "before-applied")
    return _transition(paths, journal, "applied")


def _manifest_root(paths: _Paths, manifest: RepairManifest) -> Path:
    return paths.delivery / _delivery_relative(manifest.root)


def pending_from_backup(paths_root: Path, manifest: RepairManifest, content: bytes) -> PendingTransaction:
    """Rebuild one manifest's transaction from its verified bytes with its root's owner validator."""
    paths = _Paths.of(paths_root)
    root = _manifest_root(paths, manifest)
    registered = transaction_root(manifest.root)
    if registered is None or registered.validator != manifest.validator:
        raise _repair_error(
            code="repair-corruption-stop", detail="manifest root is not registered", locator=manifest.locator
        )
    allowed = tuple(root if item == "." else paths.delivery / item for item in registered.participant_roots)
    try:
        return RuntimeTransaction.pending_from_content(
            root, Path(manifest.locator).name, content, roots=allowed, contained=manifest.validator == "contained"
        )
    except (TransactionManifestError, TransactionPathError) as exc:
        raise _repair_error(
            code="repair-corruption-stop", detail="manifest fails its owner validator", locator=manifest.locator
        ) from exc


def _replay_manifests(
    paths: _Paths, proposal: RepairProposal, journal: MigrationJournal, failure: FailureHook | None
) -> MigrationJournal:
    """One journaled step per manifest, replayed from its verified backed-up bytes (D1)."""
    for index, manifest in enumerate(proposal.manifests):
        if manifest.locator not in journal.steps:
            journal = journal.model_copy(update={"steps": (*journal.steps, manifest.locator)})
            _write_live_journal(paths, journal)
            _fail(failure, f"before-replay-{index}")
        digest = _path_digest(paths, manifest.locator)
        if digest == manifest.sha256:
            pending = pending_from_backup(paths.workspace, manifest, _backup_bytes(paths, proposal, manifest.locator))
            _guard_write()
            try:
                pending.replay(failure=_batch_hook(failure, index), guard=_guard_write)
            except (TransactionConflictError, TransactionPathError, TransactionManifestError, OSError) as exc:
                raise _repair_error(
                    code="repair-corruption-stop", detail="a participant conflicts with the replay"
                ) from exc
            _fail(failure, f"after-replay-{index}")
        elif digest is not None:
            raise _repair_error(
                code="repair-corruption-stop", detail="a manifest changed during the replay", locator=manifest.locator
            )
        participants = [entry for entry in proposal.entries if entry.manifest == manifest.locator]
        if any(_position(paths, entry) != "after" for entry in participants):
            raise _repair_error(
                code="repair-corruption-stop",
                detail="a removed manifest left a path before its replay",
                locator=manifest.locator,
            )
    return journal


# --- Verify (I9) ----------------------------------------------------------------


type RepairCheck = Callable[[Path, RepairProposal], None]
type RepairClassifier = Callable[[Path, str], tuple[RepairFindingPrint, ...]]


def verify_repair(  # noqa: PLR0913 - the I9 checks and test hooks are explicit keywords.
    workspace_root: Path,
    proposal_id: str,
    *,
    owner_check: RepairCheck,
    classify: RepairClassifier,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> MigrationJournal:
    """Scoped offline verification bound to journal J, then archive and namespace cleanup (I3, I9).

    ``owner_check`` raises ``ValueError`` when the addressed owner still rejects its record;
    ``classify`` returns complete finding fingerprints in the verification context bound to J.
    """
    paths = _Paths.of(workspace_root)
    with _repair_fence(paths, processes):
        archived = _archived_repair(paths, proposal_id)
        if archived is not None:
            if archived.state != "verified":
                raise _repair_error(code="repair-archived", detail="this repair was aborted; only abort accepts its ID")
            _remove_empty_namespace(paths)
            return archived
        journal = _require_repair_journal(paths, proposal_id, invalid="repair-verify-mismatch")
        proposal, _staged = load_repair_proposal(paths.workspace, proposal_id)
        if journal.state == "verified":
            return _archive_repair(paths, journal, failure)
        if journal.state != "applied":
            raise _repair_error(
                code="repair-journal-open", detail=f"verify requires an applied repair journal, not {journal.state}"
            )
        manifest = _verify_repair_backup(paths, proposal, journal)
        _require_journal_set(paths.workspace, journal)
        _require_repair_postcondition(paths, proposal, manifest, owner_check)
        observed = frozenset(classify(paths.workspace, proposal_id))
        expected = _expected_findings(proposal, observed)
        if observed != expected:
            added = sorted(item.finding_id for item in observed - expected)
            raise _repair_error(
                code="repair-verify-mismatch",
                detail="classification differs from the proposal-time findings minus the addressed one",
                locator=added[0] if added else None,
            )
        _fail(failure, "before-verified")
        journal = _transition(paths, journal, "verified")
        _fail(failure, "after-verified")
        return _archive_repair(paths, journal, failure)


def _expected_findings(
    proposal: RepairProposal, observed: frozenset[RepairFindingPrint]
) -> frozenset[RepairFindingPrint]:
    """Proposal-time fingerprints minus the addressed finding and A2's resolved ones.

    A2: only a finding that no longer appears at all and whose explicit locator is a path this repair
    changed may resolve with it (a C03 replay of a C01 record). A fingerprint that changed under the same
    ID, a new finding or any other disappearance still differs.
    """
    affected = {entry.locator for entry in proposal.entries if entry.before_sha256 != entry.after_sha256}
    remaining = {item for item in proposal.findings if item.finding_id != proposal.finding_id}
    observed_ids = {item.finding_id for item in observed}
    resolved = {item for item in remaining if item.finding_id not in observed_ids and item.locator in affected}
    return frozenset(remaining - resolved)


def _archived_repair(paths: _Paths, proposal_id: str) -> MigrationJournal | None:
    """Return an archived repair journal only when no live journal (valid or not) holds this ID."""
    load_repair_proposal(paths.workspace, proposal_id)
    live = paths.live_journal(proposal_id)
    if live.exists() or live.is_symlink():
        return None
    return _read_journal(paths.migration(proposal_id) / MIGRATION_JOURNAL)


def _require_repair_postcondition(
    paths: _Paths, proposal: RepairProposal, manifest: MigrationBackupManifest, owner_check: RepairCheck
) -> None:
    for entry in proposal.entries:
        if _path_digest(paths, entry.locator) != entry.after_sha256:
            raise _repair_error(
                code="repair-verify-mismatch",
                detail="a repaired path is not at its after digest",
                locator=entry.locator,
            )
    try:
        owner_check(paths.workspace, proposal)
    except (TypeError, ValueError) as exc:
        raise _repair_error(
            code="repair-verify-mismatch", detail="the owner still rejects the repaired record"
        ) from exc
    expected = dict(manifest.tree)
    for entry in proposal.entries:
        kind = classify_kind(entry.locator)
        if kind is not None and kind.mutability == "L":
            continue
        if entry.after_sha256 is None:
            expected.pop(entry.locator, None)
        else:
            expected[entry.locator] = entry.after_sha256
    actual = record_tree_digest(paths.workspace, exclude_migrations=True)
    differing = sorted(
        locator for locator in expected.keys() | actual.keys() if expected.get(locator) != actual.get(locator)
    )
    if differing:
        raise _repair_error(
            code="repair-verify-mismatch", detail="a record outside the repair changed", locator=differing[0]
        )


def _archive_repair(paths: _Paths, journal: MigrationJournal, failure: FailureHook | None) -> MigrationJournal:
    """Archive J beside its backup, remove the live journal, then the empty namespace (I3)."""
    archived = paths.migration(journal.migration_id) / MIGRATION_JOURNAL
    _write_file(archived.parent, archived.name, journal.canonical_bytes())
    _fail(failure, "after-archive")
    _remove_live_journal(paths, journal.migration_id)
    _fail(failure, "after-live-removed")
    _remove_empty_namespace(paths)
    return journal


# --- Abort ------------------------------------------------------------------------


def abort_repair(
    workspace_root: Path,
    proposal_id: str,
    *,
    processes: ControllerProcessSource | None = None,
    failure: FailureHook | None = None,
) -> AbortResult:
    """Restore the complete before-state from the backup; restartable at every step; refused after verify."""
    paths = _Paths.of(workspace_root)
    with _repair_fence(paths, processes):
        archived = _archived_repair(paths, proposal_id)
        if archived is not None:
            if archived.state != "aborted":
                raise _repair_error(
                    code="repair-archived", detail="this repair is verified; only verify accepts its ID"
                )
            return AbortResult(archived, _remove_empty_namespace(paths))
        journal = _repair_journal_or_invalid(paths, proposal_id)
        proposal, _staged = load_repair_proposal(paths.workspace, proposal_id)
        if journal is None:
            journal = _rebuilt_aborting_journal(paths, proposal)
        if journal.state == "verified":
            raise _repair_error(
                code="repair-journal-open", detail="a verified repair is committed; run verify to archive it"
            )
        manifest = _verify_repair_backup(paths, proposal, journal)
        _fail(failure, "abort-after-a")
        if journal.state != "aborting":
            journal = _transition(paths, journal, "aborting")
        _fail(failure, "abort-after-b")
        _restore_repair(paths, proposal)
        _fail(failure, "abort-after-c")
        if any(_path_digest(paths, entry.locator) != entry.before_sha256 for entry in proposal.entries) or (
            record_tree_digest(paths.workspace, exclude_migrations=True) != manifest.tree
        ):
            raise _repair_error(code="repair-corruption-stop", detail="the restored state differs from the backup")
        _fail(failure, "abort-after-d")
        archived_journal = journal.model_copy(update={"state": "aborted"})
        archive = paths.migration(proposal_id) / MIGRATION_JOURNAL
        _write_file(archive.parent, archive.name, archived_journal.canonical_bytes())
        _fail(failure, "abort-after-archive")
        _remove_live_journal(paths, proposal_id)
        _fail(failure, "abort-after-e")
        return AbortResult(archived_journal, _remove_empty_namespace(paths))


def _restore_repair(paths: _Paths, proposal: RepairProposal) -> None:
    """Records and participants in reverse order, then the original manifests (D1, D3)."""
    ordered = [entry for entry in reversed(proposal.entries) if entry.role != "manifest"]
    ordered += [entry for entry in proposal.entries if entry.role == "manifest"]
    for entry in ordered:
        if _position(paths, entry) == "before" or entry.before_sha256 == entry.after_sha256:
            continue
        if entry.before_sha256 is None:
            _remove(paths, entry.locator)
            continue
        current = _read_file(paths.delivery, entry.locator)
        _put(paths, entry.locator, _backup_bytes(paths, proposal, entry.locator), current)


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "MARKER_REWRITE",
    "MIGRATION_STATE_ROOT",
    "REPAIR_OPERATIONS",
    "REWRITES",
    "AbortResult",
    "ControllerProcess",
    "ControllerProcessUnreadableError",
    "ControllerProcessVanishedError",
    "LiveJournal",
    "MigrationBackupManifest",
    "MigrationBatch",
    "MigrationEntry",
    "MigrationError",
    "MigrationJournal",
    "MigrationProposal",
    "RepairEntry",
    "RepairFindingPrint",
    "RepairManifest",
    "RepairParticipant",
    "RepairProposal",
    "RetainedJournal",
    "abort",
    "abort_repair",
    "apply",
    "apply_repair",
    "controller_release",
    "coordination_1_to_2",
    "frontier_17_to_18",
    "live_journals",
    "load_repair_proposal",
    "owner_rejections",
    "path_digest",
    "pending_from_backup",
    "propose",
    "psutil_controller_processes",
    "repair_proposal",
    "require_no_controller_process",
    "require_no_open_journal",
    "resume",
    "resume_repair",
    "supported_controller_form",
    "upcast_migration_journal_v1",
    "verify",
    "verify_repair",
    "write_repair_stage",
]
