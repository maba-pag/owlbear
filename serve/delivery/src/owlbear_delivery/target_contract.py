"""Deterministic schema-v2 Delivery Contract compilation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

ChangeId = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
CommitmentId = Annotated[str, StringConstraints(strict=True, pattern=r"^COM-[0-9]{3}$")]
OutcomeId = Annotated[str, StringConstraints(strict=True, pattern=r"^OUT-[0-9]{3}$")]
ScopeId = Annotated[str, StringConstraints(strict=True, pattern=r"^SCOPE-[0-9]{3}$")]
Digest = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
SourceName = Literal["intent.md", "design.md"]

_TARGET_FENCE = "yaml target-contract"
_COMMITMENT_KEYS = ("kind", "id", "class", "provenance", "statement")
_OUTCOME_KEYS = ("kind", "id", "title", "promise", "acceptance", "commitments", "dependencies")
_COMMITMENT_ID = re.compile(r"^COM-[0-9]{3}$")
_OUTCOME_ID = re.compile(r"^OUT-[0-9]{3}$")


class DeliveryCommitmentClass(StrEnum):
    """Authored strength of one schema-v2 commitment."""

    DEALBREAKER = "dealbreaker"
    PROTECTED_REQUEST = "protected-request"
    IMPORTANT_REVIEWED = "important-reviewed"
    AGREED_PATH = "agreed-path"
    IMPLEMENTATION_DISCRETION = "implementation-discretion"


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


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryCommitment(_ContractModel):
    """One immutable authored commitment in a schema-v2 contract."""

    commitment_id: CommitmentId
    commitment_class: DeliveryCommitmentClass
    provenance: str = Field(min_length=1)
    statement: str = Field(min_length=1)


class DeliveryOutcome(_ContractModel):
    """One active user-facing result in a schema-v2 contract."""

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
    """Canonical schema-v2 semantic authority derived from authored sources."""

    schema_version: Literal[2] = 2
    change_id: ChangeId
    title: str = Field(min_length=1)
    commitments: tuple[DeliveryCommitment, ...]
    outcomes: tuple[DeliveryOutcome, ...] = Field(min_length=1)
    plan_scopes: tuple[DeliveryPlanScope, ...] = Field(min_length=1)
    source_bindings: tuple[DeliverySourceBinding, ...] = Field(min_length=2, max_length=2)


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
    """Compile exact authored Specification bytes into canonical schema-v2 authority."""
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
    commitments, outcomes, outcome_sources = _parse_definitions((*intent_blocks, *design_blocks), diagnostics)
    _validate_definitions(commitments, outcomes, outcome_sources, diagnostics)
    scopes = _derive_scopes(outcomes, diagnostics)

    if diagnostics:
        return DeliveryCompilationResult(diagnostics=tuple(diagnostics))

    contract = DeliveryContract(
        change_id=change_id,
        title=title,
        commitments=tuple(commitments),
        outcomes=tuple(outcomes),
        plan_scopes=scopes,
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=_digest(intent_bytes)),
            DeliverySourceBinding(source_name="design.md", sha256=_digest(design_bytes)),
        ),
    )
    canonical_bytes = _canonical_json(contract)
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


def _parse_definitions(
    blocks: tuple[tuple[SourceName, str], ...],
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> tuple[list[DeliveryCommitment], list[DeliveryOutcome], dict[str, SourceName]]:
    commitments: list[DeliveryCommitment] = []
    outcomes: list[DeliveryOutcome] = []
    outcome_sources: dict[str, SourceName] = {}
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
        elif type(kind) is not str or kind not in {"commitment", "outcome"}:
            diagnostics.append(
                _diagnostic(
                    DeliveryCompilationDiagnosticCode.KIND_UNKNOWN,
                    "definition kind is not supported",
                    source_name,
                    subject,
                )
            )
        elif kind == "commitment":
            commitment = _parse_commitment(payload, source_name, diagnostics)
            if commitment is not None and _accept_identity(
                commitment.commitment_id, commitment_ids, source_name, diagnostics
            ):
                commitments.append(commitment)
        else:
            outcome = _parse_outcome(payload, source_name, diagnostics)
            if outcome is not None and _accept_identity(outcome.outcome_id, outcome_ids, source_name, diagnostics):
                outcomes.append(outcome)
                outcome_sources[outcome.outcome_id] = source_name
    return commitments, outcomes, outcome_sources


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
    provenance = _text(payload["provenance"], "provenance", context)
    statement = _text(payload["statement"], "statement", context)
    if type(commitment_class) is not str or commitment_class not in DeliveryCommitmentClass:
        diagnostics.append(
            _diagnostic(
                DeliveryCompilationDiagnosticCode.VALUE_INVALID, "commitment class is invalid", source_name, subject
            )
        )
        commitment_class = None
    if commitment_id is None or commitment_class is None or provenance is None or statement is None:
        return None
    return DeliveryCommitment(
        commitment_id=commitment_id,
        commitment_class=DeliveryCommitmentClass(commitment_class),
        provenance=provenance,
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


def _validate_keys(
    payload: dict[object, object],
    allowed: tuple[str, ...],
    source_name: SourceName,
    subject: str | None,
    diagnostics: list[DeliveryCompilationDiagnostic],
) -> bool:
    valid = True
    unknown = sorted(str(key) for key in payload if key not in allowed)
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


def _canonical_json(contract: DeliveryContract) -> bytes:
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
    "DeliveryOutcome",
    "DeliveryPlanScope",
    "DeliverySourceBinding",
    "compile_delivery_contract",
]
