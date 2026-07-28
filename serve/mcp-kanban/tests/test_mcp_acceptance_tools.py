from __future__ import annotations

import asyncio
import json
import re
import shutil
import stat
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import (
    AttemptStore,
    CorrectiveRouteRequest,
    DispatchDiagnostic,
    DispatchDiagnosticCode,
    DispatchRuntime,
    Finding,
    FindingStore,
    GitRepositoryHistory,
    InvalidationRequest,
    JobGeneration,
    JobDisposition,
    JobRecord,
    JobStore,
    NativeRuntime,
    NativeWorkspace,
    PlanJob,
    ProofCheckoutManager,
    ReleaseJobRequest,
    RejectAcceptDiagnosticCode,
    ReceiptStore,
    StartJobDiagnosticCode,
    WHOLE_CHANGE_AUDIT_COMMAND,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext
from serve.kanban.tests.test_native_runtime import (
    _active_audit_scenario,
    _reject_audit_request,
    _terminal_accept_scenario,
)

from .test_mcp_surface_contract import _make_work_root


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_state(checkout: Path) -> dict[str, str]:
    def inspect(*arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(checkout), *arguments],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    return {
        "head": inspect("rev-parse", "--verify", "HEAD").strip(),
        "status": inspect("status", "--porcelain=v1", "--untracked-files=no"),
        "diff": inspect("diff", "--binary", "HEAD", "--"),
    }


def _frontmatter(path: Path) -> dict[str, object]:
    metadata = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
    assert isinstance(metadata, dict)
    return metadata


def _workflow_text() -> str:
    return Path("share/skills/w-node-acceptance/SKILL.md").read_text(encoding="utf-8")


def _audit_workflow_text() -> str:
    return Path("share/skills/w-whole-change-audit/SKILL.md").read_text(encoding="utf-8")


def _audit_classification(scenario: str) -> tuple[str, str]:
    row = next(line for line in _audit_workflow_text().splitlines() if line.startswith(f"| {scenario} |"))
    _empty, _scenario, finding_class, corrective_target, _empty = (item.strip() for item in row.split("|"))
    return finding_class.strip("`"), corrective_target.strip("`")


def _orchestration_text() -> str:
    return Path("share/skills/w-orchestration/SKILL.md").read_text(encoding="utf-8")


def _markdown_subsection(content: str, heading: str) -> str:
    section = content.split(heading, 1)[1]
    return section.split("\n### `", 1)[0]


def _yaml_code_block(content: str) -> dict[str, object]:
    payload = content.split("```yaml", 1)[1].split("```", 1)[0]
    parsed = yaml.safe_load(payload)
    assert isinstance(parsed, dict)
    return parsed


def _assert_acceptor_write_denied(checkout: Path) -> None:
    hook = checkout / ".owlbear" / "hooks" / "deny-writes.py"
    payload = {
        "tool_name": "execute/runInTerminal",
        "tool_input": {"command": "printf changed > README.md"},
    }
    denied = subprocess.run(
        [sys.executable, str(hook), "--terminal-read-only"],
        cwd=checkout,
        input=json.dumps(payload),
        check=True,
        capture_output=True,
        text=True,
    )
    response = json.loads(denied.stdout)
    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    with pytest.raises(PermissionError):
        (checkout / "README.md").write_text("changed\n", encoding="utf-8")


_ACCEPTANCE_FAILURES = (
    (
        "local defect",
        "implementation-defect",
        "packet",
        "DN-001-PK-001",
        "packet-implementation",
        "build-repair",
        False,
        ("build",),
    ),
    (
        "missing harness",
        "planning-omission",
        "proof",
        "PROOF-001",
        "packet-proof-plan",
        "node-plan-revision",
        False,
        ("plan",),
    ),
    (
        "boundary bypass",
        "planning-omission",
        "proof",
        "PROOF-001",
        "admitted-design-authority",
        "design-reentry",
        True,
        (),
    ),
    (
        "stale receipt",
        "implementation-defect",
        "receipt",
        "build-001",
        "packet-dependency",
        "node-plan-revision",
        False,
        ("plan",),
    ),
)


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
    board = _make_work_root(tmp_path)
    _materialize_plan(revision, board)
    repository = Path.cwd()
    commit = _git_head()
    checkouts = ProofCheckoutManager(repository, tmp_path / "proof", changes_dir)
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
    app_ctx = AppContext(workspace=NativeWorkspace(board, timedelta(hours=1)))
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
            "mode": "build",
            "packets": [
                {"id": f"{target.id}-PK-001", "dependencies": [], "impact_closure": closure},
                {
                    "id": f"{target.id}-PK-002",
                    "dependencies": [f"{target.id}-PK-001"],
                    "impact_closure": closure,
                },
            ],
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

    picked = await server.pick_jobs(
        ctx,
        change_id=revision.change_id,
        candidate_revision=commit,
        wave_size=2,
    )
    selected = [entry for wave in picked.waves for entry in wave]
    assert [(entry.job_id, entry.agent_profile) for entry in selected] == [(4, "acceptor")]

    accept_start = _start(4, 4, commit)
    started = await server.start_job(ctx, **accept_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    checkout = started["checkout"]
    assert checkout.commit == commit
    return revision, board, ctx, runtime, checkout, accept_start, commit


def _materialize_waiting_writer(revision, board: Path, *, job_id: int = 6) -> JobRecord:
    target = revision.graph.nodes[0]
    dependent = next(node for node in revision.graph.nodes if target.id in node.dependencies)
    writer = JobRecord(
        schema_version=1,
        job_id=job_id,
        kind="plan",
        priority=7,
        created_at="2026-07-25T00:05:00Z",
        updated_at="2026-07-25T00:05:00Z",
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_node_id=dependent.id,
    )
    RuntimeTransaction(board, "accept-proof-writer", (JobStore(board).create_participant(writer),)).commit()
    return writer


async def _auditor_evidence(
    revision,
    ctx,
    checkout,
    start: dict[str, object],
    accept_receipt_ids: tuple[str, ...],
) -> dict[str, object]:
    checkout_root = checkout.checkout
    agent = _frontmatter(checkout_root / "share/agents/auditor.agent.md")
    tools = agent["tools"]
    assert isinstance(tools, list)
    assert agent["hooks"]["PreToolUse"][0]["command"].endswith("deny-writes.py --terminal-read-only")
    assert not any(
        operation in tool
        for operation in ("start_job", "finish_audit", "reject_audit", "release_job")
        for tool in tools
    )
    assert (checkout_root / "share/skills/w-whole-change-audit/SKILL.md").is_file()

    change = await server.show_change(ctx, change_id=revision.change_id)
    shown_job = await server.show_job(ctx, change_id=revision.change_id, job_id=int(start["job_id"]))
    receipts = [
        await server.show_receipt(ctx, change_id=revision.change_id, receipt_id=receipt_id)
        for receipt_id in accept_receipt_ids
    ]
    requests = await server.list_requests(
        ctx,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        status="pending",
    )
    job = shown_job["job"]
    proof_id = revision.resolve(job.target_node_id).proof
    proof = revision.resolve(proof_id)
    tracked_state = _git_state(checkout_root)

    assert change["delivery_digest"] == revision.delivery_digest == job.delivery_digest
    assert change["intent"] == revision.intent
    assert change["design"] == revision.design
    assert change["decisions"] == revision.decisions.model_dump(mode="python")
    assert proof_id == "PROOF-008"
    assert requests == []
    assert tracked_state == {"head": checkout.commit, "status": "", "diff": ""}
    accepted_mappings = tuple(receipt.to_mapping() for receipt in receipts)
    probe_script = (
        "import json,sys; from pathlib import Path; "
        "sys.path.insert(0,str(Path('serve/kanban/src').resolve())); "
        "from owlbear_kanban import load_change, whole_change_audit_report; "
        "result=load_change(Path('.owlbear/changes'), 'replace-delivery-pipeline'); "
        "assert result.revision is not None; "
        f"report=whole_change_audit_report(result.revision, {accepted_mappings!r}); "
        "print(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=False))"
    )
    command_arguments = (sys.executable, "-I", "-c", probe_script)
    command = WHOLE_CHANGE_AUDIT_COMMAND
    process = await asyncio.create_subprocess_exec(
        *command_arguments,
        cwd=checkout_root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode == 0, (stdout + stderr).decode()
    return {
        "methods": list(proof.method),
        "product_promise": change["intent"],
        "accepted_decisions": revision.decisions.model_dump(mode="json"),
        "migrations": [item.model_dump(mode="json") for item in revision.graph.migrations],
        "admitted_workflows": [item.model_dump(mode="json") for item in revision.graph.workflows],
        "accepted_receipts": [receipt.to_mapping() for receipt in receipts],
        "proof": proof.model_dump(mode="json"),
        "allowed_replacements": list(proof.allowed_replacements),
        "pending_requests": [],
        "assembled_proof": {
            "boundary": proof.boundary,
            "durable_outputs": list(proof.durable_outputs),
            "commands": [command],
            "results": [{"command": command, "exit_code": process.returncode, "result": stdout.decode()}],
        },
        "before_tracked_state": tracked_state,
        "after_tracked_state": _git_state(checkout_root),
    }


async def _assert_audit_blocks_writer(revision, board: Path, ctx, audit_job_id: int, commit: str) -> None:
    waiting_writer = _materialize_waiting_writer(revision, board, job_id=audit_job_id + 1)
    conflict = await server.start_job(ctx, **_start(waiting_writer.job_id, 7, commit))
    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (audit_job_id,)


async def _finish_terminal_accept(ctx, revision, accept_request) -> JobRecord:
    fields = accept_request.model_dump(mode="python")
    accepted = await server.finish_accept(ctx, change_id=revision.change_id, **fields)
    replayed = await server.finish_accept(ctx, change_id=revision.change_id, **fields)
    assert accepted.diagnostic is None
    assert len(accepted.created_jobs) == 1
    assert replayed == accepted
    return accepted.created_jobs[0]


async def _restart_terminal_accept(ctx, revision, native, accept_request, commit: str):
    released = native.release_job(
        ReleaseJobRequest(
            job_id=accept_request.job_id,
            attempt_id=accept_request.attempt_id,
            claim_id=accept_request.claim_id,
            actor_id=accept_request.actor_id,
            process_id=accept_request.process_id,
            released_at="2026-07-24T00:59:00Z",
        )
    )
    assert released.diagnostic is None
    restarted = accept_request.model_copy(
        update={"attempt_id": "attempt-final-public", "claim_id": "claim-final-public"}
    )
    started = await server.start_job(
        ctx,
        change_id=revision.change_id,
        job_id=restarted.job_id,
        attempt_id=restarted.attempt_id,
        claim_id=restarted.claim_id,
        actor_id=restarted.actor_id,
        process_id=restarted.process_id,
        claimed_at="2026-07-24T00:59:30Z",
        candidate_revision=commit,
    )
    assert started["start"].diagnostic is None
    return restarted


def _acceptance_failure_disposition(
    revision,
    checkout,
    start: dict[str, object],
    commit: str,
    case: tuple[object, ...],
):
    name, expected_class, expected_kind, expected_id, route_target, route_kind, _design_reentry, _job_kinds = case
    target = revision.resolve("DN-001")
    proof = revision.resolve(target.proof)
    if name == "local defect":
        observed = subprocess.run(
            [sys.executable, "-c", "raise SystemExit(17)"],
            cwd=checkout.checkout,
            check=False,
            capture_output=True,
            text=True,
        )
        assert observed.returncode == 17
        finding_class, target_kind, target_id = "implementation-defect", "packet", "DN-001-PK-001"
        detail = f"assembled packet command failed with exit {observed.returncode} at {commit}"
    elif name == "missing harness":
        plan = revision.read_node_plan(target.id)
        assert "harness" not in plan
        finding_class, target_kind, target_id = "planning-omission", "proof", proof.id
        detail = f"required local harness is absent from {target.id} node plan at {commit}"
    elif name == "boundary bypass":
        replacement = "finish_accept public boundary"
        assert replacement not in proof.allowed_replacements
        finding_class, target_kind, target_id = "planning-omission", "proof", proof.id
        detail = f"replacement bypasses admitted {proof.id} boundary at {commit}"
    else:
        validity = ReceiptStore(revision).evaluate_currentness(
            "build-001",
            GitRepositoryHistory(Path.cwd()),
            "f" * 40,
        )
        assert not validity.current
        finding_class, target_kind, target_id = "implementation-defect", "receipt", "build-001"
        detail = f"build-001 is not current: {validity.code.value}"

    assert (finding_class, target_kind, target_id) == (expected_class, expected_kind, expected_id)
    workflow = _workflow_text()
    row = next(line for line in workflow.splitlines() if f"`{route_target}`" in line)
    assert f"`{finding_class}`" in row
    assert f"`{target_kind}`" in row
    assert f"`{route_kind}`" in row
    finding = Finding(
        schema_version=1,
        finding_id=f"finding-{str(name).replace(' ', '-')}",
        source_attempt_id=str(start["attempt_id"]),
        source_job_id=int(start["job_id"]),
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind=target_kind,
        target_id=target_id,
        finding_class=finding_class,
        detail=detail,
        created_at="2026-07-25T00:06:00Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target=route_target,
            target_node_ids=("DN-001",),
            packet_id=target_id if route_target in {"packet-implementation", "packet-local-proof"} else None,
        )
    )
    return finding, route, (f"evidence-{str(name).replace(' ', '-')}",)


def _create_unrelated_receipt(revision) -> bytes:
    receipts = ReceiptStore(revision)
    source = receipts.read("build-002").receipt
    assert source is not None
    mapping = source.to_mapping() | {"receipt_id": "build-unrelated", "predecessor_receipt_ids": []}
    assert receipts.create("build-unrelated", mapping).receipt is not None
    return (revision.source_dir / "receipts/build-unrelated.yaml").read_bytes()


async def _acceptor_evidence(revision, ctx, checkout, start: dict[str, object], commit: str) -> dict[str, object]:
    checkout_root = checkout.checkout
    agent_path = checkout_root / "share" / "agents" / "acceptor.agent.md"
    workflow_path = checkout_root / "share" / "skills" / "w-node-acceptance" / "SKILL.md"
    agent = _frontmatter(agent_path)
    workflow = workflow_path.read_text(encoding="utf-8")
    tools = agent["tools"]
    assert isinstance(tools, list)
    assert agent["hooks"]["PreToolUse"][0]["command"].endswith("deny-writes.py --terminal-read-only")
    assert not any(
        operation in tool
        for operation in ("start_job", "finish_accept", "reject_accept", "release_job")
        for tool in tools
    )
    assert "These fields map unchanged to `finish_accept`." in workflow
    assert "After every proof command and before returning a disposition" in workflow

    change = await server.show_change(ctx, change_id=revision.change_id)
    shown_job = await server.show_job(ctx, change_id=revision.change_id, job_id=int(start["job_id"]))
    receipts = [
        await server.show_receipt(ctx, change_id=revision.change_id, receipt_id=receipt_id)
        for receipt_id in ("build-001", "build-002")
    ]
    job = shown_job["job"]
    target = revision.resolve(job.target_node_id)
    proof = revision.resolve(target.proof)
    plan = revision.read_node_plan(target.id)
    before = _git_state(checkout_root)
    assert change["delivery_digest"] == revision.delivery_digest == job.delivery_digest
    assert job.attempt_id == start["attempt_id"]
    assert job.claim_id == start["claim_id"]
    assert job.node_plan_digest is not None
    packets = plan["packets"]
    assert isinstance(packets, list)
    assert tuple(packet["id"] for packet in packets) == ("DN-001-PK-001", "DN-001-PK-002")
    assert [receipt.payload["code_revision"] for receipt in receipts] == [commit, commit]
    assert before == {"head": commit, "status": "", "diff": ""}

    _assert_acceptor_write_denied(checkout_root)
    probe_script = (
        "from pathlib import Path; "
        "from owlbear_kanban import ReceiptStore, load_change; "
        "result=load_change(Path('.owlbear/changes'), 'replace-delivery-pipeline'); "
        "assert result.revision is not None; "
        "print(result.revision.delivery_digest, len(ReceiptStore(result.revision).list()))"
    )
    command_arguments = (
        "uv",
        "run",
        "python",
        "-c",
        probe_script,
    )
    command = " ".join(command_arguments[:3]) + " -c <assembled ChangeRevision + ReceiptStore probe>"
    process = await asyncio.create_subprocess_exec(
        *command_arguments,
        cwd=checkout_root,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode == 0, (stdout + stderr).decode()
    after = _git_state(checkout_root)
    assert after == before
    interface_ids = tuple(sorted((*target.produces, *target.consumes)))
    migration_ids = tuple(
        sorted(
            {
                interface.migration
                for interface_id in interface_ids
                if (interface := revision.resolve(interface_id)).migration is not None
            }
            | {item_id for item_id in target.owns if item_id.startswith("MIG-")}
        )
    )
    return {
        "methods": list(proof.method),
        "assembled_proof": {
            "boundary": proof.boundary,
            "durable_outputs": list(proof.durable_outputs),
            "commands": [command],
            "results": [
                {
                    "command": command,
                    "exit_code": process.returncode,
                    "result": stdout.decode(),
                }
            ],
        },
        "authority": {
            "delivery_digest": revision.delivery_digest,
            "target_node_id": target.id,
            "acceptance": list(shown_job["acceptance"]),
            "proof": target.proof,
            "node_contract": target.model_dump(mode="json"),
            "modules": list(target.modules),
            "interfaces": list(interface_ids),
            "migrations": list(migration_ids),
            "risks": list(target.risks),
        },
        "plan": {
            "node_plan_digest": job.node_plan_digest,
            "packet_ids": [packet["id"] for packet in packets],
        },
        "packet_receipts": [
            {"receipt_id": receipt.receipt_id, "code_revision": receipt.payload["code_revision"]}
            for receipt in receipts
        ],
        "changed_surfaces": {
            "paths": ["serve/kanban/"],
            "authority_targets": [target.id, target.proof],
        },
        "checkout": {"root": str(checkout_root), "candidate_sha": commit},
        "replacements": [],
        "tracked_state": {"before": before, "after": after},
    }


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
            packet_id=finding.target_id,
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
        "replacement_accept_job_id": 21,
    }


@pytest.mark.parametrize("case", _ACCEPTANCE_FAILURES, ids=[str(case[0]) for case in _ACCEPTANCE_FAILURES])
@pytest.mark.asyncio
async def test_shipped_acceptor_routes_canonical_minimum_correction(tmp_path: Path, case: tuple[object, ...]) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)

    finding, route, evidence_ids = _acceptance_failure_disposition(revision, checkout, start, commit, case)
    corrective_job_ids = tuple(range(20, 20 + len(route.jobs)))
    invalidation = InvalidationRequest(
        invalidation_id=f"invalidation-{finding.finding_id}",
        supersession_receipt_id=f"supersession-{finding.finding_id}",
        invalidated_receipt_ids=("build-001",),
        routes=(route,),
        corrective_job_ids=corrective_job_ids,
        issued_at=finding.created_at,
        code_revision=commit,
        priority=9,
    )

    payload = {
        **_identity(start),
        "rejected_at": finding.created_at,
        "detail": finding.detail,
        "evidence_ids": evidence_ids,
        "findings": (finding.model_dump(mode="json"),),
        "invalidation": invalidation.model_dump(mode="json"),
    }
    if route.jobs and all(job.kind == "build" for job in route.jobs):
        payload["replacement_accept_job_id"] = corrective_job_ids[-1] + 1
    rejected = await server.reject_accept(ctx, **payload)
    replayed = await server.reject_accept(ctx, **payload)

    assert finding.finding_class == case[1]
    assert (finding.target_kind, finding.target_id) == (case[2], case[3])
    assert evidence_ids == (f"evidence-{str(case[0]).replace(' ', '-')}",)
    assert route.route == case[5]
    assert route.design_reentry is case[6]
    assert tuple(job.kind for job in route.jobs) == case[7]
    assert len(route.jobs) <= 1
    assert rejected.diagnostic is None
    assert replayed == rejected
    assert rejected.findings == (finding,)
    assert rejected.invalidation is not None
    assert tuple(item.job.job_id for item in rejected.invalidation.corrective_jobs) == corrective_job_ids
    assert tuple(item.job.kind for item in rejected.invalidation.corrective_jobs) == case[7]
    assert FindingStore(board).read(finding.finding_id).finding == finding
    assert not checkout.root.exists()
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_replacement_accept_waits_for_every_corrective_build(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    routes = []
    findings = []
    for index, packet_id in enumerate(("DN-001-PK-001", "DN-001-PK-002"), start=1):
        finding = Finding(
            schema_version=1,
            finding_id=f"finding-accept-{index:03}",
            source_attempt_id=str(start["attempt_id"]),
            source_job_id=int(start["job_id"]),
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            target_kind="packet",
            target_id=packet_id,
            finding_class="implementation-defect",
            detail=f"{packet_id} requires corrective implementation",
            created_at="2026-07-25T00:06:00Z",
        )
        findings.append(finding)
        routes.append(
            plan_corrective_route(
                CorrectiveRouteRequest(
                    finding_id=finding.finding_id,
                    finding_class=finding.finding_class,
                    target="packet-implementation",
                    target_node_ids=("DN-001",),
                    packet_id=packet_id,
                )
            )
        )
    rejected = await server.reject_accept(
        ctx,
        **_identity(start),
        rejected_at="2026-07-25T00:06:00Z",
        detail="acceptance found two implementation defects",
        evidence_ids=("accept-proof-001",),
        findings=tuple(finding.model_dump(mode="json") for finding in findings),
        invalidation=InvalidationRequest(
            invalidation_id="invalidation-accept-001",
            supersession_receipt_id="supersession-accept-001",
            invalidated_receipt_ids=("build-001", "build-002"),
            routes=tuple(routes),
            corrective_job_ids=(20, 21),
            issued_at="2026-07-25T00:06:00Z",
            code_revision=commit,
            priority=9,
        ).model_dump(mode="json"),
        replacement_accept_job_id=22,
    )

    assert rejected.diagnostic is None
    assert rejected.replacement_accept is not None
    replacement = rejected.replacement_accept.job
    assert replacement.predecessor_job_ids == (20, 21)
    assert replacement.node_plan_digest == JobStore(board).read(20).job.node_plan_digest
    assert replacement.receipt_id is None
    assert not checkout.root.exists()

    proof = revision.resolve(revision.resolve("DN-001").proof)
    plan = revision.read_node_plan("DN-001")
    for offset, corrective_job_id in enumerate((20, 21), start=7):
        picked = await server.pick_jobs(
            ctx,
            change_id=revision.change_id,
            candidate_revision=commit,
            wave_size=3,
        )
        selected_ids = {entry.job_id for wave in picked.waves for entry in wave}
        assert 22 not in selected_ids
        corrective_start = _start(corrective_job_id, offset, commit)
        assert (await server.start_job(ctx, **corrective_start)).diagnostic is None
        packet_id = JobStore(board).read(corrective_job_id).job.packet_id
        packet = next(item for item in plan["packets"] if item["id"] == packet_id)
        finished = await server.finish_build(
            ctx,
            **_identity(corrective_start),
            finished_at=f"2026-07-25T00:{offset + 2:02}:00Z",
            receipt_id=f"build-corrected-{offset}",
            code_revision=commit,
            evidence={"methods": list(proof.method)},
            impact_closure=packet["impact_closure"],
        )
        assert finished.diagnostic is None

    resumed = await server.pick_jobs(
        ctx,
        change_id=revision.change_id,
        candidate_revision=commit,
        wave_size=3,
    )
    selected = [entry for wave in resumed.waves for entry in wave]
    assert [(entry.job_id, entry.agent_profile) for entry in selected] == [(22, "acceptor")]
    replacement_start = _start(22, 9, commit)
    started = await server.start_job(ctx, **replacement_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None


@pytest.mark.asyncio
async def test_public_accept_success_is_independent_exact_and_replay_safe(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    waiting_writer = _materialize_waiting_writer(revision, board)
    waiting_start = _start(waiting_writer.job_id, 5, commit)
    conflict = await server.start_job(ctx, **waiting_start)
    assert isinstance(conflict, DispatchDiagnostic)
    assert conflict.code is DispatchDiagnosticCode.WRITER_CONFLICT
    assert conflict.holder_job_ids == (start["job_id"],)

    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)
    closure = evidence["changed_surfaces"]
    finish = {
        "finished_at": "2026-07-25T00:06:00Z",
        "receipt_id": "accept-001",
        "code_revision": commit,
        "evidence": evidence,
        "evidence_ids": ("accept-contract-001", "accept-read-only-001"),
        "impact_closure": closure,
        "reconciliation_plan_job_ids": (6, 7),
    }
    events_before = len(AttemptStore(board).list())
    accepted = await server.finish_accept(ctx, **_identity(start), **finish)
    assert accepted.diagnostic is None
    assert accepted.receipt is not None
    assert accepted.receipt.payload["code_revision"] == commit
    assert accepted.receipt.payload["predecessor_receipt_ids"] == ("build-001", "build-002")
    assert accepted.receipt.to_mapping()["evidence"] == json.loads(json.dumps(evidence))
    assert accepted.receipt.impact_closure is not None
    assert accepted.receipt.impact_closure.model_dump(mode="json") == closure
    assert accepted.event is not None
    assert accepted.event.kind == "succeeded"
    assert not checkout.root.exists()
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    plans = [item.job for item in JobStore(board).list() if item.job.kind == "plan" and item.job.job_id in (6, 7)]
    assert [(job.job_id, job.predecessor_job_ids) for job in plans] == [(6, (4,)), (7, (4,))]

    state_after_accept = _snapshot(board)
    replayed = await server.finish_accept(ctx, **_identity(start), **finish)
    assert replayed == accepted
    assert _snapshot(board) == state_after_accept
    assert len(AttemptStore(board).list()) == events_before + 1
    shown = await server.show_receipt(ctx, change_id=revision.change_id, receipt_id="accept-001")
    assert shown == accepted.receipt


@pytest.mark.asyncio
async def test_public_accept_rejects_methods_only_evidence_without_cleanup(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    proof = revision.resolve(revision.resolve("DN-001").proof)

    result = await server.finish_accept(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:06:00Z",
        receipt_id="accept-methods-only",
        code_revision=commit,
        evidence={"methods": list(proof.method)},
        evidence_ids=("accept-methods-only",),
        reconciliation_plan_job_ids=(6, 7),
    )

    assert result.diagnostic is not None
    assert result.diagnostic.code.value == "ERR_FINISH_EVIDENCE_INVALID"
    assert result.diagnostic.lower_code == "ERR_RECEIPT_PROOF_UNSATISFIED"
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/accept-methods-only.yaml").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "proof",
        "node-contract",
        "modules",
        "interfaces",
        "migrations",
        "risks",
        "boundary",
        "durable-outputs",
        "replacements",
        "packets",
        "receipts",
        "surfaces",
    ],
)
@pytest.mark.asyncio
async def test_public_accept_rejects_forged_evidence_authority(tmp_path: Path, mutation: str) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)
    if mutation == "proof":
        evidence["authority"]["proof"] = "PROOF-999"
    elif mutation == "node-contract":
        evidence["authority"]["node_contract"]["outcome"] = "forged"
    elif mutation in {"modules", "interfaces", "migrations", "risks"}:
        evidence["authority"][mutation] = []
    elif mutation == "boundary":
        evidence["assembled_proof"]["boundary"] = "bypassed boundary"
    elif mutation == "durable-outputs":
        evidence["assembled_proof"]["durable_outputs"] = []
    elif mutation == "replacements":
        evidence["replacements"] = ["finish_accept public boundary"]
    elif mutation == "packets":
        evidence["plan"]["packet_ids"] = ["DN-001-PK-999"]
    elif mutation == "receipts":
        evidence["packet_receipts"] = [{"receipt_id": "forged-build", "code_revision": commit}]
    else:
        evidence["changed_surfaces"] = {"paths": ["serve/tools/"], "authority_targets": ["DN-001"]}

    result = await server.finish_accept(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:06:00Z",
        receipt_id=f"accept-forged-{mutation}",
        code_revision=commit,
        evidence=evidence,
        evidence_ids=(f"accept-forged-{mutation}",),
        impact_closure={"paths": ["serve/kanban/"], "authority_targets": ["DN-001", "PROOF-001"]},
        reconciliation_plan_job_ids=(6, 7),
    )

    assert result.diagnostic is not None
    assert result.diagnostic.lower_code == "ERR_RECEIPT_PROOF_UNSATISFIED"
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / f"receipts/accept-forged-{mutation}.yaml").exists()


@pytest.mark.asyncio
async def test_public_accept_rejects_symbolic_revision_authority(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)

    result = await server.finish_accept(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:06:00Z",
        receipt_id="accept-symbolic",
        code_revision="HEAD",
        evidence=evidence,
        evidence_ids=("accept-symbolic",),
        impact_closure=evidence["changed_surfaces"],
        reconciliation_plan_job_ids=(6, 7),
    )

    assert result.diagnostic is not None
    assert result.diagnostic.detail == "acceptance revision differs from dispatched checkout authority"
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/accept-symbolic.yaml").exists()


@pytest.mark.asyncio
async def test_public_accept_rejects_manifest_revision_tamper(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)
    manifest = yaml.safe_load(checkout.manifest.read_text(encoding="utf-8"))
    forged_commit = "f" * 40
    manifest["commit"] = forged_commit
    checkout.manifest.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    result = await server.finish_accept(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:06:00Z",
        receipt_id="accept-manifest-tamper",
        code_revision=forged_commit,
        evidence=evidence,
        evidence_ids=("accept-manifest-tamper",),
        impact_closure=evidence["changed_surfaces"],
        reconciliation_plan_job_ids=(6, 7),
    )

    assert result.diagnostic is not None
    assert result.diagnostic.detail == "acceptance revision differs from dispatched checkout authority"
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/accept-manifest-tamper.yaml").exists()


@pytest.mark.asyncio
async def test_public_accept_cleanup_failure_replays_cleanup_after_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, board, ctx, runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)
    finish = {
        "finished_at": "2026-07-25T00:06:00Z",
        "receipt_id": "accept-cleanup-replay",
        "code_revision": commit,
        "evidence": evidence,
        "evidence_ids": ("accept-cleanup-replay",),
        "impact_closure": evidence["changed_surfaces"],
        "reconciliation_plan_job_ids": (6, 7),
    }
    manager = runtime._proof_checkouts  # noqa: SLF001 - exercise cleanup recovery at the assembled runtime boundary.
    assert manager is not None
    cleanup = manager.cleanup

    def fail_cleanup(_job_id: int) -> None:
        raise OSError

    monkeypatch.setattr(manager, "cleanup", fail_cleanup)
    first = await server.finish_accept(ctx, **_identity(start), **finish)
    assert isinstance(first, DispatchDiagnostic)
    assert first.code is DispatchDiagnosticCode.LEASE_STALE
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"]), archived=True).job.receipt_id == "accept-cleanup-replay"

    monkeypatch.setattr(manager, "cleanup", cleanup)
    replayed = await server.finish_accept(ctx, **_identity(start), **finish)
    assert replayed.diagnostic is None
    assert replayed.receipt is not None
    assert replayed.receipt.receipt_id == "accept-cleanup-replay"
    assert not checkout.root.exists()
    assert len([event for event in AttemptStore(board).list() if event.attempt_id == start["attempt_id"]]) == 2


@pytest.mark.asyncio
async def test_public_accept_rejects_tracked_checkout_mutation(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)
    tracked = checkout.checkout / "README.md"
    tracked.chmod(stat.S_IMODE(tracked.stat().st_mode) | stat.S_IWUSR)
    tracked.write_text("modified by acceptance\n", encoding="utf-8")

    result = await server.finish_accept(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:06:00Z",
        receipt_id="accept-mutated",
        code_revision=commit,
        evidence=evidence,
        evidence_ids=("accept-mutated",),
        impact_closure=evidence["changed_surfaces"],
        reconciliation_plan_job_ids=(6, 7),
    )

    assert result.diagnostic is not None
    assert result.diagnostic.lower_code == "ERR_PROOF_TRACKED_MUTATION"
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/accept-mutated.yaml").exists()

    finding = Finding(
        schema_version=1,
        finding_id="finding-accept-tracked-mutation",
        source_attempt_id=str(start["attempt_id"]),
        source_job_id=int(start["job_id"]),
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="packet",
        target_id="DN-001-PK-001",
        finding_class="implementation-defect",
        detail=f"{result.diagnostic.lower_code}: tracked checkout state changed at {commit}",
        created_at="2026-07-25T00:06:30Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="packet-implementation",
            target_node_ids=("DN-001",),
            packet_id=finding.target_id,
        )
    )
    rejected = await server.reject_accept(
        ctx,
        **_identity(start),
        rejected_at=finding.created_at,
        detail=finding.detail,
        evidence_ids=("accept-tracked-mutation",),
        findings=(finding.model_dump(mode="json"),),
        invalidation=InvalidationRequest(
            invalidation_id="invalidation-accept-tracked-mutation",
            supersession_receipt_id="supersession-accept-tracked-mutation",
            invalidated_receipt_ids=("build-001",),
            routes=(route,),
            corrective_job_ids=(20,),
            issued_at=finding.created_at,
            code_revision=commit,
            priority=9,
        ).model_dump(mode="json"),
        replacement_accept_job_id=21,
    )
    assert rejected.diagnostic is None
    assert rejected.findings == (finding,)
    assert rejected.invalidation is not None
    assert tuple(item.job.kind for item in rejected.invalidation.corrective_jobs) == ("build",)
    assert not checkout.root.exists()


@pytest.mark.asyncio
async def test_public_start_rejects_stale_checkout_at_different_revision(tmp_path: Path) -> None:
    revision, board, ctx, runtime, checkout, start, commit = await _active_accept(tmp_path)
    released = await server.release_job(
        ctx,
        **_identity(start),
        released_at="2026-07-25T00:06:00Z",
    )
    assert released.diagnostic is None
    manager = runtime._proof_checkouts  # noqa: SLF001 - arrange stale proof state at public dispatch boundary.
    assert manager is not None
    restored = manager.materialize(JobStore(board).read(int(start["job_id"])).job, commit)
    assert restored.checkout is not None
    other = _git_head()
    result = await server.start_job(
        ctx,
        change_id=revision.change_id,
        job_id=int(start["job_id"]),
        attempt_id="attempt-stale-checkout",
        claim_id="claim-stale-checkout",
        actor_id=str(start["actor_id"]),
        process_id=str(start["process_id"]),
        claimed_at="2026-07-25T00:07:00Z",
        candidate_revision=f"{other}^",
    )
    assert result.diagnostic is not None
    assert result.diagnostic.code is StartJobDiagnosticCode.AUTHORITY_STALE
    assert result.diagnostic.detail == "existing proof checkout differs from requested candidate revision"
    assert checkout.root.exists()
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id is None


@pytest.mark.asyncio
async def test_public_start_returns_plain_diagnostic_when_proof_authority_is_unavailable(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, _checkout, start, commit = await _active_accept(tmp_path)
    released = await server.release_job(ctx, **_identity(start), released_at="2026-07-25T00:06:00Z")
    assert released.diagnostic is None
    shutil.rmtree(revision.source_dir)

    result = await server.start_job(
        ctx,
        change_id=revision.change_id,
        job_id=int(start["job_id"]),
        attempt_id="attempt-missing-authority",
        claim_id="claim-missing-authority",
        actor_id=str(start["actor_id"]),
        process_id=str(start["process_id"]),
        claimed_at="2026-07-25T00:07:00Z",
        candidate_revision=commit,
    )

    assert result.diagnostic is not None
    assert result.diagnostic.code is StartJobDiagnosticCode.AUTHORITY_STALE
    assert result.diagnostic.detail == "proof checkout setup failed"
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id is None


@pytest.mark.asyncio
async def test_public_accept_conflict_restores_exact_checkout_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, board, ctx, _runtime, checkout, start, commit = await _active_accept(tmp_path)
    evidence = await _acceptor_evidence(revision, ctx, checkout, start, commit)

    def conflict(_transaction) -> None:
        raise TransactionConflictError

    monkeypatch.setattr(RuntimeTransaction, "commit", conflict)
    with pytest.raises(TransactionConflictError):
        await server.finish_accept(
            ctx,
            **_identity(start),
            finished_at="2026-07-25T00:06:00Z",
            receipt_id="accept-conflict",
            code_revision=commit,
            evidence=evidence,
            evidence_ids=("accept-conflict",),
            impact_closure=evidence["changed_surfaces"],
            reconciliation_plan_job_ids=(6, 7),
        )

    restored = checkout.root / "checkout"
    assert restored.is_dir()
    assert _git_state(restored) == {"head": commit, "status": "", "diff": ""}
    assert JobStore(board).read(int(start["job_id"])).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/accept-conflict.yaml").exists()


@pytest.mark.asyncio
async def test_public_accept_rejection_publishes_findings_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, board, ctx, runtime, checkout, start, commit = await _active_accept(tmp_path)
    payload = _rejection_payload(revision, start, commit)
    receipts = ReceiptStore(revision)
    unrelated_before = _create_unrelated_receipt(revision)
    receipts_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}
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
    assert rejected.job is not None
    assert rejected.job.job.disposition is JobDisposition.SUPERSEDED
    assert rejected.job.job.superseded_by_receipt_id == "supersession-accept-001"
    assert rejected.invalidation is not None
    assert rejected.invalidation.affected_receipt_ids == ("build-001", "build-002")
    assert rejected.invalidation.supersession_receipt.receipt_id == "supersession-accept-001"
    assert tuple(item.job.job_id for item in rejected.invalidation.corrective_jobs) == (20,)
    assert tuple(item.job.kind for item in rejected.invalidation.corrective_jobs) == ("build",)
    assert not (revision.source_dir / "receipts/accept-001.yaml").exists()
    assert (revision.source_dir / "receipts/build-unrelated.yaml").read_bytes() == unrelated_before
    for receipt_id in ("build-001", "build-002"):
        assert not receipts.evaluate_currentness(receipt_id, GitRepositoryHistory(Path.cwd()), commit).current
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
    assert {name: content for name, content in receipts_before.items() if name == "build-unrelated.yaml"} == {
        "build-unrelated.yaml": unrelated_before
    }


@pytest.mark.asyncio
async def test_public_audit_rejection_forwards_and_exposes_persisted_correction_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision, board, native, first_start = _active_audit_scenario(tmp_path)
    released = native.release_job(
        ReleaseJobRequest(
            job_id=first_start.job_id,
            attempt_id=first_start.attempt_id,
            claim_id=first_start.claim_id,
            actor_id=first_start.actor_id,
            process_id=first_start.process_id,
            released_at="2026-07-24T01:01:30Z",
        )
    )
    assert released.diagnostic is None
    runtime = DispatchRuntime(native, board)
    app_ctx = AppContext(workspace=NativeWorkspace(board, timedelta(hours=1)))
    app_ctx.dispatch_runtimes[revision.change_id] = runtime
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    current = first_start.model_copy(update={"attempt_id": "attempt-audit-mcp", "claim_id": "claim-audit-mcp"})
    started = await server.start_job(
        ctx,
        change_id=revision.change_id,
        **current.model_dump(mode="python"),
    )
    assert started.diagnostic is None
    request = _reject_audit_request(revision, current)
    receipts_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}
    reject = MagicMock(wraps=runtime.reject_audit)
    monkeypatch.setattr(runtime, "reject_audit", reject)

    rejected = await server.reject_audit(
        ctx,
        change_id=revision.change_id,
        **request.model_dump(mode="python"),
    )
    forwarded = reject.call_args.args[0]
    shown_job = await server.show_job(ctx, change_id=revision.change_id, job_id=current.job_id)
    jobs = await server.list_jobs(
        ctx,
        change_id=revision.change_id,
        candidate_revision="a" * 40,
    )
    attempts = await server.list_attempts(ctx, change_id=revision.change_id)
    findings = await server.list_findings(ctx, change_id=revision.change_id)
    shown_finding = await server.show_finding(
        ctx,
        change_id=revision.change_id,
        finding_id=request.findings[0].finding_id,
    )
    shown_receipt = await server.show_receipt(
        ctx,
        change_id=revision.change_id,
        receipt_id=request.invalidation.supersession_receipt_id,
    )

    assert rejected.diagnostic is None
    assert forwarded == request
    assert shown_job["job"].disposition is JobDisposition.SUPERSEDED
    assert any(item.job_id == current.job_id and item.disposition is JobDisposition.SUPERSEDED for item in jobs.items)
    assert any(event.attempt_id == current.attempt_id and event.kind == "failed" for event in attempts.items)
    assert findings.items == (request.findings[0],)
    assert shown_finding == request.findings[0]
    assert shown_receipt == rejected.invalidation.supersession_receipt
    assert rejected.invalidation.corrective_jobs == ()
    assert receipts_before == {
        path.name: path.read_bytes()
        for path in (revision.source_dir / "receipts").glob("*.yaml")
        if path.name != request.invalidation.supersession_receipt_id + ".yaml"
    }


@pytest.mark.asyncio
async def test_tracked_acceptor_edit_blocks_and_releases_without_corrective_publication(tmp_path: Path) -> None:
    revision, board, ctx, _runtime, checkout, start, _commit = await _active_accept(tmp_path)
    receipts_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}
    jobs_before = tuple(item.job.job_id for item in JobStore(board).list())
    findings_before = tuple((board / "findings").glob("*.yaml")) if (board / "findings").exists() else ()

    _assert_acceptor_write_denied(checkout.checkout)
    disposition = {
        "kind": "AcceptanceBlocked",
        "target": "checkout",
        "finding": "tracked acceptor edit was denied; self-authored state cannot be accepted",
    }
    blocked_contract = _markdown_subsection(_workflow_text(), "### `AcceptanceBlocked`")
    normalized_orchestration = " ".join(_orchestration_text().split())
    assert _yaml_code_block(blocked_contract) == {
        "kind": "AcceptanceBlocked",
        "target": "<job, checkout, authority, plan, receipt, proof, or evidence target>",
        "finding": "<specific stale, malformed, incomplete, contradictory, unsafe, or unavailable condition>",
    }
    assert (
        "`AcceptanceBlocked`: call `release_job` with only the unchanged active identity and an "
        "orchestrator-owned release timestamp, halt native mode, and report the returned target and finding."
        in normalized_orchestration
    )
    assert tuple(disposition) == ("kind", "target", "finding")
    released = await server.release_job(
        ctx,
        **_identity(start),
        released_at="2026-07-25T00:06:00Z",
    )

    assert released.diagnostic is None
    assert released.event is not None
    assert released.event.kind == "released"
    assert released.event.change_id == start["change_id"]
    assert released.event.job_id == start["job_id"]
    assert released.event.attempt_id == start["attempt_id"]
    assert released.event.claim_id == start["claim_id"]
    assert released.event.actor_id == start["actor_id"]
    assert released.event.process_id == start["process_id"]
    assert released.event.delivery_digest == revision.delivery_digest
    assert released.event.target_node_id == revision.graph.nodes[0].id
    assert released.job is not None
    assert released.job.job.claim_id is None
    assert released.job.job.attempt_id is None
    assert not checkout.root.exists()
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    assert tuple(item.job.job_id for item in JobStore(board).list()) == jobs_before
    findings_after = tuple((board / "findings").glob("*.yaml")) if (board / "findings").exists() else ()
    assert findings_after == findings_before
    assert receipts_before == {
        path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")
    }


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


@pytest.mark.parametrize("failure", ["cleanup", "transaction"])
@pytest.mark.asyncio
async def test_public_accept_rejection_runtime_failure_is_atomic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    revision, _board, ctx, runtime, checkout, start, commit = await _active_accept(tmp_path)
    payload = _rejection_payload(revision, start, commit)
    before = _snapshot(tmp_path)
    manifest_before = checkout.manifest.read_bytes()
    if failure == "cleanup":
        monkeypatch.setattr(runtime._proof_checkouts, "cleanup", lambda _job_id: None)  # noqa: SLF001
        expected = RejectAcceptDiagnosticCode.CLEANUP_FAILED
    else:
        original_commit = RuntimeTransaction.commit

        def fail_rejection(transaction: RuntimeTransaction, *, failure=None) -> None:
            if transaction._transaction_id.startswith("reject-"):  # noqa: SLF001
                raise TransactionConflictError
            original_commit(transaction, failure=failure)

        monkeypatch.setattr(RuntimeTransaction, "commit", fail_rejection)
        expected = RejectAcceptDiagnosticCode.IDENTITY_CONFLICT

    rejected = await server.reject_accept(ctx, **payload)

    assert rejected.diagnostic is not None
    assert rejected.diagnostic.code is expected
    assert _snapshot(tmp_path) == before
    assert checkout.root.exists()
    assert checkout.manifest.read_bytes() == manifest_before


@pytest.mark.asyncio
async def test_public_audit_success_closes_accepted_whole_change_and_replays(tmp_path: Path) -> None:
    repository = Path.cwd()
    commit = _git_head()
    revision, board, native, accept_request, _predecessor_ids = _terminal_accept_scenario(
        tmp_path,
        code_revision=commit,
        history=GitRepositoryHistory(repository),
    )
    checkouts = ProofCheckoutManager(repository, tmp_path / "proof-mcp", revision.source_dir.parent)
    runtime = DispatchRuntime(native, board, checkouts)
    app_ctx = AppContext(workspace=NativeWorkspace(board, timedelta(hours=1)))
    app_ctx.dispatch_runtimes[revision.change_id] = runtime
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    accept_request = await _restart_terminal_accept(ctx, revision, native, accept_request, commit)
    audit_job_id = (await _finish_terminal_accept(ctx, revision, accept_request)).job_id
    picked = await server.pick_jobs(
        ctx,
        change_id=revision.change_id,
        candidate_revision=commit,
        wave_size=1,
    )
    selected = [entry for wave in picked.waves for entry in wave]
    assert [(entry.job_id, entry.agent_profile) for entry in selected] == [(audit_job_id, "auditor")]
    audit_start = _start(audit_job_id, 6, commit)
    started = await server.start_job(ctx, **audit_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    audit_checkout = started["checkout"]
    assert audit_checkout.commit == commit
    await _assert_audit_blocks_writer(revision, board, ctx, audit_job_id, commit)

    accept_receipt_ids = tuple(
        stored.job.receipt_id
        for stored in JobStore(board).list(archived=True)
        if stored.job.kind == "accept" and stored.job.receipt_id is not None
    )
    evidence = await _auditor_evidence(
        revision,
        ctx,
        audit_checkout,
        audit_start,
        accept_receipt_ids,
    )
    impact_closure = {
        "paths": ["/"],
        "authority_targets": sorted(entity.id for entity in revision.graph.iter_entities()),
    }
    finish = {
        "finished_at": "2026-07-24T01:02:00Z",
        "receipt_id": "audit-001",
        "code_revision": commit,
        "evidence": evidence,
        "evidence_ids": ("audit-proof-008",),
        "impact_closure": impact_closure,
    }
    events_before = len(AttemptStore(board).list())
    finished = await server.finish_audit(ctx, **_identity(audit_start), **finish)

    assert finished.diagnostic is None
    assert finished.receipt is not None
    assert finished.receipt.payload["code_revision"] == commit
    assert finished.receipt.payload["predecessor_receipt_ids"] == accept_receipt_ids
    assert finished.receipt.to_mapping()["evidence"] == json.loads(json.dumps(evidence))
    assert finished.receipt.impact_closure is not None
    assert finished.receipt.impact_closure.model_dump(mode="json") == impact_closure
    assert finished.event is not None
    assert finished.event.kind == "succeeded"
    assert finished.job == JobStore(board).read(audit_job_id, archived=True)
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    assert not audit_checkout.root.exists()

    state_after_finish = _snapshot(tmp_path)
    replayed = await server.finish_audit(ctx, **_identity(audit_start), **finish)
    assert replayed == finished
    assert _snapshot(tmp_path) == state_after_finish
    assert len(AttemptStore(board).list()) == events_before + 1
    audit_events = [event.kind for event in AttemptStore(board).list() if event.attempt_id == audit_start["attempt_id"]]
    assert audit_events == ["started", "succeeded"]
    shown_receipt = await server.show_receipt(ctx, change_id=revision.change_id, receipt_id="audit-001")
    assert shown_receipt == finished.receipt


@pytest.mark.parametrize(
    "mutation",
    [
        "methods-only",
        "promise",
        "decisions",
        "migrations",
        "workflows",
        "receipts",
        "requests",
        "proof",
        "replacements",
        "boundary",
        "null-command",
        "irrelevant-output",
        "tracked-state",
    ],
)
@pytest.mark.asyncio
async def test_public_audit_rejects_incomplete_or_forged_evidence(  # noqa: C901, PLR0912 - forged dimensions explicit.
    tmp_path: Path, mutation: str
) -> None:
    revision, board, _native, ctx, checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, f"proof-forged-audit-{mutation}"
    )
    start = _start(audit_job_id, 8, commit)
    started = await server.start_job(ctx, **start)
    assert isinstance(started, dict)
    checkout = started["checkout"]
    accept_receipt_ids = tuple(
        stored.job.receipt_id
        for stored in JobStore(board).list(archived=True)
        if stored.job.kind == "accept" and stored.job.receipt_id is not None
    )
    evidence = await _auditor_evidence(revision, ctx, checkout, start, accept_receipt_ids)
    if mutation == "methods-only":
        evidence = {"methods": evidence["methods"]}
    elif mutation == "promise":
        evidence["product_promise"] = "forged"
    elif mutation == "decisions":
        evidence["accepted_decisions"] = {}
    elif mutation == "migrations":
        evidence["migrations"] = []
    elif mutation == "workflows":
        evidence["admitted_workflows"] = []
    elif mutation == "receipts":
        evidence["accepted_receipts"] = []
    elif mutation == "requests":
        evidence["pending_requests"] = [{"request_id": "pending"}]
    elif mutation == "proof":
        evidence["proof"]["id"] = "PROOF-999"
    elif mutation == "replacements":
        evidence["allowed_replacements"] = ["finish_audit public boundary"]
    elif mutation == "boundary":
        evidence["assembled_proof"]["boundary"] = "bypassed"
    elif mutation == "null-command":
        evidence["assembled_proof"]["commands"] = [None]
        evidence["assembled_proof"]["results"] = [{"command": None, "exit_code": 0, "result": "forged success"}]
    elif mutation == "irrelevant-output":
        evidence["assembled_proof"]["results"][0]["result"] = "irrelevant success\n"
    else:
        evidence["after_tracked_state"]["status"] = " M README.md"

    result = await server.finish_audit(
        ctx,
        **_identity(start),
        finished_at="2026-07-24T01:03:00Z",
        receipt_id=f"audit-forged-{mutation}",
        code_revision=commit,
        evidence=evidence,
        evidence_ids=(f"audit-forged-{mutation}",),
        impact_closure={
            "paths": ["/"],
            "authority_targets": sorted(entity.id for entity in revision.graph.iter_entities()),
        },
    )

    assert result.diagnostic is not None
    assert result.diagnostic.lower_code == "ERR_RECEIPT_PROOF_UNSATISFIED"
    assert checkouts.existing(audit_job_id) is not None
    assert JobStore(board).read(audit_job_id).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / f"receipts/audit-forged-{mutation}.yaml").exists()


@pytest.mark.asyncio
async def test_public_audit_finish_rejects_request_created_after_start(tmp_path: Path) -> None:
    revision, board, _native, ctx, checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-late-request-audit"
    )
    start = _start(audit_job_id, 9, commit)
    started = await server.start_job(ctx, **start)
    assert isinstance(started, dict)
    checkout = started["checkout"]
    accept_receipt_ids = tuple(
        stored.job.receipt_id
        for stored in JobStore(board).list(archived=True)
        if stored.job.kind == "accept" and stored.job.receipt_id is not None
    )
    evidence = await _auditor_evidence(revision, ctx, checkout, start, accept_receipt_ids)
    NativeRequestRuntime(revision, board).create_request(
        NativeRequest(
            schema_version=1,
            request_id="request-late-audit",
            kind="action",
            title="Resolve late audit evidence",
            summary="Evidence became unresolved after audit start.",
            body="Resolve before finalization.",
            agent="orchestrator",
            created_at="2026-07-25T00:12:00Z",
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            target_node_id="DN-014",
            job_ids=(audit_job_id,),
            evidence=("late-audit-evidence",),
            resume_condition="Evidence is resolved.",
        )
    )

    result = await server.finish_audit(
        ctx,
        **_identity(start),
        finished_at="2026-07-25T00:12:30Z",
        receipt_id="audit-late-request",
        code_revision=commit,
        evidence=evidence,
        evidence_ids=("audit-late-request",),
        impact_closure={
            "paths": ["/"],
            "authority_targets": sorted(entity.id for entity in revision.graph.iter_entities()),
        },
    )

    assert result.diagnostic is not None
    assert result.diagnostic.detail == "audit job has unresolved requests"
    assert result.diagnostic.target == "request-late-audit"
    assert checkouts.existing(audit_job_id) is not None
    assert JobStore(board).read(audit_job_id).job.attempt_id == start["attempt_id"]
    assert not (revision.source_dir / "receipts/audit-late-request.yaml").exists()


async def _pending_public_audit(tmp_path: Path, proof_dir: str):
    repository = Path.cwd()
    commit = _git_head()
    revision, board, native, accept_request, _predecessor_ids = _terminal_accept_scenario(
        tmp_path,
        code_revision=commit,
        history=GitRepositoryHistory(repository),
    )
    checkouts = ProofCheckoutManager(repository, tmp_path / proof_dir, revision.source_dir.parent)
    runtime = DispatchRuntime(native, board, checkouts)
    app_ctx = AppContext(workspace=NativeWorkspace(board, timedelta(hours=1)))
    app_ctx.dispatch_runtimes[revision.change_id] = runtime
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    accept_request = await _restart_terminal_accept(ctx, revision, native, accept_request, commit)
    audit_job_id = (await _finish_terminal_accept(ctx, revision, accept_request)).job_id
    return revision, board, native, ctx, checkouts, audit_job_id, accept_request, commit


_AUDIT_DISPOSITION_MATRIX = (
    (
        "Cross-node integration failure",
        "implementation-defect",
        "requirement",
        "REQ-008",
        "whole-change-integration",
        "affected-node-correction",
        False,
        ("DN-001", "DN-002"),
        ("DN-001", "DN-002"),
    ),
    (
        "Implemented migration/removal absence or failure",
        "implementation-defect",
        "requirement",
        "REQ-007",
        "whole-change-integration",
        "affected-node-correction",
        False,
        ("DN-001",),
        ("DN-001",),
    ),
    (
        "Admitted Product Promise, decision, workflow, or proof omission",
        "planning-omission",
        "proof",
        "PROOF-001",
        "admitted-design-authority",
        "design-reentry",
        True,
        ("DN-001",),
        (),
    ),
)


def _audit_rejection_payload(
    revision,
    checkout,
    start: dict[str, object],
    commit: str,
    case: tuple[object, ...],
) -> dict[str, object]:
    (
        name,
        expected_finding_class,
        expected_target_kind,
        expected_target_id,
        route_target,
        _route_kind,
        _design_reentry,
        route_node_ids,
        _expected_node_ids,
    ) = case
    if name == "Cross-node integration failure":
        observed = subprocess.run(
            [sys.executable, "-c", "raise SystemExit(23)"],
            cwd=checkout.checkout,
            check=False,
            capture_output=True,
            text=True,
        )
        assert observed.returncode == 23
        finding_class, target_kind, target_id = "implementation-defect", "requirement", "REQ-008"
        detail = f"cross-node assembled command failed with exit {observed.returncode} at {commit}"
    elif name == "Implemented migration/removal absence or failure":
        migration = revision.graph.migrations[0]
        assert migration.absence_proof
        missing = checkout.checkout / ".owlbear" / "scratch" / "missing-migration-proof"
        assert not missing.exists()
        finding_class, target_kind, target_id = "implementation-defect", "requirement", "REQ-007"
        detail = f"{migration.id} absence proof artifact is unavailable at {commit}"
    else:
        proof = revision.resolve("PROOF-008")
        omitted = proof.model_dump(mode="json") | {"method": []}
        assert omitted["method"] == []
        finding_class, target_kind, target_id = "planning-omission", "proof", "PROOF-001"
        detail = f"admitted proof method is omitted from whole-change authority at {commit}"

    assert (finding_class, target_kind, target_id) == (
        expected_finding_class,
        expected_target_kind,
        expected_target_id,
    )
    emitted_finding_class, emitted_route_target = _audit_classification(name)
    assert emitted_finding_class == finding_class
    assert emitted_route_target == route_target
    scenario_id = re.sub(r"[^A-Za-z0-9]+", "-", str(name)).strip("-")
    finding = Finding(
        schema_version=1,
        finding_id=f"finding-audit-{scenario_id}",
        source_attempt_id=str(start["attempt_id"]),
        source_job_id=int(start["job_id"]),
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind=target_kind,
        target_id=target_id,
        finding_class=emitted_finding_class,
        detail=detail,
        created_at="2026-07-25T00:07:00Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target=emitted_route_target,
            target_node_ids=route_node_ids,
            packet_id=(
                finding.target_id
                if emitted_route_target in {"packet-implementation", "packet-local-proof"}
                and finding.target_kind == "packet"
                else None
            ),
        )
    )
    invalidation = InvalidationRequest(
        invalidation_id=f"invalidation-audit-{scenario_id}",
        supersession_receipt_id=f"supersession-audit-{scenario_id}",
        invalidated_receipt_ids=("accept-final",),
        routes=(route,),
        corrective_job_ids=tuple(range(100, 100 + len(route.jobs))),
        issued_at="2026-07-25T00:07:00Z",
        code_revision=commit,
        priority=9,
    )
    return {
        **_identity(start),
        "rejected_at": "2026-07-25T00:07:00Z",
        "detail": f"audit found {finding_class}: {name}",
        "evidence_ids": (f"audit-proof-{scenario_id}",),
        "findings": (finding.model_dump(mode="json"),),
        "invalidation": invalidation.model_dump(mode="json"),
    }


@pytest.mark.parametrize("case", _AUDIT_DISPOSITION_MATRIX, ids=[str(case[0]) for case in _AUDIT_DISPOSITION_MATRIX])
@pytest.mark.asyncio
async def test_public_audit_rejection_routes_canonical_minimum_correction(
    tmp_path: Path, case: tuple[object, ...]
) -> None:
    """Audit rejection routes only implicated nodes or returns to design."""
    revision, _board, _native, ctx, _checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-route-audit"
    )
    audit_start = _start(audit_job_id, 6, commit)
    started = await server.start_job(ctx, **audit_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    checkout = started["checkout"]

    (
        _name,
        finding_class,
        target_kind,
        target_id,
        _route_target,
        route_kind,
        design_reentry,
        _route_node_ids,
        expected_node_ids,
    ) = case
    payload = _audit_rejection_payload(revision, checkout, audit_start, commit, case)
    rejected = await server.reject_audit(ctx, **payload)

    assert rejected.diagnostic is None
    assert rejected.findings[0].finding_class == finding_class
    assert rejected.findings[0].target_kind == target_kind
    assert rejected.findings[0].target_id == target_id
    assert rejected.invalidation is not None
    route = payload["invalidation"]["routes"][0]
    assert route["route"] == route_kind
    assert route["design_reentry"] is design_reentry
    assert tuple(job.job.target_node_id for job in rejected.invalidation.corrective_jobs) == expected_node_ids


@pytest.mark.asyncio
async def test_public_audit_rejection_with_git_history_exposes_full_chain(
    tmp_path: Path,
) -> None:
    """Public rejection exposes its persisted chain and preserves unrelated receipts."""
    revision, board, _native, ctx, _checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-rejection-audit"
    )
    audit_start = _start(audit_job_id, 6, commit)
    started = await server.start_job(ctx, **audit_start)
    assert isinstance(started, dict)
    audit_checkout = started["checkout"]
    receipts_before = {path.name: path.read_bytes() for path in (revision.source_dir / "receipts").glob("*.yaml")}

    finding = Finding(
        schema_version=1,
        finding_id="finding-audit-history-001",
        source_attempt_id=audit_start["attempt_id"],
        source_job_id=audit_start["job_id"],
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="proof",
        target_id="PROOF-001",
        finding_class="planning-omission",
        detail="admission authority requires design re-entry under full audit",
        created_at="2026-07-25T00:08:00Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="admitted-design-authority",
            target_node_ids=("DN-001",),
        )
    )
    invalidation = InvalidationRequest(
        invalidation_id="invalidation-audit-history-001",
        supersession_receipt_id="supersession-audit-history-001",
        invalidated_receipt_ids=("accept-final",),
        routes=(route,),
        corrective_job_ids=(),
        issued_at="2026-07-25T00:08:00Z",
        code_revision=commit,
        priority=9,
    )
    payload = {
        **_identity(audit_start),
        "rejected_at": "2026-07-25T00:08:00Z",
        "detail": "audit requires design re-entry",
        "evidence_ids": ("audit-proof-history-001",),
        "findings": (finding.model_dump(mode="json"),),
        "invalidation": invalidation.model_dump(mode="json"),
    }

    rejected = await server.reject_audit(ctx, **payload)
    state_after_first = _snapshot(tmp_path)
    replayed = await server.reject_audit(ctx, **payload)

    shown_finding = await server.show_finding(
        ctx,
        change_id=revision.change_id,
        finding_id="finding-audit-history-001",
    )
    findings_list = await server.list_findings(ctx, change_id=revision.change_id)

    assert rejected.diagnostic is None
    assert rejected.event is not None
    assert rejected.event.kind == "failed"
    assert rejected.job is not None
    assert rejected.job.job.disposition is JobDisposition.SUPERSEDED
    assert rejected.findings[0] == shown_finding
    assert rejected.findings[0] in findings_list.items
    assert rejected.invalidation is not None
    assert rejected.invalidation.supersession_receipt.receipt_id == "supersession-audit-history-001"
    assert rejected.invalidation.affected_receipt_ids == ("accept-final",)
    assert rejected.invalidation.corrective_jobs == ()

    assert replayed == rejected
    assert _snapshot(tmp_path) == state_after_first
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    assert not audit_checkout.root.exists()
    for receipt_name, receipt_bytes in receipts_before.items():
        assert (revision.source_dir / "receipts" / receipt_name).read_bytes() == receipt_bytes


@pytest.mark.asyncio
async def test_public_start_job_rejects_stale_predecessor_without_mutation(tmp_path: Path) -> None:
    repository = Path.cwd()
    revision, board, native, ctx, checkouts, generated_audit_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-stale-audit"
    )
    audit_template = JobStore(board).read(generated_audit_id).job
    finding = Finding(
        schema_version=1,
        finding_id="finding-stale-accept",
        source_attempt_id="attempt-stale-accept",
        source_job_id=generated_audit_id,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="proof",
        target_id="PROOF-001",
        finding_class="planning-omission",
        detail="accepted authority is stale",
        created_at="2026-07-25T00:09:00Z",
    )
    assert FindingStore(board).create(finding.finding_id, finding.model_dump(mode="json")).finding == finding
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="admitted-design-authority",
            target_node_ids=(revision.graph.nodes[0].id,),
        )
    )
    invalidated = native.invalidate(
        InvalidationRequest(
            invalidation_id="invalidation-stale-accept",
            supersession_receipt_id="supersession-stale-accept",
            invalidated_receipt_ids=("accept-final",),
            routes=(route,),
            corrective_job_ids=(),
            issued_at="2026-07-25T00:09:00Z",
            code_revision=commit,
        )
    )
    assert invalidated.diagnostic is None
    assert (
        not ReceiptStore(revision)
        .evaluate_currentness("accept-final", GitRepositoryHistory(repository), commit)
        .current
    )
    stale_job_id = max(item.job.job_id for item in (*JobStore(board).list(), *JobStore(board).list(archived=True))) + 1
    stale_job = audit_template.model_copy(
        update={
            "job_id": stale_job_id,
            "created_at": "2026-07-25T00:09:01Z",
            "updated_at": "2026-07-25T00:09:01Z",
        }
    )
    RuntimeTransaction(board, "create-stale-audit", (JobStore(board).create_participant(stale_job),)).commit()
    state_before = _snapshot(tmp_path)

    result = await server.start_job(ctx, **_start(stale_job_id, 7, commit))

    assert result.diagnostic is not None
    assert result.diagnostic.code is StartJobDiagnosticCode.PREDECESSOR_INVALID
    assert result.diagnostic.target == "accept-final"
    assert _snapshot(tmp_path) == state_before
    assert checkouts.existing(stale_job_id) is None


@pytest.mark.asyncio
async def test_public_start_job_rejects_pending_request_without_mutation(tmp_path: Path) -> None:
    revision, board, _native, ctx, checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-request-audit"
    )
    audit_job = JobStore(board).read(audit_job_id).job
    NativeRequestRuntime(revision, board).create_request(
        NativeRequest(
            schema_version=1,
            request_id="request-pending-audit",
            kind="action",
            title="Supply missing audit evidence",
            summary="Audit evidence is incomplete.",
            body="Provide the missing evidence before audit starts.",
            agent="orchestrator",
            created_at="2026-07-25T00:10:00Z",
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            target_node_id=audit_job.target_node_id,
            job_ids=(audit_job_id,),
            evidence=("missing-audit-evidence",),
            resume_condition="Evidence is available.",
        )
    )
    state_before = _snapshot(tmp_path)

    result = await server.start_job(ctx, **_start(audit_job_id, 8, commit))

    assert result.diagnostic is not None
    assert result.diagnostic.code is StartJobDiagnosticCode.REQUEST_PENDING
    assert result.diagnostic.target == "request-pending-audit"
    assert _snapshot(tmp_path) == state_before
    assert checkouts.existing(audit_job_id) is None


@pytest.mark.asyncio
async def test_public_audit_tracked_edit_publishes_typed_minimum_correction(tmp_path: Path) -> None:
    """A tracked auditor edit is detected and routed as AuditRejected."""
    revision, board, _native, ctx, _checkouts, audit_job_id, _accept_request, commit = await _pending_public_audit(
        tmp_path, "proof-blocked-audit"
    )
    audit_start = _start(audit_job_id, 6, commit)
    started = await server.start_job(ctx, **audit_start)
    assert isinstance(started, dict)
    audit_checkout = started["checkout"]

    tracked = audit_checkout.checkout / "README.md"
    tracked.chmod(stat.S_IMODE(tracked.stat().st_mode) | stat.S_IWUSR)
    tracked.write_text("modified by auditor\n", encoding="utf-8")
    finish = await server.finish_audit(
        ctx,
        **_identity(audit_start),
        finished_at="2026-07-25T00:11:00Z",
        receipt_id="audit-tracked-mutation",
        code_revision=commit,
        evidence={"methods": list(revision.resolve("PROOF-008").method)},
        evidence_ids=("audit-tracked-mutation",),
    )
    assert finish.diagnostic is not None
    assert finish.diagnostic.lower_code == "ERR_PROOF_TRACKED_MUTATION"

    finding = Finding(
        schema_version=1,
        finding_id="finding-audit-tracked-mutation",
        source_attempt_id=str(audit_start["attempt_id"]),
        source_job_id=int(audit_start["job_id"]),
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        target_kind="requirement",
        target_id="REQ-008",
        finding_class="implementation-defect",
        detail=f"{finish.diagnostic.lower_code}: tracked auditor state changed at {commit}",
        created_at="2026-07-25T00:11:30Z",
    )
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id=finding.finding_id,
            finding_class=finding.finding_class,
            target="whole-change-integration",
            target_node_ids=("DN-001",),
        )
    )
    rejected = await server.reject_audit(
        ctx,
        **_identity(audit_start),
        rejected_at=finding.created_at,
        detail=finding.detail,
        evidence_ids=("audit-tracked-mutation",),
        findings=(finding.model_dump(mode="json"),),
        invalidation=InvalidationRequest(
            invalidation_id="invalidation-audit-tracked-mutation",
            supersession_receipt_id="supersession-audit-tracked-mutation",
            invalidated_receipt_ids=("accept-final",),
            routes=(route,),
            corrective_job_ids=(100,),
            issued_at=finding.created_at,
            code_revision=commit,
            priority=9,
        ).model_dump(mode="json"),
    )

    assert rejected.diagnostic is None
    assert rejected.findings == (finding,)
    assert rejected.invalidation is not None
    assert tuple(item.job.target_node_id for item in rejected.invalidation.corrective_jobs) == ("DN-001",)
    assert not audit_checkout.root.exists()
    assert not (revision.source_dir / "receipts/audit-tracked-mutation.yaml").exists()
    assert "readers: []" in (board / "dispatch/coordination.yaml").read_text(encoding="utf-8")
    assert not audit_checkout.root.exists()
