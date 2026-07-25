"""Durable PROOF-006 scenario for native builder success and warm local repair."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from ruamel.yaml import YAML

from owlbear_kanban import (
    AttemptStore,
    DispatchDiagnostic,
    DispatchDiagnosticCode,
    DispatchRuntime,
    JobStore,
    NativeRuntime,
    ReceiptDiagnosticCode,
    ReceiptStore,
    StartJobResult,
    load_change,
)
from owlbear_kanban.change import ChangeRevision
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext
from owlbear_tools.commit_owned import commit_owned_paths

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CHANGE_ID = "replace-delivery-pipeline"
_TARGET_NODE_ID = "DN-001"
_CHALLENGED_SECTIONS = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
_CONFIG_YAML = """\
version: 10
board:
  name: BuilderProof
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
    repository: Path
    base_revision: str


@dataclass(frozen=True)
class _ReviewInput:
    base_revision: str
    code_revision: str
    proof: subprocess.CompletedProcess[str]
    prior_findings: list[dict[str, str]]


@dataclass(frozen=True)
class _RepairOutcome:
    first_context: dict[str, object]
    first_review: dict[str, object]
    repaired_context: dict[str, object]
    repaired_review: dict[str, object]
    repair_commit: str


def _run(repository: Path, *command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        check=check,
        text=True,
        capture_output=True,
    )


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    return _run(repository, executable, *arguments).stdout.strip()


def _copy_change(tmp_path: Path) -> tuple[Path, ChangeRevision]:
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
    return change_dir, loaded.revision


def _sample_repository(tmp_path: Path) -> tuple[Path, str]:
    repository = tmp_path / "product"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "Builder Proof")
    _git(repository, "config", "user.email", "builder-proof@example.invalid")
    (repository / "README.md").write_text("# Builder proof fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(repository, "commit", "-m", "fixture: initialize product")
    return repository, _git(repository, "rev-parse", "HEAD")


@pytest.fixture
def scenario(tmp_path: Path) -> _Scenario:
    change_dir, revision = _copy_change(tmp_path)
    repository, base_revision = _sample_repository(tmp_path)
    board = tmp_path / "kanban"
    board.mkdir()
    (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    app_context = AppContext(engine=server.KanbanEngine(board), kanban_dir=board)
    native = NativeRuntime(revision, board, _History(), timedelta(minutes=5))
    app_context.dispatch_runtimes[revision.change_id] = DispatchRuntime(native, board)
    context = MagicMock()
    context.request_context.lifespan_context = app_context
    return _Scenario(change_dir, board, context, revision, repository, base_revision)


def _admission_evidence(revision: ChangeRevision) -> dict[str, object]:
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
        "limits": list(revision.graph.admission.limits),
    }


def _frontmatter(path: Path) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(content.split("---", 2)[1])
    assert isinstance(metadata, dict)
    return metadata


def _start_arguments(job_id: int, attempt: int, timestamp: str, candidate_revision: str) -> dict[str, object]:
    return {
        "change_id": _CHANGE_ID,
        "job_id": job_id,
        "attempt_id": f"attempt-{attempt:03}",
        "claim_id": f"claim-{attempt:03}",
        "actor_id": "orchestrator",
        "process_id": "builder-proof",
        "claimed_at": timestamp,
        "candidate_revision": candidate_revision,
    }


def _finish_identity(start: dict[str, object]) -> dict[str, object]:
    return {key: start[key] for key in ("change_id", "job_id", "attempt_id", "claim_id", "actor_id", "process_id")}


async def _publish_target_plan(scenario: _Scenario) -> tuple[int, int]:
    admitted = await server.admit_change(
        scenario.context,
        change_id=_CHANGE_ID,
        evidence=_admission_evidence(scenario.revision),
    )
    initial = await server.pick_jobs(
        scenario.context,
        change_id=_CHANGE_ID,
        candidate_revision=scenario.base_revision,
        wave_size=len(scenario.revision.graph.nodes),
    )
    entries = [entry for wave in initial.waves for entry in wave]
    store = JobStore(scenario.board)
    target_entry = next(entry for entry in entries if store.read(entry.job_id).job.target_node_id == _TARGET_NODE_ID)
    waiting_writer = next(entry for entry in entries if entry.job_id != target_entry.job_id)
    start = _start_arguments(target_entry.job_id, 1, "2026-07-25T01:00:00Z", scenario.base_revision)
    started = await server.start_job(scenario.context, **start)
    assert started.diagnostic is None

    target = scenario.revision.resolve(_TARGET_NODE_ID)
    proof = scenario.revision.resolve(target.proof)
    closure = {"paths": ["sample/module.py"], "authority_targets": [target.id, target.proof]}
    next_job_id = max(job["job_id"] for job in admitted["generation"]["jobs"]) + 1
    completed = await server.finish_plan(
        scenario.context,
        **_finish_identity(start),
        finished_at="2026-07-25T01:01:00Z",
        receipt_id="plan-proof-006-builder",
        code_revision=scenario.base_revision,
        evidence={"methods": list(proof.method), "review": {"disposition": "pass"}},
        evidence_ids=("plan-proof-006-review",),
        impact_closure=closure,
        node_plan={
            "packets": [
                {
                    "id": f"{target.id}-PK-001",
                    "outcome": target.outcome,
                    "obligations": [*target.owns, *target.supports],
                    "in_scope": ["sample/module.py"],
                    "excluded": [f"authority and work outside {target.id}"],
                    "modules": list(target.modules),
                    "interfaces": [*target.produces, *target.consumes],
                    "dependencies": [],
                    "acceptance_scenarios": ["sample outcome returns reviewed"],
                    "impact_closure": closure,
                    "proof": {"authority": target.proof, "methods": list(proof.method)},
                    "required_outputs": ["sample/module.py", "review evidence"],
                    "profile": {"agent": "builder", "risk_ids": list(target.risks)},
                    "context_budget": {"paths": ["sample/module.py"], "interfaces": list(target.produces)},
                }
            ]
        },
        build_job_ids=(next_job_id,),
        accept_job_id=next_job_id + 1,
    )
    assert completed.diagnostic is None
    return next_job_id, waiting_writer.job_id


def _review_context(
    scenario: _Scenario,
    started: StartJobResult,
    review_input: _ReviewInput,
) -> tuple[dict[str, object], dict[str, object]]:
    builder_path = _REPO_ROOT / "share" / "agents" / "builder.agent.md"
    reviewer_path = _REPO_ROOT / "share" / "agents" / "build-reviewer.agent.md"
    workflow_path = _REPO_ROOT / "share" / "skills" / "w-packet-building" / "SKILL.md"
    orchestration_path = _REPO_ROOT / "share" / "skills" / "w-orchestration" / "SKILL.md"
    builder = _frontmatter(builder_path)
    reviewer = _frontmatter(reviewer_path)
    workflow = workflow_path.read_text(encoding="utf-8")
    orchestration = orchestration_path.read_text(encoding="utf-8")

    assert builder["agents"] == ["builder-challenger", "build-reviewer"]
    assert "w-packet-building" in builder_path.read_text(encoding="utf-8")
    assert not any("finish_build" in tool or "release_job" in tool for tool in builder["tools"])
    assert reviewer["hooks"]["PreToolUse"][0]["command"].endswith("deny-writes.py")
    assert reviewer["model"] != builder["model"]
    assert "Return exactly one of these objects to the orchestrator" in workflow
    assert "create a scoped repair commit" in workflow
    assert 'runSubagent(agentName="builder")' in orchestration
    assert "inspect, reconstruct, or supplement those returned fields" in orchestration

    changed_paths = _git(
        scenario.repository,
        "diff",
        "--name-only",
        f"{review_input.base_revision}..{review_input.code_revision}",
    ).splitlines()
    target = scenario.revision.resolve(started.job.job.target_node_id)
    context = {
        "execution": {
            "change_id": _CHANGE_ID,
            "delivery_digest": started.job.job.delivery_digest,
            "target_node_id": started.job.job.target_node_id,
            "packet_id": f"{target.id}-PK-001",
            "node_plan_digest": started.job.job.node_plan_digest,
            "job_id": started.job.job.job_id,
            "attempt_id": started.job.job.attempt_id,
            "claim_id": started.job.job.claim_id,
        },
        "authority": {
            "node": target.id,
            "obligations": [*target.owns, *target.supports],
            "interfaces": [*target.produces, *target.consumes],
            "proof": target.proof,
        },
        "envelope": {
            "required_outputs": ["sample/module.py", "review evidence"],
            "excluded": [f"authority and work outside {target.id}"],
            "dependencies": [],
            "impact_closure": {
                "paths": ["sample/module.py"],
                "authority_targets": [target.id, target.proof],
            },
        },
        "change": {
            "base_revision": review_input.base_revision,
            "code_revision": review_input.code_revision,
            "diff": _git(
                scenario.repository,
                "diff",
                f"{review_input.base_revision}..{review_input.code_revision}",
            ),
            "changed_paths": changed_paths,
        },
        "proof": {
            "command": "python -c import sample.module; assert sample.module.outcome() == 'reviewed'",
            "exit_code": review_input.proof.returncode,
            "stdout": review_input.proof.stdout,
            "stderr": review_input.proof.stderr,
            "evidence_ids": [f"proof-{review_input.code_revision[:12]}"],
        },
        "custody": {"scoped_commit": review_input.code_revision, "unrelated_state_preserved": True},
        "prior_findings": review_input.prior_findings,
    }
    required_context = ("authority", "envelope", "change", "proof", "custody")
    assert all(context[key] for key in required_context)
    assert context["change"]["diff"]
    assert changed_paths == ["sample/module.py"]

    finding = {
        "finding_class": "implementation-defect",
        "target": "sample/module.py",
        "finding": "packet outcome does not return reviewed",
        "evidence": review_input.proof.stderr or "deterministic proof exited non-zero",
    }
    review = {
        "authority_and_packet": {"disposition": "pass", "evidence": f"{target.id} packet contract present"},
        "diff_and_changed_paths": {"disposition": "pass", "evidence": "one scoped sample path"},
        "proof": {
            "disposition": "pass" if review_input.proof.returncode == 0 else "error",
            "evidence": f"deterministic runner exit {review_input.proof.returncode}",
        },
        "commit_context": {"disposition": "pass", "evidence": review_input.code_revision},
        "scope": {"disposition": "pass", "evidence": "no escaped path"},
        "findings": [] if review_input.proof.returncode == 0 else [finding],
    }
    return context, review


def _proof(repository: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        repository,
        "python",
        "-c",
        "import sample.module; assert sample.module.outcome() == 'reviewed'",
        check=False,
    )


def _assert_reviewer_write_denied() -> None:
    hook = _REPO_ROOT / ".owlbear" / "hooks" / "deny-writes.py"
    payload = {
        "tool_name": "apply_patch",
        "tool_input": {"input": "*** Begin Patch\n*** Update File: sample/module.py\n*** End Patch"},
    }
    denied = subprocess.run(  # noqa: S603
        ["python", str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        cwd=_REPO_ROOT,
    )
    response = json.loads(denied.stdout)
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"


def _run_local_repair(scenario: _Scenario, started: StartJobResult) -> _RepairOutcome:
    sample = scenario.repository / "sample" / "module.py"
    sample.parent.mkdir()
    sample.write_text('def outcome() -> str:\n    return "wrong"\n', encoding="utf-8")
    first_commit = commit_owned_paths(
        cwd=scenario.repository,
        message="feat: implement sample packet",
        paths=("sample/module.py",),
    )
    first_context, first_review = _review_context(
        scenario,
        started,
        _ReviewInput(scenario.base_revision, first_commit, _proof(scenario.repository), []),
    )
    assert first_review["findings"][0]["finding_class"] == "implementation-defect"
    assert first_context["custody"]["scoped_commit"] == first_commit
    missing_receipt = ReceiptStore(scenario.revision).read("build-proof-006-builder")
    assert missing_receipt.receipt is None
    assert missing_receipt.diagnostics[0].code is ReceiptDiagnosticCode.FILE_MISSING
    _assert_reviewer_write_denied()

    sample.write_text('def outcome() -> str:\n    return "reviewed"\n', encoding="utf-8")
    repair_commit = commit_owned_paths(
        cwd=scenario.repository,
        message="fix: repair reviewed packet outcome",
        paths=("sample/module.py",),
    )
    repaired_context, repaired_review = _review_context(
        scenario,
        started,
        _ReviewInput(scenario.base_revision, repair_commit, _proof(scenario.repository), first_review["findings"]),
    )
    return _RepairOutcome(first_context, first_review, repaired_context, repaired_review, repair_commit)


@pytest.mark.asyncio
async def test_native_builder_repairs_local_finding_before_public_receipt(scenario: _Scenario) -> None:
    build_job_id, waiting_writer_id = await _publish_target_plan(scenario)
    planned = await server.pick_jobs(
        scenario.context,
        change_id=_CHANGE_ID,
        candidate_revision=scenario.base_revision,
        wave_size=len(scenario.revision.graph.nodes),
    )
    build_entries = [entry for wave in planned.waves for entry in wave if entry.job_id == build_job_id]
    assert build_entries, planned
    build_entry = build_entries[0]
    assert build_entry.kind == "build"
    assert build_entry.agent_profile == "builder"

    build_start = _start_arguments(build_job_id, 2, "2026-07-25T01:02:00Z", scenario.base_revision)
    started = await server.start_job(scenario.context, **build_start)
    assert started.diagnostic is None
    assert started.job is not None
    assert started.job.job.job_id == build_job_id
    assert started.job.job.delivery_digest == scenario.revision.delivery_digest
    assert started.job.job.node_plan_digest is not None
    assert started.job.job.claim_id == build_start["claim_id"]

    waiting_start = _start_arguments(waiting_writer_id, 3, "2026-07-25T01:03:00Z", scenario.base_revision)
    conflict = await server.start_job(scenario.context, **waiting_start)
    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (build_job_id,)

    repair = _run_local_repair(scenario, started)
    assert repair.repaired_review["findings"] == []
    assert all(row["disposition"] == "pass" for row in repair.repaired_review.values() if isinstance(row, dict))
    assert repair.repaired_context["prior_findings"] == repair.first_review["findings"]
    assert repair.repaired_context["change"]["code_revision"] == repair.repair_commit
    assert repair.first_context["change"] != repair.repaired_context["change"]

    target = scenario.revision.resolve(started.job.job.target_node_id)
    target_proof = scenario.revision.resolve(target.proof)
    finish = {
        "receipt_id": "build-proof-006-builder",
        "code_revision": repair.repair_commit,
        "evidence": {
            "methods": list(target_proof.method),
            "context": repair.repaired_context,
            "review": repair.repaired_review,
        },
        "evidence_ids": tuple(repair.repaired_context["proof"]["evidence_ids"]),
        "impact_closure": repair.repaired_context["envelope"]["impact_closure"],
    }
    before_events = len(AttemptStore(scenario.board).list())
    completed = await server.finish_build(
        scenario.context,
        **_finish_identity(build_start),
        finished_at="2026-07-25T01:04:00Z",
        **finish,
    )
    assert completed.diagnostic is None
    assert completed.receipt is not None
    assert completed.receipt.payload["code_revision"] == repair.repair_commit
    assert completed.receipt.payload["node_plan_digest"] == started.job.job.node_plan_digest
    expected_evidence = json.loads(json.dumps(finish["evidence"]))
    assert completed.receipt.to_mapping()["evidence"] == expected_evidence
    assert completed.receipt.impact_closure is not None
    assert completed.receipt.impact_closure.model_dump(mode="json") == finish["impact_closure"]
    persisted = ReceiptStore(scenario.revision).read("build-proof-006-builder")
    assert persisted.receipt == completed.receipt

    replayed = await server.finish_build(
        scenario.context,
        **_finish_identity(build_start),
        finished_at="2026-07-25T01:04:00Z",
        **finish,
    )
    assert replayed.receipt == completed.receipt
    assert replayed.event == completed.event
    assert len(AttemptStore(scenario.board).list()) == before_events + 1

    waiting_started = await server.start_job(scenario.context, **waiting_start)
    assert not isinstance(waiting_started, DispatchDiagnostic)
    assert waiting_started.diagnostic is None
    released = await server.release_job(
        scenario.context,
        **_finish_identity(waiting_start),
        released_at="2026-07-25T01:05:00Z",
    )
    assert released.diagnostic is None
