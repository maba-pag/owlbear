from pathlib import Path

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
