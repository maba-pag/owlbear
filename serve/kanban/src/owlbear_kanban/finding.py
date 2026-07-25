"""Immutable, contained corrective finding storage."""

from __future__ import annotations

import contextlib
import errno
import os
import re
import secrets
import stat
from collections.abc import Iterator, Mapping
from enum import StrEnum
from io import StringIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml.error import YAMLError

from owlbear_kanban.change import Digest
from owlbear_kanban.runtime_transaction import TransactionParticipant
from owlbear_kanban.yaml_rt import make_yaml

_FINDING_ID_PATTERN = r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"
_FINDING_ID_RE = re.compile(_FINDING_ID_PATTERN)
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_TEMP_CREATE_ATTEMPTS = 10

FindingId = Annotated[str, StringConstraints(strict=True, pattern=_FINDING_ID_PATTERN)]
FindingTargetKind = Literal[
    "requirement",
    "interface",
    "migration",
    "risk",
    "workflow",
    "delivery-node",
    "packet",
    "proof",
    "receipt",
    "code-revision",
]
FindingClass = Literal[
    "implementation-defect",
    "unforeseeable-discovery",
    "planning-omission",
    "scope-change",
]


class FindingDiagnosticCode(StrEnum):
    """Stable finding parser and storage diagnostic codes."""

    PATH_UNSAFE = "ERR_FINDING_PATH_UNSAFE"
    FILE_MISSING = "ERR_FINDING_FILE_MISSING"
    ENCODING = "ERR_FINDING_ENCODING"
    YAML_PARSE = "ERR_FINDING_YAML_PARSE"
    SCHEMA_INVALID = "ERR_FINDING_SCHEMA_INVALID"
    ID_MISMATCH = "ERR_FINDING_ID_MISMATCH"
    UNKNOWN_FIELD = "ERR_FINDING_FIELD_UNKNOWN"
    TARGET_INVALID = "ERR_FINDING_TARGET_INVALID"
    CLASS_INVALID = "ERR_FINDING_CLASS_INVALID"


class _FindingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Finding(_FindingModel):
    """One versioned corrective finding with source and target references."""

    schema_version: Literal[1]
    finding_id: FindingId
    source_attempt_id: str = Field(min_length=1)
    source_job_id: int = Field(gt=0)
    change_id: str = Field(min_length=1)
    delivery_digest: Digest
    target_kind: FindingTargetKind
    target_id: str = Field(min_length=1)
    finding_class: FindingClass
    detail: str = Field(min_length=1)
    created_at: str = Field(min_length=1)


class FindingDiagnostic(_FindingModel):
    """Describe one stable finding parsing or storage failure."""

    code: FindingDiagnosticCode
    detail: str
    path: str | None = None
    target: str | None = None


class FindingResult(_FindingModel):
    """Contain either one parsed finding or its diagnostics."""

    finding: Finding | None = None
    diagnostics: tuple[FindingDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> FindingResult:
        if (self.finding is None) == (not self.diagnostics):
            msg = "finding result must contain either one finding or diagnostics"
            raise ValueError(msg)
        return self


class FindingConflictError(FileExistsError):
    """Raised when immutable finding creation would replace another finding."""

    code = "ERR_FINDING_CONFLICT"

    def __init__(self, finding_id: str) -> None:
        super().__init__(f"finding already exists: {finding_id}")
        self.finding_id = finding_id


def _diagnostic(
    code: FindingDiagnosticCode,
    detail: str,
    path: str | None = None,
    target: str | None = None,
) -> FindingDiagnostic:
    return FindingDiagnostic(code=code, detail=detail, path=path, target=target)


def _diagnostic_from_validation(exc: PydanticValidationError) -> FindingDiagnosticCode:
    message = str(exc)
    if "Extra inputs" in message:
        return FindingDiagnosticCode.UNKNOWN_FIELD
    if "target_kind" in message:
        return FindingDiagnosticCode.TARGET_INVALID
    if "finding_class" in message:
        return FindingDiagnosticCode.CLASS_INVALID
    return FindingDiagnosticCode.SCHEMA_INVALID


def parse_finding_mapping(value: Mapping[str, object]) -> FindingResult:
    """Parse a schema-version-one finding mapping with stable diagnostics."""
    try:
        finding = Finding.model_validate(value)
    except PydanticValidationError as exc:
        return FindingResult(diagnostics=(FindingDiagnostic(code=_diagnostic_from_validation(exc), detail=str(exc)),))
    return FindingResult(finding=finding)


def _finding_location(finding_id: str) -> tuple[str, str]:
    if (
        "\x00" in finding_id
        or not _FINDING_ID_RE.fullmatch(finding_id)
        or PurePosixPath(finding_id).is_absolute()
        or PureWindowsPath(finding_id).is_absolute()
    ):
        message = "finding ID is not a safe canonical identifier"
        raise ValueError(message)
    filename = f"{finding_id}.yaml"
    return filename, f"findings/{filename}"


class FindingStore:
    """Contained immutable finding storage rooted at an explicit work directory."""

    def __init__(self, work_root: Path) -> None:
        self._work_root = work_root

    @contextlib.contextmanager
    def _directory(self, *, create: bool) -> Iterator[int | None]:
        try:
            root_fd = os.open(self._work_root, _DIRECTORY_FLAGS)
        except OSError as exc:
            message = "work root could not be opened safely"
            raise ValueError(message) from exc
        try:
            if create:
                with contextlib.suppress(FileExistsError):
                    os.mkdir("findings", mode=0o755, dir_fd=root_fd)
            try:
                directory_fd = os.open("findings", _DIRECTORY_FLAGS, dir_fd=root_fd)
            except FileNotFoundError:
                directory_fd = None
            except OSError as exc:
                message = "findings directory could not be opened safely"
                raise ValueError(message) from exc
            try:
                yield directory_fd
            finally:
                if directory_fd is not None:
                    os.close(directory_fd)
        finally:
            os.close(root_fd)

    @staticmethod
    def _read(  # noqa: PLR0911 - each I/O failure maps to a distinct stable diagnostic.
        directory_fd: int, finding_id: str, filename: str, path: str
    ) -> FindingResult:
        try:
            file_fd = os.open(filename, _FILE_FLAGS, dir_fd=directory_fd)
        except FileNotFoundError:
            return FindingResult(
                diagnostics=(
                    _diagnostic(FindingDiagnosticCode.FILE_MISSING, "finding file is missing", path, finding_id),
                )
            )
        except OSError:
            return FindingResult(
                diagnostics=(
                    _diagnostic(
                        FindingDiagnosticCode.PATH_UNSAFE, "finding file could not be opened safely", path, finding_id
                    ),
                )
            )
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                return FindingResult(
                    diagnostics=(
                        _diagnostic(
                            FindingDiagnosticCode.PATH_UNSAFE,
                            "finding path must identify a regular file",
                            path,
                            finding_id,
                        ),
                    )
                )
            try:
                with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
                    value = make_yaml().load(handle)
            except UnicodeDecodeError:
                return FindingResult(
                    diagnostics=(
                        _diagnostic(
                            FindingDiagnosticCode.ENCODING, "finding file is not strict UTF-8", path, finding_id
                        ),
                    )
                )
            except YAMLError:
                return FindingResult(
                    diagnostics=(
                        _diagnostic(
                            FindingDiagnosticCode.YAML_PARSE, "finding YAML could not be parsed", path, finding_id
                        ),
                    )
                )
        finally:
            with contextlib.suppress(OSError):
                os.close(file_fd)
        if not isinstance(value, Mapping):
            return FindingResult(
                diagnostics=(
                    _diagnostic(
                        FindingDiagnosticCode.SCHEMA_INVALID, "finding document must be a mapping", path, finding_id
                    ),
                )
            )
        result = parse_finding_mapping(value)
        if result.finding is not None and result.finding.finding_id != finding_id:
            return FindingResult(
                diagnostics=(
                    _diagnostic(
                        FindingDiagnosticCode.ID_MISMATCH,
                        "finding filename and record identities differ",
                        path,
                        finding_id,
                    ),
                )
            )
        return (
            result
            if result.finding is not None
            else FindingResult(
                diagnostics=tuple(
                    item.model_copy(update={"path": path, "target": finding_id}) for item in result.diagnostics
                )
            )
        )

    def create(  # noqa: C901, PLR0911, PLR0912 - publication stages preserve stable failure diagnostics.
        self, finding_id: str, value: Mapping[str, object]
    ) -> FindingResult:
        """Create a finding, returning its existing value for byte-equivalent replay."""
        try:
            filename, path = _finding_location(finding_id)
        except ValueError:
            return FindingResult(
                diagnostics=(
                    _diagnostic(FindingDiagnosticCode.PATH_UNSAFE, "finding ID is not a safe canonical identifier"),
                )
            )
        result = parse_finding_mapping(value)
        if result.finding is None:
            return result
        if result.finding.finding_id != finding_id:
            return FindingResult(
                diagnostics=(
                    _diagnostic(
                        FindingDiagnosticCode.ID_MISMATCH,
                        "finding filename and record identities differ",
                        path,
                        finding_id,
                    ),
                )
            )
        stream = StringIO()
        make_yaml(explicit_start=True).dump(result.finding.model_dump(mode="json"), stream)
        content = stream.getvalue()
        try:
            with self._directory(create=True) as directory_fd:
                assert directory_fd is not None
                temporary_fd: int | None = None
                temporary_name: str | None = None
                try:
                    for _attempt in range(_TEMP_CREATE_ATTEMPTS):
                        temporary_name = f".tmp-{secrets.token_hex(16)}.yaml"
                        try:
                            temporary_fd = os.open(temporary_name, _CREATE_FLAGS, 0o600, dir_fd=directory_fd)
                            break
                        except FileExistsError:
                            continue
                    if temporary_fd is None or temporary_name is None:
                        message = "could not allocate a unique finding temporary file"
                        raise OSError(message)
                    with os.fdopen(os.dup(temporary_fd), "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.link(
                        temporary_name,
                        filename,
                        src_dir_fd=directory_fd,
                        dst_dir_fd=directory_fd,
                        follow_symlinks=False,
                    )
                    os.fsync(directory_fd)
                except FileExistsError:
                    existing = self._read(directory_fd, finding_id, filename, path)
                    if existing.finding is not None and existing.finding.model_dump(
                        mode="json"
                    ) == result.finding.model_dump(mode="json"):
                        return existing
                    if existing.finding is not None:
                        raise FindingConflictError(finding_id) from None
                    return existing
                finally:
                    if temporary_name is not None:
                        with contextlib.suppress(OSError):
                            os.unlink(temporary_name, dir_fd=directory_fd)
                    if temporary_fd is not None:
                        os.close(temporary_fd)
        except FindingConflictError:
            raise
        except OSError as exc:
            code = (
                FindingDiagnosticCode.PATH_UNSAFE
                if exc.errno in {errno.ELOOP, errno.ENOTDIR}
                else FindingDiagnosticCode.FILE_MISSING
            )
            return FindingResult(
                diagnostics=(_diagnostic(code, "finding file could not be created safely", path, finding_id),)
            )
        return result

    def create_participant(
        self, finding_id: str, value: Mapping[str, object]
    ) -> tuple[Finding, TransactionParticipant]:
        """Validate and plan one immutable finding transaction participant."""
        filename, _path = _finding_location(finding_id)
        result = parse_finding_mapping(value)
        if result.finding is None:
            msg = result.diagnostics[0].detail
            raise ValueError(msg)
        finding = result.finding
        if finding.finding_id != finding_id:
            msg = "finding filename and record identities differ"
            raise ValueError(msg)
        stream = StringIO()
        make_yaml(explicit_start=True).dump(finding.model_dump(mode="json"), stream)
        return finding, TransactionParticipant(
            self._work_root,
            Path("findings") / filename,
            stream.getvalue().encode("utf-8"),
        )

    def read(self, finding_id: str) -> FindingResult:
        """Read one contained immutable finding."""
        try:
            filename, path = _finding_location(finding_id)
        except ValueError:
            return FindingResult(
                diagnostics=(
                    _diagnostic(FindingDiagnosticCode.PATH_UNSAFE, "finding ID is not a safe canonical identifier"),
                )
            )
        try:
            with self._directory(create=False) as directory_fd:
                if directory_fd is None:
                    return FindingResult(
                        diagnostics=(
                            _diagnostic(
                                FindingDiagnosticCode.FILE_MISSING, "finding file is missing", path, finding_id
                            ),
                        )
                    )
                return self._read(directory_fd, finding_id, filename, path)
        except ValueError:
            return FindingResult(
                diagnostics=(
                    _diagnostic(
                        FindingDiagnosticCode.PATH_UNSAFE,
                        "findings directory could not be opened safely",
                        path,
                        finding_id,
                    ),
                )
            )

    def list(self) -> tuple[FindingResult, ...]:
        """List findings in ascending canonical finding-ID order."""
        try:
            with self._directory(create=False) as directory_fd:
                if directory_fd is None:
                    return ()
                entries: list[FindingResult] = []
                names = os.listdir(directory_fd)  # noqa: PTH208 - Path.iterdir cannot use the pinned descriptor.
                for filename in sorted(name for name in names if name.endswith(".yaml")):
                    finding_id = PurePosixPath(filename).stem
                    path = f"findings/{filename}"
                    try:
                        expected, _ = _finding_location(finding_id)
                    except ValueError:
                        entries.append(
                            FindingResult(
                                diagnostics=(
                                    _diagnostic(
                                        FindingDiagnosticCode.PATH_UNSAFE, "finding filename is not canonical", path
                                    ),
                                )
                            )
                        )
                        continue
                    if filename != expected:
                        entries.append(
                            FindingResult(
                                diagnostics=(
                                    _diagnostic(
                                        FindingDiagnosticCode.PATH_UNSAFE, "finding filename is not canonical", path
                                    ),
                                )
                            )
                        )
                        continue
                    entries.append(self._read(directory_fd, finding_id, filename, path))
                return tuple(entries)
        except ValueError:
            return (
                FindingResult(
                    diagnostics=(
                        _diagnostic(
                            FindingDiagnosticCode.PATH_UNSAFE,
                            "findings directory could not be opened safely",
                            "findings",
                        ),
                    )
                ),
            )
