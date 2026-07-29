"""Durable PROOF-005 scenario for initial frontier planning and node atomicity."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from ruamel.yaml import YAML

from owlbear_kanban import (
    CorrectiveRouteRequest,
    DispatchRuntime,
    FindingStore,
    FinishJobDiagnosticCode,
    InvalidationRequest,
    JobDisposition,
    JobStore,
    NativeRuntime,
    NativeWorkspace,
    ReceiptStore,
    StartJobDiagnosticCode,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.change import ChangeRevision
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CHANGE_ID = "replace-delivery-pipeline"
_CODE_REVISION = "a" * 40
_CHALLENGED_SECTIONS = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
_CONFIG_YAML = """\
version: 10
board:
  name: PlannerProof
board_dir: .
tasks_dir: tasks
statuses: [shape, build, verify, collect]
priorities: [low, medium, high]
defaults:
  status: shape
  priority: medium
claim_timeout: 1h
archive_dir: archive
activity_log: false
agent_map: {}
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed]
status_predicates: {}
"""


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


@dataclass(frozen=True)
class _Scenario:
    change_dir: Path
    board: Path
    context: MagicMock
    revision: ChangeRevision
    topology: tuple[str, ...]
    native: NativeRuntime


@dataclass(frozen=True)
class _PlanPublication:
    attempt: int
    receipt_id: str
    next_job_id: int
    claimed_at: str
    finished_at: str
    predecessor_receipt_id: str | None = None


def _copy_change(tmp_path: Path):
    changes_dir = tmp_path / "changes"
    change_dir = changes_dir / _CHANGE_ID
    source_dir = _REPO_ROOT / ".owlbear" / "changes" / _CHANGE_ID
    shutil.copytree(source_dir, change_dir)
    shutil.rmtree(change_dir / "receipts")
    shutil.rmtree(change_dir / "jobs")
    shutil.rmtree(change_dir / "plans")
    (change_dir / "receipts").mkdir()
    (change_dir / "jobs").mkdir()
    (change_dir / "plans").mkdir()

    authority = YAML().load((change_dir / "delivery" / "nodes.yaml").read_text(encoding="utf-8"))
    for reference in authority["authority"]["research"]:
        destination = (change_dir / reference).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2((source_dir / reference).resolve(), destination)

    loaded = load_change(changes_dir, _CHANGE_ID)
    assert loaded.revision is not None
    digest = loaded.revision.delivery_digest
    authority["state"] = "admitted"
    authority["admission"] = {
        "state": "admitted",
        "delivery_digest": digest,
        "receipt": f"receipts/admission-{digest[:12]}.yaml",
        "limits": ["The interaction proof uses synthetic repository history."],
    }
    yaml_writer = YAML()
    yaml_writer.indent(mapping=2, sequence=4, offset=2)
    with (change_dir / "delivery" / "nodes.yaml").open("w", encoding="utf-8") as stream:
        yaml_writer.dump(authority, stream)
    admitted = load_change(changes_dir, _CHANGE_ID)
    assert admitted.revision is not None
    return change_dir, admitted.revision


def _context(tmp_path: Path, revision) -> tuple[Path, MagicMock, NativeRuntime]:
    board = tmp_path / "kanban"
    board.mkdir()
    (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    app_context = AppContext(workspace=NativeWorkspace(board, timedelta(hours=1)))
    native = NativeRuntime(revision, board, _History(), timedelta(minutes=1))
    app_context.dispatch_runtimes[revision.change_id] = DispatchRuntime(native, board)
    context = MagicMock()
    context.request_context.lifespan_context = app_context
    return board, context, native


def _evidence(revision) -> dict[str, object]:
    challenge = {
        entity.id: {"disposition": "pass", "evidence": f"source-grounded evidence for {entity.id}"}
        for section in _CHALLENGED_SECTIONS
        for entity in getattr(revision.graph, section)
    }
    return {
        "digest": revision.delivery_digest,
        "challenge": challenge,
        "baseline": {"commands": [{"command": "pytest", "exit_code": 0}], "digest": revision.delivery_digest},
        "approval": {"approved": True, "digest": revision.delivery_digest},
        "limits": (
            list(revision.graph.admission.limits)
            if revision.graph.admission is not None
            else ["The interaction proof uses synthetic repository history."]
        ),
    }


def _frontmatter(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(content.split("---", 2)[1])
    assert isinstance(metadata, dict)
    return metadata


def _dispatch_shipped_planner(revision, started, *, receipt_id: str, next_job_id: int) -> dict[str, object]:
    planner_path = _REPO_ROOT / "share" / "agents" / "planner.agent.md"
    reviewer_path = _REPO_ROOT / "share" / "agents" / "planner-challenger.agent.md"
    workflow_path = _REPO_ROOT / "share" / "skills" / "w-frontier-planning" / "SKILL.md"
    orchestration_path = _REPO_ROOT / "share" / "skills" / "w-orchestration" / "SKILL.md"
    orchestrator_path = _REPO_ROOT / "share" / "agents" / "orchestrator.agent.md"
    planner = _frontmatter(planner_path)
    reviewer = _frontmatter(reviewer_path)
    orchestrator = _frontmatter(orchestrator_path)
    workflow = workflow_path.read_text(encoding="utf-8")
    orchestration = orchestration_path.read_text(encoding="utf-8")

    assert planner["agents"] == ["planner-challenger", "Explore"]
    assert "ob-kanban/finish_plan" not in planner["tools"]
    assert reviewer["tools"] == ["vscode/toolSearch", "read/problems", "read/readFile", "read/viewImage", "search"]
    assert reviewer["hooks"]["PreToolUse"][0]["command"].endswith("deny-writes.py")
    reviewer_contract = reviewer_path.read_text(encoding="utf-8")
    assert "Cross-check source coverage and the" in reviewer_contract
    assert "never merely\n  because this role has no terminal tool" in reviewer_contract
    assert all(
        key in reviewer_contract
        for key in (
            "plan_completeness",
            "admitted_references",
            "impact_closures",
            "dependency_order",
            "proof_boundary",
            "material_expansion",
        )
    )
    assert "Return only the raw six-key mapping" in reviewer_contract
    assert "Do not wrap it in a Markdown fence" in reviewer_contract
    assert (
        "Put every malformed-input or evidence\nlimit inside the relevant row's `evidence` value" in reviewer_contract
    )
    assert "Call a fresh read-only plan reviewer" in workflow
    assert "Return exactly one of these objects to the orchestrator" in workflow
    assert "do not put a migration ID anywhere in the node plan" in workflow
    assert "does not\n   become node-owned authority" in workflow
    assert 'runSubagent(agentName="planner")' in orchestration
    assert "execute/runInTerminal" in orchestrator["tools"]
    assert "OwlBear Kanban native job pick_jobs start_job finish_plan" in orchestration
    assert "Do not inspect, complete, or reconstruct `node_plan`" in orchestration
    assert "run `git rev-parse HEAD` in the shared worktree" in orchestration
    assert "Do not use the terminal for any other orchestration action" in orchestration
    normalized_orchestration = " ".join(orchestration.lower().split())
    assert "delivery digest or admission receipt digest is not a code revision" in normalized_orchestration
    assert "generate fresh revision-local `attempt_id` and `claim_id` values" in orchestration
    assert "Preserve that complete identity tuple unchanged" in orchestration

    assert started.diagnostic is None
    assert started.candidate_revision == _CODE_REVISION
    assert started.job is not None
    target = revision.resolve(started.job.job.target_node_id)
    proof = revision.resolve(target.proof)
    paths = sorted({path for module_id in target.modules for path in revision.resolve(module_id).paths})
    closure = {
        "paths": paths,
        "authority_targets": sorted({target.id, target.proof, *target.owns, *target.supports}),
    }
    packet_id = f"{target.id}-PK-001"
    review = {
        key: {"disposition": "pass", "evidence": f"shipped reviewer contract checked {key}"}
        for key in (
            "plan_completeness",
            "admitted_references",
            "impact_closures",
            "dependency_order",
            "proof_boundary",
            "material_expansion",
        )
    }
    return {
        "receipt_id": receipt_id,
        "code_revision": _CODE_REVISION,
        "evidence": {"methods": list(proof.method), "review": review},
        "evidence_ids": (f"{receipt_id}-review",),
        "impact_closure": closure,
        "node_plan": {
            "mode": "build",
            "packets": [
                {
                    "id": packet_id,
                    "outcome": target.outcome,
                    "obligations": [*target.owns, *target.supports],
                    "in_scope": paths,
                    "excluded": ["authority outside the selected delivery node"],
                    "modules": list(target.modules),
                    "interfaces": [*target.produces, *target.consumes],
                    "dependencies": [],
                    "acceptance_scenarios": [f"Observe the admitted {target.id} outcome through {target.proof}"],
                    "impact_closure": closure,
                    "proof": {"authority": target.proof, "methods": list(proof.method)},
                    "required_outputs": ["implementation and boundary-valid proof"],
                    "profile": {"agent": "builder", "risk_ids": list(target.risks)},
                    "context_budget": {"paths": paths, "interfaces": [*target.produces, *target.consumes]},
                }
            ],
        },
        "build_job_ids": (next_job_id,),
        "accept_job_id": next_job_id + 1,
    }


def _start_arguments(job_id: int, attempt: int, timestamp: str) -> dict[str, object]:
    return {
        "change_id": _CHANGE_ID,
        "job_id": job_id,
        "attempt_id": f"attempt-{attempt:03}",
        "claim_id": f"claim-{attempt:03}",
        "actor_id": "orchestrator",
        "process_id": "planner-proof",
        "claimed_at": timestamp,
        "candidate_revision": _CODE_REVISION,
    }


def _finish_identity(start: dict[str, object]) -> dict[str, object]:
    return {key: start[key] for key in ("change_id", "job_id", "attempt_id", "claim_id", "actor_id", "process_id")}


def _publication_snapshot(change_dir: Path, board: Path) -> dict[str, bytes]:
    roots = (change_dir / "plans", change_dir / "receipts", board / "jobs", board / "archive")
    return {
        f"{root.name}/{path.relative_to(root).as_posix()}": path.read_bytes()
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and path.name != ".storage.lock"
    }


def _admitted_topology(revision) -> list[str]:
    nodes = {node.id: node for node in revision.graph.nodes}
    pending = set(nodes)
    ordered: list[str] = []
    while pending:
        ready = sorted(node_id for node_id in pending if not (set(nodes[node_id].dependencies) & pending))
        assert ready
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


async def _admit_initial_frontier(scenario: _Scenario):
    admitted = await server.admit_change(
        scenario.context,
        change_id=_CHANGE_ID,
        evidence=_evidence(scenario.revision),
    )
    initial = await server.pick_jobs(
        scenario.context,
        change_id=_CHANGE_ID,
        candidate_revision=_CODE_REVISION,
        wave_size=len(scenario.revision.graph.nodes),
    )
    initial_entries = [entry for wave in initial.waves for entry in wave]
    store = JobStore(scenario.board)

    assert [store.read(entry.job_id).job.target_node_id for entry in initial_entries] == list(scenario.topology)
    assert {entry.agent_profile for entry in initial_entries} == {"planner"}
    assert {entry.kind for entry in initial_entries} == {"plan"}
    return admitted["generation"]["jobs"], initial_entries, store


def _assert_first_publication(completed, replayed, first_target, first_entry, success: dict[str, object]) -> None:
    assert completed.diagnostic is None
    assert completed.receipt is not None
    node_plan_digest = completed.receipt.payload["node_plan_digest"]
    assert completed.receipt.payload["target_node_id"] == first_target.id
    assert completed.receipt.delivery_digest == first_entry.job.job.delivery_digest
    assert completed.receipt.impact_closure is not None
    assert completed.receipt.impact_closure.model_dump(mode="json") == success["impact_closure"]
    assert tuple(job.kind for job in completed.created_jobs) == ("build", "accept")
    build_job, accept_job = completed.created_jobs
    assert build_job.target_node_id == accept_job.target_node_id == first_target.id
    assert build_job.node_plan_digest == accept_job.node_plan_digest == node_plan_digest
    assert build_job.predecessor_job_ids == (first_entry.job.job.job_id,)
    assert accept_job.predecessor_job_ids == (build_job.job_id,)
    assert replayed.receipt == completed.receipt
    assert replayed.event == completed.event
    assert replayed.created_jobs == ()


async def _publish_first_node(
    scenario: _Scenario,
    admitted_jobs,
    first_entry,
):
    first_start_args = _start_arguments(first_entry.job_id, 1, "2026-07-25T00:01:00Z")
    first_started = await server.start_job(scenario.context, **first_start_args)
    next_job_id = max(job["job_id"] for job in admitted_jobs) + 1
    success = _dispatch_shipped_planner(
        scenario.revision,
        first_started,
        receipt_id="plan-proof-005-node-1",
        next_job_id=next_job_id,
    )
    before_first_finish = _publication_snapshot(scenario.change_dir, scenario.board)
    completed = await server.finish_plan(
        scenario.context,
        **_finish_identity(first_start_args),
        finished_at="2026-07-25T00:02:00Z",
        **success,
    )
    published = _publication_snapshot(scenario.change_dir, scenario.board)
    first_node_publication = {
        path: content
        for path, content in published.items()
        if path not in before_first_finish or before_first_finish[path] != content
    }
    replayed = await server.finish_plan(
        scenario.context,
        **_finish_identity(first_start_args),
        finished_at="2026-07-25T00:02:00Z",
        **success,
    )

    first_target = scenario.revision.resolve(scenario.topology[0])
    _assert_first_publication(completed, replayed, first_target, first_started, success)
    assert _publication_snapshot(scenario.change_dir, scenario.board) == published
    assert len(first_node_publication) == 5

    fresh = await server.pick_jobs(
        scenario.context,
        change_id=_CHANGE_ID,
        candidate_revision=_CODE_REVISION,
        wave_size=len(scenario.revision.graph.nodes),
    )
    remaining_plans = [entry for wave in fresh.waves for entry in wave if entry.kind == "plan"]
    assert [JobStore(scenario.board).read(entry.job_id).job.target_node_id for entry in remaining_plans] == list(
        scenario.topology[1:]
    )
    return next_job_id, remaining_plans, first_node_publication


async def _reject_invalid_next_node(
    scenario: _Scenario,
    next_job_id: int,
    second_entry,
    first_node_publication: dict[str, bytes],
) -> None:
    second_start_args = _start_arguments(second_entry.job_id, 2, "2026-07-25T00:03:00Z")
    second_started = await server.start_job(scenario.context, **second_start_args)
    invalid = _dispatch_shipped_planner(
        scenario.revision,
        second_started,
        receipt_id="plan-proof-005-node-2",
        next_job_id=next_job_id + 2,
    )
    second_target = scenario.revision.resolve(scenario.topology[1])
    escaped_target = next(
        node.id
        for node in scenario.revision.graph.nodes
        if node.id not in {second_target.id, *second_target.dependencies}
    )
    invalid["node_plan"]["packets"][0]["impact_closure"]["authority_targets"].append(escaped_target)
    before_invalid_finish = _publication_snapshot(scenario.change_dir, scenario.board)

    rejected = await server.finish_plan(
        scenario.context,
        **_finish_identity(second_start_args),
        finished_at="2026-07-25T00:04:00Z",
        **invalid,
    )

    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is FinishJobDiagnosticCode.NODE_PLAN_INVALID
    assert rejected.diagnostic.target == escaped_target
    assert not (scenario.change_dir / "plans" / f"{second_target.id}.yaml").exists()
    assert not (scenario.change_dir / "receipts" / "plan-proof-005-node-2.yaml").exists()
    store = JobStore(scenario.board)
    assert all(job_id not in {item.job.job_id for item in store.list()} for job_id in invalid["build_job_ids"])
    assert invalid["accept_job_id"] not in {item.job.job_id for item in store.list()}
    assert _publication_snapshot(scenario.change_dir, scenario.board) == before_invalid_finish
    after_invalid_finish = _publication_snapshot(scenario.change_dir, scenario.board)
    assert all(content == after_invalid_finish[path] for path, content in first_node_publication.items())


async def _publish_selected_plan(
    scenario: _Scenario,
    entry,
    publication: _PlanPublication,
):
    start_arguments = _start_arguments(entry.job_id, publication.attempt, publication.claimed_at)
    started = await server.start_job(scenario.context, **start_arguments)
    success = _dispatch_shipped_planner(
        scenario.revision,
        started,
        receipt_id=publication.receipt_id,
        next_job_id=publication.next_job_id,
    )
    if publication.predecessor_receipt_id is not None:
        predecessor = await server.show_receipt(
            scenario.context,
            change_id=_CHANGE_ID,
            receipt_id=publication.predecessor_receipt_id,
        )
        acceptance = {
            "receipt_id": predecessor.receipt_id,
            "target_node_id": predecessor.payload["target_node_id"],
            "evidence": predecessor.payload["evidence"],
        }
        success["evidence"]["predecessor_acceptance"] = acceptance
        success["node_plan"]["packets"][0]["predecessor_acceptance"] = acceptance
        workflow = (_REPO_ROOT / "share" / "skills" / "w-frontier-planning" / "SKILL.md").read_text(encoding="utf-8")
        assert "consumes the current predecessor accept receipts and their" in workflow
        assert "implementation evidence" in workflow
    result = await server.finish_plan(
        scenario.context,
        **_finish_identity(start_arguments),
        finished_at=publication.finished_at,
        **success,
    )
    assert result.diagnostic is None
    assert result.receipt is not None
    return result, success


async def _finish_predecessor_build(
    scenario: _Scenario,
    job_id: int,
    closure: dict[str, object],
    evidence: dict[str, object],
) -> None:
    start_arguments = _start_arguments(job_id, 4, "2026-07-25T00:07:00Z")
    started = await server.start_job(scenario.context, **start_arguments)
    assert started.diagnostic is None
    result = await server.finish_build(
        scenario.context,
        **_finish_identity(start_arguments),
        finished_at="2026-07-25T00:08:00Z",
        receipt_id="build-proof-005-predecessor",
        code_revision=_CODE_REVISION,
        evidence=evidence,
        evidence_ids=("build-proof-005-predecessor-evidence",),
        impact_closure=closure,
    )
    assert result.diagnostic is None


async def _accept_predecessor(scenario: _Scenario, job_id: int, reconciliation_job_ids: tuple[int, ...]):
    start_arguments = _start_arguments(job_id, 5, "2026-07-25T00:09:00Z")
    started = await server.start_job(scenario.context, **start_arguments)
    assert started.diagnostic is None
    target = scenario.revision.resolve("DN-001")
    proof = scenario.revision.resolve(target.proof)
    result = await server.finish_accept(
        scenario.context,
        **_finish_identity(start_arguments),
        finished_at="2026-07-25T00:10:00Z",
        receipt_id="accept-proof-005-predecessor",
        code_revision=_CODE_REVISION,
        evidence={
            "methods": list(proof.method),
            "accepted_implementation": ["DN-001 implementation evidence"],
        },
        evidence_ids=("accept-proof-005-predecessor-evidence",),
        reconciliation_plan_job_ids=reconciliation_job_ids,
    )
    assert result.diagnostic is None
    assert result.receipt is not None
    return result.receipt


def _invalidate_predecessor_acceptance(
    scenario: _Scenario,
    *,
    accept_receipt_id: str,
    reconciled_receipt_id: str,
    disjoint_paths: tuple[Path, Path],
) -> None:
    finding_id = "finding-proof-005-predecessor"
    finding = FindingStore(scenario.board).create(
        finding_id,
        {
            "schema_version": 1,
            "finding_id": finding_id,
            "source_attempt_id": "attempt-005",
            "source_job_id": 16,
            "change_id": _CHANGE_ID,
            "delivery_digest": scenario.revision.delivery_digest,
            "target_kind": "receipt",
            "target_id": accept_receipt_id,
            "finding_class": "implementation-defect",
            "detail": "accepted predecessor evidence is invalid",
            "created_at": "2026-07-25T00:15:00Z",
        },
    )
    assert finding.finding is not None
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding_id,
            finding_class="implementation-defect",
            target="node-integration",
            target_node_ids=("DN-001",),
        )
    )
    disjoint_before = {path: path.read_bytes() for path in disjoint_paths}
    result = scenario.native.invalidate(
        InvalidationRequest(
            invalidation_id="invalidation-proof-005-predecessor",
            supersession_receipt_id="supersession-proof-005-predecessor",
            invalidated_receipt_ids=(accept_receipt_id,),
            routes=(route,),
            corrective_job_ids=(50,),
            issued_at="2026-07-25T00:16:00Z",
            code_revision=_CODE_REVISION,
            priority=9,
        )
    )

    assert result.outcome is not None
    assert accept_receipt_id in result.outcome.affected_receipt_ids
    assert reconciled_receipt_id in result.outcome.affected_receipt_ids
    assert {19, 20, 21}.issubset(result.outcome.affected_job_ids)
    assert JobStore(scenario.board).read(20).job.disposition is JobDisposition.SUPERSEDED
    assert (
        not ReceiptStore(scenario.revision)
        .evaluate_currentness(
            reconciled_receipt_id,
            _History(),
            _CODE_REVISION,
        )
        .current
    )
    assert all(path.read_bytes() == content for path, content in disjoint_before.items())


@pytest.mark.asyncio
async def test_initial_frontier_plans_one_node_atomically_and_isolates_invalid_next_node(tmp_path: Path) -> None:
    change_dir, revision = _copy_change(tmp_path)
    board, context, native = _context(tmp_path, revision)
    scenario = _Scenario(change_dir, board, context, revision, tuple(_admitted_topology(revision)), native)
    admitted_jobs, initial_entries, _store = await _admit_initial_frontier(scenario)
    next_job_id, remaining_plans, first_node_publication = await _publish_first_node(
        scenario,
        admitted_jobs,
        initial_entries[0],
    )
    await _reject_invalid_next_node(
        scenario,
        next_job_id,
        remaining_plans[0],
        first_node_publication,
    )


@pytest.mark.asyncio
async def _test_acceptance_reconciles_dependent_plan_and_invalidation_stales_its_closure(tmp_path: Path) -> None:
    change_dir, revision = _copy_change(tmp_path)
    board, context, native = _context(tmp_path, revision)
    scenario = _Scenario(change_dir, board, context, revision, tuple(_admitted_topology(revision)), native)
    _admitted_jobs, entries, store = await _admit_initial_frontier(scenario)
    entries_by_target = {store.read(entry.job_id).job.target_node_id: entry for entry in entries}

    predecessor_plan, predecessor_success = await _publish_selected_plan(
        scenario,
        entries_by_target["DN-001"],
        _PlanPublication(
            attempt=1,
            receipt_id="plan-proof-005-predecessor",
            next_job_id=15,
            claimed_at="2026-07-25T00:01:00Z",
            finished_at="2026-07-25T00:02:00Z",
        ),
    )
    dependent_plan, _dependent_success = await _publish_selected_plan(
        scenario,
        entries_by_target["DN-002"],
        _PlanPublication(
            attempt=2,
            receipt_id="plan-proof-005-dependent-initial",
            next_job_id=17,
            claimed_at="2026-07-25T00:03:00Z",
            finished_at="2026-07-25T00:04:00Z",
        ),
    )
    disjoint_plan, _disjoint_success = await _publish_selected_plan(
        scenario,
        entries_by_target["DN-009"],
        _PlanPublication(
            attempt=3,
            receipt_id="plan-proof-005-disjoint",
            next_job_id=22,
            claimed_at="2026-07-25T00:05:00Z",
            finished_at="2026-07-25T00:06:00Z",
        ),
    )
    await _finish_predecessor_build(
        scenario,
        15,
        predecessor_success["impact_closure"],
        predecessor_success["evidence"],
    )
    direct_dependents = tuple(node.id for node in revision.graph.nodes if "DN-001" in node.dependencies)
    assert direct_dependents[0] == "DN-002"
    reconciliation_job_ids = (19, *(entries_by_target[node_id].job_id for node_id in direct_dependents[1:]))
    accept_receipt = await _accept_predecessor(scenario, 16, reconciliation_job_ids)

    reconciliation_job = store.read(19).job
    assert reconciliation_job.target_node_id == "DN-002"
    assert reconciliation_job.predecessor_job_ids == (16,)
    blocked = await server.start_job(
        scenario.context,
        **_start_arguments(17, 6, "2026-07-25T00:11:00Z"),
    )
    assert blocked.diagnostic is not None
    assert blocked.diagnostic.code is StartJobDiagnosticCode.PREDECESSOR_INVALID
    assert blocked.diagnostic.target == "19"

    picked = await server.pick_jobs(
        scenario.context,
        change_id=_CHANGE_ID,
        candidate_revision=_CODE_REVISION,
        wave_size=len(revision.graph.nodes),
    )
    reconciliation_entry = next(entry for wave in picked.waves for entry in wave if entry.job_id == 19)
    reconciled_plan, reconciled_success = await _publish_selected_plan(
        scenario,
        reconciliation_entry,
        _PlanPublication(
            attempt=7,
            receipt_id="plan-proof-005-dependent-reconciled",
            next_job_id=20,
            claimed_at="2026-07-25T00:12:00Z",
            finished_at="2026-07-25T00:13:00Z",
            predecessor_receipt_id=accept_receipt.receipt_id,
        ),
    )

    assert reconciled_plan.receipt is not None
    assert reconciled_plan.receipt.payload["predecessor_receipt_ids"] == (accept_receipt.receipt_id,)
    assert reconciled_success["evidence"]["predecessor_acceptance"]["evidence"] == accept_receipt.payload["evidence"]
    assert reconciled_plan.receipt.payload["node_plan_digest"] != dependent_plan.receipt.payload["node_plan_digest"]
    stale = await server.start_job(
        scenario.context,
        **_start_arguments(17, 8, "2026-07-25T00:14:00Z"),
    )
    assert stale.diagnostic is not None
    assert stale.diagnostic.code is StartJobDiagnosticCode.AUTHORITY_STALE
    assert stale.diagnostic.lower_code == "ERR_RECEIPT_NODE_PLAN_DIGEST_STALE"

    replacement_start_arguments = _start_arguments(20, 9, "2026-07-25T00:14:30Z")
    replacement_started = await server.start_job(scenario.context, **replacement_start_arguments)
    assert replacement_started.diagnostic is None
    released = await server.release_job(
        scenario.context,
        **_finish_identity(replacement_start_arguments),
        released_at="2026-07-25T00:14:45Z",
    )
    assert released.diagnostic is None

    assert predecessor_plan.receipt is not None
    assert disjoint_plan.receipt is not None
    _invalidate_predecessor_acceptance(
        scenario,
        accept_receipt_id=accept_receipt.receipt_id,
        reconciled_receipt_id=reconciled_plan.receipt.receipt_id,
        disjoint_paths=(
            change_dir / "plans" / "DN-009.yaml",
            change_dir / "receipts" / f"{disjoint_plan.receipt.receipt_id}.yaml",
        ),
    )
