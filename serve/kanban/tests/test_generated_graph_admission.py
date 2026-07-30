from __future__ import annotations

import random
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from owlbear_kanban import (
    AdmissionEvidence,
    ChangeDiagnosticCode,
    DispatchRuntime,
    JobRecord,
    JobStore,
    NativeRuntime,
    evaluate_admission,
    load_change,
    validate_and_admit,
)
from owlbear_kanban.change import ChangeRevision

_SEED = 2095
_TIMESTAMP = "2026-07-27T12:00:00Z"
_YAML_FILES = (
    "decisions.yaml",
    "delivery/obligations.yaml",
    "delivery/contracts.yaml",
    "delivery/nodes.yaml",
)
_SCRAMBLED_TOPOLOGY = ("DN-001", "DN-003", "DN-002", "DN-005", "DN-004", "DN-007", "DN-006")


def _node_id(index: int) -> str:
    return f"DN-{index:03d}"


def _dependencies(family: str, index: int) -> list[str]:
    if family == "scrambled":
        topology_index = _SCRAMBLED_TOPOLOGY.index(_node_id(index))
        return [] if topology_index == 0 else [_SCRAMBLED_TOPOLOGY[topology_index - 1]]
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
    if family == "scrambled":
        nodes.reverse()
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


class _History:
    def revisions_exist(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def is_descendant(self, _tested_revision: str, _candidate_revision: str) -> bool:
        return True

    def name_status(self, _tested_revision: str, _candidate_revision: str) -> bytes:
        return b""


@pytest.mark.parametrize(
    ("family", "count"),
    [("single", 1), ("branching", 15), ("joining", 7), ("scrambled", 7), ("hundreds", 240)],
)
def test_generated_graph_families_publish_authored_order_dispatch_topology_and_replay(
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

    authored_targets = tuple(node.id for node in revision.graph.nodes)
    topology_targets = (
        _SCRAMBLED_TOPOLOGY if family == "scrambled" else tuple(_node_id(index) for index in range(1, count + 1))
    )
    assert assessment.findings == ()
    assert receipt is not None
    assert generation is not None
    assert tuple(job.target_node_id for job in generation.jobs) == authored_targets
    runtime = DispatchRuntime(
        NativeRuntime(revision, work_root, _History(), timedelta(minutes=5)),
        work_root,
    )
    plan = runtime.pick_waves(revision.delivery_digest, size=count)
    dispatched_targets = tuple(
        JobStore(work_root).read(entry.job_id).job.target_node_id for wave in plan.waves for entry in wave
    )
    assert dispatched_targets == topology_targets
    dispatched_positions = {target: index for index, target in enumerate(dispatched_targets)}
    assert all(
        dispatched_positions[dependency] < dispatched_positions[node.id]
        for node in revision.graph.nodes
        for dependency in node.dependencies
    )
    if family == "scrambled":
        assert authored_targets == tuple(sorted(topology_targets, reverse=True))
        assert topology_targets != tuple(sorted(topology_targets))
    assert replayed == (receipt, generation, assessment)
    assert tuple(stored.job for stored in JobStore(work_root).list()) == tuple(
        JobRecord(schema_version=1, **job.model_dump()) for job in generation.jobs
    )
    assert len(tuple((revision.source_dir / "receipts").glob("*.yaml"))) == 1
    assert len(tuple((revision.source_dir / "jobs").glob("*.yaml"))) == 1


def _mutate_document(revision: ChangeRevision, relative_path: str, mutation: Callable[[dict], None]) -> None:
    path = revision.source_dir / relative_path
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutation(document)
    path.write_text(yaml.safe_dump(document, sort_keys=False, width=120), encoding="utf-8")


def _dependency_cycle(document: dict) -> None:
    document["nodes"][0]["dependencies"] = [document["nodes"][-1]["id"]]


def _disconnected_obligation(document: dict) -> None:
    document["nodes"][1]["owns"] = []


def _duplicate_owner(document: dict) -> None:
    document["nodes"][1]["owns"].append("REQ-001")


def _interface_omission(document: dict) -> None:
    document["nodes"][-1]["consumes"] = []


def _migration_gap(document: dict) -> None:
    document["migrations"][0]["ordered_steps"] = []


def _risk_disposition(document: dict) -> None:
    document["risks"][0]["disposition"] = ""


def _proof_authorization(document: dict) -> None:
    document["proofs"][0]["allowed_replacements"] = []


def _proof_boundary_collision(document: dict) -> None:
    document["proofs"][0]["boundary"] = "  TEMPORARY FILESYSTEM  "


def test_generated_dangling_reference_is_rejected_by_canonical_loader(tmp_path: Path) -> None:
    revision = _generated_revision(tmp_path, "dangling", 5)
    _mutate_document(
        revision,
        "delivery/nodes.yaml",
        lambda document: document["nodes"][0].update(dependencies=["DN-999"]),
    )

    result = load_change(revision.source_dir.parent, revision.change_id)

    assert result.revision is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == [ChangeDiagnosticCode.REFERENCE_MISSING]
    assert not (revision.source_dir / "receipts").exists()
    assert not (revision.source_dir / "jobs").exists()


@pytest.mark.parametrize(
    ("relative_path", "mutation", "expected_code"),
    [
        ("delivery/nodes.yaml", _dependency_cycle, "DV-008"),
        ("delivery/nodes.yaml", _disconnected_obligation, "DV-003"),
        ("delivery/nodes.yaml", _duplicate_owner, "DV-003"),
        ("delivery/nodes.yaml", _interface_omission, "DV-004"),
        ("delivery/contracts.yaml", _migration_gap, "DV-005"),
        ("delivery/contracts.yaml", _risk_disposition, "DV-006"),
        ("delivery/contracts.yaml", _proof_authorization, "DV-007"),
        ("delivery/contracts.yaml", _proof_boundary_collision, "DV-009"),
    ],
)
def test_generated_yaml_mutations_return_exact_admission_code_before_publication(
    tmp_path: Path,
    relative_path: str,
    mutation: Callable[[dict], None],
    expected_code: str,
) -> None:
    revision = _generated_revision(tmp_path, "invalid", 5)
    _mutate_document(revision, relative_path, mutation)
    revision = _bind_admission(revision.source_dir.parent, revision.change_id)
    work_root = tmp_path / "work"

    receipt, generation, assessment = validate_and_admit(revision, _evidence(revision), work_root)

    assert tuple(finding.code for finding in assessment.errors) == (expected_code,)
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
