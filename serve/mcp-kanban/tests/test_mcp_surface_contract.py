"""Prove dev-code MCP runtime before main sync (#1347).

(a) Why editor-runtime MCP success via '../owlbear' does not prove dev-source readiness:
    The dev workspace MCP config launches MCP servers with ``uv --project ../owlbear``,
    pointing at the sibling *consumer* checkout. That path is stale relative to dev and
    does not exercise current dev source. A successful MCP tool call in the editor only
    proves the consumer overlay works — not that the dev code is sync-ready.

(b) Seed-placeholder MCP config and dev-code validation are separate concerns:
    ``seed/.vscode/mcp.json`` ships a placeholder config for new consumer checkouts.
    It has nothing to do with validating dev source. These tests run against dev source
    directly and must never parse or depend on any ``.vscode/mcp.json`` file at runtime.

(c) Updating EXPECTED_TOOLS is required when the deployment contract changes:
    ``EXPECTED_TOOLS`` in this file is the authoritative deployment-contract snapshot.
    When a tool is intentionally added or removed, update EXPECTED_TOOLS in the same
    commit that modifies the tool registration in server.py. A drift between the two
    constitutes a broken contract and will fail this test.

AC1 (td:2): app_lifespan starts against isolated temp board fixture; yields AppContext.
AC2 (td:1): owlbear_mcp_kanban.__file__ resolves under the repo working tree.
AC3 (td:1): Live tool registry (post-lifespan, no exclusions) == EXPECTED_TOOLS exactly.
AC4 (td:1): Generic task and old-lifecycle registrations are absent.
AC5-AC7: td:0 — no executable tests.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import owlbear_mcp_kanban
from owlbear_mcp_kanban import server
from owlbear_kanban import (
    AttemptStore,
    AdmissionPublicationError,
    DispatchRuntime,
    JobGeneration,
    JobRecord,
    JobStore,
    NativeRuntime,
    PlanJob,
    load_change,
)
from owlbear_kanban.change import ChangeRevision
from owlbear_kanban.runtime_transaction import RuntimeTransaction
from owlbear_mcp_kanban.server import AppContext, app_lifespan, mcp

# ---------------------------------------------------------------------------
# Deployment-contract snapshot
# UPDATE THIS SET (and server.py) together when tools are added or removed.
# ---------------------------------------------------------------------------

EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "admit_change",
        "change_health",
        "create_request",
        "finish_accept",
        "finish_audit",
        "finish_build",
        "finish_plan",
        "list_activity",
        "list_attempts",
        "list_changes",
        "list_jobs",
        "list_requests",
        "pick_jobs",
        "recover_expired_claims",
        "release_job",
        "show_change",
        "show_job",
        "show_receipt",
        "show_request",
        "start_job",
        "validate_change",
        "work_health",
    }
)

REMOVED_TASK_TOOLS: frozenset[str] = frozenset(
    {"list_tasks", "show_task", "create_task", "edit_task", "move_task", "pick_tasks", "start_work", "end_work"}
)

READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "change_health",
        "list_activity",
        "list_attempts",
        "list_changes",
        "list_jobs",
        "list_requests",
        "pick_jobs",
        "show_change",
        "show_job",
        "show_receipt",
        "show_request",
        "validate_change",
        "work_health",
    }
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal valid kanban board under *base_dir* and return its path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _server_mock() -> MagicMock:
    """Minimal FastMCP mock — only ``remove_tool`` is called by _apply_tool_exclusions."""
    server = MagicMock()
    server.remove_tool.side_effect = Exception("no tool")
    return server


def _find_repo_root() -> Path:
    """Walk up from this test file until a pyproject.toml sentinel is found."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise RuntimeError(
        f"Could not locate repo root from {Path(__file__).resolve()!r}. "
        "Expected a pyproject.toml file in an ancestor directory."
    )


# ---------------------------------------------------------------------------
# AC1 — lifespan startup against isolated temp board
# ---------------------------------------------------------------------------


class TestFromAC_ModuleSourceOrigin:
    """AC2: owlbear_mcp_kanban.__file__ resolves under the dev repo working tree."""

    def test_module_file_resolves_under_repo_working_tree(self) -> None:
        """AC2: Imported module must live under the dev repo tree, not a consumer checkout.

        Uses this test file's own __file__ parent chain to derive the repo root —
        no hardcoded paths. Fails when the module was loaded from a sibling consumer
        checkout (``../owlbear``) or a non-dev installation.
        """
        repo_root = _find_repo_root()
        module_path = Path(owlbear_mcp_kanban.__file__).resolve()
        assert module_path.is_relative_to(repo_root), (
            f"owlbear_mcp_kanban resolves to {module_path!r}, which is NOT under "
            f"the repo root {repo_root!r}. "
            "This indicates the module was loaded from a sibling consumer checkout "
            "('../owlbear') or a non-dev installation instead of the dev source tree."
        )


# ---------------------------------------------------------------------------
# AC3 — tool registry contract
# ---------------------------------------------------------------------------


class TestFromAC_ToolRegistryContract:
    """AC3: Live registry (post-lifespan, no exclusions) matches EXPECTED_TOOLS exactly."""

    @pytest.mark.asyncio
    async def test_live_registry_contains_exactly_twenty_two_tools(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3: After lifespan with KANBAN_TOOLS_EXCLUDE unset, tool set == EXPECTED_TOOLS.

        Runs app_lifespan (not just module import) because _apply_tool_exclusions
        executes at lifespan time. With no exclusions, the full deployment contract
        must be intact. Introspects mcp._tool_manager._tools — the established pattern
        in test_tool_annotations_494.py and related MCP contract tests.
        """
        board = _make_board(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))
        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)

        # _server_mock() is used to avoid permanently mutating the mcp singleton;
        # with no exclusions _apply_tool_exclusions is a no-op regardless.
        async with app_lifespan(_server_mock()):
            registered = frozenset(
                t.name
                for t in mcp._tool_manager._tools.values()  # noqa: SLF001
            )

        assert registered == EXPECTED_TOOLS, (
            f"Tool registry mismatch after lifespan. "
            f"Missing from registry: {EXPECTED_TOOLS - registered!r}. "
            f"Unexpected in registry: {registered - EXPECTED_TOOLS!r}. "
            "Update EXPECTED_TOOLS in this file when tools are intentionally "
            "added or removed from server.py."
        )

    def test_native_annotations_match_operation_semantics(self) -> None:
        """Declare every native operation idempotent, non-destructive, and read-accurate."""
        tools = {tool.name: tool for tool in mcp._tool_manager._tools.values()}  # noqa: SLF001
        assert tools.keys() == EXPECTED_TOOLS
        for name, tool in tools.items():
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is (name in READ_ONLY_TOOLS)
            assert tool.annotations.idempotentHint is True
            assert tool.annotations.destructiveHint is False


# ---------------------------------------------------------------------------
# AC4 — legacy registration absence
# ---------------------------------------------------------------------------


class TestFromAC_LegacyRegistrationAbsence:
    """AC4: generic task and old lifecycle tools are not registered."""

    def test_generic_task_and_old_lifecycle_tools_are_absent(self) -> None:
        """Keep only native change and job identities on the public MCP surface."""
        registered = frozenset(mcp._tool_manager._tools)  # noqa: SLF001
        assert registered.isdisjoint(REMOVED_TASK_TOOLS | {"finish_shape"})
        assert all(not hasattr(server, name) for name in REMOVED_TASK_TOOLS | {"finish_shape"})
        assert server.__all__ is not None
        assert set(server.__all__).isdisjoint(REMOVED_TASK_TOOLS | {"finish_shape"})


def _proof011_context(
    tmp_path: Path,
) -> tuple[ChangeRevision, Path, MagicMock, dict[str, object], str]:
    changes_dir = tmp_path / "changes"
    authority_dir = changes_dir / "replace-delivery-pipeline"
    shutil.copytree(Path(".owlbear/changes/replace-delivery-pipeline"), authority_dir)
    shutil.rmtree(authority_dir / "receipts")
    shutil.rmtree(authority_dir / "jobs")
    (authority_dir / "plans" / "DN-001.yaml").unlink()
    board = _make_board(tmp_path)
    loaded = load_change(changes_dir, "replace-delivery-pipeline")
    assert loaded.revision is not None
    revision = loaded.revision
    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(revision.graph, section)
    }
    evidence = {
        "digest": revision.delivery_digest,
        "challenge": challenge,
        "baseline": {"commands": ["pytest"], "digest": revision.delivery_digest},
        "approval": {"approved": True, "digest": revision.delivery_digest},
        "limits": list(revision.graph.admission.limits),
    }
    app_ctx = AppContext(engine=server.KanbanEngine(board), kanban_dir=board)
    app_ctx.dispatch_runtimes[revision.change_id] = DispatchRuntime(
        NativeRuntime(revision, board, _History(), timedelta(minutes=1)), board
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return revision, board, ctx, evidence, Path(revision.graph.admission.receipt).stem


async def _proof011_request(
    ctx: MagicMock,
    revision: ChangeRevision,
    requested_job: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, object]]:
    request = await server.create_request(
        ctx,
        request_id="request-proof-011",
        created_at="2026-07-25T00:00:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        kind="action",
        title="Provide final-node evidence",
        summary="The final admitted node needs external evidence.",
        agent="builder",
        target_node_id=requested_job["target_node_id"],
        job_ids=[requested_job["job_id"]],
        body="evidence-id=proof-011",
    )
    requests = await server.list_requests(ctx, revision.change_id, revision.delivery_digest)
    shown = await server.show_request(ctx, revision.change_id, revision.delivery_digest, "request-proof-011")
    return request, requests, shown


def _proof011_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".storage.lock"
    }


class TestProof011NativeControlPlane:
    """The assembled public control plane carries admission into native work."""

    @pytest.mark.asyncio
    async def test_admission_feeds_native_job_queries(self, tmp_path: Path) -> None:
        """Invoke the complete graph-aware native control plane through public tools."""
        revision, board, ctx, evidence, receipt_id = _proof011_context(tmp_path)

        changes = await server.list_changes(ctx)
        shown = await server.show_change(ctx, change_id=revision.change_id)
        assessment = await server.validate_change(ctx, change_id=revision.change_id, evidence=evidence)
        admitted = await server.admit_change(ctx, change_id=revision.change_id, evidence=evidence)
        jobs = await server.list_jobs(
            ctx,
            change_id=revision.change_id,
            candidate_revision="a" * 40,
        )
        admitted_jobs = admitted["generation"]["jobs"]
        requested_job = admitted_jobs[-1]
        request, requests, shown_request = await _proof011_request(ctx, revision, requested_job)
        waves = await server.pick_jobs(
            ctx,
            change_id=revision.change_id,
            candidate_revision="a" * 40,
            wave_size=5,
        )
        selected = waves.waves[0][0]
        started_at = "2026-07-25T00:01:00Z"
        finished_at = "2026-07-25T00:02:00Z"
        started = await server.start_job(ctx, **_start_kwargs(selected.job_id, 1, started_at))
        selected_job = JobStore(board).read(selected.job_id).job
        target = next(node for node in revision.graph.nodes if node.id == selected_job.target_node_id)
        proof = revision.resolve(target.proof)
        closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}
        next_job_id = max(job["job_id"] for job in admitted_jobs) + 1
        completed = await server.finish_plan(
            ctx,
            **_finish_kwargs(_start_kwargs(selected.job_id, 1, started_at)),
            finished_at=finished_at,
            receipt_id="plan-proof-011",
            code_revision="a" * 40,
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
            build_job_ids=(next_job_id, next_job_id + 1),
            accept_job_id=next_job_id + 2,
        )
        receipt = await server.show_receipt(
            ctx,
            change_id=revision.change_id,
            receipt_id="plan-proof-011",
        )
        attempts = await server.list_attempts(ctx, change_id=revision.change_id)
        activity = await server.list_activity(ctx, change_id=revision.change_id)
        change_integrity = await server.change_health(ctx, change_id=revision.change_id)
        work_integrity = await server.work_health(ctx, change_id=revision.change_id)

        assert changes == [{"change_id": revision.change_id, "state": "loaded", "digest": revision.delivery_digest}]
        assert shown["delivery_digest"] == revision.delivery_digest
        assert all(finding["severity"] != "error" for finding in assessment["findings"])
        assert admitted["receipt"]["receipt_id"] == receipt_id
        assert len(jobs.items) == len(revision.graph.nodes)
        assert {item.kind for item in jobs.items} == {"plan"}
        assert request["request"]["request_id"] == "request-proof-011"
        assert [item["request"]["request_id"] for item in requests] == ["request-proof-011"]
        assert shown_request == {key: value for key, value in request.items() if key != "guidance"}
        assert selected.agent_profile == "planner"
        assert selected.job_id != requested_job["job_id"]
        assert started.diagnostic is None
        assert completed.diagnostic is None
        assert completed.receipt == receipt
        assert {job.kind for job in completed.created_jobs} == {"build", "accept"}
        assert [event.kind for event in attempts.items] == ["started", "succeeded"]
        assert {entry.kind for entry in activity.items} >= {"attempt", "receipt"}
        assert change_integrity["findings"] == ()
        assert work_integrity["findings"] == ()


class TestNativeAdmissionErrors:
    """Public admission failures return stable codes without partial artifacts."""

    @pytest.mark.asyncio
    async def test_malformed_evidence_does_not_mutate_stores(self, tmp_path: Path) -> None:
        revision, _board, ctx, _evidence, _receipt_id = _proof011_context(tmp_path)
        before = _proof011_snapshot(tmp_path)

        with pytest.raises(ToolError, match="ERR_PARAM_VALIDATION"):
            await server.admit_change(ctx, change_id=revision.change_id, evidence={"digest": 1})

        assert _proof011_snapshot(tmp_path) == before

    @pytest.mark.asyncio
    async def test_changed_evidence_conflict_does_not_mutate_stores(self, tmp_path: Path) -> None:
        revision, _board, ctx, evidence, _receipt_id = _proof011_context(tmp_path)
        await server.admit_change(ctx, change_id=revision.change_id, evidence=evidence)
        before = _proof011_snapshot(tmp_path)
        changed_evidence = evidence | {"baseline": {"commands": ["pytest", "ruff"], "digest": revision.delivery_digest}}

        with pytest.raises(ToolError, match="ERR_ADMISSION_CONFLICT"):
            await server.admit_change(ctx, change_id=revision.change_id, evidence=changed_evidence)

        assert _proof011_snapshot(tmp_path) == before

    @pytest.mark.asyncio
    async def test_publication_failure_does_not_mutate_stores(self, tmp_path: Path, monkeypatch) -> None:
        revision, _board, ctx, evidence, _receipt_id = _proof011_context(tmp_path)
        before = _proof011_snapshot(tmp_path)

        def fail_publication(_transaction, _evidence) -> None:
            message = "injected publication failure"
            raise AdmissionPublicationError(RuntimeError(message))

        monkeypatch.setattr(server.AdmissionTransaction, "validate_and_admit", fail_publication)
        with pytest.raises(ToolError, match="ERR_ADMISSION_PUBLICATION"):
            await server.admit_change(ctx, change_id=revision.change_id, evidence=evidence)

        assert _proof011_snapshot(tmp_path) == before


class TestFinishAcceptSchema:
    """The accept bridge exposes its native reconciliation identity contract."""

    def test_finish_accept_requires_reconciliation_plan_job_ids(self) -> None:
        """The public MCP schema requires accept-specific reconciliation plan IDs."""
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "finish_accept"),  # noqa: SLF001
            None,
        )
        assert tool is not None, "finish_accept must be registered in the MCP tool registry"
        assert "reconciliation_plan_job_ids" in tool.parameters.get("required", [])


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


def _native_ctx(tmp_path: Path) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(engine=MagicMock(), kanban_dir=tmp_path / "kanban")
    return ctx


def _start_kwargs(job_id: int, attempt: int, timestamp: str) -> dict[str, object]:
    return {
        "change_id": "replace-delivery-pipeline",
        "job_id": job_id,
        "attempt_id": f"attempt-{attempt:03}",
        "claim_id": f"claim-{attempt:03}",
        "actor_id": "proof-runner",
        "process_id": "proof-process",
        "claimed_at": timestamp,
        "candidate_revision": "a" * 40,
    }


def _finish_kwargs(start: dict[str, object]) -> dict[str, object]:
    return {key: start[key] for key in ("change_id", "job_id", "attempt_id", "claim_id", "actor_id", "process_id")}


def _release_kwargs(start: dict[str, object]) -> dict[str, object]:
    return _finish_kwargs(start)


@dataclass(frozen=True)
class Success:
    receipt_id: str


@dataclass(frozen=True)
class RateLimited:
    pass


@dataclass(frozen=True)
class Crash:
    pass


@dataclass(frozen=True)
class NativeHalt:
    agent_profile: str


@dataclass
class LifecycleLedgerEntry:
    """Records one runner disposition and its matching native lifecycle operation."""

    agent_profile: str
    disposition: Success | RateLimited | Crash
    operation: str
    attempt_id: str
    selected_pick: int
    terminal_pick: int
    terminal_kind: str | None = None


def _lifecycle_operation(agent_profile: str, disposition: Success | RateLimited | Crash) -> str:
    """Return the sole lifecycle operation selected by a runner disposition."""

    match disposition:
        case Success():
            return {
                "planner": "finish_plan",
                "builder": "finish_build",
                "acceptor": "finish_accept",
                "auditor": "finish_audit",
            }[agent_profile]
        case RateLimited():
            return "release_job"
        case Crash():
            return "recover_expired_claims"


def _terminal_kind(disposition: Success | RateLimited | Crash) -> str:
    """Return the terminal attempt event expected from a runner disposition."""

    match disposition:
        case Success():
            return "succeeded"
        case RateLimited():
            return "released"
        case Crash():
            return "crashed"


def _assert_disposition_causality(
    ledger: list[LifecycleLedgerEntry],
    runner_dispositions: list[Success | RateLimited | Crash],
    observed_operations: dict[str, str],
) -> None:
    """Prove runner results, native operations, and attempt terminals remain causally bound."""

    assert len(ledger) == len(runner_dispositions)
    for entry, disposition in zip(ledger, runner_dispositions, strict=True):
        assert entry.disposition is disposition
        assert entry.operation == _lifecycle_operation(entry.agent_profile, disposition)
        assert observed_operations[entry.attempt_id] == entry.operation
        assert entry.terminal_kind == _terminal_kind(disposition)
        assert entry.selected_pick == entry.terminal_pick


class TestProof014NativeMcpScenario:
    """The bootstrap native loop dispatches profiles through the installed MCP bridge."""

    @pytest.mark.asyncio
    async def test_profiles_release_recovery_and_replanning_use_native_tools(  # noqa: C901, PLR0915
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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
        runtime = DispatchRuntime(NativeRuntime(revision, work_root, _History(), timedelta(minutes=1)), work_root)
        ctx = _native_ctx(tmp_path)
        monkeypatch.setattr(server, "_dispatch_runtime", lambda _app_ctx, _change_id: runtime)
        observed_tools = {
            "finish_plan": AsyncMock(wraps=server.finish_plan),
            "finish_build": AsyncMock(wraps=server.finish_build),
            "finish_accept": AsyncMock(wraps=server.finish_accept),
            "finish_audit": AsyncMock(wraps=server.finish_audit),
            "release_job": AsyncMock(wraps=server.release_job),
            "recover_expired_claims": AsyncMock(wraps=server.recover_expired_claims),
        }
        for operation, tool in observed_tools.items():
            monkeypatch.setattr(server, operation, tool)
        dispatches: list[tuple[str, int]] = []
        lifecycle_ledger: list[LifecycleLedgerEntry] = []
        runner_dispositions: list[Success | RateLimited | Crash] = []
        pick_count = 0
        runner = AsyncMock(
            side_effect=[
                Success("plan-001"),
                RateLimited(),
                Success("build-001"),
                Success("build-002"),
                Success("accept-001"),
                Crash(),
                Success("audit-001"),
            ]
        )
        target = revision.graph.nodes[0]
        proof = revision.resolve(target.proof)
        closure = {"paths": ["serve/kanban/"], "authority_targets": [target.id, target.proof]}
        node_plan_digest: str | None = None
        installed_profiles = {"planner", "builder", "acceptor", "auditor"}

        async def dispatch_one(attempt: int, claimed_at: str, finished_at: str) -> int | NativeHalt:
            nonlocal node_plan_digest, pick_count
            plan = await server.pick_jobs(
                ctx,
                change_id=revision.change_id,
                candidate_revision="a" * 40,
                wave_size=2,
            )
            pick_count += 1
            entry = plan.waves[0][0]
            dispatches.append((entry.agent_profile, entry.job_id))
            if entry.agent_profile not in installed_profiles:
                return NativeHalt(entry.agent_profile)
            started = _start_kwargs(entry.job_id, attempt, claimed_at)
            start = await server.start_job(ctx, **started)
            assert start.diagnostic is None
            outcome = await runner(entry.agent_profile, entry.job_id, start)
            runner_dispositions.append(outcome)
            operation = _lifecycle_operation(entry.agent_profile, outcome)
            terminal_pick = pick_count
            match operation:
                case "finish_plan":
                    finish = _finish_kwargs(started)
                    assert isinstance(outcome, Success)
                    result = await server.finish_plan(
                        ctx,
                        **finish,
                        finished_at=finished_at,
                        receipt_id=outcome.receipt_id,
                        code_revision="a" * 40,
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
                    assert result.receipt is not None
                    node_plan_digest = result.receipt.payload["node_plan_digest"]
                case "finish_build":
                    finish = _finish_kwargs(started)
                    assert isinstance(outcome, Success)
                    result = await server.finish_build(
                        ctx,
                        **finish,
                        finished_at=finished_at,
                        receipt_id=outcome.receipt_id,
                        code_revision="a" * 40,
                        evidence={"methods": list(proof.method)},
                        impact_closure=closure,
                    )
                case "finish_accept":
                    finish = _finish_kwargs(started)
                    assert isinstance(outcome, Success)
                    result = await server.finish_accept(
                        ctx,
                        **finish,
                        finished_at=finished_at,
                        receipt_id=outcome.receipt_id,
                        code_revision="a" * 40,
                        evidence={"methods": list(proof.method)},
                        reconciliation_plan_job_ids=(5, 6),
                    )
                case "finish_audit":
                    finish = _finish_kwargs(started)
                    assert isinstance(outcome, Success)
                    result = await server.finish_audit(
                        ctx,
                        **finish,
                        finished_at=finished_at,
                        receipt_id=outcome.receipt_id,
                        code_revision="a" * 40,
                        evidence={"methods": list(proof.method)},
                    )
                case "release_job":
                    result = await server.release_job(ctx, **_release_kwargs(started), released_at=finished_at)
                    assert result.diagnostic is None
                    assert result.event is not None
                    assert result.event.kind == "released"
                case "recover_expired_claims":
                    result = await server.recover_expired_claims(
                        ctx,
                        change_id=revision.change_id,
                        recovered_at=finished_at,
                        actor_id="proof-runner",
                        process_id="proof-process",
                    )
                    assert len(result.recovered) == 1
                    assert result.recovered[0].event.kind == "crashed"
                case unexpected:
                    pytest.fail(f"unexpected lifecycle operation: {unexpected}")
            if operation == "recover_expired_claims":
                assert result.diagnostics == ()
            else:
                assert result.diagnostic is None
            assert start.event is not None
            lifecycle_ledger.append(
                LifecycleLedgerEntry(
                    agent_profile=entry.agent_profile,
                    disposition=outcome,
                    operation=operation,
                    attempt_id=start.event.attempt_id,
                    selected_pick=terminal_pick,
                    terminal_pick=pick_count,
                )
            )
            return entry.job_id

        assert await dispatch_one(1, "2026-07-24T00:01:00Z", "2026-07-24T00:02:00Z") == 1
        assert await dispatch_one(2, "2026-07-24T00:03:00Z", "2026-07-24T00:03:30Z") == 2
        assert await dispatch_one(3, "2026-07-24T00:03:31Z", "2026-07-24T00:04:00Z") == 2
        assert await dispatch_one(4, "2026-07-24T00:04:01Z", "2026-07-24T00:05:00Z") == 3
        installed_profiles.remove("acceptor")
        jobs_before = jobs.list()
        attempts_before = AttemptStore(work_root).list()
        assert await dispatch_one(5, "2026-07-24T00:05:01Z", "2026-07-24T00:06:00Z") == NativeHalt("acceptor")
        assert jobs.list() == jobs_before
        assert AttemptStore(work_root).list() == attempts_before
        installed_profiles.add("acceptor")
        dispatches.pop()
        assert await dispatch_one(5, "2026-07-24T00:05:01Z", "2026-07-24T00:06:00Z") == 4
        assert node_plan_digest is not None

        audit = JobRecord(
            schema_version=1,
            job_id=7,
            kind="audit",
            priority=7,
            created_at="2026-07-24T00:06:00Z",
            updated_at="2026-07-24T00:06:00Z",
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            target_node_id=target.id,
            node_plan_digest=node_plan_digest,
            predecessor_job_ids=(4,),
        )
        RuntimeTransaction(work_root, "proof-014-audit", (jobs.create_participant(audit),)).commit()
        assert await dispatch_one(6, "2026-07-24T00:07:00Z", "2026-07-24T00:08:01Z") == 7
        assert await dispatch_one(7, "2026-07-24T00:08:02Z", "2026-07-24T00:09:00Z") == 7
        assert dispatches == [
            ("planner", 1),
            ("builder", 2),
            ("builder", 2),
            ("builder", 3),
            ("acceptor", 4),
            ("auditor", 7),
            ("auditor", 7),
        ]
        assert [call.args[:2] for call in runner.await_args_list] == dispatches
        assert all(
            call.args[2].event is not None and call.args[2].event.attempt_id == f"attempt-{index:03d}"
            for index, call in enumerate(runner.await_args_list, start=1)
        )
        events = AttemptStore(work_root).list()
        terminal_kinds = {"released", "crashed", "succeeded"}
        attempt_events = {
            attempt_id: tuple(event for event in events if event.attempt_id == attempt_id)
            for attempt_id in {event.attempt_id for event in events}
        }
        assert all(
            [event.sequence for event in attempt] == [1, 2]
            and attempt[0].kind == "started"
            and attempt[1].kind in terminal_kinds
            for attempt in attempt_events.values()
        )
        assert {attempt_id: attempt[1].kind for attempt_id, attempt in attempt_events.items()} == {
            "attempt-001": "succeeded",
            "attempt-002": "released",
            "attempt-003": "succeeded",
            "attempt-004": "succeeded",
            "attempt-005": "succeeded",
            "attempt-006": "crashed",
            "attempt-007": "succeeded",
        }
        for entry in lifecycle_ledger:
            entry.terminal_kind = attempt_events[entry.attempt_id][1].kind
        observed_operations = {
            str(call.kwargs["attempt_id"]): operation
            for operation, tool in observed_tools.items()
            if operation != "recover_expired_claims"
            for call in tool.await_args_list
        }
        recovery_entries = [entry for entry in lifecycle_ledger if entry.operation == "recover_expired_claims"]
        recovery_tool = observed_tools["recover_expired_claims"]
        assert recovery_tool.await_count == len(recovery_entries)
        for entry in recovery_entries:
            observed_operations[entry.attempt_id] = "recover_expired_claims"
        _assert_disposition_causality(lifecycle_ledger, runner_dispositions, observed_operations)

    def test_disposition_causality_rejects_attempt_order_bypass(self) -> None:
        """A lifecycle operation chosen without the runner result is not accepted as causal proof."""

        disposition = Success("receipt-from-runner")
        bypassed_ledger = [
            LifecycleLedgerEntry(
                agent_profile="builder",
                disposition=disposition,
                operation="finish_build",
                attempt_id="attempt-bypass",
                selected_pick=1,
                terminal_pick=1,
                terminal_kind="succeeded",
            )
        ]

        with pytest.raises(AssertionError):
            _assert_disposition_causality(
                bypassed_ledger,
                [disposition],
                {"attempt-bypass": "finish_plan"},
            )
