"""Registry and capability gate for persisted Delivery record formats.

This module is a stdlib-only leaf: it imports no Delivery module, no Pydantic and no network or
Git client, so the controller can classify on-disk state before any typed read or write.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

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
MIGRATION_JOURNAL: Final = "journal.json"
CONTROLLER_LOCK: Final = "runtime/controller.lock"
CONTROLLER_PROCESSES_ROOT: Final = "runtime/controller-processes"
# Pinned controller releases live beside, not inside, Delivery state (N02 D1, I6).
CONTROLLER_ROOT: Final = ".owlbear/controller"
CONTROLLER_PIN: Final = ".owlbear/controller/pin.json"
CONTROLLER_RELEASES: Final = ".owlbear/controller/releases"
PIN_SCHEMA_VERSION: Final = 1
_PIN_KEYS: Final = frozenset({"schema_version", "commit", "previous", "pinned_at", "release_sha256"})
_MAX_PIN_BYTES: Final = 4096
_COMMIT: Final = re.compile(r"[0-9a-f]{40}")
_SHA256: Final = re.compile(r"[0-9a-f]{64}")
_LAUNCHER_HINT: Final = (
    "start Delivery through .owlbear/controller/bin/delivery-mcp or .owlbear/controller/bin/cockpit, "
    "or change the pin with delivery-controller switch"
)
SUPPORTED_FORMAT: Final = 3
# Registered format migrations in order (name, source, target); a copy runs every step from its observed
# format. format-0-to-1 (N02-B): registered record rewrites and marker 1; format-1-to-2 (N03-A) and
# format-2-to-3 (N05-B2, merge attempts an older controller must not act on): marker only.
FORMAT_MIGRATIONS: Final[tuple[tuple[str, int, int], ...]] = (
    ("format-0-to-1", 0, 1),
    ("format-1-to-2", 1, 2),
    ("format-2-to-3", 2, 3),
)
# Version 2 journals carry an explicit operation ``kind`` (``repair``); migration journals keep
# version 1 bytes so every N02 release still reads retained migration history (N08 I3, D3).
JOURNAL_SCHEMA_VERSION: Final = 2
JOURNAL_READ_VERSIONS: Final = (1, 2)
JOURNAL_STATES: Final = frozenset({"backed-up", "applying", "applied", "verified", "aborting"})
# Runtime entries a fresh (never-written) workspace may hold besides locks and transients.
_FRESH_RUNTIME_LOCATORS: Final = frozenset({"runtime/host.json", "runtime/host.local.json", FORMAT_MARKER})
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
    Without ``implicit_version``, an absent or non-integer version of a versioned record is unknown.
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
    _kind(
        "config",
        "config",
        r"config\.json",
        (f"{_LOADER}:DeliveryStartupConfig",),
        "T",
        2,
    ),
    _kind(
        "host",
        "host",
        r"runtime/host\.json",
        (f"{_LOADER}:DeliveryHostConfig",),
        "T",
        1,
    ),
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
        2,
        rewrites=((1, "owlbear_delivery.state_migration:coordination_1_to_2"),),
    ),
    _kind(
        "frontier",
        "frontier",
        rf"{_CH}/frontier\.json",
        (f"{_RUNTIME_MODELS}:DeliveryFrontier",),
        "M",
        19,
        read_upcasts=((18, "owlbear_delivery.runtime_support:parse_delivery_frontier"),),
        rewrites=((17, "owlbear_delivery.state_migration:frontier_17_to_18"),),
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
        "direct_operation",
        "direct_operation",
        rf"{_CH}/action-receipts/direct-{_D}/(?:started|finished)\.json",
        (f"{_WORKSPACE}:ChangeDirectOperation",),
        "R",
        1,
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
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_planning_pause_receipt"),),
    ),
    _kind(
        "planning_retry_receipt",
        "planning",
        rf"{_CH}/planning-retry-receipts/{_OUT}/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryPlanningRetrySettlementReceipt",),
        "R",
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_planning_retry_receipt"),),
    ),
    _kind(
        "builder_invocation_receipt",
        "builder",
        rf"{_CH}/builder-invocation-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderInvocationSettlementReceipt",),
        "R",
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_builder_invocation_receipt"),),
    ),
    _kind(
        "builder_plan_promotion_receipt",
        "builder",
        rf"{_CH}/builder-plan-promotion-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderPlanPromotionReceipt",),
        "R",
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_builder_plan_promotion_receipt"),),
    ),
    _kind(
        "builder_request_resolution_receipt",
        "builder",
        rf"{_CH}/builder-request-resolution-receipts/{_D}\.json",
        (f"{_RUNTIME_RECEIPTS}:_DeliveryBuilderRequestResolutionReceipt",),
        "R",
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_builder_request_resolution_receipt"),),
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
        2,
        read_upcasts=((1, f"{_RUNTIME_RECEIPTS}:parse_builder_handoff_change_intent_receipt"),),
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
        "merge_attempt",
        "merge_attempt",
        rf"{_CH}/merge-attempts/{_D}\.json",
        ("owlbear_delivery.merge_approval:MergeAttemptRecord",),
        "M",
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
        3,
        read_upcasts=(
            (1, "owlbear_delivery.delivery_state:parse_delivery_state_snapshot"),
            (2, "owlbear_delivery.delivery_state:parse_delivery_state_snapshot"),
        ),
    ),
    _kind("format_marker", "format_marker", r"runtime/format\.json", (), "M", None, read=False),
    _kind(
        "migration_journal",
        "migration_journal",
        rf"runtime/migrations/{_D}/journal\.json",
        ("owlbear_delivery.state_migration:MigrationJournal",),
        "M",
        JOURNAL_SCHEMA_VERSION,
        read_upcasts=((1, "owlbear_delivery.state_migration:upcast_migration_journal_v1"),),
        read=False,
    ),
    _kind(
        "controller_process",
        "controller_process",
        rf"{CONTROLLER_PROCESSES_ROOT}(?:/.*)?",
        (),
        "L",
        None,
        read=False,
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
REMOTE_SNAPSHOT_CURRENT: Final = 3
REMOTE_SNAPSHOT_READ_VERSIONS: Final = (1, 2, 3)

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
    f"{_RUNTIME_MODELS}:DeliveryLegacyObservation": "frontier",
    f"{_RUNTIME_MODELS}:DeliveryLegacyObservationReceipt": "frontier",
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
_JOURNAL_TEMPORARY: Final = re.compile(r"\.tmp-[0-9a-f]{24}")
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
    version_absent: bool = False


@dataclass(frozen=True, slots=True)
class CapabilityRefusal:
    """First reason this controller must not read or write the scanned workspace."""

    code: RefusalCode
    locator: str
    detail: str
    version_absent: bool = False


@dataclass(frozen=True, slots=True)
class MigrationJournalState:
    """Raw state of one ``runtime/migrations`` entry; ``state`` is ``invalid`` when it is not a journal.

    ``kind`` is ``migration`` (version 1, ``delivery-migrate``) or ``repair`` (version 2, ``delivery-repair``).
    """

    locator: str
    migration_id: str | None
    state: str
    schema_version: int | None = None
    kind: str = "migration"

    @property
    def refusal(self) -> CapabilityRefusal | None:
        """Return why this journal blocks a normal start, or ``None`` for a verified journal."""
        if self.state == "verified":
            return None
        if self.schema_version is not None and self.schema_version > JOURNAL_SCHEMA_VERSION:
            detail = f"Delivery migration journal schema_version {self.schema_version} is newer than this controller"
            return CapabilityRefusal("state-newer-than-controller", self.locator, detail)
        tool = "delivery-repair" if self.kind == "repair" else "delivery-migrate"
        return CapabilityRefusal(
            "state-migration-incomplete",
            self.locator,
            f"Delivery {self.kind} journal is {self.state}; only {tool} may continue or abort it",
        )


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Bounded, write-free classification of one workspace's Delivery records.

    ``format_absent`` with a ``current`` format status marks a fresh workspace (no runtime record yet),
    which a controller stamps with the supported format before its first write.
    """

    records: tuple[RecordCapability, ...] = ()
    format: int = SUPPORTED_FORMAT
    format_status: CapabilityStatus = "current"
    format_absent: bool = False
    journals: tuple[MigrationJournalState, ...] = ()
    complete: bool = True
    incomplete_detail: str | None = None

    @property
    def migration_journals(self) -> tuple[str, ...]:
        """Return the locators of journals that block a normal start."""
        return tuple(journal.locator for journal in self.journals if journal.refusal is not None)

    @property
    def refusals(self) -> tuple[CapabilityRefusal, ...]:
        """Return every refusal in deterministic priority order; migration-required comes last."""
        refusals = [refusal for journal in self.journals if (refusal := journal.refusal) is not None]
        detail = (
            f"Delivery state format {self.format} requires the registered migration to format {SUPPORTED_FORMAT}"
            if self.format_status == "migration-required"
            else f"Delivery state format {self.format} is not supported by this controller "
            f"(supported: {SUPPORTED_FORMAT})"
        )
        format_refusal = CapabilityRefusal(
            _REFUSAL_BY_STATUS.get(self.format_status, "state-version-unknown"), FORMAT_MARKER, detail
        )
        if self.format_status not in {"current", "migration-required"}:
            refusals.append(format_refusal)
        if not self.complete:
            refusals.append(
                CapabilityRefusal(
                    "state-version-unknown",
                    ".",
                    self.incomplete_detail or "Delivery state could not be classified completely",
                )
            )
        record_refusals = [
            CapabilityRefusal(
                _REFUSAL_BY_STATUS[record.status],
                record.locator,
                _record_refusal_detail(record),
                version_absent=record.version_absent,
            )
            for record in self.records
            if record.status in _REFUSAL_BY_STATUS
        ]
        refusals.extend(refusal for refusal in record_refusals if refusal.code != "state-migration-required")
        if self.format_status == "migration-required" and self.complete:
            refusals.append(format_refusal)
        refusals.extend(refusal for refusal in record_refusals if refusal.code == "state-migration-required")
        return tuple(refusals)


class StateCapabilityError(RuntimeError):
    """Persisted Delivery state is outside this controller's supported formats."""

    __slots__ = ("code", "detail", "locator", "version_absent")

    def __init__(self, refusal: CapabilityRefusal) -> None:
        self.code: RefusalCode = refusal.code
        self.locator = refusal.locator
        self.version_absent = refusal.version_absent
        self.detail = f"{refusal.code}: {refusal.detail} ({DELIVERY_STATE_ROOT}/{refusal.locator})"
        super().__init__(self.detail)


def _record_refusal_detail(record: RecordCapability) -> str:
    kind = next((item for item in RECORD_KINDS if item.kind_id == record.kind_id), None)
    accepted = ", ".join(str(version) for version in kind.read_versions) if kind is not None else "none"
    shown = "absent" if record.version_absent else "not an integer" if record.version is None else str(record.version)
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
        return "unknown-version" if present else "current"
    if not present and kind.implicit_version is not None:
        return _classify_integer_version(kind, kind.implicit_version, kind.current)
    if not present or isinstance(version, bool) or not isinstance(version, int):
        return "unknown-version"
    return _classify_integer_version(kind, version, kind.current)


def _classify_integer_version(kind: RecordKind, version: int, current: int) -> CapabilityStatus:
    if version == current:
        return "current"
    if version in dict(kind.read_upcasts):
        return "readable-legacy"
    if version in dict(kind.rewrites):
        return "migration-required"
    return "newer" if version > current else "unknown-version"


def classify_record(kind: RecordKind, locator: str, content: bytes) -> RecordCapability:
    """Classify raw record bytes by their top-level ``schema_version`` only."""
    if kind.allow_empty and not content:
        return RecordCapability(kind.kind_id, locator, "current")
    try:
        payload = json.loads(content)
    except UnicodeDecodeError, RecursionError, ValueError:
        return RecordCapability(kind.kind_id, locator, "unreadable")
    if not isinstance(payload, dict):
        return RecordCapability(kind.kind_id, locator, "unreadable")
    present = "schema_version" in payload
    version = payload.get("schema_version")
    status = classify_version(kind, version, present=present)
    reported = version if isinstance(version, int) and not isinstance(version, bool) else None
    absent = not present and kind.current is not None
    if absent and kind.implicit_version is not None:
        reported, absent = kind.implicit_version, False
    return RecordCapability(kind.kind_id, locator, status, reported, version_absent=absent)


def config_capability(content: bytes) -> CapabilityReport:
    """Classify raw startup configuration bytes before any typed configuration parse."""
    kind = classify_kind("config.json")
    if kind is None:  # pragma: no cover - the registry always names the configuration record.
        raise AssertionError
    return CapabilityReport(records=(classify_record(kind, "config.json", content),))


@dataclass
class _Scan:
    records: list[RecordCapability] = field(default_factory=list)
    journals: list[MigrationJournalState] = field(default_factory=list)
    entries: int = 0
    total_bytes: int = 0
    incomplete_detail: str | None = None
    format: int | None = None
    format_status: CapabilityStatus = "current"
    marker_present: bool = False
    runtime_records: bool = False

    def charge(self) -> bool:
        self.entries += 1
        if self.entries > MAX_ENTRIES:
            self.incomplete_detail = f"Delivery state exceeds the {MAX_ENTRIES}-entry capability scan bound"
            return False
        return True


def scan_capability(workspace_root: Path, *, verification_journal: str | None = None) -> CapabilityReport:
    """Classify every registered record under the workspace's Delivery root without writing.

    ``verification_journal`` is the offline migration verifier's mode only: the named ``applied``
    journal is then accepted like a verified one. Normal controllers never pass it.
    """
    scan = _Scan()
    root = workspace_root / DELIVERY_STATE_ROOT
    try:
        root_fd = os.open(root, _DIRECTORY_FLAGS)
    except FileNotFoundError:
        return CapabilityReport(format=0, format_absent=True)
    except OSError as exc:
        detail = "Delivery state root is a symlink" if exc.errno == errno.ELOOP else "Delivery state root is unreadable"
        return CapabilityReport(complete=False, incomplete_detail=detail)
    try:
        _walk(root_fd, "", 0, scan)
    finally:
        os.close(root_fd)
    journals = tuple(
        MigrationJournalState(journal.locator, journal.migration_id, "verified", journal.schema_version, journal.kind)
        if verification_journal is not None
        and journal.migration_id == verification_journal
        and journal.state == "applied"
        else journal
        for journal in sorted(scan.journals, key=lambda journal: journal.locator)
    )
    format_value, format_status = scan.format, scan.format_status
    if format_status == "current" and (format_value is None or format_value < SUPPORTED_FORMAT):
        format_status = "migration-required" if scan.runtime_records else "current"
    return CapabilityReport(
        records=tuple(sorted(scan.records, key=lambda record: record.locator)),
        format=0 if format_value is None else format_value,
        format_status=format_status,
        format_absent=not scan.marker_present,
        journals=journals,
        complete=scan.incomplete_detail is None,
        incomplete_detail=scan.incomplete_detail,
    )


def _entries(directory_fd: int, scan: _Scan) -> list[os.DirEntry[str]]:
    """Charge each entry as it is enumerated, so an oversized directory is never consumed past the bound."""
    bounded: list[os.DirEntry[str]] = []
    with os.scandir(directory_fd) as entries:
        for entry in entries:
            if not scan.charge():
                return []
            bounded.append(entry)
    return sorted(bounded, key=lambda entry: entry.name)


def _walk(directory_fd: int, prefix: str, depth: int, scan: _Scan) -> None:
    if depth > MAX_DEPTH:
        scan.incomplete_detail = f"Delivery state exceeds the {MAX_DEPTH}-level capability scan depth"
        return
    for entry in _entries(directory_fd, scan):
        if scan.incomplete_detail is not None:
            return
        locator = f"{prefix}{entry.name}"
        if locator == MIGRATIONS_ROOT:
            _scan_migrations(directory_fd, entry, scan)
        elif prefix or entry.name not in _SKIP_DIRECTORIES:
            _classify_entry(directory_fd, entry, locator, depth, scan)


def _counts_as_runtime_record(locator: str, kind: RecordKind | None) -> bool:
    return (
        locator.startswith("runtime/")
        and locator not in _FRESH_RUNTIME_LOCATORS
        and (kind is None or kind.mutability != "L")
    )


def _classify_entry(directory_fd: int, entry: os.DirEntry[str], locator: str, depth: int, scan: _Scan) -> None:
    kind = classify_kind(locator)
    is_directory = entry.is_dir(follow_symlinks=False)
    if not is_directory and _counts_as_runtime_record(locator, kind):
        scan.runtime_records = True
    if is_directory:
        if kind is not None and not kind.read:
            scan.runtime_records = scan.runtime_records or _counts_as_runtime_record(locator, kind)
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
        scan.records.append(classify_record(kind, locator, content))


def _scan_migrations(parent_fd: int, entry: os.DirEntry[str], scan: _Scan) -> None:
    """Read each migration journal raw; any other entry in the namespace is an invalid journal."""
    if not entry.is_dir(follow_symlinks=False):
        scan.journals.append(MigrationJournalState(MIGRATIONS_ROOT, None, "invalid"))
        return
    try:
        namespace_fd = os.open(entry.name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError:
        scan.journals.append(MigrationJournalState(MIGRATIONS_ROOT, None, "invalid"))
        return
    try:
        for child in _entries(namespace_fd, scan):
            locator = f"{MIGRATIONS_ROOT}/{child.name}"
            if re.fullmatch(_D, child.name) is None or not child.is_dir(follow_symlinks=False):
                scan.journals.append(MigrationJournalState(locator, None, "invalid"))
            else:
                scan.journals.append(_read_journal(namespace_fd, child.name, scan))
    finally:
        os.close(namespace_fd)


def _read_journal(namespace_fd: int, migration_id: str, scan: _Scan) -> MigrationJournalState:
    locator = f"{MIGRATIONS_ROOT}/{migration_id}/{MIGRATION_JOURNAL}"
    try:
        directory_fd = os.open(migration_id, _DIRECTORY_FLAGS, dir_fd=namespace_fd)
    except OSError:
        return MigrationJournalState(locator, migration_id, "invalid")
    try:
        # An interrupted atomic journal write may leave its contained temporary beside the journal.
        names = [child.name for child in _entries(directory_fd, scan) if not _JOURNAL_TEMPORARY.fullmatch(child.name)]
        content = _read_record(directory_fd, MIGRATION_JOURNAL, scan) if names == [MIGRATION_JOURNAL] else None
    finally:
        os.close(directory_fd)
    try:
        payload = json.loads(content) if content is not None else None
    except UnicodeDecodeError, RecursionError, ValueError:
        payload = None
    if not isinstance(payload, dict):
        return MigrationJournalState(locator, migration_id, "invalid")
    version, state = payload.get("schema_version"), payload.get("state")
    if isinstance(version, bool) or not isinstance(version, int):
        return MigrationJournalState(locator, migration_id, "invalid")
    kind = journal_kind(payload)
    if kind is None or state not in JOURNAL_STATES or payload.get("migration_id") != migration_id:
        return MigrationJournalState(locator, migration_id, "invalid", version)
    if content is None or not journal_envelope_valid(payload, content):
        return MigrationJournalState(locator, migration_id, "invalid", version, kind)
    return MigrationJournalState(locator, migration_id, str(state), version, kind)


def journal_kind(payload: dict[str, object]) -> str | None:
    """Return a raw journal's operation kind: version 1 is a migration, version 2 names ``repair``."""
    version = payload.get("schema_version")
    if isinstance(version, bool):
        return None
    if version == 1 and "kind" not in payload:
        return "migration"
    if version == JOURNAL_SCHEMA_VERSION and payload.get("kind") == "repair":
        return "repair"
    return None


_JOURNAL_V1_FIELDS = frozenset(
    {"schema_version", "migration_id", "state", "source_format", "target_format", "backup_manifest_sha256", "batches"}
)
_JOURNAL_V2_FIELDS = _JOURNAL_V1_FIELDS | {"kind", "confirmed", "retained", "steps"}
_BATCH_ID = re.compile(r"migration-[0-9a-f]{16}-[0-9]{4}")


def _digest_value(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(_D, value) is not None


def _format_value(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _text_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _batch_value(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"transaction_id", "locators"}
        and isinstance(value["transaction_id"], str)
        and _BATCH_ID.fullmatch(value["transaction_id"]) is not None
        and _text_list(value["locators"])
        and bool(value["locators"])
    )


def _retained_value(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"migration_id", "sha256"}
        and _digest_value(value["migration_id"])
        and _digest_value(value["sha256"])
    )


def journal_envelope_valid(payload: dict[str, object], content: bytes) -> bool:
    """Return whether a supported-version journal has its complete envelope in canonical bytes.

    Version 1 is exactly the N02 migration journal (its bytes stay accepted); version 2 is a same-format
    repair journal. Anything less is invalid, so a truncated ``verified`` journal never lets a start pass.
    """
    version = payload.get("schema_version")
    if set(payload) != (_JOURNAL_V1_FIELDS if version == 1 else _JOURNAL_V2_FIELDS):
        return False
    if content != (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode():
        return False
    batches = payload["batches"]
    if not (
        _digest_value(payload["backup_manifest_sha256"])
        and _format_value(payload["source_format"])
        and _format_value(payload["target_format"])
        and isinstance(batches, list)
        and all(_batch_value(batch) for batch in batches)
    ):
        return False
    if version == 1:
        return True
    retained = payload["retained"]
    return (
        payload["kind"] == "repair"
        and batches == []
        and payload["source_format"] == payload["target_format"]
        and (payload["confirmed"] is None or _digest_value(payload["confirmed"]))
        and isinstance(retained, list)
        and all(_retained_value(item) for item in retained)
        and _text_list(payload["steps"])
    )


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
    scan.marker_present = True
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


def format_marker_bytes(format_value: int = SUPPORTED_FORMAT) -> bytes:
    """Return the canonical ``runtime/format.json`` bytes for one workspace format."""
    return json.dumps({"format": format_value}, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def format_migration_steps(source_format: int) -> tuple[str, ...]:
    """Return the registered steps from ``source_format`` to the supported format, in order."""
    steps: list[str] = []
    current = source_format
    for name, source, target in FORMAT_MIGRATIONS:
        if source == current and target <= SUPPORTED_FORMAT:
            steps.append(name)
            current = target
    if current != SUPPORTED_FORMAT:
        message = f"no registered format migration leads from format {source_format} to {SUPPORTED_FORMAT}"
        raise ValueError(message)
    return tuple(steps)


@dataclass(frozen=True, slots=True)
class ControllerPin:
    """The workspace's pinned controller release (``.owlbear/controller/pin.json``) and its predecessor.

    ``release_sha256`` is the SHA-256 of the release's ``RELEASE.json``, which ``delivery-controller verify``
    checks so that the pin names exactly the release record it verified (I6).
    """

    commit: str
    release_sha256: str
    previous: str | None = None


class ControllerPinError(ValueError):
    """The workspace pin exists but cannot be trusted; a pinned workspace then refuses every controller."""


def _open_contained(parent_fd: int, name: str, flags: int) -> int | None:
    """Open one child without following links; ``None`` when absent, ``ControllerPinError`` when unusable."""
    try:
        return os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        detail = f"{name} is a symlink" if exc.errno == errno.ELOOP else f"{name} is unreadable"
        raise ControllerPinError(detail) from exc


def _read_pin_bytes(workspace_root: Path) -> bytes | None:
    try:
        owlbear_fd = os.open(workspace_root / ".owlbear", _DIRECTORY_FLAGS)
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = ".owlbear is not a readable directory"
        raise ControllerPinError(msg) from exc
    try:
        controller_fd = _open_contained(owlbear_fd, "controller", _DIRECTORY_FLAGS)
    finally:
        os.close(owlbear_fd)
    if controller_fd is None:
        return None
    try:
        pin_fd = _open_contained(controller_fd, "pin.json", _FILE_FLAGS)
    finally:
        os.close(controller_fd)
    if pin_fd is None:
        return None
    try:
        if not stat.S_ISREG(os.fstat(pin_fd).st_mode):
            msg = "pin.json is not a regular file"
            raise ControllerPinError(msg)
        content = os.read(pin_fd, _MAX_PIN_BYTES + 1)
    finally:
        os.close(pin_fd)
    if len(content) > _MAX_PIN_BYTES:
        msg = "pin.json exceeds its size bound"
        raise ControllerPinError(msg)
    return content


def read_controller_pin(workspace_root: Path) -> ControllerPin | None:
    """Return the pinned release, ``None`` for an unpinned workspace, or raise ``ControllerPinError``."""
    content = _read_pin_bytes(workspace_root)
    if content is None:
        return None
    try:
        payload = json.loads(content)
    except UnicodeDecodeError, RecursionError, ValueError:
        payload = None
    if not isinstance(payload, dict) or set(payload) - _PIN_KEYS:
        msg = "pin.json is not a controller pin record"
        raise ControllerPinError(msg)
    version, commit, previous = payload.get("schema_version"), payload.get("commit"), payload.get("previous")
    if isinstance(version, bool) or version != PIN_SCHEMA_VERSION:
        msg = f"pin.json schema_version {version!r} is not supported (accepted: {PIN_SCHEMA_VERSION})"
        raise ControllerPinError(msg)
    if not isinstance(commit, str) or _COMMIT.fullmatch(commit) is None:
        msg = "pin.json does not name a full commit"
        raise ControllerPinError(msg)
    if previous is not None and (not isinstance(previous, str) or _COMMIT.fullmatch(previous) is None):
        msg = "pin.json names an invalid previous release"
        raise ControllerPinError(msg)
    release_sha256 = payload.get("release_sha256")
    if not isinstance(release_sha256, str) or _SHA256.fullmatch(release_sha256) is None:
        msg = "pin.json does not name the release record digest"
        raise ControllerPinError(msg)
    return ControllerPin(commit, release_sha256, previous)


def controller_pin_refusal(workspace_root: Path, code_file: Path) -> str | None:
    """Return why code at ``code_file`` may not control this workspace (I6), or ``None`` when it may.

    Unpinned workspaces accept any controller. A pinned workspace accepts only code whose real path lies
    inside the real directory of its pinned release; an unusable pin refuses every controller.
    """
    try:
        pin = read_controller_pin(workspace_root)
    except ControllerPinError as exc:
        return f"the controller pin is unusable ({exc}); {_LAUNCHER_HINT}"
    if pin is None:
        return None
    release = workspace_root / CONTROLLER_RELEASES / pin.commit
    code = Path(os.path.realpath(code_file))
    if not release.is_symlink() and release.is_dir() and code.is_relative_to(os.path.realpath(release)):
        return None
    return (
        f"this workspace is pinned to controller release {pin.commit}, but this controller runs from "
        f"{code.parent}; {_LAUNCHER_HINT}"
    )


def record_tree_digest(workspace_root: Path, *, exclude_migrations: bool = False) -> dict[str, str]:
    """Return SHA-256 digests of every non-transient Delivery record file, for no-write proofs.

    Symlinks (to files or directories) are recorded by target, never followed. ``exclude_migrations``
    omits the ``runtime/migrations`` namespace, as migration backup manifests do.
    """
    root = workspace_root / DELIVERY_STATE_ROOT
    digests: dict[str, str] = {}
    if not root.is_dir():
        return digests
    for directory, directory_names, file_names in os.walk(root):
        relative_directory = os.path.relpath(directory, root)
        prefix = "" if relative_directory == "." else f"{relative_directory.replace(os.sep, '/')}/"
        if not prefix:
            directory_names[:] = [name for name in directory_names if name not in _SKIP_DIRECTORIES]
        skipped = {"migrations"} if exclude_migrations and prefix == "runtime/" else set()
        directory_names[:] = [name for name in directory_names if name not in skipped]
        base = Path(directory)
        linked = [name for name in directory_names if (base / name).is_symlink()]
        for name in (*(name for name in file_names if name not in skipped), *linked):
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


# ---------------------------------------------------------------------------
# Gated controller process records (D12, class L)
# ---------------------------------------------------------------------------

_CONTROLLER_PROCESS_KEYS: Final = frozenset({"pid", "create_time", "cmdline_sha256"})
MAX_CONTROLLER_PROCESS_RECORD_BYTES: Final = 512


@dataclass(frozen=True, slots=True)
class ControllerProcessRecord:
    """Identity a gated controller publishes at ``runtime/controller-processes/<pid>.json``."""

    pid: int
    create_time: float
    cmdline_sha256: str


def controller_cmdline_digest(cmdline: Sequence[str]) -> str:
    """Return the SHA-256 of one argument vector (NUL-joined), never the arguments themselves."""
    return hashlib.sha256("\0".join(cmdline).encode("utf-8", "surrogateescape")).hexdigest()


def controller_process_record_bytes(pid: int, create_time: float, cmdline: Sequence[str]) -> bytes:
    """Return the canonical record bytes for one gated controller process."""
    payload = {"cmdline_sha256": controller_cmdline_digest(cmdline), "create_time": create_time, "pid": pid}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def parse_controller_process_record(content: bytes) -> ControllerProcessRecord | None:
    """Parse one record strictly; anything else (oversize, extra keys, wrong types) is ``None``."""
    if len(content) > MAX_CONTROLLER_PROCESS_RECORD_BYTES:
        return None
    try:
        payload = json.loads(content)
    except UnicodeDecodeError, RecursionError, ValueError:
        return None
    if not isinstance(payload, dict) or set(payload) != _CONTROLLER_PROCESS_KEYS:
        return None
    pid, create_time, digest = payload["pid"], payload["create_time"], payload["cmdline_sha256"]
    valid = (
        not isinstance(pid, bool)
        and isinstance(pid, int)
        and pid > 0
        and isinstance(create_time, float)
        and math.isfinite(create_time)
        and isinstance(digest, str)
        and re.fullmatch(_D, digest) is not None
    )
    return ControllerProcessRecord(pid, create_time, digest) if valid else None


# ---------------------------------------------------------------------------
# Transaction root map (N08 D1): every RuntimeTransaction recovery root and its owner validator
# ---------------------------------------------------------------------------

type TransactionValidator = Literal["generic", "contained"]


@dataclass(frozen=True, slots=True)
class TransactionRoot:
    """One manifest root: Delivery-root-relative ``pattern``, allowed participant roots and owner validator.

    ``participant_roots`` are Delivery-root-relative; ``.`` is the manifest root itself (contained roots).
    ``call_sites`` names every ``module:Class.method`` that recovers this root; a source scan pins them.
    """

    pattern: str
    participant_roots: tuple[str, ...]
    validator: TransactionValidator
    call_sites: tuple[str, ...]


_DESIGN_RECOVERY = "owlbear_delivery.design_package:DesignPackageStore._recover_transactions"
TRANSACTION_ROOTS: Final[tuple[TransactionRoot, ...]] = (
    TransactionRoot(
        "runtime",
        ("runtime", "packages"),
        "generic",
        (
            "owlbear_delivery.workspace_coordination:PortfolioCoordinator.__init__",
            "owlbear_delivery.workspace_coordination:PortfolioCoordinator.recover_pending_transactions",
            _DESIGN_RECOVERY,
            "owlbear_delivery.delivery_runtime:DeliveryRuntime._read",
            "owlbear_delivery.recovery:RetryLedger.repair_bindings",
            "owlbear_delivery.recovery:RetryLedger._read_with_bytes",
        ),
    ),
    TransactionRoot("packages", ("packages",), "generic", (_DESIGN_RECOVERY,)),
    TransactionRoot(
        rf"runtime/finalization-reports/{_C}",
        (".",),
        "contained",
        ("owlbear_delivery.finalization_reports:FinalizationReportStore._locked",),
    ),
    TransactionRoot(
        rf"runtime/proof-attempts/{_C}",
        (".",),
        "contained",
        ("owlbear_delivery.finalization_reports:ProofAttemptStore._locked",),
    ),
)


def transaction_root(locator: str) -> TransactionRoot | None:
    """Return the registered manifest root whose pattern matches one Delivery-root-relative directory."""
    return next((root for root in TRANSACTION_ROOTS if re.fullmatch(root.pattern, locator)), None)


__all__ = [
    "CONTROLLER_LOCK",
    "CONTROLLER_PIN",
    "CONTROLLER_PROCESSES_ROOT",
    "CONTROLLER_RELEASES",
    "CONTROLLER_ROOT",
    "DELIVERY_STATE_ROOT",
    "FAMILIES",
    "FORMAT_MARKER",
    "FORMAT_MIGRATIONS",
    "JOURNAL_READ_VERSIONS",
    "JOURNAL_SCHEMA_VERSION",
    "JOURNAL_STATES",
    "MAX_CONTROLLER_PROCESS_RECORD_BYTES",
    "MIGRATIONS_ROOT",
    "MIGRATION_JOURNAL",
    "NESTED_MODELS",
    "NON_PERSISTED_MODELS",
    "PIN_SCHEMA_VERSION",
    "RECORD_KINDS",
    "REMOTE_SNAPSHOT_CURRENT",
    "REMOTE_SNAPSHOT_READ_VERSIONS",
    "SUPPORTED_FORMAT",
    "TRANSACTION_ROOTS",
    "CapabilityRefusal",
    "CapabilityReport",
    "ControllerPin",
    "ControllerPinError",
    "ControllerProcessRecord",
    "MigrationJournalState",
    "RecordCapability",
    "RecordKind",
    "StateCapabilityError",
    "TransactionRoot",
    "classify_kind",
    "classify_record",
    "classify_version",
    "config_capability",
    "controller_cmdline_digest",
    "controller_pin_refusal",
    "controller_process_record_bytes",
    "format_marker_bytes",
    "format_migration_steps",
    "journal_kind",
    "parse_controller_process_record",
    "read_controller_pin",
    "record_tree_digest",
    "require_capability",
    "scan_capability",
    "transaction_root",
]
