"""Immutable native change receipt storage and health."""

from __future__ import annotations

import contextlib
import math
import os
import re
import tempfile
from collections.abc import Mapping
from datetime import date, datetime, time
from enum import StrEnum
from io import StringIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Annotated, Literal, Never

from pydantic import BaseModel, ConfigDict, StringConstraints, field_serializer, model_validator
from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml.error import YAMLError

from owlbear_kanban._naming import validate_path_containment
from owlbear_kanban.change import ChangeId, ChangeRevision, Digest, load_change
from owlbear_kanban.yaml_rt import make_yaml

_RECEIPT_ID_PATTERN = r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"
_RECEIPT_ID_RE = re.compile(_RECEIPT_ID_PATTERN)

ReceiptId = Annotated[str, StringConstraints(strict=True, pattern=_RECEIPT_ID_PATTERN)]
ReceiptKind = Literal["admission", "shape", "build", "accept", "audit", "supersession"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]

_COMMON_RECEIPT_FIELDS = (
    "schema_version",
    "kind",
    "receipt_id",
    "change_id",
    "delivery_digest",
    "issued_at",
)


def _freeze_json(value: JsonValue) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _to_json_value(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            msg = "receipt payload mapping keys must be strings"
            raise ValueError(msg)
        return {key: _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        msg = "receipt payload numbers must be finite"
        raise ValueError(msg)
    if value is None or isinstance(value, str | int | float | bool):
        return value
    msg = f"unsupported receipt payload value: {type(value).__name__}"
    raise ValueError(msg)


def _thaw_json(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    msg = f"unsupported frozen JSON value: {type(value).__name__}"
    raise TypeError(msg)


class _ReceiptModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ReceiptRecord(_ReceiptModel):
    """Common receipt identity plus its kind-specific root payload."""

    schema_version: Literal[1]
    kind: ReceiptKind
    receipt_id: ReceiptId
    change_id: ChangeId
    delivery_digest: Digest
    issued_at: str
    payload: Mapping[str, JsonValue]

    def model_post_init(self, _context: object) -> None:
        object.__setattr__(self, "payload", _freeze_json(dict(self.payload)))

    @field_serializer("payload")
    def _serialize_payload(self, value: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
        return {key: _thaw_json(item) for key, item in value.items()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> ReceiptRecord:
        """Validate a root receipt mapping and separate its common envelope."""
        normalized = _to_json_value(value)
        if not isinstance(normalized, dict):
            msg = "receipt document must be a mapping"
            raise TypeError(msg)
        document = normalized
        envelope = {name: document.pop(name, None) for name in _COMMON_RECEIPT_FIELDS}
        return cls.model_validate({**envelope, "payload": document})

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return the native root receipt mapping."""
        envelope = self.model_dump(mode="json", exclude={"payload"})
        payload = self.model_dump(mode="json", include={"payload"})["payload"]
        return {**envelope, **payload}


class ReceiptDiagnosticCode(StrEnum):
    """Stable receipt-store diagnostic codes."""

    PATH_UNSAFE = "ERR_RECEIPT_PATH_UNSAFE"
    FILE_MISSING = "ERR_RECEIPT_FILE_MISSING"
    ENCODING = "ERR_RECEIPT_ENCODING"
    YAML_PARSE = "ERR_RECEIPT_YAML_PARSE"
    SCHEMA_INVALID = "ERR_RECEIPT_SCHEMA_INVALID"
    ID_MISMATCH = "ERR_RECEIPT_ID_MISMATCH"
    REVISION_MISMATCH = "ERR_RECEIPT_REVISION_MISMATCH"


class ReceiptDiagnostic(_ReceiptModel):
    code: ReceiptDiagnosticCode
    detail: str
    path: str | None = None
    target: str | None = None


class ReceiptResult(_ReceiptModel):
    receipt: ReceiptRecord | None = None
    diagnostics: tuple[ReceiptDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> ReceiptResult:
        if (self.receipt is None) == (not self.diagnostics):
            msg = "receipt result must contain either one receipt or diagnostics"
            raise ValueError(msg)
        return self


class ChangeHealthFinding(_ReceiptModel):
    code: str
    detail: str
    path: str | None = None
    target: str | None = None


class ChangeHealthResult(_ReceiptModel):
    findings: tuple[ChangeHealthFinding, ...] = ()
    checked_paths: tuple[str, ...] = ()


class ReceiptConflictError(FileExistsError):
    """Raised when immutable receipt creation would overwrite a receipt."""

    code = "ERR_RECEIPT_CONFLICT"

    def __init__(self, receipt_id: str) -> None:
        super().__init__(f"receipt already exists: {receipt_id}")
        self.receipt_id = receipt_id


class _ReceiptFailure(Exception):
    def __init__(self, diagnostic: ReceiptDiagnostic) -> None:
        super().__init__(diagnostic.detail)
        self.diagnostic = diagnostic


def _fail(
    code: ReceiptDiagnosticCode,
    detail: str,
    *,
    path: str | None = None,
    target: str | None = None,
) -> Never:
    raise _ReceiptFailure(ReceiptDiagnostic(code=code, detail=detail, path=path, target=target))


def _schema_detail(exc: PydanticValidationError) -> str:
    error = exc.errors(include_input=False, include_url=False)[0]
    location = ".".join(str(part) for part in error["loc"])
    return f"receipt schema rejected {location or '<root>'}: {error['type']}"


def _atomic_create(path: Path, content: str, receipt_id: str) -> None:
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".yaml")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            os.fchmod(handle.fileno(), 0o644)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            raise ReceiptConflictError(receipt_id) from None
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        with contextlib.suppress(OSError):
            temp_path.unlink()


class ReceiptStore:
    """Contained immutable receipt store for one loaded change revision."""

    def __init__(self, revision: ChangeRevision) -> None:
        self._revision = revision
        self._receipts_dir = revision.source_dir / "receipts"

    def _validate_receipts_dir(self, *, create: bool) -> None:
        if self._receipts_dir.is_symlink():
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipts directory must not be a symlink",
                path="receipts",
            )
        try:
            validate_path_containment(self._revision.source_dir, self._receipts_dir)
        except (OSError, ValueError):
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipts directory escapes the change directory",
                path="receipts",
            )
        if create:
            try:
                self._receipts_dir.mkdir(mode=0o755, exist_ok=True)
            except OSError:
                _fail(
                    ReceiptDiagnosticCode.PATH_UNSAFE,
                    "receipts directory could not be created",
                    path="receipts",
                )
        if self._receipts_dir.exists() and not self._receipts_dir.is_dir():
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipts path must be a directory",
                path="receipts",
            )
        if self._receipts_dir.is_symlink():
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipts directory must not be a symlink",
                path="receipts",
            )

    def _receipt_path(self, receipt_id: str, *, require_file: bool) -> Path:
        if (
            "\x00" in receipt_id
            or not _RECEIPT_ID_RE.fullmatch(receipt_id)
            or PurePosixPath(receipt_id).is_absolute()
            or PureWindowsPath(receipt_id).is_absolute()
        ):
            _fail(ReceiptDiagnosticCode.PATH_UNSAFE, "receipt ID is not a safe canonical identifier")
        path = self._receipts_dir / f"{receipt_id}.yaml"
        relative_path = f"receipts/{path.name}"
        if path.is_symlink():
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipt files must not be symlinks",
                path=relative_path,
                target=receipt_id,
            )
        try:
            validate_path_containment(self._revision.source_dir, path)
        except (OSError, ValueError):
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipt file escapes the change directory",
                path=relative_path,
                target=receipt_id,
            )
        if require_file and not path.is_file():
            _fail(
                ReceiptDiagnosticCode.FILE_MISSING,
                "receipt file is missing",
                path=relative_path,
                target=receipt_id,
            )
        return path

    def _validate_record(
        self,
        receipt_id: str,
        value: Mapping[str, object],
        *,
        path: str,
    ) -> ReceiptRecord:
        try:
            record = ReceiptRecord.from_mapping(value)
        except (PydanticValidationError, TypeError, ValueError) as exc:
            detail = _schema_detail(exc) if isinstance(exc, PydanticValidationError) else "receipt schema is invalid"
            _fail(ReceiptDiagnosticCode.SCHEMA_INVALID, detail, path=path, target=receipt_id)
        if record.receipt_id != receipt_id:
            _fail(
                ReceiptDiagnosticCode.ID_MISMATCH,
                "receipt filename and envelope identities differ",
                path=f"receipts/{receipt_id}.yaml",
                target=record.receipt_id,
            )
        if record.change_id != self._revision.change_id or record.delivery_digest != self._revision.delivery_digest:
            _fail(
                ReceiptDiagnosticCode.REVISION_MISMATCH,
                "receipt identity does not match the loaded change revision",
                path=f"receipts/{receipt_id}.yaml",
                target=receipt_id,
            )
        return record

    def create(self, receipt_id: str, value: Mapping[str, object]) -> ReceiptResult:
        """Create one immutable receipt without overwriting an existing receipt."""
        try:
            path = self._receipt_path(receipt_id, require_file=False)
            relative_path = f"receipts/{path.name}"
            record = self._validate_record(receipt_id, value, path=relative_path)
            self._validate_receipts_dir(create=True)
            path = self._receipt_path(receipt_id, require_file=False)
            stream = StringIO()
            make_yaml(explicit_start=True).dump(record.to_mapping(), stream)
            _atomic_create(path, stream.getvalue(), receipt_id)
        except _ReceiptFailure as exc:
            return ReceiptResult(diagnostics=(exc.diagnostic,))
        return ReceiptResult(receipt=record)

    def read(self, receipt_id: str) -> ReceiptResult:
        """Read and validate one immutable receipt."""
        try:
            self._validate_receipts_dir(create=False)
            path = self._receipt_path(receipt_id, require_file=True)
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                _fail(
                    ReceiptDiagnosticCode.ENCODING,
                    "receipt file is not strict UTF-8",
                    path=f"receipts/{path.name}",
                    target=receipt_id,
                )
            except OSError:
                _fail(
                    ReceiptDiagnosticCode.FILE_MISSING,
                    "receipt file could not be read",
                    path=f"receipts/{path.name}",
                    target=receipt_id,
                )
            try:
                value = make_yaml().load(text)
            except YAMLError:
                _fail(
                    ReceiptDiagnosticCode.YAML_PARSE,
                    "receipt YAML could not be parsed",
                    path=f"receipts/{path.name}",
                    target=receipt_id,
                )
            if not isinstance(value, Mapping):
                _fail(
                    ReceiptDiagnosticCode.SCHEMA_INVALID,
                    "receipt document must be a mapping",
                    path=f"receipts/{path.name}",
                    target=receipt_id,
                )
            record = self._validate_record(receipt_id, value, path=f"receipts/{path.name}")
        except _ReceiptFailure as exc:
            return ReceiptResult(diagnostics=(exc.diagnostic,))
        return ReceiptResult(receipt=record)


def _health_finding(diagnostic: ReceiptDiagnostic) -> ChangeHealthFinding:
    return ChangeHealthFinding(
        code=diagnostic.code.value,
        detail=diagnostic.detail,
        path=diagnostic.path,
        target=diagnostic.target,
    )


def _expected_admission_path(revision: ChangeRevision) -> tuple[str | None, ChangeHealthFinding | None]:
    if revision.graph.admission is None:
        return None, None
    value = revision.graph.admission.receipt
    candidate = PurePosixPath(value)
    if (
        candidate.is_absolute()
        or candidate.parts != ("receipts", candidate.name)
        or candidate.suffix != ".yaml"
        or not _RECEIPT_ID_RE.fullmatch(candidate.stem)
    ):
        return None, ChangeHealthFinding(
            code=ReceiptDiagnosticCode.PATH_UNSAFE.value,
            detail="admission receipt reference is not a safe canonical receipt path",
        )
    return value, None


def _receipt_health(revision: ChangeRevision) -> tuple[list[ChangeHealthFinding], list[str]]:
    findings: list[ChangeHealthFinding] = []
    checked_paths: list[str] = []
    store = ReceiptStore(revision)
    receipts_dir = revision.source_dir / "receipts"
    expected_path, expected_finding = _expected_admission_path(revision)
    receipt_storage_usable = True
    if expected_finding is not None:
        findings.append(expected_finding)
    if receipts_dir.is_symlink():
        receipt_storage_usable = False
        findings.append(
            ChangeHealthFinding(
                code=ReceiptDiagnosticCode.PATH_UNSAFE.value,
                detail="receipts directory must not be a symlink",
                path="receipts",
            )
        )
    elif receipts_dir.exists() and not receipts_dir.is_dir():
        receipt_storage_usable = False
        findings.append(
            ChangeHealthFinding(
                code=ReceiptDiagnosticCode.PATH_UNSAFE.value,
                detail="receipts path must be a directory",
                path="receipts",
            )
        )
    elif receipts_dir.is_dir():
        for path in sorted(receipts_dir.glob("*.yaml")):
            relative_path = f"receipts/{path.name}"
            checked_paths.append(relative_path)
            result = store.read(path.stem)
            findings.extend(_health_finding(item) for item in result.diagnostics)

    if receipt_storage_usable and expected_path is not None and expected_path not in checked_paths:
        checked_paths.append(expected_path)
        findings.append(
            ChangeHealthFinding(
                code=ReceiptDiagnosticCode.FILE_MISSING.value,
                detail="admission receipt file is missing",
                path=expected_path,
                target=PurePosixPath(expected_path).stem,
            )
        )
    return findings, checked_paths


def change_health(changes_dir: Path, change_id: str) -> ChangeHealthResult:
    """Return deterministic read-only authority and receipt health evidence."""
    authority_paths = ("intent.md", "design.md", "decisions.yaml", "graph.yaml")
    load_result = load_change(changes_dir, change_id)
    checked_paths = list(authority_paths)
    findings = [
        ChangeHealthFinding(code=item.code.value, detail=item.detail, path=item.path, target=item.target)
        for item in load_result.diagnostics
    ]
    if load_result.revision is None:
        return ChangeHealthResult(findings=tuple(findings), checked_paths=tuple(checked_paths))

    receipt_findings, receipt_paths = _receipt_health(load_result.revision)
    findings.extend(receipt_findings)
    checked_paths.extend(receipt_paths)
    findings.sort(key=lambda item: (item.path or "", item.code, item.target or ""))
    return ChangeHealthResult(findings=tuple(findings), checked_paths=tuple(checked_paths))


__all__ = [
    "ChangeHealthFinding",
    "ChangeHealthResult",
    "ReceiptConflictError",
    "ReceiptDiagnostic",
    "ReceiptDiagnosticCode",
    "ReceiptKind",
    "ReceiptRecord",
    "ReceiptResult",
    "ReceiptStore",
    "change_health",
]
