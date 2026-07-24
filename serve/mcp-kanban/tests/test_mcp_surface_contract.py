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
AC4 (td:1): end_work published parameter schema includes all 5 outcome values.
AC5-AC7: td:0 — no executable tests.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import owlbear_mcp_kanban
from owlbear_mcp_kanban import server
from owlbear_kanban import (
    AttemptStore,
    DispatchRuntime,
    JobGeneration,
    JobRecord,
    JobStore,
    NativeRuntime,
    ShapeJob,
    load_change,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction
from owlbear_kanban.yaml_rt import make_yaml
from owlbear_mcp_kanban.server import AppContext, app_lifespan, mcp

# ---------------------------------------------------------------------------
# Deployment-contract snapshot
# UPDATE THIS SET (and server.py) together when tools are added or removed.
# ---------------------------------------------------------------------------

EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "list_tasks",
        "show_task",
        "create_task",
        "move_task",
        "edit_task",
        "start_work",
        "end_work",
        "pick_tasks",
        "create_request",
        "list_requests",
        "show_request",
        "pick_jobs",
        "start_job",
        "finish_shape",
        "finish_build",
        "finish_accept",
        "finish_audit",
        "release_job",
        "recover_expired_claims",
    }
)

EXPECTED_OUTCOMES: frozenset[str] = frozenset({"success", "fail", "reject", "block", "release"})

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
    async def test_live_registry_contains_exactly_twelve_tools(
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


# ---------------------------------------------------------------------------
# AC4 — end_work outcome schema
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkOutcomeSchema:
    """AC4: end_work published parameter schema (post-_patch_params) includes all 5 outcomes."""

    def test_end_work_published_outcome_schema_includes_all_five_values(self) -> None:
        """AC4: mcp._tool_manager._tools['end_work'].parameters exposes all 5 outcome values.

        Checks the published MCP schema — what MCP clients receive — NOT the Python
        function signature. _patch_params mutates the schema at module scope; this test
        runs after import so post-mutation state is captured. The schema may encode
        allowed values as ``enum`` or ``anyOf`` branches; both forms are accepted.
        """
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "end_work"),  # noqa: SLF001
            None,
        )
        assert tool is not None, "end_work must be registered in the MCP tool registry"

        outcome_prop = tool.parameters.get("properties", {}).get("outcome", {})

        # Collect string literals from the schema subtree (enum or anyOf/const forms).
        actual_values: set[str] = set()
        if "enum" in outcome_prop:
            actual_values.update(v for v in outcome_prop["enum"] if isinstance(v, str))
        if "anyOf" in outcome_prop:
            for branch in outcome_prop["anyOf"]:
                if "const" in branch and isinstance(branch["const"], str):
                    actual_values.add(branch["const"])
                if "enum" in branch:
                    actual_values.update(v for v in branch["enum"] if isinstance(v, str))

        assert actual_values >= EXPECTED_OUTCOMES, (
            f"end_work outcome schema is missing values: "
            f"{EXPECTED_OUTCOMES - actual_values!r}. "
            f"Found values: {actual_values!r}. "
            f"Raw 'outcome' property schema: {outcome_prop!r}"
        )


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


class TestProof014NativeMcpScenario:
    """The bootstrap native loop dispatches profiles through the installed MCP bridge."""

    def test_native_mode_artifacts_expose_if_015_contract(self) -> None:
        """The source ecosystem retains the non-default IF-015 contract."""
        root = next(parent for parent in Path(__file__).resolve().parents if (parent / "share").is_dir())
        agent = (root / "share/agents/orchestrator.agent.md").read_text(encoding="utf-8")
        skill = (root / "share/skills/w-orchestration/SKILL.md").read_text(encoding="utf-8")
        prompt = (root / "share/prompts/orchestrate.prompt.md").read_text(encoding="utf-8")
        wiring = (root / "share/WIRING.md").read_text(encoding="utf-8")
        native_tools = {
            "pick_jobs",
            "start_job",
            "finish_shape",
            "finish_build",
            "finish_accept",
            "finish_audit",
            "release_job",
            "recover_expired_claims",
        }

        agent_tools = {
            tool.removeprefix("ob-kanban/")
            for tool in agent.split("tools: [", 1)[1].split("]", 1)[0].replace(" ", "").split(",")
        }
        assert native_tools <= agent_tools
        for artifact in (skill, prompt, wiring):
            assert "IF-015" in artifact
            assert "pick_tasks" in artifact
        assert "non-default" in skill
        assert "acceptor" not in agent.split("agents:", 1)[1].split("---", 1)[0]
        assert "auditor" not in agent.split("agents:", 1)[1].split("---", 1)[0]

    @pytest.mark.asyncio
    async def test_profiles_release_recovery_and_replanning_use_native_tools(  # noqa: PLR0915
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        changes_dir = tmp_path / "changes"
        shutil.copytree(
            Path(".owlbear/changes/replace-delivery-pipeline"),
            changes_dir / "replace-delivery-pipeline",
        )
        graph_path = changes_dir / "replace-delivery-pipeline" / "graph.yaml"
        document = make_yaml().load(graph_path.read_text(encoding="utf-8"))
        document["execution"]["node_plans"].pop("DN-001", None)
        with graph_path.open("w", encoding="utf-8") as stream:
            make_yaml(explicit_start=True).dump(document, stream)
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
                    ShapeJob(
                        job_id=1,
                        kind="shape",
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
        dispatches: list[tuple[str, int]] = []
        runner = AsyncMock(
            side_effect=[
                Success("shape-001"),
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
        installed_profiles = {"shaper", "builder", "acceptor", "auditor"}

        async def dispatch_one(attempt: int, claimed_at: str, finished_at: str) -> int | NativeHalt:
            nonlocal node_plan_digest
            plan = await server.pick_jobs(
                ctx,
                change_id=revision.change_id,
                candidate_revision="a" * 40,
                wave_size=2,
            )
            entry = plan.waves[0][0]
            dispatches.append((entry.agent_profile, entry.job_id))
            if entry.agent_profile not in installed_profiles:
                return NativeHalt(entry.agent_profile)
            started = _start_kwargs(entry.job_id, attempt, claimed_at)
            start = await server.start_job(ctx, **started)
            assert start.diagnostic is None
            outcome = await runner(entry.agent_profile, entry.job_id, start)
            match outcome:
                case Success(receipt_id):
                    finish = _finish_kwargs(started)
                    if entry.agent_profile == "shaper":
                        result = await server.finish_shape(
                            ctx,
                            **finish,
                            finished_at=finished_at,
                            receipt_id=receipt_id,
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
                    elif entry.agent_profile == "builder":
                        result = await server.finish_build(
                            ctx,
                            **finish,
                            finished_at=finished_at,
                            receipt_id=receipt_id,
                            code_revision="a" * 40,
                            evidence={"methods": list(proof.method)},
                            impact_closure=closure,
                        )
                    elif entry.agent_profile == "acceptor":
                        result = await server.finish_accept(
                            ctx,
                            **finish,
                            finished_at=finished_at,
                            receipt_id=receipt_id,
                            code_revision="a" * 40,
                            evidence={"methods": list(proof.method)},
                        )
                    else:
                        result = await server.finish_audit(
                            ctx,
                            **finish,
                            finished_at=finished_at,
                            receipt_id=receipt_id,
                            code_revision="a" * 40,
                            evidence={"methods": list(proof.method)},
                        )
                    assert result.diagnostic is None
                case RateLimited():
                    result = await server.release_job(ctx, **_release_kwargs(started), released_at=finished_at)
                    assert result.diagnostic is None
                    assert result.event is not None
                    assert result.event.kind == "released"
                case Crash():
                    result = await server.recover_expired_claims(
                        ctx,
                        change_id=revision.change_id,
                        recovered_at=finished_at,
                        actor_id="proof-runner",
                        process_id="proof-process",
                    )
                    assert len(result.recovered) == 1
                    assert result.recovered[0].event.kind == "crashed"
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
            job_id=5,
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
        assert await dispatch_one(6, "2026-07-24T00:07:00Z", "2026-07-24T00:08:01Z") == 5
        assert await dispatch_one(7, "2026-07-24T00:08:02Z", "2026-07-24T00:09:00Z") == 5
        assert dispatches == [
            ("shaper", 1),
            ("builder", 2),
            ("builder", 2),
            ("builder", 3),
            ("acceptor", 4),
            ("auditor", 5),
            ("auditor", 5),
        ]
        assert [call.args[:2] for call in runner.await_args_list] == dispatches
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
