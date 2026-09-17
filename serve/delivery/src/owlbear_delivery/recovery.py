"""Exact, host-verified recovery authority; no caller assertion grants custody."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant

_MAX_RECORD_BYTES = 65_536
_DIGEST_LENGTH = 64
MAX_RECOVERY_INTENTS = 256


class _RecoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RecoveryInvocationRequest(_RecoveryModel):
    """Engine-issued identity and complete managed-resource boundary sent to a host."""

    change_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    owner_id: str = Field(min_length=1, max_length=128)
    attempt_id: str = Field(min_length=1, max_length=128)
    outcome_id: str | None = None
    kind: Literal["claim", "finalizer", "mark-ready", "reconcile-checkpoint", "sync-target", "observe-acceptance"]
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch: str = Field(min_length=1, max_length=256)
    worktree: str = Field(min_length=1, max_length=4096)
    repository: str = Field(min_length=1, max_length=4096)
    runtime_root: str = Field(min_length=1, max_length=4096)
    integration_target: str = Field(min_length=1, max_length=256)
    publication_repository: str | None = Field(default=None, max_length=256)
    mutation_channels: tuple[
        Literal[
            "managed-filesystem",
            "shared-git-metadata-and-refs",
            "git-remotes",
            "delivery-runtime",
            "publication-provider",
        ],
        ...,
    ] = (
        "managed-filesystem",
        "shared-git-metadata-and-refs",
        "git-remotes",
        "delivery-runtime",
        "publication-provider",
    )


class RecoveryInvocation(_RecoveryModel):
    """Host registration, not a reinterpretation of a dispatch PID/session string."""

    schema_version: Literal[1] = 1
    request: RecoveryInvocationRequest
    host_instance: str = Field(min_length=1, max_length=128)
    host_generation: str = Field(min_length=1, max_length=128)
    invocation_id: str = Field(min_length=1, max_length=256)


class RecoveryIntent(_RecoveryModel):
    """Immutable proposed recovery of one captured owner; never a release capability."""

    schema_version: Literal[1] = 1
    invocation: RecoveryInvocation
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    coordination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    workspace_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_record: str = Field(min_length=1, max_length=16384)
    failure_id: str | None = Field(default=None, max_length=128)
    effect_receipt_id: str | None = Field(default=None, max_length=128)
    engine_result_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    proposal_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    kind: Literal["clean-claim", "clean-finalizer", "ready-readback"]

    @property
    def recovery_id(self) -> str:
        """Return the content-addressed journal identity (not evidence authenticity)."""
        return digest(encoded(self))


class RecoveryEvidenceReference(_RecoveryModel):
    """Opaque reference resolved exclusively by the configured host owner."""

    reference: str = Field(min_length=1, max_length=256)


class RecoveryEvidence(_RecoveryModel):
    """Owner-verified whole-invocation closure or restart-durable enforced exclusion."""

    schema_version: Literal[1] = 1
    reference: RecoveryEvidenceReference
    recovery_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    invocation: RecoveryInvocation
    status: Literal["closed", "excluded", "still-running", "unknown", "unavailable"]
    scope: Literal["invocation-all-descendants-all-tool-jobs"] = "invocation-all-descendants-all-tool-jobs"


class RecoveryReceipt(_RecoveryModel):
    """Completed recovery, distinct from success of the original failed action."""

    schema_version: Literal[1] = 1
    recovery_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: RecoveryEvidence
    stages: tuple[Literal["proposed"], Literal["excluded"], Literal["reconciled"], Literal["completed"]] = (
        "proposed",
        "excluded",
        "reconciled",
        "completed",
    )
    preservation: Literal["clean-no-restoration"] = "clean-no-restoration"
    owner_effect: Literal["no-workspace-effect", "ready-receipt-readback"]
    owner_observation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finished_at: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _completed_evidence(self) -> Self:
        if (
            self.evidence.recovery_id != self.recovery_id
            or self.evidence.status not in {"closed", "excluded"}
            or (self.owner_effect == "ready-receipt-readback") != (self.owner_observation_id is not None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        return self


class RecoveryEvidenceProvider(Protocol):
    """Trusted engine dependency, never a transport-supplied acknowledgement.

    Registration must bind the issued identity before dispatch. Verification resolves an
    opaque reference independently, covers the complete dynamically-created writer/job
    graph and forbids resuming the invocation. `excluded` additionally promises actual
    exclusion from every resource/channel in the request, durable across all restarts
    until closure. A cancellation request, observed PID exit or reacquired lock is not
    verification. Providers must return unknown when they cannot uphold this contract.
    """

    def register(self, request: RecoveryInvocationRequest) -> RecoveryInvocation | None:
        """Register an engine-issued invocation before dispatch."""
        ...

    def verify(self, reference: RecoveryEvidenceReference, intent: RecoveryIntent) -> RecoveryEvidence:
        """Resolve current evidence using the same opaque reference across restarts.

        Identity remains stable when exclusion advances to closure. Lost evidence is
        unknown/unavailable, never a replacement reference or reconstructed provenance.
        """
        ...


class UnavailableRecoveryEvidenceProvider:
    """Default host boundary: no evidence, no release."""

    def register(self, request: RecoveryInvocationRequest) -> None:
        """Do not manufacture host provenance for an issued invocation."""

    def verify(self, reference: RecoveryEvidenceReference, intent: RecoveryIntent) -> RecoveryEvidence:
        """Return unavailable without consulting caller identity strings."""
        return RecoveryEvidence(
            reference=reference, recovery_id=intent.recovery_id, invocation=intent.invocation, status="unavailable"
        )


def encoded(model: BaseModel) -> bytes:
    """Canonical immutable journal bytes."""
    return (model.model_dump_json() + "\n").encode()


def digest(content: bytes) -> str:
    """Hash exact persisted bytes."""
    return hashlib.sha256(content).hexdigest()


def invocation_path(invocation: RecoveryInvocationRequest) -> Path:
    """Locate an exact issued owner without accepting caller-authored path segments."""
    return Path("changes") / invocation.change_id / "invocations" / f"{digest(invocation.owner_id.encode())}.json"


def journal_path(change_id: str, recovery_id: str, name: str) -> Path:
    """Build contained journal paths from validated identities."""
    if not change_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in change_id):
        raise DeliveryWorkerExclusionRequiredError
    if len(recovery_id) != _DIGEST_LENGTH or any(char not in "0123456789abcdef" for char in recovery_id):
        raise DeliveryWorkerExclusionRequiredError
    if name not in {"intent", "evidence", "receipt"}:
        raise DeliveryWorkerExclusionRequiredError
    return Path("changes") / change_id / "recovery-receipts" / recovery_id / f"{name}.json"


def publish_record(root: Path, path: Path, model: BaseModel) -> None:
    """Publish immutable authority using the existing durable transaction owner."""
    RuntimeTransaction(
        root, f"recovery-{digest(str(path).encode())}", (TransactionParticipant(root, path, encoded(model)),)
    ).commit()


def read_record(root: Path, relative: Path) -> bytes:
    """Read only bounded contained recovery metadata, never a symlink target."""
    path = root / relative
    if relative.is_absolute() or root.resolve() not in path.resolve().parents:
        raise DeliveryWorkerExclusionRequiredError
    if any((root / Path(*relative.parts[:index])).is_symlink() for index in range(1, len(relative.parts) + 1)):
        raise DeliveryWorkerExclusionRequiredError
    with path.open("rb") as stream:
        content = stream.read(_MAX_RECORD_BYTES + 1)
    if len(content) > _MAX_RECORD_BYTES:
        raise DeliveryWorkerExclusionRequiredError
    return content


def verify_evidence(
    provider: RecoveryEvidenceProvider, reference: RecoveryEvidenceReference, intent: RecoveryIntent
) -> RecoveryEvidence:
    """Validate the configured owner's response, never deserialize a caller's proof."""
    try:
        evidence = provider.verify(reference, intent)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeliveryWorkerExclusionRequiredError from exc
    if (
        not isinstance(evidence, RecoveryEvidence)
        or evidence.reference != reference
        or evidence.recovery_id != intent.recovery_id
        or evidence.invocation != intent.invocation
        or evidence.scope != "invocation-all-descendants-all-tool-jobs"
        or evidence.status not in {"closed", "excluded"}
    ):
        raise DeliveryWorkerExclusionRequiredError
    return evidence


class DeliveryWorkerExclusionRequiredError(RuntimeError):
    """Custody cannot be released without exact host-owned exclusion evidence."""

    code = "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            "Custody and files are unchanged. Recovery requires supported worker exclusion "
            "covering the invocation, all descendant writers and outstanding tool jobs, with "
            "no ability to resume, or restart-durable exclusion from every managed filesystem, "
            "Git and mutation resource. Timeout and caller confirmation are not evidence."
        )
