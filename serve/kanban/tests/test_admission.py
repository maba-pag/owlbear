from pathlib import Path

from owlbear_kanban import AdmissionEvidence, evaluate_admission, load_change


def test_admitted_revision_evaluates_without_findings() -> None:
    result = load_change(Path(".owlbear/changes"), "replace-delivery-pipeline")
    assert result.revision is not None

    assessment = evaluate_admission(
        result.revision,
        AdmissionEvidence(
            digest=result.revision.delivery_digest,
            challenge={"complete": True},
            baseline={"clean": True},
            approval={"approved": True},
            limits=("bootstrap",),
        ),
    )

    assert assessment.admitted
    assert assessment.findings == ()
