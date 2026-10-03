"""Registry and capability gate for persisted Delivery record formats.

This module is a stdlib-only leaf: it imports no Delivery module, no Pydantic and no network or
Git client, so the controller can classify on-disk state before any typed read or write.
"""

from __future__ import annotations

import errno
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator

type Mutability = Literal["M", "R", "H", "O", "T", "L"]
type CapabilityStatus = Literal[
    "current",
    "readable-legacy",
    "migration-required",
    "newer",
    "unknown-version",
    "unrecognized",
    "unreadable",
    "historical",
    "opaque",
    "transient",
]
type RefusalCode = Literal[
    "state-newer-than-controller",
    "state-version-unknown",
    "state-migration-required",
    "state-migration-incomplete",
]

DELIVERY_STATE_ROOT: Final = ".owlbear/delivery"
FORMAT_MARKER: Final = "runtime/format.json"
MIGRATIONS_ROOT: Final = "runtime/migrations"
CONTROLLER_LOCK: Final = "runtime/controller.lock"
SUPPORTED_FORMAT: Final = 0
MAX_ENTRIES: Final = 200_000
MAX_DEPTH: Final = 24
MAX_RECORD_BYTES: Final = 64 << 20
MAX_TOTAL_BYTES: Final = 2 << 30

_C = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_D = r"[0-9a-f]{64}"
_N = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}"
_OUT = r"OUT-[0-9]{3}"
_OP = r"continue-[0-9a-f]{64}"
_CH = rf"runtime/changes/{_C}"
_PRESERVATION = rf"{_CH}/recovery-receipts/{_D}/preservation"
_PULL_REQUESTS = "runtime/publications/pull-requests"


@dataclass(frozen=True, slots=True)
class RecordKind:
    """One persisted record shape: its path, owner models, mutability and accepted versions.

    ``current`` is ``None`` for unversioned records: they must not carry ``schema_version`` and
    are covered by the workspace format marker. ``read_upcasts`` names the owner function that
    turns each accepted legacy version into the current model without rewriting stored bytes.
    ``envelope`` names the key under which a dict-backed record embeds its owner model.
    """

    kind_id: str
    family_id: str
    pattern: str
    owners: tuple[str, ...]
    mutability: Mutability
    current: int | None
    read_upcasts: tuple[tuple[int, str], ...] = ()
    rewrites: tuple[tuple[int, str], ...] = ()
    implicit_version: int | None = None
    allow_empty: bool = False
    read: bool = True
    envelope: str | None = None

    @property
    def read_versions(self) -> tuple[int, ...]:
        """Return every accepted on-disk version, current last."""
        legacy = tuple(version for version, _owner in self.read_upcasts)
        return (*legacy, self.current) if self.current is not None else ()


def _kind(  # noqa: PLR0913, PLR0917 - registry rows bind every format attribute explicitly.
    kind_id: str,
    family_id: str,
    pattern: str,
    owners: tuple[str, ...],
    mutability: Mutability,
    current: int | None,
    **options: object,
) -> RecordKind:
    return RecordKind(kind_id, family_id, pattern, owners, mutability, current, **options)  # type: ignore[arg-type]


_LOADER = "owlbear_delivery.delivery_application_loader"
_RUNTIME_MODELS = "owlbear_delivery.runtime_models"
_RUNTIME_RECEIPTS = "owlbear_delivery.runtime_receipts"
_RECOVERY = "owlbear_delivery.recovery"
_DRAFT = "owlbear_delivery.draft_pull_request"
_WORKSPACE = "owlbear_delivery.workspace_models"
_REPORTS = "owlbear_delivery.finalization_reports"

RECORD_KINDS: Final[tuple[RecordKind, ...]] = (
    _kind("config", "config", r"config\.json", (f"{_LOADER}:DeliveryStartupConfig",), "T", 2),
    _kind("host", "host", r"runtime/host\.json", (f"{_LOADER}:DeliveryHostConfig",), "T", 1),
    _kind(
        "host_local",
        "host_local",
        r"runtime/host\.local\.json",
        (f"{_LOADER}:_DeliveryHostConfigOverrides",),
        "M",
        1,
        implicit_version=1,
    ),
    _kind(
        "coordination",
        "coordination",
        rf"runtime/coordination/changes/{_C}\.json",
        (f"{_WORKSPACE}:ChangeCoordination",),
        "M",
        1,
    ),
    _kind(
        "frontier",
        "frontier",
        rf"{_CH}/frontier\.json",
        (f"{_RUNTIME_MODELS}:DeliveryFrontier",),
        "M",
        18,
        read_upcasts=((17, "owlbear_delivery.runtime_support:parse_delivery_frontier"),),
    ),
    _kind(
        "contract", "contract", rf"{_CH}/contract\.json", ("owlbear_delivery.target_contract:DeliveryContract",), "R", 2
    ),
    _kind(
        "admission",
        "admission",
        rf"{_CH}/admission\.json",
        ("owlbear_delivery.delivery_admission:DeliveryAdmissionReceipt",),
        "R",
        1,
    ),
    _kind(
        "state_publication",
        "state_publication",
        rf"{_CH}/state-publication\.json",
        (f"{_RUNTIME_MODELS}:DeliveryPendingStatePublication",),
        "M",
        1,
    ),
    _kind(
        "revision_record",
        "revision_record",
        rf"{_CH}/revisions/{_D}/(?:contract|frontier|admission)\.json",
        (),
        "H",
        None,
        read=False,
    ),
    _kind(
        "result_receipt",
        "result_receipt",
        rf"{_CH}/result-receipts/{_OUT}/{_D}\.json",
        (f"{_RUNTIME_MODELS}:DeliveryResultCandidate",),
        "R",
        None,
    ),
    _kind(
        "action_receipt",
        "action_receipt",
        rf"{_CH}/action-receipts/{_OP}/(?:intent|started|result)\.json",
        (
            f"{_WORKSPACE}:ChangeContinuationAction",
            "owlbear_delivery.application_models:DeliveryEngineActionResult",
        ),
        "R",
        None,
    ),
    _kind(
        "recovery_invocation",
        "recovery",
        rf"{_CH}/invocations/{_D}\.json",
        (f"{_RECOVERY}:RecoveryInvocation",),
        "R",
        1,
    ),
    _kind(
        "recovery_record",
        "recovery",
        rf"{_CH}/recovery-receipts/{_D}/(?:intent|evidence|receipt)\.json",
        (
            f"{_RECOVERY}:RecoveryIntent",
            f"{_RECOVERY}:RecoveryEvidence",
            f"{_RECOVERY}:RecoveryReceipt",
            f"{_RUNTIME_MODELS}:CompletedOutcomeRepairReceipt",
        ),
        "R",
        1,
    ),
    _kind(
        "preservation_manifest",
        "preservation",
        rf"{_PRESERVATION}/manifest\.json",
        (f"{_WORKSPACE}:WorktreePreservationReceipt",),
        "R",
        1,
        envelope="receipt",
    ),
    _kind("preservation_object", "preservation", rf"{_PRESERVATION}/objects/{_D}\.raw", (), "O", None, read=False),
    _kind(
        "restoration_record",
        "preservation",
        rf"{_PRESERVATION}/restoration/{_D}/"
        rf"(?:(?:intent|result|failure)\.json|paths/{_D}/(?:intent|result|staging)\.json)",
        (),
        "R",
        1,
    ),
    _kind(
        "restoration_stage",
        "preservation",
        rf"{_PRESERVATION}/restoration/{_D}/paths/{_D}/stage-[0-9a-f]{{32}}(?:/.*)?",
        (),
        "O",
        None,
        read=False,
    ),
    _kind("retry_ledger", "retry", rf"{_CH}/retry-ledger/current\.json", (f"{_RECOVERY}:RetryLedgerSummary",), "M", 1),
    _kind("retry_attempt", "retry", rf"{_CH}/retry-ledger/attempts/{_N}\.json", (f"{_RECOVERY}:RetryAttempt",), "R", 1),
    _kind(
        "retry_outcome",
        "retry",
        rf"{_CH}/retry-ledger/outcomes/{_D}\.json",
        (f"{_RECOVERY}:RetryAttemptOutcome",),
        "R",
        1,
    ),
    _kind(
        "retry_repair_binding",
        "retry",
        rf"{_CH}/retry-ledger/repair-bindings/{_D}\.json",
        (f"{_RECOVERY}:RetryRepairBinding",),
        "R",
        1,
    ),
    _kind(
        "retry_owner_result",
        "retry",
        rf"{_CH}/retry-ledger/owner-results/{_N}\.json",
        (f"{_RECOVERY}:RetryOwnerResult",),
        "R",
        1,
    ),
    _kind(
        "planning_pause_receipt",
        "planning",
        rf"{_CH}/planning-pause-receipts/{_OUT}/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryPlanningPauseReplay",),
        "R",
        1,
    ),
    _kind(
        "planning_retry_receipt",
        "planning",
        rf"{_CH}/planning-retry-receipts/{_OUT}/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryPlanningRetrySettlementReceipt",),
        "R",
        1,
    ),
    _kind(
        "builder_invocation_receipt",
        "builder",
        rf"{_CH}/builder-invocation-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderInvocationSettlementReceipt",),
        "R",
        1,
    ),
    _kind(
        "builder_plan_promotion_receipt",
        "builder",
        rf"{_CH}/builder-plan-promotion-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderPlanPromotionReceipt",),
        "R",
        1,
    ),
    _kind(
        "builder_request_resolution_receipt",
        "builder",
        rf"{_CH}/builder-request-resolution-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderRequestResolutionReceipt",),
        "R",
        1,
    ),
    _kind(
        "builder_handoff_change_intent_head",
        "builder",
        rf"{_CH}/builder-handoff-change-intent-receipts/{_D}/head\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderHandoffChangeIntentHead",),
        "M",
        1,
    ),
    _kind(
        "builder_handoff_change_intent_receipt",
        "builder",
        rf"{_CH}/builder-handoff-change-intent-receipts/{_D}/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderHandoffChangeIntentReceipt",),
        "R",
        1,
    ),
    _kind(
        "claim_issuer",
        "claim_issuer",
        rf"{_CH}/claim-issuers/[A-Za-z0-9][A-Za-z0-9._-]{{0,127}}\.json",
        ("owlbear_delivery.worker_stall:DeliveryClaimIssuer",),
        "R",
        1,
    ),
    _kind(
        "finalization_report",
        "finalization_report",
        rf"runtime/finalization-reports/{_C}/reports/{_N}\.json",
        (f"{_REPORTS}:FinalizationReport",),
        "R",
        None,
    ),
    _kind(
        "finalization_report_pointer",
        "finalization_report",
        rf"runtime/finalization-reports/{_C}/current\.json",
        (f"{_REPORTS}:_CurrentReport",),
        "M",
        None,
    ),
    _kind(
        "proof_attempt",
        "proof_attempt",
        rf"runtime/proof-attempts/{_C}/attempts/{_N}\.json",
        (f"{_REPORTS}:ProofAttempt",),
        "R",
        None,
    ),
    _kind(
        "finalizer_settlement",
        "finalizer_settlement",
        rf"runtime/finalizer-settlements/{_C}/{_D}\.json",
        (f"{_REPORTS}:FinalizerSettlementReceipt",),
        "R",
        1,
    ),
    _kind(
        "completion_evidence",
        "completion",
        rf"runtime/completions/{_C}/{_D}\.json",
        ("owlbear_delivery.acceptance:CompletionReceipt",),
        "R",
        1,
    ),
    _kind(
        "completion_display",
        "completion",
        rf"runtime/completions/{_C}/display\.json",
        ("owlbear_delivery.acceptance:CompletionDisplayMetadata",),
        "R",
        1,
    ),
    _kind(
        "branch_publication",
        "branch_publication",
        rf"runtime/publications/change-branches/operations/{_D}\.json",
        (
            "owlbear_delivery.change_publication:_PublicationOperation",
            "owlbear_delivery.change_publication:_SupersessionOperation",
        ),
        "R",
        1,
    ),
    _kind(
        "pull_request_operation",
        "pull_request_publication",
        rf"{_PULL_REQUESTS}/operations/{_N}\.json",
        (f"{_DRAFT}:_DraftPullRequestOperation",),
        "R",
        1,
    ),
    _kind(
        "pull_request_supersession_operation",
        "pull_request_publication",
        rf"{_PULL_REQUESTS}/supersession-operations/{_N}\.json",
        (f"{_DRAFT}:_DraftPullRequestSupersessionOperation",),
        "R",
        1,
    ),
    _kind(
        "pull_request_summary_operation",
        "pull_request_publication",
        rf"{_PULL_REQUESTS}/summary-operations/{_N}\.json",
        (f"{_DRAFT}:_GeneratedSummaryOperation",),
        "R",
        1,
    ),
    _kind(
        "pull_request_draft_state_operation",
        "pull_request_publication",
        rf"{_PULL_REQUESTS}/draft-state-operations/{_N}\.json",
        (f"{_DRAFT}:_DraftStateOperation",),
        "R",
        1,
    ),
    _kind(
        "pull_request_supersession_receipt",
        "pull_request_receipt",
        rf"{_PULL_REQUESTS}/supersession-receipts/{_N}\.json",
        (f"{_DRAFT}:DraftPullRequestSupersessionReceipt",),
        "R",
        1,
    ),
    _kind(
        "pull_request_summary_receipt",
        "pull_request_receipt",
        rf"{_PULL_REQUESTS}/summary-receipts/{_N}\.json",
        (f"{_DRAFT}:GeneratedPullRequestSummaryReceipt",),
        "R",
        1,
    ),
    _kind(
        "pull_request_draft_state_receipt",
        "pull_request_receipt",
        rf"{_PULL_REQUESTS}/draft-state-receipts/{_N}\.json",
        (
            f"{_DRAFT}:_PullRequestDraftStateReceipt",
            f"{_DRAFT}:PullRequestReadyReceipt",
            f"{_DRAFT}:PullRequestDraftReceipt",
        ),
        "R",
        1,
    ),
    _kind(
        "pull_request_current_receipt",
        "pull_request_current",
        rf"{_PULL_REQUESTS}/receipts/{_C}\.json",
        (f"{_DRAFT}:DraftPullRequestPublicationReceipt",),
        "M",
        1,
    ),
    _kind(
        "pull_request_publication_history",
        "pull_request_current",
        rf"{_PULL_REQUESTS}/publication-history/{_C}\.json",
        (f"{_DRAFT}:DraftPullRequestPublicationHistory",),
        "M",
        1,
    ),
    _kind(
        "pull_request_check_observation",
        "pull_request_observation",
        rf"{_PULL_REQUESTS}/check-observations/{_C}/{_D}\.json",
        (f"{_DRAFT}:PublicationCheckObservationReceipt",),
        "R",
        1,
    ),
    _kind(
        "pull_request_observation",
        "pull_request_observation",
        rf"{_PULL_REQUESTS}/pull-request-observations/{_C}/{_D}\.json",
        (f"{_DRAFT}:PublicationPullRequestObservationReceipt",),
        "R",
        1,
    ),
    _kind(
        "acceptance_cursor",
        "acceptance_cursor",
        r"runtime/claims/acceptance-reconciliation/cursor\.json",
        ("owlbear_delivery.application_models:_AcceptanceReconciliationCursor",),
        "M",
        1,
    ),
    _kind(
        "package_manifest",
        "package",
        rf"packages/{_C}/manifest\.json",
        ("owlbear_delivery.design_package:DesignPackageManifest",),
        "T",
        1,
    ),
    _kind(
        "package_authority",
        "package",
        rf"packages/{_C}/authority\.json",
        ("owlbear_delivery.target_contract:DeliveryContract",),
        "R",
        2,
        allow_empty=True,
    ),
    _kind("package_document", "package", rf"packages/{_C}/(?:intent|design)\.md", (), "T", None, read=False),
    _kind(
        "snapshot",
        "snapshot",
        rf"state/{_C}/snapshot\.json",
        ("owlbear_delivery.delivery_state:DeliveryStateSnapshot",),
        "R",
        2,
        read_upcasts=((1, "owlbear_delivery.delivery_state:parse_delivery_state_snapshot"),),
    ),
    _kind(
        "lock",
        "locks",
        r"(?:.*/)?\.storage\.lock|runtime/controller\.lock"
        r"|runtime/claims/(?!acceptance-reconciliation(?:/|$)).*"
        r"|runtime/coordination/target-sync-lock(?:/.*)?"
        r"|runtime/publications/(?:pull-requests|checkpoints)/locks(?:/.*)?",
        (),
        "L",
        None,
        read=False,
    ),
    _kind(
        "transaction",
        "transaction",
        r"(?:.*/)?transactions(?:/.*)?|(?:.*/)?\.tmp-[^/]*(?:/.*)?|runtime/logs(?:/.*)?",
        (),
        "L",
        None,
        read=False,
    ),
)

# Remote-only record, read through Git rather than the local tree.
REMOTE_SNAPSHOT_CURRENT: Final = 2
REMOTE_SNAPSHOT_READ_VERSIONS: Final = (1, 2)

# Models with ``schema_version`` persisted only inside, or as the base of, a registered owner record.
NESTED_MODELS: Final[dict[str, str]] = {
    "owlbear_delivery.acceptance:CompletionEvidence": "completion",
    "owlbear_delivery.change_publication:ChangeBranchPublicationReceipt": "action_receipt",
    f"{_WORKSPACE}:_ChangeWorktreeCleanupRecord": "coordination",
    f"{_WORKSPACE}:ChangeWorktreeCleanup": "coordination",
    f"{_WORKSPACE}:ChangeWorktreeCleanupIntent": "coordination",
    f"{_WORKSPACE}:ChangeExternalHeadAdoptionIntent": "coordination",
    f"{_WORKSPACE}:PublicationBaselineRecoveryReceipt": "coordination",
    f"{_WORKSPACE}:OutOfBandHeadRecoveryReceipt": "coordination",
    f"{_WORKSPACE}:ChangeTargetSyncReceipt": "coordination",
    f"{_WORKSPACE}:ChangeTargetSyncConflictState": "coordination",
    f"{_WORKSPACE}:ChangeTargetSyncAbortReceipt": "coordination",
    f"{_WORKSPACE}:ChangeExternalHeadAdoptionReceipt": "coordination",
    f"{_WORKSPACE}:ChangeExternalHeadPromotionReceipt": "coordination",
    f"{_WORKSPACE}:ChangeDesignPackageSnapshotIntent": "coordination",
    f"{_WORKSPACE}:ChangeDesignPackageSnapshotReceipt": "coordination",
    f"{_WORKSPACE}:DirtyWorktreeQuarantineReceipt": "coordination",
    f"{_RUNTIME_MODELS}:DeliveryChangePublicationIdentity": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryChangePublicationHistory": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryChangeDeferral": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryChangeAbandonment": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryObservation": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryObservationReceipt": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryReview": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryReviewReceipt": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryFinalization": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryFinalizationReceipt": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryFinalizationInvalidation": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryFinalizationInvalidationReceipt": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryMergedPullRequestLatch": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryChangeDisposition": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryChangeDispositionResolution": "frontier",
    f"{_RECOVERY}:RetryEpisodeKey": "retry",
    f"{_DRAFT}:_PublicationCheckObservationPayload": "pull_request_observation",
    f"{_DRAFT}:_PublicationPullRequestObservationPayload": "pull_request_observation",
}

# Models with ``schema_version`` that are API results or in-memory values, never stored as records.
NON_PERSISTED_MODELS: Final[frozenset[str]] = frozenset(
    {
        "owlbear_delivery.application_models:DeliveryTargetSyncRepairReceipt",
        "owlbear_delivery.application_models:DeliveryStateSnapshotRepairReceipt",
        "owlbear_delivery.application_models:DeliveryStrandedFrontierRepairReceipt",
        "owlbear_delivery.application_models:DeliveryQuarantinedSnapshotRepairReceipt",
        "owlbear_delivery.application_models:DeliveryChangePublicationSupersessionReceipt",
        "owlbear_delivery.change_publication:ChangeBranchSupersessionReceipt",
        "owlbear_delivery.completed_history:_CompletedChangeRecordBase",
        "owlbear_delivery.completed_history:AbandonedChangeRecord",
        "owlbear_delivery.completed_history:ReceiptCompletedChangeRecord",
        "owlbear_delivery.completed_history:_Cursor",
        "owlbear_delivery.delivery_state:DeliveryStatePublicationReceipt",
        f"{_WORKSPACE}:CapacityLedger",
    }
)

_REFUSAL_BY_STATUS: Final[dict[str, RefusalCode]] = {
    "newer": "state-newer-than-controller",
    "unknown-version": "state-version-unknown",
    "migration-required": "state-migration-required",
}
_COMPILED: Final = tuple((kind, re.compile(kind.pattern)) for kind in RECORD_KINDS)
_SKIP_DIRECTORIES: Final = frozenset({"worktrees"})
_DIRECTORY_FLAGS: Final = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS: Final = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def _families() -> dict[str, tuple[RecordKind, ...]]:
    families: dict[str, list[RecordKind]] = {}
    for kind in RECORD_KINDS:
        families.setdefault(kind.family_id, []).append(kind)
    return {family_id: tuple(kinds) for family_id, kinds in families.items()}


FAMILIES: Final[dict[str, tuple[RecordKind, ...]]] = _families()


@dataclass(frozen=True, slots=True)
class RecordCapability:
    """Classification of one on-disk record; ``locator`` is relative to the Delivery root."""

    kind_id: str | None
    locator: str
    status: CapabilityStatus
    version: int | None = None


@dataclass(frozen=True, slots=True)
class CapabilityRefusal:
    """First reason this controller must not read or write the scanned workspace."""

    code: RefusalCode
    locator: str
    detail: str


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Bounded, write-free classification of one workspace's Delivery records."""

    records: tuple[RecordCapability, ...] = ()
    format: int = SUPPORTED_FORMAT
    format_status: CapabilityStatus = "current"
    migration_journals: tuple[str, ...] = ()
    complete: bool = True
    incomplete_detail: str | None = None

    @property
    def refusals(self) -> tuple[CapabilityRefusal, ...]:
        """Return every refusal in deterministic priority order."""
        refusals = [
            CapabilityRefusal(
                "state-migration-incomplete",
                locator,
                "a Delivery migration journal exists; only the migration tool may continue it",
            )
            for locator in self.migration_journals
        ]
        if self.format_status != "current":
            refusals.append(
                CapabilityRefusal(
                    _REFUSAL_BY_STATUS.get(self.format_status, "state-version-unknown"),
                    FORMAT_MARKER,
                    f"Delivery state format {self.format} is not supported by this controller "
                    f"(supported: {SUPPORTED_FORMAT})",
                )
            )
        if not self.complete:
            refusals.append(
                CapabilityRefusal(
                    "state-version-unknown",
                    ".",
                    self.incomplete_detail or "Delivery state could not be classified completely",
                )
            )
        refusals.extend(
            CapabilityRefusal(
                _REFUSAL_BY_STATUS[record.status],
                record.locator,
                _record_refusal_detail(record),
            )
            for record in self.records
            if record.status in _REFUSAL_BY_STATUS
        )
        return tuple(refusals)


class StateCapabilityError(RuntimeError):
    """Persisted Delivery state is outside this controller's supported formats."""

    __slots__ = ("code", "detail", "locator")

    def __init__(self, refusal: CapabilityRefusal) -> None:
        self.code: RefusalCode = refusal.code
        self.locator = refusal.locator
        self.detail = f"{refusal.code}: {refusal.detail} ({DELIVERY_STATE_ROOT}/{refusal.locator})"
        super().__init__(self.detail)


def _record_refusal_detail(record: RecordCapability) -> str:
    kind = next((item for item in RECORD_KINDS if item.kind_id == record.kind_id), None)
    accepted = ", ".join(str(version) for version in kind.read_versions) if kind is not None else "none"
    shown = "absent" if record.version is None else str(record.version)
    return f"{record.kind_id} schema_version {shown} is not supported (accepted: {accepted or 'unversioned'})"


def require_capability(report: CapabilityReport) -> None:
    """Raise the first refusal so no typed read or write runs on unsupported state."""
    refusals = report.refusals
    if refusals:
        raise StateCapabilityError(refusals[0])


def classify_kind(locator: str) -> RecordKind | None:
    """Return the registered record kind for one Delivery-root-relative POSIX path."""
    for kind, pattern in _COMPILED:
        if pattern.fullmatch(locator) is not None:
            return kind
    return None


def classify_version(kind: RecordKind, version: object, *, present: bool) -> CapabilityStatus:
    """Classify one raw ``schema_version`` value for a registered record kind."""
    if kind.current is None:
        return "current" if not present else "unknown-version"
    if not present and kind.implicit_version is not None:
        version = kind.implicit_version
    elif not present or isinstance(version, bool) or not isinstance(version, int):
        return "unreadable"
    if version == kind.current:
        return "current"
    if version in dict(kind.read_upcasts):
        return "readable-legacy"
    if version in dict(kind.rewrites):
        return "migration-required"
    return "newer" if version > kind.current else "unknown-version"


def classify_record_bytes(kind: RecordKind, content: bytes) -> tuple[CapabilityStatus, int | None]:
    """Classify raw record bytes by their top-level ``schema_version`` only."""
    if kind.allow_empty and not content:
        return "current", None
    try:
        payload = json.loads(content)
    except UnicodeDecodeError, RecursionError, ValueError:
        return "unreadable", None
    if not isinstance(payload, dict):
        return "unreadable", None
    present = "schema_version" in payload
    version = payload.get("schema_version")
    status = classify_version(kind, version, present=present)
    reported = version if isinstance(version, int) and not isinstance(version, bool) else None
    if not present and kind.implicit_version is not None:
        reported = kind.implicit_version
    return status, reported


def config_capability(content: bytes) -> CapabilityReport:
    """Classify raw startup configuration bytes before any typed configuration parse."""
    kind = classify_kind("config.json")
    if kind is None:  # pragma: no cover - the registry always names the configuration record.
        raise AssertionError
    status, version = classify_record_bytes(kind, content)
    return CapabilityReport(records=(RecordCapability(kind.kind_id, "config.json", status, version),))


@dataclass
class _Scan:
    records: list[RecordCapability] = field(default_factory=list)
    journals: list[str] = field(default_factory=list)
    entries: int = 0
    total_bytes: int = 0
    incomplete_detail: str | None = None
    format: int = SUPPORTED_FORMAT
    format_status: CapabilityStatus = "current"

    def charge(self) -> bool:
        self.entries += 1
        if self.entries > MAX_ENTRIES:
            self.incomplete_detail = f"Delivery state exceeds the {MAX_ENTRIES}-entry capability scan bound"
            return False
        return True


def scan_capability(workspace_root: Path) -> CapabilityReport:
    """Classify every registered record under the workspace's Delivery root without writing."""
    scan = _Scan()
    root = workspace_root / DELIVERY_STATE_ROOT
    try:
        root_fd = os.open(root, _DIRECTORY_FLAGS)
    except FileNotFoundError:
        return CapabilityReport()
    except OSError as exc:
        detail = "Delivery state root is a symlink" if exc.errno == errno.ELOOP else "Delivery state root is unreadable"
        return CapabilityReport(complete=False, incomplete_detail=detail)
    try:
        _walk(root_fd, "", 0, scan)
    finally:
        os.close(root_fd)
    return CapabilityReport(
        records=tuple(sorted(scan.records, key=lambda record: record.locator)),
        format=scan.format,
        format_status=scan.format_status,
        migration_journals=tuple(sorted(scan.journals)),
        complete=scan.incomplete_detail is None,
        incomplete_detail=scan.incomplete_detail,
    )


def _entries(directory_fd: int) -> Iterator[os.DirEntry[str]]:
    with os.scandir(directory_fd) as entries:
        yield from sorted(entries, key=lambda entry: entry.name)


def _walk(directory_fd: int, prefix: str, depth: int, scan: _Scan) -> None:
    if depth > MAX_DEPTH:
        scan.incomplete_detail = f"Delivery state exceeds the {MAX_DEPTH}-level capability scan depth"
        return
    for entry in _entries(directory_fd):
        if scan.incomplete_detail is not None or not scan.charge():
            return
        locator = f"{prefix}{entry.name}"
        if locator == MIGRATIONS_ROOT:
            scan.journals.append(locator)
        elif prefix or entry.name not in _SKIP_DIRECTORIES:
            _classify_entry(directory_fd, entry, locator, depth, scan)


def _classify_entry(directory_fd: int, entry: os.DirEntry[str], locator: str, depth: int, scan: _Scan) -> None:
    kind = classify_kind(locator)
    if entry.is_dir(follow_symlinks=False):
        if kind is not None and not kind.read:
            scan.records.append(RecordCapability(kind.kind_id, locator, _passive_status(kind)))
        else:
            _walk_child(directory_fd, entry.name, locator, depth, scan)
    elif locator == FORMAT_MARKER:
        _read_format_marker(directory_fd, entry.name, scan)
    elif kind is None:
        scan.records.append(RecordCapability(None, "<unrecognized>", "unrecognized"))
    elif not kind.read:
        scan.records.append(RecordCapability(kind.kind_id, locator, _passive_status(kind)))
    else:
        content = _read_record(directory_fd, entry.name, scan)
        if content is None:
            status: CapabilityStatus = "unknown-version" if scan.incomplete_detail else "unreadable"
            scan.records.append(RecordCapability(kind.kind_id, locator, status))
            return
        status, version = classify_record_bytes(kind, content)
        scan.records.append(RecordCapability(kind.kind_id, locator, status, version))


def _passive_status(kind: RecordKind) -> CapabilityStatus:
    return {"H": "historical", "O": "opaque"}.get(kind.mutability, "transient")  # type: ignore[return-value]


def _walk_child(parent_fd: int, name: str, locator: str, depth: int, scan: _Scan) -> None:
    try:
        child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError:
        scan.records.append(RecordCapability(None, locator, "unreadable"))
        return
    try:
        _walk(child_fd, f"{locator}/", depth + 1, scan)
    finally:
        os.close(child_fd)


def _read_record(parent_fd: int, name: str, scan: _Scan) -> bytes | None:
    try:
        fd = os.open(name, _FILE_FLAGS, dir_fd=parent_fd)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None
        size = int(info.st_size)
        if size > MAX_RECORD_BYTES or scan.total_bytes + size > MAX_TOTAL_BYTES:
            scan.incomplete_detail = "Delivery state exceeds the capability scan byte bound"
            return None
        chunks = []
        remaining = size + 1
        while remaining > 0:
            chunk = os.read(fd, min(1 << 20, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        scan.total_bytes += len(content)
        return None if len(content) > size else content
    except OSError:
        return None
    finally:
        os.close(fd)


def _read_format_marker(parent_fd: int, name: str, scan: _Scan) -> None:
    content = _read_record(parent_fd, name, scan)
    payload: object = None
    if content is not None:
        try:
            payload = json.loads(content)
        except UnicodeDecodeError, RecursionError, ValueError:
            payload = None
    value = payload.get("format") if isinstance(payload, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        scan.format_status = "unknown-version"
        return
    scan.format = value
    if value > SUPPORTED_FORMAT:
        scan.format_status = "newer"
    elif value < SUPPORTED_FORMAT:  # pragma: no cover - format 0 is the lowest format.
        scan.format_status = "unknown-version"


def record_tree_digest(workspace_root: Path) -> dict[str, str]:
    """Return SHA-256 digests of every non-transient Delivery record file, for no-write proofs."""
    import hashlib  # noqa: PLC0415 - proof helper only.

    root = workspace_root / DELIVERY_STATE_ROOT
    digests: dict[str, str] = {}
    if not root.is_dir():
        return digests
    for directory, directory_names, file_names in os.walk(root):
        relative_directory = os.path.relpath(directory, root)
        prefix = "" if relative_directory == "." else f"{relative_directory.replace(os.sep, '/')}/"
        if not prefix:
            directory_names[:] = [name for name in directory_names if name not in _SKIP_DIRECTORIES]
        for name in file_names:
            locator = f"{prefix}{name}"
            kind = classify_kind(locator)
            if kind is not None and kind.mutability == "L":
                continue
            path = os.path.join(directory, name)  # noqa: PTH118 - os.walk yields string paths.
            if os.path.islink(path):  # noqa: PTH114 - os.walk yields string paths.
                digests[locator] = f"symlink:{Path(path).readlink()}"
                continue
            with open(path, "rb") as handle:  # noqa: PTH123 - os.walk yields string paths.
                digests[locator] = hashlib.sha256(handle.read()).hexdigest()
    return digests


__all__ = [
    "CONTROLLER_LOCK",
    "DELIVERY_STATE_ROOT",
    "FAMILIES",
    "FORMAT_MARKER",
    "MIGRATIONS_ROOT",
    "NESTED_MODELS",
    "NON_PERSISTED_MODELS",
    "RECORD_KINDS",
    "REMOTE_SNAPSHOT_CURRENT",
    "REMOTE_SNAPSHOT_READ_VERSIONS",
    "SUPPORTED_FORMAT",
    "CapabilityRefusal",
    "CapabilityReport",
    "RecordCapability",
    "RecordKind",
    "StateCapabilityError",
    "classify_kind",
    "classify_record_bytes",
    "classify_version",
    "config_capability",
    "record_tree_digest",
    "require_capability",
    "scan_capability",
]
