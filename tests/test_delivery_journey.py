"""V01 (N10 D2): one Change from admission to completion through registered Delivery MCP and Cockpit HTTP."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from mcp import Client
from serve.delivery.tests.evidence_support import finalization_proof

from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_delivery.delivery_application_loader import load_delivery_application
from owlbear_delivery.delivery_runtime import (
    DeliveryCommandResult,
    DeliveryFinalizationSemantics,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryTaskDefinition,
)
from owlbear_delivery.publication_provider import (
    FindPublicationPullRequest,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery_github.memory import InMemoryPublicationProvider
from owlbear_delivery_mcp.target_server import assemble_target_server

if TYPE_CHECKING:
    from types import ModuleType

CHANGE_ID = "journey"
REPOSITORY = "example/project"
SESSION = {"host_id": "journey-host", "capabilities": ["planner", "builder", "finalizer", "engine"]}
OBSERVED_AT = datetime(2026, 10, 5, 12, tzinfo=UTC)
INTENT = """# Journey

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: N10 journey
statement: Deliver one reviewed product change.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Ship the journey
promise: The product file carries the journey line.
acceptance: ["AC-001: The product file names the journey."]
commitments: [COM-001]
dependencies: []
```
"""


def _seed() -> ModuleType:
    """The assembled Work E2E seed owns the disposable repository and config writers."""
    path = Path(__file__).resolve().parents[1] / "serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py"
    spec = importlib.util.spec_from_file_location("seed_work_portfolio_delivery", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed executable and test-owned arguments.
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@dataclass
class _FollowingMemoryProvider(InMemoryPublicationProvider):
    """Memory GitHub whose open pull requests follow branch pushes and report clean mergeability, as GitHub's do."""

    remote: Path | None = None

    def _follow(self) -> None:
        assert self.remote is not None
        for key, pull_request in tuple(self.pull_requests.items()):
            if pull_request.state != "open":
                continue
            head = _git(self.remote, "rev-parse", f"refs/heads/{pull_request.head_branch}")
            self.pull_requests[key] = pull_request.model_copy(
                update={"head_sha": head, "mergeable": True, "merge_state_status": "CLEAN"}
            )

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        self._follow()
        return super().read_pull_request(repository, number)

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        self._follow()
        return super().find_pull_request(request)


async def _call(client: Client, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, (tool, result.content)
    assert result.structured_content is not None, tool
    return result.structured_content


async def _acquire(client: Client, application: Any, session_id: str) -> dict[str, Any]:
    basis = application.get_change(CHANGE_ID).readiness.basis.model_dump(mode="json")
    return await _call(
        client,
        "acquire_change_action",
        {"change_id": CHANGE_ID, "expected_basis": basis, "session_id": session_id, **SESSION},
    )


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Write the journey line",
        result="The product file names the journey.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("product.txt",),
        maintained_surfaces=("product.txt",),
        constraints=("Change only product.txt.",),
        exclusions=("No other file.",),
        acceptance_observations=("product.txt names the journey.",),
        proof_boundaries=("product.txt",),
    )


def _task_result(context: dict[str, Any], head: str) -> dict[str, Any]:
    task = DeliveryTaskDefinition.model_validate_json(json.dumps(context["task"]))
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=CHANGE_ID,
            task_or_finalization_id=task.task_id,
            exact_commit=head,
            observation_kind="pytest",
            procedure="journey product check",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="journey-builder",
            observed_at=OBSERVED_AT,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=head,
            author_id="journey-builder",
            reviewer_id="journey-reviewer",
            evidence=("The exact commit satisfies the task.",),
            reviewed_at=OBSERVED_AT,
        )
    )
    return {
        "result_id": "result-task-001",
        "change_id": CHANGE_ID,
        "authority_digest": context["launch"]["authority_digest"],
        "task_id": task.task_id,
        "task_digest": task.digest,
        "completed_commit": head,
        "observations": [observation.model_dump(mode="json")],
        "review": review.model_dump(mode="json"),
    }


async def _agent_plans_and_builds(client: Client, application: Any) -> str:
    package = await _call(
        client, "create_design_session", {"change_id": CHANGE_ID, "intent_bytes": INTENT, "design_bytes": "# Design\n"}
    )
    admitted = await _call(
        client,
        "admit_change",
        {"change_id": CHANGE_ID, "expected_package_id": package["package_id"], "active_claim_ids": []},
    )
    assert admitted["contract"]["change_id"] == CHANGE_ID

    planner = (await _acquire(client, application, "planner-session"))["launch"]
    assert planner is not None
    assert planner["task_id"] is None
    claim_id = planner["claim"]["claim_id"]
    published = await _call(
        client,
        "publish_delivery_plan",
        {
            "change_id": CHANGE_ID,
            "plan": {"outcome_id": "OUT-001", "claim_id": claim_id, "tasks": [_task().model_dump(mode="json")]},
        },
    )
    await _call(
        client,
        "transition_delivery",
        {
            "change_id": CHANGE_ID,
            "transition": {
                "action": "advance",
                "outcome_id": "OUT-001",
                "claim_id": claim_id,
                "output": published["output"],
            },
        },
    )

    acquired = await _acquire(client, application, "builder-session")
    if acquired["kind"] == "reconciled":
        acquired = await _acquire(client, application, "builder-session")
    builder = acquired["launch"]
    assert builder is not None, acquired
    assert builder["task_id"] == "TASK-001"
    context = await _call(
        client,
        "show_build_context",
        {
            "change_id": CHANGE_ID,
            "outcome_id": "OUT-001",
            "attempt_id": builder["claim"]["attempt_id"],
            "claim_id": builder["claim"]["claim_id"],
        },
    )
    worktree = Path(builder["worktree_path"])
    (worktree / "product.txt").write_text("journey\n", encoding="utf-8")
    _git(worktree, "commit", "-am", "Write the journey line")
    head = _git(worktree, "rev-parse", "HEAD")
    await _call(
        client,
        "submit_result",
        {
            "change_id": CHANGE_ID,
            "outcome_id": "OUT-001",
            "claim_id": builder["claim"]["claim_id"],
            "result": _task_result(context, head),
        },
    )
    return head


async def _agent_finalizes_and_publishes(client: Client, application: Any, head: str) -> tuple[list[str], str]:
    """Continue with only Finalizer and engine actions until Delivery asks the user to approve the merge."""
    steps: list[str] = []
    finalized = ""
    for index in range(20):
        acquired = await _acquire(client, application, f"continue-{index}")
        if acquired["finalization"] is not None:
            context = await _call(client, "show_finalization_context", {"change_id": CHANGE_ID})
            finalized = context["change_head"]
            assert _git(Path(context["worktree_path"]), "merge-base", "--is-ancestor", head, finalized) == ""
            proof = finalization_proof(
                DeliveryFinalizationSemantics.model_validate_json(json.dumps(context["semantics"])),
                change_id=CHANGE_ID,
                exact_head=finalized,
                operation_id=acquired["finalization"]["attempt"]["writer"]["attempt_id"],
                observed_at=OBSERVED_AT,
                procedure="journey finalization check",
                author_id="journey-builder",
                reviewer_id="journey-finalization-reviewer",
                evidence="The exact Change head satisfies finalization authority.",
            )
            await _call(
                client, "finalize_change", {"change_id": CHANGE_ID, "finalization": proof.model_dump(mode="json")}
            )
            steps.append("finalize")
        elif acquired["engine_action"] is not None:
            action = acquired["engine_action"]
            executed = await _call(
                client, "execute_change_action", {"change_id": CHANGE_ID, "operation_id": action["operation_id"]}
            )
            steps.append(f"{action['kind']}:{executed['reason_code']}:{executed['failure']}")
        elif acquired["kind"] == "reconciled":
            steps.append("reconciled")
        else:
            assert (acquired["kind"], acquired["reason_code"]) == ("waiting", "merge-approval-required"), (
                steps,
                acquired,
            )
            return steps, finalized
    pytest.fail(f"no merge offer after {steps}")


@pytest.mark.asyncio
async def test_v01_one_change_runs_from_admission_to_completion_through_mcp_and_cockpit(tmp_path: Path) -> None:
    seed = _seed()
    workspace = tmp_path / "workspace"
    base = seed._seed_repository(workspace)  # noqa: SLF001
    seed._write_host_config(workspace)  # noqa: SLF001
    config = seed._write_config(workspace)  # noqa: SLF001
    memory = _FollowingMemoryProvider(remote=workspace / ".git" / "e2e-origin.git")
    memory.add_repository(PublicationRepository(repository=REPOSITORY, default_branch="main"))
    memory.set_branch_head(REPOSITORY, "main", base)

    application = load_delivery_application(config, workspace_root=workspace, publication_provider=memory)
    async with Client(assemble_target_server(application)) as client:
        head = await _agent_plans_and_builds(client, application)

    # A fresh process resumes from persisted state only (U4).
    application = load_delivery_application(config, workspace_root=workspace, publication_provider=memory)
    async with Client(assemble_target_server(application)) as client:
        steps, finalized = await _agent_finalizes_and_publishes(client, application, head)

    # The user side: Cockpit reads, one approval, and the page's automatic acceptance reconciliation.
    with TestClient(assemble_target_app(application)) as cockpit:
        detail = cockpit.get(f"/api/changes/{CHANGE_ID}/work-items/publication")
        assert detail.status_code == 200, detail.text
        readiness = detail.json()["item"]["readiness"]
        assert readiness["reason_code"] == "merge-approval-required"
        offer = readiness["merge_offer"]
        assert (offer["head_sha"], offer["target_head"]) == (finalized, base)
        approved = cockpit.post(
            f"/api/changes/{CHANGE_ID}/approve-merge",
            json={"offer_id": offer["offer_id"], "submission_id": "journey-approval"},
        )
        assert approved.status_code == 200, approved.text
        memory.execute_pending_merges()
        reconciled = cockpit.post("/api/work-items/acceptance/reconcile", json={"change_ids": [CHANGE_ID]})
        assert reconciled.status_code == 200, reconciled.text
        completed = cockpit.get(f"/api/work-items/completed/{CHANGE_ID}")
        portfolio = cockpit.get("/api/work-items")

    assert [step.split(":")[0] for step in steps if step != "reconciled"] == [
        "sync-target",
        "finalize",
        "reconcile-checkpoint",
        "mark-ready",
    ], steps
    assert [json.loads(body)["sha"] for body in memory.merge_request_bodies] == [finalized]
    assert completed.status_code == 200, completed.text
    record = completed.json()
    assert (record["record_kind"], record["finalized_change_head"]) == ("completion-receipt", finalized)
    assert [outcome["completion_id"] for outcome in reconciled.json()["outcomes"]] == [record["completion_id"]]
    operating = portfolio.json()["operating"]
    assert (operating["unfinished_change_count"], operating["completed_change_count"]) == (0, 1)
    async with Client(assemble_target_server(application)) as client:
        assert (await _acquire(client, application, "after-completion"))["kind"] == "terminal"
