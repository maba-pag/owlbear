"""Transport-free Delivery application configuration and composition."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.change_publication import ChangeBranchPublisher
from owlbear_delivery.change_workspace import (
    CapacityConfigurationConflictError,
    CapacityLedgerConflictError,
    ChangeWorkspaceManager,
    CoordinationConflictError,
    PortfolioCoordinator,
)
from owlbear_delivery.completed_history import CompletedHistoryCatalog
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryDiscoveryErrorCode,
    DeliveryDiscoveryRootError,
    DeliveryDiscoveryStartupError,
    discover_persisted_changes,
    require_startup_contracts,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryRuntime,
    DeliveryRuntimeMigrationError,
    DeliveryWorkerRole,
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
from owlbear_delivery.target_admission import DeliveryAuthorityRegistry

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


class DeliveryHostConfig(_LoaderModel):
    """Host-local limits for concurrent Delivery work."""

    schema_version: Literal[1]
    writer_capacity: int = Field(default=1, gt=0)
    execution_capacity: int = Field(default=1, gt=0)


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
            }[field]
            error = _load_error(field, detail)
            raise error
    remote_url = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
        (git_executable, "-C", str(paths.repository_root), "remote", "get-url", config.remote),
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


def _load_host_config(paths: _DeliveryPaths) -> DeliveryHostConfig:
    path = paths.runtime_root / "host.json"
    try:
        if not path.exists():
            if path.is_symlink():
                error = _load_error("host_config", "host-local Delivery capacity configuration is unsafe")
                raise error
            return DeliveryHostConfig(schema_version=1)
        if path.is_symlink() or not path.is_file():
            error = _load_error("host_config", "host-local Delivery capacity configuration must be a regular file")
            raise error
        return DeliveryHostConfig.model_validate_json(path.read_bytes())
    except DeliveryApplicationLoadError:
        raise
    except ValidationError as exc:
        location = exc.errors(include_url=False, include_context=False)[0].get("loc")
        field = location[0] if isinstance(location, tuple | list) and location else "host_config"
        error = _load_error(str(field), f"host-local Delivery capacity configuration is invalid: {path}")
        raise error from exc
    except (OSError, ValueError) as exc:
        error = _load_error("host_config", f"host-local Delivery capacity configuration cannot be read: {path}")
        raise error from exc


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


def _compose_application(
    config: DeliveryStartupConfig,
    host_config: DeliveryHostConfig,
    paths: _DeliveryPaths,
    contracts: dict[str, DeliveryContract],
    publication_provider: PublicationProvider | None,
) -> PortfolioApplication:
    package_store = DesignPackageStore(paths.package_root, paths.repository_root)
    try:
        coordinator = PortfolioCoordinator(paths.runtime_root, capacity=host_config.writer_capacity)
    except CapacityConfigurationConflictError as exc:
        error = _load_error(
            "writer_capacity",
            f"host-local Delivery capacity configuration in host.json cannot be lower than active writers: {exc}",
        )
        raise error from exc
    except CapacityLedgerConflictError as exc:
        error = _load_error(
            "runtime_root",
            f"Delivery capacity ledger changed concurrently; retry startup: {exc}",
        )
        raise error from exc
    workspace_manager = ChangeWorkspaceManager(
        paths.repository_root,
        paths.worktree_root,
        coordinator,
        config.target_branch,
        config.remote,
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
    contracts = _load_contracts(paths.runtime_root)
    return _compose_application(config, host_config, paths, contracts, publication_provider)
