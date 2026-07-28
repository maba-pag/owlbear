"""Test MCP native query tool adapters (list_jobs, show_job, list_attempts, list_activity)."""

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path

import pytest

from owlbear_kanban import DispatchRuntime, NativeRuntime, load_change
from owlbear_kanban.jobs import JobGeneration, JobStore, PlanJob
from owlbear_mcp_kanban import server


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


def _native_ctx(tmp_path: Path) -> object:
    """Build a minimal AppContext for native tool tests."""
    from owlbear_mcp_kanban.server import AppContext
    from owlbear_kanban import NativeWorkspace

    kanban_dir = tmp_path / "kanban"
    kanban_dir.mkdir(exist_ok=True)
    app_ctx = AppContext(workspace=NativeWorkspace(kanban_dir, timedelta(hours=1)))

    class _Ctx:
        class _RequestContext:
            def __init__(self):
                self.lifespan_context = app_ctx

        def __init__(self):
            self.request_context = self._RequestContext()

    return _Ctx()


class TestNativeQueryTools:
    """Test the 4 native query MCP tools: list_jobs, show_job, list_attempts, list_activity."""

    @pytest.mark.asyncio
    async def test_list_jobs_returns_paged_projection(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-1: list_jobs returns bounded RuntimeJobProjection pages with stable cursors."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()
        jobs = JobStore(work_root)
        jobs.materialize(
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
                        created_at="2026-07-24T00:00:00Z",
                        updated_at="2026-07-24T00:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[0].id,
                        receipt_id="bootstrap-001",
                    ),
                    PlanJob(
                        job_id=2,
                        kind="plan",
                        priority=8,
                        created_at="2026-07-24T01:00:00Z",
                        updated_at="2026-07-24T01:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[1].id
                        if len(revision.graph.nodes) > 1
                        else revision.graph.nodes[0].id,
                        receipt_id="bootstrap-001",
                    ),
                ),
            )
        )

        # Archive job 2 to test active+archived projection
        stored = jobs.read(2)
        jobs.archive(2, stored.token)

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        result = await server.list_jobs(
            ctx,
            change_id=revision.change_id,
            candidate_revision="a" * 40,
            limit=10,
        )

        # Verify both active and archived jobs returned
        assert len(result.items) == 2
        assert {item.job_id for item in result.items} == {1, 2}

        # Verify all required projection fields present
        job_proj = result.items[0]
        assert hasattr(job_proj, "job_id")
        assert hasattr(job_proj, "kind")
        assert hasattr(job_proj, "priority")
        assert hasattr(job_proj, "dependency_ready")
        assert hasattr(job_proj, "claim_id")
        assert hasattr(job_proj, "requests")
        assert hasattr(job_proj, "attempt")
        assert hasattr(job_proj, "finding")
        assert hasattr(job_proj, "receipt")
        assert hasattr(job_proj, "validity")
        assert hasattr(job_proj, "disposition")

        # Test cursor pagination
        page1 = await server.list_jobs(ctx, change_id=revision.change_id, candidate_revision="a" * 40, limit=1)
        assert len(page1.items) == 1
        assert page1.next_cursor is not None

        page2 = await server.list_jobs(
            ctx, change_id=revision.change_id, candidate_revision="a" * 40, cursor=page1.next_cursor, limit=1
        )
        assert len(page2.items) == 1
        assert page2.items[0].job_id != page1.items[0].job_id

        # Test stale cursor error
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="ERR_CURSOR_STALE"):
            await server.list_jobs(
                ctx, change_id=revision.change_id, candidate_revision="a" * 40, cursor="stale-999", limit=1
            )

    @pytest.mark.asyncio
    async def test_show_job_composes_immutable_record_and_projection(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: show_job composes JobRecord and JobProjection fields."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()
        jobs = JobStore(work_root)
        jobs.materialize(
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
                        created_at="2026-07-24T00:00:00Z",
                        updated_at="2026-07-24T00:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[0].id,
                        receipt_id="bootstrap-001",
                    ),
                ),
            )
        )

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        result = await server.show_job(
            ctx,
            change_id=revision.change_id,
            job_id=1,
        )

        # Verify composition from JobRecord (immutable) and project_job (authority)
        assert "job" in result
        job = result["job"]
        assert job.job_id == 1
        assert job.kind == "plan"

        # Verify project_job authority fields
        assert "title" in result
        assert "outcome" in result
        assert "acceptance" in result
        assert "modules" in result
        assert "interfaces" in result
        assert "proof" in result

        # Verify these are actual values, not None
        assert isinstance(result["acceptance"], (list, tuple))
        assert isinstance(result["modules"], (list, tuple))

        # Test missing job error
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="ERR_JOB_NOT_FOUND"):
            await server.show_job(ctx, change_id=revision.change_id, job_id=999)

    @pytest.mark.asyncio
    async def test_list_attempts_returns_paged_events(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-3: list_attempts returns bounded pages ordered by attempt ID and sequence."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()
        jobs = JobStore(work_root)
        jobs.materialize(
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
                        created_at="2026-07-24T00:00:00Z",
                        updated_at="2026-07-24T00:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[0].id,
                        receipt_id="bootstrap-001",
                    ),
                ),
            )
        )

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        result = await server.list_attempts(
            ctx,
            change_id=revision.change_id,
            limit=10,
        )

        # Verify list_attempts returns page structure
        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert isinstance(result.items, tuple)

        # If there are events, verify ordering and preserved fields
        if len(result.items) > 0:
            for event in result.items:
                assert hasattr(event, "job_id")
                assert hasattr(event, "timestamp")
                assert hasattr(event, "kind")
                assert hasattr(event, "attempt_id")
                assert hasattr(event, "sequence")
            # Verify ordering by (attempt_id, sequence)
            for i in range(len(result.items) - 1):
                curr = result.items[i]
                next_event = result.items[i + 1]
                assert (curr.attempt_id, curr.sequence) <= (next_event.attempt_id, next_event.sequence)

        # Test stale cursor error
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="ERR_CURSOR_STALE"):
            await server.list_attempts(ctx, change_id=revision.change_id, cursor="stale-999", limit=1)

    @pytest.mark.asyncio
    async def test_list_activity_returns_chronological_history(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-4: list_activity returns bounded chronological RuntimeHistoryEntry pages."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()
        jobs = JobStore(work_root)
        jobs.materialize(
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
                        created_at="2026-07-24T00:00:00Z",
                        updated_at="2026-07-24T00:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[0].id,
                        receipt_id="bootstrap-001",
                    ),
                ),
            )
        )

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        result = await server.list_activity(
            ctx,
            change_id=revision.change_id,
            limit=10,
        )

        # Verify list_activity returns page structure
        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert isinstance(result.items, tuple)

        # If there are history entries, verify chronological ordering
        if len(result.items) > 1:
            for i in range(len(result.items) - 1):
                curr = result.items[i]
                next_entry = result.items[i + 1]
                assert (curr.timestamp, curr.identity) <= (next_entry.timestamp, next_entry.identity), (
                    f"Not chronologically ordered: {curr.timestamp}/{curr.identity} vs {next_entry.timestamp}/{next_entry.identity}"
                )

        # Verify kind-specific fields exist for each kind
        for entry in result.items:
            assert entry.kind in ("attempt", "finding", "receipt", "request")
            assert hasattr(entry, "timestamp")
            assert hasattr(entry, "identity")
            if entry.kind == "attempt":
                assert entry.attempt is not None
            elif entry.kind == "finding":
                assert entry.finding is not None
            elif entry.kind == "receipt":
                assert entry.receipt is not None
            elif entry.kind == "request":
                assert entry.request is not None

        # Test cursor pagination if there are enough items
        if len(result.items) > 1:
            page1 = await server.list_activity(ctx, change_id=revision.change_id, limit=1)
            assert len(page1.items) == 1
            if page1.next_cursor:
                page2 = await server.list_activity(ctx, change_id=revision.change_id, cursor=page1.next_cursor, limit=1)
                assert len(page2.items) >= 1

        # Test stale cursor error
        from mcp.server.fastmcp.exceptions import ToolError

        with pytest.raises(ToolError, match="ERR_CURSOR_STALE"):
            await server.list_activity(ctx, change_id=revision.change_id, cursor="stale-999", limit=1)

    @pytest.mark.asyncio
    async def test_show_receipt_returns_immutable_receipt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-1: show_receipt returns immutable ReceiptRecord for existing receipt."""
        import yaml

        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        # Create a test receipt
        receipts_dir = revision.source_dir / "receipts"
        receipts_dir.mkdir(exist_ok=True)
        test_receipt_id = "test-receipt-001"
        receipt_data = {
            "schema_version": 1,
            "kind": "admission",
            "receipt_id": test_receipt_id,
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "issued_at": "2026-07-24T00:00:00Z",
            "payload": {"test": "data"},
        }
        (receipts_dir / f"{test_receipt_id}.yaml").write_text(yaml.dump(receipt_data))

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Test successful receipt read
        result = await server.show_receipt(
            ctx,
            change_id=revision.change_id,
            receipt_id=test_receipt_id,
        )

        assert result.receipt_id == test_receipt_id
        assert result.kind == "admission"
        assert result.change_id == revision.change_id

    @pytest.mark.asyncio
    async def test_show_receipt_missing_receipt_distinct_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-1: show_receipt returns distinct stable error for missing receipt."""
        from mcp.server.fastmcp.exceptions import ToolError

        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Test missing receipt error
        with pytest.raises(ToolError, match="ERR_RECEIPT_MISSING"):
            await server.show_receipt(
                ctx,
                change_id=revision.change_id,
                receipt_id="nonexistent-receipt",
            )

    @pytest.mark.asyncio
    async def test_show_receipt_malformed_receipt_distinct_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-1: show_receipt returns distinct stable error for malformed receipt."""
        from mcp.server.fastmcp.exceptions import ToolError

        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        # Create a malformed receipt
        receipts_dir = revision.source_dir / "receipts"
        receipts_dir.mkdir(exist_ok=True)
        test_receipt_id = "malformed-receipt-001"
        (receipts_dir / f"{test_receipt_id}.yaml").write_text("invalid: yaml: content: [")

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Test malformed receipt error (distinct from missing)
        with pytest.raises(ToolError) as exc_info:
            _result = await server.show_receipt(
                ctx,
                change_id=revision.change_id,
                receipt_id=test_receipt_id,
            )

        # Verify distinct error code (not ERR_RECEIPT_MISSING)
        error_str = str(exc_info.value)
        assert "ERR_RECEIPT_YAML_PARSE" in error_str or "ERR_RECEIPT_SCHEMA_INVALID" in error_str
        assert "ERR_RECEIPT_MISSING" not in error_str
        # Verify no path leak
        assert "receipts/" not in error_str
        error_detail = error_str.rsplit(":", maxsplit=1)[-1]
        assert "/" not in error_detail

    @pytest.mark.asyncio
    async def test_work_health_returns_bounded_findings(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: work_health returns bounded sorted WorkHealthResult with findings and paths."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        result = await server.work_health(
            ctx,
            change_id=revision.change_id,
            limit=10,
        )

        # Verify WorkHealthResult structure
        assert "findings" in result
        assert "checked_paths" in result
        assert "next_cursor" in result or result.get("next_cursor") is None
        assert isinstance(result["findings"], (list, tuple))
        assert isinstance(result["checked_paths"], (list, tuple))

        # Verify bounded by limit
        assert len(result["checked_paths"]) <= 10

        # Verify findings sorted by (path, code, target)
        if len(result["findings"]) > 1:
            for i in range(len(result["findings"]) - 1):
                curr = result["findings"][i]
                next_f = result["findings"][i + 1]
                curr_key = (curr["path"], curr["code"], curr.get("target") or "")
                next_key = (next_f["path"], next_f["code"], next_f.get("target") or "")
                assert curr_key <= next_key, f"Findings not sorted: {curr_key} > {next_key}"

        # Verify findings structure (if any)
        for finding in result["findings"]:
            assert "code" in finding
            assert "detail" in finding
            assert "path" in finding

    @pytest.mark.asyncio
    async def test_work_health_cursor_pagination(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: work_health supports stable cursor pagination."""
        from mcp.server.fastmcp.exceptions import ToolError

        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Get first page
        page1 = await server.work_health(
            ctx,
            change_id=revision.change_id,
            limit=1,
        )

        # If there's a cursor, test pagination
        if page1.get("next_cursor"):
            page2 = await server.work_health(
                ctx,
                change_id=revision.change_id,
                cursor=page1["next_cursor"],
                limit=1,
            )
            assert "findings" in page2

        # Test stale cursor error
        with pytest.raises(ToolError, match="ERR_CURSOR_STALE"):
            await server.work_health(
                ctx,
                change_id=revision.change_id,
                cursor="stale-cursor-999",
                limit=1,
            )

    @pytest.mark.asyncio
    async def test_work_health_healthy_workspace_empty_findings(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: work_health returns empty findings for healthy valid workspace."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        # Remove all existing receipts to start clean
        receipts_dir = changes_dir / "replace-delivery-pipeline" / "receipts"
        if receipts_dir.exists():
            shutil.rmtree(receipts_dir)
        receipts_dir.mkdir()
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        # Create healthy workspace with valid job using JobStore.materialize
        jobs = JobStore(work_root)
        jobs.materialize(
            JobGeneration(
                schema_version=1,
                change_id=revision.change_id,
                delivery_digest=revision.delivery_digest,
                receipt_id="test-receipt-001",
                jobs=(
                    PlanJob(
                        job_id=1,
                        kind="plan",
                        priority=7,
                        created_at="2026-07-24T00:00:00Z",
                        updated_at="2026-07-24T00:00:00Z",
                        change_id=revision.change_id,
                        delivery_digest=revision.delivery_digest,
                        target_node_id=revision.graph.nodes[0].id,
                        receipt_id="test-receipt-001",
                    ),
                ),
            )
        )

        # Create corresponding receipt
        import yaml

        receipt_data = {
            "schema_version": 1,
            "kind": "admission",
            "receipt_id": "test-receipt-001",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "issued_at": "2026-07-24T00:00:00Z",
            "payload": {},
        }
        (receipts_dir / "test-receipt-001.yaml").write_text(yaml.dump(receipt_data))

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Capture mtime before work_health call
        job_path = work_root / "jobs" / "1.yaml"
        receipt_path = receipts_dir / "test-receipt-001.yaml"
        job_mtime_before = job_path.stat().st_mtime_ns
        receipt_mtime_before = receipt_path.stat().st_mtime_ns

        result = await server.work_health(
            ctx,
            change_id=revision.change_id,
            limit=100,
        )

        # Verify empty findings for healthy workspace
        assert len(result["findings"]) == 0
        assert "jobs/1.yaml" in result["checked_paths"]
        assert "receipts/test-receipt-001.yaml" in result["checked_paths"]

        # Verify paths unchanged (mtime verification)
        job_mtime_after = job_path.stat().st_mtime_ns
        receipt_mtime_after = receipt_path.stat().st_mtime_ns
        assert job_mtime_before == job_mtime_after
        assert receipt_mtime_before == receipt_mtime_after

    @pytest.mark.asyncio
    async def test_work_health_corrupt_job_returns_err_work_job_invalid(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: work_health returns ERR_WORK_JOB_INVALID for malformed job storage."""
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        # Remove all existing receipts to start clean
        receipts_dir = changes_dir / "replace-delivery-pipeline" / "receipts"
        if receipts_dir.exists():
            shutil.rmtree(receipts_dir)
        receipts_dir.mkdir()
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        # Create corrupt job with malformed YAML
        jobs_dir = work_root / "jobs"
        jobs_dir.mkdir()
        (jobs_dir / "999.yaml").write_text("[unclosed")

        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Capture mtime before work_health call
        corrupt_job_path = jobs_dir / "999.yaml"
        mtime_before = corrupt_job_path.stat().st_mtime_ns

        result = await server.work_health(
            ctx,
            change_id=revision.change_id,
            limit=100,
        )

        # Verify ERR_WORK_JOB_INVALID finding with controlled relative path
        findings = result["findings"]
        assert len(findings) > 0
        corrupt_finding = next((f for f in findings if f["code"] == "ERR_WORK_JOB_INVALID"), None)
        assert corrupt_finding is not None
        assert corrupt_finding["path"] == "jobs/999.yaml"
        assert corrupt_finding["detail"] == "job record is malformed or unsafe"

        # Verify path unchanged (mtime verification)
        mtime_after = corrupt_job_path.stat().st_mtime_ns
        assert mtime_before == mtime_after

    @pytest.mark.asyncio
    async def test_work_health_orphan_proof_checkout_returns_err(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-2: work_health returns ERR_WORK_PROOF_CHECKOUT_ORPHAN for orphan checkout."""
        from owlbear_kanban import ProofCheckoutManager

        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        # Remove all existing receipts to start clean
        receipts_dir = changes_dir / "replace-delivery-pipeline" / "receipts"
        if receipts_dir.exists():
            shutil.rmtree(receipts_dir)
        receipts_dir.mkdir()
        (changes_dir / "replace-delivery-pipeline" / "plans" / "DN-001.yaml").unlink()
        loaded = load_change(changes_dir, "replace-delivery-pipeline")
        assert loaded.revision is not None
        revision = loaded.revision

        work_root = tmp_path / "kanban"
        work_root.mkdir()

        # Create orphan proof checkout directory through real checkout convention
        proof_root = work_root / "proof-checkouts"
        proof_root.mkdir(mode=0o700)
        orphan_dir = proof_root / "123"
        orphan_dir.mkdir(mode=0o700)

        # Create proof checkout manager and runtime with it
        proof_checkouts = ProofCheckoutManager(Path.cwd(), proof_root, changes_dir)
        runtime = DispatchRuntime(
            NativeRuntime(revision, work_root, _History(), timedelta(minutes=1), proof_checkouts=proof_checkouts),
            work_root,
        )
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)

        # Capture mtime before work_health call
        mtime_before = orphan_dir.stat().st_mtime_ns

        result = await server.work_health(
            ctx,
            change_id=revision.change_id,
            limit=100,
        )

        # Verify ERR_WORK_PROOF_CHECKOUT_ORPHAN finding with canonical target
        findings = result["findings"]
        assert len(findings) > 0
        orphan_finding = next((f for f in findings if f["code"] == "ERR_WORK_PROOF_CHECKOUT_ORPHAN"), None)
        assert orphan_finding is not None
        assert orphan_finding["path"] == "proof-checkouts/123"
        assert orphan_finding["target"] == "123"
        assert orphan_finding["detail"] == "proof checkout requires cleanup"

        # Verify path unchanged (mtime verification)
        mtime_after = orphan_dir.stat().st_mtime_ns
        assert mtime_before == mtime_after
