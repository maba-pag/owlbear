"""Seed canonical native stores for the assembled Cockpit browser proof."""

# ruff: noqa: INP001
from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

from owlbear_kanban import (
    CorrectiveRouteRequest,
    FindingStore,
    GitRepositoryHistory,
    InvalidationRequest,
    JobGeneration,
    JobRecord,
    JobStore,
    KanbanEngine,
    NativeRuntime,
    PlanJob,
    ReceiptStore,
    load_change,
    plan_corrective_route,
)
from owlbear_kanban.change import (
    AuthorityMetadata,
    ChangeRevision,
    DecisionsDocument,
    DeliveryContractsDocument,
    DeliveryNode,
    DeliveryNodesDocument,
    DeliveryObligationsDocument,
    Interface,
    Module,
    Proof,
    Requirement,
    Risk,
)
from owlbear_kanban.runtime_requests import NativeRequest, NativeRequestRuntime
from owlbear_kanban.yaml_rt import make_yaml

CHANGE_ID = "replace-delivery-pipeline"
SCALE_CHANGE_ID = "scale-proof"
SCALE_NODE_COUNT = 300


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(  # noqa: S603 - arguments are controlled by this fixture.
        ["git", *args],  # noqa: S607 - Git is resolved from the test environment.
        cwd=repository,
        text=True,
    ).strip()


def _dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        make_yaml(explicit_start=True).dump(value, handle)


def _materialize(store: JobStore, record: JobRecord) -> None:
    generated = store.materialize(
        JobGeneration(
            schema_version=1,
            change_id=record.change_id,
            delivery_digest=record.delivery_digest,
            receipt_id=record.receipt_id or "seed-receipt",
            jobs=(
                PlanJob(
                    job_id=record.job_id,
                    kind="plan",
                    priority=record.priority,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    change_id=record.change_id,
                    delivery_digest=record.delivery_digest,
                    target_node_id=record.target_node_id,
                    receipt_id=record.receipt_id or "seed-receipt",
                ),
            ),
        )
    )[0]
    store.update(record, generated.token)


def _job(revision: ChangeRevision, job_id: int, kind: str, **changes: object) -> JobRecord:
    return JobRecord.model_validate(
        {
            "schema_version": 1,
            "job_id": job_id,
            "kind": kind,
            "priority": 1,
            "created_at": "2026-07-26T10:00:00Z",
            "updated_at": "2026-07-26T10:00:00Z",
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "target_node_id": "DN-011",
            **changes,
        }
    )


def _build_receipt(revision: ChangeRevision, code_revision: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "build",
        "receipt_id": "build-proof",
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "issued_at": "2026-07-26T10:01:00Z",
        "impact_closure": {"paths": ["serve/kanban/"], "authority_targets": ["DN-001", "PROOF-001"]},
        "target_node_id": "DN-001",
        "node_plan_digest": "b" * 64,
        "predecessor_receipt_ids": [],
        "evidence": {"commands": ["npm test", "npm run build"]},
        "code_revision": code_revision,
    }


def _seed_scale_change(changes_dir: Path) -> None:
    root = changes_dir / SCALE_CHANGE_ID
    root.mkdir(parents=True)
    (root / "intent.md").write_text(f"# Scale proof\n\nChange ID: {SCALE_CHANGE_ID}\n", encoding="utf-8")
    (root / "design.md").write_text(f"# Scale design\n\nChange ID: {SCALE_CHANGE_ID}\n", encoding="utf-8")
    _dump(
        root / "decisions.yaml",
        DecisionsDocument(schema_version=1, change_id=SCALE_CHANGE_ID, decisions=()).model_dump(mode="json"),
    )

    requirements = []
    modules = []
    interfaces = []
    risks = []
    proofs = []
    nodes = []
    for number in range(1, SCALE_NODE_COUNT + 1):
        suffix = f"{number:03d}"
        node_id = f"DN-{suffix}"
        requirement_id = f"REQ-{suffix}"
        module_id = f"MOD-{suffix}"
        interface_id = f"IF-{suffix}"
        risk_id = f"RISK-{suffix}"
        proof_id = f"PROOF-{suffix}"
        requirements.append(
            Requirement(
                id=requirement_id, title=f"Requirement {number}", statement=f"Scale requirement {number}", workflows=()
            )
        )
        modules.append(
            Module(
                id=module_id,
                paths=(f"serve/scale/{suffix}/",),
                current_responsibility="Scale fixture",
                planned_change="Scale fixture",
            )
        )
        interfaces.append(
            Interface(
                id=interface_id,
                name=f"Interface {number}",
                producer=node_id,
                consumers=((f"DN-{number + 1:03d}",) if number < SCALE_NODE_COUNT else ()),
                contract="Scale contract",
                authority=module_id,
                failure_semantics="Fail closed",
                migration=None,
                proof=proof_id,
            )
        )
        risks.append(
            Risk(
                id=risk_id,
                **{"class": "scale"},
                title=f"Risk {number}",
                scenarios=("Scale scenario",),
                disposition="Covered by scale proof",
                owner=node_id,
                proof=proof_id,
            )
        )
        proofs.append(
            Proof(
                id=proof_id,
                title=f"Proof {number}",
                boundary="Real FastAPI scale fixture",
                owner=node_id,
                method=("Browser geometry",),
                allowed_replacements=(),
                durable_outputs=("Playwright screenshot",),
            )
        )
        nodes.append(
            DeliveryNode(
                id=node_id,
                title=f"Delivery node {number}",
                outcome=f"Outcome {number}",
                owns=(requirement_id,),
                supports=(),
                modules=(module_id,),
                produces=(interface_id,),
                consumes=((f"IF-{number - 1:03d}",) if number > 1 else ()),
                dependencies=((f"DN-{number - 1:03d}",) if number > 1 else ()),
                risks=(risk_id,),
                proof=proof_id,
            )
        )

    _dump(
        root / "delivery" / "obligations.yaml",
        DeliveryObligationsDocument(
            schema_version=1,
            change_id=SCALE_CHANGE_ID,
            requirements=tuple(requirements),
            negative_requirements=(),
            preserved_behaviors=(),
            workflows=(),
        ).model_dump(mode="json"),
    )
    _dump(
        root / "delivery" / "contracts.yaml",
        DeliveryContractsDocument(
            schema_version=1,
            change_id=SCALE_CHANGE_ID,
            modules=tuple(modules),
            interfaces=tuple(interfaces),
            migrations=(),
            risks=tuple(risks),
            proofs=tuple(proofs),
        ).model_dump(mode="json", by_alias=True),
    )
    _dump(
        root / "delivery" / "nodes.yaml",
        DeliveryNodesDocument(
            schema_version=1,
            change_id=SCALE_CHANGE_ID,
            state="draft",
            authority=AuthorityMetadata(
                intent="intent.md", design="design.md", decisions="decisions.yaml", research=()
            ),
            admission=None,
            nodes=tuple(nodes),
        ).model_dump(mode="json"),
    )
    for node in nodes:
        _dump(
            root / "plans" / f"{node.id}.yaml",
            {
                "packets": [
                    {
                        "id": f"{node.id}-PK-001",
                        "dependencies": [],
                        "impact_closure": {"paths": ["serve/"], "authority_targets": [node.id, node.proof]},
                    }
                ]
            },
        )


def _seed_memory(memory_dir: Path) -> None:
    memory_dir.mkdir(parents=True)
    content = """---
id: 11111111-1111-4111-8111-111111111111
title: Native proof memory
categories: [process]
confidence: 0.9
state: pending
outstanding_count: 1
unremarkable_count: 0
didnt_use_count: 0
score: 0.9
scope_agents: [builder]
source_agent: builder
created_at: "2026-07-26T10:00:00Z"
updated_at: "2026-07-26T10:00:00Z"
approved_at: null
contested_by_task: null
---

Memory continuity over the native Cockpit shell.
"""
    (memory_dir / "11111111-1111-4111-8111-111111111111.md").write_text(content, encoding="utf-8")


def _load_proof_revision(changes_dir: Path) -> ChangeRevision:
    loaded = load_change(changes_dir, CHANGE_ID)
    scale = load_change(changes_dir, SCALE_CHANGE_ID)
    if loaded.revision is None or scale.revision is None or len(scale.revision.graph.nodes) != SCALE_NODE_COUNT:
        message = f"native proof fixtures failed validation: {loaded.diagnostics} {scale.diagnostics}"
        raise RuntimeError(message)
    return loaded.revision


def _seed_native_work(revision: ChangeRevision, work_root: Path, workspace: Path, head: str) -> None:
    receipts = ReceiptStore(revision)
    if receipts.create("build-proof", _build_receipt(revision, head)).receipt is None:
        message = "build receipt was not created"
        raise RuntimeError(message)
    jobs = JobStore(work_root)
    _materialize(jobs, _job(revision, 1, "build", receipt_id="build-proof", target_node_id="DN-001"))
    _materialize(jobs, _job(revision, 2, "accept"))
    request_runtime = NativeRequestRuntime(revision, work_root)
    for offset, viewport in enumerate(("desktop", "mobile"), start=3):
        request_id = f"request-{viewport}"
        _materialize(jobs, _job(revision, offset, "build", pending_request_ids=(request_id,)))
        request_runtime.create_request(
            NativeRequest(
                request_id=request_id,
                kind="action",
                title=f"Provide {viewport} proof signature",
                summary="A linked job needs signed evidence.",
                body="Return the signed proof value.",
                agent="builder",
                created_at=f"2026-07-26T10:0{offset}:00Z",
                change_id=revision.change_id,
                delivery_digest=revision.delivery_digest,
                target_node_id="DN-011",
                job_ids=(offset,),
                evidence=("signature=proof",),
                resume_condition="The proof signature is supplied.",
            )
        )
    finding = {
        "schema_version": 1,
        "finding_id": "finding-proof",
        "source_attempt_id": "attempt-build-proof",
        "source_job_id": 1,
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "target_kind": "packet",
        "target_id": "DN-001-PK-001",
        "finding_class": "implementation-defect",
        "detail": "Corrective history fixture",
        "created_at": "2026-07-26T10:03:00Z",
    }
    if FindingStore(work_root).create("finding-proof", finding).finding is None:
        message = "finding was not created"
        raise RuntimeError(message)
    route = plan_corrective_route(
        CorrectiveRouteRequest(
            finding_id="finding-proof",
            finding_class="implementation-defect",
            target="packet-implementation",
            target_node_ids=("DN-001",),
        )
    )
    runtime = NativeRuntime(revision, work_root, GitRepositoryHistory(workspace), timedelta(minutes=5))
    outcome = runtime.invalidate(
        InvalidationRequest(
            invalidation_id="invalidation-proof",
            supersession_receipt_id="supersession-proof",
            invalidated_receipt_ids=("build-proof",),
            routes=(route,),
            corrective_job_ids=(20,),
            issued_at="2026-07-26T10:04:00Z",
            code_revision=head,
        )
    )
    if outcome.outcome is None:
        message = f"invalidation was not created: {outcome.diagnostic}"
        raise RuntimeError(message)


def main() -> None:
    """Create one temporary project with primary and scale proof fixtures."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    workspace = args.workspace.resolve()
    changes_dir = workspace / ".owlbear" / "changes"
    work_root = workspace / ".owlbear" / "kanban"
    source = project_root / ".owlbear" / "changes" / CHANGE_ID
    shutil.copytree(source, changes_dir / CHANGE_ID)
    shutil.rmtree(changes_dir / CHANGE_ID / "receipts", ignore_errors=True)
    shutil.rmtree(changes_dir / CHANGE_ID / "jobs", ignore_errors=True)
    _seed_scale_change(changes_dir)
    (work_root / "tasks").mkdir(parents=True)
    (work_root / "archive").mkdir()
    _seed_memory(workspace / ".owlbear" / "memory")
    (workspace / ".owlbear" / "ideas.md").write_text(
        "# Native proof ideas\n\n- [ ] Preserve Ideas continuity\n", encoding="utf-8"
    )

    _git(workspace, "init", "-q")
    _git(workspace, "add", ".")
    subprocess.check_call(
        [  # noqa: S607 - Git is resolved from the test environment.
            "git",
            "-c",
            "user.name=OwlBear Proof",
            "-c",
            "user.email=proof@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=workspace,
    )
    head = _git(workspace, "rev-parse", "HEAD")

    revision = _load_proof_revision(changes_dir)
    _seed_native_work(revision, work_root, workspace, head)
    engine = KanbanEngine(work_root)
    legacy_task = engine.create_task("Legacy proof task", status="build", priority="high")
    engine.create_request(legacy_task.id, "action", "Legacy proof request", "Historical only.", "builder")


if __name__ == "__main__":
    main()
