"""Public MCP contract tests for native request creation and reads."""

from __future__ import annotations

import inspect
import shutil
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import JobGeneration, JobStore, NativeWorkspace, PlanJob, load_change
from owlbear_kanban.change import ChangeRevision
from owlbear_kanban.runtime_requests import NativeRequestRuntime, RequestResolution
from owlbear_mcp_kanban.server import AppContext, create_request, list_requests, mcp, show_request

if TYPE_CHECKING:
    from owlbear_kanban.jobs import StoredJob


CHANGE_ID = "replace-delivery-pipeline"
CREATED_AT = "2026-07-25T00:00:00Z"


@pytest.fixture
def work_root(tmp_path: Path) -> Path:
    """Copy the admitted change so MCP tools cross the real loader boundary."""
    source = Path(".owlbear/changes") / CHANGE_ID
    destination = tmp_path / "changes" / CHANGE_ID
    shutil.copytree(source, destination)
    return tmp_path


@pytest.fixture
def revision(work_root: Path) -> ChangeRevision:
    """Load the copied admitted change through the production loader."""
    loaded = load_change(work_root / "changes", CHANGE_ID)
    assert loaded.revision is not None
    return loaded.revision


@pytest.fixture
def app_ctx(work_root: Path) -> AppContext:
    """Provide the board root used by the MCP request runtime."""
    kanban_dir = work_root / "board"
    kanban_dir.mkdir()
    return AppContext(workspace=NativeWorkspace(kanban_dir, timedelta(hours=1)))


@pytest.fixture
def mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Provide the FastMCP lifespan context expected by public tools."""
    context = MagicMock()
    context.request_context.lifespan_context = app_ctx
    return context


def _materialize_job(  # noqa: PLR0913
    work_root: Path,
    revision: ChangeRevision,
    *,
    job_id: int = 1,
    target_node_id: str | None = None,
    change_id: str | None = None,
    delivery_digest: str | None = None,
) -> StoredJob:
    """Materialize one job record for request-reference scenarios."""
    resolved_change_id = change_id or revision.change_id
    resolved_digest = delivery_digest or revision.delivery_digest
    generation = JobGeneration(
        schema_version=1,
        change_id=resolved_change_id,
        delivery_digest=resolved_digest,
        receipt_id=f"receipt-{job_id}",
        jobs=(
            PlanJob(
                job_id=job_id,
                kind="plan",
                priority=0,
                created_at=CREATED_AT,
                updated_at=CREATED_AT,
                change_id=resolved_change_id,
                delivery_digest=resolved_digest,
                target_node_id=target_node_id or revision.graph.nodes[0].id,
                receipt_id=f"receipt-{job_id}",
            ),
        ),
    )
    return JobStore(work_root).materialize(generation)[0]


def _storage_snapshot(work_root: Path) -> dict[str, bytes]:
    """Capture complete request and active-job bytes below the runtime root."""
    paths = sorted((*work_root.glob("requests/**/*.yaml"), *work_root.glob("jobs/**/*.yaml")))
    return {path.relative_to(work_root).as_posix(): path.read_bytes() for path in paths}


async def _create_action(  # noqa: PLR0913
    mcp_ctx: MagicMock,
    revision: ChangeRevision,
    *,
    request_id: str,
    created_at: str = CREATED_AT,
    change_id: str | None = None,
    delivery_digest: str | None = None,
    target_node_id: str | None = None,
    job_ids: list[int] | None = None,
    summary: str = "External evidence is required.",
) -> dict[str, object]:
    """Invoke the public create tool with a complete native action payload."""
    return await create_request(
        mcp_ctx,
        request_id=request_id,
        created_at=created_at,
        change_id=change_id or revision.change_id,
        delivery_digest=delivery_digest or revision.delivery_digest,
        kind="action",
        title="Provide release evidence",
        summary=summary,
        agent="builder",
        target_node_id=target_node_id,
        job_ids=job_ids,
        body="release-id=42",
    )


@pytest.mark.parametrize("tool_name", ["create_request", "list_requests", "show_request"])
def test_native_request_tools_are_registered(tool_name: str) -> None:
    """Expose the three native request operations through FastMCP."""
    assert tool_name in mcp._tool_manager._tools  # noqa: SLF001


def test_resolve_request_tool_is_not_registered() -> None:
    """Keep request resolution outside the agent-facing MCP surface."""
    assert "resolve_request" not in mcp._tool_manager._tools  # noqa: SLF001


def test_native_request_tool_signatures() -> None:
    """Require native revision and immutable request identity fields."""
    create = inspect.signature(create_request).parameters
    required = {
        "ctx",
        "request_id",
        "created_at",
        "change_id",
        "delivery_digest",
        "kind",
        "title",
        "summary",
        "agent",
    }
    assert required <= create.keys()
    assert all(create[name].default is inspect.Parameter.empty for name in required)
    assert {"target_node_id", "job_ids", "options", "body"} <= create.keys()

    listed = inspect.signature(list_requests).parameters
    assert {"ctx", "change_id", "delivery_digest", "status"} <= listed.keys()
    assert listed["status"].default == "pending"

    shown = inspect.signature(show_request).parameters
    assert {"ctx", "change_id", "delivery_digest", "request_id"} == shown.keys()


@pytest.mark.asyncio
async def test_create_request_replays_exact_native_identity_without_mutation(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Persist one linked request and replay the same immutable payload exactly."""
    stored_job = _materialize_job(app_ctx.workspace.work_root, revision)
    target_node_id = revision.graph.nodes[0].id

    created = await _create_action(
        mcp_ctx,
        revision,
        request_id="request-replay",
        target_node_id=target_node_id,
        job_ids=[stored_job.job.job_id],
    )
    snapshot = _storage_snapshot(app_ctx.workspace.work_root)
    replayed = await _create_action(
        mcp_ctx,
        revision,
        request_id="request-replay",
        target_node_id=target_node_id,
        job_ids=[stored_job.job.job_id],
    )

    assert replayed == created
    assert _storage_snapshot(app_ctx.workspace.work_root) == snapshot
    assert set(snapshot) == {"jobs/1.yaml", "requests/pending/request-replay.yaml"}
    assert JobStore(app_ctx.workspace.work_root).read(1).job.pending_request_ids == ("request-replay",)


@pytest.mark.asyncio
async def test_create_decision_request_preserves_options(
    mcp_ctx: MagicMock,
    revision: ChangeRevision,
) -> None:
    """Preserve structured decision tradeoffs through the public adapter."""
    options = [
        {
            "option_id": "local-fix",
            "label": "Apply local fix",
            "pros": ("Contained",),
            "cons": ("Narrow",),
            "risks": (),
            "recommended": True,
            "confidence": 0.9,
            "rationale": "The issue is implementation-local.",
        },
        {
            "option_id": "redesign",
            "label": "Re-enter design",
            "pros": ("Revisits authority",),
            "cons": ("Interrupts delivery",),
            "risks": ("Broader delay",),
            "recommended": False,
            "confidence": 0.7,
            "rationale": "Use when authority must change.",
        },
    ]

    result = await create_request(
        mcp_ctx,
        request_id="request-decision",
        created_at=CREATED_AT,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        kind="decision",
        title="Choose implementation",
        summary="One runtime choice is required.",
        agent="shaper",
        options=options,
    )

    request = cast("dict[str, object]", result["request"])
    assert request["kind"] == "decision"
    assert request["options"] == tuple(options)


@pytest.mark.asyncio
async def test_create_request_reference_errors_leave_storage_unchanged(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Map change, digest, node, and missing-job failures without mutation."""
    target_node_id = revision.graph.nodes[0].id
    cases = (
        ({"request_id": "request-change", "change_id": "missing-change"}, "ERR_CHANGE_NOT_FOUND"),
        ({"request_id": "request-digest", "delivery_digest": "0" * 64}, "ERR_DIGEST_MISMATCH"),
        ({"request_id": "request-node", "target_node_id": "DN-999"}, "ERR_NATIVE_REQUEST_REFERENCE"),
        (
            {"request_id": "request-job", "target_node_id": target_node_id, "job_ids": [99999]},
            "ERR_NATIVE_REQUEST_REFERENCE",
        ),
    )

    for arguments, error_code in cases:
        before = _storage_snapshot(app_ctx.workspace.work_root)
        with pytest.raises(ToolError, match=error_code):
            await _create_action(mcp_ctx, revision, **arguments)  # type: ignore[arg-type]
        assert _storage_snapshot(app_ctx.workspace.work_root) == before


@pytest.mark.asyncio
async def test_create_request_rejects_jobs_outside_revision_or_target(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Reject revision- and target-mismatched jobs without changing storage."""
    first_node = revision.graph.nodes[0].id
    second_node = revision.graph.nodes[1].id
    _materialize_job(app_ctx.workspace.work_root, revision, job_id=2, change_id="other-change")
    _materialize_job(app_ctx.workspace.work_root, revision, job_id=3, target_node_id=second_node)

    for request_id, job_id in (("request-revision-job", 2), ("request-target-job", 3)):
        before = _storage_snapshot(app_ctx.workspace.work_root)
        with pytest.raises(ToolError, match="ERR_NATIVE_REQUEST_REFERENCE"):
            await _create_action(
                mcp_ctx,
                revision,
                request_id=request_id,
                target_node_id=first_node,
                job_ids=[job_id],
            )
        assert _storage_snapshot(app_ctx.workspace.work_root) == before


@pytest.mark.asyncio
async def test_create_request_changed_replay_conflicts_without_mutation(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Treat changed immutable content under one request identity as a conflict."""
    await _create_action(mcp_ctx, revision, request_id="request-conflict")
    before = _storage_snapshot(app_ctx.workspace.work_root)

    with pytest.raises(ToolError, match="ERR_NATIVE_REQUEST_CONFLICT"):
        await _create_action(
            mcp_ctx,
            revision,
            request_id="request-conflict",
            summary="Changed immutable summary.",
        )

    assert _storage_snapshot(app_ctx.workspace.work_root) == before


@pytest.mark.asyncio
async def test_list_requests_filters_status_in_request_identity_order(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Filter pending and resolved summaries in ascending request identity order."""
    for request_id in ("request-zulu", "request-alpha", "request-mike"):
        await _create_action(mcp_ctx, revision, request_id=request_id)
    NativeRequestRuntime(revision, app_ctx.workspace.work_root).resolve_request(
        RequestResolution(
            request_id="request-alpha",
            disposition="local",
            resolved_at="2026-07-25T00:01:00Z",
            resolved_by="user",
            response="Evidence supplied.",
            rationale="The request is complete.",
        )
    )

    pending = await list_requests(
        mcp_ctx,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        status="pending",
    )
    resolved = await list_requests(
        mcp_ctx,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        status="resolved",
    )

    assert [item["request"]["request_id"] for item in pending] == ["request-mike", "request-zulu"]
    assert [item["request"]["request_id"] for item in resolved] == ["request-alpha"]
    assert all("body" not in item["request"] for item in (*pending, *resolved))


@pytest.mark.asyncio
async def test_list_requests_rejects_unsupported_status(
    mcp_ctx: MagicMock,
    revision: ChangeRevision,
) -> None:
    """Return a stable parameter error for unsupported request status."""
    with pytest.raises(ToolError, match="status must be 'pending', 'resolved', or 'all'"):
        await list_requests(
            mcp_ctx,
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            status="invalid",
        )


@pytest.mark.asyncio
async def test_show_request_returns_full_record_and_missing_is_read_only(
    mcp_ctx: MagicMock,
    app_ctx: AppContext,
    revision: ChangeRevision,
) -> None:
    """Return full request detail and a stable read-only not-found error."""
    created = await _create_action(mcp_ctx, revision, request_id="request-show")
    shown = await show_request(
        mcp_ctx,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        request_id="request-show",
    )
    assert shown == {"request": created["request"], "resolution": created["resolution"]}
    assert shown["request"]["body"] == "release-id=42"
    assert shown["resolution"] is None

    before = _storage_snapshot(app_ctx.workspace.work_root)
    with pytest.raises(ToolError, match="ERR_NATIVE_REQUEST_NOT_FOUND"):
        await show_request(
            mcp_ctx,
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            request_id="request-missing",
        )
    assert _storage_snapshot(app_ctx.workspace.work_root) == before
