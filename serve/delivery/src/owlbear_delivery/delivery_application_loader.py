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
    ChangeWorkspaceManager,
    CoordinationConflictError,
    PortfolioCoordinator,
)
from owlbear_delivery.completed_history import CompletedHistoryCatalog
from owlbear_delivery.delivery_runtime import (
    DeliveryFrontier,
    DeliveryRuntime,
    DeliveryWorkerRole,
    parse_delivery_frontier,
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
from owlbear_delivery.target_contract import DeliveryContract

if TYPE_CHECKING:
    from owlbear_delivery.publication_provider import PublicationProvider


class _LoaderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStartupConfig(_LoaderModel):
    """Workspace-local Delivery policy loaded before owner construction."""

    schema_version: Literal[2]
    remote: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    github_repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")


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


def _read_contract(change_root: Path) -> DeliveryContract:
    try:
        contract = DeliveryContract.model_validate_json((change_root / "contract.json").read_bytes())
    except (OSError, ValidationError) as exc:
        error = _load_error("runtime_root", "Delivery state is invalid")
        raise error from exc
    if contract.change_id != change_root.name:
        error = _load_error("runtime_root", "Delivery state identity is invalid")
        raise error
    return contract


def _load_contracts(runtime_root: Path) -> dict[str, DeliveryContract]:
    changes_root = runtime_root / "changes"
    if not changes_root.exists():
        return {}
    if changes_root.is_symlink() or not changes_root.is_dir():
        error = _load_error("runtime_root", "Delivery state root is invalid")
        raise error
    try:
        change_roots = tuple(sorted(changes_root.iterdir()))
    except OSError as exc:
        error = _load_error("runtime_root", "Delivery state is invalid")
        raise error from exc
    return {
        contract.change_id: contract
        for change_root in change_roots
        if change_root.is_dir() and not change_root.is_symlink()
        for contract in (_read_contract(change_root),)
    }


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
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
            worker_agent="builder",
            reviewer_agent="build-reviewer",
        ),
    )


def _validate_runtime_state(runtime_root: Path, contracts: dict[str, DeliveryContract]) -> None:
    try:
        for contract in contracts.values():
            frontier_path = runtime_root / "changes" / contract.change_id / "frontier.json"
            frontier = parse_delivery_frontier(frontier_path.read_bytes())[0]
            _require_runtime_bindings(contract, frontier)
    except (OSError, ValidationError, TypeError, ValueError) as exc:
        error = _load_error("runtime_root", "Delivery runtime state is invalid")
        raise error from exc


def _require_runtime_bindings(contract: DeliveryContract, frontier: DeliveryFrontier) -> None:
    expected = tuple((scope.outcome_id, scope.scope_id) for scope in contract.plan_scopes)
    actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
    if actual != expected:
        raise ValueError


def _compose_application(
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
    contracts: dict[str, DeliveryContract],
    publication_provider: PublicationProvider | None,
) -> PortfolioApplication:
    package_store = DesignPackageStore(paths.package_root, paths.repository_root)
    coordinator = PortfolioCoordinator(paths.runtime_root, capacity=1)
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
        execution_capacity=1,
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
    contracts = _load_contracts(paths.runtime_root)
    _validate_runtime_state(paths.runtime_root, contracts)
    return _compose_application(config, paths, contracts, publication_provider)
