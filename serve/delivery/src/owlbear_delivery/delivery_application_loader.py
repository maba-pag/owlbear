"""Transport-free Delivery application configuration and composition."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import weakref
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.acceptance import CompletionReceiptStore
from owlbear_delivery.change_publication import ChangeBranchPublisher
from owlbear_delivery.change_workspace import (
    BuilderHandoffSource,
    ChangeCoordination,
    ChangeWorkspaceManager,
    CoordinationConflictError,
    PortfolioCoordinator,
)
from owlbear_delivery.completed_history import CompletedHistoryCatalog
from owlbear_delivery.delivery_admission import DeliveryAuthorityRegistry
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryDiscoveryErrorCode,
    DeliveryDiscoveryRootError,
    discover_persisted_changes,
)
from owlbear_delivery.delivery_runtime import (
    REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES,
    BlockDelivery,
    DeliveryAcceptanceAttentionReason,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryBuilderHandoffContext,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeDispositionKind,
    DeliveryFrontier,
    DeliveryPendingStatePublication,
    DeliveryPlanCandidate,
    DeliveryRequestKind,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    RetryDelivery,
    ReturnDelivery,
    _DeliveryBuilderInvocationSettlementReceipt,
    _DeliveryBuilderPlanPromotionReceipt,
    _DeliveryPlanningPauseReplay,
    _model_content,
    _read_builder_handoff_change_intent_receipts,
    _read_builder_request_resolution_receipt,
)
from owlbear_delivery.delivery_state import (
    REMOTE_STATE_VERSION_UNSUPPORTED,
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    DeliveryStateSnapshot,
)
from owlbear_delivery.design_package import DesignPackageStore
from owlbear_delivery.draft_pull_request import DraftPullRequestPublisher
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.portfolio_application import (
    DeliveryRolePolicy,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthHeadRelation,
    DeliveryHealthReason,
    DeliveryHealthResolution,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant
from owlbear_delivery.state_formats import StateCapabilityError, require_capability, scan_capability
from owlbear_delivery.storage_io import ControllerFencedError, ControllerLock, acquire_controller_lock

if TYPE_CHECKING:
    from owlbear_delivery.delivery_runtime import DeliveryRequest, _DeliveryBuilderHandoffChangeIntentReceipt
    from owlbear_delivery.publication_provider import PublicationProvider
    from owlbear_delivery.target_contract import DeliveryContract
    from owlbear_delivery.worker_stall import WindowHostIdentity


class _LoaderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStartupConfig(_LoaderModel):
    """Workspace-local Delivery policy loaded before owner construction."""

    schema_version: Literal[2]
    remote: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    github_repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    delivery_state_branch: str = "owlbear/delivery-state"


class DeliveryHostConfig(_LoaderModel):
    """Host-local limits and timeout for Delivery work."""

    schema_version: Literal[1]
    execution_capacity: int = Field(default=3, gt=0)
    claim_timeout_seconds: int = Field(default=60 * 60, gt=0)


class _DeliveryHostConfigOverrides(_LoaderModel):
    """Optional host-local overrides layered over tracked Delivery defaults."""

    schema_version: Literal[1] = 1
    execution_capacity: int | None = Field(default=None, gt=0)
    claim_timeout_seconds: int | None = Field(default=None, gt=0)


@dataclass(frozen=True)
class _DeliveryPaths:
    package_root: Path
    runtime_root: Path
    repository_root: Path
    worktree_root: Path


@dataclass(frozen=True)
class _BuilderReturnReplayContext:
    snapshot: DeliveryStateSnapshot
    local_frontier: DeliveryFrontier
    settlement: _DeliveryBuilderInvocationSettlementReceipt
    paths: _DeliveryPaths
    branch_head: str


@dataclass(frozen=True)
class _PlannerPauseHistory:
    settled: OutcomeAuthorityBinding
    answered_requests: tuple[DeliveryRequest, ...]
    paused: tuple[OutcomeAuthorityBinding, ...]
    answered: tuple[OutcomeAuthorityBinding, ...]
    latest: OutcomeAuthorityBinding


class DeliveryApplicationLoadError(RuntimeError):
    """Field-aware failure raised before Delivery state owners are composed."""

    __slots__ = ("code", "detail", "field")

    def __init__(self, field: str, detail: str, *, code: str | None = None) -> None:
        self.field = field
        self.detail = detail
        self.code = code
        super().__init__(detail)


class DeliveryStateVersionError(DeliveryApplicationLoadError):
    """Persisted Delivery state is outside the formats this controller may read or write."""

    __slots__ = ("locator",)

    def __init__(self, code: str, detail: str, *, locator: str) -> None:
        super().__init__("state_version", detail, code=code)
        self.locator = locator


CONTROLLER_FENCED = "controller-fenced"
_CONTROLLER_LOCKS: weakref.WeakKeyDictionary[PortfolioApplication, ControllerLock] = weakref.WeakKeyDictionary()


_REMOTE_REF_MISSING = 2
_RECOVERABLE_ADMISSION_ERRORS = frozenset(
    {
        DeliveryDiscoveryErrorCode.ADMISSION_UNAVAILABLE,
        DeliveryDiscoveryErrorCode.ADMISSION_INVALID,
    }
)
_logger = logging.getLogger(__name__)


def _load_error(field: str, detail: str) -> DeliveryApplicationLoadError:
    return DeliveryApplicationLoadError(field, detail)


def _derive_paths(workspace_root: Path) -> _DeliveryPaths:
    repository_root = workspace_root.resolve()
    if not repository_root.is_dir():
        field = "workspace_root"
        detail = "workspace root must be an existing directory"
        raise _load_error(field, detail)
    state_root = repository_root / ".owlbear"
    delivery_root = state_root / "delivery"
    if state_root.is_symlink() or delivery_root.is_symlink():
        field = "workspace_root"
        detail = "Delivery state parents must not be symlinks"
        raise _load_error(field, detail)
    paths = _DeliveryPaths(
        package_root=delivery_root / "packages",
        runtime_root=delivery_root / "runtime",
        repository_root=repository_root,
        worktree_root=delivery_root / "worktrees",
    )
    for field, path in (
        ("package_root", paths.package_root),
        ("runtime_root", paths.runtime_root),
        ("worktree_root", paths.worktree_root),
    ):
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise _load_error(field, "derived path must name a directory")
    return paths


def _validate_git_config(config: DeliveryStartupConfig, paths: _DeliveryPaths) -> None:
    try:
        git_executable = resolve_git_executable()
    except RuntimeError as exc:
        error = _load_error("repository_root", "Git executable is unavailable")
        raise error from exc
    checks = (
        (("rev-parse", "--git-dir"), "repository_root"),
        (("check-ref-format", f"refs/heads/{config.target_branch}"), "target_branch"),
        (("check-ref-format", f"refs/heads/{config.delivery_state_branch}"), "delivery_state_branch"),
        (("remote", "get-url", config.remote), "remote"),
        (
            ("rev-parse", "--verify", f"refs/remotes/{config.remote}/{config.target_branch}^{{commit}}"),
            "target_branch",
        ),
    )
    for arguments, field in checks:
        completed = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
            (git_executable, "-C", str(paths.repository_root), *arguments),
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = {
                "repository_root": "configured Git repository is invalid",
                "remote": "configured Git remote is invalid",
                "target_branch": "configured target branch or remote-tracking target is invalid",
                "delivery_state_branch": "configured Delivery-state branch name is invalid",
            }[field]
            error = _load_error(field, detail)
            raise error
    remote_url = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
        (git_executable, "-C", str(paths.repository_root), "config", "--get", f"remote.{config.remote}.url"),
        check=False,
        capture_output=True,
        text=True,
    )
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^\s/]+/[^\s/]+?)(?:\.git)?",
        remote_url.stdout.strip(),
    )
    if match is None or match.group(1) != config.github_repository:
        field = "github_repository"
        detail = "configured GitHub repository does not match the remote URL"
        raise _load_error(field, detail)
    worktrees = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
        (git_executable, "-C", str(paths.repository_root), "worktree", "list", "--porcelain", "-z"),
        check=False,
        capture_output=True,
    )
    if worktrees.returncode != 0:
        field = "repository_root"
        detail = "Git must support 'worktree list --porcelain -z' for safe Delivery startup"
        raise _load_error(field, detail)
    registered_worktrees = tuple(
        Path(os.fsdecode(field.removeprefix(b"worktree "))).resolve()
        for field in worktrees.stdout.split(b"\0")
        if field.startswith(b"worktree ")
    )
    if not registered_worktrees:
        field = "repository_root"
        detail = "Git worktree registry contains no primary checkout"
        raise _load_error(field, detail)
    primary_worktree = registered_worktrees[0]
    if paths.repository_root != primary_worktree:
        field = "workspace_root"
        detail = "Delivery must start from the primary Git worktree"
        raise _load_error(field, detail)


def _load_contracts(runtime_root: Path) -> tuple[dict[str, DeliveryContract], tuple[DeliveryHealthDiagnostic, ...]]:
    try:
        observations = discover_persisted_changes(runtime_root)
    except DeliveryDiscoveryRootError as exc:
        error = _load_error("runtime_root", exc.detail)
        raise error from exc
    contracts: dict[str, DeliveryContract] = {}
    diagnostics: list[DeliveryHealthDiagnostic] = []
    for observation in observations:
        if observation.error is not None:
            detail = observation.diagnostic_detail or "Persisted Delivery state is unavailable."
            diagnostics.append(
                DeliveryHealthDiagnostic(
                    source="local-runtime",
                    code=observation.error.code.value,
                    detail=detail,
                    change_id=observation.change_id,
                    path=f".owlbear/delivery/runtime/changes/{observation.change_id}",
                    reason=DeliveryHealthReason.RUNTIME_UNAVAILABLE,
                    resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                )
            )
        if (
            observation.contract is not None
            and observation.contract.change_id == observation.change_id
            and (observation.error is None or observation.error.code in _RECOVERABLE_ADMISSION_ERRORS)
        ):
            contracts[observation.change_id] = observation.contract
    return contracts, tuple(diagnostics)


def _load_host_config_model[T: BaseModel](path: Path, model: type[T], default: T) -> T:
    try:
        if not path.exists():
            if path.is_symlink():
                error = _load_error("host_config", "host-local Delivery runtime configuration is unsafe")
                raise error
            return default
        if path.is_symlink() or not path.is_file():
            error = _load_error("host_config", "host-local Delivery runtime configuration must be a regular file")
            raise error
        return model.model_validate_json(path.read_bytes())
    except DeliveryApplicationLoadError:
        raise
    except ValidationError as exc:
        location = exc.errors(include_url=False, include_context=False)[0].get("loc")
        field = location[0] if isinstance(location, tuple | list) and location else "host_config"
        error = _load_error(str(field), f"host-local Delivery runtime configuration is invalid: {path}")
        raise error from exc
    except (OSError, ValueError) as exc:
        error = _load_error("host_config", f"host-local Delivery runtime configuration cannot be read: {path}")
        raise error from exc


def _load_host_config(paths: _DeliveryPaths) -> DeliveryHostConfig:
    baseline = _load_host_config_model(
        paths.runtime_root / "host.json",
        DeliveryHostConfig,
        DeliveryHostConfig(schema_version=1),
    )
    overrides = _load_host_config_model(
        paths.runtime_root / "host.local.json",
        _DeliveryHostConfigOverrides,
        _DeliveryHostConfigOverrides(),
    )
    values = baseline.model_dump()
    local_values = overrides.model_dump(exclude_none=True)
    local_values.pop("schema_version", None)
    values.update(local_values)
    return DeliveryHostConfig.model_validate(values)


def _role_policies() -> tuple[DeliveryRolePolicy, ...]:
    return (
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.PLANNER,
            worker_agent="planner",
            reviewer_agent="planner-challenger",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.BUILDER,
            worker_agent="builder",
            reviewer_agent="build-reviewer",
        ),
    )


def _bootstrap_remote_state(
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
) -> tuple[DeliveryHealthDiagnostic, ...]:
    """Restore missing local Delivery state from remote semantic snapshots."""
    package_store = DesignPackageStore(
        paths.package_root,
        paths.repository_root,
        transaction_root=paths.runtime_root,
    )
    try:
        state_publisher = DeliveryStatePublisher(
            paths.repository_root,
            remote=config.remote,
            state_branch=config.delivery_state_branch,
        )
        inventory = state_publisher.read_snapshot_inventory()
    except DeliveryStatePublicationError as exc:
        return (
            DeliveryHealthDiagnostic(
                source="remote-state",
                code="remote-state-unavailable",
                detail=_bounded_health_detail(
                    str(exc),
                    "Remote Delivery-state snapshots are unavailable; local state was retained.",
                ),
                retry_safe=exc.retry_safe,
                reason=DeliveryHealthReason.REMOTE_STATE_UNAVAILABLE,
                resolution=(
                    DeliveryHealthResolution.RETRY if exc.retry_safe else DeliveryHealthResolution.AUTHORITY_GAP
                ),
            ),
        )
    diagnostics = [
        DeliveryHealthDiagnostic(
            source="remote-state",
            code=item.code,
            detail=item.detail,
            change_id=item.change_id,
            path=item.path,
            reason=(
                DeliveryHealthReason.REMOTE_STATE_VERSION_UNSUPPORTED
                if item.code == REMOTE_STATE_VERSION_UNSUPPORTED
                else DeliveryHealthReason.REMOTE_STATE_RECONCILIATION
            ),
            resolution=DeliveryHealthResolution.AUTHORITY_GAP,
        )
        for item in inventory.diagnostics
    ]
    if not inventory.snapshots:
        return tuple(diagnostics)
    coordinator = PortfolioCoordinator(paths.runtime_root)
    workspace_manager = ChangeWorkspaceManager(
        paths.repository_root,
        paths.worktree_root,
        coordinator,
        config.target_branch,
        config.remote,
    )
    local_change_ids = _local_runtime_change_ids(paths.runtime_root)
    for snapshot in inventory.snapshots:
        try:
            if snapshot.change_id in local_change_ids:
                _validate_local_snapshot(snapshot, config, paths, package_store, workspace_manager)
            else:
                _restore_remote_snapshot(snapshot, config, paths, package_store, coordinator, workspace_manager)
        except _DeferredRemoteStateReconciliationError as exc:
            diagnostics.append(
                DeliveryHealthDiagnostic(
                    source="remote-state",
                    code="remote-change-head-ahead",
                    detail="Remote Change branch is ahead of its reviewed Delivery snapshot and was quarantined.",
                    change_id=snapshot.change_id,
                    reason=DeliveryHealthReason.REMOTE_CHANGE_HEAD_AHEAD,
                    resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                    expected_head=exc.expected_head,
                    observed_head=exc.observed_head,
                    observed_local_head=exc.observed_local_head,
                    head_relation=exc.head_relation,
                )
            )
            continue
        except _RemoteChangeHeadMismatchError as exc:
            diagnostics.append(
                DeliveryHealthDiagnostic(
                    source="remote-state",
                    code="remote-state-reconciliation-required",
                    detail=str(exc),
                    change_id=snapshot.change_id,
                    reason=exc.reason,
                    resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                    expected_head=exc.expected_head,
                    observed_head=exc.observed_head,
                    observed_local_head=exc.observed_local_head,
                    head_relation=exc.head_relation,
                )
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            detail = _bounded_health_detail(
                str(exc),
                "Remote Delivery state could not be reconciled and was quarantined.",
            )
            reason = (
                DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                if "local Delivery runtime artifact differs from its remote snapshot: frontier.json" in detail
                else DeliveryHealthReason.REMOTE_STATE_RECONCILIATION
            )
            diagnostics.append(
                DeliveryHealthDiagnostic(
                    source="remote-state",
                    code="remote-state-reconciliation-required",
                    detail=detail,
                    change_id=snapshot.change_id,
                    reason=reason,
                    resolution=(
                        DeliveryHealthResolution.INSPECT
                        if reason is DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                        else DeliveryHealthResolution.AUTHORITY_GAP
                    ),
                )
            )
    return tuple(diagnostics)


def _restore_remote_snapshot(  # noqa: PLR0913, PLR0917 - restoration binds each independent state owner.
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
    package_store: DesignPackageStore,
    coordinator: PortfolioCoordinator,
    workspace_manager: ChangeWorkspaceManager,
) -> None:
    """Restore one exact remote snapshot into host-local Delivery state."""
    revision, has_remote_change_branch = _fetch_snapshot_change_head(snapshot, config, paths.repository_root)
    package_files = {
        name: _read_git_blob(
            paths.repository_root,
            revision,
            f".owlbear/delivery/packages/{snapshot.change_id}/{name}",
        )
        for name in ("authority.json", "design.md", "intent.md", "manifest.json")
    }
    package_store.restore(snapshot.change_id, package_files)
    if has_remote_change_branch:
        _restore_local_change_branch(snapshot, paths.repository_root)
    worktree_path = paths.worktree_root / snapshot.change_id
    if has_remote_change_branch and not snapshot.frontier.change_completion and not worktree_path.exists():
        ChangeWorkspaceManager.restore_worktree(
            paths.repository_root,
            worktree_path,
            snapshot.branch,
        )
    try:
        coordinator.show(snapshot.change_id)
    except CoordinationConflictError:
        coordinator.register(
            ChangeCoordination(
                change_id=snapshot.change_id,
                branch=snapshot.branch,
                worktree_path=worktree_path,
                integration_target=snapshot.integration_target,
                target_head=snapshot.target_head,
                publication_base_head=snapshot.publication_base_head,
                last_reviewed_commit=snapshot.last_reviewed_commit,
            )
        )
    _restore_runtime_snapshot(snapshot, paths.runtime_root)
    workspace_manager.show(snapshot.change_id)


def _validate_local_snapshot(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
    package_store: DesignPackageStore,
    workspace_manager: ChangeWorkspaceManager,
) -> None:
    """Reject local Delivery state outside exact or explicitly recoverable authority."""
    try:
        package = package_store.read_verified(snapshot.change_id)
    except (OSError, RuntimeError, ValueError) as exc:
        _bootstrap_failure("local Delivery package cannot be reconciled with its remote snapshot", exc)
    if package.package_id != snapshot.package_id:
        _bootstrap_failure("local Delivery package differs from its remote snapshot")
    try:
        coordination = workspace_manager.show(snapshot.change_id)
    except (OSError, RuntimeError, ValueError) as exc:
        _bootstrap_failure("local Delivery coordination cannot be reconciled with its remote snapshot", exc)
    if (
        coordination.branch != snapshot.branch
        or coordination.integration_target != snapshot.integration_target
        or coordination.target_head != snapshot.target_head
        or coordination.publication_base_head != snapshot.publication_base_head
        or coordination.last_reviewed_commit != snapshot.last_reviewed_commit
    ):
        _bootstrap_failure("local Delivery coordination differs from its remote snapshot")
    relative_root = paths.runtime_root / "changes" / snapshot.change_id
    expected = {
        "contract.json": _canonical_model(snapshot.contract),
        "frontier.json": _canonical_model(snapshot.frontier),
        "admission.json": _canonical_model(snapshot.admission),
    }
    frontier_bytes, frontier = _read_local_snapshot_frontier(relative_root / "frontier.json")
    local_pending_publication = _read_local_pending_publication(
        relative_root / "state-publication.json",
        frontier_bytes,
    )
    if local_pending_publication and (
        coordination.builder_handoff is not None
        or any(binding.builder_handoff_context is not None for binding in frontier.bindings)
    ):
        _bootstrap_failure("local Builder handoff cannot be combined with portable state publication")
    local_attention_successor = _is_unpublished_acceptance_attention_successor(
        snapshot.frontier, frontier
    ) or _is_unpublished_target_sync_attention_successor(snapshot.frontier, frontier)
    local_claim_successor = _is_unpublished_claim_successor(snapshot.frontier, frontier)
    local_builder_handoff_successor = _is_unpublished_builder_handoff_successor(
        snapshot,
        frontier,
        coordination,
        paths,
        workspace_manager,
    )
    local_checkpoint_successor = _is_unpublished_checkpoint_successor(snapshot.frontier, frontier)
    local_recoverable_successor = (
        local_attention_successor
        or local_claim_successor
        or local_builder_handoff_successor
        or local_checkpoint_successor
        or local_pending_publication
    )
    if local_claim_successor:
        _require_local_snapshot_branch(snapshot, paths.repository_root)
    _fetch_snapshot_change_head(
        snapshot,
        config,
        paths.repository_root,
        allow_local_branch=True,
        allow_local_descendant=local_attention_successor or local_builder_handoff_successor,
    )
    if frontier_bytes != expected["frontier.json"] and not local_recoverable_successor:
        _bootstrap_failure("local Delivery runtime artifact differs from its remote snapshot: frontier.json")
    _validate_local_snapshot_artifacts(relative_root, expected)
    try:
        completion = CompletionReceiptStore(paths.runtime_root).read_bundle(snapshot.change_id)
    except RuntimeError as exc:
        _bootstrap_failure("local completion evidence cannot be reconciled with its remote snapshot", exc)
    if completion != snapshot.completion:
        _bootstrap_failure("local completion evidence differs from its remote snapshot")


def _read_local_snapshot_frontier(path: Path) -> tuple[bytes, DeliveryFrontier]:
    """Read and validate the local frontier needed for startup reconciliation."""
    if path.is_symlink() or not path.is_file():
        _bootstrap_failure("local Delivery runtime artifact differs from its remote snapshot: frontier.json")
    try:
        content = path.read_bytes()
        return content, DeliveryFrontier.model_validate_json(content, strict=True)
    except (OSError, ValueError) as exc:
        _bootstrap_failure("local Delivery runtime artifact differs from its remote snapshot: frontier.json", exc)


def _read_local_pending_publication(path: Path, frontier_bytes: bytes) -> bool:
    """Recognize one exact pending local publication marker for restart replay."""
    if not path.exists():
        return False
    if path.is_symlink() or not path.is_file():
        _bootstrap_failure("local Delivery publication intent cannot be reconciled")
    try:
        intent = DeliveryPendingStatePublication.model_validate_json(path.read_bytes(), strict=True)
    except (OSError, TypeError, ValueError) as exc:
        _bootstrap_failure("local Delivery publication intent cannot be reconciled", exc)
    return (
        intent.status == "pending"
        and intent.base_frontier_digest is not None
        and intent.frontier_digest == hashlib.sha256(frontier_bytes).hexdigest()
    )


def _validate_local_snapshot_artifacts(
    relative_root: Path,
    expected: dict[str, bytes],
) -> None:
    """Validate the non-frontier local artifacts against the remote snapshot."""
    for name in ("contract.json", "admission.json"):
        _validate_local_snapshot_artifact(relative_root / name, name, expected[name])


def _validate_local_snapshot_artifact(
    path: Path,
    name: str,
    expected: bytes,
) -> None:
    """Require one local runtime artifact to match its remote snapshot bytes."""
    if path.is_symlink() or not path.is_file():
        _bootstrap_failure(f"local Delivery runtime artifact differs from its remote snapshot: {name}")
    actual = path.read_bytes()
    if actual == expected:
        return
    _bootstrap_failure(f"local Delivery runtime artifact differs from its remote snapshot: {name}")


def _fetch_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    repository: Path,
    *,
    allow_local_branch: bool = False,
    allow_local_descendant: bool = False,
) -> tuple[str, bool]:
    """Fetch the remote Change branch or use the configured target for finalized authority."""
    remote_branch = _remote_branch_head(repository, config.remote, snapshot.branch)
    if remote_branch is not None:
        return _fetch_remote_snapshot_change_head(snapshot, config, repository, remote_branch)
    local_head = _local_snapshot_change_head(
        snapshot,
        repository,
        allow_local_branch=allow_local_branch,
        allow_local_descendant=allow_local_descendant,
    )
    if local_head is not None:
        return local_head, False
    if snapshot.frontier.change_completion is not None:
        return _fetch_completed_snapshot_change_head(snapshot, config, repository)
    if snapshot.frontier.finalization is not None:
        return _fetch_finalized_snapshot_change_head(snapshot, config, repository)
    message = "remote Change branch is missing for an active Delivery snapshot"
    return _bootstrap_failure(message)


def _fetch_remote_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    repository: Path,
    remote_branch: str,
) -> tuple[str, bool]:
    """Validate and fetch one remote Change branch at its snapshot head."""
    if remote_branch != snapshot.change_head:
        observed_local_head = _loader_git_output(
            repository,
            "rev-parse",
            "--verify",
            f"refs/heads/{snapshot.branch}^{{commit}}",
        )
        head_relation = _head_relation(repository, snapshot.change_head, remote_branch)
        if _can_defer_remote_state_reconciliation(snapshot, repository, remote_branch):
            raise _DeferredRemoteStateReconciliationError(
                expected_head=snapshot.change_head,
                observed_head=remote_branch,
                observed_local_head=observed_local_head,
                head_relation=head_relation,
            )
        raise _RemoteChangeHeadMismatchError(
            change_id=snapshot.change_id,
            expected_head=snapshot.change_head,
            observed_head=remote_branch,
            observed_local_head=observed_local_head,
            head_relation=head_relation,
            reason=(
                DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH
                if head_relation is not DeliveryHealthHeadRelation.DESCENDANT
                else DeliveryHealthReason.REMOTE_STATE_RECONCILIATION
            ),
        )
    result = _run_loader_git(
        repository,
        "fetch",
        "--no-tags",
        "--no-write-fetch-head",
        "--refmap=",
        config.remote,
        f"refs/heads/{snapshot.branch}",
        check=False,
    )
    if result.returncode != 0:
        _bootstrap_failure("remote Change branch could not be fetched")
    return snapshot.change_head, True


def _local_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    repository: Path,
    *,
    allow_local_branch: bool,
    allow_local_descendant: bool,
) -> str | None:
    """Return the snapshot head when a retained local branch is safe to use."""
    if not allow_local_branch or snapshot.frontier.change_completion is not None:
        return None
    local_branch = _loader_git_output(
        repository,
        "rev-parse",
        "--verify",
        f"refs/heads/{snapshot.branch}^{{commit}}",
    )
    if local_branch == snapshot.change_head:
        return snapshot.change_head
    if (
        allow_local_descendant
        and local_branch is not None
        and _loader_git_is_ancestor(repository, snapshot.change_head, local_branch)
    ):
        return snapshot.change_head
    return None


def _require_local_snapshot_branch(snapshot: DeliveryStateSnapshot, repository: Path) -> None:
    """Require one active local snapshot branch to remain at its reviewed head."""
    local_head = _local_snapshot_change_head(
        snapshot,
        repository,
        allow_local_branch=True,
        allow_local_descendant=False,
    )
    if local_head != snapshot.change_head:
        _bootstrap_failure("local Change branch differs from Delivery-state snapshot")


def _is_unpublished_claim_successor(
    snapshot_frontier: DeliveryFrontier,
    local_frontier: DeliveryFrontier,
) -> bool:
    """Recognize a local frontier that adds host-local claim and output state."""
    if snapshot_frontier.change_completion is not None or local_frontier.change_completion is not None:
        return False
    if len(snapshot_frontier.bindings) != len(local_frontier.bindings):
        return False
    local_has_claim = False
    for snapshot_binding, local_binding in zip(snapshot_frontier.bindings, local_frontier.bindings, strict=True):
        if snapshot_binding.outcome_id != local_binding.outcome_id:
            return False
        if snapshot_binding.active_claim is not None:
            return False
        if local_binding.active_claim is not None:
            local_has_claim = True
    transient_fields = {
        "active_claim": None,
        "output": None,
        "candidate": None,
        "result_candidate": None,
        "recovery_attention": None,
        "retry_diagnostic": None,
    }
    snapshot_without_claims = snapshot_frontier.model_copy(
        update={
            "bindings": tuple(binding.model_copy(update=transient_fields) for binding in snapshot_frontier.bindings)
        }
    )
    local_without_claims = local_frontier.model_copy(
        update={"bindings": tuple(binding.model_copy(update=transient_fields) for binding in local_frontier.bindings)}
    )
    return local_has_claim and snapshot_without_claims == local_without_claims


def _is_unpublished_builder_handoff_successor(
    snapshot: DeliveryStateSnapshot,
    local_frontier: DeliveryFrontier,
    coordination: ChangeCoordination,
    paths: _DeliveryPaths,
    workspace_manager: ChangeWorkspaceManager,
) -> bool:
    """Recognize one exact local Builder handoff settlement or its permitted successor."""
    local_bindings = tuple(
        binding for binding in local_frontier.bindings if binding.builder_handoff_context is not None
    )
    if not local_bindings and coordination.builder_handoff is None:
        return False
    if len(local_bindings) != 1:
        _bootstrap_failure("local Builder handoff does not have one exact outcome context")
    local_binding = local_bindings[0]
    context = local_binding.builder_handoff_context
    if context is None:
        _bootstrap_failure("local Builder handoff context is unavailable")
    snapshot_binding = next(
        (binding for binding in snapshot.frontier.bindings if binding.outcome_id == context.outcome_id),
        None,
    )
    if snapshot_binding is None:
        _bootstrap_failure("local Builder handoff outcome is absent from its remote snapshot")
    receipt = _read_local_builder_handoff_receipt(paths.runtime_root, snapshot.change_id, context)
    if not _builder_handoff_receipt_matches_snapshot(snapshot, snapshot_binding, receipt.handoff_context, receipt):
        _bootstrap_failure("local Builder handoff receipt does not match its reviewed task authority")
    if not _builder_handoff_owner_matches(coordination, local_binding, context, receipt.envelope):
        _bootstrap_failure("local Builder handoff receipt does not match current Change custody")
    branch_head = _validate_local_builder_handoff_workspace(snapshot, coordination, context, paths, workspace_manager)
    _validate_local_builder_handoff_frontier(
        snapshot,
        local_frontier,
        receipt,
        branch_head,
        paths,
    )
    return True


def _builder_handoff_receipt_matches_snapshot(
    snapshot: DeliveryStateSnapshot,
    snapshot_binding: OutcomeAuthorityBinding,
    context: DeliveryBuilderHandoffContext,
    receipt: _DeliveryBuilderInvocationSettlementReceipt,
) -> bool:
    """Bind one immutable Builder settlement to its published task authority and route."""
    envelope = receipt.envelope
    request = envelope.request
    requestless = envelope.disposition in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES and request is None
    if requestless:
        request_matches = True
        expected_route = "same-task"
    elif isinstance(request, RetryDelivery):
        request_matches = request.abandoned_commit == context.branch_head and request.attempt_id == envelope.attempt_id
        expected_route = "same-task"
    elif isinstance(request, BlockDelivery):
        delivery_request = request.request
        request_matches = (
            delivery_request is not None
            and delivery_request.resolution is None
            and delivery_request.outcome_id == context.outcome_id
            and delivery_request.request_id not in {item.request_id for item in snapshot_binding.requests}
        )
        expected_route = "same-task"
    elif isinstance(request, ReturnDelivery):
        expected_route = {
            DeliveryStage.PLANNING: "same-outcome-planner",
            DeliveryStage.DESIGN: "same-outcome-design",
        }.get(request.target)
        request_matches = (
            expected_route is not None
            and request.preserved_commit == context.branch_head
            and request.attempt_id == envelope.attempt_id
        )
    else:
        return False
    original_task = next((task for task in snapshot_binding.tasks if task.task_id == context.original_task_id), None)
    return all(
        (
            request_matches,
            context.route == expected_route,
            receipt.handoff_context == context,
            envelope.disposition == "normal-return" or requestless,
            envelope.change_id == snapshot.change_id,
            envelope.outcome_id == context.outcome_id,
            envelope.task_id == context.original_task_id,
            request is None or (request.outcome_id == context.outcome_id and request.claim_id == envelope.claim_id),
            envelope.expected_last_reviewed_commit == snapshot.last_reviewed_commit,
            context.last_reviewed_commit == snapshot.last_reviewed_commit,
            any(outcome.outcome_id == context.outcome_id for outcome in snapshot.contract.outcomes),
            original_task is not None,
            original_task.plan_scope_id == snapshot_binding.plan_scope_id,
            original_task.commitment_ids == context.original_task_commitment_ids,
            original_task.maintained_surfaces == context.original_task_maintained_surfaces,
        )
    )


def _validate_local_builder_handoff_workspace(
    snapshot: DeliveryStateSnapshot,
    coordination: ChangeCoordination,
    context: DeliveryBuilderHandoffContext,
    paths: _DeliveryPaths,
    workspace_manager: ChangeWorkspaceManager,
) -> str:
    """Require retained metadata or an active successor branch to match the exact handoff."""
    if coordination.builder_handoff is None:
        active_head = workspace_manager.source_head(
            snapshot.change_id,
            require_clean=False,
            builder_handoff_source=BuilderHandoffSource(
                settlement_id=context.settlement_id,
                original_task_id=context.original_task_id,
                branch_head=context.branch_head,
                last_reviewed_commit=context.last_reviewed_commit,
                metadata_fingerprint=context.metadata_fingerprint,
            ),
        )
        local_branch_head = _loader_git_output(
            paths.repository_root,
            "rev-parse",
            "--verify",
            f"refs/heads/{snapshot.branch}^{{commit}}",
        )
        if not (
            active_head == local_branch_head
            and _loader_git_is_ancestor(paths.repository_root, snapshot.change_head, context.branch_head)
        ):
            _bootstrap_failure("active Builder handoff branch differs from its captured descendant")
        return active_head

    metadata = workspace_manager._capture_builder_handoff_metadata(coordination)  # noqa: SLF001
    local_branch_head = _loader_git_output(
        paths.repository_root,
        "rev-parse",
        "--verify",
        f"refs/heads/{snapshot.branch}^{{commit}}",
    )
    if not all(
        (
            metadata.change_id == snapshot.change_id,
            metadata.branch == snapshot.branch,
            metadata.worktree_path == coordination.worktree_path,
            metadata.last_reviewed_commit == context.last_reviewed_commit,
            metadata.branch_head == context.branch_head,
            metadata.registration.path == metadata.worktree_path,
            metadata.registration.branch == metadata.branch,
            metadata.registration.head == metadata.branch_head,
            metadata.fingerprint == context.metadata_fingerprint,
            local_branch_head == context.branch_head,
            _loader_git_is_ancestor(paths.repository_root, snapshot.change_head, context.branch_head),
        )
    ):
        _bootstrap_failure("local Builder handoff metadata or Change head differs from its captured proof")
    return context.branch_head


def _validate_local_builder_handoff_frontier(
    snapshot: DeliveryStateSnapshot,
    local_frontier: DeliveryFrontier,
    receipt: _DeliveryBuilderInvocationSettlementReceipt,
    branch_head: str,
    paths: _DeliveryPaths,
) -> None:
    """Require the exact retry or pause result, answer, claim, and candidate."""
    if isinstance(receipt.envelope.request, ReturnDelivery):
        _validate_local_builder_return_frontier(
            _BuilderReturnReplayContext(snapshot, local_frontier, receipt, paths, branch_head)
        )
        return
    outcome_id = receipt.envelope.outcome_id
    local_binding = next((binding for binding in local_frontier.bindings if binding.outcome_id == outcome_id), None)
    if local_binding is None:
        _bootstrap_failure("local Builder handoff frontier lacks its exact outcome binding")
    expected_binding = _builder_handoff_settled_binding(snapshot, local_binding, receipt, paths)
    if local_binding.active_claim is not None:
        claim = local_binding.active_claim
        expected_binding = expected_binding.model_copy(update={"active_claim": claim})
        candidate = local_binding.result_candidate
        if candidate is not None:
            _validate_local_builder_handoff_candidate(snapshot, local_binding, receipt, branch_head, paths)
            expected_binding = expected_binding.model_copy(
                update={"result_candidate": candidate, "output": candidate.output}
            )
    expected_frontier = snapshot.frontier.model_copy(
        update={
            "bindings": tuple(
                expected_binding if binding.outcome_id == receipt.envelope.outcome_id else binding
                for binding in snapshot.frontier.bindings
            )
        }
    )
    if local_binding.active_claim is None:
        expected_frontier = _builder_handoff_lifecycle_successor_frontier(
            snapshot.frontier,
            expected_frontier,
            receipt,
            paths.runtime_root,
        )
    if expected_frontier != local_frontier:
        _bootstrap_failure("local Delivery frontier contains state outside the exact Builder handoff")


def _validate_local_builder_return_frontier(
    replay: _BuilderReturnReplayContext,
) -> None:
    """Validate the passive Design handoff or an exact successor of a Builder return."""
    snapshot = replay.snapshot
    local_frontier = replay.local_frontier
    settlement = replay.settlement
    paths = replay.paths
    outcome_id = settlement.envelope.outcome_id
    local_binding = next((binding for binding in local_frontier.bindings if binding.outcome_id == outcome_id), None)
    if local_binding is None or local_binding.builder_handoff_context is None:
        _bootstrap_failure("local Builder return frontier lacks its exact outcome handoff")
    settled_binding = _builder_handoff_settled_binding(snapshot, local_binding, settlement, paths)
    context = local_binding.builder_handoff_context
    if context.route == "same-outcome-planner":
        expected_frontier = _local_planner_return_frontier(replay, local_binding, settled_binding)
    elif context.route == "same-outcome-design":
        if local_binding.stage != DeliveryStage.DESIGN or local_binding != settled_binding:
            _bootstrap_failure("local Design return differs from its exact passive handoff")
        expected_frontier = _local_builder_return_successor_frontier(replay, settled_binding)
    elif context.route == "same-task":
        expected_frontier = _local_promoted_builder_return_frontier(replay, local_binding, settled_binding)
    else:
        _bootstrap_failure("local Builder return has an unsupported handoff route")

    if expected_frontier != local_frontier:
        _bootstrap_failure("local Delivery frontier differs from its exact Builder return promotion")


def _local_planner_return_frontier(
    replay: _BuilderReturnReplayContext,
    local_binding: OutcomeAuthorityBinding,
    settled_binding: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    """Derive the exact Planning-stage successor and its permitted active candidate fields."""
    snapshot = replay.snapshot
    settlement = replay.settlement
    paths = replay.paths
    if (
        local_binding.stage != DeliveryStage.PLANNING
        or local_binding.builder_handoff_context != settlement.handoff_context
    ):
        _bootstrap_failure("local Builder return does not retain its exact Planning handoff")
    promotion = _read_local_builder_plan_promotion_receipt(
        paths.runtime_root,
        snapshot.change_id,
        settlement.settlement_id,
        required=False,
    )
    if promotion is not None:
        _bootstrap_failure("unpromoted Builder return already has a plan promotion receipt")
    history = _planner_handoff_pause_history(replay, settled_binding, local_binding)
    expected_binding = _local_planner_handoff_successor(replay, history, local_binding)
    return _local_builder_return_successor_frontier(replay, expected_binding, history=history)


def _local_promoted_builder_return_frontier(
    replay: _BuilderReturnReplayContext,
    local_binding: OutcomeAuthorityBinding,
    settled_binding: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    """Derive the receipt-backed same-task successor before or after Builder acquisition."""
    snapshot = replay.snapshot
    settlement = replay.settlement
    paths = replay.paths
    if local_binding.stage != DeliveryStage.IMPLEMENTATION:
        _bootstrap_failure("promoted Builder return is not in Implementation")
    promotion = _read_local_builder_plan_promotion_receipt(
        paths.runtime_root,
        snapshot.change_id,
        settlement.settlement_id,
        required=True,
    )
    history = _validate_local_builder_plan_promotion(replay, settled_binding, promotion)
    if promotion.result_binding.builder_handoff_context != local_binding.builder_handoff_context:
        _bootstrap_failure("promoted Builder return lost its exact same-task handoff")
    expected_binding = _promoted_builder_return_successor(replay, local_binding, promotion)
    return _local_builder_return_successor_frontier(replay, expected_binding, promotion=promotion, history=history)


def _promoted_builder_return_successor(
    replay: _BuilderReturnReplayContext,
    local_binding: OutcomeAuthorityBinding,
    promotion: _DeliveryBuilderPlanPromotionReceipt,
) -> OutcomeAuthorityBinding:
    """Allow only the promoted binding or its exact same-task Builder claim and result candidate."""
    expected_binding = promotion.result_binding
    claim = local_binding.active_claim
    if claim is None:
        return expected_binding
    settlement = replay.settlement
    context = settlement.handoff_context
    if (
        claim.worker_role != DeliveryWorkerRole.BUILDER
        or claim.task_id != context.original_task_id
        or claim.attempt_id == settlement.envelope.attempt_id
        or claim.claim_id == settlement.envelope.claim_id
    ):
        _bootstrap_failure("promoted Builder return has an unrelated active claim")
    expected_binding = expected_binding.model_copy(update={"active_claim": claim})
    candidate = local_binding.result_candidate
    if candidate is None:
        return expected_binding
    _validate_local_builder_handoff_candidate(
        replay.snapshot,
        local_binding,
        settlement,
        replay.branch_head,
        replay.paths,
    )
    return expected_binding.model_copy(update={"result_candidate": candidate, "output": candidate.output})


def _local_builder_return_successor_frontier(
    replay: _BuilderReturnReplayContext,
    expected_binding: OutcomeAuthorityBinding,
    *,
    promotion: _DeliveryBuilderPlanPromotionReceipt | None = None,
    history: _PlannerPauseHistory | None = None,
) -> DeliveryFrontier:
    """Replace only the exact handoff row and fold any authenticated lifecycle receipts."""
    snapshot = replay.snapshot
    local_frontier = replay.local_frontier
    settlement = replay.settlement
    outcome_id = settlement.envelope.outcome_id
    expected_frontier = snapshot.frontier.model_copy(
        update={
            "bindings": tuple(
                expected_binding if binding.outcome_id == outcome_id else binding
                for binding in snapshot.frontier.bindings
            )
        }
    )
    if next(binding for binding in local_frontier.bindings if binding.outcome_id == outcome_id).active_claim is None:
        if history is not None:
            return _planner_handoff_lifecycle_successor_frontier(replay, expected_frontier, history, promotion)
        return _builder_handoff_lifecycle_successor_frontier(
            snapshot.frontier,
            expected_frontier,
            settlement,
            replay.paths.runtime_root,
        )
    return expected_frontier


def _local_planner_handoff_successor(
    replay: _BuilderReturnReplayContext,
    history: _PlannerPauseHistory,
    local_binding: OutcomeAuthorityBinding,
) -> OutcomeAuthorityBinding:
    """Allow only receipt-chained Planner pauses, answers, one active claim, and its canonical candidate."""
    settlement = replay.settlement
    claim = local_binding.active_claim
    candidate = local_binding.candidate
    if claim is None:
        if candidate is not None:
            _bootstrap_failure("local Planner candidate has no active Planner claim")
        return history.latest
    claimable_binding = _claimable_planner_handoff_binding(history)
    if (
        claim.worker_role != DeliveryWorkerRole.PLANNER
        or claim.task_id is not None
        or claim.attempt_id == settlement.envelope.attempt_id
        or claim.claim_id == settlement.envelope.claim_id
    ):
        _bootstrap_failure("local Builder return has an unrelated active Planner claim")
    if candidate is None:
        return claimable_binding.model_copy(update={"active_claim": claim})
    _validate_local_builder_plan_candidate(replay.snapshot, history.settled, claim, candidate)
    return claimable_binding.model_copy(
        update={"active_claim": claim, "candidate": candidate, "output": candidate.output}
    )


def _claimable_planner_handoff_binding(history: _PlannerPauseHistory) -> OutcomeAuthorityBinding:
    """Return the settled or answered Planning row a fresh Planner claim may hold."""
    binding = history.latest
    if binding.block is not None and not binding.block.resolved:
        _bootstrap_failure("local Planner claim overlaps an unanswered Planning pause")
    return binding


def _planner_handoff_pause_history(
    replay: _BuilderReturnReplayContext,
    settled_binding: OutcomeAuthorityBinding,
    local_binding: OutcomeAuthorityBinding,
) -> _PlannerPauseHistory:
    """Chain every Planner request pause to its immutable receipt and derive the latest claimless row."""
    settled_requests = settled_binding.requests
    if local_binding.requests[: len(settled_requests)] != settled_requests:
        _bootstrap_failure("local Planner pause differs from its exact Planning pause receipt")
    receipts = _read_planner_handoff_pause_receipts(replay, settled_binding)
    claim_ids = {replay.settlement.envelope.claim_id}
    answered_requests: list[DeliveryRequest] = []
    paused: list[OutcomeAuthorityBinding] = []
    answered: list[OutcomeAuthorityBinding] = []
    for index, local_request in enumerate(local_binding.requests[len(settled_requests) :]):
        if len(answered_requests) != index:
            _bootstrap_failure("local Planner pause answer has no recorded resolution")
        path, receipt = receipts.pop(local_request.request_id, (None, None))
        expected = (
            None
            if path is None or receipt is None or receipt.claim_id in claim_ids
            else _planner_handoff_receipt_pause(replay, path, receipt, settled_binding, tuple(answered_requests))
        )
        if receipt is None or expected is None:
            _bootstrap_failure("local Planner pause differs from its exact Planning pause receipt")
        claim_ids.add(receipt.claim_id)
        paused.append(expected)
        if local_request.resolution is not None:
            answered_row = _planner_handoff_answered_request(expected, local_request, settled_binding)
            answered.append(answered_row)
            answered_requests.append(answered_row.requests[-1])
    if receipts:
        _bootstrap_failure("local Planning pause receipt is outside its exact Planner pause sequence")
    history = _PlannerPauseHistory(
        settled=settled_binding,
        answered_requests=tuple(answered_requests),
        paused=tuple(paused),
        answered=tuple(answered),
        latest=settled_binding,
    )
    latest = (
        _exhausted_planner_handoff_row(history, local_binding.block)
        if settled_binding.block is not None
        else _planner_handoff_latest_row(history, local_binding.block)
    )
    return replace(history, latest=latest)


def _exhausted_planner_handoff_row(
    history: _PlannerPauseHistory,
    block: DeliveryBlock | None,
) -> OutcomeAuthorityBinding:
    """Admit only the unchanged read-only settlement of an exhausted Builder return."""
    if history.paused or block != history.settled.block:
        _bootstrap_failure("local exhausted Builder return differs from its exact settlement")
    return history.settled


def _read_planner_handoff_pause_receipts(
    replay: _BuilderReturnReplayContext,
    settled_binding: OutcomeAuthorityBinding,
) -> dict[str, tuple[Path, _DeliveryPlanningPauseReplay]]:
    """Read every request-bearing Planning pause receipt bound to this exact Planner handoff."""
    changes_root = replay.paths.runtime_root / "changes"
    receipt_root = changes_root / replay.snapshot.change_id / "planning-pause-receipts"
    receipt_directory = receipt_root / settled_binding.outcome_id
    if any(path.is_symlink() for path in (changes_root, receipt_root.parent, receipt_root, receipt_directory)):
        _bootstrap_failure("local Planning pause receipt path is unsafe")
    receipts: dict[str, tuple[Path, _DeliveryPlanningPauseReplay]] = {}
    for path in sorted(receipt_directory.glob("*.json")) if receipt_directory.is_dir() else []:
        if path.is_symlink() or not path.is_file():
            _bootstrap_failure("local Planning pause receipt path is unsafe")
        try:
            receipt = _DeliveryPlanningPauseReplay.model_validate_json(path.read_bytes(), strict=True)
        except (OSError, TypeError, ValueError) as exc:
            _bootstrap_failure("local Planning pause receipt is invalid", exc)
        request = receipt.request.request
        if request is None or receipt.result.builder_handoff_context != settled_binding.builder_handoff_context:
            continue
        if request.request_id in receipts:
            _bootstrap_failure("local Planning pause receipt is outside its exact Planner pause sequence")
        receipts[request.request_id] = (path, receipt)
    return receipts


def _planner_handoff_receipt_pause(
    replay: _BuilderReturnReplayContext,
    path: Path,
    receipt: _DeliveryPlanningPauseReplay,
    settled_binding: OutcomeAuthorityBinding,
    answered_requests: tuple[DeliveryRequest, ...],
) -> OutcomeAuthorityBinding | None:
    """Return the paused row one receipt binds over the settled row and every earlier answer."""
    transition = receipt.request
    request = transition.request
    if request is None:
        return None
    prior_requests = (*settled_binding.requests, *answered_requests)
    paused = _planner_handoff_paused_binding(
        settled_binding,
        DeliveryBlock(
            block_id=transition.block_id,
            reason=transition.reason,
            unblock_condition=transition.unblock_condition,
            expected_evidence=transition.expected_evidence,
            locators=transition.locators,
            request_id=request.request_id,
            resume_commit=transition.resume_commit,
        ),
        (*prior_requests, request),
    )
    matches = all(
        (
            receipt.change_id == replay.snapshot.change_id,
            receipt.outcome_id == settled_binding.outcome_id,
            path.name == f"{receipt.request_digest}.json",
            transition.resume_commit is None,
            request.resolution is None,
            request.request_id not in {item.request_id for item in prior_requests},
            receipt.result == paused,
        )
    )
    return paused if matches else None


def _planner_handoff_latest_row(
    history: _PlannerPauseHistory,
    block: DeliveryBlock | None,
) -> OutcomeAuthorityBinding:
    """Derive the settled row, the latest receipt-backed pause, or a requestless pause, with any answer."""
    if block is None:
        if history.paused:
            _bootstrap_failure("local Planner pause differs from its exact Planning pause receipt")
        return history.settled
    if block.request_id is None:
        if block.resume_commit is not None:
            _bootstrap_failure("local Planner pause has an Implementation resume commit")
        if len(history.answered) != len(history.paused):
            _bootstrap_failure("local Planner pause answer has no recorded resolution")
        paused = _planner_handoff_requestless_pause(history, block, len(history.answered_requests))
        return _planner_handoff_cleared_pause(paused, block, history.settled) if block.resolved else paused
    latest_block = history.paused[-1].block if history.paused else None
    if latest_block is None or latest_block.request_id != block.request_id:
        _bootstrap_failure("local Planner pause differs from its exact Planning pause receipt")
    if not block.resolved:
        return history.paused[-1]
    if len(history.answered) != len(history.paused):
        _bootstrap_failure("local Planner pause answer has no recorded resolution")
    return history.answered[-1]


def _planner_handoff_paused_binding(
    settled_binding: OutcomeAuthorityBinding,
    block: DeliveryBlock,
    requests: tuple[DeliveryRequest, ...],
) -> OutcomeAuthorityBinding:
    """Mirror the runtime Planning block over the exact settled Builder return."""
    return settled_binding.model_copy(
        update={
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "recovery_attention": None,
            "retry_diagnostic": None,
            "block": block,
            "requests": requests,
        }
    )


def _planner_handoff_requestless_pause(
    history: _PlannerPauseHistory,
    block: DeliveryBlock,
    answered_count: int,
) -> OutcomeAuthorityBinding:
    """Mirror one requestless Planner block over the settled row and its first answered requests."""
    return _planner_handoff_paused_binding(
        history.settled,
        block.model_copy(update={"resolution_note": None, "resolution_locators": ()}),
        (*history.settled.requests, *history.answered_requests[:answered_count]),
    )


def _planner_handoff_cleared_pause(
    paused: OutcomeAuthorityBinding,
    block: DeliveryBlock,
    settled_binding: OutcomeAuthorityBinding,
) -> OutcomeAuthorityBinding:
    """Derive the operator clearance that restores the retained Planning context."""
    if not block.resolution_note or not block.resolution_locators:
        _bootstrap_failure("local Planner requestless clearance lacks operator evidence")
    return paused.model_copy(update={"block": block, "return_context": settled_binding.return_context})


def _planner_handoff_answered_request(
    paused: OutcomeAuthorityBinding,
    local_request: DeliveryRequest,
    settled_binding: OutcomeAuthorityBinding,
) -> OutcomeAuthorityBinding:
    """Derive the recorded answer that restores the retained Planning context."""
    block = paused.block
    original = paused.requests[-1]
    resolution = local_request.resolution
    if block is None or block.request_id is None or resolution is None:
        _bootstrap_failure("local Planner pause answer has no recorded resolution")
    if (original.kind == DeliveryRequestKind.DECISION and resolution.selected_option_id is None) or (
        resolution.selected_option_id is not None
        and resolution.selected_option_id not in {option.option_id for option in original.options}
    ):
        _bootstrap_failure("local Planner pause answer does not answer its exact bounded options")
    return paused.model_copy(
        update={
            "requests": (*paused.requests[:-1], original.model_copy(update={"resolution": resolution})),
            "block": block.model_copy(
                update={
                    "resolution_note": resolution.response_text or resolution.selected_option_id,
                    "resolution_locators": (block.request_id,),
                }
            ),
            "return_context": settled_binding.return_context,
        }
    )


def _planner_handoff_lifecycle_rank(
    history: _PlannerPauseHistory,
    row: OutcomeAuthorityBinding,
    promotion: _DeliveryBuilderPlanPromotionReceipt | None,
) -> int | None:
    """Order one claimless row within the exact receipt-chained Planner pause history."""
    if promotion is not None and row == promotion.result_binding:
        return 3 * len(history.paused) + 4
    known = (
        (0, history.settled),
        *((3 * index + 2, item) for index, item in enumerate(history.paused)),
        *((3 * index + 3, item) for index, item in enumerate(history.answered)),
    )
    rank = next((rank for rank, item in known if item == row), None)
    block = row.block
    if rank is not None or block is None or block.request_id is not None or block.resume_commit is not None:
        return rank
    for answered_count in range(len(history.answered_requests) + 1):
        paused = _planner_handoff_requestless_pause(history, block, answered_count)
        cleared = paused.model_copy(update={"block": block, "return_context": history.settled.return_context})
        if row == paused or (block.resolution_note and block.resolution_locators and row == cleared):
            return 3 * answered_count + 1
    return None


def _validate_local_builder_plan_candidate(
    snapshot: DeliveryStateSnapshot,
    settled_binding: OutcomeAuthorityBinding,
    planner_claim: DeliveryActiveClaim,
    candidate: DeliveryPlanCandidate,
) -> None:
    """Validate one claim-bound, canonical same-outcome Planner return candidate."""
    context = settled_binding.builder_handoff_context
    tasks = candidate.tasks
    task_ids = tuple(task.task_id for task in tasks)
    task_map = {task.task_id: task for task in tasks}
    source_tasks = {task.task_id: task for task in settled_binding.tasks}
    completed_task_ids = {result.task_id for result in settled_binding.results}
    contract_outcome = next(
        (outcome for outcome in snapshot.contract.outcomes if outcome.outcome_id == settled_binding.outcome_id),
        None,
    )
    digest = hashlib.sha256(b"".join(_model_content(task) for task in tasks)).hexdigest()
    original_task = task_map.get(context.original_task_id)
    if contract_outcome is None or original_task is None:
        _bootstrap_failure("local Planner candidate lacks its exact outcome or original task")
    if not all(
        (
            planner_claim.worker_role == DeliveryWorkerRole.PLANNER,
            planner_claim.task_id is None,
            candidate.claim_id == planner_claim.claim_id,
            candidate.candidate_id == f"plan-{digest}",
            candidate.digest == digest,
            len(task_ids) == len(set(task_ids)),
            all(
                task.outcome_id == settled_binding.outcome_id
                and task.plan_scope_id == settled_binding.plan_scope_id
                and set(task.commitment_ids) <= set(contract_outcome.commitment_ids)
                and set(task.dependency_ids) <= set(task_ids)
                and task.task_id not in task.dependency_ids
                for task in tasks
            ),
            all(
                result.task_id in task_map
                and result.task_digest == source_tasks[result.task_id].digest
                and task_map[result.task_id] == source_tasks[result.task_id]
                for result in settled_binding.results
            ),
            original_task.task_id not in completed_task_ids,
            original_task.commitment_ids == context.original_task_commitment_ids,
            original_task.maintained_surfaces == context.original_task_maintained_surfaces,
            set(original_task.dependency_ids) <= completed_task_ids,
        )
    ):
        _bootstrap_failure("local Planner candidate differs from its exact task, result, or scope authority")
    ready = {task.task_id for task in tasks if not task.dependency_ids}
    visited = set(ready)
    while True:
        expanded = visited | {task.task_id for task in tasks if set(task.dependency_ids) <= visited}
        if expanded == visited:
            break
        visited = expanded
    if not ready or visited != set(task_ids):
        _bootstrap_failure("local Planner candidate does not contain an acyclic task chain")


def _validate_local_builder_plan_promotion(
    replay: _BuilderReturnReplayContext,
    settled_binding: OutcomeAuthorityBinding,
    promotion: _DeliveryBuilderPlanPromotionReceipt,
) -> _PlannerPauseHistory:
    """Require the exact Planner claim, candidate, and successor bound to the original return."""
    snapshot = replay.snapshot
    settlement = replay.settlement
    claim = promotion.planner_claim
    if (
        promotion.change_id != snapshot.change_id
        or promotion.outcome_id != settlement.envelope.outcome_id
        or promotion.settlement_id != settlement.settlement_id
        or promotion.source_binding.builder_handoff_context != settlement.handoff_context
        or claim.attempt_id == settlement.envelope.attempt_id
        or claim.claim_id == settlement.envelope.claim_id
    ):
        _bootstrap_failure("local Builder plan promotion receipt has a foreign identity")
    _validate_local_builder_plan_candidate(snapshot, settled_binding, claim, promotion.candidate)
    history = _planner_handoff_pause_history(replay, settled_binding, promotion.source_binding)
    expected_source = _claimable_planner_handoff_binding(history).model_copy(
        update={
            "active_claim": claim,
            "candidate": promotion.candidate,
            "output": promotion.candidate.output,
        }
    )
    if promotion.source_binding != expected_source:
        _bootstrap_failure("local Builder plan promotion receipt does not retain its exact Planner source row")
    return history


def _builder_handoff_settled_binding(
    snapshot: DeliveryStateSnapshot,
    local_binding: OutcomeAuthorityBinding,
    receipt: _DeliveryBuilderInvocationSettlementReceipt,
    paths: _DeliveryPaths,
) -> OutcomeAuthorityBinding:
    """Derive the exact immutable retry or request-bearing pause result."""
    envelope = receipt.envelope
    snapshot_binding = next(
        (binding for binding in snapshot.frontier.bindings if binding.outcome_id == envelope.outcome_id),
        None,
    )
    if snapshot_binding is None:
        _bootstrap_failure("local Builder handoff outcome is absent from its remote snapshot")
    if isinstance(envelope.request, BlockDelivery):
        expected_result = DeliveryRuntime._builder_pause_settled_binding(  # noqa: SLF001
            snapshot_binding,
            receipt.handoff_context,
            envelope.request,
        )
        if receipt.result != expected_result:
            _bootstrap_failure("local Builder pause result is not the exact successor of its remote binding")
        if local_binding != expected_result:
            return _builder_request_resolution_successor(paths.runtime_root, snapshot, receipt)
        return expected_result
    if isinstance(envelope.request, ReturnDelivery):
        if envelope.request.target not in {DeliveryStage.PLANNING, DeliveryStage.DESIGN}:
            _bootstrap_failure("local Builder return settlement has an unsupported target")
        expected_results = tuple(
            DeliveryRuntime._builder_return_settled_binding(  # noqa: SLF001
                snapshot_binding,
                receipt.handoff_context,
                envelope.request,
                exhausted=exhausted,
            )
            for exhausted in (False, True)
        )
        if receipt.result not in expected_results:
            _bootstrap_failure("local Builder return result is not the exact successor of its remote binding")
        return receipt.result
    requestless = envelope.disposition in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES and envelope.request is None
    if not isinstance(envelope.request, RetryDelivery) and not requestless:
        _bootstrap_failure("local Builder handoff route is unsupported")
    expected_results = tuple(
        DeliveryRuntime._builder_retry_settled_binding(  # noqa: SLF001
            snapshot_binding,
            receipt.handoff_context,
            envelope,
            exhausted=exhausted,
        )
        for exhausted in (False, True)
    )
    if receipt.result not in expected_results:
        _bootstrap_failure("local Builder handoff result is not the exact retry successor of its remote binding")
    return receipt.result


def _builder_handoff_lifecycle_successor_frontier(
    snapshot_frontier: DeliveryFrontier,
    expected_frontier: DeliveryFrontier,
    settlement: _DeliveryBuilderInvocationSettlementReceipt,
    runtime_root: Path,
) -> DeliveryFrontier:
    """Fold exact local lifecycle receipts over a known Builder settlement or answer."""
    chain = _builder_handoff_lifecycle_chain(runtime_root, settlement)
    if not chain:
        return expected_frontier

    baselines, resolved_frontier, settlement_frontier = _builder_handoff_lifecycle_baselines(
        snapshot_frontier,
        expected_frontier,
        settlement,
    )
    lifecycle_fields = ("change_deferral", "change_abandonment", "pending_checkpoint")
    previous_frontier: DeliveryFrontier | None = None
    previous_baseline: DeliveryFrontier | None = None
    for item in chain:
        baseline = next(
            (
                candidate
                for candidate in baselines
                if _builder_handoff_frontier_with_lifecycle_fields(candidate, item.before_frontier)
                == item.before_frontier
            ),
            None,
        )
        if baseline is None:
            _bootstrap_failure("local Builder lifecycle intent is not anchored to its exact settlement or answer")
        if _builder_handoff_frontier_with_lifecycle_fields(baseline, item.after_frontier) != item.after_frontier:
            _bootstrap_failure("local Builder lifecycle intent receipt changes unsupported frontier state")

        if previous_frontier is not None and item.before_frontier != previous_frontier:
            resolved_after_answer = (
                previous_baseline == settlement_frontier
                and resolved_frontier is not None
                and baseline == resolved_frontier
                and all(
                    getattr(previous_frontier, field_name) == getattr(item.before_frontier, field_name)
                    for field_name in lifecycle_fields
                )
            )
            if not resolved_after_answer:
                _bootstrap_failure("local Builder lifecycle intent chain contains an unrecorded frontier transition")

        previous_frontier = item.after_frontier
        previous_baseline = baseline

    return _builder_handoff_frontier_with_lifecycle_fields(expected_frontier, chain[-1].after_frontier)


def _builder_handoff_lifecycle_chain(
    runtime_root: Path,
    settlement: _DeliveryBuilderInvocationSettlementReceipt,
) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...]:
    """Read the exact lifecycle receipt chain addressed by one Builder settlement."""
    try:
        return _read_builder_handoff_change_intent_receipts(
            runtime_root,
            settlement.envelope.change_id,
            settlement.handoff_context,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        _bootstrap_failure("local Builder lifecycle intent receipt chain is unavailable or invalid", exc)


def _planner_handoff_lifecycle_successor_frontier(
    replay: _BuilderReturnReplayContext,
    expected_frontier: DeliveryFrontier,
    history: _PlannerPauseHistory,
    promotion: _DeliveryBuilderPlanPromotionReceipt | None,
) -> DeliveryFrontier:
    """Fold lifecycle receipts anchored in order to the settlement, Planner pauses, answers, or promotion."""
    chain = _builder_handoff_lifecycle_chain(replay.paths.runtime_root, replay.settlement)
    if not chain:
        return expected_frontier
    snapshot_frontier = replay.snapshot.frontier
    outcome_id = replay.settlement.envelope.outcome_id
    current_rank = _planner_handoff_lifecycle_rank(
        history,
        history.latest if promotion is None else promotion.result_binding,
        promotion,
    )
    previous: tuple[DeliveryFrontier, int] | None = None
    for item in chain:
        row = next((binding for binding in item.before_frontier.bindings if binding.outcome_id == outcome_id), None)
        rank = None if row is None else _planner_handoff_lifecycle_rank(history, row, promotion)
        if rank is None or current_rank is None or rank > current_rank:
            _bootstrap_failure("local Builder lifecycle intent is not anchored to its exact settlement or answer")
        baseline = snapshot_frontier.model_copy(
            update={
                "bindings": tuple(
                    row if binding.outcome_id == outcome_id else binding for binding in snapshot_frontier.bindings
                )
            }
        )
        if _builder_handoff_frontier_with_lifecycle_fields(baseline, item.before_frontier) != item.before_frontier:
            _bootstrap_failure("local Builder lifecycle intent is not anchored to its exact settlement or answer")
        if _builder_handoff_frontier_with_lifecycle_fields(baseline, item.after_frontier) != item.after_frontier:
            _bootstrap_failure("local Builder lifecycle intent receipt changes unsupported frontier state")
        if (
            previous is not None
            and item.before_frontier != previous[0]
            and (
                rank < previous[1]
                or _builder_handoff_frontier_with_lifecycle_fields(item.before_frontier, previous[0])
                != item.before_frontier
            )
        ):
            _bootstrap_failure("local Builder lifecycle intent chain contains an unrecorded frontier transition")
        previous = (item.after_frontier, rank)
    return _builder_handoff_frontier_with_lifecycle_fields(expected_frontier, chain[-1].after_frontier)


def _builder_handoff_lifecycle_baselines(
    snapshot_frontier: DeliveryFrontier,
    expected_frontier: DeliveryFrontier,
    settlement: _DeliveryBuilderInvocationSettlementReceipt,
) -> tuple[tuple[DeliveryFrontier, ...], DeliveryFrontier | None, DeliveryFrontier]:
    """Select only a settlement or answered pause as a lifecycle baseline."""
    outcome_id = settlement.envelope.outcome_id
    settlement_frontier = snapshot_frontier.model_copy(
        update={
            "bindings": tuple(
                settlement.result if binding.outcome_id == outcome_id else binding
                for binding in snapshot_frontier.bindings
            )
        }
    )
    if expected_frontier == settlement_frontier:
        resolved_frontier = None
        baselines = (settlement_frontier,)
    elif isinstance(settlement.envelope.request, BlockDelivery):
        resolved_frontier = expected_frontier
        baselines = (settlement_frontier, resolved_frontier)
    else:
        _bootstrap_failure("local Builder lifecycle intent has an unknown request-resolution baseline")
    return baselines, resolved_frontier, settlement_frontier


def _builder_handoff_frontier_with_lifecycle_fields(
    frontier: DeliveryFrontier,
    lifecycle_frontier: DeliveryFrontier,
) -> DeliveryFrontier:
    """Copy only fields permitted to change in a Builder handoff lifecycle receipt."""
    lifecycle_fields = ("change_deferral", "change_abandonment", "pending_checkpoint")
    return frontier.model_copy(
        update={field_name: getattr(lifecycle_frontier, field_name) for field_name in lifecycle_fields}
    )


def _validate_local_builder_handoff_candidate(
    snapshot: DeliveryStateSnapshot,
    local_binding: OutcomeAuthorityBinding,
    receipt: _DeliveryBuilderInvocationSettlementReceipt,
    branch_head: str,
    paths: _DeliveryPaths,
) -> None:
    """Validate one candidate against its exact same-task claim and commit ancestry."""
    candidate = local_binding.result_candidate
    claim = local_binding.active_claim
    task = next(
        (item for item in local_binding.tasks if item.task_id == receipt.handoff_context.original_task_id),
        None,
    )
    if candidate is None or claim is None or task is None:
        _bootstrap_failure("local Builder result candidate lacks its exact task or active claim")
    result_digest = hashlib.sha256(_canonical_model(candidate.result)).hexdigest()
    if not all(
        (
            claim.worker_role == DeliveryWorkerRole.BUILDER,
            claim.task_id == task.task_id,
            candidate.claim_id == claim.claim_id,
            candidate.candidate_id == f"result-{result_digest}",
            candidate.digest == result_digest,
            candidate.result.change_id == snapshot.change_id,
            candidate.result.authority_digest == snapshot.authority_digest,
            candidate.result.task_id == task.task_id,
            candidate.result.task_digest == task.digest,
            _loader_git_is_ancestor(
                paths.repository_root,
                receipt.handoff_context.branch_head,
                candidate.result.completed_commit,
            ),
            _loader_git_is_ancestor(paths.repository_root, candidate.result.completed_commit, branch_head),
        )
    ):
        _bootstrap_failure("local Builder result candidate differs from its exact active claim and task")


def _builder_request_resolution_successor(
    runtime_root: Path,
    snapshot: DeliveryStateSnapshot,
    settlement: _DeliveryBuilderInvocationSettlementReceipt,
) -> OutcomeAuthorityBinding:
    """Derive only the exact request and block resolution recorded for one local pause."""
    envelope = settlement.envelope
    block_request = envelope.request
    if not isinstance(block_request, BlockDelivery) or block_request.request is None:
        _bootstrap_failure("local Builder handoff has no exact request-bearing pause")
    original_request = block_request.request
    original_block = settlement.result.block
    if original_block is None or original_block.request_id != original_request.request_id:
        _bootstrap_failure("local Builder pause result does not retain its exact request block")
    try:
        resolution_receipt = _read_builder_request_resolution_receipt(
            runtime_root,
            snapshot.change_id,
            original_request.request_id,
            settlement.handoff_context,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        _bootstrap_failure("local Builder request resolution receipt is unavailable or invalid", exc)

    resolution = resolution_receipt.resolved_request.resolution
    if resolution is None:
        _bootstrap_failure("local Builder request resolution receipt has no user answer")
    if (original_request.kind == DeliveryRequestKind.DECISION and resolution.selected_option_id is None) or (
        resolution.selected_option_id is not None
        and resolution.selected_option_id not in {option.option_id for option in original_request.options}
    ):
        _bootstrap_failure("local Builder request resolution does not answer its exact bounded options")
    expected_request = original_request.model_copy(update={"resolution": resolution})
    expected_block = original_block.model_copy(
        update={
            "resolution_note": resolution.response_text or resolution.selected_option_id,
            "resolution_locators": (original_request.request_id,),
        }
    )
    if not all(
        (
            resolution_receipt.change_id == snapshot.change_id,
            resolution_receipt.outcome_id == envelope.outcome_id,
            resolution_receipt.request_id == original_request.request_id,
            resolution_receipt.settlement_id == settlement.settlement_id,
            resolution_receipt.builder_handoff_context == settlement.handoff_context,
            resolution_receipt.resolved_request == expected_request,
            resolution_receipt.updated_block == expected_block,
        )
    ):
        _bootstrap_failure("local Builder request resolution receipt differs from its exact settlement pause")
    return settlement.result.model_copy(
        update={
            "requests": tuple(
                expected_request if request.request_id == original_request.request_id else request
                for request in settlement.result.requests
            ),
            "block": expected_block,
        }
    )


def _builder_handoff_owner_matches(
    coordination: ChangeCoordination,
    binding: OutcomeAuthorityBinding,
    context: DeliveryBuilderHandoffContext,
    envelope: DeliveryBuilderInvocationSettlement,
) -> bool:
    """Match a retained handoff or its exact newly acquired Builder claim."""
    writer = coordination.writer
    if writer is None or coordination.change_id != envelope.change_id:
        return False
    handoff = coordination.builder_handoff
    if handoff is not None:
        if not all(
            (
                handoff.change_id == envelope.change_id,
                writer == handoff.original_writer.model_copy(update={"kind": "handoff"}),
                handoff.settlement_id == context.settlement_id,
                handoff.original_task_id == context.original_task_id,
                handoff.last_reviewed_commit == context.last_reviewed_commit,
                handoff.branch_head == context.branch_head,
                handoff.metadata_fingerprint == context.metadata_fingerprint,
            )
        ):
            return False
        claim = binding.active_claim
        if claim is None:
            return True
        return (
            context.route == "same-outcome-planner"
            and binding.stage == DeliveryStage.PLANNING
            and claim.worker_role == DeliveryWorkerRole.PLANNER
            and claim.task_id is None
            and claim.attempt_id != envelope.attempt_id
            and claim.claim_id != envelope.claim_id
        )
    claim = binding.active_claim
    return (
        claim is not None
        and claim.worker_role == DeliveryWorkerRole.BUILDER
        and claim.task_id == context.original_task_id
        and claim.attempt_id != envelope.attempt_id
        and claim.claim_id != envelope.claim_id
        and writer.kind == "build"
        and writer.attempt_id == claim.attempt_id
        and writer.claim_id == claim.claim_id
        and writer.actor_id == claim.owner_id
        and writer.process_id == claim.process_id
        and writer.claimed_at == claim.started_at
    )


def _read_local_builder_handoff_receipt(
    runtime_root: Path,
    change_id: str,
    context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderInvocationSettlementReceipt:
    """Read one exact immutable Builder settlement receipt without constructing a runtime."""
    attempt_digest = hashlib.sha256(context.attempt_id.encode("utf-8")).hexdigest()
    change_root = runtime_root / "changes" / change_id
    receipt_directory = change_root / "builder-invocation-receipts"
    receipt_path = receipt_directory / f"{attempt_digest}.json"
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_directory, receipt_path)):
        _bootstrap_failure("local Builder handoff receipt path is unsafe")
    if not receipt_path.is_file():
        _bootstrap_failure("local Builder handoff settlement receipt is missing")
    try:
        return _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(receipt_path.read_bytes(), strict=True)
    except (OSError, TypeError, ValueError) as exc:
        _bootstrap_failure("local Builder handoff settlement receipt is invalid", exc)


def _read_local_builder_plan_promotion_receipt(
    runtime_root: Path,
    change_id: str,
    settlement_id: str,
    *,
    required: bool,
) -> _DeliveryBuilderPlanPromotionReceipt | None:
    """Read one exact host-local Planning promotion receipt without constructing a runtime."""
    change_root = runtime_root / "changes" / change_id
    receipt_directory = change_root / "builder-plan-promotion-receipts"
    receipt_path = receipt_directory / f"{settlement_id}.json"
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_directory, receipt_path)):
        _bootstrap_failure("local Builder plan promotion receipt path is unsafe")
    if not receipt_path.exists():
        if required:
            _bootstrap_failure("local Builder plan promotion receipt is missing")
        return None
    if not receipt_path.is_file():
        _bootstrap_failure("local Builder plan promotion receipt is not a regular file")
    try:
        return _DeliveryBuilderPlanPromotionReceipt.model_validate_json(receipt_path.read_bytes(), strict=True)
    except (OSError, TypeError, ValueError) as exc:
        _bootstrap_failure("local Builder plan promotion receipt is invalid", exc)


def _is_unpublished_checkpoint_successor(
    snapshot_frontier: DeliveryFrontier,
    local_frontier: DeliveryFrontier,
) -> bool:
    """Recognize a local checkpoint retained until Change reconciliation."""
    pending = local_frontier.pending_checkpoint
    if (
        snapshot_frontier.pending_checkpoint is not None
        or pending is None
        or pending.head is None
        or local_frontier.published_head != pending.head
        or snapshot_frontier.published_head != pending.head
    ):
        return False
    return snapshot_frontier == local_frontier.model_copy(update={"pending_checkpoint": None})


def _is_unpublished_acceptance_attention_successor(
    snapshot_frontier: DeliveryFrontier,
    local_frontier: DeliveryFrontier,
) -> bool:
    """Recognize a local acceptance attention captured after the last state snapshot."""
    disposition = local_frontier.change_disposition
    if (
        snapshot_frontier.change_disposition is not None
        or disposition is None
        or disposition.kind != DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
        or local_frontier.change_disposition_resolution is not None
        or local_frontier.ready is not None
    ):
        return False
    common_attention_fields = {
        "change_disposition": None,
        "change_disposition_publication": None,
        "change_disposition_resolution": None,
        "ready": None,
    }
    if (
        snapshot_frontier.finalization == local_frontier.finalization
        and snapshot_frontier.finalization_invalidation == local_frontier.finalization_invalidation
        and snapshot_frontier.model_copy(update=common_attention_fields)
        == local_frontier.model_copy(update=common_attention_fields)
    ):
        return True
    if disposition.acceptance_reason != DeliveryAcceptanceAttentionReason.HEAD_MOVED:
        return False
    snapshot_finalization = snapshot_frontier.finalization
    local_invalidation = local_frontier.finalization_invalidation
    if (
        snapshot_finalization is None
        or snapshot_frontier.finalization_invalidation is not None
        or local_frontier.finalization is not None
        or local_invalidation is None
        or local_invalidation.change_id != snapshot_finalization.change_id
        or local_invalidation.finalization_id != snapshot_finalization.finalization_id
        or local_invalidation.expected_head != snapshot_finalization.exact_head
        or local_invalidation.observed_head == snapshot_finalization.exact_head
        or local_invalidation.reason != "head-drift"
    ):
        return False
    transition_fields = {
        **common_attention_fields,
        "finalization": None,
        "finalization_invalidation": None,
    }
    return snapshot_frontier.model_copy(update=transition_fields) == local_frontier.model_copy(update=transition_fields)


def _is_unpublished_target_sync_attention_successor(
    snapshot_frontier: DeliveryFrontier,
    local_frontier: DeliveryFrontier,
) -> bool:
    """Recognize a local target-sync conflict captured after the last state snapshot."""
    disposition = local_frontier.change_disposition
    if (
        snapshot_frontier.change_disposition is not None
        or disposition is None
        or disposition.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION
        or not any(item.startswith("target-sync-operation:") for item in disposition.diagnostics)
        or local_frontier.change_disposition_resolution is not None
        or local_frontier.ready is not None
        or local_frontier.target_sync_receipt is not None
    ):
        return False

    attention_fields = {
        "target_sync_receipt": None,
        "change_disposition": None,
        "change_disposition_publication": None,
        "change_disposition_resolution": None,
        "ready": None,
    }
    if snapshot_frontier.finalization is None:
        return (
            local_frontier.finalization is None
            and local_frontier.finalization_invalidation is None
            and snapshot_frontier.model_copy(update=attention_fields)
            == local_frontier.model_copy(update=attention_fields)
        )

    invalidation = local_frontier.finalization_invalidation
    if (
        snapshot_frontier.finalization_invalidation is not None
        or local_frontier.finalization is not None
        or invalidation is None
        or invalidation.change_id != snapshot_frontier.finalization.change_id
        or invalidation.finalization_id != snapshot_frontier.finalization.finalization_id
        or invalidation.expected_head != snapshot_frontier.finalization.exact_head
        or invalidation.observed_head == snapshot_frontier.finalization.exact_head
        or invalidation.reason != "target-sync-conflict"
    ):
        return False
    transition_fields = {
        **attention_fields,
        "finalization": None,
        "finalization_invalidation": None,
    }
    return snapshot_frontier.model_copy(update=transition_fields) == local_frontier.model_copy(update=transition_fields)


def _fetch_completed_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    repository: Path,
) -> tuple[str, bool]:
    """Validate a completed snapshot against the configured target branch."""
    if snapshot.frontier.change_completion is None:
        _bootstrap_failure("remote Change branch is missing for an active Delivery snapshot")
    target_ref = f"refs/remotes/{config.remote}/{config.target_branch}"
    target_head = _loader_git_output(repository, "rev-parse", "--verify", f"{target_ref}^{{commit}}")
    if target_head is None:
        _bootstrap_failure("configured target head is unavailable for a completed snapshot")
    latch = snapshot.frontier.merged_pull_request_latch
    if latch is None:
        _bootstrap_failure("completed Delivery snapshot has no accepted merge identity")
    if (
        _run_loader_git(
            repository,
            "merge-base",
            "--is-ancestor",
            latch.accepted_merge_commit,
            target_ref,
            check=False,
        ).returncode
        != 0
    ):
        _bootstrap_failure("accepted merge commit is not present on the configured target")
    return latch.accepted_merge_commit, False


def _fetch_finalized_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    repository: Path,
) -> tuple[str, bool]:
    """Validate finalized authority against the configured target after branch deletion."""
    finalization = snapshot.frontier.finalization
    if finalization is None:
        _bootstrap_failure("finalized Delivery snapshot has no finalization authority")
    if finalization.exact_head != snapshot.change_head:
        _bootstrap_failure("finalized Delivery snapshot head does not match its finalization authority")
    target_ref = f"refs/remotes/{config.remote}/{config.target_branch}"
    target_head = _loader_git_output(repository, "rev-parse", "--verify", f"{target_ref}^{{commit}}")
    if target_head is None:
        _bootstrap_failure("configured target head is unavailable for a finalized snapshot")
    if not _loader_git_is_ancestor(repository, finalization.exact_head, target_ref):
        _bootstrap_failure("finalized Change head is not present on the configured target")
    return finalization.exact_head, False


class _DeferredRemoteStateReconciliationError(Exception):
    """One Change is safely deferred while its remote branch advances past its snapshot."""

    __slots__ = ("expected_head", "head_relation", "observed_head", "observed_local_head")

    def __init__(
        self,
        *,
        expected_head: str,
        observed_head: str,
        observed_local_head: str | None,
        head_relation: DeliveryHealthHeadRelation | None,
    ) -> None:
        self.expected_head = expected_head
        self.observed_head = observed_head
        self.observed_local_head = observed_local_head
        self.head_relation = head_relation
        super().__init__("remote Change branch is ahead of its reviewed Delivery snapshot")


class _RemoteChangeHeadMismatchError(DeliveryApplicationLoadError):
    """One remote Change head cannot be reconciled with its reviewed snapshot."""

    __slots__ = (
        "expected_head",
        "head_relation",
        "observed_head",
        "observed_local_head",
        "reason",
    )

    def __init__(  # noqa: PLR0913 - the exception preserves each exact head classification field.
        self,
        *,
        change_id: str,
        expected_head: str,
        observed_head: str,
        observed_local_head: str | None,
        head_relation: DeliveryHealthHeadRelation | None,
        reason: DeliveryHealthReason,
    ) -> None:
        self.expected_head = expected_head
        self.observed_head = observed_head
        self.observed_local_head = observed_local_head
        self.head_relation = head_relation
        self.reason = reason
        super().__init__(
            "runtime_root",
            f"remote Change branch differs from Delivery-state snapshot: {change_id}",
        )


def _can_defer_remote_state_reconciliation(
    snapshot: DeliveryStateSnapshot,
    repository: Path,
    remote_branch: str,
) -> bool:
    """Return whether one clean reviewed descendant can be quarantined at startup."""
    if snapshot.frontier.change_completion is not None:
        return False
    if not _loader_git_is_ancestor(repository, snapshot.last_reviewed_commit, remote_branch):
        return False
    return _loader_git_is_ancestor(repository, snapshot.change_head, remote_branch)


def _loader_git_is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    """Check commit ancestry without changing repository state."""
    return (
        _run_loader_git(
            repository,
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
            check=False,
        ).returncode
        == 0
    )


def _head_relation(
    repository: Path,
    expected_head: str,
    observed_head: str,
) -> DeliveryHealthHeadRelation | None:
    """Classify one observed Git head against expected Delivery authority."""
    if expected_head == observed_head:
        return DeliveryHealthHeadRelation.EQUAL
    if _loader_git_is_ancestor(repository, expected_head, observed_head):
        return DeliveryHealthHeadRelation.DESCENDANT
    if _loader_git_is_ancestor(repository, observed_head, expected_head):
        return DeliveryHealthHeadRelation.ANCESTOR
    return DeliveryHealthHeadRelation.DIVERGENT


def _restore_local_change_branch(
    snapshot: DeliveryStateSnapshot,
    repository: Path,
) -> None:
    """Create or validate the local Change branch at the remote snapshot head."""
    branch_ref = f"refs/heads/{snapshot.branch}"
    local_head = _loader_git_output(repository, "rev-parse", "--verify", f"{branch_ref}^{{commit}}")
    if local_head is None:
        result = _run_loader_git(repository, "branch", snapshot.branch, snapshot.change_head, check=False)
        if result.returncode != 0:
            _bootstrap_failure("local Change branch could not be recreated")
    elif local_head != snapshot.change_head:
        _bootstrap_failure("local Change branch differs from Delivery-state snapshot")


def _restore_runtime_snapshot(snapshot: DeliveryStateSnapshot, runtime_root: Path) -> None:
    """Atomically recreate one Change's startup and terminal evidence files."""
    relative_root = Path("changes") / snapshot.change_id
    participants = (
        TransactionParticipant(runtime_root, relative_root / "contract.json", _canonical_model(snapshot.contract)),
        TransactionParticipant(runtime_root, relative_root / "frontier.json", _canonical_model(snapshot.frontier)),
        TransactionParticipant(runtime_root, relative_root / "admission.json", _canonical_model(snapshot.admission)),
    )
    completion_store = CompletionReceiptStore(runtime_root)
    existing_completion = completion_store.read_bundle(snapshot.change_id)
    if existing_completion != snapshot.completion:
        if existing_completion is not None:
            _bootstrap_failure("local completion evidence differs from its remote snapshot")
        if snapshot.completion is not None:
            participants += (
                completion_store.participant(snapshot.completion.receipt),
                completion_store.display_participant(snapshot.completion.display),
            )
    transaction = RuntimeTransaction(
        runtime_root,
        f"delivery-state-bootstrap-{snapshot.change_id}-{snapshot.snapshot_id}",
        participants,
    )
    try:
        transaction.commit()
    except (OSError, RuntimeError, ValueError) as exc:
        transaction.abort()
        _bootstrap_failure("local Delivery state could not be restored", exc)


def _local_runtime_change_ids(runtime_root: Path) -> set[str]:
    changes_root = runtime_root / "changes"
    if not changes_root.is_dir():
        return set()
    return {path.name for path in changes_root.iterdir() if path.is_dir() and not path.is_symlink()}


def _remote_branch_head(repository: Path, remote: str, branch: str) -> str | None:
    result = _run_loader_git(
        repository,
        "ls-remote",
        "--exit-code",
        "--heads",
        remote,
        f"refs/heads/{branch}",
        check=False,
    )
    if result.returncode == _REMOTE_REF_MISSING:
        return None
    if result.returncode != 0:
        _bootstrap_failure("remote Change branch could not be observed")
    lines = result.stdout.decode(errors="replace").strip().splitlines()
    if len(lines) != 1:
        _bootstrap_failure("remote Change branch response is invalid")
    return lines[0].split("\t", 1)[0]


def _read_git_blob(repository: Path, revision: str, path: str) -> bytes:
    result = _run_loader_git(repository, "show", f"{revision}:{path}", check=False)
    if result.returncode != 0:
        _bootstrap_failure("remote Delivery package file is missing")
    return result.stdout


def _loader_git_output(repository: Path, *arguments: str) -> str | None:
    result = _run_loader_git(repository, *arguments, check=False)
    return result.stdout.decode().strip() if result.returncode == 0 else None


def _run_loader_git(
    repository: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
        (resolve_git_executable(), "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
    )


def _canonical_model(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _bootstrap_failure(detail: str, cause: Exception | None = None) -> Never:
    error = _load_error("runtime_root", detail)
    if cause is None:
        raise error
    raise error from cause


def _bounded_health_detail(detail: str, fallback: str) -> str:
    compact = " ".join(detail.split())
    return (compact or fallback)[:240]


def _compose_application(  # noqa: PLR0913, PLR0917 - composition binds independent authority owners.
    config: DeliveryStartupConfig,
    host_config: DeliveryHostConfig,
    paths: _DeliveryPaths,
    contracts: dict[str, DeliveryContract],
    publication_provider: PublicationProvider | None,
    health_diagnostics: tuple[DeliveryHealthDiagnostic, ...] = (),
    issuer_host: WindowHostIdentity | None = None,
) -> PortfolioApplication:
    package_store = DesignPackageStore(
        paths.package_root,
        paths.repository_root,
        transaction_root=paths.runtime_root,
    )
    coordinator = PortfolioCoordinator(paths.runtime_root)
    workspace_manager = ChangeWorkspaceManager(
        paths.repository_root,
        paths.worktree_root,
        coordinator,
        config.target_branch,
        config.remote,
    )
    delivery_state_publisher = DeliveryStatePublisher(
        paths.repository_root,
        remote=config.remote,
        state_branch=config.delivery_state_branch,
    )
    runtimes, runtime_diagnostics = _composed_runtimes(
        paths.runtime_root,
        contracts,
        workspace_manager,
    )
    dependencies = PortfolioApplicationDependencies(
        target_root=paths.runtime_root,
        package_store=package_store,
        authority_registry=DeliveryAuthorityRegistry(
            paths.runtime_root,
            package_store,
            integration_target=config.target_branch,
        ),
        coordinator=coordinator,
        workspace_manager=workspace_manager,
        completed_history_catalog=CompletedHistoryCatalog(
            paths.runtime_root,
        ),
        delivery_state_publisher=delivery_state_publisher,
        change_branch_publisher=ChangeBranchPublisher(
            paths.repository_root,
            coordinator,
            remote=config.remote,
            target_branch=config.target_branch,
            operation_root=paths.runtime_root / "publications/change-branches/operations",
        ),
        draft_pull_request_publisher=(
            DraftPullRequestPublisher(
                publication_provider,
                repository=config.github_repository,
                target_branch=config.target_branch,
                state_root=paths.runtime_root / "publications/pull-requests",
            )
            if publication_provider is not None
            else None
        ),
        health_diagnostics=(*health_diagnostics, *runtime_diagnostics),
        issuer_window=issuer_host,
    )
    application_config = PortfolioApplicationConfig(
        package_root=paths.package_root,
        execution_capacity=host_config.execution_capacity,
        claim_timeout_seconds=host_config.claim_timeout_seconds,
        role_policies=_role_policies(),
    )
    return PortfolioApplication(runtimes, dependencies, application_config)


def _composed_runtimes(
    runtime_root: Path,
    contracts: dict[str, DeliveryContract],
    workspace_manager: ChangeWorkspaceManager,
) -> tuple[dict[str, DeliveryRuntime], tuple[DeliveryHealthDiagnostic, ...]]:
    runtimes = {}
    diagnostics: list[DeliveryHealthDiagnostic] = []
    for change_id, contract in contracts.items():
        try:
            runtimes[change_id] = DeliveryRuntime(
                runtime_root,
                contract,
                workspace_manager=workspace_manager,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            diagnostics.append(
                DeliveryHealthDiagnostic(
                    source="local-runtime",
                    code="runtime-unavailable",
                    detail=_bounded_health_detail(
                        str(exc),
                        "Delivery runtime is unavailable and was quarantined.",
                    ),
                    change_id=change_id,
                    path=f".owlbear/delivery/runtime/changes/{change_id}",
                    reason=DeliveryHealthReason.RUNTIME_UNAVAILABLE,
                    resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                )
            )
    return runtimes, tuple(diagnostics)


def load_delivery_application(
    config: DeliveryStartupConfig,
    *,
    workspace_root: Path,
    publication_provider: PublicationProvider | None = None,
    issuer_host: WindowHostIdentity | None = None,
) -> PortfolioApplication:
    """Validate external identities before constructing the Delivery state owners.

    The shared controller lock and the format gate run first, so fenced or unsupported state is
    refused before any Git, remote, typed read or write. The returned application holds the lock
    until ``close_delivery_application`` or garbage collection.
    Only a process whose agents receive its claims passes ``issuer_host``; claims issued without it are
    never settled automatically and need user-confirmed release.
    """
    paths = _derive_paths(workspace_root)
    controller_lock = _acquire_controller_fence(paths)
    try:
        _require_state_capability(paths)
        application = _load_gated_application(config, paths, publication_provider, issuer_host)
    except BaseException:
        controller_lock.release()
        raise
    _CONTROLLER_LOCKS[application] = controller_lock
    weakref.finalize(application, controller_lock.release)
    return application


def close_delivery_application(application: PortfolioApplication) -> None:
    """Release the controller lock of one loaded application; stop its checkpoint supervisor first."""
    controller_lock = _CONTROLLER_LOCKS.pop(application, None)
    if controller_lock is not None:
        controller_lock.release()


def _acquire_controller_fence(paths: _DeliveryPaths) -> ControllerLock:
    try:
        return acquire_controller_lock(paths.runtime_root)
    except ControllerFencedError as exc:
        error = DeliveryApplicationLoadError(
            "controller_lock",
            f"{CONTROLLER_FENCED}: Delivery state is fenced by a migration or upgrade; no state was read",
            code=CONTROLLER_FENCED,
        )
        raise error from exc
    except (OSError, ValueError) as exc:
        error = _load_error("runtime_root", "workspace controller lock is unavailable")
        raise error from exc


def _require_state_capability(paths: _DeliveryPaths) -> None:
    try:
        require_capability(scan_capability(paths.repository_root))
    except StateCapabilityError as exc:
        raise DeliveryStateVersionError(exc.code, exc.detail, locator=exc.locator) from exc


def _load_gated_application(
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
    publication_provider: PublicationProvider | None,
    issuer_host: WindowHostIdentity | None,
) -> PortfolioApplication:
    _validate_git_config(config, paths)
    host_config = _load_host_config(paths)
    remote_diagnostics: tuple[DeliveryHealthDiagnostic, ...] = ()
    if "delivery_state_branch" in config.model_fields_set:
        remote_diagnostics = _bootstrap_remote_state(config, paths)
    contracts, local_diagnostics = _load_contracts(paths.runtime_root)
    health_diagnostics = (*remote_diagnostics, *local_diagnostics)
    if health_diagnostics:
        change_count = len(
            {diagnostic.change_id for diagnostic in health_diagnostics if diagnostic.change_id is not None}
        )
        _logger.warning(
            "Delivery started with %d health attention item(s) across %d Change(s); call delivery_health for details.",
            len(health_diagnostics),
            change_count,
        )
    return _compose_application(
        config,
        host_config,
        paths,
        contracts,
        publication_provider,
        health_diagnostics,
        issuer_host,
    )
