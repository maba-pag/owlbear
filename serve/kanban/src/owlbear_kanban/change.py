"""Native change authority loading and semantic identity."""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
from collections.abc import Iterator, Mapping
from datetime import date, datetime, time
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Annotated, Literal, Never

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    model_validator,
)
from pydantic import (
    ValidationError as PydanticValidationError,
)
from ruamel.yaml.error import YAMLError

from owlbear_kanban._naming import validate_path_containment
from owlbear_kanban.runtime_transaction import (
    RuntimeTransaction,
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)
from owlbear_kanban.yaml_rt import make_yaml

_CHANGE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_STABLE_ID_PATTERN = r"^(?:REQ|NEG|KEEP|DEC|WF|MOD|IF|MIG|RISK|PROOF|DN)-[0-9]{3}$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_CHANGE_ID_RE = re.compile(_CHANGE_ID_PATTERN)
_STABLE_ID_RE = re.compile(_STABLE_ID_PATTERN)
_DIRECTORY_OPEN_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_OPEN_FLAGS = os.O_RDONLY | os.O_NOFOLLOW

ChangeId = Annotated[str, StringConstraints(strict=True, pattern=_CHANGE_ID_PATTERN)]
StableId = Annotated[str, StringConstraints(strict=True, pattern=_STABLE_ID_PATTERN)]
Digest = Annotated[str, StringConstraints(strict=True, pattern=_DIGEST_PATTERN)]


def _list_to_tuple(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


type FrozenSequence[T] = Annotated[tuple[T, ...], BeforeValidator(_list_to_tuple)]
type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def _freeze_json(value: JsonValue) -> object:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> JsonValue:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_thaw_json(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    msg = f"unsupported frozen JSON value: {type(value).__name__}"
    raise TypeError(msg)


class _BoundaryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, strict=True)


class DecisionOption(_BoundaryModel):
    id: str
    label: str
    confidence: Annotated[float, Field(allow_inf_nan=False)]
    recommended: bool
    pros: FrozenSequence[str]
    cons: FrozenSequence[str]
    risks: FrozenSequence[str]


class Decision(_BoundaryModel):
    id: StableId
    title: str
    status: Literal["pending", "accepted", "superseded"]
    decided_at: str | date | datetime | time | None = None
    authority: str
    selected: str | None = None
    rationale: str
    options: FrozenSequence[DecisionOption]


class DecisionsDocument(_BoundaryModel):
    """Collect the versioned authority decisions for one change."""

    schema_version: Literal[1]
    change_id: ChangeId
    decisions: FrozenSequence[Decision]


class Requirement(_BoundaryModel):
    id: StableId
    title: str
    statement: str
    workflows: FrozenSequence[StableId]


class NegativeRequirement(_BoundaryModel):
    id: StableId
    statement: str


class PreservedBehavior(_BoundaryModel):
    id: StableId
    statement: str


class Workflow(_BoundaryModel):
    id: StableId
    title: str
    entry: str
    result: str
    proof: StableId


class Module(_BoundaryModel):
    id: StableId
    paths: FrozenSequence[str]
    current_responsibility: str
    planned_change: str


class Interface(_BoundaryModel):
    id: StableId
    name: str
    producer: StableId
    consumers: FrozenSequence[StableId]
    terminal_plan_prerequisite: bool = False
    contract: str
    authority: StableId
    failure_semantics: str
    migration: StableId | None
    proof: StableId
    runtime_producer: str | None = None
    runtime_consumers: FrozenSequence[str] = ()


class Migration(_BoundaryModel):
    id: StableId
    title: str
    owner: StableId
    source: str = Field(alias="from")
    destination: str = Field(alias="to")
    ordered_steps: FrozenSequence[str]
    consumer_inventory: FrozenSequence[str]
    compatibility: str
    deletion_owner: StableId
    absence_proof: StableId


class Risk(_BoundaryModel):
    id: StableId
    risk_class: str = Field(alias="class")
    title: str
    scenarios: FrozenSequence[str]
    disposition: str
    owner: StableId
    supporting_nodes: FrozenSequence[StableId] = ()
    proof: StableId


class Proof(_BoundaryModel):
    id: StableId
    title: str
    boundary: str
    owner: StableId
    method: FrozenSequence[str]
    allowed_replacements: FrozenSequence[str]
    durable_outputs: FrozenSequence[str]


class DeliveryNode(_BoundaryModel):
    id: StableId
    title: str
    outcome: str
    owns: FrozenSequence[StableId]
    supports: FrozenSequence[StableId]
    modules: FrozenSequence[StableId]
    produces: FrozenSequence[StableId]
    consumes: FrozenSequence[StableId]
    dependencies: FrozenSequence[StableId]
    risks: FrozenSequence[StableId]
    proof: StableId


class DeliveryObligationsDocument(_BoundaryModel):
    """Own product obligations and workflows in a modular change package."""

    schema_version: Literal[1]
    change_id: ChangeId
    requirements: FrozenSequence[Requirement]
    negative_requirements: FrozenSequence[NegativeRequirement]
    preserved_behaviors: FrozenSequence[PreservedBehavior]
    workflows: FrozenSequence[Workflow]


class DeliveryContractsDocument(_BoundaryModel):
    """Own module, interface, migration, risk, and proof contracts."""

    schema_version: Literal[1]
    change_id: ChangeId
    modules: FrozenSequence[Module]
    interfaces: FrozenSequence[Interface]
    migrations: FrozenSequence[Migration]
    risks: FrozenSequence[Risk]
    proofs: FrozenSequence[Proof]


type StableEntity = (
    Decision
    | Requirement
    | NegativeRequirement
    | PreservedBehavior
    | Workflow
    | Module
    | Interface
    | Migration
    | Risk
    | Proof
    | DeliveryNode
)

DELIVERY_SECTION_NAMES = (
    "requirements",
    "negative_requirements",
    "preserved_behaviors",
    "workflows",
    "modules",
    "interfaces",
    "migrations",
    "risks",
    "proofs",
    "nodes",
)

_SECTION_PREFIXES = {
    "decisions": "DEC",
    "requirements": "REQ",
    "negative_requirements": "NEG",
    "preserved_behaviors": "KEEP",
    "workflows": "WF",
    "modules": "MOD",
    "interfaces": "IF",
    "migrations": "MIG",
    "risks": "RISK",
    "proofs": "PROOF",
    "nodes": "DN",
}


class AuthorityMetadata(_BoundaryModel):
    intent: Literal["intent.md"]
    design: Literal["design.md"]
    decisions: Literal["decisions.yaml"]
    research: FrozenSequence[str]


class AdmissionMetadata(_BoundaryModel):
    state: Literal["admitted"]
    delivery_digest: Digest
    receipt: str
    limits: FrozenSequence[str]


class DeliveryNodesDocument(_BoundaryModel):
    """Own delivery-node topology and package-level graph metadata."""

    schema_version: Literal[1]
    change_id: ChangeId
    state: Literal["draft", "admitted", "executing", "accepted", "abandoned", "superseded"]
    authority: AuthorityMetadata
    admission: AdmissionMetadata | None = None
    nodes: FrozenSequence[DeliveryNode]


class DeliveryGraph(_BoundaryModel):
    """Represent the authored delivery authority for a change."""

    schema_version: Literal[1]
    change_id: ChangeId
    state: Literal["draft", "admitted", "executing", "accepted", "abandoned", "superseded"]
    authority: AuthorityMetadata
    admission: AdmissionMetadata | None = None
    requirements: FrozenSequence[Requirement]
    negative_requirements: FrozenSequence[NegativeRequirement]
    preserved_behaviors: FrozenSequence[PreservedBehavior]
    workflows: FrozenSequence[Workflow]
    modules: FrozenSequence[Module]
    interfaces: FrozenSequence[Interface]
    migrations: FrozenSequence[Migration]
    risks: FrozenSequence[Risk]
    proofs: FrozenSequence[Proof]
    nodes: FrozenSequence[DeliveryNode]

    def iter_entities(self) -> Iterator[StableEntity]:
        """Yield delivery entities in authored section order."""
        for section in DELIVERY_SECTION_NAMES:
            yield from getattr(self, section)


class ChangeDiagnosticCode(StrEnum):
    """Stable loader diagnostic codes."""

    PATH_UNSAFE = "ERR_CHANGE_PATH_UNSAFE"
    FILE_MISSING = "ERR_CHANGE_FILE_MISSING"
    ENCODING = "ERR_CHANGE_ENCODING"
    YAML_PARSE = "ERR_CHANGE_YAML_PARSE"
    SCHEMA_INVALID = "ERR_CHANGE_SCHEMA_INVALID"
    ID_DUPLICATE = "ERR_CHANGE_ID_DUPLICATE"
    REFERENCE_MISSING = "ERR_CHANGE_REFERENCE_MISSING"


class ChangeDiagnostic(_BoundaryModel):
    """Describe one stable change-revision loading failure."""

    code: ChangeDiagnosticCode
    detail: str
    path: str | None = None
    target: str | None = None


class ChangeRevision(_BoundaryModel):
    """Bind validated change authority to its delivery digest and stable identities."""

    source_dir: Path
    change_id: ChangeId
    intent: str
    design: str
    decisions: DecisionsDocument
    graph: DeliveryGraph
    delivery_digest: Digest

    _identity_index: Mapping[str, StableEntity] = PrivateAttr()
    _source_identity: tuple[int, int] = PrivateAttr(default=(-1, -1))

    def model_post_init(self, _context: object) -> None:
        """Build the immutable lookup index for all stable revision identities."""
        index = {decision.id: decision for decision in self.decisions.decisions}
        index.update({entity.id: entity for entity in self.graph.iter_entities()})
        object.__setattr__(self, "_identity_index", MappingProxyType(index))

    @property
    def source_identity(self) -> tuple[int, int]:
        """Return the filesystem identity bound when this revision was loaded."""
        return self._source_identity

    @property
    def accepted_decisions(self) -> tuple[Decision, ...]:
        """Return accepted decisions in stable identity order."""
        accepted = (item for item in self.decisions.decisions if item.status == "accepted")
        return tuple(sorted(accepted, key=lambda item: item.id))

    def resolve(self, stable_id: str) -> StableEntity:
        """Resolve one stable identity or raise ``KeyError``."""
        return self._identity_index[stable_id]

    def read_node_plan(self, node_id: str) -> Mapping[str, object] | None:
        """Read one isolated node plan from this revision's pinned source directory."""
        from owlbear_kanban.node_plan import NodePlanStore  # noqa: PLC0415

        stored = NodePlanStore(self).read(node_id)
        return stored.plan if stored is not None else None


class ChangeLoadResult(_BoundaryModel):
    """Contain either one loaded change revision or its diagnostics."""

    revision: ChangeRevision | None = None
    diagnostics: FrozenSequence[ChangeDiagnostic] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> ChangeLoadResult:
        if (self.revision is None) == (not self.diagnostics):
            msg = "load result must contain either one revision or diagnostics"
            raise ValueError(msg)
        return self


class _LoadFailure(Exception):
    def __init__(self, diagnostic: ChangeDiagnostic) -> None:
        super().__init__(diagnostic.detail)
        self.diagnostic = diagnostic


def _fail(
    code: ChangeDiagnosticCode,
    detail: str,
    *,
    path: Path | None = None,
    target: str | None = None,
) -> Never:
    raise _LoadFailure(
        ChangeDiagnostic(
            code=code,
            detail=detail,
            path=path.name if path is not None else None,
            target=target,
        )
    )


def _validate_change_path(changes_dir: Path, change_id: str) -> Path:
    if (
        "\x00" in change_id
        or not _CHANGE_ID_RE.fullmatch(change_id)
        or PurePosixPath(change_id).is_absolute()
        or PureWindowsPath(change_id).is_absolute()
    ):
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "change ID is not a safe canonical identifier")

    if changes_dir.is_symlink():
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "changes directory must not be a symlink", path=changes_dir)

    change_dir = changes_dir / change_id
    if change_dir.is_symlink():
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "change directory must not be a symlink", path=change_dir)

    try:
        validate_path_containment(changes_dir, change_dir)
    except OSError, ValueError:
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "change directory escapes the changes root", path=change_dir)

    if not change_dir.is_dir():
        _fail(ChangeDiagnosticCode.FILE_MISSING, "change directory is missing", path=change_dir, target=change_id)
    return change_dir


@contextlib.contextmanager
def _change_directory(path: Path) -> Iterator[tuple[int, tuple[int, int]]]:
    try:
        directory_fd = os.open(path, _DIRECTORY_OPEN_FLAGS)
    except FileNotFoundError:
        _fail(ChangeDiagnosticCode.FILE_MISSING, "change directory is missing", path=path)
    except OSError:
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "change directory could not be opened safely", path=path)
    source_stat = os.fstat(directory_fd)
    try:
        yield directory_fd, (source_stat.st_dev, source_stat.st_ino)
    finally:
        os.close(directory_fd)


def _read_text(directory_fd: int, name: str, *, markdown: bool) -> str:
    path = Path(name)
    try:
        file_fd = os.open(name, _FILE_OPEN_FLAGS, dir_fd=directory_fd)
    except FileNotFoundError:
        _fail(ChangeDiagnosticCode.FILE_MISSING, "required authority file is missing", path=path, target=name)
    except OSError:
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "authority file could not be opened safely", path=path, target=name)
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            _fail(ChangeDiagnosticCode.PATH_UNSAFE, "authority path must be a regular file", path=path, target=name)
        with os.fdopen(file_fd, "rb") as handle:
            file_fd = -1
            raw = handle.read()
    except OSError:
        _fail(ChangeDiagnosticCode.FILE_MISSING, "authority file could not be read", path=path, target=name)
    finally:
        if file_fd >= 0:
            os.close(file_fd)
    if markdown and raw.startswith(b"\xef\xbb\xbf"):
        _fail(ChangeDiagnosticCode.ENCODING, "Markdown authority must not contain a byte-order mark", path=path)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        _fail(ChangeDiagnosticCode.ENCODING, "authority file is not strict UTF-8", path=path, target=path.name)


def _to_plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    return value


def _read_yaml(directory_fd: int, name: str) -> object:
    text = _read_text(directory_fd, name, markdown=False)
    try:
        return _to_plain(make_yaml().load(text))
    except YAMLError:
        _fail(ChangeDiagnosticCode.YAML_PARSE, "authority YAML could not be parsed", path=Path(name), target=name)


@contextlib.contextmanager
def _authority_directory(directory_fd: int, name: str) -> Iterator[int]:
    path = Path(name)
    try:
        child_fd = os.open(name, _DIRECTORY_OPEN_FLAGS, dir_fd=directory_fd)
    except FileNotFoundError:
        _fail(ChangeDiagnosticCode.FILE_MISSING, "required authority directory is missing", path=path, target=name)
    except OSError:
        _fail(
            ChangeDiagnosticCode.PATH_UNSAFE, "authority directory could not be opened safely", path=path, target=name
        )
    try:
        yield child_fd
    finally:
        os.close(child_fd)


def _schema_detail(document: str, exc: PydanticValidationError) -> str:
    error = exc.errors(include_input=False, include_url=False)[0]
    location = ".".join(str(part) for part in error["loc"])
    return f"{document} schema rejected {location or '<root>'}: {error['type']}"


def _validate_identities(decisions: DecisionsDocument, graph: DeliveryGraph) -> None:
    records: list[tuple[str, StableEntity]] = [("decisions", item) for item in decisions.decisions]
    records.extend((section, item) for section in DELIVERY_SECTION_NAMES for item in getattr(graph, section))
    identities: set[str] = set()
    for section, item in records:
        prefix = _SECTION_PREFIXES[section]
        if not item.id.startswith(f"{prefix}-"):
            _fail(
                ChangeDiagnosticCode.SCHEMA_INVALID,
                f"{item.id} is not a {prefix} identity",
                target=item.id,
            )
        if item.id in identities:
            _fail(ChangeDiagnosticCode.ID_DUPLICATE, "stable identity is duplicated", target=item.id)
        identities.add(item.id)

    for section in DELIVERY_SECTION_NAMES:
        for item in getattr(graph, section):
            for reference in _iter_references(item.model_dump(mode="json", by_alias=True, exclude_unset=True)):
                if reference not in identities:
                    _fail(
                        ChangeDiagnosticCode.REFERENCE_MISSING,
                        f"{item.id} references an undeclared identity",
                        target=reference,
                    )


def _iter_references(value: object, *, field: str | None = None) -> Iterator[str]:
    reference_fields = {
        "absence_proof",
        "authority",
        "consumers",
        "consumes",
        "deletion_owner",
        "dependencies",
        "migration",
        "modules",
        "owner",
        "owns",
        "producer",
        "produces",
        "proof",
        "risks",
        "supporting_nodes",
        "supports",
        "workflows",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_references(item, field=str(key))
    elif isinstance(value, list):
        for item in value:
            yield from _iter_references(item, field=field)
    elif field in reference_fields and isinstance(value, str) and _STABLE_ID_RE.fullmatch(value):
        yield value


def _normalize_markdown(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def compute_delivery_digest(
    intent: str,
    design: str,
    decisions: DecisionsDocument,
    graph: DeliveryGraph,
) -> str:
    """Return the canonical ``delivery-v1`` SHA-256 digest."""
    accepted = sorted(
        (
            item.model_dump(mode="json", by_alias=True, exclude_unset=True)
            for item in decisions.decisions
            if item.status == "accepted"
        ),
        key=lambda item: item["id"],
    )
    delivery = {
        section: [item.model_dump(mode="json", by_alias=True, exclude_unset=True) for item in getattr(graph, section)]
        for section in DELIVERY_SECTION_NAMES
    }
    envelope = {
        "intent": _normalize_markdown(intent),
        "design": _normalize_markdown(design),
        "decisions": accepted,
        "delivery": delivery,
    }
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def _build_revision(  # noqa: PLR0913
    *,
    change_dir: Path,
    change_id: str,
    source_identity: tuple[int, int],
    intent: str,
    design: str,
    decisions: DecisionsDocument,
    graph: DeliveryGraph,
) -> ChangeRevision:
    if decisions.change_id != change_id or graph.change_id != change_id:
        _fail(
            ChangeDiagnosticCode.SCHEMA_INVALID,
            "authority documents do not name the requested change",
            target=change_id,
        )
    _validate_identities(decisions, graph)
    revision = ChangeRevision(
        source_dir=change_dir.absolute(),
        change_id=change_id,
        intent=intent,
        design=design,
        decisions=decisions,
        graph=graph,
        delivery_digest=compute_delivery_digest(intent, design, decisions, graph),
    )
    object.__setattr__(revision, "_source_identity", source_identity)
    try:
        RuntimeTransaction.recover_all(revision.source_dir)
    except TransactionPathError:
        _fail(ChangeDiagnosticCode.PATH_UNSAFE, "pending transaction contains an unsafe participant path")
    except TransactionManifestError:
        _fail(ChangeDiagnosticCode.SCHEMA_INVALID, "pending transaction manifest is invalid")
    except TransactionConflictError:
        _fail(ChangeDiagnosticCode.SCHEMA_INVALID, "pending transaction conflicts with immutable bytes")
    return revision


def _validate_document(model: type[_BoundaryModel], value: object, path: str) -> _BoundaryModel:
    try:
        return model.model_validate(value)
    except PydanticValidationError as exc:
        _fail(
            ChangeDiagnosticCode.SCHEMA_INVALID,
            _schema_detail(path, exc),
            path=Path(path),
            target=path,
        )


def load_modular_change(changes_dir: Path, change_id: str) -> ChangeLoadResult:
    """Load one contained modular native change package."""
    try:
        change_dir = _validate_change_path(changes_dir, change_id)
        with _change_directory(change_dir) as (directory_fd, source_identity):
            try:
                os.stat("graph.yaml", dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            except OSError:
                _fail(ChangeDiagnosticCode.PATH_UNSAFE, "legacy graph authority could not be inspected")
            else:
                _fail(
                    ChangeDiagnosticCode.SCHEMA_INVALID,
                    "legacy graph.yaml authority is not permitted",
                    path=Path("graph.yaml"),
                    target="graph.yaml",
                )
            intent = _read_text(directory_fd, "intent.md", markdown=True)
            design = _read_text(directory_fd, "design.md", markdown=True)
            decisions = _validate_document(
                DecisionsDocument,
                _read_yaml(directory_fd, "decisions.yaml"),
                "decisions.yaml",
            )
            with _authority_directory(directory_fd, "delivery") as delivery_fd:
                obligations = _validate_document(
                    DeliveryObligationsDocument,
                    _read_yaml(delivery_fd, "obligations.yaml"),
                    "delivery/obligations.yaml",
                )
                contracts = _validate_document(
                    DeliveryContractsDocument,
                    _read_yaml(delivery_fd, "contracts.yaml"),
                    "delivery/contracts.yaml",
                )
                nodes = _validate_document(
                    DeliveryNodesDocument,
                    _read_yaml(delivery_fd, "nodes.yaml"),
                    "delivery/nodes.yaml",
                )
            assert isinstance(decisions, DecisionsDocument)
            assert isinstance(obligations, DeliveryObligationsDocument)
            assert isinstance(contracts, DeliveryContractsDocument)
            assert isinstance(nodes, DeliveryNodesDocument)
            document_ids = {decisions.change_id, obligations.change_id, contracts.change_id, nodes.change_id}
            if document_ids != {change_id}:
                _fail(
                    ChangeDiagnosticCode.SCHEMA_INVALID,
                    "authority documents do not name the requested change",
                    target=change_id,
                )
            graph = DeliveryGraph(
                schema_version=nodes.schema_version,
                change_id=nodes.change_id,
                state=nodes.state,
                authority=nodes.authority,
                admission=nodes.admission,
                requirements=obligations.requirements,
                negative_requirements=obligations.negative_requirements,
                preserved_behaviors=obligations.preserved_behaviors,
                workflows=obligations.workflows,
                modules=contracts.modules,
                interfaces=contracts.interfaces,
                migrations=contracts.migrations,
                risks=contracts.risks,
                proofs=contracts.proofs,
                nodes=nodes.nodes,
            )
        revision = _build_revision(
            change_dir=change_dir,
            change_id=change_id,
            source_identity=source_identity,
            intent=intent,
            design=design,
            decisions=decisions,
            graph=graph,
        )
    except _LoadFailure as exc:
        return ChangeLoadResult(diagnostics=(exc.diagnostic,))
    return ChangeLoadResult(revision=revision)


def load_change(changes_dir: Path, change_id: str) -> ChangeLoadResult:
    """Load one contained modular native change package."""
    return load_modular_change(changes_dir, change_id)


__all__ = [
    "ChangeDiagnostic",
    "ChangeDiagnosticCode",
    "ChangeLoadResult",
    "ChangeRevision",
    "DecisionsDocument",
    "DeliveryContractsDocument",
    "DeliveryGraph",
    "DeliveryNodesDocument",
    "DeliveryObligationsDocument",
    "compute_delivery_digest",
    "load_change",
    "load_modular_change",
]
