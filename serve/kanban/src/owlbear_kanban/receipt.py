"""Immutable native change receipt storage and health."""

from __future__ import annotations

import contextlib
import errno
import hashlib
import json
import math
import os
import re
import secrets
import stat
import subprocess
from collections.abc import Iterable, Iterator, Mapping
from datetime import date, datetime, time
from enum import StrEnum
from io import StringIO
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Annotated, Literal, Never, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints, TypeAdapter, field_serializer, model_validator
from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml.error import YAMLError

from owlbear_kanban.change import ChangeId, ChangeRevision, Digest, Proof, StableId, load_change
from owlbear_kanban.runtime_transaction import TransactionParticipant
from owlbear_kanban.yaml_rt import make_yaml

_RECEIPT_ID_PATTERN = r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"
_RECEIPT_ID_RE = re.compile(_RECEIPT_ID_PATTERN)
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_TEMP_OPEN_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
_TEMP_CREATE_ATTEMPTS = 10
_STABLE_ID_ADAPTER = TypeAdapter(StableId)

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
    "impact_closure",
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


class ImpactClosureError(ValueError):
    """Report an invalid receipt impact closure with a stable code."""

    code = "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"
    MISSING = "ERR_RECEIPT_IMPACT_CLOSURE_MISSING"
    PATH_EMPTY = "impact closure path selector must be a non-empty string"
    PATH_NOT_POSIX = "impact closure path selector is not repository-relative POSIX"
    PATH_NOT_CANONICAL = "impact closure path selector is not canonical"
    NOT_MAPPING = "impact closure must be a mapping"
    UNKNOWN_FIELDS = "impact closure must contain only paths and authority_targets"
    PATHS_EMPTY = "impact closure paths must be a non-empty sequence"
    TARGETS_INVALID = "impact closure authority_targets must be a sequence of stable IDs"
    TARGET_UNDECLARED = "impact closure references an undeclared authority target"


def parse_repository_path(value: object) -> str:
    """Validate and return one canonical repository-relative path selector."""
    if not isinstance(value, str) or not value:
        raise ImpactClosureError(ImpactClosureError.PATH_EMPTY)
    if value == "/":
        return value
    if value.startswith("/") or "\\" in value or "\x00" in value:
        raise ImpactClosureError(ImpactClosureError.PATH_NOT_POSIX)
    path = value.removesuffix("/")
    if not path or any(segment in {"", ".", ".."} for segment in path.split("/")):
        raise ImpactClosureError(ImpactClosureError.PATH_NOT_CANONICAL)
    return value


class ImpactClosure(_ReceiptModel):
    """Frozen repository paths and authority targets consumed by receipt proof."""

    paths: tuple[str, ...]
    authority_targets: tuple[str, ...]


def parse_impact_closure(
    value: object,
    *,
    declared_authority_targets: Iterable[str] | None = None,
) -> ImpactClosure:
    """Validate and freeze one canonical receipt impact closure."""
    if not isinstance(value, Mapping):
        raise ImpactClosureError(ImpactClosureError.NOT_MAPPING)
    if set(value) != {"paths", "authority_targets"}:
        raise ImpactClosureError(ImpactClosureError.UNKNOWN_FIELDS)
    paths = value["paths"]
    authority_targets = value["authority_targets"]
    if not isinstance(paths, list | tuple) or not paths:
        raise ImpactClosureError(ImpactClosureError.PATHS_EMPTY)
    if not isinstance(authority_targets, list | tuple):
        raise ImpactClosureError(ImpactClosureError.TARGETS_INVALID)
    try:
        canonical_targets = tuple(sorted({_STABLE_ID_ADAPTER.validate_python(target) for target in authority_targets}))
    except PydanticValidationError as exc:
        raise ImpactClosureError(ImpactClosureError.TARGETS_INVALID) from exc
    canonical_paths = tuple(sorted({parse_repository_path(path) for path in paths}))
    if declared_authority_targets is not None:
        declared = set(declared_authority_targets)
        if not set(canonical_targets) <= declared:
            raise ImpactClosureError(ImpactClosureError.TARGET_UNDECLARED)
    return ImpactClosure(paths=canonical_paths, authority_targets=canonical_targets)


def _undeclared_authority_target(revision: ChangeRevision, closure: ImpactClosure) -> str | None:
    for target in closure.authority_targets:
        try:
            revision.resolve(target)
        except KeyError:
            return target
    return None


class ReceiptRecord(_ReceiptModel):
    """Common receipt identity plus its kind-specific root payload."""

    schema_version: int
    kind: ReceiptKind
    receipt_id: ReceiptId
    change_id: ChangeId
    delivery_digest: Digest
    issued_at: str
    impact_closure: ImpactClosure | None = None
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
        if envelope["kind"] != "admission":
            closure = envelope["impact_closure"]
            if closure is None:
                raise ImpactClosureError(ImpactClosureError.MISSING)
            envelope["impact_closure"] = parse_impact_closure(closure)
        return cls.model_validate({**envelope, "payload": document})

    def to_mapping(self) -> dict[str, JsonValue]:
        """Return the native root receipt mapping."""
        envelope = self.model_dump(mode="json", exclude={"payload"}, exclude_none=True)
        payload = self.model_dump(mode="json", include={"payload"})["payload"]
        return {**envelope, **payload}


class ReceiptParseDiagnosticCode(StrEnum):
    UNKNOWN_FIELD = "ERR_RECEIPT_FIELD_UNKNOWN"
    UNKNOWN_KIND = "ERR_RECEIPT_KIND_INVALID"
    SCHEMA_INVALID = "ERR_RECEIPT_SCHEMA_INVALID"
    TARGET_MISSING = "ERR_RECEIPT_TARGET_MISSING"
    NODE_PLAN_DIGEST_MISSING = "ERR_RECEIPT_NODE_PLAN_DIGEST_MISSING"
    PREDECESSOR_MISSING = "ERR_RECEIPT_PREDECESSOR_MISSING"
    EVIDENCE_MISSING = "ERR_RECEIPT_EVIDENCE_MISSING"
    CODE_REVISION_MISSING = "ERR_RECEIPT_CODE_REVISION_MISSING"
    IMPACT_CLOSURE_MISSING = "ERR_RECEIPT_IMPACT_CLOSURE_MISSING"
    IMPACT_CLOSURE_INVALID = "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"


class ReceiptValidityCode(StrEnum):
    """Stable local receipt-currentness results."""

    CURRENT = "CURRENT"
    SCHEMA_UNSUPPORTED = "ERR_RECEIPT_SCHEMA_UNSUPPORTED"
    TARGET_MISSING = "ERR_RECEIPT_TARGET_MISSING"
    DELIVERY_DIGEST_STALE = "ERR_RECEIPT_DELIVERY_DIGEST_STALE"
    NODE_PLAN_DIGEST_STALE = "ERR_RECEIPT_NODE_PLAN_DIGEST_STALE"
    PROOF_UNSATISFIED = "ERR_RECEIPT_PROOF_UNSATISFIED"
    FIELD_MISSING = "ERR_RECEIPT_FIELD_MISSING"
    IMPACT_CLOSURE_MISSING = "ERR_RECEIPT_IMPACT_CLOSURE_MISSING"
    IMPACT_CLOSURE_INVALID = "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"
    CODE_REVISION_MISSING = "ERR_RECEIPT_CODE_REVISION_MISSING"
    CODE_REVISION_NOT_DESCENDANT = "ERR_RECEIPT_CODE_REVISION_NOT_DESCENDANT"
    CODE_PATH_STALE = "ERR_RECEIPT_CODE_PATH_STALE"
    CODE_HISTORY_UNAVAILABLE = "ERR_RECEIPT_CODE_HISTORY_UNAVAILABLE"
    PREDECESSOR_MISSING = "ERR_RECEIPT_PREDECESSOR_MISSING"
    PREDECESSOR_INVALID = "ERR_RECEIPT_PREDECESSOR_INVALID"
    PREDECESSOR_CYCLE = "ERR_RECEIPT_PREDECESSOR_CYCLE"
    SUPERSEDED = "ERR_RECEIPT_SUPERSEDED"


class ReceiptValidity(_ReceiptModel):
    """The deterministic local-currentness result for one receipt."""

    code: ReceiptValidityCode
    detail: str
    target: str | None = None
    path: str | None = None
    selector: str | None = None

    @property
    def current(self) -> bool:
        """Whether local authority and proof checks are current."""
        return self.code is ReceiptValidityCode.CURRENT


class RepositoryHistory(Protocol):
    """Deterministic repository-history operations used by receipt currency checks."""

    def revisions_exist(self, tested_revision: str, candidate_revision: str) -> bool:
        """Return whether both revision identifiers resolve to commits."""

    def is_descendant(self, tested_revision: str, candidate_revision: str) -> bool:
        """Return whether the candidate descends from the tested revision."""

    def name_status(self, tested_revision: str, candidate_revision: str) -> bytes:
        """Return NUL-delimited Git name-status output for the revision range."""


class RepositoryHistoryError(RuntimeError):
    """Report a repository-history query that cannot establish currency."""


class GitRepositoryHistory:
    """Repository-history adapter backed by deterministic Git commands."""

    def __init__(self, repository: Path) -> None:
        self._repository = repository

    def revisions_exist(self, tested_revision: str, candidate_revision: str) -> bool:
        return all(
            self._run("rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}", allow_missing=True) is not None
            for revision in (tested_revision, candidate_revision)
        )

    def is_descendant(self, tested_revision: str, candidate_revision: str) -> bool:
        return (
            self._run("merge-base", "--is-ancestor", tested_revision, candidate_revision, allow_missing=True)
            is not None
        )

    def name_status(self, tested_revision: str, candidate_revision: str) -> bytes:
        result = self._run(
            "diff",
            "--name-status",
            "-z",
            "-M",
            "-C",
            "--find-copies-harder",
            tested_revision,
            candidate_revision,
        )
        assert result is not None
        return result

    def _run(self, *arguments: str, allow_missing: bool = False) -> bytes | None:
        try:
            command = ["git", "-C", str(self._repository), *arguments]
            result = subprocess.run(  # noqa: S603 -- fixed command-vector invocation
                command,
                check=False,
                capture_output=True,
            )
        except OSError as exc:
            raise RepositoryHistoryError from exc
        if result.returncode == 0:
            return result.stdout
        if allow_missing and result.returncode == 1:
            return None
        raise RepositoryHistoryError


def evaluate_code_revision_currency(
    history: RepositoryHistory,
    tested_revision: str,
    candidate_revision: str,
    impact_closure: ImpactClosure,
) -> ReceiptValidity:
    """Classify whether a candidate revision preserves a receipt's frozen path closure."""
    try:
        if not history.revisions_exist(tested_revision, candidate_revision):
            return ReceiptValidity(
                code=ReceiptValidityCode.CODE_REVISION_MISSING,
                detail="tested or candidate code revision does not exist",
            )
        if tested_revision == candidate_revision:
            return ReceiptValidity(code=ReceiptValidityCode.CURRENT, detail="candidate matches tested code revision")
        if not history.is_descendant(tested_revision, candidate_revision):
            return ReceiptValidity(
                code=ReceiptValidityCode.CODE_REVISION_NOT_DESCENDANT,
                detail="candidate code revision does not descend from the tested revision",
            )
        for path in _name_status_paths(history.name_status(tested_revision, candidate_revision)):
            selector = _intersecting_selector(path, impact_closure.paths)
            if selector is not None:
                return ReceiptValidity(
                    code=ReceiptValidityCode.CODE_PATH_STALE,
                    detail="changed code path intersects the receipt impact closure",
                    path=path,
                    selector=selector,
                )
    except (RepositoryHistoryError, UnicodeDecodeError, ValueError):
        return ReceiptValidity(
            code=ReceiptValidityCode.CODE_HISTORY_UNAVAILABLE,
            detail="repository history could not prove code-revision currency",
        )
    return ReceiptValidity(
        code=ReceiptValidityCode.CURRENT,
        detail="no changed code path intersects the receipt impact closure",
    )


def _name_status_paths(value: bytes) -> tuple[str, ...]:
    fields = value.split(b"\0")
    if not fields or fields.pop() != b"":
        msg = "Git name-status output is not NUL terminated"
        raise ValueError(msg)
    paths: list[str] = []
    while fields:
        status = fields.pop(0).decode("ascii")
        if status.startswith(("R", "C")):
            if len(status) == 1 or not status[1:].isdigit():
                msg = "Git name-status output is malformed"
                raise ValueError(msg)
            path_count = 2
        elif status in {"A", "M", "D", "T", "U", "X", "B"}:
            path_count = 1
        else:
            msg = "Git name-status output is malformed"
            raise ValueError(msg)
        if len(fields) < path_count:
            msg = "Git name-status output is malformed"
            raise ValueError(msg)
        raw_paths, fields = fields[:path_count], fields[path_count:]
        paths.extend(parse_repository_path(raw_path.decode("utf-8", errors="strict")) for raw_path in raw_paths)
    return tuple(paths)


def _intersecting_selector(path: str, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        if selector in ("/", path) or (selector.endswith("/") and path.startswith(selector)):
            return selector
    return None


class ReceiptParseDiagnostic(_ReceiptModel):
    code: ReceiptParseDiagnosticCode
    detail: str
    target: str | None = None


class ReceiptParseResult(_ReceiptModel):
    receipt: ReceiptRecord | None = None
    diagnostics: tuple[ReceiptParseDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> ReceiptParseResult:
        if (self.receipt is None) == (not self.diagnostics):
            detail = "receipt parse result must contain one outcome"
            raise ValueError(detail)
        return self


def parse_receipt_mapping(value: Mapping[str, object]) -> ReceiptParseResult:
    """Parse a receipt and validate purpose-specific evidence links."""
    try:
        record = ReceiptRecord.from_mapping(value)
    except ImpactClosureError as exc:
        code = (
            ReceiptParseDiagnosticCode.IMPACT_CLOSURE_MISSING
            if str(exc) == ImpactClosureError.MISSING
            else ReceiptParseDiagnosticCode.IMPACT_CLOSURE_INVALID
        )
        return ReceiptParseResult(diagnostics=(ReceiptParseDiagnostic(code=code, detail=str(exc)),))
    except (PydanticValidationError, TypeError, ValueError) as exc:
        message = str(exc)
        code = ReceiptParseDiagnosticCode.SCHEMA_INVALID
        if "kind" in message:
            code = ReceiptParseDiagnosticCode.UNKNOWN_KIND
        elif "Extra inputs" in message:
            code = ReceiptParseDiagnosticCode.UNKNOWN_FIELD
        return ReceiptParseResult(diagnostics=(ReceiptParseDiagnostic(code=code, detail=message),))
    if record.kind == "admission":
        return ReceiptParseResult(receipt=record)
    required = {
        "target_node_id": ReceiptParseDiagnosticCode.TARGET_MISSING,
        "predecessor_receipt_ids": ReceiptParseDiagnosticCode.PREDECESSOR_MISSING,
        "evidence": ReceiptParseDiagnosticCode.EVIDENCE_MISSING,
        "code_revision": ReceiptParseDiagnosticCode.CODE_REVISION_MISSING,
    }
    if record.kind in {"shape", "build", "accept"}:
        required["node_plan_digest"] = ReceiptParseDiagnosticCode.NODE_PLAN_DIGEST_MISSING
    diagnostics = tuple(
        ReceiptParseDiagnostic(code=code, detail=f"receipt payload is missing {field}")
        for field, code in sorted(required.items())
        if field not in record.payload
    )
    return ReceiptParseResult(diagnostics=diagnostics) if diagnostics else ReceiptParseResult(receipt=record)


def compute_node_plan_digest(revision: ChangeRevision, target: str) -> Digest:
    """Return the canonical digest for one delivery node and its packet plan."""
    node = revision.resolve(target)
    if not hasattr(node, "proof"):
        msg = f"receipt target is not a delivery node: {target}"
        raise KeyError(msg)
    payload = {
        "delivery_digest": revision.delivery_digest,
        "node": node.model_dump(mode="json"),
        "node_plan": revision.graph.execution.node_plans.get(target),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _target_proof(revision: ChangeRevision, target: str) -> Proof | None:
    try:
        node = revision.resolve(target)
    except KeyError:
        return None
    if not hasattr(node, "proof"):
        return None
    proof = revision.resolve(node.proof)
    return proof if isinstance(proof, Proof) else None


def evaluate_receipt_currentness(revision: ChangeRevision, receipt: ReceiptRecord) -> ReceiptValidity:
    """Evaluate local receipt authority and proof currentness without graph traversal."""
    if receipt.schema_version != 1:
        result = ReceiptValidity(
            code=ReceiptValidityCode.SCHEMA_UNSUPPORTED,
            detail="receipt schema version is unsupported",
        )
    elif receipt.delivery_digest != revision.delivery_digest:
        result = ReceiptValidity(
            code=ReceiptValidityCode.DELIVERY_DIGEST_STALE,
            detail="receipt delivery digest differs from the loaded revision",
        )
    elif receipt.kind != "admission" and receipt.impact_closure is None:
        result = ReceiptValidity(
            code=ReceiptValidityCode.IMPACT_CLOSURE_MISSING,
            detail="receipt is missing impact_closure",
        )
    elif (
        receipt.kind != "admission"
        and (undeclared_target := _undeclared_authority_target(revision, receipt.impact_closure)) is not None
    ):
        result = ReceiptValidity(
            code=ReceiptValidityCode.IMPACT_CLOSURE_INVALID,
            detail="receipt impact closure references an undeclared authority target",
            target=undeclared_target,
        )
    elif receipt.kind == "admission":
        result = ReceiptValidity(code=ReceiptValidityCode.CURRENT, detail="admission receipt is locally current")
    else:
        result = _evaluate_target_receipt(revision, receipt)
    return result


def _evaluate_target_receipt(revision: ChangeRevision, receipt: ReceiptRecord) -> ReceiptValidity:
    target = receipt.payload.get("target_node_id")
    if not isinstance(target, str) or _target_proof(revision, target) is None:
        return ReceiptValidity(
            code=ReceiptValidityCode.TARGET_MISSING,
            detail="receipt target delivery node does not exist",
            target=target if isinstance(target, str) else None,
        )
    node_plan_digest = receipt.payload.get("node_plan_digest")
    if not isinstance(node_plan_digest, str):
        return ReceiptValidity(
            code=ReceiptValidityCode.FIELD_MISSING,
            detail="receipt payload is missing node_plan_digest",
            target=target,
        )
    if node_plan_digest != compute_node_plan_digest(revision, target):
        return ReceiptValidity(
            code=ReceiptValidityCode.NODE_PLAN_DIGEST_STALE,
            detail="receipt node plan digest differs from the loaded revision",
            target=target,
        )
    evidence = receipt.payload.get("evidence")
    proof = _target_proof(revision, target)
    methods = evidence.get("methods") if isinstance(evidence, Mapping) else None
    if (
        not proof
        or not isinstance(methods, tuple)
        or not all(isinstance(method, str) for method in methods)
        or not set(proof.method) <= set(methods)
    ):
        return ReceiptValidity(
            code=ReceiptValidityCode.PROOF_UNSATISFIED,
            detail="receipt evidence does not satisfy the target proof contract",
            target=target,
        )
    return ReceiptValidity(code=ReceiptValidityCode.CURRENT, detail="receipt is locally current", target=target)


class ReceiptDiagnosticCode(StrEnum):
    """Stable receipt-store diagnostic codes."""

    PATH_UNSAFE = "ERR_RECEIPT_PATH_UNSAFE"
    FILE_MISSING = "ERR_RECEIPT_FILE_MISSING"
    ENCODING = "ERR_RECEIPT_ENCODING"
    YAML_PARSE = "ERR_RECEIPT_YAML_PARSE"
    SCHEMA_INVALID = "ERR_RECEIPT_SCHEMA_INVALID"
    ID_MISMATCH = "ERR_RECEIPT_ID_MISMATCH"
    REVISION_MISMATCH = "ERR_RECEIPT_REVISION_MISMATCH"
    IMPACT_CLOSURE_MISSING = "ERR_RECEIPT_IMPACT_CLOSURE_MISSING"
    IMPACT_CLOSURE_INVALID = "ERR_RECEIPT_IMPACT_CLOSURE_INVALID"


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


def _receipt_location(receipt_id: str) -> tuple[str, str]:
    if (
        "\x00" in receipt_id
        or not _RECEIPT_ID_RE.fullmatch(receipt_id)
        or PurePosixPath(receipt_id).is_absolute()
        or PureWindowsPath(receipt_id).is_absolute()
    ):
        _fail(ReceiptDiagnosticCode.PATH_UNSAFE, "receipt ID is not a safe canonical identifier")
    filename = f"{receipt_id}.yaml"
    return filename, f"receipts/{filename}"


def _open_receipts_directory(
    source_dir: Path,
    source_identity: tuple[int, int],
    *,
    create: bool,
) -> int | None:
    try:
        source_fd = os.open(source_dir, _DIRECTORY_OPEN_FLAGS)
    except OSError:
        _fail(ReceiptDiagnosticCode.PATH_UNSAFE, "change directory could not be opened safely")
    try:
        source_stat = os.fstat(source_fd)
        if (source_stat.st_dev, source_stat.st_ino) != source_identity:
            _fail(ReceiptDiagnosticCode.PATH_UNSAFE, "change directory identity has changed")
        if create:
            with contextlib.suppress(FileExistsError):
                os.mkdir("receipts", mode=0o755, dir_fd=source_fd)
        try:
            return os.open("receipts", _DIRECTORY_OPEN_FLAGS, dir_fd=source_fd)
        except FileNotFoundError:
            if not create:
                return None
            raise
        except OSError:
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipts directory could not be opened safely",
                path="receipts",
            )
    except OSError:
        _fail(
            ReceiptDiagnosticCode.PATH_UNSAFE,
            "receipts directory could not be created safely",
            path="receipts",
        )
    finally:
        os.close(source_fd)


@contextlib.contextmanager
def _receipts_directory(
    source_dir: Path,
    source_identity: tuple[int, int],
    *,
    create: bool,
) -> Iterator[int | None]:
    directory_fd = _open_receipts_directory(source_dir, source_identity, create=create)
    try:
        yield directory_fd
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def _create_temp_file(directory_fd: int) -> tuple[int, str]:
    for _attempt in range(_TEMP_CREATE_ATTEMPTS):
        name = f".tmp-{secrets.token_hex(16)}.yaml"
        try:
            return os.open(name, _TEMP_OPEN_FLAGS, 0o600, dir_fd=directory_fd), name
        except FileExistsError:
            continue
    msg = "could not allocate a unique receipt temporary file"
    raise FileExistsError(msg)


def _file_identity(file_stat: os.stat_result) -> tuple[int, int]:
    return file_stat.st_dev, file_stat.st_ino


def _entry_identity(directory_fd: int, name: str) -> tuple[int, int]:
    return _file_identity(os.stat(name, dir_fd=directory_fd, follow_symlinks=False))


def _validate_published_file(directory_fd: int, filename: str, expected_identity: tuple[int, int]) -> None:
    published_fd = os.open(filename, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
    try:
        if _file_identity(os.fstat(published_fd)) != expected_identity:
            raise OSError(errno.ESTALE, "published receipt identity changed")
        os.fsync(published_fd)
        os.fsync(directory_fd)
        if _entry_identity(directory_fd, filename) != expected_identity:
            raise OSError(errno.ESTALE, "published receipt identity changed")
    finally:
        os.close(published_fd)


def _atomic_create(directory_fd: int, filename: str, content: str, receipt_id: str) -> None:
    file_fd, temp_name = _create_temp_file(directory_fd)
    try:
        expected_identity = _file_identity(os.fstat(file_fd))
        os.fchmod(file_fd, 0o644)
        with os.fdopen(os.dup(file_fd), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if _entry_identity(directory_fd, temp_name) != expected_identity:
            raise OSError(errno.ESTALE, "receipt temporary file identity changed")
        try:
            os.link(
                temp_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            raise ReceiptConflictError(receipt_id) from None
        try:
            _validate_published_file(directory_fd, filename, expected_identity)
        except OSError:
            with contextlib.suppress(OSError):
                os.unlink(filename, dir_fd=directory_fd)
            raise
    finally:
        with contextlib.suppress(OSError):
            os.unlink(temp_name, dir_fd=directory_fd)
        os.close(file_fd)


def _read_receipt_text(directory_fd: int, filename: str, receipt_id: str, path: str) -> str:
    try:
        file_fd = os.open(filename, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
    except FileNotFoundError:
        _fail(ReceiptDiagnosticCode.FILE_MISSING, "receipt file is missing", path=path, target=receipt_id)
    except OSError as exc:
        code = (
            ReceiptDiagnosticCode.PATH_UNSAFE
            if exc.errno in {errno.ELOOP, errno.ENOTDIR}
            else ReceiptDiagnosticCode.FILE_MISSING
        )
        _fail(code, "receipt file could not be opened safely", path=path, target=receipt_id)
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            _fail(
                ReceiptDiagnosticCode.PATH_UNSAFE,
                "receipt path must identify a regular file",
                path=path,
                target=receipt_id,
            )
        try:
            with os.fdopen(file_fd, "r", encoding="utf-8") as handle:
                return handle.read()
        except UnicodeDecodeError:
            _fail(
                ReceiptDiagnosticCode.ENCODING,
                "receipt file is not strict UTF-8",
                path=path,
                target=receipt_id,
            )
    finally:
        with contextlib.suppress(OSError):
            os.close(file_fd)


class ReceiptStore:
    """Contained immutable receipt store for one loaded change revision."""

    def __init__(self, revision: ChangeRevision) -> None:
        self._revision = revision

    def _validate_record(
        self,
        receipt_id: str,
        value: Mapping[str, object],
        *,
        path: str,
    ) -> ReceiptRecord:
        try:
            record = ReceiptRecord.from_mapping(value)
        except ImpactClosureError as exc:
            code = (
                ReceiptDiagnosticCode.IMPACT_CLOSURE_MISSING
                if str(exc) == ImpactClosureError.MISSING
                else ReceiptDiagnosticCode.IMPACT_CLOSURE_INVALID
            )
            _fail(code, str(exc), path=path, target=receipt_id)
        except (PydanticValidationError, TypeError, ValueError) as exc:
            detail = _schema_detail(exc) if isinstance(exc, PydanticValidationError) else "receipt schema is invalid"
            _fail(ReceiptDiagnosticCode.SCHEMA_INVALID, detail, path=path, target=receipt_id)
        if record.schema_version != 1:
            _fail(
                ReceiptDiagnosticCode.SCHEMA_INVALID,
                "receipt schema version is unsupported",
                path=path,
                target=receipt_id,
            )
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
        if (
            record.impact_closure is not None
            and (undeclared_target := _undeclared_authority_target(self._revision, record.impact_closure)) is not None
        ):
            _fail(
                ReceiptDiagnosticCode.IMPACT_CLOSURE_INVALID,
                "receipt impact closure references an undeclared authority target",
                path=path,
                target=undeclared_target,
            )
        return record

    def create(self, receipt_id: str, value: Mapping[str, object]) -> ReceiptResult:
        """Create one immutable receipt without overwriting an existing receipt."""
        try:
            filename, relative_path = _receipt_location(receipt_id)
            record = self._validate_record(receipt_id, value, path=relative_path)
            stream = StringIO()
            make_yaml(explicit_start=True).dump(record.to_mapping(), stream)
            with _receipts_directory(
                self._revision.source_dir,
                self._revision.source_identity,
                create=True,
            ) as directory_fd:
                if directory_fd is None:
                    _fail(
                        ReceiptDiagnosticCode.PATH_UNSAFE,
                        "receipts directory could not be created safely",
                        path="receipts",
                    )
                try:
                    _atomic_create(directory_fd, filename, stream.getvalue(), receipt_id)
                except ReceiptConflictError:
                    raise
                except OSError:
                    _fail(
                        ReceiptDiagnosticCode.PATH_UNSAFE,
                        "receipt file could not be created safely",
                        path=relative_path,
                        target=receipt_id,
                    )
        except _ReceiptFailure as exc:
            return ReceiptResult(diagnostics=(exc.diagnostic,))
        return ReceiptResult(receipt=record)

    def create_participant(
        self, receipt_id: str, value: Mapping[str, object]
    ) -> tuple[ReceiptRecord, TransactionParticipant]:
        """Validate and plan one immutable receipt transaction participant."""
        filename, relative_path = _receipt_location(receipt_id)
        record = self._validate_record(receipt_id, value, path=relative_path)
        stream = StringIO()
        make_yaml(explicit_start=True).dump(record.to_mapping(), stream)
        return record, TransactionParticipant(
            self._revision.source_dir,
            Path("receipts") / filename,
            stream.getvalue().encode("utf-8"),
        )

    def _read_from_directory(self, directory_fd: int, receipt_id: str, filename: str, path: str) -> ReceiptResult:
        try:
            text = _read_receipt_text(directory_fd, filename, receipt_id, path)
            try:
                value = make_yaml().load(text)
            except YAMLError:
                _fail(
                    ReceiptDiagnosticCode.YAML_PARSE,
                    "receipt YAML could not be parsed",
                    path=path,
                    target=receipt_id,
                )
            if not isinstance(value, Mapping):
                _fail(
                    ReceiptDiagnosticCode.SCHEMA_INVALID,
                    "receipt document must be a mapping",
                    path=path,
                    target=receipt_id,
                )
            record = self._validate_record(receipt_id, value, path=path)
        except _ReceiptFailure as exc:
            return ReceiptResult(diagnostics=(exc.diagnostic,))
        return ReceiptResult(receipt=record)

    def read(self, receipt_id: str) -> ReceiptResult:
        """Read and validate one immutable receipt."""
        try:
            filename, relative_path = _receipt_location(receipt_id)
            with _receipts_directory(
                self._revision.source_dir,
                self._revision.source_identity,
                create=False,
            ) as directory_fd:
                if directory_fd is None:
                    _fail(
                        ReceiptDiagnosticCode.FILE_MISSING,
                        "receipt file is missing",
                        path=relative_path,
                        target=receipt_id,
                    )
                return self._read_from_directory(directory_fd, receipt_id, filename, relative_path)
        except _ReceiptFailure as exc:
            return ReceiptResult(diagnostics=(exc.diagnostic,))

    def list(self) -> tuple[ReceiptResult, ...]:
        """List canonical receipts in ascending receipt-ID order."""
        entries, diagnostic = self._scan()
        if diagnostic is not None:
            return (ReceiptResult(diagnostics=(diagnostic,)),)
        return tuple(result for _path, result in entries)

    def evaluate_currentness(
        self,
        receipt_id: str,
        history: RepositoryHistory,
        candidate_revision: str,
    ) -> ReceiptValidity:
        """Evaluate local, code, predecessor, and supersession receipt currentness."""
        entries, diagnostic = self._scan()
        if diagnostic is not None:
            return ReceiptValidity(
                code=ReceiptValidityCode.PREDECESSOR_INVALID,
                detail="receipt storage could not be scanned",
                target=receipt_id,
            )
        records = {result.receipt.receipt_id: result.receipt for _path, result in entries if result.receipt is not None}
        superseded = {
            target
            for receipt in records.values()
            if receipt.kind == "supersession"
            for target in (receipt.payload.get("invalidated_receipt_ids") or ())
            if isinstance(target, str)
        }
        return _CompleteCurrentnessEvaluator(
            self._revision,
            records,
            superseded,
            history,
            candidate_revision,
        ).evaluate(receipt_id)

    def _scan(self) -> tuple[tuple[tuple[str, ReceiptResult], ...], ReceiptDiagnostic | None]:
        try:
            with _receipts_directory(
                self._revision.source_dir,
                self._revision.source_identity,
                create=False,
            ) as directory_fd:
                if directory_fd is None:
                    return (), None
                entries: list[tuple[str, ReceiptResult]] = []
                names = os.listdir(directory_fd)  # noqa: PTH208 - Path.iterdir cannot use the pinned descriptor.
                for filename in sorted(name for name in names if name.endswith(".yaml")):
                    receipt_id = PurePosixPath(filename).stem
                    relative_path = f"receipts/{filename}"
                    try:
                        expected_filename, _expected_path = _receipt_location(receipt_id)
                        if filename != expected_filename:
                            _fail(
                                ReceiptDiagnosticCode.PATH_UNSAFE,
                                "receipt filename is not canonical",
                                path=relative_path,
                            )
                        result = self._read_from_directory(directory_fd, receipt_id, filename, relative_path)
                    except _ReceiptFailure as exc:
                        result = ReceiptResult(diagnostics=(exc.diagnostic,))
                    entries.append((relative_path, result))
                return tuple(entries), None
        except _ReceiptFailure as exc:
            return (), exc.diagnostic


class _CompleteCurrentnessEvaluator:
    def __init__(
        self,
        revision: ChangeRevision,
        records: Mapping[str, ReceiptRecord],
        superseded: set[str],
        history: RepositoryHistory,
        candidate_revision: str,
    ) -> None:
        self._revision = revision
        self._records = records
        self._superseded = superseded
        self._history = history
        self._candidate_revision = candidate_revision
        self._memo: dict[str, ReceiptValidity] = {}
        self._active: set[str] = set()

    def evaluate(self, receipt_id: str) -> ReceiptValidity:
        if receipt_id in self._memo:
            return self._memo[receipt_id]
        if receipt_id in self._active:
            return ReceiptValidity(
                code=ReceiptValidityCode.PREDECESSOR_CYCLE,
                detail="receipt predecessor graph contains a cycle",
                target=receipt_id,
            )
        if receipt_id in self._superseded:
            result = ReceiptValidity(
                code=ReceiptValidityCode.SUPERSEDED,
                detail="a supersession receipt explicitly invalidates this receipt",
                target=receipt_id,
            )
            self._memo[receipt_id] = result
            return result
        receipt = self._records.get(receipt_id)
        if receipt is None:
            return ReceiptValidity(
                code=ReceiptValidityCode.PREDECESSOR_MISSING,
                detail="referenced predecessor receipt is missing",
                target=receipt_id,
            )
        self._active.add(receipt_id)
        try:
            result = self._evaluate_record(receipt)
        finally:
            self._active.remove(receipt_id)
        self._memo[receipt_id] = result
        return result

    def _evaluate_record(self, receipt: ReceiptRecord) -> ReceiptValidity:
        local = evaluate_receipt_currentness(self._revision, receipt)
        if not local.current:
            return local
        code = self._evaluate_code_revision(receipt)
        return self._evaluate_predecessors(receipt) if code.current else code

    def _evaluate_code_revision(self, receipt: ReceiptRecord) -> ReceiptValidity:
        tested_revision = receipt.payload.get("code_revision")
        if not isinstance(tested_revision, str) or receipt.impact_closure is None:
            return ReceiptValidity(
                code=ReceiptValidityCode.CODE_REVISION_MISSING,
                detail="receipt payload is missing code_revision",
                target=receipt.receipt_id,
            )
        return evaluate_code_revision_currency(
            self._history,
            tested_revision,
            self._candidate_revision,
            receipt.impact_closure,
        )

    def _evaluate_predecessors(self, receipt: ReceiptRecord) -> ReceiptValidity:
        predecessors = receipt.payload.get("predecessor_receipt_ids")
        if not isinstance(predecessors, tuple) or not all(isinstance(item, str) for item in predecessors):
            return ReceiptValidity(
                code=ReceiptValidityCode.FIELD_MISSING,
                detail="receipt payload is missing predecessor_receipt_ids",
                target=receipt.receipt_id,
            )
        for predecessor_id in predecessors:
            predecessor = self.evaluate(predecessor_id)
            if not predecessor.current:
                code = predecessor.code
                if code not in {
                    ReceiptValidityCode.PREDECESSOR_MISSING,
                    ReceiptValidityCode.PREDECESSOR_CYCLE,
                }:
                    code = ReceiptValidityCode.PREDECESSOR_INVALID
                return ReceiptValidity(
                    code=code,
                    detail="referenced predecessor receipt is not current",
                    target=predecessor.target if code is ReceiptValidityCode.PREDECESSOR_CYCLE else predecessor_id,
                )
        return ReceiptValidity(code=ReceiptValidityCode.CURRENT, detail="receipt is completely current")


def _health_finding(diagnostic: ReceiptDiagnostic, *, checked_path: str) -> ChangeHealthFinding:
    return ChangeHealthFinding(
        code=diagnostic.code.value,
        detail=diagnostic.detail,
        path=diagnostic.path or checked_path,
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
    expected_path, expected_finding = _expected_admission_path(revision)
    entries, storage_diagnostic = store._scan()  # noqa: SLF001 - same-module health collaborator
    receipt_storage_usable = storage_diagnostic is None
    if expected_finding is not None:
        findings.append(expected_finding)
    if storage_diagnostic is not None:
        findings.append(_health_finding(storage_diagnostic, checked_path="receipts"))
    for relative_path, result in entries:
        checked_paths.append(relative_path)
        findings.extend(_health_finding(item, checked_path=relative_path) for item in result.diagnostics)

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
    "ReceiptParseDiagnostic",
    "ReceiptParseDiagnosticCode",
    "ReceiptParseResult",
    "ReceiptRecord",
    "ReceiptResult",
    "ReceiptStore",
    "change_health",
    "parse_receipt_mapping",
]
