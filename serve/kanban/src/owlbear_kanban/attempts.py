"""Immutable attempt lifecycle event contracts."""

from __future__ import annotations

import contextlib
import errno
import json
import os
import stat
from collections.abc import Iterator, Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban.identities import Digest
from owlbear_kanban.runtime_transaction import TransactionParticipant

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW

AttemptEventKind = Literal["started", "released", "failed", "crashed", "succeeded"]


class AttemptEventDiagnosticCode(StrEnum):
    """Stable attempt event parser diagnostic codes."""

    UNKNOWN_FIELD = "ERR_ATTEMPT_EVENT_FIELD_UNKNOWN"
    IDENTITY_INVALID = "ERR_ATTEMPT_EVENT_IDENTITY_INVALID"
    REFERENCE_INVALID = "ERR_ATTEMPT_EVENT_REFERENCE_INVALID"
    SEQUENCE_INVALID = "ERR_ATTEMPT_EVENT_SEQUENCE_INVALID"
    KIND_INVALID = "ERR_ATTEMPT_EVENT_KIND_INVALID"
    REQUIRED_REFERENCE_MISSING = "ERR_ATTEMPT_EVENT_REFERENCE_MISSING"
    SCHEMA_INVALID = "ERR_ATTEMPT_EVENT_SCHEMA_INVALID"


class AttemptDiagnosticCode(StrEnum):
    """Stable attempt-store diagnostic codes."""

    PATH_UNSAFE = "ERR_ATTEMPT_PATH_UNSAFE"
    FILE_MISSING = "ERR_ATTEMPT_FILE_MISSING"
    ENCODING = "ERR_ATTEMPT_ENCODING"
    JSON_PARSE = "ERR_ATTEMPT_JSON_PARSE"
    SCHEMA_INVALID = "ERR_ATTEMPT_SCHEMA_INVALID"
    ID_MISMATCH = "ERR_ATTEMPT_ID_MISMATCH"
    WRITE_FAILED = "ERR_ATTEMPT_WRITE_FAILED"


class _AttemptEventModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AttemptEvent(_AttemptEventModel):
    """One schema-version-one append-only attempt lifecycle event."""

    schema_version: Literal[1]
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    change_id: str = Field(min_length=1)
    delivery_digest: Digest
    target_node_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    sequence: int = Field(gt=0)
    timestamp: str = Field(min_length=1)
    kind: AttemptEventKind
    detail: str | None = None
    evidence_ids: tuple[str, ...] = ()


class AttemptEventDiagnostic(_AttemptEventModel):
    """Describe one stable attempt-event parsing failure."""

    code: AttemptEventDiagnosticCode
    detail: str


class AttemptEventParseResult(_AttemptEventModel):
    """Contain either one parsed attempt event or its diagnostics."""

    event: AttemptEvent | None = None
    diagnostics: tuple[AttemptEventDiagnostic, ...] = ()

    def model_post_init(self, __context: object, /) -> None:
        """Enforce that parsing produces exactly one event-or-diagnostics outcome."""
        if (self.event is None) == (not self.diagnostics):
            msg = "attempt event result must contain either one event or diagnostics"
            raise ValueError(msg)


class AttemptDiagnostic(_AttemptEventModel):
    """One stable attempt-store diagnostic."""

    code: AttemptDiagnosticCode
    detail: str
    path: str | None = None
    target: str | None = None


class AttemptResult(_AttemptEventModel):
    """One attempt-store result containing either an event or diagnostics."""

    event: AttemptEvent | None = None
    diagnostics: tuple[AttemptDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> AttemptResult:
        if (self.event is None) == (not self.diagnostics):
            msg = "attempt result must contain either one event or diagnostics"
            raise ValueError(msg)
        return self


class AttemptConflictError(FileExistsError):
    """Raised when immutable attempt creation would replace a different event."""

    code = "ERR_ATTEMPT_CONFLICT"

    def __init__(self, attempt_id: str, sequence: int) -> None:
        super().__init__(f"attempt event already exists: {attempt_id}/{sequence}")
        self.attempt_id = attempt_id
        self.sequence = sequence


def _diagnostic_from_validation(exc: PydanticValidationError) -> AttemptEventDiagnosticCode:
    message = str(exc)
    code = AttemptEventDiagnosticCode.SCHEMA_INVALID
    if "Extra inputs" in message:
        code = AttemptEventDiagnosticCode.UNKNOWN_FIELD
    elif "sequence" in message:
        code = AttemptEventDiagnosticCode.SEQUENCE_INVALID
    elif "kind" in message:
        code = AttemptEventDiagnosticCode.KIND_INVALID
    elif "Field required" in message and any(
        field in message for field in ("job_id", "change_id", "delivery_digest", "target_node_id", "evidence_ids")
    ):
        code = AttemptEventDiagnosticCode.REQUIRED_REFERENCE_MISSING
    elif any(
        field in message for field in ("job_id", "change_id", "delivery_digest", "target_node_id", "evidence_ids")
    ):
        code = AttemptEventDiagnosticCode.REFERENCE_INVALID
    elif any(field in message for field in ("attempt_id", "claim_id", "actor_id", "process_id")):
        code = AttemptEventDiagnosticCode.IDENTITY_INVALID
    return code


def parse_attempt_event_mapping(value: Mapping[str, object]) -> AttemptEventParseResult:
    """Parse a schema-version-one attempt event mapping with stable diagnostics."""
    normalized = dict(value)
    if isinstance(normalized.get("evidence_ids"), list):
        normalized["evidence_ids"] = tuple(normalized["evidence_ids"])
    try:
        event = AttemptEvent.model_validate(normalized)
    except PydanticValidationError as exc:
        return AttemptEventParseResult(
            diagnostics=(AttemptEventDiagnostic(code=_diagnostic_from_validation(exc), detail=str(exc)),)
        )
    return AttemptEventParseResult(event=event)


def serialize_attempt_event_mapping(event: AttemptEvent) -> dict[str, object]:
    """Serialize an attempt event as a schema-version-one JSON-compatible mapping."""
    return event.model_dump(mode="json")


def _diagnostic(
    code: AttemptDiagnosticCode, detail: str, path: str | None = None, target: str | None = None
) -> AttemptDiagnostic:
    return AttemptDiagnostic(code=code, detail=detail, path=path, target=target)


def _event_location(attempt_id: str, sequence: int) -> tuple[str, str, str]:
    if (
        not attempt_id
        or "\x00" in attempt_id
        or PurePosixPath(attempt_id).is_absolute()
        or PureWindowsPath(attempt_id).is_absolute()
        or PurePosixPath(attempt_id).name != attempt_id
        or PureWindowsPath(attempt_id).name != attempt_id
        or sequence <= 0
    ):
        msg = "attempt event identity is not safe"
        raise ValueError(msg)
    filename = f"{sequence}.json"
    path = f"attempts/{attempt_id}/{filename}"
    return attempt_id, filename, path


def _event_content(event: AttemptEvent) -> bytes:
    content = json.dumps(serialize_attempt_event_mapping(event), separators=(",", ":"), ensure_ascii=True)
    return f"{content}\n".encode()


class AttemptStore:
    """Contained immutable attempt-event storage rooted at an explicit work directory."""

    def __init__(self, work_root: Path) -> None:
        self._work_root = work_root

    @contextlib.contextmanager
    def _directory(self, attempt_id: str, *, create: bool) -> Iterator[int | None]:
        try:
            root_fd = os.open(self._work_root, _DIRECTORY_FLAGS)
        except OSError as exc:
            msg = "work root could not be opened safely"
            raise ValueError(msg) from exc
        attempts_fd: int | None = None
        directory_fd: int | None = None
        try:
            if create:
                with contextlib.suppress(FileExistsError):
                    os.mkdir("attempts", mode=0o755, dir_fd=root_fd)
            try:
                attempts_fd = os.open("attempts", _DIRECTORY_FLAGS, dir_fd=root_fd)
            except FileNotFoundError:
                yield None
                return
            if create:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(attempt_id, mode=0o755, dir_fd=attempts_fd)
            try:
                directory_fd = os.open(attempt_id, _DIRECTORY_FLAGS, dir_fd=attempts_fd)
            except FileNotFoundError:
                yield None
                return
            yield directory_fd
        finally:
            if directory_fd is not None:
                os.close(directory_fd)
            if attempts_fd is not None:
                os.close(attempts_fd)
            os.close(root_fd)

    @staticmethod
    def _read(  # noqa: PLR0911 - each I/O failure maps to a distinct stable diagnostic.
        directory_fd: int, event: AttemptEvent, filename: str, path: str
    ) -> AttemptResult:
        try:
            file_fd = os.open(filename, _FILE_FLAGS, dir_fd=directory_fd)
        except FileNotFoundError:
            return AttemptResult(
                diagnostics=(_diagnostic(AttemptDiagnosticCode.FILE_MISSING, "attempt event is missing", path),)
            )
        except OSError:
            return AttemptResult(
                diagnostics=(
                    _diagnostic(AttemptDiagnosticCode.PATH_UNSAFE, "attempt event could not be opened safely", path),
                )
            )
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                return AttemptResult(
                    diagnostics=(
                        _diagnostic(AttemptDiagnosticCode.PATH_UNSAFE, "attempt path must be a regular file", path),
                    )
                )
            try:
                with os.fdopen(file_fd, "rb") as handle:
                    content = handle.read()
            except OSError:
                return AttemptResult(
                    diagnostics=(
                        _diagnostic(AttemptDiagnosticCode.WRITE_FAILED, "attempt event could not be read", path),
                    )
                )
        finally:
            with contextlib.suppress(OSError):
                os.close(file_fd)
        try:
            value = json.loads(content.decode("utf-8"))
        except UnicodeDecodeError:
            return AttemptResult(
                diagnostics=(_diagnostic(AttemptDiagnosticCode.ENCODING, "attempt event is not strict UTF-8", path),)
            )
        except json.JSONDecodeError:
            return AttemptResult(
                diagnostics=(
                    _diagnostic(AttemptDiagnosticCode.JSON_PARSE, "attempt event JSON could not be parsed", path),
                )
            )
        if not isinstance(value, Mapping):
            return AttemptResult(
                diagnostics=(
                    _diagnostic(AttemptDiagnosticCode.SCHEMA_INVALID, "attempt event must be a mapping", path),
                )
            )
        parsed = parse_attempt_event_mapping(value)
        if parsed.event is None:
            return AttemptResult(
                diagnostics=(
                    _diagnostic(AttemptDiagnosticCode.SCHEMA_INVALID, "attempt event schema is invalid", path),
                )
            )
        if parsed.event.attempt_id != event.attempt_id or parsed.event.sequence != event.sequence:
            return AttemptResult(
                diagnostics=(
                    _diagnostic(AttemptDiagnosticCode.ID_MISMATCH, "attempt event identity does not match path", path),
                )
            )
        return AttemptResult(event=parsed.event)

    def create(self, event: AttemptEvent) -> AttemptResult:
        """Create an immutable event or return its byte-equivalent replay."""
        try:
            attempt_id, filename, path = _event_location(event.attempt_id, event.sequence)
        except ValueError:
            return AttemptResult(
                diagnostics=(_diagnostic(AttemptDiagnosticCode.PATH_UNSAFE, "attempt event identity is not safe"),)
            )
        content = _event_content(event)
        try:
            with self._directory(attempt_id, create=True) as directory_fd:
                assert directory_fd is not None
                try:
                    file_fd = os.open(filename, _CREATE_FLAGS, 0o644, dir_fd=directory_fd)
                except FileExistsError:
                    existing = self._read(directory_fd, event, filename, path)
                    if existing.event is not None and _event_content(existing.event) == content:
                        return existing
                    if existing.event is not None:
                        raise AttemptConflictError(event.attempt_id, event.sequence) from None
                    return existing
                try:
                    with os.fdopen(file_fd, "wb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.fsync(directory_fd)
                except OSError:
                    with contextlib.suppress(OSError):
                        os.unlink(filename, dir_fd=directory_fd)
                    return AttemptResult(
                        diagnostics=(
                            _diagnostic(AttemptDiagnosticCode.WRITE_FAILED, "attempt event could not be written", path),
                        )
                    )
        except AttemptConflictError:
            raise
        except (OSError, ValueError) as exc:
            code = AttemptDiagnosticCode.WRITE_FAILED
            if isinstance(exc, ValueError) or exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                code = AttemptDiagnosticCode.PATH_UNSAFE
            return AttemptResult(diagnostics=(_diagnostic(code, "attempt event could not be created safely", path),))
        return AttemptResult(event=event)

    def create_participant(self, event: AttemptEvent) -> TransactionParticipant:
        """Plan a non-mutating immutable event transaction participant."""
        _attempt_id, _filename, path = _event_location(event.attempt_id, event.sequence)
        return TransactionParticipant(self._work_root, Path(path), _event_content(event))

    def read(self, attempt_id: str, sequence: int) -> AttemptResult:
        """Read one immutable event by attempt ID and sequence."""
        try:
            safe_attempt_id, filename, path = _event_location(attempt_id, sequence)
            expected = AttemptEvent.model_construct(attempt_id=safe_attempt_id, sequence=sequence)
        except ValueError:
            return AttemptResult(
                diagnostics=(_diagnostic(AttemptDiagnosticCode.PATH_UNSAFE, "attempt event identity is not safe"),)
            )
        try:
            with self._directory(safe_attempt_id, create=False) as directory_fd:
                if directory_fd is None:
                    return AttemptResult(
                        diagnostics=(_diagnostic(AttemptDiagnosticCode.FILE_MISSING, "attempt event is missing", path),)
                    )
                return self._read(directory_fd, expected, filename, path)
        except ValueError:
            return AttemptResult(
                diagnostics=(
                    _diagnostic(
                        AttemptDiagnosticCode.PATH_UNSAFE,
                        "attempt directory could not be opened safely",
                        path,
                    ),
                )
            )

    def list(self) -> tuple[AttemptEvent, ...]:
        """List events by attempt ID then positive sequence."""
        try:
            root_fd = os.open(self._work_root, _DIRECTORY_FLAGS)
        except OSError as exc:
            msg = "work root could not be opened safely"
            raise ValueError(msg) from exc
        try:
            try:
                attempts_fd = os.open("attempts", _DIRECTORY_FLAGS, dir_fd=root_fd)
            except FileNotFoundError:
                return ()
            try:
                events: list[AttemptEvent] = []
                for attempt_id in sorted(os.listdir(attempts_fd)):  # noqa: PTH208 - descriptor-relative traversal.
                    if attempt_id.startswith("."):
                        continue
                    try:
                        directory_fd = os.open(attempt_id, _DIRECTORY_FLAGS, dir_fd=attempts_fd)
                    except OSError as exc:
                        msg = "attempt directory could not be opened safely"
                        raise ValueError(msg) from exc
                    try:
                        for filename in os.listdir(directory_fd):  # noqa: PTH208 - descriptor-relative traversal.
                            if not filename.endswith(".json"):
                                continue
                            try:
                                sequence = int(filename.removesuffix(".json"))
                            except ValueError:
                                continue
                            result = self.read(attempt_id, sequence)
                            if result.event is None:
                                msg = "attempt event could not be listed safely"
                                raise ValueError(msg)
                            events.append(result.event)
                    finally:
                        os.close(directory_fd)
                return tuple(sorted(events, key=lambda event: (event.attempt_id, event.sequence)))
            finally:
                os.close(attempts_fd)
        finally:
            os.close(root_fd)
