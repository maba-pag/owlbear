from pathlib import Path

import pytest

from owlbear_kanban import AdmissionEvidence, evaluate_admission, load_change


def _admission_evidence(revision):
    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(revision.graph, section)
    }
    return AdmissionEvidence(
        digest=revision.delivery_digest,
        challenge=challenge,
        baseline={"commands": ("pytest",), "digest": revision.delivery_digest},
        approval={"approved": True, "digest": revision.delivery_digest},
        limits=("bootstrap",),
    )


def _with_nodes(revision, nodes):
    graph = revision.graph.model_copy(update={"nodes": nodes})
    return revision.model_copy(update={"graph": graph})


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda revision: _with_nodes(
                revision,
                tuple(
                    node.model_copy(update={"dependencies": (*node.dependencies, "DN-002")})
                    if node.id == "DN-001"
                    else node
                    for node in revision.graph.nodes
                ),
            ),
            "DV-008",
        ),
        (
            lambda revision: _with_nodes(
                revision,
                tuple(
                    node.model_copy(update={"dependencies": ()}) if node.id == "DN-010" else node
                    for node in revision.graph.nodes
                ),
            ),
            "DV-008",
        ),
        (
            lambda revision: _with_nodes(
                revision,
                tuple(
                    node.model_copy(update={"produces": ("REQ-001",)}) if node.id == "DN-010" else node
                    for node in revision.graph.nodes
                ),
            ),
            "DV-011",
        ),
        (
            lambda revision: revision.model_copy(
                update={
                    "graph": revision.graph.model_copy(
                        update={
                            "interfaces": tuple(
                                interface.model_copy(update={"producer": "DN-010"})
                                if interface.id == "IF-001"
                                else interface
                                for interface in revision.graph.interfaces
                            )
                        }
                    )
                }
            ),
            "DV-008",
        ),
    ],
)
def test_graph_mutations_return_expected_public_finding(mutation, code) -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    revision = mutation(result.revision)
    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == code for item in assessment.errors)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda revision: revision.model_copy(
            update={
                "decisions": revision.decisions.model_copy(
                    update={
                        "decisions": tuple(
                            decision.model_copy(update={"status": "pending"}) if decision.id == "DEC-001" else decision
                            for decision in revision.decisions.decisions
                        )
                    }
                )
            }
        ),
        lambda revision: revision.model_copy(
            update={
                "graph": revision.graph.model_copy(
                    update={"admission": revision.graph.admission.model_copy(update={"delivery_digest": "0" * 64})}
                )
            }
        ),
        lambda revision: revision.model_copy(
            update={
                "decisions": revision.decisions.model_copy(
                    update={
                        "decisions": tuple(
                            decision.model_copy(update={"selected": None}) if decision.id == "DEC-001" else decision
                            for decision in revision.decisions.decisions
                        )
                    }
                )
            }
        ),
    ],
)
def test_authority_mutations_return_dv010(mutation) -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    revision = mutation(result.revision)
    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == "DV-010" for item in assessment.errors)


def test_admitted_dag_is_silent_and_findings_are_deterministic() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    assessment = evaluate_admission(result.revision, _admission_evidence(result.revision))
    repeated = evaluate_admission(result.revision, _admission_evidence(result.revision))

    assert not {item.code for item in assessment.errors} & {"DV-008", "DV-010", "DV-011"}
    assert assessment.findings == repeated.findings


def test_invalid_graph_findings_are_sorted() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    revision = _with_nodes(
        result.revision,
        tuple(
            node.model_copy(update={"dependencies": ()}) if node.id == "DN-010" else node
            for node in result.revision.graph.nodes
        ),
    )

    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert tuple((item.code, item.target) for item in assessment.findings) == tuple(
        sorted((item.code, item.target) for item in assessment.findings)
    )


def test_admitted_revision_evaluates_without_findings() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(result.revision.graph, section)
    }
    assessment = evaluate_admission(
        result.revision,
        AdmissionEvidence(
            digest=result.revision.delivery_digest,
            challenge=challenge,
            baseline={"commands": ("pytest",), "digest": result.revision.delivery_digest},
            approval={"approved": True, "digest": result.revision.delivery_digest},
            limits=("bootstrap",),
        ),
    )

    assert assessment.admitted
    assert assessment.findings == ()


def test_free_form_pass_does_not_satisfy_challenge_gate() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    assessment = evaluate_admission(
        result.revision,
        AdmissionEvidence(
            digest=result.revision.delivery_digest,
            challenge={"pass": True},
            baseline={"commands": ("pytest",)},
            approval={"approved": True},
            limits=("bootstrap",),
        ),
    )

    assert not assessment.admitted
    assert any(item.code == "EV-002" for item in assessment.errors)


def test_baseline_and_approval_must_bind_to_revision_digest() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    challenge = {
        entity.id: {"disposition": "pass", "evidence": entity.id}
        for section in ("requirements", "workflows", "interfaces", "migrations", "risks", "proofs", "nodes")
        for entity in getattr(result.revision.graph, section)
    }
    assessment = evaluate_admission(
        result.revision,
        AdmissionEvidence(
            digest=result.revision.delivery_digest,
            challenge=challenge,
            baseline={"commands": ("pytest",)},
            approval={"approved": True},
            limits=("bootstrap",),
        ),
    )

    assert not assessment.admitted
    assert {item.code for item in assessment.errors} == {"EV-003", "EV-004"}


def test_duplicate_accountable_ownership_returns_dv003() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    graph = result.revision.graph
    duplicate = graph.nodes[0].model_copy(update={"owns": (*graph.nodes[0].owns, "REQ-002")})
    revision = result.revision.model_copy(
        update={"graph": graph.model_copy(update={"nodes": (duplicate, *graph.nodes[1:])})}
    )

    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == "DV-003" and item.target == "REQ-002" for item in assessment.errors)


def test_interface_without_migration_disposition_returns_dv004() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    graph = result.revision.graph
    interface = next(item for item in graph.interfaces if item.migration is not None)
    replacement = interface.model_copy(update={"migration": "MIG-999"})
    interfaces = tuple(replacement if item.id == interface.id else item for item in graph.interfaces)
    revision = result.revision.model_copy(update={"graph": graph.model_copy(update={"interfaces": interfaces})})

    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == "DV-004" and item.target == interface.id for item in assessment.errors)


def test_interface_without_consumers_returns_dv004() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    graph = result.revision.graph
    interface = graph.interfaces[0]
    replacement = interface.model_copy(update={"consumers": ()})
    interfaces = tuple(replacement if item.id == interface.id else item for item in graph.interfaces)
    revision = result.revision.model_copy(update={"graph": graph.model_copy(update={"interfaces": interfaces})})

    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == "DV-004" and item.target == interface.id for item in assessment.errors)


def test_proof_owner_outside_acceptance_predecessors_returns_dv007() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None
    graph = result.revision.graph
    proof = next(item for item in graph.proofs if item.id == "PROOF-007")
    owner = next(item for item in graph.nodes if item.id == "DN-010")
    proofs = tuple(
        proof.model_copy(update={"owner": owner.id}) if item.id == proof.id else item for item in graph.proofs
    )
    nodes = tuple(owner.model_copy(update={"proof": proof.id}) if item.id == owner.id else item for item in graph.nodes)
    revision = result.revision.model_copy(update={"graph": graph.model_copy(update={"proofs": proofs, "nodes": nodes})})

    assessment = evaluate_admission(revision, _admission_evidence(revision))

    assert any(item.code == "DV-007" and item.target == proof.id for item in assessment.errors)
