"""Contract tests for the live Delivery MCPServer assembly and startup."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp import Client
from pydantic import BaseModel, ConfigDict

import owlbear_delivery_mcp.server as live_server
from owlbear_delivery import (
    AdministrativeDeliveryMove,
    ChangeCoordination,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliverySourceBinding,
    DeliveryStage,
    OutcomeAuthorityBinding,
    PortfolioApplication,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryResultCandidate,
    DeliveryReview,
    DeliveryReviewReceipt,
    PublishDeliveryResult,
)
from owlbear_delivery_mcp.server import (
    app_lifespan,
    load_delivery_application,
    load_delivery_config,
    mcp,
)
from owlbear_delivery_github import GitHubCliPublicationProvider
from owlbear_delivery_mcp.target_models import DeliveryStartupDiagnostic
from owlbear_delivery_mcp.target_server import TargetMCPAdapter, assemble_target_server

DELIVERY_TOOLS = {
    "create_design_session",
    "read_design_session",
    "revise_design_session",
    "publish_design_checkpoint",
    "derive_delivery_contract",
    "validate_delivery_contract",
    "admit_delivery_change",
    "list_work_items",
    "show_work_item",
    "acquire_frontier_work",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "publish_delivery_plan",
    "publish_delivery_result",
    "finalize_change",
    "mark_change_ready",
    "reconcile_finalization_head",
    "reconcile_change_checkpoint",
    "observe_change_publication_checks",
    "observe_acceptance",
    "transition_delivery",
    "recover_claim",
    "recover_integration_repair_claim",
    "show_integration_attention",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
}
READ_TOOLS = {
    "read_design_session",
    "derive_delivery_contract",
    "validate_delivery_contract",
    "list_work_items",
    "show_work_item",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "show_integration_attention",
    "observe_change_publication_checks",
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


class _PublicationApplication(_RecordingApplication):
    def __init__(self) -> None:
        super().__init__()
        self.transition: object | None = None

    def publish_delivery_result(self, _change_id: str, request: object) -> DeliveryResultCandidate:
        self.calls.append("publish_delivery_result")
        assert isinstance(request, PublishDeliveryResult)
        return DeliveryResultCandidate(
            candidate_id="result-" + "d" * 64,
            claim_id="claim-1",
            digest="d" * 64,
            result=request.result,
        )

    def transition_delivery(self, _change_id: str, request: object) -> _Result:
        self.calls.append("transition_delivery")
        self.transition = request
        return _Result(operation="transition_delivery")


class _BlockingAcceptanceApplication(_RecordingApplication):
    def __init__(self, started: threading.Event, release: threading.Event) -> None:
        super().__init__()
        self._started = started
        self._release = release

    def observe_acceptance(self, _change_id: str) -> _Result:
        self._started.set()
        self._release.wait(timeout=2)
        return _Result(operation="observe_acceptance")


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
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repository


def _config() -> dict[str, object]:
    return {
        "schema_version": 2,
        "remote": "origin",
        "target_branch": "main",
        "github_repository": "example/project",
    }


def _write_config(path: Path, content: dict[str, object]) -> None:
    path.write_text(json.dumps(content), encoding="utf-8")


def _write_delivery_state(runtime_root: Path, repository: Path) -> None:
    digest = hashlib.sha256(b"source").hexdigest()
    contract = DeliveryContract(
        change_id="change-a",
        title="Assembled projection",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="assembled MCP test",
                statement="Project current Delivery state.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Observe transitions",
                promise="Registered tools return current stage.",
                acceptance=("The stage changes without server reload.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=digest),
            DeliverySourceBinding(source_name="design.md", sha256=digest),
        ),
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
            ),
        ),
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    change_root.joinpath("contract.json").write_text(contract.model_dump_json(), encoding="utf-8")
    change_root.joinpath("frontier.json").write_text(frontier.model_dump_json(), encoding="utf-8")
    target_head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "main"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    coordination_root = runtime_root / "claims/changes"
    coordination_root.mkdir(parents=True)
    coordination_root.joinpath("change-a.json").write_text(
        ChangeCoordination(
            change_id="change-a",
            branch="main",
            worktree_path=repository,
            integration_target="main",
            target_head=target_head,
            last_reviewed_commit=target_head,
        ).model_dump_json(),
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_live_registry_is_exact_and_annotated_from_assembled_tools() -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert set(tools) == DELIVERY_TOOLS
    assert set(tools).isdisjoint(EXCLUDED_TOOLS)
    for name, tool in tools.items():
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is (name in READ_TOOLS)
        assert tool.annotations.idempotent_hint is (name != "acquire_frontier_work")
        assert tool.annotations.destructive_hint is False
        request_schema = tool.input_schema["properties"]["request"]
        assert "$ref" in request_schema
        request_definition = tool.input_schema["$defs"][request_schema["$ref"].removeprefix("#/$defs/")]
        if "$ref" in request_definition:
            request_definition = tool.input_schema["$defs"][request_definition["$ref"].removeprefix("#/$defs/")]
        assert request_definition["additionalProperties"] is False


@pytest.mark.asyncio
async def test_registered_tool_invokes_strict_adapter_once() -> None:
    application = _RecordingApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        result = await client.call_tool("list_work_items", {"request": {}})

    assert set(tools) == DELIVERY_TOOLS
    assert result.structured_content == {"result": []}
    assert application.calls == ["list_work_items"]


def _published_result_payload() -> dict[str, object]:
    completed_commit = "c" * 40
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id="change-a",
            task_or_finalization_id="TASK-001",
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="live Delivery MCP contract test",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="MCP server test author",
            reviewer_id="MCP server test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return {
        "result_id": "result-1",
        "change_id": "change-a",
        "authority_digest": "a" * 64,
        "task_id": "TASK-001",
        "task_digest": "b" * 64,
        "completed_commit": completed_commit,
        "observations": [observation.model_dump(mode="json")],
        "review": review.model_dump(mode="json"),
    }


@pytest.mark.asyncio
async def test_published_result_output_forwards_unchanged_to_transition() -> None:
    application = _PublicationApplication()
    server = assemble_target_server(application)  # type: ignore[arg-type]
    publication_request = {
        "change_id": "change-a",
        "request": {
            "outcome_id": "OUT-001",
            "claim_id": "claim-1",
            "result": _published_result_payload(),
        },
    }

    async with Client(server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        published = await client.call_tool("publish_delivery_result", {"request": publication_request})
        assert published.structured_content is not None
        output = published.structured_content["output"]
        transitioned = await client.call_tool(
            "transition_delivery",
            {
                "request": {
                    "change_id": "change-a",
                    "request": {
                        "action": "advance",
                        "outcome_id": "OUT-001",
                        "claim_id": "claim-1",
                        "output": output,
                    },
                },
            },
        )

    publication_schema = tools["publish_delivery_result"].input_schema["properties"]["request"]
    publication_definitions = tools["publish_delivery_result"].input_schema["$defs"]
    transition_definitions = tools["transition_delivery"].input_schema["$defs"]
    publication_definition = publication_definitions[publication_schema["$ref"].removeprefix("#/$defs/")]
    publication_definition = publication_definitions[publication_definition["$ref"].removeprefix("#/$defs/")]
    publication_request_definition = publication_definitions[
        publication_definition["properties"]["request"]["$ref"].removeprefix("#/$defs/")
    ]
    result_definition = publication_definitions[
        publication_request_definition["properties"]["result"]["$ref"].removeprefix("#/$defs/")
    ]
    assert publication_definition["properties"]["change_id"]["type"] == "string"
    assert {"observations", "review"} <= set(result_definition["required"])
    finalization_schema = tools["finalize_change"].input_schema
    finalization_request = finalization_schema["$defs"]["FinalizeDeliveryChange"]
    assert {"operation_id", "exact_head", "observations", "review"} <= set(finalization_request["required"])
    ready_schema = tools["mark_change_ready"].input_schema
    ready_request = ready_schema["$defs"]["MarkChangePullRequestReady"]
    assert {"change_id", "operation_id", "finalization_id", "exact_head"} == set(ready_request["required"])
    reconciliation_schema = tools["reconcile_finalization_head"].input_schema
    reconciliation_request = reconciliation_schema["$defs"]["ChangeParams"]
    assert set(reconciliation_request["properties"]) == {"change_id"}
    acceptance_schema = tools["observe_acceptance"].input_schema
    acceptance_request = acceptance_schema["$defs"]["ChangeParams"]
    assert set(acceptance_request["properties"]) == {"change_id"}
    assert transition_definitions["DeliveryTransition"]["discriminator"]["propertyName"] == "action"
    assert "output" in tools["publish_delivery_plan"].output_schema["required"]
    assert "output" in tools["publish_delivery_result"].output_schema["required"]
    assert output == {
        "output_id": "result-" + "d" * 64,
        "claim_id": "claim-1",
        "stage": "implementation",
        "kind": "implementation",
        "digest": "d" * 64,
    }
    assert transitioned.structured_content == {"operation": "transition_delivery"}
    assert application.calls == ["publish_delivery_result", "transition_delivery"]


@pytest.mark.asyncio
async def test_acceptance_observation_yields_the_mcp_event_loop() -> None:
    started = threading.Event()
    release = threading.Event()
    fallback_release = threading.Timer(1, release.set)
    fallback_release.start()
    adapter = TargetMCPAdapter(_BlockingAcceptanceApplication(started, release))  # type: ignore[arg-type]
    launched_at = time.monotonic()

    task = asyncio.create_task(adapter.observe_acceptance({"change_id": "change-a"}))
    assert await asyncio.to_thread(started.wait, 2)
    elapsed = time.monotonic() - launched_at
    release.set()
    result = await task
    fallback_release.cancel()

    assert elapsed < 0.5
    assert result == {"operation": "observe_acceptance"}


MISSING_FIELDS = [
    ("schema_version",),
    ("remote",),
    ("target_branch",),
    ("github_repository",),
]


@pytest.mark.parametrize("field_path", MISSING_FIELDS)
def test_missing_required_config_fails_unconfigured_before_state_creation(
    tmp_path: Path,
    field_path: tuple[str, ...],
) -> None:
    content = _config()
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
async def test_missing_canonical_config_fails_before_state_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        async with app_lifespan(mcp):
            pass

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_UNCONFIGURED"
    assert exc_info.value.field == ".owlbear/delivery/config.json"
    assert not (tmp_path / ".owlbear/target").exists()


@pytest.mark.parametrize(
    ("mutation", "field"),
    [
        (lambda content, _tmp: content.update(schema_version=1), "schema_version"),
        (lambda content, _tmp: content.update(remote=""), "remote"),
        (lambda content, _tmp: content.update(target_branch=""), "target_branch"),
        (lambda content, _tmp: content.update(github_repository="invalid"), "github_repository"),
        (lambda content, _tmp: content.update(execution_capacity=2), "execution_capacity"),
    ],
)
def test_invalid_config_fails_before_state_creation(
    tmp_path: Path,
    mutation: Any,
    field: str,
) -> None:
    content = _config()
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
    assert exc_info.value.field == ".owlbear/delivery/config.json"
    assert "do-not-report" not in str(exc_info.value)


def test_invalid_target_branch_fails_before_owner_state_mutation(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    content = _config()
    content["target_branch"] = "bad target"
    path = tmp_path / "delivery.json"
    _write_config(path, content)
    config = load_delivery_config(path)
    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(config, repository)

    assert exc_info.value.code == "ERR_DELIVERY_STARTUP_INVALID"
    assert exc_info.value.field == "target_branch"
    assert not (tmp_path / "target").exists()


def test_startup_uses_remote_tracking_target_without_local_target_branch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(repository, "checkout", "--detach", "HEAD")
    _git(repository, "branch", "-D", "main")
    path = tmp_path / "delivery.json"
    _write_config(path, _config())

    application = load_delivery_application(load_delivery_config(path), repository)

    assert isinstance(application, PortfolioApplication)


def test_missing_remote_tracking_target_fails_before_owner_state_mutation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(repository, "update-ref", "-d", "refs/remotes/origin/main")
    path = tmp_path / "delivery.json"
    _write_config(path, _config())

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(load_delivery_config(path), repository)

    assert exc_info.value.field == "target_branch"
    assert not (tmp_path / "target").exists()


def test_github_repository_mismatch_fails_before_owner_state_mutation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    content = _config()
    content["github_repository"] = "other/project"
    path = tmp_path / "delivery.json"
    _write_config(path, content)

    with pytest.raises(DeliveryStartupDiagnostic) as exc_info:
        load_delivery_application(load_delivery_config(path), repository)

    assert exc_info.value.field == "github_repository"
    assert not (tmp_path / "target").exists()


@pytest.mark.asyncio
async def test_complete_config_constructs_application_before_lifespan_yield(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = repository / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True)
    _write_config(path, _config())
    monkeypatch.chdir(repository)
    async with app_lifespan(mcp) as context:
        tools = {tool.name: tool for tool in await mcp.list_tools()}
        assert isinstance(context.application, PortfolioApplication)
        assert set(tools) == DELIVERY_TOOLS
        assert (repository / ".owlbear/delivery/runtime/capacity.json").is_file()

    with pytest.raises(RuntimeError, match="outside server lifespan"):
        live_server._live_application()


def test_mcp_startup_delegates_owner_construction_to_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    path = tmp_path / "delivery.json"
    _write_config(path, _config())
    config = load_delivery_config(path)
    application = object()
    calls: list[tuple[object, Path, object]] = []

    def load_core(candidate: object, *, workspace_root: Path, publication_provider: object) -> object:
        calls.append((candidate, workspace_root, publication_provider))
        return application

    monkeypatch.setattr(live_server, "load_core_delivery_application", load_core)

    assert load_delivery_application(config, repository) is application
    assert len(calls) == 1
    assert calls[0][:2] == (config, repository)
    assert isinstance(calls[0][2], GitHubCliPublicationProvider)


@pytest.mark.asyncio
async def test_assembled_work_item_tools_observe_runtime_transition(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    _write_delivery_state(runtime_root, repository)
    path = tmp_path / "delivery.json"
    _write_config(path, _config())
    config = load_delivery_config(path)
    application = load_delivery_application(config, repository)
    server = assemble_target_server(application)
    async with Client(server) as client:
        before = await client.call_tool(
            "show_work_item",
            {"request": {"change_id": "change-a", "work_item_id": "OUT-001"}},
        )
        application.administrative_move(
            "change-a",
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Operator evidence invalidated the result.",
                expected_version=application.preview_administrative_move(
                    "change-a",
                    "OUT-001",
                    DeliveryStage.PLANNING,
                ).snapshot_version,
            ),
        )
        listed = await client.call_tool("list_work_items", {"request": {}})
        after = await client.call_tool(
            "show_work_item",
            {"request": {"change_id": "change-a", "work_item_id": "OUT-001"}},
        )

    assert before.structured_content is not None
    assert listed.structured_content is not None
    assert after.structured_content is not None
    assert before.structured_content["projection"]["stage"] == "completed"
    assert listed.structured_content["result"][0]["stage"] == "planning"
    assert after.structured_content["projection"]["stage"] == "planning"
