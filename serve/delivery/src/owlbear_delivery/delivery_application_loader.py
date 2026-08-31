"""Transport-free Delivery application configuration and composition."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.acceptance import CompletionReceiptStore
from owlbear_delivery.change_publication import ChangeBranchPublisher
from owlbear_delivery.change_workspace import (
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
    DeliveryDiscoveryStartupError,
    discover_persisted_changes,
    require_startup_contracts,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryFrontier,
    DeliveryRuntime,
    DeliveryRuntimeMigrationError,
    DeliveryWorkerRole,
)
from owlbear_delivery.delivery_state import (
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    DeliveryStateSnapshot,
    _legacy_frontier_bytes,
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
from owlbear_delivery.runtime_transaction import RuntimeTransaction, TransactionParticipant

if TYPE_CHECKING:
    from owlbear_delivery.publication_provider import PublicationProvider
    from owlbear_delivery.target_contract import DeliveryContract


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


class DeliveryApplicationLoadError(RuntimeError):
    """Field-aware failure raised before Delivery state owners are composed."""

    __slots__ = ("detail", "field")

    def __init__(self, field: str, detail: str) -> None:
        self.field = field
        self.detail = detail
        super().__init__(detail)


_REMOTE_REF_MISSING = 2


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
    # Current startup refuses unfinished transition journals instead of treating them as authority.
    migration_journal = delivery_root / "migration.json"
    if migration_journal.exists():
        field = "runtime_root"
        detail = "interrupted Delivery migration must be recovered before startup"
        raise _load_error(field, detail)
    retirement_journal = delivery_root / "integration-retirement.json"
    if retirement_journal.exists():
        field = "runtime_root"
        detail = "interrupted Integration retirement must be recovered before startup"
        raise _load_error(field, detail)
    # Current startup also rejects pre-current roots so state cannot be silently orphaned.
    for field, legacy_root in (
        ("runtime_root", repository_root / ".owlbear/target"),
        ("worktree_root", repository_root / ".owlbear/worktrees"),
    ):
        try:
            has_legacy_state = legacy_root.exists() and any(legacy_root.iterdir())
        except OSError as exc:
            error = _load_error(field, "legacy Delivery path cannot be inspected")
            raise error from exc
        if has_legacy_state:
            raise _load_error(field, "legacy Delivery state must be migrated before startup")
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
    legacy_root = primary_worktree / ".owlbear/worktrees"
    for registered in registered_worktrees:
        if registered == legacy_root or legacy_root in registered.parents:
            field_name = "worktree_root"
            detail = "legacy Git worktree registrations must be migrated before startup"
            raise _load_error(field_name, detail)


def _load_contracts(runtime_root: Path) -> dict[str, DeliveryContract]:
    try:
        observations = discover_persisted_changes(runtime_root)
    except DeliveryDiscoveryRootError as exc:
        error = _load_error("runtime_root", exc.detail)
        raise error from exc
    try:
        return require_startup_contracts(observations)
    except DeliveryDiscoveryStartupError as exc:
        discovery_error = exc.observation.error
        code = discovery_error.code if discovery_error is not None else None
        if code is DeliveryDiscoveryErrorCode.FRONTIER_MIGRATION_REQUIRED:
            detail = discovery_error.detail
            error = _load_error("runtime_root", detail)
            raise error from DeliveryRuntimeMigrationError(detail)
        if code is DeliveryDiscoveryErrorCode.CONTRACT_IDENTITY_INVALID:
            detail = "Delivery state identity is invalid"
        elif code in {
            DeliveryDiscoveryErrorCode.FRONTIER_UNAVAILABLE,
            DeliveryDiscoveryErrorCode.FRONTIER_INVALID,
            DeliveryDiscoveryErrorCode.FRONTIER_BINDING_INVALID,
            DeliveryDiscoveryErrorCode.ADMISSION_FRONTIER_MISMATCH,
        }:
            detail = "Delivery runtime state is invalid"
        else:
            detail = "Delivery state is invalid"
        error = _load_error("runtime_root", detail)
        raise error from exc


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
) -> None:
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
        snapshots = state_publisher.read_snapshots()
    except DeliveryStatePublicationError as exc:
        if _local_runtime_change_ids(paths.runtime_root):
            return
        error = _load_error("runtime_root", "remote Delivery-state snapshots are unavailable")
        raise error from exc
    if not snapshots:
        return
    coordinator = PortfolioCoordinator(paths.runtime_root)
    workspace_manager = ChangeWorkspaceManager(
        paths.repository_root,
        paths.worktree_root,
        coordinator,
        config.target_branch,
        config.remote,
    )
    local_change_ids = _local_runtime_change_ids(paths.runtime_root)
    for snapshot in snapshots:
        try:
            if snapshot.change_id in local_change_ids:
                _validate_local_snapshot(snapshot, config, paths, package_store, coordinator)
            else:
                _restore_remote_snapshot(snapshot, config, paths, package_store, coordinator, workspace_manager)
        except _DeferredRemoteStateReconciliationError:
            continue
        except DeliveryApplicationLoadError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            _bootstrap_failure("remote Delivery state could not be reconciled", exc)


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
    if not snapshot.frontier.change_completion and not worktree_path.exists():
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
    coordinator: PortfolioCoordinator,
) -> None:
    """Reject local Delivery state that does not exactly match its remote checkpoint."""
    _fetch_snapshot_change_head(snapshot, config, paths.repository_root)
    try:
        package = package_store.read_verified(snapshot.change_id)
    except (OSError, RuntimeError, ValueError) as exc:
        _bootstrap_failure("local Delivery package cannot be reconciled with its remote snapshot", exc)
    if package.package_id != snapshot.package_id:
        _bootstrap_failure("local Delivery package differs from its remote snapshot")
    try:
        coordination = coordinator.show(snapshot.change_id)
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
    for name, content in expected.items():
        _validate_local_snapshot_artifact(relative_root / name, name, content, snapshot)
    frontier = DeliveryFrontier.model_validate_json((relative_root / "frontier.json").read_bytes())
    if frontier != snapshot.frontier:
        _bootstrap_failure("local Delivery frontier differs from its remote snapshot")
    try:
        completion = CompletionReceiptStore(paths.runtime_root).read_bundle(snapshot.change_id)
    except RuntimeError as exc:
        _bootstrap_failure("local completion evidence cannot be reconciled with its remote snapshot", exc)
    if completion != snapshot.completion:
        _bootstrap_failure("local completion evidence differs from its remote snapshot")


def _validate_local_snapshot_artifact(
    path: Path,
    name: str,
    expected: bytes,
    snapshot: DeliveryStateSnapshot,
) -> None:
    """Require one local runtime artifact to match current or known legacy bytes."""
    if path.is_symlink() or not path.is_file():
        _bootstrap_failure(f"local Delivery runtime artifact differs from its remote snapshot: {name}")
    actual = path.read_bytes()
    if actual == expected:
        return
    if name == "frontier.json" and actual == _legacy_frontier_bytes(snapshot.frontier):
        return
    _bootstrap_failure(f"local Delivery runtime artifact differs from its remote snapshot: {name}")


def _fetch_snapshot_change_head(
    snapshot: DeliveryStateSnapshot,
    config: DeliveryStartupConfig,
    repository: Path,
) -> tuple[str, bool]:
    """Fetch the remote Change branch or use the configured target for completion."""
    remote_branch = _remote_branch_head(repository, config.remote, snapshot.branch)
    if remote_branch is not None:
        if remote_branch != snapshot.change_head:
            if _can_defer_remote_state_reconciliation(snapshot, repository, remote_branch):
                raise _DeferredRemoteStateReconciliationError
            _bootstrap_failure(f"remote Change branch differs from Delivery-state snapshot: {snapshot.change_id}")
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


class _DeferredRemoteStateReconciliationError(Exception):
    """One Change is safely deferred while its remote branch advances past its snapshot."""


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


def _compose_application(
    config: DeliveryStartupConfig,
    host_config: DeliveryHostConfig,
    paths: _DeliveryPaths,
    contracts: dict[str, DeliveryContract],
    publication_provider: PublicationProvider | None,
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
    runtimes = _composed_runtimes(paths.runtime_root, contracts, workspace_manager)
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
            paths.repository_root,
            config.target_branch,
            f"refs/remotes/{config.remote}/{config.target_branch}",
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
) -> dict[str, DeliveryRuntime]:
    runtimes = {}
    for change_id, contract in contracts.items():
        try:
            reviewed_head = workspace_manager.show(change_id).last_reviewed_commit
        except CoordinationConflictError:
            continue
        runtimes[change_id] = DeliveryRuntime(
            runtime_root,
            contract,
            workspace_manager=workspace_manager,
            migration_reviewed_head=reviewed_head,
        )
    return runtimes


def load_delivery_application(
    config: DeliveryStartupConfig,
    *,
    workspace_root: Path,
    publication_provider: PublicationProvider | None = None,
) -> PortfolioApplication:
    """Validate external identities before constructing the Delivery state owners."""
    paths = _derive_paths(workspace_root)
    _validate_git_config(config, paths)
    host_config = _load_host_config(paths)
    if "delivery_state_branch" in config.model_fields_set:
        _bootstrap_remote_state(config, paths)
    contracts = _load_contracts(paths.runtime_root)
    return _compose_application(config, host_config, paths, contracts, publication_provider)
