"""Receipt-backed completion authority for one merged Delivery Change."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.runtime_transaction import TransactionParticipant

_CHANGE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"


class _AcceptanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CompletionPullRequestIdentity(_AcceptanceModel):
    """Exact provider pull-request identity bound into completion history."""

    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)


class CompletionEvidence(_AcceptanceModel):
    """Exact accepted facts and durable evidence selected for one completion."""

    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    finalization_receipt_id: str = Field(pattern=_DIGEST_PATTERN)
    finalized_change_head: str = Field(pattern=_SHA_PATTERN)
    repository_identity: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    pull_request_identity: CompletionPullRequestIdentity
    accepted_target_ref: str = Field(min_length=1)
    accepted_merge_commit: str = Field(pattern=_SHA_PATTERN)
    merged_at: datetime
    acceptance_observation_id: str = Field(pattern=_DIGEST_PATTERN)
    check_observation_ids: tuple[str, ...] = ()
    review_receipt_ids: tuple[str, ...] = Field(min_length=1)
    completed_at: datetime

    @model_validator(mode="after")
    def _validate_evidence(self) -> CompletionEvidence:
        if self.merged_at.tzinfo is None or self.completed_at.tzinfo is None:
            message = "completion timestamps must include a timezone"
            raise ValueError(message)
        if self.completed_at < self.merged_at:
            message = "completion cannot precede the provider merge timestamp"
            raise ValueError(message)
        if tuple(sorted(set(self.check_observation_ids))) != self.check_observation_ids:
            message = "completion check observation identities must be unique and sorted"
            raise ValueError(message)
        if tuple(sorted(set(self.review_receipt_ids))) != self.review_receipt_ids:
            message = "completion review receipt identities must be unique and sorted"
            raise ValueError(message)
        return self


class CompletionReceipt(CompletionEvidence):
    """Content-addressed terminal receipt for one user-merged Change."""

    completion_id: str = Field(pattern=_DIGEST_PATTERN)
    acceptance_evidence_digest: str = Field(pattern=_DIGEST_PATTERN)

    @classmethod
    def create(cls, evidence: CompletionEvidence) -> CompletionReceipt:
        """Create one receipt from canonical accepted facts and evidence identities."""
        evidence_values = {field_name: getattr(evidence, field_name) for field_name in type(evidence).model_fields}
        acceptance_evidence_digest = _digest(
            {
                "finalization_receipt_id": evidence.finalization_receipt_id,
                "finalized_change_head": evidence.finalized_change_head,
                "repository_identity": evidence.repository_identity,
                "pull_request_identity": evidence.pull_request_identity.model_dump(),
                "accepted_target_ref": evidence.accepted_target_ref,
                "accepted_merge_commit": evidence.accepted_merge_commit,
                "merged_at": evidence.merged_at.isoformat(),
                "acceptance_observation_id": evidence.acceptance_observation_id,
                "check_observation_ids": evidence.check_observation_ids,
                "review_receipt_ids": evidence.review_receipt_ids,
            }
        )
        candidate = cls.model_construct(
            completion_id="0" * 64,
            acceptance_evidence_digest=acceptance_evidence_digest,
            **evidence_values,
        )
        completion_id = _digest(candidate.model_dump(mode="json", exclude={"completion_id"}))
        return cls(
            completion_id=completion_id,
            acceptance_evidence_digest=acceptance_evidence_digest,
            **evidence_values,
        )

    @model_validator(mode="after")
    def _validate_receipt(self) -> CompletionReceipt:
        expected_evidence_digest = _digest(
            {
                "finalization_receipt_id": self.finalization_receipt_id,
                "finalized_change_head": self.finalized_change_head,
                "repository_identity": self.repository_identity,
                "pull_request_identity": self.pull_request_identity.model_dump(),
                "accepted_target_ref": self.accepted_target_ref,
                "accepted_merge_commit": self.accepted_merge_commit,
                "merged_at": self.merged_at.isoformat(),
                "acceptance_observation_id": self.acceptance_observation_id,
                "check_observation_ids": self.check_observation_ids,
                "review_receipt_ids": self.review_receipt_ids,
            }
        )
        if self.acceptance_evidence_digest != expected_evidence_digest:
            message = "completion acceptance evidence digest is invalid"
            raise ValueError(message)
        if self.completion_id != _digest(self.model_dump(mode="json", exclude={"completion_id"})):
            message = "completion receipt identity is invalid"
            raise ValueError(message)
        return self


class CompletionReceiptConflictError(RuntimeError):
    """Completion history is absent, duplicated, or inconsistent with frontier state."""

    code = "ERR_COMPLETION_RECEIPT_CONFLICT"


class CompletionReceiptStore:
    """Read and prepare immutable completion receipts below one runtime root."""

    def __init__(self, runtime_root: Path) -> None:
        self._runtime_root = runtime_root.resolve()

    def read(self, change_id: str) -> CompletionReceipt | None:
        """Read the unique durable completion receipt for one Change."""
        root = self._runtime_root / "completions" / change_id
        if root.is_symlink():
            raise CompletionReceiptConflictError
        if not root.exists():
            return None
        if not root.is_dir():
            raise CompletionReceiptConflictError
        paths = tuple(sorted(root.glob("*.json")))
        if len(paths) != 1 or paths[0].is_symlink():
            raise CompletionReceiptConflictError
        try:
            receipt = CompletionReceipt.model_validate_json(paths[0].read_bytes())
        except (OSError, ValidationError) as exc:
            raise CompletionReceiptConflictError from exc
        if receipt.change_id != change_id or paths[0].stem != receipt.completion_id:
            raise CompletionReceiptConflictError
        return receipt

    def participant(self, receipt: CompletionReceipt) -> TransactionParticipant:
        """Prepare one runtime-rooted immutable completion participant."""
        return TransactionParticipant(
            self._runtime_root,
            Path("completions") / receipt.change_id / f"{receipt.completion_id}.json",
            _model_content(receipt),
        )


def _digest(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _model_content(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


__all__ = [
    "CompletionEvidence",
    "CompletionPullRequestIdentity",
    "CompletionReceipt",
    "CompletionReceiptConflictError",
    "CompletionReceiptStore",
]
