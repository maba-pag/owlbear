"""Live OwlBear MCP server for target delivery."""

from __future__ import annotations

import os
import shutil
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from owlbear_kanban import (
    ChangeWorkspaceManager,
    Commitment,
    CommitmentClass,
    CompletedHistoryCatalog,
    DeliveryAuthorityRegistry,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryWorkerRole,
    DesignPackageStore,
    Outcome,
    PlanScopeKind,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioCoordinator,
    TargetAuthority,
    TaskPlanScope,
    TaskProgress,
    WorkItemEvidence,
    WorkItemProjector,
)
from owlbear_kanban.target_cutover import (
    TargetCutoverError,
    TargetCutoverRequest,
    authorize_target_mutation,
)
from owlbear_mcp_kanban.target_models import (
    DeliveryRoleIdentityConfig,
    DeliveryStartupConfig,
    DeliveryStartupDiagnostic,
)
from owlbear_mcp_kanban.target_server import (
    DeliveryAppContext,
    TargetMCPAdapter,
    register_target_tools,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_DEFAULT_WORKSPACE_ROOT = Path.cwd()
_DEFAULT_CUTOVER_REQUEST = Path(".owlbear/target-cutover-request.json")
_UNCONFIGURED = "ERR_DELIVERY_STARTUP_UNCONFIGURED"
_INVALID = "ERR_DELIVERY_STARTUP_INVALID"
_live_context: DeliveryAppContext | None = None


def _resolve_workspace_root() -> Path:
    configured = os.environ.get("OWLBEAR_WORKSPACE_ROOT", "").strip()
    return (Path(configured) if configured else _DEFAULT_WORKSPACE_ROOT).resolve()


def _resolve_request_path(workspace_root: Path) -> Path:
    configured = os.environ.get("OWLBEAR_TARGET_CUTOVER_REQUEST", "").strip()
    selected = Path(configured) if configured else _DEFAULT_CUTOVER_REQUEST
    return selected.resolve() if selected.is_absolute() else (workspace_root / selected).resolve()


def _delivery_config_path() -> Path:
    configured = os.environ.get("OWLBEAR_DELIVERY_CONFIG", "").strip()
    if not configured:
        raise DeliveryStartupDiagnostic(
            _UNCONFIGURED,
            "Delivery startup configuration path is required",
            "OWLBEAR_DELIVERY_CONFIG",
        )
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise DeliveryStartupDiagnostic(
            _UNCONFIGURED,
            "Delivery startup configuration file is required",
            "OWLBEAR_DELIVERY_CONFIG",
        )
    return path


def load_delivery_config(path: Path) -> DeliveryStartupConfig:
    """Parse one strict startup document without constructing state owners."""
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise DeliveryStartupDiagnostic(
            _INVALID,
            "Delivery startup configuration cannot be read",
            "OWLBEAR_DELIVERY_CONFIG",
        ) from exc
    try:
        return DeliveryStartupConfig.model_validate_json(content)
    except ValidationError as exc:
        error = exc.errors(include_url=False, include_context=False, include_input=False)[0]
        field = _validation_field(error)
        code = _UNCONFIGURED if _is_missing_required(error, field) else _INVALID
        detail = (
            "required Delivery startup configuration is absent"
            if code == _UNCONFIGURED
            else "Delivery startup configuration field is invalid"
        )
        raise DeliveryStartupDiagnostic(code, detail, field) from exc


def _validation_field(error: dict[str, object]) -> str:
    location = error.get("loc")
    if not isinstance(location, tuple | list):
        return "OWLBEAR_DELIVERY_CONFIG"
    parts = tuple(str(part) for part in location)
    return ".".join(parts) if parts else "OWLBEAR_DELIVERY_CONFIG"


def _is_missing_required(error: dict[str, object], field: str) -> bool:
    if error.get("type") != "missing":
        return False
    top_level = {"execution_capacity", "writer_capacity", "integration_target", "role_policies"}
    return field.split(".", maxsplit=1)[0] in top_level


def _authorize_configured_target(config: DeliveryStartupConfig) -> None:
    workspace_root = _resolve_workspace_root()
    request_path = _resolve_request_path(workspace_root)
    try:
        request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
        authorize_target_mutation(workspace_root, request)
    except (OSError, ValidationError, TargetCutoverError) as exc:
        raise DeliveryStartupDiagnostic(
            _INVALID,
            "target cutover authority is invalid",
            "OWLBEAR_TARGET_CUTOVER_REQUEST",
        ) from exc
    expected_target = (workspace_root / request.target_path).resolve()
    if config.target_root.resolve() != expected_target:
        raise DeliveryStartupDiagnostic(
            _INVALID,
            "configured target root differs from cutover authority",
            "target_root",
        )


def _validate_git_config(config: DeliveryStartupConfig) -> None:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise DeliveryStartupDiagnostic(_INVALID, "Git executable is unavailable", "repository_root")
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
            raise DeliveryStartupDiagnostic(
                _INVALID,
                "configured repository or integration target is invalid",
                field,
            )


def _load_contracts(target_root: Path) -> dict[str, DeliveryContract]:
    changes_root = target_root / "delivery" / "changes"
    if not changes_root.exists():
        return {}
    if changes_root.is_symlink() or not changes_root.is_dir():
        raise DeliveryStartupDiagnostic(_INVALID, "Delivery state root is invalid", "target_root")
    contracts: dict[str, DeliveryContract] = {}
    try:
        for change_root in sorted(changes_root.iterdir()):
            if not change_root.is_dir() or change_root.is_symlink():
                continue
            contract = DeliveryContract.model_validate_json((change_root / "contract.json").read_bytes())
            if contract.change_id != change_root.name:
                raise DeliveryStartupDiagnostic(
                    _INVALID,
                    "Delivery state identity is invalid",
                    "target_root",
                )
            contracts[contract.change_id] = contract
    except (OSError, ValidationError) as exc:
        raise DeliveryStartupDiagnostic(_INVALID, "Delivery state is invalid", "target_root") from exc
    return contracts


def _role_policy(
    role: DeliveryWorkerRole,
    identity: DeliveryRoleIdentityConfig,
) -> DeliveryRolePolicy:
    return DeliveryRolePolicy(worker_role=role, **identity.model_dump())


def _role_policies(config: DeliveryStartupConfig) -> tuple[DeliveryRolePolicy, ...]:
    policies = config.role_policies
    return (
        _role_policy(DeliveryWorkerRole.PLANNER, policies.planner),
        _role_policy(DeliveryWorkerRole.BUILDER, policies.builder),
        _role_policy(DeliveryWorkerRole.ASSEMBLY_REVIEWER, policies.assembly_reviewer),
    )


def _project_authority(contract: DeliveryContract, frontier: DeliveryFrontier) -> TargetAuthority:
    bindings = {binding.outcome_id: binding for binding in frontier.bindings}
    return TargetAuthority(
        change_id=contract.change_id,
        title=contract.title,
        commitments=tuple(
            Commitment(
                commitment_id=item.commitment_id,
                commitment_class=CommitmentClass(item.commitment_class.value),
                provenance=item.provenance,
                statement=item.statement,
            )
            for item in contract.commitments
        ),
        outcomes=tuple(Outcome.model_validate(item.model_dump()) for item in contract.outcomes),
        task_plan_scopes=tuple(
            TaskPlanScope(
                scope_id=scope.scope_id,
                kind=PlanScopeKind.OUTCOME,
                target_id=scope.outcome_id,
                composition_claim="Assemble reviewed Delivery outputs"
                if bindings[scope.outcome_id].assembly_required
                else None,
            )
            for scope in contract.plan_scopes
        ),
    )


def _project_evidence(contract: DeliveryContract, frontier: DeliveryFrontier) -> WorkItemEvidence:
    scopes = {scope.outcome_id: scope.scope_id for scope in contract.plan_scopes}
    progressed = tuple(
        binding for binding in frontier.bindings if binding.stage not in {DeliveryStage.DESIGN, DeliveryStage.PLANNING}
    )
    return WorkItemEvidence(
        planned_scope_ids=tuple(scopes[item.outcome_id] for item in progressed),
        task_progress=tuple(
            TaskProgress(
                scope_id=scopes[item.outcome_id],
                task_count=len(item.tasks),
                reviewed_task_count=len(item.results),
            )
            for item in progressed
        ),
        completed_assembly_scope_ids=tuple(
            scopes[item.outcome_id]
            for item in frontier.bindings
            if item.assembly_required and item.stage == DeliveryStage.COMPLETED
        ),
        pending_request_work_item_ids=tuple(
            item.outcome_id for item in frontier.bindings if item.block is not None and not item.block.resolved
        ),
    )


def _work_item_projectors(
    contracts: dict[str, DeliveryContract],
    runtimes: dict[str, DeliveryRuntime],
) -> dict[str, WorkItemProjector]:
    projectors = {}
    for change_id, contract in contracts.items():
        frontier = DeliveryFrontier.model_validate_json(runtimes[change_id].frontier_bytes())
        projectors[change_id] = WorkItemProjector(
            _project_authority(contract, frontier),
            _project_evidence(contract, frontier),
        )
    return projectors


def load_delivery_application(config: DeliveryStartupConfig) -> PortfolioApplication:
    """Construct every Delivery owner from one fully validated startup config."""
    _validate_git_config(config)
    _authorize_configured_target(config)
    contracts = _load_contracts(config.target_root)
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
        work_item_projectors=_work_item_projectors(contracts, runtimes),
        completed_history_catalog=CompletedHistoryCatalog(config.repository_root, config.integration_target),
    )
    return PortfolioApplication(
        runtimes,
        dependencies,
        PortfolioApplicationConfig(
            package_root=config.package_root,
            execution_capacity=config.execution_capacity,
            role_policies=_role_policies(config),
        ),
    )


def _live_application() -> PortfolioApplication:
    if _live_context is None:
        message = "Delivery application is unavailable outside server lifespan"
        raise RuntimeError(message)
    return _live_context.application


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[DeliveryAppContext]:
    """Construct one explicitly configured Delivery application for this process."""
    global _live_context  # noqa: PLW0603 - process lifespan owns this binding.
    config = load_delivery_config(_delivery_config_path())
    context = DeliveryAppContext(application=load_delivery_application(config))
    _live_context = context
    try:
        yield context
    finally:
        _live_context = None


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)
register_target_tools(mcp, TargetMCPAdapter.from_provider(_live_application))

__all__ = [
    "DeliveryAppContext",
    "DeliveryStartupConfig",
    "DeliveryStartupDiagnostic",
    "TargetMCPAdapter",
    "app_lifespan",
    "load_delivery_application",
    "load_delivery_config",
    "mcp",
]
