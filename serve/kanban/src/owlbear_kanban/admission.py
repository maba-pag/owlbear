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

    revision_digest: str
    findings: tuple[AdmissionFinding, ...]

    @property
    def errors(self) -> tuple[AdmissionFinding, ...]:
        return tuple(item for item in self.findings if item.severity == AdmissionSeverity.ERROR)

    @property
    def admitted(self) -> bool:
        return not self.errors


def _finding(code: str, target: str, detail: str, remediation: str, evidence: str = "") -> AdmissionFinding:
    return AdmissionFinding(
        code=code,
        severity=AdmissionSeverity.ERROR,
        target=target,
        evidence=evidence or target,
        detail=detail,
        remediation=remediation,
    )


def _evaluate_graph(revision: ChangeRevision) -> list[AdmissionFinding]:  # noqa: C901
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

    owned: set[str] = set()
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
            owned.add(obligation)
            owned.update(node.supports)
    for obligation in obligation_ids - owned:
        findings.extend(
            [
                _finding(
                    "DV-003",
                    obligation,
                    "obligation has no delivery-node owner or support",
                    "Assign the obligation to a delivery node.",
                )
            ]
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
    return findings


def _evaluate_structured_evidence(revision: ChangeRevision, evidence: AdmissionEvidence) -> list[AdmissionFinding]:
    findings: list[AdmissionFinding] = []
    challenged_sections = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
    expected = {entity.id for section in challenged_sections for entity in getattr(revision.graph, section)}
    actual = set(evidence.challenge)
    findings.extend(
        _finding(
            "DV-010",
            target,
            "challenge disposition targets an undeclared delivery entity",
            "Remove the dangling challenge target.",
        )
        for target in sorted(actual - expected)
    )
    findings.extend(
        _finding(
            "DV-010",
            target,
            "structured challenge disposition is missing",
            "Record one disposition and evidence for this delivery entity.",
        )
        for target in sorted(expected - actual)
    )
    for target in sorted(expected & actual):
        disposition = evidence.challenge[target]
        if not isinstance(disposition, Mapping) or disposition.get("disposition") not in {"pass", "fail", "defer"}:
            findings.append(
                _finding(
                    "DV-010",
                    target,
                    "challenge evidence must contain a structured disposition",
                    "Record disposition and evidence for this delivery entity.",
                )
            )
        elif disposition["disposition"] != "pass":
            findings.append(
                _finding(
                    "DV-010",
                    target,
                    f"challenge disposition is {disposition['disposition']}",
                    "Resolve the challenge finding before admission.",
                )
            )
        elif not isinstance(disposition.get("evidence"), str) or not disposition["evidence"].strip():
            findings.append(
                _finding(
                    "DV-010",
                    target,
                    "challenge disposition has no evidence",
                    "Record source-grounded evidence for this disposition.",
                )
            )
    if not isinstance(evidence.baseline.get("commands"), (tuple, list)) or not evidence.baseline.get("commands"):
        findings.append(
            _finding(
                "DV-012",
                revision.change_id,
                "baseline evidence must list executed commands",
                "Record clean baseline commands and results.",
            )
        )
    if evidence.baseline.get("digest") not in {None, evidence.digest}:
        findings.append(
            _finding(
                "DV-012",
                revision.change_id,
                "baseline evidence is bound to a different digest",
                "Recompute the baseline for this delivery digest.",
                str(evidence.baseline.get("digest")),
            )
        )
    if evidence.approval.get("digest") not in {None, evidence.digest}:
        findings.append(
            _finding(
                "DV-011",
                revision.change_id,
                "approval is bound to a different digest",
                "Record approval for this delivery digest.",
                str(evidence.approval.get("digest")),
            )
        )
    return findings


def evaluate_admission(revision: ChangeRevision, evidence: AdmissionEvidence) -> AdmissionAssessment:
    """Evaluate one revision and digest-bound evidence without performing writes."""
    digest = compute_delivery_digest(revision.intent, revision.design, revision.decisions, revision.graph)
    findings = _evaluate_graph(revision)
    if evidence.digest != digest:
        findings.append(
            _finding(
                "DV-001",
                revision.change_id,
                "evidence digest does not match the loaded revision",
                "Recompute evidence for the current delivery digest.",
                evidence.digest,
            )
        )
    if not evidence.challenge:
        findings.append(
            _finding(
                "DV-010",
                revision.change_id,
                "independent challenge evidence is missing",
                "Provide complete structured challenge evidence.",
            )
        )
    if not evidence.baseline:
        findings.append(
            _finding(
                "DV-012",
                revision.change_id,
                "clean baseline evidence is missing",
                "Record the clean baseline and focused commands.",
            )
        )
    if evidence.approval.get("approved") is not True:
        findings.append(
            _finding(
                "DV-011",
                revision.change_id,
                "explicit user approval is missing",
                "Record explicit approval for this delivery digest.",
            )
        )
    if not evidence.limits:
        findings.append(
            _finding("DV-013", revision.change_id, "known limits are missing", "Record the limits of this admission.")
        )
    findings.extend(_evaluate_structured_evidence(revision, evidence))
    findings.sort(key=lambda item: (item.code, item.target, item.detail))
    return AdmissionAssessment(revision_digest=digest, findings=tuple(findings))


__all__ = ["AdmissionAssessment", "AdmissionEvidence", "AdmissionFinding", "AdmissionSeverity", "evaluate_admission"]
