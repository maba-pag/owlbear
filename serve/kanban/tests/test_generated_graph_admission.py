from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from owlbear_kanban import (
    AdmissionEvidence,
    JobRecord,
    JobStore,
    compute_delivery_digest,
    evaluate_admission,
    load_change,
    validate_and_admit,
)
from owlbear_kanban.change import AdmissionMetadata, ChangeRevision, DeliveryGraph

_SEED = 2095
_TIMESTAMP = "2026-07-27T12:00:00Z"
_YAML_FILES = (
    "decisions.yaml",
    "delivery/obligations.yaml",
    "delivery/contracts.yaml",
    "delivery/nodes.yaml",
)


def _node_id(index: int) -> str:
    return f"DN-{index:03d}"


def _dependencies(family: str, index: int) -> list[str]:
    if index == 1:
        return []
    if family == "branching":
        return [_node_id((index - 2) // 2 + 1)]
    if family == "joining" and index == 4:
        return [_node_id(2), _node_id(3)]
    if family == "joining" and index in {2, 3}:
        return [_node_id(1)]
    return [_node_id(index - 1)]


def _authority(change_id: str, family: str, count: int, seed: int) -> dict[str, dict[str, object]]:
    generator = random.Random(seed)  # noqa: S311 - deterministic test data, not security-sensitive randomness.
    requirements = [
        {
            "id": f"REQ-{index:03d}",
            "title": f"Generated requirement {generator.randrange(1_000_000):06d}",
            "statement": f"Node {index} has one accountable generated obligation.",
            "workflows": [],
        }
        for index in range(1, count + 1)
    ]
    proofs = [
        {
            "id": f"PROOF-{index:03d}",
            "title": f"Generated proof {index}",
            "boundary": "Public generated graph admission",
            "owner": _node_id(index),
            "method": ["Load and admit generated modular authority"],
            "allowed_replacements": ["Temporary filesystem"],
            "durable_outputs": ["Generated admission contract test"],
        }
        for index in range(1, count + 1)
    ]
    nodes = [
        {
            "id": _node_id(index),
            "title": f"Generated node {index}",
            "outcome": f"Generated outcome {index}",
            "owns": [f"REQ-{index:03d}"],
            "supports": [],
            "modules": ["MOD-001"],
            "produces": ["IF-001"] if index == 1 else [],
            "consumes": ["IF-001"] if index == count else [],
            "dependencies": _dependencies(family, index),
            "risks": ["RISK-001"] if index == 1 else [],
            "proof": f"PROOF-{index:03d}",
        }
        for index in range(1, count + 1)
    ]
    common = {"schema_version": 1, "change_id": change_id}
    return {
        "decisions.yaml": {**common, "decisions": []},
        "delivery/obligations.yaml": {
            **common,
            "requirements": requirements,
            "negative_requirements": [],
            "preserved_behaviors": [],
            "workflows": [],
        },
        "delivery/contracts.yaml": {
            **common,
            "modules": [
                {
                    "id": "MOD-001",
                    "paths": ["serve/kanban/"],
                    "current_responsibility": "Generated graph admission",
                    "planned_change": "Prove general admission behavior",
                }
            ],
            "interfaces": [
                {
                    "id": "IF-001",
                    "name": "Generated delivery interface",
                    "producer": "DN-001",
                    "consumers": [_node_id(count)],
                    "contract": "Publish one generated delivery result",
                    "authority": "MOD-001",
                    "failure_semantics": "Admission rejects incomplete contracts",
                    "migration": "MIG-001",
                    "proof": "PROOF-001",
                }
            ],
            "migrations": [
                {
                    "id": "MIG-001",
                    "title": "Generated migration",
                    "owner": "DN-001",
                    "from": "Unadmitted generated authority",
                    "to": "Admitted generated authority",
                    "ordered_steps": ["Validate", "Publish"],
                    "consumer_inventory": ["Generated test consumer"],
                    "compatibility": "No compatibility path",
                    "deletion_owner": "DN-001",
                    "absence_proof": "PROOF-001",
                }
            ],
            "risks": [
                {
                    "id": "RISK-001",
                    "class": "correctness",
                    "title": "Generated topology drift",
                    "scenarios": ["Generated dependencies cease to be acyclic"],
                    "disposition": "Reject invalid generated authority",
                    "owner": "DN-001",
                    "proof": "PROOF-001",
                }
            ],
            "proofs": proofs,
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
            "nodes": nodes,
        },
    }


def _dump_documents(change_dir: Path, documents: dict[str, dict[str, object]]) -> None:
    for relative_path, document in documents.items():
        path = change_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False, width=120), encoding="utf-8")


def _load(changes_dir: Path, change_id: str) -> ChangeRevision:
    result = load_change(changes_dir, change_id)
    assert result.diagnostics == ()
    assert result.revision is not None
    return result.revision


def _bind_admission(changes_dir: Path, change_id: str) -> ChangeRevision:
    revision = _load(changes_dir, change_id)
    nodes_path = revision.source_dir / "delivery/nodes.yaml"
    nodes = yaml.safe_load(nodes_path.read_text(encoding="utf-8"))
    nodes["state"] = "admitted"
    nodes["admission"] = {
        "state": "admitted",
        "delivery_digest": revision.delivery_digest,
        "receipt": f"receipts/admission-{revision.delivery_digest[:12]}.yaml",
        "limits": ["Generated authority is test-only."],
    }
    nodes_path.write_text(yaml.safe_dump(nodes, sort_keys=False, width=120), encoding="utf-8")
    return _load(changes_dir, change_id)


def _generated_revision(
    tmp_path: Path,
    family: str,
    count: int,
    *,
    seed: int = _SEED,
) -> ChangeRevision:
    change_id = f"generated-{family}"
    changes_dir = tmp_path / "changes"
    change_dir = changes_dir / change_id
    change_dir.mkdir(parents=True)
    (change_dir / "intent.md").write_text("Prove generated graph admission.\n", encoding="utf-8")
    (change_dir / "design.md").write_text("Use deterministic modular authority.\n", encoding="utf-8")
    _dump_documents(change_dir, _authority(change_id, family, count, seed))
    return _bind_admission(changes_dir, change_id)


def _evidence(revision: ChangeRevision) -> AdmissionEvidence:
    challenge = {
        entity.id: {"disposition": "pass", "evidence": f"generated:{entity.id}"}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(revision.graph, section)
    }
    return AdmissionEvidence(
        digest=revision.delivery_digest,
        challenge=challenge,
        baseline={"commands": ("generated-admission",), "digest": revision.delivery_digest},
        approval={"approved": True, "digest": revision.delivery_digest},
        limits=("Generated authority is test-only.",),
    )


@pytest.mark.parametrize(
    ("family", "count"),
    [("single", 1), ("branching", 15), ("joining", 7), ("hundreds", 240)],
)
def test_generated_graph_families_publish_in_stable_topology_order_and_replay(
    tmp_path: Path,
    family: str,
    count: int,
) -> None:
    revision = _generated_revision(tmp_path, family, count)
    evidence = _evidence(revision)
    work_root = tmp_path / "work"
    work_root.mkdir()

    receipt, generation, assessment = validate_and_admit(
        revision,
        evidence,
        work_root,
        timestamp=_TIMESTAMP,
    )
    replayed = validate_and_admit(revision, evidence, work_root, timestamp=_TIMESTAMP)

    expected_targets = tuple(_node_id(index) for index in range(1, count + 1))
    assert assessment.findings == ()
    assert receipt is not None
    assert generation is not None
    assert tuple(job.target_node_id for job in generation.jobs) == expected_targets
    assert all(
        dependency in expected_targets[:index]
        for index, node in enumerate(revision.graph.nodes)
        for dependency in node.dependencies
    )
    assert replayed == (receipt, generation, assessment)
    assert tuple(stored.job for stored in JobStore(work_root).list()) == tuple(
        JobRecord(schema_version=1, **job.model_dump()) for job in generation.jobs
    )
    assert len(tuple((revision.source_dir / "receipts").glob("*.yaml"))) == 1
    assert len(tuple((revision.source_dir / "jobs").glob("*.yaml"))) == 1


def _rebind(revision: ChangeRevision, graph: DeliveryGraph) -> ChangeRevision:
    digest = compute_delivery_digest(revision.intent, revision.design, revision.decisions, graph)
    admitted = graph.model_copy(
        update={
            "admission": AdmissionMetadata(
                state="admitted",
                delivery_digest=digest,
                receipt=f"receipts/admission-{digest[:12]}.yaml",
                limits=("Generated authority is test-only.",),
            )
        }
    )
    return revision.model_copy(update={"graph": admitted, "delivery_digest": digest})


def _replace_node(revision: ChangeRevision, node_index: int, **updates: object) -> ChangeRevision:
    nodes = tuple(
        node.model_copy(update=updates) if index == node_index else node
        for index, node in enumerate(revision.graph.nodes)
    )
    return _rebind(revision, revision.graph.model_copy(update={"nodes": nodes}))


def _dangling_reference(revision: ChangeRevision) -> ChangeRevision:
    return _replace_node(revision, 0, dependencies=("DN-999",))


def _dependency_cycle(revision: ChangeRevision) -> ChangeRevision:
    return _replace_node(revision, 0, dependencies=(revision.graph.nodes[-1].id,))


def _disconnected_obligation(revision: ChangeRevision) -> ChangeRevision:
    return _replace_node(revision, 1, owns=())


def _duplicate_owner(revision: ChangeRevision) -> ChangeRevision:
    return _replace_node(revision, 1, owns=(*revision.graph.nodes[1].owns, "REQ-001"))


def _interface_omission(revision: ChangeRevision) -> ChangeRevision:
    return _replace_node(revision, len(revision.graph.nodes) - 1, consumes=())


def _migration_gap(revision: ChangeRevision) -> ChangeRevision:
    migration = revision.graph.migrations[0].model_copy(update={"ordered_steps": ()})
    return _rebind(revision, revision.graph.model_copy(update={"migrations": (migration,)}))


def _risk_disposition(revision: ChangeRevision) -> ChangeRevision:
    risk = revision.graph.risks[0].model_copy(update={"disposition": ""})
    return _rebind(revision, revision.graph.model_copy(update={"risks": (risk,)}))


def _proof_authorization(revision: ChangeRevision) -> ChangeRevision:
    proof = revision.graph.proofs[0].model_copy(update={"allowed_replacements": ()})
    proofs = (proof, *revision.graph.proofs[1:])
    return _rebind(revision, revision.graph.model_copy(update={"proofs": proofs}))


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (_dangling_reference, "DV-002"),
        (_dependency_cycle, "DV-008"),
        (_disconnected_obligation, "DV-003"),
        (_duplicate_owner, "DV-003"),
        (_interface_omission, "DV-004"),
        (_migration_gap, "DV-005"),
        (_risk_disposition, "DV-006"),
        (_proof_authorization, "DV-007"),
    ],
)
def test_generated_invalid_classes_return_exact_code_before_publication(
    tmp_path: Path,
    mutation: Callable[[ChangeRevision], ChangeRevision],
    expected_code: str,
) -> None:
    revision = mutation(_generated_revision(tmp_path, "invalid", 5))
    work_root = tmp_path / "work"

    receipt, generation, assessment = validate_and_admit(revision, _evidence(revision), work_root)

    assert {finding.code for finding in assessment.errors} == {expected_code}
    assert receipt is None
    assert generation is None
    assert not (revision.source_dir / "receipts").exists()
    assert not (revision.source_dir / "jobs").exists()
    assert not work_root.exists()


def _reverse_mappings(value: object) -> object:
    if isinstance(value, dict):
        return {key: _reverse_mappings(item) for key, item in reversed(tuple(value.items()))}
    if isinstance(value, list):
        return [_reverse_mappings(item) for item in value]
    return value


def test_generated_modular_loading_canonicalizes_key_order_wrapping_and_findings(tmp_path: Path) -> None:
    revision = _generated_revision(tmp_path, "semantic", 12, seed=_SEED)
    contracts_path = revision.source_dir / "delivery/contracts.yaml"
    contracts = yaml.safe_load(contracts_path.read_text(encoding="utf-8"))
    contracts["risks"][0]["disposition"] = ""
    contracts["proofs"][0]["allowed_replacements"] = []
    contracts_path.write_text(yaml.safe_dump(contracts, sort_keys=False, width=120), encoding="utf-8")
    revision = _bind_admission(revision.source_dir.parent, revision.change_id)
    first = evaluate_admission(revision, _evidence(revision))

    for relative_path in _YAML_FILES:
        path = revision.source_dir / relative_path
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        path.write_text(
            yaml.safe_dump(
                _reverse_mappings(document),
                sort_keys=False,
                width=35,
                explicit_start=True,
            ),
            encoding="utf-8",
        )

    reordered = _load(revision.source_dir.parent, revision.change_id)
    repeated = _load(revision.source_dir.parent, revision.change_id)
    second = evaluate_admission(reordered, _evidence(reordered))
    third = evaluate_admission(repeated, _evidence(repeated))

    assert revision.delivery_digest == reordered.delivery_digest == repeated.delivery_digest
    assert {finding.code for finding in first.errors} == {"DV-006", "DV-007"}
    assert first.findings == second.findings == third.findings
    assert tuple((item.code, item.target, item.detail) for item in second.findings) == tuple(
        sorted((item.code, item.target, item.detail) for item in second.findings)
    )
