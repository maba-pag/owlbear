"""One merge attempt per Cockpit approval and its readback-only settlement (N05 1.4, 1.11)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.publication_provider import (
    PublicationMergeMethod,
    PublicationMergeRequestStatus,
    RequestPublicationMerge,
)
from owlbear_delivery.storage_io import atomic_write

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.merge_offer import MergeOffer
    from owlbear_delivery.publication_provider import PublicationMergeEvidence, PublicationMergeRequestResult

_SHA = r"^[0-9a-f]{40}$"
_DIGEST = r"^[0-9a-f]{64}$"
_CHANGE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class MergeAttemptState(StrEnum):
    """Attempt journal states; only ``intent``, ``released`` and ``pending`` are nonterminal."""

    INTENT = "intent"
    RELEASED = "released"
    PENDING = "pending"
    MERGED = "merged"
    REFUSED = "refused"
    NOT_SENT = "not-sent"
    HEAD_CHANGED = "head-changed"
    CLOSED = "closed"


NONTERMINAL_MERGE_STATES = frozenset({MergeAttemptState.INTENT, MergeAttemptState.RELEASED, MergeAttemptState.PENDING})
MERGE_RESPONSE_DEADLINE = timedelta(minutes=10)
MERGE_OBSERVATION_WINDOW = timedelta(hours=24)


class MergeRace(StrEnum):
    """Post-merge comparison against the approved target (U3(e))."""

    NONE = "none"
    TARGET_ADVANCED = "target-advanced"
    SCOPE_CHANGED = "scope-changed"


class MergeAttemptRecord(BaseModel):
    """One approval's offer facts, provenance and settlement; rewritten by CAS under the checkpoint lock."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    approval_id: str = Field(pattern=_DIGEST)
    change_id: str = Field(pattern=_CHANGE)
    offer_id: str = Field(pattern=_DIGEST)
    submission_id: str = Field(min_length=1, max_length=128)
    host_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    approved_at: str = Field(min_length=1)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA)
    base_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=_SHA)
    finalization_id: str = Field(pattern=_DIGEST)
    ready_receipt_id: str = Field(pattern=_DIGEST)
    merge_method: PublicationMergeMethod
    state: MergeAttemptState
    released_at: str | None = None
    group_id: int | None = None
    group_started_at: str | None = None
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    refusal_reason: str | None = Field(default=None, max_length=64)
    merge_commit: str | None = Field(default=None, pattern=_SHA)
    parent_1: str | None = Field(default=None, pattern=_SHA)
    merged_base: str | None = None
    race: MergeRace | None = None

    @property
    def nonterminal(self) -> bool:
        """Return whether readback may still change this attempt."""
        return self.state in NONTERMINAL_MERGE_STATES

    @property
    def pr_url(self) -> str:
        """Return the provider pull-request page for the attention text (1.13)."""
        return f"https://github.com/{self.repository}/pull/{self.number}"

    def request(self) -> RequestPublicationMerge:
        """Return the one ``sha``-fenced request this approval may send."""
        return RequestPublicationMerge(
            repository=self.repository,
            number=self.number,
            node_id=self.node_id,
            expected_head_sha=self.head_sha,
            merge_method=self.merge_method,
        )


class ApproveChangeMerge(BaseModel):
    """The user's Cockpit approval of one exact offer; a retried POST repeats ``submission_id``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str = Field(pattern=_CHANGE)
    offer_id: str = Field(pattern=_DIGEST)
    submission_id: str = Field(min_length=1, max_length=128)
    host_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)


class MergeApprovalResult(BaseModel):
    """The approval's attempt after its single request, and the completion when acceptance completed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    attempt: MergeAttemptRecord
    completion_id: str | None = Field(default=None, pattern=_DIGEST)


class MergeAttemptConflictError(RuntimeError):
    """The stored attempt differs from the expected predecessor of a CAS rewrite."""


def approval_id(offer_id: str, submission_id: str) -> str:
    """Return the attempt identity: one per offer and dialog submission (D4)."""
    payload = json.dumps({"offer_id": offer_id, "submission_id": submission_id}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def new_merge_attempt(request: ApproveChangeMerge, offer: MergeOffer, approved_at: str) -> MergeAttemptRecord:
    """Return the ``intent`` record for one approval of one exact offer."""
    return MergeAttemptRecord(
        approval_id=approval_id(offer.offer_id, request.submission_id),
        change_id=request.change_id,
        offer_id=offer.offer_id,
        submission_id=request.submission_id,
        host_id=request.host_id,
        session_id=request.session_id,
        approved_at=approved_at,
        repository=offer.repository,
        number=offer.number,
        node_id=offer.node_id,
        head_sha=offer.head_sha,
        base_branch=offer.base_branch,
        target_head=offer.target_head,
        finalization_id=offer.finalization_id,
        ready_receipt_id=offer.ready_receipt_id,
        merge_method=offer.merge_method,
        state=MergeAttemptState.INTENT,
    )


class MergeAttemptStore:
    """Attempt records in each Change's ``merge-attempts`` directory; callers hold the checkpoint lock."""

    def __init__(self, target_root: Path, change_id: str) -> None:
        self._root = target_root / "changes" / change_id / "merge-attempts"

    def read(self, attempt_id: str) -> MergeAttemptRecord | None:
        """Return one attempt, or ``None`` when it was never written."""
        path = self._root / f"{attempt_id}.json"
        try:
            return MergeAttemptRecord.model_validate_json(path.read_bytes(), strict=True)
        except FileNotFoundError:
            return None
        except ValidationError as exc:
            message = f"merge attempt {attempt_id} is unreadable"
            raise ValueError(message) from exc

    def attempts(self) -> tuple[MergeAttemptRecord, ...]:
        """Return every attempt of this Change."""
        if not self._root.is_dir():
            return ()
        records = (self.read(path.stem) for path in sorted(self._root.glob("*.json")))
        return tuple(record for record in records if record is not None)

    def nonterminal(self) -> MergeAttemptRecord | None:
        """Return the one attempt readback may still settle, if any (D4)."""
        return next((record for record in self.attempts() if record.nonterminal), None)

    def observed(self) -> MergeAttemptRecord | None:
        """Return the approval acceptance still observes: open, or merged on the approved target."""
        return self.nonterminal() or next(
            (
                record
                for record in self.attempts()
                if record.state is MergeAttemptState.MERGED and record.race is MergeRace.NONE
            ),
            None,
        )

    def raced(self) -> MergeAttemptRecord | None:
        """Return a merged attempt whose merge differs from the approved target or scope (I4, Q4)."""
        return next(
            (
                record
                for record in self.attempts()
                if record.state is MergeAttemptState.MERGED and record.race is not MergeRace.NONE
            ),
            None,
        )

    def write(self, record: MergeAttemptRecord, *, expected: MergeAttemptRecord | None) -> MergeAttemptRecord:
        """Create or CAS-rewrite one attempt; ``expected`` is the stored predecessor or ``None``."""
        if self.read(record.approval_id) != expected:
            message = "merge attempt changed since it was read"
            raise MergeAttemptConflictError(message)
        self._root.mkdir(parents=True, exist_ok=True)
        content = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
        atomic_write(self._root / f"{record.approval_id}.json", content)
        return record


def _race(attempt: MergeAttemptRecord, evidence: PublicationMergeEvidence) -> MergeRace:
    if evidence.base_branch != attempt.base_branch:
        return MergeRace.SCOPE_CHANGED
    if evidence.merge_commit_parents[0] != attempt.target_head:
        return MergeRace.TARGET_ADVANCED
    return MergeRace.NONE


def _merge_age(attempt: MergeAttemptRecord, now: str) -> timedelta:
    started = attempt.released_at or attempt.approved_at
    return datetime.fromisoformat(now) - datetime.fromisoformat(started)


def merge_response_overdue(attempt: MergeAttemptRecord, now: str) -> bool:
    """Return whether the provider has left this approval unsettled past its deadline; never refuses or resends."""
    return _merge_age(attempt, now) > MERGE_RESPONSE_DEADLINE


def merge_observation_expired(attempt: MergeAttemptRecord, now: str) -> bool:
    """Return whether automatic acceptance reads for this approval have ended; Check again still reads."""
    return _merge_age(attempt, now) > MERGE_OBSERVATION_WINDOW


def settle_merge_attempt(  # noqa: PLR0911 - one return per settlement row, in match order.
    attempt: MergeAttemptRecord,
    evidence: PublicationMergeEvidence | None,
    result: PublicationMergeRequestResult | None,
) -> MergeAttemptRecord:
    """Apply rows S1-S8 to one fresh read; ``None`` evidence is a failed read, never a refusal."""
    if not attempt.nonterminal:
        return attempt
    if evidence is not None and evidence.merged:
        if evidence.head_sha != attempt.head_sha:
            return attempt.model_copy(update={"state": MergeAttemptState.HEAD_CHANGED})
        return attempt.model_copy(
            update={
                "state": MergeAttemptState.MERGED,
                "merge_commit": evidence.merge_commit_sha,
                "parent_1": evidence.merge_commit_parents[0],
                "merged_base": evidence.base_branch,
                "race": _race(attempt, evidence),
            }
        )
    if attempt.state is MergeAttemptState.INTENT:
        return attempt.model_copy(update={"state": MergeAttemptState.NOT_SENT})
    if result is not None and result.status is PublicationMergeRequestStatus.REFUSED and result.refusal is not None:
        return attempt.model_copy(
            update={"state": MergeAttemptState.REFUSED, "refusal_reason": result.refusal.reason.value}
        )
    pending = result.pending if result is not None else None
    if pending is not None and not pending.matches(attempt.request()):
        return attempt.model_copy(update={"state": MergeAttemptState.REFUSED, "refusal_reason": "foreign-request"})
    if evidence is not None and evidence.state == "closed":
        return attempt.model_copy(update={"state": MergeAttemptState.CLOSED})
    if evidence is not None and evidence.head_sha != attempt.head_sha:
        return attempt.model_copy(update={"state": MergeAttemptState.HEAD_CHANGED})
    if pending is not None:
        return attempt.model_copy(update={"state": MergeAttemptState.PENDING, "request_id": pending.request_id})
    return attempt


__all__ = [
    "MERGE_OBSERVATION_WINDOW",
    "MERGE_RESPONSE_DEADLINE",
    "NONTERMINAL_MERGE_STATES",
    "ApproveChangeMerge",
    "MergeApprovalResult",
    "MergeAttemptConflictError",
    "MergeAttemptRecord",
    "MergeAttemptState",
    "MergeAttemptStore",
    "MergeRace",
    "approval_id",
    "merge_observation_expired",
    "merge_response_overdue",
    "new_merge_attempt",
    "settle_merge_attempt",
]
