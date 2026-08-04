"""Transport-free Delivery application configuration and composition."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from owlbear_kanban.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator
from owlbear_kanban.completed_history import CompletedHistoryCatalog
from owlbear_kanban.delivery_runtime import (
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryWorkerRole,
)
from owlbear_kanban.design_package import DesignPackageStore
from owlbear_kanban.portfolio_application import (
    DeliveryRolePolicy,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
)
from owlbear_kanban.target_admission import DeliveryAuthorityRegistry
from owlbear_kanban.target_contract import DeliveryContract


class _LoaderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryRoleIdentityConfig(_LoaderModel):
    """Explicit worker and reviewer identities for one Delivery role."""

    worker_agent: str = Field(min_length=1)
    worker_model: str = Field(min_length=1)
    reviewer_agent: str = Field(min_length=1)
    reviewer_model: str = Field(min_length=1)


class DeliveryRolePoliciesConfig(_LoaderModel):
    """Complete role policy required before owner construction."""

    planner: DeliveryRoleIdentityConfig
    builder: DeliveryRoleIdentityConfig
    assembly_reviewer: DeliveryRoleIdentityConfig = Field(alias="assembly-reviewer")


class DeliveryStartupConfig(_LoaderModel):
    """Validated roots, capacities, target, and identities for Delivery startup."""

    package_root: Path
    target_root: Path
    repository_root: Path
    worktree_root: Path
    execution_capacity: int = Field(gt=0)
    writer_capacity: int = Field(gt=0)
    integration_target: str = Field(min_length=1)
    role_policies: DeliveryRolePoliciesConfig

    @field_validator("package_root", "target_root", "repository_root", "worktree_root")
    @classmethod
    def _validate_directory_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            message = "path must be absolute"
            raise ValueError(message)
        if value.exists() and (value.is_symlink() or not value.is_dir()):
            message = "path must name a directory"
            raise ValueError(message)
        return value

    @field_validator("repository_root")
    @classmethod
    def _validate_repository_root(cls, value: Path) -> Path:
        if not value.is_dir():
            message = "repository root must exist"
            raise ValueError(message)
        return value


class DeliveryApplicationLoadError(RuntimeError):
    """Field-aware failure raised before Delivery state owners are composed."""

    __slots__ = ("detail", "field")

    def __init__(self, field: str, detail: str) -> None:
        self.field = field
        self.detail = detail
        super().__init__(detail)


def _load_error(field: str, detail: str) -> DeliveryApplicationLoadError:
    return DeliveryApplicationLoadError(field, detail)


def _validate_git_config(config: DeliveryStartupConfig) -> None:
    git_executable = shutil.which("git")
    if git_executable is None:
        error = _load_error("repository_root", "Git executable is unavailable")
        raise error
    checks = (
        (("rev-parse", "--git-dir"), "repository_root"),
        (("check-ref-format", f"refs/heads/{config.integration_target}"), "integration_target"),
        (("rev-parse", "--verify", f"refs/heads/{config.integration_target}^{{commit}}"), "integration_target"),
    )
    for arguments, field in checks:
        completed = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
            (git_executable, "-C", str(config.repository_root), *arguments),
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


def _role_policy(role: DeliveryWorkerRole, identity: DeliveryRoleIdentityConfig) -> DeliveryRolePolicy:
    return DeliveryRolePolicy(worker_role=role, **identity.model_dump())


def _role_policies(config: DeliveryStartupConfig) -> tuple[DeliveryRolePolicy, ...]:
    policies = config.role_policies
    return (
        _role_policy(DeliveryWorkerRole.PLANNER, policies.planner),
        _role_policy(DeliveryWorkerRole.BUILDER, policies.builder),
        _role_policy(DeliveryWorkerRole.ASSEMBLY_REVIEWER, policies.assembly_reviewer),
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
    contracts: dict[str, DeliveryContract],
) -> PortfolioApplication:
    package_store = DesignPackageStore(config.package_root, config.repository_root)
    coordinator = PortfolioCoordinator(config.target_root, capacity=config.writer_capacity)
    workspace_manager = ChangeWorkspaceManager(
        config.repository_root,
        config.worktree_root,
        coordinator,
        config.integration_target,
    )
    runtimes = {
        change_id: DeliveryRuntime(config.target_root, contract, workspace_manager=workspace_manager)
        for change_id, contract in contracts.items()
    }
    dependencies = PortfolioApplicationDependencies(
        package_store=package_store,
        authority_registry=DeliveryAuthorityRegistry(
            config.target_root,
            package_store,
            integration_target=config.integration_target,
        ),
        coordinator=coordinator,
        workspace_manager=workspace_manager,
        completed_history_catalog=CompletedHistoryCatalog(config.repository_root, config.integration_target),
    )
    application_config = PortfolioApplicationConfig(
        package_root=config.package_root,
        execution_capacity=config.execution_capacity,
        role_policies=_role_policies(config),
    )
    return PortfolioApplication(runtimes, dependencies, application_config)


def load_delivery_application(
    config: DeliveryStartupConfig,
    *,
    authorized_target_root: Path,
) -> PortfolioApplication:
    """Validate external identities before constructing the Delivery state owners."""
    if config.target_root.resolve() != authorized_target_root.resolve():
        error = _load_error("target_root", "configured target root is not authorized")
        raise error
    _validate_git_config(config)
    contracts = _load_contracts(config.target_root)
    _validate_runtime_state(config.target_root, contracts)
    return _compose_application(config, contracts)
