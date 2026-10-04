"""One merge-offer computation from fresh provider facts, shared by readiness and approval (N05 I1, I9)."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery.publication_provider import (
    PublicationCheckBlockingState,
    PublicationCheckSnapshot,
    PublicationMergeEvidence,
    PublicationMergeMethod,
    PublicationMergeSettings,
    PublicationPullRequest,
    classify_publication_check,
)

_SHA = r"^[0-9a-f]{40}$"
_DIGEST = r"^[0-9a-f]{64}$"
_REPOSITORY = r"^[^\s/]+/[^\s/]+$"
# U1 (a): Delivery offers only merge commits, so the reviewed head stays in target history.
OFFERED_MERGE_METHOD = PublicationMergeMethod.MERGE
_OFFERABLE_STATES = frozenset({"CLEAN", "HAS_HOOKS", "UNSTABLE"})
_CONFLICT_STATES = frozenset({"DIRTY", "CONFLICTING"})


class _MergeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MergeBlockReason(StrEnum):
    """Known reasons Delivery offers no merge; the user acts in GitHub or Delivery syncs."""

    CONFLICTS = "conflicts"
    BEHIND = "behind"
    PROTECTION = "protection"
    DRAFT = "draft"
    CLOSED = "closed"
    CHECKS_FAILED = "checks-failed"
    QUEUE_REQUIRED = "queue-required"
    STACKED = "stacked"
    WRONG_BASE = "wrong-base"
    CAPABILITY_UNAVAILABLE = "capability-unavailable"
    METHOD_NOT_ALLOWED = "method-not-allowed"


class MergeBlock(_MergeModel):
    """One known reason the pull request cannot be offered for merge."""

    reason: MergeBlockReason
    detail: str | None = Field(default=None, min_length=1, max_length=200)


class MergeOfferCheck(_MergeModel):
    """One required check bound by name and conclusion, never by observation identity (A7)."""

    name: str = Field(min_length=1)
    conclusion: str = Field(min_length=1)


class MergeCheckSummary(_MergeModel):
    """Required and optional check counts at the offered head."""

    required_passed: int = Field(ge=0)
    required_pending: int = Field(ge=0)
    required_failed: int = Field(ge=0)
    optional_failed: int = Field(ge=0)


class MergeProofSummary(_MergeModel):
    """Finalization proof behind the offer; the proof target is the last target-sync head."""

    observation_count: int = Field(ge=0)
    review_id: str = Field(pattern=_DIGEST)
    proof_target: str = Field(pattern=_SHA)


class MergeOffer(_MergeModel):
    """Exact merge offer; ``offer_id`` binds every I1 fact and excludes the title and summaries."""

    offer_id: str = Field(pattern=_DIGEST)
    repository: str = Field(min_length=3, pattern=_REPOSITORY)
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA)
    base_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=_SHA)
    finalization_id: str = Field(pattern=_DIGEST)
    ready_receipt_id: str = Field(pattern=_DIGEST)
    merge_method: PublicationMergeMethod
    stack_size: int = Field(ge=1)
    required_checks: tuple[MergeOfferCheck, ...]
    check_summary: MergeCheckSummary
    proof: MergeProofSummary


class MergeOfferAuthority(_MergeModel):
    """Delivery-owned facts an offer must match: finalization, ready receipt and proof target."""

    repository: str = Field(min_length=3, pattern=_REPOSITORY)
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    exact_head: str = Field(pattern=_SHA)
    finalization_id: str = Field(pattern=_DIGEST)
    ready_receipt_id: str = Field(pattern=_DIGEST)
    observation_count: int = Field(ge=0)
    review_id: str = Field(pattern=_DIGEST)
    proof_target: str | None = Field(default=None, pattern=_SHA)


class MergeFacts(_MergeModel):
    """Provider facts read for one offer; ``capable`` is false without the merge protocol (D1)."""

    capable: bool
    evidence: PublicationMergeEvidence | None = None
    settings: PublicationMergeSettings | None = None
    checks: PublicationCheckSnapshot | None = None
    target_head: str | None = Field(default=None, pattern=_SHA)


MergeReadinessReason = Literal[
    "merge-approval-required",
    "merge-checking",
    "merge-blocked",
    "target-sync-required",
    "checks-running",
    "provider-unavailable",
]


class MergeDecision(_MergeModel):
    """Readiness meaning of one awaiting-merge pull request."""

    reason: MergeReadinessReason
    offer: MergeOffer | None = None
    block: MergeBlock | None = None
    target_head: str | None = Field(default=None, pattern=_SHA)


def _blocked(reason: MergeBlockReason, detail: str | None = None) -> MergeDecision:
    return MergeDecision(reason="merge-blocked", block=MergeBlock(reason=reason, detail=detail))


def _check_summary(checks: PublicationCheckSnapshot) -> MergeCheckSummary:
    states = [(check.required, classify_publication_check(check)) for check in checks.checks]
    return MergeCheckSummary(
        required_passed=sum(
            required and state is PublicationCheckBlockingState.NOT_BLOCKING for required, state in states
        ),
        required_pending=sum(state is PublicationCheckBlockingState.REQUIRED_PENDING for _required, state in states),
        required_failed=sum(state is PublicationCheckBlockingState.BLOCKING for _required, state in states),
        optional_failed=sum(
            not check.required
            and check.conclusion is not None
            and classify_publication_check(check.model_copy(update={"required": True}))
            is PublicationCheckBlockingState.BLOCKING
            for check in checks.checks
        ),
    )


def decide_merge(  # noqa: C901, PLR0911, PLR0912 - one ordered row per classification (D7, D9, I10).
    authority: MergeOfferAuthority,
    pull_request: PublicationPullRequest,
    facts: MergeFacts | None,
) -> MergeDecision | None:
    """Classify one open pull request; ``None`` leaves a merged, closed or moved head to acceptance."""
    if facts is None:
        return MergeDecision(reason="provider-unavailable")
    if not facts.capable:
        return _blocked(MergeBlockReason.CAPABILITY_UNAVAILABLE)
    evidence, settings, checks = facts.evidence, facts.settings, facts.checks
    if evidence is None or settings is None or checks is None or facts.target_head is None:
        return MergeDecision(reason="provider-unavailable")
    if evidence.merged or evidence.head_sha != authority.exact_head:
        return None
    if evidence.state != "open":
        return _blocked(MergeBlockReason.CLOSED)
    if evidence.draft:
        return _blocked(MergeBlockReason.DRAFT)
    if evidence.stack is not None and evidence.stack.size > 1:
        return _blocked(MergeBlockReason.STACKED, f"stack of {evidence.stack.size} pull requests")
    if evidence.base_branch != authority.target_branch:
        return _blocked(MergeBlockReason.WRONG_BASE, f"base {evidence.base_branch}")
    if authority.proof_target != facts.target_head:
        return MergeDecision(reason="target-sync-required", target_head=facts.target_head)
    if not settings.viewer_can_push:
        return _blocked(MergeBlockReason.CAPABILITY_UNAVAILABLE, "no push permission")
    if settings.queue_required:
        return _blocked(MergeBlockReason.QUEUE_REQUIRED)
    if OFFERED_MERGE_METHOD not in settings.allowed_methods:
        return _blocked(MergeBlockReason.METHOD_NOT_ALLOWED)
    state = (pull_request.merge_state_status or "").upper()
    if pull_request.mergeable is False or state in _CONFLICT_STATES:
        return _blocked(MergeBlockReason.CONFLICTS)
    if state == "BEHIND":
        return _blocked(MergeBlockReason.BEHIND)
    if state in {"", "UNKNOWN"}:
        return MergeDecision(reason="merge-checking")
    if checks.head_sha != authority.exact_head:
        return MergeDecision(reason="provider-unavailable")
    summary = _check_summary(checks)
    if summary.required_failed:
        return _blocked(MergeBlockReason.CHECKS_FAILED, f"{summary.required_failed} required check(s) failed")
    if summary.required_pending:
        return MergeDecision(reason="checks-running")
    if state == "DRAFT":
        return _blocked(MergeBlockReason.DRAFT)
    if state not in _OFFERABLE_STATES:
        return _blocked(MergeBlockReason.PROTECTION, state.lower())
    required_checks = tuple(
        sorted(
            (
                MergeOfferCheck(name=check.name, conclusion=check.conclusion or check.status)
                for check in checks.checks
                if check.required
            ),
            key=lambda check: (check.name, check.conclusion),
        )
    )
    bound: dict[str, object] = {
        "repository": evidence.repository,
        "number": evidence.number,
        "node_id": evidence.node_id,
        "head_sha": evidence.head_sha,
        "base_branch": evidence.base_branch,
        "target_head": facts.target_head,
        "finalization_id": authority.finalization_id,
        "ready_receipt_id": authority.ready_receipt_id,
        "merge_method": OFFERED_MERGE_METHOD.value,
        "stack_size": evidence.stack.size if evidence.stack is not None else 1,
        "required_checks": [check.model_dump() for check in required_checks],
    }
    offer = MergeOffer(
        offer_id=hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        repository=evidence.repository,
        number=evidence.number,
        node_id=evidence.node_id,
        title=pull_request.title,
        head_sha=evidence.head_sha,
        base_branch=evidence.base_branch,
        target_head=facts.target_head,
        finalization_id=authority.finalization_id,
        ready_receipt_id=authority.ready_receipt_id,
        merge_method=OFFERED_MERGE_METHOD,
        stack_size=evidence.stack.size if evidence.stack is not None else 1,
        required_checks=required_checks,
        check_summary=summary,
        proof=MergeProofSummary(
            observation_count=authority.observation_count,
            review_id=authority.review_id,
            proof_target=facts.target_head,
        ),
    )
    return MergeDecision(reason="merge-approval-required", offer=offer)


__all__ = [
    "OFFERED_MERGE_METHOD",
    "MergeBlock",
    "MergeBlockReason",
    "MergeCheckSummary",
    "MergeDecision",
    "MergeFacts",
    "MergeOffer",
    "MergeOfferAuthority",
    "MergeOfferCheck",
    "MergeProofSummary",
    "MergeReadinessReason",
    "decide_merge",
]
