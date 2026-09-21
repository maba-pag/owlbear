"""Bounded host-local finalization diagnostics, separate from lifecycle proof."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
    contained_directory,
    read_contained,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

MAX_REPORT_BYTES = 16_384
MAX_REPORTS = 256
_MAX_PATH_LENGTH = 240
_MAX_IDENTIFIER_LENGTH = 128
type _ReportFileSignature = tuple[str, int, int, int, int, int]


class FinalizationReportError(RuntimeError):
    """A diagnostic write or read failed without changing product authority."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FinalizationFailureCode(StrEnum):
    """Registered structural failure codes with engine-owned explanations."""

    WORKSPACE_DIRTY = "workspace-dirty"
    WORKSPACE_PREFLIGHT_FAILED = "workspace-preflight-failed"
    MAINTAINED_CHECK_FAILED = "maintained-check-failed"
    MAINTAINED_CHECK_UNAVAILABLE = "maintained-check-unavailable"
    INDEPENDENT_REVIEW_FAILED = "independent-review-failed"
    INDEPENDENT_REVIEW_UNAVAILABLE = "independent-review-unavailable"
    PROOF_MUTATED_WORKTREE = "proof-mutated-worktree"


_SUMMARIES = {
    FinalizationFailureCode.WORKSPACE_DIRTY: "Verification did not run because the managed workspace is dirty.",
    FinalizationFailureCode.WORKSPACE_PREFLIGHT_FAILED: "Managed workspace preflight did not pass.",
    FinalizationFailureCode.MAINTAINED_CHECK_FAILED: "A maintained verification check failed.",
    FinalizationFailureCode.MAINTAINED_CHECK_UNAVAILABLE: "A maintained verification check could not be observed.",
    FinalizationFailureCode.INDEPENDENT_REVIEW_FAILED: "Independent verification review reported a finding.",
    FinalizationFailureCode.INDEPENDENT_REVIEW_UNAVAILABLE: "Independent verification review was unavailable.",
    FinalizationFailureCode.PROOF_MUTATED_WORKTREE: "The maintained proof procedure mutated the managed workspace.",
}


class _ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ReportFinalizationFailure(_ReportModel):
    """Structural diagnostic input, never a successful proof or repair request."""

    change_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    expected_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_diagnostic_sequence: int = Field(ge=0)
    attempt_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    category: Literal["custody-preflight", "maintained-check", "independent-review", "proof-mutation"]
    code: FinalizationFailureCode
    checks_state: Literal["not-run", "failed", "unknown"]
    check_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    exit_status: int | None = Field(default=None, ge=-255, le=255)
    expected_workspace_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    procedure_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    proof_fingerprint_before: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    proof_fingerprint_after: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    paths: tuple[str, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def _validate_structure(self) -> ReportFinalizationFailure:
        prefix = {
            "custody-preflight": "workspace-",
            "maintained-check": "maintained-check-",
            "independent-review": "independent-review-",
            "proof-mutation": "proof-mutated-",
        }[self.category]
        if not self.code.value.startswith(prefix):
            msg = "failure code must match its diagnostic category"
            raise ValueError(msg)
        if self.category == "custody-preflight" and self.expected_workspace_fingerprint is None:
            msg = "custody diagnostics require an observed workspace fingerprint"
            raise ValueError(msg)
        if self.category not in {"custody-preflight", "proof-mutation"} and self.paths:
            msg = "dirty paths belong only to custody diagnostics"
            raise ValueError(msg)
        if self.category == "proof-mutation" and (
            self.procedure_id is None
            or self.proof_fingerprint_before is None
            or self.proof_fingerprint_after is None
            or self.proof_fingerprint_before == self.proof_fingerprint_after
            or self.code is not FinalizationFailureCode.PROOF_MUTATED_WORKTREE
        ):
            msg = "proof mutation diagnostics require procedure and distinct before/after fingerprints"
            raise ValueError(msg)
        if self.category != "proof-mutation" and any(
            value is not None
            for value in (self.procedure_id, self.proof_fingerprint_before, self.proof_fingerprint_after)
        ):
            msg = "proof mutation evidence belongs only to proof-mutation diagnostics"
            raise ValueError(msg)
        for value in self.paths:
            path = PurePosixPath(value)
            if (
                not value
                or len(value) > _MAX_PATH_LENGTH
                or path.is_absolute()
                or ".." in path.parts
                or str(path) != value
                or value == "."
                or "\\" in value
                or not value.isprintable()
            ):
                msg = "diagnostic paths must be normalized contained relative paths"
                raise ValueError(msg)
        if len(set(self.paths)) != len(self.paths):
            msg = "diagnostic paths must be unique"
            raise ValueError(msg)
        return self


def _encoded(model: BaseModel, *, exclude: set[str] | None = None) -> bytes:
    return (
        json.dumps(model.model_dump(mode="json", exclude=exclude), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


_CURRENT_REPORT_REQUEST_FIELDS = frozenset(
    {"procedure_id", "proof_fingerprint_before", "proof_fingerprint_after"}
)


def _encoded_report(report: FinalizationReport, *, exclude: set[str] | None = None) -> bytes:
    """Serialize a report with the format that established its identity.

    D03-C added proof-mutation request fields without changing the report schema
    version.  A report loaded without those fields must therefore be hashed and
    size-checked from its original field set rather than from a reserialized
    current model.
    """
    legacy = not report.request.model_fields_set.intersection(_CURRENT_REPORT_REQUEST_FIELDS)
    payload = report.model_dump(mode="json", exclude=exclude)
    if legacy:
        request = payload.get("request")
        if isinstance(request, dict):
            for field in _CURRENT_REPORT_REQUEST_FIELDS:
                request.pop(field, None)
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


class FinalizationReport(_ReportModel):
    """Immutable diagnostic identity; its producer is not authenticated proof."""

    report_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    sequence: int = Field(ge=1, le=MAX_REPORTS)
    request: ReportFinalizationFailure
    observed_at: datetime
    producer: Literal["finalization-diagnostic"] = "finalization-diagnostic"
    summary: str = Field(min_length=1, max_length=240)
    check_id: None = None
    exit_status: None = None

    @model_validator(mode="after")
    def _validate_record(self) -> FinalizationReport:
        if self.observed_at.tzinfo is None or self.sequence != self.request.expected_diagnostic_sequence + 1:
            msg = "report sequence and timestamp must bind the diagnostic request"
            raise ValueError(msg)
        if self.summary != _SUMMARIES[self.request.code]:
            msg = "report summary must use its registered engine template"
            raise ValueError(msg)
        if hashlib.sha256(_encoded_report(self, exclude={"report_id"})).hexdigest() != self.report_id:
            msg = "report identity does not match its immutable content"
            raise ValueError(msg)
        if len(_encoded_report(self)) > MAX_REPORT_BYTES:
            msg = "diagnostic report exceeds encoded capacity"
            raise ValueError(msg)
        return self

    @classmethod
    def create(cls, request: ReportFinalizationFailure, observed_at: datetime) -> FinalizationReport:
        """Create a canonical engine-authored diagnostic identity."""
        values = {
            "sequence": request.expected_diagnostic_sequence + 1,
            "request": request.model_dump(mode="json"),
            "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
            "producer": "finalization-diagnostic",
            "summary": _SUMMARIES[request.code],
            "check_id": None,
            "exit_status": None,
        }
        content = (json.dumps(values, sort_keys=True, separators=(",", ":")) + "\n").encode()
        values["report_id"] = hashlib.sha256(content).hexdigest()
        return cls.model_validate_json(json.dumps(values))


class FinalizationAttempt(_ReportModel):
    """A retained diagnostic with explicit applicability to the displayed candidate."""

    report: FinalizationReport
    applicability: Literal["current", "historical"]


class _CurrentReport(_ReportModel):
    sequence: int = Field(ge=0, le=MAX_REPORTS)
    report_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class FinalizationReportSnapshot(_ReportModel):
    """Validated host-local history and its current diagnostic sequence."""

    sequence: int = 0
    current_report_id: str | None = None
    reports: tuple[FinalizationReport, ...] = ()


class FinalizationReportStore:
    """Per-Change serialized, descriptor-contained, recoverable diagnostic history."""

    def __init__(self, runtime_root: Path, change_id: str) -> None:
        if (
            not change_id
            or len(change_id) > _MAX_IDENTIFIER_LENGTH
            or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in change_id)
        ):
            msg = "invalid Change identity"
            raise ValueError(msg)
        self._runtime_root = runtime_root
        self._relative_root = Path("finalization-reports") / change_id
        self._root = runtime_root / self._relative_root
        self._change_id = change_id
        self._cached_pointer: bytes | None = None
        self._cached_report_inventory: tuple[_ReportFileSignature, ...] = ()
        self._cached_snapshot: FinalizationReportSnapshot | None = None

    @contextmanager
    def _locked(self, *, create: bool) -> Iterator[int | None]:
        root_fd = None
        entered = False
        try:
            root_fd = os.open(self._runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            with contained_directory(root_fd, self._relative_root, create=create) as report_fd:
                lock_fd = os.open(
                    ".storage.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=report_fd
                )
                try:
                    if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                        msg = "invalid report lock"
                        raise ValueError(msg)
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                    RuntimeTransaction.recover_contained(self._root, report_fd)
                    entered = True
                    yield report_fd
                finally:
                    os.close(lock_fd)
        except FileNotFoundError as exc:
            if create or root_fd is None or entered:
                msg = "report-store-unavailable"
                raise FinalizationReportError(msg) from exc
            yield None
        except (OSError, ValueError, TransactionConflictError, yaml.YAMLError) as exc:
            msg = "report-store-unavailable"
            raise FinalizationReportError(msg) from exc
        finally:
            if root_fd is not None:
                os.close(root_fd)

    def read(self) -> FinalizationReportSnapshot:
        """Read history, recovering only previously recorded report transactions."""
        with self._locked(create=False) as descriptor:
            return self._read(descriptor) if descriptor is not None else FinalizationReportSnapshot()

    def _read(self, descriptor: int) -> FinalizationReportSnapshot:
        pointer_bytes = read_contained(descriptor, Path("current.json"), limit=MAX_REPORT_BYTES)
        inventory = self._report_inventory(descriptor)
        if (
            self._cached_snapshot is not None
            and pointer_bytes == self._cached_pointer
            and inventory == self._cached_report_inventory
        ):
            return self._cached_snapshot
        names = tuple(item[0] for item in inventory)
        if len(names) > MAX_REPORTS:
            msg = "diagnostic history exceeds capacity"
            raise ValueError(msg)
        reports = []
        for name in names:
            content = read_contained(descriptor, Path("reports") / name, limit=MAX_REPORT_BYTES)
            report = FinalizationReport.model_validate_json(content)
            if name != f"{report.report_id}.json" or report.request.change_id != self._change_id:
                msg = "report storage identity mismatch"
                raise ValueError(msg)
            reports.append(report)
        ordered = tuple(sorted(reports, key=lambda report: report.sequence))
        if tuple(report.sequence for report in ordered) != tuple(range(1, len(ordered) + 1)):
            msg = "report history sequence is inconsistent"
            raise ValueError(msg)
        if len({report.request.attempt_key for report in ordered}) != len(ordered):
            msg = "report attempt identities must be unique"
            raise ValueError(msg)
        pointer = (
            _CurrentReport.model_validate_json(pointer_bytes)
            if pointer_bytes is not None
            else _CurrentReport(sequence=0)
        )
        if pointer.sequence != len(ordered) or (
            pointer.report_id is not None and (not ordered or pointer.report_id != ordered[-1].report_id)
        ):
            msg = "report pointer is inconsistent with immutable history"
            raise ValueError(msg)
        snapshot = FinalizationReportSnapshot(
            sequence=pointer.sequence, current_report_id=pointer.report_id, reports=ordered
        )
        self._cache_snapshot(snapshot, pointer_bytes, inventory)
        return snapshot

    @staticmethod
    def _report_inventory(descriptor: int) -> tuple[_ReportFileSignature, ...]:
        try:
            with contained_directory(descriptor, Path("reports")) as reports_fd, os.scandir(reports_fd) as entries:
                return tuple(
                    sorted(
                        (
                            entry.name,
                            metadata.st_mode,
                            metadata.st_ino,
                            metadata.st_size,
                            metadata.st_mtime_ns,
                            metadata.st_ctime_ns,
                        )
                        for entry in entries
                        for metadata in (entry.stat(follow_symlinks=False),)
                    )
                )
        except FileNotFoundError:
            return ()

    def _cache_snapshot(
        self,
        snapshot: FinalizationReportSnapshot,
        pointer_bytes: bytes | None,
        inventory: tuple[_ReportFileSignature, ...],
    ) -> None:
        self._cached_snapshot = snapshot
        self._cached_pointer = pointer_bytes
        self._cached_report_inventory = inventory

    def record(
        self,
        request: ReportFinalizationFailure,
        observed_at: datetime,
        validate_basis: Callable[[], None],
    ) -> FinalizationReport:
        """Replay before checking new authority, then atomically append and advance."""
        if request.change_id != self._change_id:
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        with self._locked(create=True) as descriptor:
            snapshot = self._read(descriptor)
            prior = next(
                (report for report in snapshot.reports if report.request.attempt_key == request.attempt_key), None
            )
            if prior is not None:
                if prior.request != request:
                    msg = "diagnostic-conflict"
                    raise FinalizationReportError(msg)
                return prior
            if snapshot.sequence >= MAX_REPORTS:
                msg = "diagnostic-capacity"
                raise FinalizationReportError(msg)
            if request.expected_diagnostic_sequence != snapshot.sequence:
                msg = "diagnostic-conflict"
                raise FinalizationReportError(msg)
            validate_basis()
            report = FinalizationReport.create(request, observed_at)
            pointer = _CurrentReport(sequence=report.sequence, report_id=report.report_id)
            previous = read_contained(descriptor, Path("current.json"), limit=MAX_REPORT_BYTES)
            participant = (
                TransactionParticipant(self._root, Path("current.json"), _encoded(pointer))
                if previous is None
                else ReplacementTransactionParticipant(self._root, Path("current.json"), previous, _encoded(pointer))
            )
            RuntimeTransaction(
                self._root,
                report.report_id,
                (
                    TransactionParticipant(self._root, Path("reports") / f"{report.report_id}.json", _encoded(report)),
                    participant,
                ),
            ).commit_contained(descriptor)
            self._cache_snapshot(
                FinalizationReportSnapshot(
                    sequence=report.sequence,
                    current_report_id=report.report_id,
                    reports=(*snapshot.reports, report),
                ),
                _encoded(pointer),
                self._report_inventory(descriptor),
            )
            return report

    def retire(self, candidate: str, contract_digest: str) -> None:
        """Retire only a matching current pointer, retaining sequence and history."""
        with self._locked(create=False) as descriptor:
            if descriptor is None:
                return
            snapshot = self._read(descriptor)
            if not snapshot.current_report_id:
                return
            report = snapshot.reports[-1]
            if (
                report.request.expected_change_head != candidate
                or report.request.expected_contract_digest != contract_digest
            ):
                return
            previous = _encoded(_CurrentReport(sequence=snapshot.sequence, report_id=report.report_id))
            replacement = _encoded(_CurrentReport(sequence=snapshot.sequence))
            RuntimeTransaction(
                self._root,
                f"retire-{report.report_id}",
                (ReplacementTransactionParticipant(self._root, Path("current.json"), previous, replacement),),
            ).commit_contained(descriptor)
            self._cache_snapshot(
                snapshot.model_copy(update={"current_report_id": None}), replacement, self._cached_report_inventory
            )
