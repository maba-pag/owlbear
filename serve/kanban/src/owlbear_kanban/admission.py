"""Deterministic, side-effect-free admission evaluation for change revisions."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from re import fullmatch
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.change import DELIVERY_SECTION_NAMES, ChangeRevision, StableId, compute_delivery_digest


class AdmissionSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class AdmissionDisposition(StrEnum):
    PASS = "pass"  # noqa: S105
    WARNING = "warning"
    ERROR = "error"


class AdmissionFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    code: str
    severity: AdmissionSeverity
    target: str
    evidence: str
    detail: str
    remediation: str


class AdmissionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    digest: str
    challenge: Mapping[str, Any] = Field(default_factory=dict)
    baseline: Mapping[str, Any] = Field(default_factory=dict)
    approval: Mapping[str, Any] = Field(default_factory=dict)
    limits: tuple[str, ...] = ()


class AdmissionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: int = 1
    revision_digest: str
    findings: tuple[AdmissionFinding, ...]
    limits: tuple[str, ...] = ()

    @property
    def errors(self) -> tuple[AdmissionFinding, ...]:
        return tuple(item for item in self.findings if item.severity == AdmissionSeverity.ERROR)

    @property
    def admitted(self) -> bool:
        return not self.errors


def _finding(  # noqa: PLR0913, PLR0917
    code: str,
    target: str,
    detail: str,
    remediation: str,
    evidence: str = "",
    severity: AdmissionSeverity = AdmissionSeverity.ERROR,
) -> AdmissionFinding:
    return AdmissionFinding(
        code=code,
        severity=severity,
        target=target,
        evidence=evidence or target,
        detail=detail,
        remediation=remediation,
    )


def _evaluate_graph(revision: ChangeRevision) -> list[AdmissionFinding]:  # noqa: C901, PLR0912, PLR0915
    findings: list[AdmissionFinding] = []
    entities = {entity.id for entity in revision.graph.iter_entities()}
    prefixes = ("REQ-", "NEG-", "KEEP-", "WF-", "MOD-", "IF-", "MIG-", "RISK-", "PROOF-", "DN-")
    for section in DELIVERY_SECTION_NAMES:
        for entity in getattr(revision.graph, section):
            for value in entity.model_dump(mode="python", by_alias=True).values():
                values = value if isinstance(value, tuple) else (value,)
                for item in values:
                    if (
                        isinstance(item, str)
                        and any(fullmatch(rf"{prefix}[0-9]{{3}}", item) for prefix in prefixes)
                        and item not in entities
                    ):
                        findings.extend(
                            [
                                _finding(
                                    "DV-002",
                                    entity.id,
                                    f"reference {item} is not declared",
                                    "Declare the referenced stable entity.",
                                    item,
                                )
                            ]
                        )

    owners: dict[str, list[StableId]] = {}
    supported: set[str] = set()
    obligation_ids = {
        item.id
        for item in (
            *revision.graph.requirements,
            *revision.graph.negative_requirements,
            *revision.graph.preserved_behaviors,
        )
    }
    for node in revision.graph.nodes:
        for obligation in node.owns:
            owners.setdefault(obligation, []).append(node.id)
        for obligation in node.supports:
            supported.add(obligation)
    proof_ids = {proof.id for proof in revision.graph.proofs}
    for obligation in obligation_ids:
        obligation_owners = owners.get(obligation, [])
        valid_owner = (
            len(obligation_owners) == 1
            and next(node for node in revision.graph.nodes if node.id == obligation_owners[0]).proof in proof_ids
        )
        if len(obligation_owners) > 1 or (not valid_owner and not supported):
            detail = (
                "obligation has multiple delivery-node owners or support paths"
                if len(obligation_owners) > 1
                else "obligation has no delivery-node owner or support"
            )
            findings.append(
                _finding(
                    "DV-003",
                    obligation,
                    detail,
                    "Assign exactly one delivery node and its proof path to the obligation.",
                )
            )

    node_ids = {node.id for node in revision.graph.nodes}
    visiting: set[StableId] = set()
    visited: set[StableId] = set()
    by_id = {node.id: node for node in revision.graph.nodes}

    def visit(node_id: StableId) -> None:
        if node_id in visiting:
            findings.append(
                _finding(
                    "DV-008", node_id, "delivery graph contains a dependency cycle", "Remove the dependency cycle."
                )
            )
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for dependency in by_id[node_id].dependencies:
            if dependency in node_ids:
                visit(dependency)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_ids:
        visit(node_id)

    if node_ids:
        connected = {next(iter(node_ids))}
        changed = True
        while changed:
            changed = False
            for node in revision.graph.nodes:
                neighbors = set(node.dependencies) & node_ids
                if node.id in connected or neighbors & connected:
                    before = len(connected)
                    connected.add(node.id)
                    connected.update(neighbors)
                    changed |= len(connected) != before
        findings.extend(
            _finding(
                "DV-008",
                node_id,
                "delivery graph contains a disconnected node",
                "Connect the node to the delivery graph.",
            )
            for node_id in sorted(node_ids - connected)
        )

    def is_ancestor(ancestor_id: StableId, node_id: StableId) -> bool:
        pending = [node_id]
        seen: set[StableId] = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == ancestor_id:
                return True
            pending.extend(by_id.get(current, ()).dependencies if current in by_id else ())
        return False

    findings.extend(
        _finding(
            "DV-008",
            workflow.id,
            "workflow is unreachable from a delivery node",
            "Assign the workflow to a delivery node.",
        )
        for workflow in revision.graph.workflows
        if not any(workflow.id in node.owns or workflow.id in node.supports for node in revision.graph.nodes)
        and not any(workflow.id in requirement.workflows for requirement in revision.graph.requirements)
    )
    for interface in revision.graph.interfaces:
        producer = by_id.get(interface.producer)
        if producer is None:
            continue
        findings.extend(
            _finding(
                "DV-008",
                interface.id,
                "interface producer is outside consumer dependency ancestry",
                "Order the producer before the consumer.",
            )
            for consumer_id in interface.consumers
            if consumer_id in by_id and not is_ancestor(producer.id, consumer_id)
        )
    return findings


def _evaluate_delivery_contracts(revision: ChangeRevision) -> list[AdmissionFinding]:
    findings: list[AdmissionFinding] = []
    nodes = {node.id: node for node in revision.graph.nodes}
    entities = {entity.id for entity in revision.graph.iter_entities()}

    for interface in revision.graph.interfaces:
        producer = nodes.get(interface.producer)
        consumers = [nodes.get(consumer) for consumer in interface.consumers]
        if (
            producer is None
            or not interface.consumers
            or interface.id not in producer.produces
            or any(node is None or interface.id not in node.consumes for node in consumers)
            or not all(
                (
                    interface.contract,
                    interface.authority in entities,
                    interface.failure_semantics,
                    interface.migration is None or interface.migration in entities,
                    interface.proof in entities,
                )
            )
        ):
            findings.append(
                _finding(
                    "DV-004",
                    interface.id,
                    "interface producer, consumer, authority, failure, or proof contract is incomplete",
                    "Align node produces/consumes references and populate every interface contract field.",
                )
            )

    findings.extend(
        _finding(
            "DV-005",
            migration.id,
            "migration contract is incomplete",
            "Provide ordered steps, consumer inventory, compatibility, deletion owner, and absence proof.",
        )
        for migration in revision.graph.migrations
        if not all(
            (
                migration.owner in entities,
                migration.source,
                migration.destination,
                migration.ordered_steps,
                migration.consumer_inventory,
                migration.compatibility,
                migration.deletion_owner in entities,
                migration.absence_proof in entities,
            )
        )
    )
    findings.extend(
        _finding(
            "DV-006",
            risk.id,
            "risk disposition is incomplete",
            "Provide scenarios, disposition, owner, and proof for the risk.",
        )
        for risk in revision.graph.risks
        if not all((risk.scenarios, risk.disposition, risk.owner in entities, risk.proof in entities))
    )

    referenced_proofs = {
        entity.proof
        for section in ("workflows", "interfaces", "risks", "nodes")
        for entity in getattr(revision.graph, section)
    }
    dependencies = {node.id: set(node.dependencies) for node in revision.graph.nodes}

    def is_predecessor(owner_id: StableId, node_id: StableId) -> bool:
        pending = [node_id]
        seen: set[StableId] = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == owner_id:
                return True
            pending.extend(dependencies.get(current, ()))
        return False

    for proof in revision.graph.proofs:
        owner = nodes.get(proof.owner)
        if proof.id in referenced_proofs and (
            owner is None
            or owner.proof != proof.id
            or not all(is_predecessor(owner.id, node.id) for node in revision.graph.nodes if node.proof == proof.id)
            or not all((proof.boundary, proof.method, proof.allowed_replacements, proof.durable_outputs))
        ):
            findings.append(
                _finding(
                    "DV-007",
                    proof.id,
                    "proof contract has no build-capable owning predecessor or is incomplete",
                    "Populate proof fields and assign it to the predecessor delivery node.",
                )
            )
    return findings


def _evaluate_authority(revision: ChangeRevision) -> list[AdmissionFinding]:
    findings: list[AdmissionFinding] = []
    findings.extend(
        _finding(
            "DV-010",
            decision.id,
            "material decision is pending or accepted without a selected option",
            "Resolve the decision and select an option before admission.",
        )
        for decision in revision.decisions.decisions
        if decision.status == "pending" or (decision.status == "accepted" and not decision.selected)
    )
    admission = revision.graph.admission
    if admission is None or admission.delivery_digest != revision.delivery_digest:
        findings.append(
            _finding(
                "DV-010",
                revision.change_id,
                "graph admission metadata is missing or bound to a different revision digest",
                "Bind admitted graph metadata to the current delivery digest.",
            )
        )

    categories = {
        "owns": {
            item.id
            for item in (
                *revision.graph.requirements,
                *revision.graph.negative_requirements,
                *revision.graph.preserved_behaviors,
            )
        },
        "supports": {
            item.id
            for item in (
                *revision.graph.requirements,
                *revision.graph.negative_requirements,
                *revision.graph.preserved_behaviors,
            )
        },
        "modules": {item.id for item in revision.graph.modules},
        "produces": {item.id for item in revision.graph.interfaces},
        "consumes": {item.id for item in revision.graph.interfaces},
        "risks": {item.id for item in revision.graph.risks},
    }
    for node in revision.graph.nodes:
        for field, allowed in categories.items():
            findings.extend(
                _finding(
                    "DV-011",
                    node.id,
                    f"node {field} reference {reference} is outside its declared authority category",
                    f"Reference only declared {field} entities from the delivery graph.",
                    reference,
                )
                for reference in getattr(node, field)
                if reference not in allowed
            )
        if node.proof not in {item.id for item in revision.graph.proofs}:
            findings.append(
                _finding(
                    "DV-011",
                    node.id,
                    f"node proof reference {node.proof} is outside its declared proof category",
                    "Reference a declared proof entity.",
                    node.proof,
                )
            )
    return findings


def _evaluate_structured_evidence(revision: ChangeRevision, evidence: AdmissionEvidence) -> list[AdmissionFinding]:
    findings: list[AdmissionFinding] = []
    challenged_sections = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
    expected = {entity.id for section in challenged_sections for entity in getattr(revision.graph, section)}
    actual = set(evidence.challenge)
    findings.extend(
        _finding(
            "EV-002",
            target,
            "challenge disposition targets an undeclared delivery entity",
            "Remove the dangling challenge target.",
        )
        for target in sorted(actual - expected)
    )
    findings.extend(
        _finding(
            "EV-002",
            target,
            "structured challenge disposition is missing",
            "Record one disposition and evidence for this delivery entity.",
        )
        for target in sorted(expected - actual)
    )
    for target in sorted(expected & actual):
        disposition = evidence.challenge[target]
        if not isinstance(disposition, Mapping) or disposition.get("disposition") not in {"pass", "warning", "error"}:
            findings.append(
                _finding(
                    "EV-002",
                    target,
                    "challenge evidence must contain a structured disposition",
                    "Record disposition and evidence for this delivery entity.",
                )
            )
        elif not isinstance(disposition.get("evidence"), str) or not disposition["evidence"].strip():
            findings.append(
                _finding(
                    "EV-002",
                    target,
                    "challenge disposition has no evidence",
                    "Record source-grounded evidence for this disposition.",
                )
            )
        elif disposition["disposition"] != "pass":
            findings.append(
                _finding(
                    "EV-002",
                    target,
                    f"challenge disposition is {disposition['disposition']}",
                    "Resolve the challenge finding before admission.",
                    severity=(
                        AdmissionSeverity.WARNING
                        if disposition["disposition"] == "warning"
                        else AdmissionSeverity.ERROR
                    ),
                )
            )
    if not isinstance(evidence.baseline.get("commands"), (tuple, list)) or not evidence.baseline.get("commands"):
        findings.append(
            _finding(
                "EV-003",
                revision.change_id,
                "baseline evidence must list executed commands",
                "Record clean baseline commands and results.",
            )
        )
    elif any(
        isinstance(command, Mapping) and command.get("exit_code", 0) != 0 for command in evidence.baseline["commands"]
    ):
        findings.append(
            _finding(
                "EV-003",
                revision.change_id,
                "baseline command failed",
                "Record a baseline with successful commands.",
            )
        )
    if evidence.baseline.get("digest") != evidence.digest:
        findings.append(
            _finding(
                "EV-003",
                revision.change_id,
                "baseline evidence is missing or bound to a different digest",
                "Recompute the baseline for this delivery digest.",
                str(evidence.baseline.get("digest", "missing")),
            )
        )
    if evidence.approval.get("digest") != evidence.digest:
        findings.append(
            _finding(
                "EV-004",
                revision.change_id,
                "approval is missing or bound to a different digest",
                "Record approval for this delivery digest.",
                str(evidence.approval.get("digest", "missing")),
            )
        )
    return findings


def evaluate_admission(revision: ChangeRevision, evidence: AdmissionEvidence) -> AdmissionAssessment:
    """Evaluate one revision and digest-bound evidence without performing writes."""
    digest = compute_delivery_digest(revision.intent, revision.design, revision.decisions, revision.graph)
    findings = _evaluate_graph(revision)
    findings.extend(_evaluate_delivery_contracts(revision))
    findings.extend(_evaluate_authority(revision))
    if evidence.digest != digest:
        findings.append(
            _finding(
                "EV-001",
                revision.change_id,
                "evidence digest does not match the loaded revision",
                "Recompute evidence for the current delivery digest.",
                evidence.digest,
            )
        )
    if not evidence.challenge:
        findings.append(
            _finding(
                "EV-002",
                revision.change_id,
                "independent challenge evidence is missing",
                "Provide complete structured challenge evidence.",
            )
        )
    if not evidence.baseline:
        findings.append(
            _finding(
                "EV-003",
                revision.change_id,
                "clean baseline evidence is missing",
                "Record the clean baseline and focused commands.",
            )
        )
    if evidence.approval.get("approved") is not True:
        findings.append(
            _finding(
                "EV-004",
                revision.change_id,
                "explicit user approval is missing",
                "Record explicit approval for this delivery digest.",
            )
        )
    if not evidence.limits:
        findings.append(
            _finding("EV-005", revision.change_id, "known limits are missing", "Record the limits of this admission.")
        )
    findings.extend(_evaluate_structured_evidence(revision, evidence))
    findings.sort(key=lambda item: (item.code, item.target, item.detail))
    return AdmissionAssessment(revision_digest=digest, findings=tuple(findings), limits=evidence.limits)


__all__ = [
    "AdmissionAssessment",
    "AdmissionDisposition",
    "AdmissionEvidence",
    "AdmissionFinding",
    "AdmissionSeverity",
    "evaluate_admission",
]
