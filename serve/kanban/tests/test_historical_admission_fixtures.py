import json
from pathlib import Path

import pytest

from owlbear_kanban import AdmissionEvidence, evaluate_admission, load_change


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "historical-admission"
FIXTURES = {
    "r1-browser": {"defective": {("DV-004", "IF-001"), ("DV-007", "PROOF-001")}, "corrected": set()},
    "r2-workspace": {
        "defective": {("DV-004", "IF-001"), ("DV-005", "MIG-001"), ("DV-006", "RISK-001")},
        "corrected": set(),
    },
    "r3-memory-purge": {"defective": {("DV-007", "PROOF-001")}, "corrected": set()},
    "r4-memory-lifecycle": {
        "defective": {("DV-004", "IF-001"), ("DV-007", "PROOF-001")},
        "corrected": set(),
    },
}


def _evidence(revision):
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
        limits=("historical fixture",),
    )


@pytest.fixture(scope="module")
def fixture_root():
    return FIXTURE_ROOT


@pytest.mark.parametrize("fixture_name", tuple(FIXTURES))
@pytest.mark.parametrize("variant", ["defective", "corrected"])
def test_historical_four_file_fixture_admission_is_stable(fixture_root, fixture_name, variant):
    result = load_change(fixture_root, f"{fixture_name}-{variant}")
    assert result.revision is not None
    revision = result.revision
    assert {path.name for path in (fixture_root / f"{fixture_name}-{variant}").iterdir()} == {
        "intent.md",
        "design.md",
        "decisions.yaml",
        "graph.yaml",
    }
    assert revision.graph.admission.delivery_digest == revision.delivery_digest

    first = evaluate_admission(revision, _evidence(revision))
    second = evaluate_admission(revision, _evidence(revision))

    first_pairs = tuple((item.code, item.target) for item in first.findings)
    assert first_pairs == tuple((item.code, item.target) for item in second.findings)
    assert first.model_dump_json() == second.model_dump_json()
    assert json.loads(first.model_dump_json())["schema_version"] == 1
    expected_pairs = FIXTURES[fixture_name][variant]
    if variant == "corrected":
        assert first.admitted
        assert not first.findings
    else:
        assert not first.admitted
        assert set(first_pairs) == expected_pairs
