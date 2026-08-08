"""Transport-free Delivery application configuration and composition."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator
from owlbear_delivery.completed_history import CompletedHistoryCatalog
from owlbear_delivery.delivery_runtime import (
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryWorkerRole,
)
from owlbear_delivery.design_package import DesignPackageStore
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
    from pathlib import Path


class _LoaderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStartupConfig(_LoaderModel):
    """Workspace-local Delivery policy loaded before owner construction."""

    schema_version: Literal[1]
    integration_target: str = Field(min_length=1)


@dataclass(frozen=True)
class _DeliveryPaths:
    package_root: Path
    target_root: Path
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
    paths = _DeliveryPaths(
        package_root=repository_root / ".owlbear/delivery/packages",
        target_root=repository_root / ".owlbear/target",
        repository_root=repository_root,
        worktree_root=repository_root / ".owlbear/worktrees",
    )
    for field, path in (
        ("package_root", paths.package_root),
        ("target_root", paths.target_root),
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
        (("check-ref-format", f"refs/heads/{config.integration_target}"), "integration_target"),
        (("rev-parse", "--verify", f"refs/heads/{config.integration_target}^{{commit}}"), "integration_target"),
    )
    for arguments, field in checks:
        completed = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
            (git_executable, "-C", str(paths.repository_root), *arguments),
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            error = _load_error(field, "configured repository or integration target is invalid")
            raise error


def _read_contract(change_root: Path) -> DeliveryContract:
    try:
        contract = DeliveryContract.model_validate_json((change_root / "contract.json").read_bytes())
    except (OSError, ValidationError) as exc:
        error = _load_error("target_root", "Delivery state is invalid")
        raise error from exc
    if contract.change_id != change_root.name:
        error = _load_error("target_root", "Delivery state identity is invalid")
        raise error
    return contract


def _load_contracts(target_root: Path) -> dict[str, DeliveryContract]:
    changes_root = target_root / "delivery" / "changes"
    if not changes_root.exists():
        return {}
    if changes_root.is_symlink() or not changes_root.is_dir():
        error = _load_error("target_root", "Delivery state root is invalid")
        raise error
    try:
        change_roots = tuple(sorted(changes_root.iterdir()))
    except OSError as exc:
        error = _load_error("target_root", "Delivery state is invalid")
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
            worker_role=DeliveryWorkerRole.ASSEMBLY_REVIEWER,
            worker_agent="build-reviewer",
            reviewer_agent="build-reviewer",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
            worker_agent="builder",
            reviewer_agent="build-reviewer",
        ),
    )


def _validate_runtime_state(target_root: Path, contracts: dict[str, DeliveryContract]) -> None:
    try:
        for contract in contracts.values():
            DeliveryRuntime(target_root, contract)
    except (OSError, ValidationError, DeliveryRuntimeConflictError, DeliveryRuntimeReferenceError) as exc:
        error = _load_error("target_root", "Delivery runtime state is invalid")
        raise error from exc


def _compose_application(
    config: DeliveryStartupConfig,
    paths: _DeliveryPaths,
    contracts: dict[str, DeliveryContract],
) -> PortfolioApplication:
    package_store = DesignPackageStore(paths.package_root, paths.repository_root)
    coordinator = PortfolioCoordinator(paths.target_root, capacity=1)
    workspace_manager = ChangeWorkspaceManager(
        paths.repository_root,
        paths.worktree_root,
        coordinator,
        config.integration_target,
    )
    runtimes = {
        change_id: DeliveryRuntime(paths.target_root, contract, workspace_manager=workspace_manager)
        for change_id, contract in contracts.items()
    }
    dependencies = PortfolioApplicationDependencies(
        target_root=paths.target_root,
        package_store=package_store,
        authority_registry=DeliveryAuthorityRegistry(
            paths.target_root,
            package_store,
            integration_target=config.integration_target,
        ),
        coordinator=coordinator,
        workspace_manager=workspace_manager,
        completed_history_catalog=CompletedHistoryCatalog(paths.repository_root, config.integration_target),
    )
    application_config = PortfolioApplicationConfig(
        package_root=paths.package_root,
        execution_capacity=1,
        role_policies=_role_policies(),
    )
    return PortfolioApplication(runtimes, dependencies, application_config)


def load_delivery_application(
    config: DeliveryStartupConfig,
    *,
    workspace_root: Path,
    authorized_target_root: Path,
) -> PortfolioApplication:
    """Validate external identities before constructing the Delivery state owners."""
    paths = _derive_paths(workspace_root)
    if paths.target_root.resolve() != authorized_target_root.resolve():
        error = _load_error("target_root", "configured target root is not authorized")
        raise error
    _validate_git_config(config, paths)
    contracts = _load_contracts(paths.target_root)
    _validate_runtime_state(paths.target_root, contracts)
    return _compose_application(config, paths, contracts)
