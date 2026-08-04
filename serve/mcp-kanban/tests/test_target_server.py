"""Contract tests for the live Delivery FastMCP assembly and startup."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

import owlbear_mcp_kanban.server as live_server
from owlbear_kanban import PortfolioApplication
from owlbear_mcp_kanban.server import (
    app_lifespan,
    load_delivery_application,
    load_delivery_config,
    mcp,
)
from owlbear_mcp_kanban.target_models import DeliveryStartupDiagnostic
from owlbear_mcp_kanban.target_server import assemble_target_server

DELIVERY_TOOLS = {
    "create_design_session",
    "publish_design_checkpoint",
    "derive_delivery_contract",
    "validate_delivery_contract",
    "admit_delivery_change",
    "list_work_items",
    "show_work_item",
    "acquire_frontier_work",
    "show_plan_context",
    "show_build_context",
    "publish_delivery_plan",
    "publish_delivery_result",
    "transition_delivery",
    "recover_claim",
    "list_integration_ready_changes",
    "show_integration_attention",
    "integrate_ready_change",
    "admit_reviewed_integration_repair",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
}
READ_TOOLS = {
    "derive_delivery_contract",
    "validate_delivery_contract",
    "list_work_items",
    "show_work_item",
    "show_plan_context",
    "show_build_context",
    "list_integration_ready_changes",
    "show_integration_attention",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
}
EXCLUDED_TOOLS = {
    "list_changes",
    "show_change",
    "validate_change",
    "admit_change",
    "resolve_request",
    "create_request",
    "unblock_delivery",
    "list_semantic_updates",
    "list_work_item_activity",
    "show_completion_summary",
    "respond_to_review",
    "arbitrate_attempt",
    "recover_interrupted_task",
    "start_job",
    "finish_plan",
    "finish_build",
    "finish_assembly",
    "return_delivery",
    "list_frontier",
    "show_job",
    "show_attempt",
    "show_receipt",
}


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    operation: str


class _RecordingApplication:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        def operation(*_args: object, **_kwargs: object) -> object:
            self.calls.append(name)
            return () if name == "list_work_items" else _Result(operation=name)

        return operation


def _git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
    )


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery Startup Test")
    _git(repository, "config", "user.email", "delivery-startup@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    return repository


def _config(tmp_path: Path, repository: Path | None = None) -> dict[str, object]:
    identities = {
        "worker_agent": "worker",
        "worker_model": "worker-model",
        "reviewer_agent": "reviewer",
        "reviewer_model": "reviewer-model",
    }
    return {
        "package_root": str(tmp_path / "packages"),
        "target_root": str(tmp_path / "target"),
        "repository_root": str(repository or tmp_path),
        "worktree_root": str(tmp_path / "worktrees"),
        "execution_capacity": 3,
        "writer_capacity": 1,
        "integration_target": "main",
        "role_policies": {
            "planner": dict(identities),
            "builder": dict(identities),
            "assembly-reviewer": dict(identities),
        },
    }


def _write_config(path: Path, content: dict[str, object]) -> None:
    path.write_text(json.dumps(content), encoding="utf-8")


@pytest.mark.asyncio
async def test_live_registry_is_exact_and_annotated_from_assembled_tools() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert set(tools) == DELIVERY_TOOLS
    assert set(tools).isdisjoint(EXCLUDED_TOOLS)
    for name, tool in tools.items():
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is (name in READ_TOOLS)
        assert tool.annotations.idempotentHint is (name != "acquire_frontier_work")
        assert tool.annotations.destructiveHint is False


@pytest.mark.asyncio
async def test_registered_tool_invokes_strict_adapter_once() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    tools = {tool.name: tool for tool in await server.list_tools()}

    assert set(tools) == DELIVERY_TOOLS
    registered = server._tool_manager.get_tool("list_work_items")  # noqa: SLF001
    assert registered is not None
    result = await registered.fn({})

    assert result == []
    assert application.calls == ["list_work_items"]


MISSING_FIELDS = [
    ("execution_capacity",),
    ("writer_capacity",),
    ("integration_target",),
    ("role_policies", "planner"),
    ("role_policies", "builder"),
    ("role_policies", "assembly-reviewer"),
    *(
        ("role_policies", role, identity)
        for role in ("planner", "builder", "assembly-reviewer")
        for identity in ("worker_agent", "worker_model", "reviewer_agent", "reviewer_model")
    ),
]


@pytest.mark.parametrize("field_path", MISSING_FIELDS)
def test_missing_required_config_fails_unconfigured_before_state_creation(
    tmp_path: Path,
    field_path: tuple[str, ...],
) -> None:
    content = copy.deepcopy(_config(tmp_path))
    parent = content
    for key in field_path[:-1]:
        parent = parent[key]  # type: ignore[assignment,index]
    del parent[field_path[-1]]  # type: ignore[arg-type,index]
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    diagnostic = exc_info.value
    assert diagnostic.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert diagnostic.field == ".".join(field_path)
    assert diagnostic.retry_safe is False
    assert not (tmp_path / "target").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("configured_path", [None, "missing.json"])
async def test_missing_config_path_or_file_fails_before_state_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    configured_path: str | None,
) -> None:
    monkeypatch.delenv("OWLBEAR_DELIVERY_CONFIG", raising=False)
    if configured_path is not None:
        monkeypatch.setenv("OWLBEAR_DELIVERY_CONFIG", str(tmp_path / configured_path))

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert exc_info.value.field == "OWLBEAR_DELIVERY_CONFIG"
    assert not (tmp_path / "target").exists()


@pytest.mark.parametrize(
    ("mutation", "field"),
    [
        (lambda content, _tmp: content.update(execution_capacity=0), "execution_capacity"),
        (lambda content, _tmp: content.update(writer_capacity="1"), "writer_capacity"),
        (lambda content, _tmp: content.update(package_root="relative"), "package_root"),
        (lambda content, tmp: content.update(repository_root=str(tmp / "absent")), "repository_root"),
        (
            lambda content, _tmp: content["role_policies"]["planner"].update(worker_agent=1),
            "role_policies.planner.worker_agent",
        ),
    ],
)
def test_invalid_config_fails_before_state_creation(
    tmp_path: Path,
    mutation: Any,
    field: str,
) -> None:
    content = _config(tmp_path)
    mutation(content, tmp_path)
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == field
    assert exc_info.value.retry_safe is False
    assert not (tmp_path / "target").exists()


def test_malformed_json_fails_invalid_without_exposing_content(tmp_path: Path) -> None:
    path = tmp_path / "delivery.json"
    path.write_text('{"secret": "do-not-report"', encoding="utf-8")

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_config(path)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == "OWLBEAR_DELIVERY_CONFIG"
    assert "do-not-report" not in str(exc_info.value)


def test_invalid_integration_target_fails_before_owner_state_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    content = _config(tmp_path, repository)
    content["integration_target"] = "bad target"
    path = tmp_path / "delivery.json"
    _write_config(path, content)
    config = load_delivery_config(path)
    monkeypatch.setattr(live_server, "_authorize_configured_target", lambda _config: None)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(config)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == "integration_target"
    assert not (tmp_path / "target").exists()


@pytest.mark.asyncio
async def test_complete_config_constructs_application_before_lifespan_yield(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = tmp_path / "delivery.json"
    _write_config(path, _config(tmp_path, repository))
    monkeypatch.setenv("OWLBEAR_DELIVERY_CONFIG", str(path))
    monkeypatch.setattr(live_server, "_authorize_configured_target", lambda _config: None)

    async with app_lifespan(mcp) as context:
        tools = {tool.name: tool for tool in await mcp.list_tools()}
        assert isinstance(context.application, PortfolioApplication)
        assert set(tools) == DELIVERY_TOOLS
        assert (tmp_path / "target/target-runtime/capacity.json").is_file()

    with pytest.raises(RuntimeError, match="outside server lifespan"):
        live_server._live_application()
