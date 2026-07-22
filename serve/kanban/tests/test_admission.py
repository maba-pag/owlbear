from pathlib import Path

from owlbear_kanban import AdmissionEvidence, evaluate_admission, load_change


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
