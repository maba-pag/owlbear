from __future__ import annotations

import shutil
import subprocess
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import (
    CorrectiveRouteRequest,
    DispatchRuntime,
    Finding,
    FindingStore,
    GitRepositoryHistory,
    InvalidationRequest,
    JobGeneration,
    JobStore,
    NativeRuntime,
    PlanJob,
    ProofCheckoutManager,
    RejectAcceptDiagnosticCode,
    load_change,
    plan_corrective_route,
)
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext

from .test_mcp_surface_contract import _make_board


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".storage.lock"
    }


def _start(job_id: int, attempt: int, commit: str) -> dict[str, object]:
    return {
        "change_id": "replace-delivery-pipeline",
        "job_id": job_id,
        "attempt_id": f"attempt-{attempt:03}",
        "claim_id": f"claim-{attempt:03}",
        "actor_id": "acceptance-proof",
        "process_id": "acceptance-process",
        "claimed_at": f"2026-07-25T00:0{attempt}:00Z",
        "candidate_revision": commit,
    }


def _identity(start: dict[str, object]) -> dict[str, object]:
    return {key: start[key] for key in ("change_id", "job_id", "attempt_id", "claim_id", "actor_id", "process_id")}


def _materialize_plan(revision, work_root: Path) -> None:
    target = revision.graph.nodes[0]
    JobStore(work_root).materialize(
        JobGeneration(
            schema_version=1,
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            receipt_id="bootstrap-001",
            jobs=(
                PlanJob(
                    job_id=1,
                    kind="plan",
                    priority=7,
                    created_at="2026-07-25T00:00:00Z",
                    updated_at="2026-07-25T00:00:00Z",
                    change_id=revision.change_id,
                    delivery_digest=revision.delivery_digest,
                    target_node_id=target.id,
                    receipt_id="bootstrap-001",
                ),
            ),
        )
    )


async def _active_accept(tmp_path: Path):  # noqa: PLR0915 - public lifecycle assembly is the proof boundary.
    changes_dir = tmp_path / "changes"
    authority = changes_dir / "replace-delivery-pipeline"
    shutil.copytree(Path(".owlbear/changes/replace-delivery-pipeline"), authority)
    shutil.rmtree(authority / "receipts")
    shutil.rmtree(authority / "jobs")
    (authority / "plans" / "DN-001.yaml").unlink()
    loaded = load_change(changes_dir, "replace-delivery-pipeline")
    assert loaded.revision is not None
    revision = loaded.revision
    board = _make_board(tmp_path)
    _materialize_plan(revision, board)
    repository = Path.cwd()
    commit = _git_head()
    checkouts = ProofCheckoutManager(repository, tmp_path / "proof")
    runtime = DispatchRuntime(
        NativeRuntime(
            revision,
            board,
            GitRepositoryHistory(repository),
            timedelta(minutes=5),
            checkouts,
        ),
        board,
        checkouts,
    )
    app_ctx = AppContext(engine=server.KanbanEngine(board), kanban_dir=board)
    app_ctx.dispatch_runtimes[revision.change_id] = runtime
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    target = revision.graph.nodes[0]
    proof = revision.resolve(target.proof)
    closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}

    plan_start = _start(1, 1, commit)
    assert (await server.start_job(ctx, **plan_start)).diagnostic is None
    plan = await server.finish_plan(
        ctx,
        **_identity(plan_start),
        finished_at="2026-07-25T00:02:00Z",
        receipt_id="plan-001",
        code_revision=commit,
        evidence={"methods": list(proof.method)},
        node_plan={
            "packets": [
                {"id": f"{target.id}-PK-001", "dependencies": [], "impact_closure": closure},
                {
                    "id": f"{target.id}-PK-002",
                    "dependencies": [f"{target.id}-PK-001"],
                    "impact_closure": closure,
                },
            ]
        },
        build_job_ids=(2, 3),
        accept_job_id=4,
    )
    assert plan.diagnostic is None
    for job_id, attempt, receipt_id in ((2, 2, "build-001"), (3, 3, "build-002")):
        build_start = _start(job_id, attempt, commit)
        assert (await server.start_job(ctx, **build_start)).diagnostic is None
        built = await server.finish_build(
            ctx,
            **_identity(build_start),
            finished_at=f"2026-07-25T00:0{attempt + 2}:00Z",
            receipt_id=receipt_id,
            code_revision=commit,
            evidence={"methods": list(proof.method)},
            impact_closure=closure,
        )
        assert built.diagnostic is None

    accept_start = _start(4, 4, commit)
    started = await server.start_job(ctx, **accept_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    checkout = started["checkout"]
    assert checkout.commit == commit
    return revision, board, ctx, runtime, checkout, accept_start, commit


def _rejection_payload(revision, start: dict[str, object], commit: str) -> dict[str, object]:
    finding = Finding(
        schema_version=1,
        finding_id="finding-accept-001",
        source_attempt_id=str(start["attempt_id"]),
        source_job_id=int(start["job_id"]),
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="packet",
        target_id="DN-001-PK-001",
        finding_class="implementation-defect",
        detail="packet proof does not satisfy admitted behavior",
        created_at="2026-07-25T00:06:00Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="packet-implementation",
            target_node_ids=("DN-001",),
        )
    )
    invalidation = InvalidationRequest(
        invalidation_id="invalidation-accept-001",
        supersession_receipt_id="supersession-accept-001",
        invalidated_receipt_ids=("build-001",),
        routes=(route,),
        corrective_job_ids=(20,),
        issued_at="2026-07-25T00:06:00Z",
        code_revision=commit,
        priority=9,
    )
    return {
        **_identity(start),
        "rejected_at": "2026-07-25T00:06:00Z",
        "detail": "acceptance found an implementation defect",
        "evidence_ids": ("accept-proof-001",),
        "findings": (finding.model_dump(mode="json"),),
        "invalidation": invalidation.model_dump(mode="json"),
    }


@pytest.mark.asyncio
async def test_public_accept_rejection_publishes_findings_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, board, ctx, runtime, checkout, start, commit = await _active_accept(tmp_path)
    payload = _rejection_payload(revision, start, commit)
    reject = MagicMock(wraps=runtime.reject_accept)
    monkeypatch.setattr(runtime, "reject_accept", reject)

    rejected = await server.reject_accept(ctx, **payload)
    replayed = await server.reject_accept(ctx, **payload)
    forwarded = reject.call_args_list[0].args[0]
    second_finding = rejected.findings[0].model_copy(
        update={"finding_id": "finding-accept-002", "created_at": "2026-07-25T00:07:00Z"}
    )
    assert (
        FindingStore(board)
        .create(
            second_finding.finding_id,
            second_finding.model_dump(mode="json"),
        )
        .finding
        == second_finding
    )
    page_1 = await server.list_findings(ctx, change_id=revision.change_id, limit=1)
    assert page_1.next_cursor is not None
    page_2 = await server.list_findings(
        ctx,
        change_id=revision.change_id,
        cursor=page_1.next_cursor,
        limit=1,
    )
    shown = await server.show_finding(
        ctx,
        change_id=revision.change_id,
        finding_id="finding-accept-001",
    )

    assert rejected.diagnostic is None
    assert replayed == rejected
    assert forwarded.job_id == start["job_id"]
    assert forwarded.findings[0] == rejected.findings[0]
    assert forwarded.invalidation.invalidation_id == "invalidation-accept-001"
    assert rejected.event is not None
    assert rejected.event.kind == "failed"
    assert rejected.invalidation is not None
    assert tuple(item.job.job_id for item in rejected.invalidation.corrective_jobs) == (20,)
    assert page_1.items == (shown,)
    assert page_2.items == (second_finding,)
    assert page_2.next_cursor is None
    assert shown == rejected.findings[0]
    assert not checkout.root.exists()
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    before_errors = _snapshot(board)
    with pytest.raises(ToolError, match="ERR_CURSOR_STALE"):
        await server.list_findings(ctx, change_id=revision.change_id, cursor="stale-999", limit=1)
    with pytest.raises(ToolError, match="ERR_FINDING_MISSING"):
        await server.show_finding(ctx, change_id=revision.change_id, finding_id="finding-missing")
    assert _snapshot(board) == before_errors


@pytest.mark.asyncio
async def test_public_accept_rejection_failure_preserves_all_stores(tmp_path: Path) -> None:
    revision, _board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    payload = _rejection_payload(revision, start, commit)
    invalidation = dict(payload["invalidation"])
    invalidation["invalidated_receipt_ids"] = ("build-missing",)
    payload["invalidation"] = invalidation
    before = _snapshot(tmp_path)

    rejected = await server.reject_accept(ctx, **payload)

    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is RejectAcceptDiagnosticCode.INVALIDATION_INVALID
    assert _snapshot(tmp_path) == before
    assert checkout.root.exists()
