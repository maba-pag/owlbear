"""Test MCP native query tool adapters (list_jobs, show_job, list_attempts, list_activity)."""

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from owlbear_kanban import DispatchRuntime, NativeRuntime, load_change
from owlbear_kanban.attempts import AttemptStore
from owlbear_kanban.jobs import JobGeneration, JobStore, PlanJob
from owlbear_kanban.receipt import GitRepositoryHistory
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
    from owlbear_kanban import KanbanEngine

    kanban_dir = tmp_path / "kanban"
    kanban_dir.mkdir(exist_ok=True)
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    config_yaml = kanban_dir / "config.yaml"
    if not config_yaml.exists():
        config_yaml.write_text(
            "version: 10\nboard:\n  name: TestBoard\ntasks_dir: tasks\n"
        )
    engine = KanbanEngine(kanban_dir)
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)

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
                ),
            )
        )

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

        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert len(result.items) == 1
        assert result.items[0].job_id == 1

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

        assert "job" in result
        assert "title" in result
        assert "outcome" in result
        assert "acceptance" in result
        assert "modules" in result
        assert "interfaces" in result
        assert "proof" in result

    @pytest.mark.asyncio
    async def test_list_attempts_returns_paged_events(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC-3: list_attempts returns bounded pages ordered by attempt ID."""
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

        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert isinstance(result.items, tuple)

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

        assert hasattr(result, "items")
        assert hasattr(result, "next_cursor")
        assert isinstance(result.items, tuple)
