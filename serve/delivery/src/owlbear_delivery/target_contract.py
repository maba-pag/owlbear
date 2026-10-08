"""Deterministic schema-v3 Delivery Contract compilation; schema-v2 contracts stay readable."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any, Literal

from markdown_it import MarkdownIt
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    model_serializer,
    model_validator,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_delivery.acceptance_criteria import is_near_miss_acceptance_item, parse_acceptance_item

ChangeId = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
CommitmentId = Annotated[str, StringConstraints(strict=True, pattern=r"^COM-[0-9]{3}$")]
DecisionId = Annotated[str, StringConstraints(strict=True, pattern=r"^DEC-[0-9]{3}$")]
OutcomeId = Annotated[str, StringConstraints(strict=True, pattern=r"^OUT-[0-9]{3}$")]
ScopeId = Annotated[str, StringConstraints(strict=True, pattern=r"^SCOPE-[0-9]{3}$")]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
SourceName = Literal["intent.md", "design.md"]

_TARGET_FENCE = "yaml target-contract"
_COMMITMENT_KEYS = ("kind", "id", "class", "decisions", "statement")
_DECISION_KEYS = ("kind", "id", "origin", "basis", "statement")
_DECISION_OPTIONAL_KEYS = ("supersedes",)
_OUTCOME_KEYS = ("kind", "id", "title", "promise", "acceptance", "commitments", "dependencies")
_COMMITMENT_ID = re.compile(r"^COM-[0-9]{3}$")
_DECISION_ID = re.compile(r"^DEC-[0-9]{3}$")
_OUTCOME_ID = re.compile(r"^OUT-[0-9]{3}$")
_LEGACY_SCHEMA_VERSION = 2
_SCHEMA_VERSION = 3


class DeliveryCommitmentClass(StrEnum):
    """Authored strength of one commitment."""

    DEALBREAKER = "dealbreaker"
    PROTECTED_REQUEST = "protected-request"
    IMPORTANT_REVIEWED = "important-reviewed"
    AGREED_PATH = "agreed-path"
    IMPLEMENTATION_DISCRETION = "implementation-discretion"


class DeliveryDecisionOrigin(StrEnum):
    """Who made one recorded decision."""

    DECIDED = "decided"
    APPROVED = "approved"
    AUTONOMOUS = "autonomous"


class DeliveryCompilationDiagnosticCode(StrEnum):
    """Stable compiler failure categories independent of parser wording."""

    CHANGE_ID_INVALID = "change-id-invalid"
    SOURCE_ENCODING_INVALID = "source-encoding-invalid"
    TITLE_MISSING = "title-missing"
    TITLE_DUPLICATE = "title-duplicate"
    YAML_INVALID = "yaml-invalid"
    DEFINITION_NOT_MAPPING = "definition-not-mapping"
    KIND_MISSING = "kind-missing"
    KIND_UNKNOWN = "kind-unknown"
    KEY_UNKNOWN = "key-unknown"
    KEY_MISSING = "key-missing"
    VALUE_INVALID = "value-invalid"
    IDENTITY_INVALID = "identity-invalid"
    IDENTITY_DUPLICATE = "identity-duplicate"
    DEFINITION_MISSING = "definition-missing"
    REFERENCE_UNRESOLVED = "reference-unresolved"
    DEPENDENCY_CYCLE = "dependency-cycle"
    ACTIVE_OUTCOME_MISSING = "active-outcome-missing"
    SCOPE_IDENTITY_COLLISION = "scope-identity-collision"
    SCOPE_COVERAGE_INVALID = "scope-coverage-invalid"
    ACCEPTANCE_IDENTITY_MIXED = "acceptance-identity-mixed"
    ACCEPTANCE_IDENTITY_DUPLICATE = "acceptance-identity-duplicate"
    ACCEPTANCE_IDENTITY_INVALID = "acceptance-identity-invalid"
    ACCEPTANCE_IDENTITY_REQUIRED = "acceptance-identity-required"
    DECISION_INACTIVE = "decision-inactive"
    DECISION_ORIGIN_REQUIRED = "decision-origin-required"
    SUPERSESSION_INVALID = "supersession-invalid"
    DECISION_HISTORY_CHANGED = "decision-history-changed"
    DECISION_REQUEST_INVALID = "decision-request-invalid"


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryDecision(_ContractModel):
    """One recorded decision with its origin; superseded decisions remain as history."""

    decision_id: DecisionId
    origin: DeliveryDecisionOrigin
    basis: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    supersedes: tuple[Annotated[str, StringConstraints(strict=True, min_length=1)], ...] = ()


class DeliveryCommitment(_ContractModel):
    """One immutable authored commitment: schema v2 names provenance, schema v3 its decisions."""

    commitment_id: CommitmentId
    commitment_class: DeliveryCommitmentClass
    provenance: str | None = Field(default=None, min_length=1)
    decision_ids: tuple[DecisionId, ...] = ()
    statement: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_basis(self) -> DeliveryCommitment:
        if (self.provenance is None) == (not self.decision_ids):
            message = "a commitment names either provenance (schema 2) or decisions (schema 3)"
            raise ValueError(message)
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload: dict[str, Any] = handler(self)
        if self.provenance is None:
            payload.pop("provenance", None)
        if not self.decision_ids:
            payload.pop("decision_ids", None)
        return payload


class DeliveryOutcome(_ContractModel):
    """One active user-facing result in a contract."""

    outcome_id: OutcomeId
    title: str = Field(min_length=1)
    promise: str = Field(min_length=1)
    acceptance: tuple[str, ...] = Field(min_length=1)
    commitment_ids: tuple[CommitmentId, ...]
    dependency_ids: tuple[OutcomeId, ...]


class DeliveryPlanScope(_ContractModel):
    """The deterministic planning scope owned by one outcome."""

    scope_id: ScopeId
    outcome_id: OutcomeId


class DeliverySourceBinding(_ContractModel):
    """Whole-document binding for one authored Specification source."""

    source_name: SourceName
    sha256: Digest


class DeliveryContract(_ContractModel):
    """Canonical semantic authority derived from authored sources; schema 2 is read-only legacy."""

    schema_version: Literal[2, 3] = 2
    change_id: ChangeId
    title: str = Field(min_length=1)
    decisions: tuple[DeliveryDecision, ...] = ()
    commitments: tuple[DeliveryCommitment, ...]
    outcomes: tuple[DeliveryOutcome, ...] = Field(min_length=1)
    plan_scopes: tuple[DeliveryPlanScope, ...] = Field(min_length=1)
    source_bindings: tuple[DeliverySourceBinding, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _validate_schema(self) -> DeliveryContract:
        legacy = self.schema_version == _LEGACY_SCHEMA_VERSION
        if legacy and (self.decisions or any(item.provenance is None for item in self.commitments)):
            message = "a schema-2 contract has provenance commitments and no decisions"
            raise ValueError(message)
        if not legacy and (not self.decisions or any(not item.decision_ids for item in self.commitments)):
            message = "a schema-3 contract records decisions and links every commitment to them"
            raise ValueError(message)
        return self

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        payload: dict[str, Any] = handler(self)
        if not self.decisions:
            payload.pop("decisions", None)
        return payload

    def active_decisions(self) -> tuple[DeliveryDecision, ...]:
        """Return decisions no other decision supersedes."""
        superseded = {identity for item in self.decisions for identity in item.supersedes}
        return tuple(item for item in self.decisions if item.decision_id not in superseded)

    def superseded_request_ids(self) -> frozenset[str]:
        """Return answered request identities that a recorded decision supersedes."""
        return frozenset(
            identity for item in self.decisions for identity in item.supersedes if not is_decision_id(identity)
        )


def parse_delivery_contract(content: bytes) -> DeliveryContract:
    """Strictly parse one stored contract of either readable schema version."""
    return DeliveryContract.model_validate_json(content, strict=True)


def is_decision_id(identity: str) -> bool:
    """Return whether a supersession target names a decision rather than an answered request."""
    return _DECISION_ID.fullmatch(identity) is not None


class DeliveryDecisionDelta(_ContractModel):
    """How a candidate's decisions differ from the admitted contract, for the approval summary."""

    converted_from_schema_2: bool = False
    added: tuple[DeliveryDecision, ...] = ()
    superseded: tuple[DeliveryDecision, ...] = ()
    superseded_request_ids: tuple[str, ...] = ()
    # Admitted decisions the candidate edits or drops; revision activation refuses them.
    changed_admitted_ids: tuple[str, ...] = ()


def decision_delta(admitted: DeliveryContract, candidate: DeliveryContract) -> DeliveryDecisionDelta:
    """Return the decisions a candidate adds, newly supersedes, or illegally changes."""
    previous = {item.decision_id: item for item in admitted.decisions}
    current = {item.decision_id: item for item in candidate.decisions}
    previously_superseded = {identity for item in admitted.decisions for identity in item.supersedes}
    newly_superseded = {
        identity for item in candidate.decisions for identity in item.supersedes
    } - previously_superseded
    return DeliveryDecisionDelta(
        converted_from_schema_2=admitted.schema_version == _LEGACY_SCHEMA_VERSION,
        added=tuple(item for item in candidate.decisions if item.decision_id not in previous),
        superseded=tuple(item for item in candidate.decisions if item.decision_id in newly_superseded),
        superseded_request_ids=tuple(sorted(identity for identity in newly_superseded if not is_decision_id(identity))),
        changed_admitted_ids=tuple(
            sorted(identity for identity, item in previous.items() if current.get(identity) != item)
        ),
    )


class DeliveryCompilationDiagnostic(_ContractModel):
    """One stable source-compilation failure."""

    code: DeliveryCompilationDiagnosticCode
    source_name: SourceName | None = None
    subject: str | None = None
    detail: str = Field(min_length=1)


class DeliveryCompilationResult(_ContractModel):
    """Either one complete contract representation or ordered diagnostics."""

    contract: DeliveryContract | None = None
    canonical_bytes: bytes | None = None
    digest: Digest | None = None
    diagnostics: tuple[DeliveryCompilationDiagnostic, ...] = ()
    # Set for a revision of an admitted Change.
    decision_delta: DeliveryDecisionDelta | None = None

    @model_validator(mode="after")
    def _validate_exclusive_result(self) -> DeliveryCompilationResult:
        complete = self.contract is not None and self.canonical_bytes is not None and self.digest is not None
        empty = self.contract is None and self.canonical_bytes is None and self.digest is None
        if complete == bool(self.diagnostics) or not (complete or empty):
            message = "compilation result must contain exactly one complete success or nonempty diagnostics"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class _DefinitionContext:
    source_name: SourceName
    subject: str | None
    diagnostics: list[DeliveryCompilationDiagnostic]


def compile_delivery_contract(
    change_id: str,
    intent_bytes: bytes,
    design_bytes: bytes,
) -> DeliveryCompilationResult:
    """Compile exact authored Specification bytes into canonical schema-v3 authority."""
    diagnostics: list[DeliveryCompilationDiagnostic] = []
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change_id) is None:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.CHANGE_ID_INVALID,
                "change identity must be lowercase hyphen-separated ASCII",
                subject=change_id,
            )
        )

    intent_text = _decode_source("intent.md", intent_bytes, diagnostics)
    design_text = _decode_source("design.md", design_bytes, diagnostics)
    if intent_text is None or design_text is None:
        return DeliveryCompilationResult(diagnostics=tuple(diagnostics))

    title, intent_blocks = _parse_markdown("intent.md", intent_text, diagnostics, require_title=True)
    _, design_blocks = _parse_markdown("design.md", design_text, diagnostics, require_title=False)
    definitions = _parse_definitions((*intent_blocks, *design_blocks), diagnostics)
    _validate_definitions(definitions.commitments, definitions.outcomes, definitions.outcome_sources, diagnostics)
    _validate_decisions(definitions, diagnostics)
    scopes = _derive_scopes(definitions.outcomes, diagnostics)

    if diagnostics:
        return DeliveryCompilationResult(diagnostics=tuple(diagnostics))

    contract = DeliveryContract(
        schema_version=_SCHEMA_VERSION,
        change_id=change_id,
        title=title,
        decisions=tuple(definitions.decisions),
        commitments=tuple(definitions.commitments),
        outcomes=tuple(definitions.outcomes),
        plan_scopes=scopes,
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=_digest(intent_bytes)),
            DeliverySourceBinding(source_name="design.md", sha256=_digest(design_bytes)),
        ),
    )
    canonical_bytes = contract_canonical_bytes(contract)
    return DeliveryCompilationResult(
        contract=contract,
        canonical_bytes=canonical_bytes,
        digest=_digest(canonical_bytes),
    )


def _decode_source(
    source_name: SourceName,
    content: bytes,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> str | None:
    try:
        return content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.SOURCE_ENCODING_INVALID,
                "source must be strict UTF-8",
                source_name,
            )
        )
        return None


def _parse_markdown(
    source_name: SourceName,
    text: str,
    diagnostics: list[DeliveryCompilationDiagnostic],
    *,
    require_title: bool,
) -> tuple[str, tuple[tuple[SourceName, str], ...]]:
    tokens = MarkdownIt("commonmark").parse(text)
    titles = [
        tokens[index + 1].content
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag == "h1"
    ]
    if require_title and not titles:
        diagnostics.append(
            _diagnostic(DeliveryCompilationDiagnosticCode.TITLE_MISSING, "intent must contain one H1", source_name)
        )
    if require_title and len(titles) > 1:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.TITLE_DUPLICATE, "intent must contain exactly one H1", source_name
            )
        )
    blocks = tuple(
        (source_name, token.content)
        for token in tokens
        if token.type == "fence" and token.info.strip() == _TARGET_FENCE
    )
    return (titles[0] if titles else ""), blocks


@dataclass
class _Definitions:
    decisions: list[DeliveryDecision]
    commitments: list[DeliveryCommitment]
    outcomes: list[DeliveryOutcome]
    decision_sources: dict[str, SourceName]
    commitment_sources: dict[str, SourceName]
    outcome_sources: dict[str, SourceName]


def _parse_definitions(
    blocks: tuple[tuple[SourceName, str], ...],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> _Definitions:
    definitions = _Definitions([], [], [], {}, {}, {})
    decision_ids: set[str] = set()
    commitment_ids: set[str] = set()
    outcome_ids: set[str] = set()
    for source_name, content in blocks:
        payload = _load_yaml(source_name, content, diagnostics)
        if payload is None:
            continue
        kind = payload.get("kind")
        subject = payload.get("id") if type(payload.get("id")) is str else None
        if kind is None:
            diagnostics.append(
                _diagnostic(
                    DeliveryCompilationDiagnosticCode.KIND_MISSING, "definition kind is required", source_name, subject
                )
            )
        elif type(kind) is not str or kind not in {"decision", "commitment", "outcome"}:
            diagnostics.append(
                _diagnostic(
                    DeliveryCompilationDiagnosticCode.KIND_UNKNOWN,
                    "definition kind is not supported",
                    source_name,
                    subject,
                )
            )
        elif kind == "decision":
            decision = _parse_decision(payload, source_name, diagnostics)
            if decision is not None and _accept_identity(decision.decision_id, decision_ids, source_name, diagnostics):
                definitions.decisions.append(decision)
                definitions.decision_sources[decision.decision_id] = source_name
        elif kind == "commitment":
            commitment = _parse_commitment(payload, source_name, diagnostics)
            if commitment is not None and _accept_identity(
                commitment.commitment_id, commitment_ids, source_name, diagnostics
            ):
                definitions.commitments.append(commitment)
                definitions.commitment_sources[commitment.commitment_id] = source_name
        else:
            outcome = _parse_outcome(payload, source_name, diagnostics)
            if outcome is not None and _accept_identity(outcome.outcome_id, outcome_ids, source_name, diagnostics):
                definitions.outcomes.append(outcome)
                definitions.outcome_sources[outcome.outcome_id] = source_name
    return definitions


def _load_yaml(
    source_name: SourceName,
    content: str,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> dict[object, object] | None:
    parser = YAML(typ="safe", pure=True)
    parser.allow_duplicate_keys = False
    try:
        payload = parser.load(content)
    except YAMLError:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.YAML_INVALID, "target contract block is not valid YAML", source_name
            )
        )
        return None
    if not isinstance(payload, dict):
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.DEFINITION_NOT_MAPPING,
                "target contract block must be a mapping",
                source_name,
            )
        )
        return None
    if not all(type(key) is str for key in payload):
        diagnostics.append(
            _diagnostic(DeliveryCompilationDiagnosticCode.KEY_UNKNOWN, "definition keys must be strings", source_name)
        )
        return None
    return payload


def _parse_decision(
    payload: dict[object, object],
    source_name: SourceName,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> DeliveryDecision | None:
    subject = payload.get("id") if type(payload.get("id")) is str else None
    context = _DefinitionContext(source_name, subject, diagnostics)
    if not _validate_keys(payload, _DECISION_KEYS, source_name, subject, diagnostics, optional=_DECISION_OPTIONAL_KEYS):
        return None
    decision_id = _identity(payload["id"], _DECISION_ID, "decision id", context)
    origin = payload["origin"]
    basis = _text(payload["basis"], "basis", context)
    statement = _text(payload["statement"], "statement", context)
    supersedes = _text_sequence(payload.get("supersedes", []), "supersedes", context)
    if type(origin) is not str or origin not in DeliveryDecisionOrigin:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.VALUE_INVALID, "decision origin is invalid", source_name, subject
            )
        )
        origin = None
    if decision_id is None or origin is None or basis is None or statement is None or supersedes is None:
        return None
    return DeliveryDecision(
        decision_id=decision_id,
        origin=DeliveryDecisionOrigin(origin),
        basis=basis,
        statement=statement,
        supersedes=supersedes,
    )


def _parse_commitment(
    payload: dict[object, object],
    source_name: SourceName,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> DeliveryCommitment | None:
    subject = payload.get("id") if type(payload.get("id")) is str else None
    context = _DefinitionContext(source_name, subject, diagnostics)
    if not _validate_keys(payload, _COMMITMENT_KEYS, source_name, subject, diagnostics):
        return None
    commitment_id = _identity(payload["id"], _COMMITMENT_ID, "commitment id", context)
    commitment_class = payload["class"]
    decision_ids = _identity_sequence(payload["decisions"], _DECISION_ID, "decisions", context)
    statement = _text(payload["statement"], "statement", context)
    if type(commitment_class) is not str or commitment_class not in DeliveryCommitmentClass:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.VALUE_INVALID, "commitment class is invalid", source_name, subject
            )
        )
        commitment_class = None
    if decision_ids == ():
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.VALUE_INVALID,
                "a commitment names at least one decision",
                source_name,
                subject,
            )
        )
        decision_ids = None
    if commitment_id is None or commitment_class is None or decision_ids is None or statement is None:
        return None
    return DeliveryCommitment(
        commitment_id=commitment_id,
        commitment_class=DeliveryCommitmentClass(commitment_class),
        decision_ids=decision_ids,
        statement=statement,
    )


def _parse_outcome(
    payload: dict[object, object],
    source_name: SourceName,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> DeliveryOutcome | None:
    subject = payload.get("id") if type(payload.get("id")) is str else None
    context = _DefinitionContext(source_name, subject, diagnostics)
    if not _validate_keys(payload, _OUTCOME_KEYS, source_name, subject, diagnostics):
        return None
    outcome_id = _identity(payload["id"], _OUTCOME_ID, "outcome id", context)
    title = _text(payload["title"], "outcome title", context)
    promise = _text(payload["promise"], "outcome promise", context)
    acceptance = _text_sequence(payload["acceptance"], "acceptance", context, require_items=True)
    commitment_ids = _identity_sequence(payload["commitments"], _COMMITMENT_ID, "commitments", context)
    dependency_ids = _identity_sequence(payload["dependencies"], _OUTCOME_ID, "dependencies", context)
    if None in (outcome_id, title, promise, acceptance, commitment_ids, dependency_ids):
        return None
    return DeliveryOutcome(
        outcome_id=outcome_id,
        title=title,
        promise=promise,
        acceptance=acceptance,
        commitment_ids=commitment_ids,
        dependency_ids=dependency_ids,
    )


def _validate_keys(  # noqa: PLR0913 - optional keys extend the shared key contract.
    payload: dict[object, object],
    allowed: tuple[str, ...],
    source_name: SourceName,
    subject: str | None,
    diagnostics: list[DeliveryCompilationDiagnostic],
    *,
    optional: tuple[str, ...] = (),
) -> bool:
    valid = True
    unknown = sorted(str(key) for key in payload if key not in allowed and key not in optional)
    for key in unknown:
        diagnostics.append(
            _diagnostic(DeliveryCompilationDiagnosticCode.KEY_UNKNOWN, f"unknown key: {key}", source_name, subject)
        )
        valid = False
    for key in allowed:
        if key not in payload:
            diagnostics.append(
                _diagnostic(DeliveryCompilationDiagnosticCode.KEY_MISSING, f"missing key: {key}", source_name, subject)
            )
            valid = False
    return valid


def _identity(
    value: object,
    pattern: re.Pattern[str],
    label: str,
    context: _DefinitionContext,
) -> str | None:
    if type(value) is str and pattern.fullmatch(value):
        return value
    context.diagnostics.append(
        _diagnostic(
            DeliveryCompilationDiagnosticCode.IDENTITY_INVALID,
            f"{label} is invalid",
            context.source_name,
            context.subject,
        )
    )
    return None


def _text(
    value: object,
    label: str,
    context: _DefinitionContext,
) -> str | None:
    if type(value) is str and value:
        return value
    context.diagnostics.append(
        _diagnostic(
            DeliveryCompilationDiagnosticCode.VALUE_INVALID,
            f"{label} must be a nonempty string",
            context.source_name,
            context.subject,
        )
    )
    return None


def _text_sequence(
    value: object,
    label: str,
    context: _DefinitionContext,
    *,
    require_items: bool = False,
) -> tuple[str, ...] | None:
    if isinstance(value, list) and (value or not require_items) and all(type(item) is str and item for item in value):
        return tuple(value)
    context.diagnostics.append(
        _diagnostic(
            DeliveryCompilationDiagnosticCode.VALUE_INVALID,
            f"{label} must be a string sequence",
            context.source_name,
            context.subject,
        )
    )
    return None


def _identity_sequence(
    value: object,
    pattern: re.Pattern[str],
    label: str,
    context: _DefinitionContext,
) -> tuple[str, ...] | None:
    values = _text_sequence(value, label, context)
    if values is None:
        return None
    if all(pattern.fullmatch(item) for item in values):
        return values
    context.diagnostics.append(
        _diagnostic(
            DeliveryCompilationDiagnosticCode.IDENTITY_INVALID,
            f"{label} contain an invalid identity",
            context.source_name,
            context.subject,
        )
    )
    return None


def _accept_identity(
    identity: str,
    seen: set[str],
    source_name: SourceName,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> bool:
    if identity in seen:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.IDENTITY_DUPLICATE,
                "definition identity is duplicated",
                source_name,
                identity,
            )
        )
        return False
    seen.add(identity)
    return True


def _validate_definitions(
    commitments: list[DeliveryCommitment],
    outcomes: list[DeliveryOutcome],
    outcome_sources: dict[str, SourceName],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> None:
    if not commitments:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.DEFINITION_MISSING,
                "at least one commitment is required",
                subject="commitment",
            )
        )
    if not outcomes:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.ACTIVE_OUTCOME_MISSING,
                "at least one active outcome is required",
                subject="outcome",
            )
        )
        return
    _validate_acceptance_identities(outcomes, outcome_sources, diagnostics)
    commitment_ids = {item.commitment_id for item in commitments}
    outcome_ids = {item.outcome_id for item in outcomes}
    for outcome in outcomes:
        source_name = outcome_sources[outcome.outcome_id]
        diagnostics.extend(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
                "commitment reference is unresolved",
                source_name,
                reference,
            )
            for reference in outcome.commitment_ids
            if reference not in commitment_ids
        )
        diagnostics.extend(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
                "outcome dependency is unresolved",
                source_name,
                reference,
            )
            for reference in outcome.dependency_ids
            if reference not in outcome_ids
        )
    _validate_dependency_dag(outcomes, outcome_ids, outcome_sources, diagnostics)


def _validate_decisions(definitions: _Definitions, diagnostics: list[DeliveryCompilationDiagnostic]) -> None:
    decisions = {item.decision_id: item for item in definitions.decisions}
    if not decisions:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.DEFINITION_MISSING,
                "at least one decision is required",
                subject="decision",
            )
        )
    successors: dict[str, str] = {}
    for decision in definitions.decisions:
        source_name = definitions.decision_sources[decision.decision_id]
        for message in _supersession_findings(decision, decisions, successors):
            code, detail = message
            diagnostics.append(_diagnostic(code, detail, source_name, decision.decision_id))
    cycle = _supersession_cycle(decisions, successors)
    if cycle is not None:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID,
                "decision supersession must not form a cycle",
                definitions.decision_sources[cycle],
                cycle,
            )
        )
    for commitment in definitions.commitments:
        source_name = definitions.commitment_sources[commitment.commitment_id]
        for reference in commitment.decision_ids:
            if reference not in decisions:
                code, detail = (
                    DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
                    "decision reference is unresolved",
                )
            elif reference in successors:
                code, detail = (
                    DeliveryCompilationDiagnosticCode.DECISION_INACTIVE,
                    "commitment names a superseded decision",
                )
            else:
                continue
            diagnostics.append(_diagnostic(code, detail, source_name, reference))


def _supersession_cycle(decisions: dict[str, DeliveryDecision], successors: dict[str, str]) -> str | None:
    """Return one decision that its own supersession chain reaches again, if any."""
    for identity in decisions:
        seen = {identity}
        current = identity
        while (current := successors.get(current, "")) and current not in seen:
            seen.add(current)
        if current == identity:
            return identity
    return None


def _supersession_findings(
    decision: DeliveryDecision,
    decisions: dict[str, DeliveryDecision],
    successors: dict[str, str],
) -> list[tuple[DeliveryCompilationDiagnosticCode, str]]:
    """Record ``decision``'s supersession edges and return each rule it breaks."""
    findings: list[tuple[DeliveryCompilationDiagnosticCode, str]] = []
    decided = decision.origin is DeliveryDecisionOrigin.DECIDED
    for target in decision.supersedes:
        if target == decision.decision_id:
            findings.append(
                (DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID, "a decision cannot supersede itself")
            )
            continue
        if target in successors:
            findings.append(
                (DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID, "a decision is superseded at most once")
            )
            continue
        if not is_decision_id(target):
            successors[target] = decision.decision_id
            if not decided:
                findings.append(
                    (
                        DeliveryCompilationDiagnosticCode.DECISION_ORIGIN_REQUIRED,
                        "only a decided decision supersedes an answered request",
                    )
                )
            continue
        previous = decisions.get(target)
        if previous is None:
            findings.append(
                (DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED, "superseded decision is unresolved")
            )
            continue
        successors[target] = decision.decision_id
        if not decided and (previous.origin is DeliveryDecisionOrigin.DECIDED or previous.supersedes):
            findings.append(
                (
                    DeliveryCompilationDiagnosticCode.DECISION_ORIGIN_REQUIRED,
                    "superseding a decided decision, or one that already superseded another, needs the user's decision",
                )
            )
    return findings


def _validate_acceptance_identities(
    outcomes: list[DeliveryOutcome],
    outcome_sources: dict[str, SourceName],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> None:
    seen: set[str] = set()
    authored = legacy = 0
    for outcome in outcomes:
        source_name = outcome_sources[outcome.outcome_id]
        for item in outcome.acceptance:
            if is_near_miss_acceptance_item(item):
                diagnostics.append(
                    _diagnostic(
                        DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_INVALID,
                        "acceptance item starts like an AC-NNN identity but is not of the form 'AC-NNN: <statement>'",
                        source_name,
                        outcome.outcome_id,
                    )
                )
                continue
            identity = parse_acceptance_item(item)[0]
            if identity is None:
                legacy += 1
                continue
            authored += 1
            if identity in seen:
                diagnostics.append(
                    _diagnostic(
                        DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_DUPLICATE,
                        "acceptance identity is duplicated within the Change",
                        source_name,
                        identity,
                    )
                )
            seen.add(identity)
    if authored and legacy:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_MIXED,
                "every acceptance item must declare an AC-NNN identity, or none may",
                subject="acceptance",
            )
        )


def _validate_dependency_dag(
    outcomes: list[DeliveryOutcome],
    outcome_ids: set[str],
    outcome_sources: dict[str, SourceName],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> None:
    remaining = {
        item.outcome_id: {dependency for dependency in item.dependency_ids if dependency in outcome_ids}
        for item in outcomes
    }
    while ready := {identity for identity, dependencies in remaining.items() if not dependencies}:
        remaining = {
            identity: dependencies - ready for identity, dependencies in remaining.items() if identity not in ready
        }
    if remaining:
        subject = next(item.outcome_id for item in outcomes if item.outcome_id in remaining)
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.DEPENDENCY_CYCLE,
                "outcome dependencies must be acyclic",
                outcome_sources[subject],
                subject,
            )
        )


def _derive_scopes(
    outcomes: list[DeliveryOutcome],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> tuple[DeliveryPlanScope, ...]:
    scopes = tuple(
        DeliveryPlanScope(scope_id=f"SCOPE-{outcome.outcome_id.removeprefix('OUT-')}", outcome_id=outcome.outcome_id)
        for outcome in outcomes
    )
    scope_ids = [scope.scope_id for scope in scopes]
    if len(scope_ids) != len(set(scope_ids)):
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.SCOPE_IDENTITY_COLLISION, "derived scope identities must be unique"
            )
        )
    if {scope.outcome_id for scope in scopes} != {outcome.outcome_id for outcome in outcomes} or len(scopes) != len(
        outcomes
    ):
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.SCOPE_COVERAGE_INVALID,
                "every outcome must own exactly one plan scope",
            )
        )
    return scopes


def _diagnostic(
    code: DeliveryCompilationDiagnosticCode,
    detail: str,
    source_name: SourceName | None = None,
    subject: str | None = None,
) -> DeliveryCompilationDiagnostic:
    return DeliveryCompilationDiagnostic(code=code, source_name=source_name, subject=subject, detail=detail)


def contract_canonical_bytes(contract: DeliveryContract) -> bytes:
    """Return the admitted contract bytes whose SHA-256 is the contract digest."""
    payload = contract.model_dump(mode="json")
    return f"{json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n".encode()


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


__all__ = [
    "DeliveryCommitment",
    "DeliveryCommitmentClass",
    "DeliveryCompilationDiagnostic",
    "DeliveryCompilationDiagnosticCode",
    "DeliveryCompilationResult",
    "DeliveryContract",
    "DeliveryDecision",
    "DeliveryDecisionDelta",
    "DeliveryDecisionOrigin",
    "DeliveryOutcome",
    "DeliveryPlanScope",
    "DeliverySourceBinding",
    "compile_delivery_contract",
    "contract_canonical_bytes",
    "decision_delta",
    "is_decision_id",
    "parse_delivery_contract",
]
