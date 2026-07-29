"""Assembled PROOF-013 fresh-consumer native delivery workflow."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from owlbear_kanban import (
    DispatchRuntime,
    FinishJobDiagnosticCode,
    GitRepositoryHistory,
    JobStore,
    NativeRuntime,
    NativeWorkspace,
    ProofCheckoutManager,
    ReceiptStore,
    WHOLE_CHANGE_AUDIT_COMMAND,
    load_change,
)
from owlbear_mcp_kanban import server
from owlbear_mcp_kanban.server import AppContext

from .test_mcp_acceptance_tools import _identity, _rejection_payload, _start

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIVE_CARRIER = _REPO_ROOT / ".owlbear" / "kanban"
_CHANGE_ID = "proof-013-native-delivery"
_SECTIONS = ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")


@dataclass(frozen=True)
class _Scenario:
    consumer: Path
    revision: object
    board: Path
    context: object
    commit: str
    supersession_receipt_id: str | None = None
    corrective_receipt_id: str | None = None


def _run(repository: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    )


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    return _run(repository, executable, *arguments).stdout.strip()


def _documents() -> dict[str, dict[str, object]]:
    common = {"schema_version": 1, "change_id": _CHANGE_ID}
    nodes = (
        ("DN-001", "REQ-001", "MOD-001", "PROOF-001", ()),
        ("DN-002", "REQ-002", "MOD-002", "PROOF-002", ("DN-001",)),
        ("DN-014", "REQ-014", "MOD-002", "PROOF-008", ("DN-002",)),
    )
    return {
        "decisions.yaml": {**common, "decisions": []},
        "delivery/obligations.yaml": {
            **common,
            "requirements": [
                {
                    "id": requirement_id,
                    "title": f"Delivery requirement for {node_id}",
                    "statement": f"{node_id} completes its admitted delivery responsibility.",
                    "workflows": [],
                }
                for node_id, requirement_id, _module_id, _proof_id, _dependencies in nodes
            ],
            "negative_requirements": [],
            "preserved_behaviors": [],
            "workflows": [],
        },
        "delivery/contracts.yaml": {
            **common,
            "modules": [
                {
                    "id": "MOD-001",
                    "paths": ["module-one/"],
                    "current_responsibility": "First delivery module",
                    "planned_change": "Correct and accept the first module",
                },
                {
                    "id": "MOD-002",
                    "paths": ["module-two/"],
                    "current_responsibility": "Second delivery module and assembled audit authority",
                    "planned_change": "Accept the second module and audit the assembled delivery",
                },
            ],
            "interfaces": [],
            "migrations": [],
            "risks": [],
            "proofs": [
                {
                    "id": proof_id,
                    "title": f"Delivery proof for {node_id}",
                    "boundary": "Disposable public native-delivery workflow",
                    "owner": node_id,
                    "method": [f"Complete {node_id} through public MCP lifecycle tools"],
                    "allowed_replacements": ["Temporary filesystem and Git repository"],
                    "durable_outputs": ["PROOF-013 assembled workflow result"],
                }
                for node_id, _requirement_id, _module_id, proof_id, _dependencies in nodes
            ],
        },
        "delivery/nodes.yaml": {
            **common,
            "state": "draft",
            "authority": {
                "intent": "intent.md",
                "design": "design.md",
                "decisions": "decisions.yaml",
                "research": [],
            },
            "admission": None,
            "nodes": [
                {
                    "id": node_id,
                    "title": f"Deliver {node_id}",
                    "outcome": f"{node_id} is independently accepted.",
                    "owns": [requirement_id],
                    "supports": [],
                    "modules": [module_id],
                    "produces": [],
                    "consumes": [],
                    "dependencies": list(dependencies),
                    "risks": [],
                    "proof": proof_id,
                }
                for node_id, requirement_id, module_id, proof_id, dependencies in nodes
            ],
        },
    }


def _write_change(change_root: Path) -> None:
    change_dir = change_root / _CHANGE_ID
    change_dir.mkdir()
    (change_dir / "intent.md").write_text("Deliver two modules through the native workflow.\n", encoding="utf-8")
    (change_dir / "design.md").write_text(
        "Use two delivery-work nodes followed by mandatory DN-014 audit authority.\n",
        encoding="utf-8",
    )
    for relative_path, document in _documents().items():
        path = change_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False, width=120), encoding="utf-8")
    loaded = load_change(change_root, _CHANGE_ID)
    assert loaded.diagnostics == ()
    assert loaded.revision is not None
    nodes_path = change_dir / "delivery" / "nodes.yaml"
    nodes = yaml.safe_load(nodes_path.read_text(encoding="utf-8"))
    nodes["state"] = "admitted"
    nodes["admission"] = {
        "state": "admitted",
        "delivery_digest": loaded.revision.delivery_digest,
        "receipt": f"receipts/admission-{loaded.revision.delivery_digest[:12]}.yaml",
        "limits": ["Disposable PROOF-013 consumer only."],
    }
    nodes_path.write_text(yaml.safe_dump(nodes, sort_keys=False, width=120), encoding="utf-8")


def _evidence(revision) -> dict[str, object]:
    challenge = {
        entity.id: {"disposition": "pass", "evidence": f"PROOF-013:{entity.id}"}
        for section in _SECTIONS
        for entity in getattr(revision.graph, section)
    }
    return {
        "digest": revision.delivery_digest,
        "challenge": challenge,
        "baseline": {
            "commands": [{"command": "public native delivery proof", "exit_code": 0}],
            "digest": revision.delivery_digest,
        },
        "approval": {"approved": True, "digest": revision.delivery_digest},
        "limits": ["Disposable PROOF-013 consumer only."],
    }


def _next_job_ids(board: Path, count: int) -> tuple[int, ...]:
    jobs = (*JobStore(board).list(), *JobStore(board).list(archived=True))
    highest = max((stored.job.job_id for stored in jobs), default=0)
    return tuple(range(highest + 1, highest + count + 1))


def _active_plan_id(board: Path, target_node_id: str) -> int:
    plans = [
        stored.job.job_id
        for stored in JobStore(board).list()
        if stored.job.kind == "plan" and stored.job.target_node_id == target_node_id
    ]
    assert len(plans) == 1
    return plans[0]


async def _pick_one(scenario: _Scenario, kind: str):
    picked = await server.pick_jobs(
        scenario.context,
        change_id=scenario.revision.change_id,
        candidate_revision=scenario.commit,
        wave_size=len(scenario.revision.graph.nodes),
    )
    assert picked.waves
    selected = [entry for entry in picked.waves[0] if entry.kind == kind]
    assert len(selected) == 1
    return selected[0]


def _closure(revision, target) -> dict[str, list[str]]:
    module_paths = [path for module_id in target.modules for path in revision.resolve(module_id).paths]
    return {"paths": module_paths, "authority_targets": [target.id, target.proof]}


def _git_state(repository: Path) -> dict[str, str]:
    return {
        "head": _git(repository, "rev-parse", "HEAD"),
        "status": _git(repository, "status", "--porcelain=v1", "--untracked-files=no"),
        "diff": _git(repository, "diff", "--binary", "HEAD", "--"),
    }


async def _assert_out_of_authority_plan_refused(
    scenario: _Scenario,
    start: dict[str, object],
    target,
    proof,
) -> None:
    build_job_id, accept_job_id = _next_job_ids(scenario.board, 2)
    escaped_target = "DN-014"
    result = await server.finish_plan(
        scenario.context,
        **_identity(start),
        finished_at="2026-07-28T00:01:30Z",
        receipt_id="plan-outside-authority",
        code_revision=scenario.commit,
        evidence={"methods": list(proof.method)},
        node_plan={
            "mode": "build",
            "packets": [
                {
                    "id": f"{target.id}-PK-INVALID",
                    "dependencies": [],
                    "impact_closure": {
                        "paths": ["module-one/"],
                        "authority_targets": [target.id, target.proof, escaped_target],
                    },
                }
            ],
        },
        build_job_ids=(build_job_id,),
        accept_job_id=accept_job_id,
    )
    assert result.diagnostic is not None
    assert result.diagnostic.code is FinishJobDiagnosticCode.NODE_PLAN_INVALID
    assert result.diagnostic.target == escaped_target
    assert not (scenario.revision.source_dir / "receipts" / "plan-outside-authority.yaml").exists()
    assert not (scenario.revision.source_dir / "plans" / f"{target.id}.yaml").exists()
    published_ids = {stored.job.job_id for stored in JobStore(scenario.board).list()}
    assert published_ids.isdisjoint((build_job_id, accept_job_id))


def _acceptance_evidence(
    scenario: _Scenario,
    checkout,
    job,
    target,
    proof,
) -> dict[str, object]:
    revision = scenario.revision
    interface_ids = tuple(sorted((*target.produces, *target.consumes)))
    migration_ids = tuple(
        sorted(
            {
                revision.resolve(interface_id).migration
                for interface_id in interface_ids
                if revision.resolve(interface_id).migration is not None
            }
            | {item_id for item_id in target.owns if item_id.startswith("MIG-")}
        )
    )
    node_plan = revision.read_node_plan(target.id)
    packets = node_plan["packets"]
    predecessor_receipts = []
    for predecessor_job_id in job.predecessor_job_ids:
        predecessor = JobStore(scenario.board).read(predecessor_job_id, archived=True).job
        assert predecessor.receipt_id is not None
        predecessor_receipts.append({"receipt_id": predecessor.receipt_id, "code_revision": scenario.commit})
    state = _git_state(checkout.checkout)
    command = "git rev-parse HEAD and git status --porcelain=v1"
    return {
        "methods": list(proof.method),
        "assembled_proof": {
            "boundary": proof.boundary,
            "durable_outputs": list(proof.durable_outputs),
            "commands": [command],
            "results": [{"command": command, "exit_code": 0, "result": f"{state['head']} clean"}],
        },
        "authority": {
            "delivery_digest": revision.delivery_digest,
            "target_node_id": target.id,
            "proof": proof.id,
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
        "packet_receipts": predecessor_receipts,
        "changed_surfaces": _closure(revision, target),
        "checkout": {"root": str(checkout.checkout), "candidate_sha": scenario.commit},
        "replacements": [],
        "tracked_state": {"before": state, "after": _git_state(checkout.checkout)},
    }


async def _audit_evidence(scenario: _Scenario, checkout, audit_job) -> dict[str, object]:
    revision = scenario.revision
    accepted_receipt_ids = tuple(
        JobStore(scenario.board).read(job_id, archived=True).job.receipt_id for job_id in audit_job.predecessor_job_ids
    )
    assert all(receipt_id is not None for receipt_id in accepted_receipt_ids)
    accepted_receipts = tuple(
        ReceiptStore(revision).read(receipt_id).receipt for receipt_id in accepted_receipt_ids if receipt_id is not None
    )
    assert all(receipt is not None for receipt in accepted_receipts)
    accepted_mappings = tuple(receipt.to_mapping() for receipt in accepted_receipts if receipt is not None)
    probe_script = (
        "import json; from pathlib import Path; "
        "from owlbear_kanban import load_change, whole_change_audit_report; "
        f"result=load_change(Path('.owlbear/changes'), {_CHANGE_ID!r}); "
        "assert result.revision is not None; "
        f"report=whole_change_audit_report(result.revision, {accepted_mappings!r}); "
        "print(json.dumps(report,sort_keys=True,separators=(',',':'),ensure_ascii=False))"
    )
    state = _git_state(checkout.checkout)
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-c",
        probe_script,
        cwd=checkout.checkout,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    assert process.returncode == 0, (stdout + stderr).decode()
    proof = revision.resolve("PROOF-008")
    return {
        "methods": list(proof.method),
        "product_promise": revision.intent,
        "accepted_decisions": revision.decisions.model_dump(mode="json"),
        "migrations": [item.model_dump(mode="json") for item in revision.graph.migrations],
        "admitted_workflows": [item.model_dump(mode="json") for item in revision.graph.workflows],
        "accepted_receipts": list(accepted_mappings),
        "proof": proof.model_dump(mode="json"),
        "allowed_replacements": list(proof.allowed_replacements),
        "pending_requests": [],
        "assembled_proof": {
            "boundary": proof.boundary,
            "durable_outputs": list(proof.durable_outputs),
            "commands": [WHOLE_CHANGE_AUDIT_COMMAND],
            "results": [
                {
                    "command": WHOLE_CHANGE_AUDIT_COMMAND,
                    "exit_code": process.returncode,
                    "result": stdout.decode(),
                }
            ],
        },
        "before_tracked_state": state,
        "after_tracked_state": _git_state(checkout.checkout),
    }


async def _finish_plan(scenario: _Scenario, attempt: int):
    revision = scenario.revision
    entry = await _pick_one(scenario, "plan")
    start = _start(entry.job_id, attempt, scenario.commit) | {"change_id": revision.change_id}
    started = await server.start_job(scenario.context, **start)
    assert started.diagnostic is None
    job = JobStore(scenario.board).read(entry.job_id).job
    target = revision.resolve(job.target_node_id)
    proof = revision.resolve(target.proof)
    if target.id == "DN-001":
        await _assert_out_of_authority_plan_refused(scenario, start, target, proof)
    build_job_id, accept_job_id = _next_job_ids(scenario.board, 2)
    closure = _closure(revision, target)
    predecessor_acceptance = []
    for predecessor_job_id in job.predecessor_job_ids:
        predecessor = JobStore(scenario.board).read(predecessor_job_id, archived=True).job
        assert predecessor.receipt_id is not None
        predecessor_acceptance.append(predecessor.receipt_id)
    evidence: dict[str, object] = {"methods": list(proof.method)}
    packet: dict[str, object] = {
        "id": f"{target.id}-PK-001",
        "dependencies": [],
        "impact_closure": closure,
    }
    if predecessor_acceptance:
        evidence["predecessor_acceptance"] = predecessor_acceptance
        packet["predecessor_acceptance"] = predecessor_acceptance
    finished = await server.finish_plan(
        scenario.context,
        **_identity(start),
        finished_at=f"2026-07-28T00:{attempt + 1:02}:00Z",
        receipt_id=f"plan-{target.id.lower()}",
        code_revision=scenario.commit,
        evidence=evidence,
        node_plan={"mode": "build", "packets": [packet]},
        build_job_ids=(build_job_id,),
        accept_job_id=accept_job_id,
    )
    assert finished.diagnostic is None
    assert tuple(job.kind for job in finished.created_jobs) == ("build", "accept")
    return target, finished.created_jobs


async def _finish_build(scenario: _Scenario, job_id: int, attempt: int) -> None:
    revision = scenario.revision
    start = _start(job_id, attempt, scenario.commit) | {"change_id": revision.change_id}
    started = await server.start_job(scenario.context, **start)
    assert started.diagnostic is None
    job = JobStore(scenario.board).read(job_id).job
    target = revision.resolve(job.target_node_id)
    proof = revision.resolve(target.proof)
    finished = await server.finish_build(
        scenario.context,
        **_identity(start),
        finished_at=f"2026-07-28T00:{attempt + 1:02}:00Z",
        receipt_id=f"build-{target.id.lower()}-{job_id}",
        code_revision=scenario.commit,
        evidence={"methods": list(proof.method)},
        evidence_ids=(f"proof-{target.id.lower()}",),
        impact_closure=_closure(revision, target),
    )
    assert finished.diagnostic is None


async def _finish_accept(
    scenario: _Scenario,
    job_id: int,
    attempt: int,
    *,
    reconciliation_plan_job_ids: tuple[int, ...],
):
    revision = scenario.revision
    start = _start(job_id, attempt, scenario.commit) | {"change_id": revision.change_id}
    started = await server.start_job(scenario.context, **start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    assert started["checkout"].commit == scenario.commit
    job = JobStore(scenario.board).read(job_id).job
    target = revision.resolve(job.target_node_id)
    proof = revision.resolve(target.proof)
    evidence = _acceptance_evidence(
        scenario,
        started["checkout"],
        job,
        target,
        proof,
    )
    dependents = tuple(node for node in revision.graph.nodes if target.id in node.dependencies)
    evidence["reconciliation"] = [
        {"target_node_id": dependent.id, "plan_job_id": plan_job_id}
        for dependent, plan_job_id in zip(dependents, reconciliation_plan_job_ids, strict=True)
    ]
    finished = await server.finish_accept(
        scenario.context,
        **_identity(start),
        finished_at=f"2026-07-28T00:{attempt + 1:02}:00Z",
        receipt_id=f"accept-{target.id.lower()}",
        code_revision=scenario.commit,
        evidence=evidence,
        evidence_ids=(f"accept-proof-{target.id.lower()}",),
        impact_closure=_closure(revision, target),
        reconciliation_plan_job_ids=reconciliation_plan_job_ids,
    )
    assert finished.diagnostic is None
    return finished


async def _setup_scenario(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _git(consumer, "init", "--initial-branch=main")
    _git(consumer, "config", "user.name", "PROOF-013")
    _git(consumer, "config", "user.email", "proof-013@example.invalid")
    setup = _run(consumer, sys.executable, str(_REPO_ROOT / "setup" / "init.py"))

    work_root = consumer / ".owlbear" / "kanban"
    change_root = consumer / ".owlbear" / "changes"
    assert "OwlBear workspace initialised" in setup.stdout
    assert work_root.is_dir()
    assert change_root.is_dir()
    assert consumer.is_relative_to(tmp_path)
    assert not work_root.is_relative_to(_LIVE_CARRIER)
    assert not change_root.is_relative_to(_REPO_ROOT / ".owlbear" / "changes")
    assert not (consumer / ".owlbear" / "legacy").exists()

    _write_change(change_root)
    (consumer / "module-one").mkdir()
    (consumer / "module-two").mkdir()
    (consumer / "module-one" / "delivery.txt").write_text("defective\n", encoding="utf-8")
    (consumer / "module-two" / "delivery.txt").write_text("ready\n", encoding="utf-8")
    _git(consumer, "add", ".")
    _git(consumer, "commit", "-m", "fixture: initialize disposable consumer")
    base_commit = _git(consumer, "rev-parse", "HEAD")
    monkeypatch.chdir(consumer)

    loaded = load_change(change_root, _CHANGE_ID)
    assert loaded.diagnostics == ()
    assert loaded.revision is not None
    revision = loaded.revision
    checkouts = ProofCheckoutManager(consumer, tmp_path / "proof", change_root)
    app_context = AppContext(workspace=NativeWorkspace(work_root, timedelta(hours=1)))
    app_context.dispatch_runtimes[revision.change_id] = DispatchRuntime(
        NativeRuntime(
            revision,
            work_root,
            GitRepositoryHistory(consumer),
            timedelta(minutes=5),
            checkouts,
        ),
        work_root,
        checkouts,
    )
    context = MagicMock()
    context.request_context.lifespan_context = app_context

    shown = await server.show_change(context, change_id=revision.change_id)
    evidence = _evidence(revision)
    assessed = await server.validate_change(context, change_id=revision.change_id, evidence=evidence)
    admitted = await server.admit_change(context, change_id=revision.change_id, evidence=evidence)
    assert shown["delivery_digest"] == revision.delivery_digest
    assert all(finding["severity"] != "error" for finding in assessed["findings"]), assessed["findings"]
    assert admitted["receipt"] is not None
    assert len(admitted["generation"]["jobs"]) == 3
    return _Scenario(consumer, revision, work_root, context, base_commit)


async def _correct_first_node(scenario: _Scenario) -> _Scenario:
    revision = scenario.revision
    first_target, first_jobs = await _finish_plan(scenario, 1)
    assert first_target.id == "DN-001"
    first_build, first_accept = first_jobs
    await _finish_build(scenario, first_build.job_id, 2)

    first_start = _start(first_accept.job_id, 3, scenario.commit) | {"change_id": revision.change_id}
    started = await server.start_job(scenario.context, **first_start)
    assert isinstance(started, dict)
    assert started["start"].diagnostic is None
    corrective_job_id, replacement_job_id = _next_job_ids(scenario.board, 2)
    rejection = _rejection_payload(revision, first_start, scenario.commit)
    finding = rejection["findings"][0] | {"change_id": revision.change_id}
    invalidation = rejection["invalidation"] | {
        "invalidated_receipt_ids": (f"build-dn-001-{first_build.job_id}",),
        "corrective_job_ids": (corrective_job_id,),
    }
    rejected = await server.reject_accept(
        scenario.context,
        **(
            rejection
            | {
                "change_id": revision.change_id,
                "findings": (finding,),
                "invalidation": invalidation,
                "replacement_accept_job_id": replacement_job_id,
            }
        ),
    )
    assert rejected.diagnostic is None
    assert rejected.invalidation is not None
    assert tuple(job.job.kind for job in rejected.invalidation.corrective_jobs) == ("build",)
    assert rejected.replacement_accept is not None
    supersession_receipt_id = rejected.invalidation.supersession_receipt.receipt_id
    original_build_receipt = f"build-dn-001-{first_build.job_id}"
    currentness = ReceiptStore(revision).evaluate_currentness(
        original_build_receipt,
        GitRepositoryHistory(scenario.consumer),
        scenario.commit,
    )
    assert currentness.code.value == "ERR_RECEIPT_SUPERSEDED"
    blocked = await server.pick_jobs(
        scenario.context,
        change_id=revision.change_id,
        candidate_revision=scenario.commit,
        wave_size=3,
    )
    assert all(entry.job_id != rejected.replacement_accept.job.job_id for wave in blocked.waves for entry in wave)

    (scenario.consumer / "module-one" / "delivery.txt").write_text("corrected\n", encoding="utf-8")
    _git(scenario.consumer, "add", "module-one/delivery.txt")
    _git(scenario.consumer, "commit", "-m", "fix: correct disposable implementation")
    corrected = replace(
        scenario,
        commit=_git(scenario.consumer, "rev-parse", "HEAD"),
        supersession_receipt_id=supersession_receipt_id,
    )
    corrective_job = rejected.invalidation.corrective_jobs[0].job
    await _finish_build(corrected, corrective_job.job_id, 4)
    corrective_receipt_id = f"build-dn-001-{corrective_job.job_id}"
    corrected = replace(corrected, corrective_receipt_id=corrective_receipt_id)
    selected = await _pick_one(corrected, "accept")
    assert selected.job_id == rejected.replacement_accept.job.job_id
    replacement = await _finish_accept(
        corrected,
        rejected.replacement_accept.job.job_id,
        5,
        reconciliation_plan_job_ids=(_active_plan_id(scenario.board, "DN-002"),),
    )
    assert replacement.created_jobs == ()
    assert JobStore(scenario.board).read(_active_plan_id(scenario.board, "DN-002")).job.predecessor_job_ids == (
        rejected.replacement_accept.job.job_id,
    )
    return corrected


async def _complete_second_node(scenario: _Scenario) -> None:
    second_target, second_jobs = await _finish_plan(scenario, 6)
    assert second_target.id == "DN-002"
    second_build, second_accept = second_jobs
    await _finish_build(scenario, second_build.job_id, 7)
    second = await _finish_accept(
        scenario,
        second_accept.job_id,
        8,
        reconciliation_plan_job_ids=(_active_plan_id(scenario.board, "DN-014"),),
    )
    assert second.created_jobs == ()
    assert JobStore(scenario.board).read(_active_plan_id(scenario.board, "DN-014")).job.predecessor_job_ids == (
        second_accept.job_id,
    )


async def _complete_final_audit(scenario: _Scenario) -> None:
    revision = scenario.revision
    audit_target, audit_node_jobs = await _finish_plan(scenario, 9)
    assert audit_target.id == "DN-014"
    audit_build, audit_accept = audit_node_jobs
    await _finish_build(scenario, audit_build.job_id, 10)
    terminal = await _finish_accept(scenario, audit_accept.job_id, 11, reconciliation_plan_job_ids=())
    assert len(terminal.created_jobs) == 1
    audit_job = terminal.created_jobs[0]
    assert audit_job.kind == "audit"
    assert audit_job.target_node_id == "DN-014"

    audit_start = _start(audit_job.job_id, 12, scenario.commit) | {"change_id": revision.change_id}
    audit_started = await server.start_job(scenario.context, **audit_start)
    assert isinstance(audit_started, dict)
    assert audit_started["start"].diagnostic is None
    assert audit_started["checkout"].commit == scenario.commit
    evidence = await _audit_evidence(scenario, audit_started["checkout"], audit_job)
    finished = await server.finish_audit(
        scenario.context,
        **_identity(audit_start),
        finished_at="2026-07-28T00:13:00Z",
        receipt_id="audit-proof-013",
        code_revision=scenario.commit,
        evidence=evidence,
        evidence_ids=("PROOF-008", "PROOF-013"),
        impact_closure={
            "paths": ["module-one/", "module-two/"],
            "authority_targets": sorted(entity.id for entity in revision.graph.iter_entities()),
        },
    )
    assert finished.diagnostic is None
    assert finished.receipt is not None
    assert finished.receipt.receipt_id == "audit-proof-013"
    assert finished.receipt.payload["code_revision"] == scenario.commit
    assert finished.receipt.delivery_digest == revision.delivery_digest
    assert finished.receipt.payload["node_plan_digest"] == audit_job.node_plan_digest
    assert finished.receipt.payload["predecessor_receipt_ids"] == (
        "accept-dn-001",
        "accept-dn-002",
        "accept-dn-014",
    )
    assert finished.receipt.impact_closure is not None
    assert finished.receipt.impact_closure.model_dump(mode="json") == {
        "paths": ["/"],
        "authority_targets": sorted(entity.id for entity in revision.graph.iter_entities()),
    }
    assert finished.event is not None
    assert finished.event.evidence_ids == ("PROOF-008", "PROOF-013")
    accepted_receipts = finished.receipt.payload["evidence"]["accepted_receipts"]
    corrected_accept = next(receipt for receipt in accepted_receipts if receipt["target_node_id"] == "DN-001")
    assert corrected_accept["predecessor_receipt_ids"] == (scenario.corrective_receipt_id,)
    assert scenario.supersession_receipt_id is not None
    supersession = await server.show_receipt(
        scenario.context,
        change_id=revision.change_id,
        receipt_id=scenario.supersession_receipt_id,
    )
    assert supersession.kind == "supersession"
    health = await server.work_health(scenario.context, change_id=revision.change_id)
    assert health["findings"] == ()
    assert health["checked_paths"]


@pytest.mark.asyncio
async def test_fresh_consumer_completes_native_delivery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = await _setup_scenario(tmp_path, monkeypatch)
    corrected = await _correct_first_node(scenario)
    await _complete_second_node(corrected)
    await _complete_final_audit(corrected)
    assert not (scenario.consumer / ".owlbear" / "legacy").exists()
    if export_workspace := os.environ.get("PROOF_013_EXPORT_WORKSPACE"):
        shutil.copytree(scenario.consumer, Path(export_workspace), dirs_exist_ok=True)
