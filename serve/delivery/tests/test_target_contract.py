from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from owlbear_delivery import DeliveryCommitmentClass, DeliveryCompilationDiagnosticCode, compile_delivery_contract
from owlbear_delivery.target_contract import contract_canonical_bytes, parse_delivery_contract

_DECISION = """```yaml target-contract
kind: decision
id: DEC-001
origin: decided
basis: askQuestions 2026-10-08 "Keep compilation deterministic?"
statement: Compilation stays deterministic.
```
"""
_COMMITMENT = """```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
decisions: [DEC-001]
statement: Keep compilation deterministic.
```
"""
_OUTCOME = """```yaml target-contract
kind: outcome
id: OUT-001
title: Compile authority
promise: Authored definitions become authority.
acceptance: [Compilation succeeds.]
commitments: [COM-001]
dependencies: [{dependencies}]
```
"""
_INTENT_COMMITMENTS = (
    ("COM-001", "dealbreaker", "Compilation is deterministic."),
    ("COM-002", "protected-request", "Invalid definitions fail closed."),
    ("COM-003", "important-reviewed", "Authored order is preserved."),
    ("COM-004", "agreed-path", "Every outcome receives a planning scope."),
    ("COM-005", "implementation-discretion", "Diagnostics use stable categories."),
    ("COM-006", "dealbreaker", "Source bytes remain bound to authority."),
)
_DESIGN_COMMITMENTS = (
    ("COM-007", "agreed-path", "Intent definitions precede design definitions."),
    ("COM-008", "important-reviewed", "Outcome dependencies form a directed acyclic graph."),
    ("COM-009", "protected-request", "Canonical JSON has one stable encoding."),
    ("COM-010", "agreed-path", "Architecture definitions share the public schema."),
    ("COM-011", "implementation-discretion", "Internal parsing strategy may vary."),
)
_INTENT_OUTCOMES = (
    ("OUT-001", ("COM-001", "COM-002"), ()),
    ("OUT-002", ("COM-003",), ("OUT-001",)),
    ("OUT-003", ("COM-004",), ("OUT-001",)),
    ("OUT-004", ("COM-005",), ("OUT-002",)),
    ("OUT-005", ("COM-006",), ("OUT-003",)),
)
_DESIGN_OUTCOMES = (
    ("OUT-006", ("COM-007",), ("OUT-003", "OUT-005")),
    ("OUT-007", ("COM-008",), ("OUT-006",)),
    ("OUT-008", ("COM-009",), ("OUT-004",)),
    ("OUT-009", ("COM-010",), ("OUT-007", "OUT-008")),
    ("OUT-010", ("COM-011",), ("OUT-009",)),
)


def _commitment_block(identity: str, commitment_class: str, statement: str, _source: str) -> str:
    return f"""```yaml target-contract
kind: commitment
id: {identity}
class: {commitment_class}
decisions: [DEC-001]
statement: {statement}
```
"""


def _outcome_block(identity: str, commitments: tuple[str, ...], dependencies: tuple[str, ...]) -> str:
    commitment_list = ", ".join(commitments)
    dependency_list = ", ".join(dependencies)
    return f"""```yaml target-contract
kind: outcome
id: {identity}
title: Fixture result {identity}
promise: Deliver the observable result for {identity}.
acceptance: [{identity} can be observed.]
commitments: [{commitment_list}]
dependencies: [{dependency_list}]
```
"""


def _specification_fixture() -> tuple[bytes, bytes]:
    intent = "# Self-Contained Delivery Contract\n\nRepresentative intent.\n\n" + "\n".join(
        [
            _DECISION,
            *(_commitment_block(*definition, "intent") for definition in _INTENT_COMMITMENTS),
            *(_outcome_block(*definition) for definition in _INTENT_OUTCOMES),
        ]
    )
    design = "# Fixture Architecture\n\nRepresentative architecture.\n\n" + "\n".join(
        [
            *(_commitment_block(*definition, "design") for definition in _DESIGN_COMMITMENTS),
            *(_outcome_block(*definition) for definition in _DESIGN_OUTCOMES),
        ]
    )
    return intent.encode(), design.encode()


def test_specification_compiles_to_complete_replayable_contract() -> None:
    intent_bytes, design_bytes = _specification_fixture()

    result = compile_delivery_contract("fixture-delivery", intent_bytes, design_bytes)
    replay = compile_delivery_contract("fixture-delivery", intent_bytes, design_bytes)

    assert result.diagnostics == ()
    assert result.contract is not None
    assert result.canonical_bytes is not None
    assert result.digest is not None
    assert result == replay
    assert result.contract.title == "Self-Contained Delivery Contract"
    assert len(result.contract.commitments) == 11
    assert len(result.contract.outcomes) == len(result.contract.plan_scopes) == 10
    assert tuple(item.commitment_id for item in result.contract.commitments) == tuple(
        definition[0] for definition in (*_INTENT_COMMITMENTS, *_DESIGN_COMMITMENTS)
    )
    assert tuple(item.outcome_id for item in result.contract.outcomes) == tuple(
        definition[0] for definition in (*_INTENT_OUTCOMES, *_DESIGN_OUTCOMES)
    )
    assert result.contract.commitments[-1].commitment_class is DeliveryCommitmentClass.IMPLEMENTATION_DISCRETION
    assert result.contract.outcomes[5].dependency_ids == ("OUT-003", "OUT-005")
    assert tuple((scope.scope_id, scope.outcome_id) for scope in result.contract.plan_scopes) == tuple(
        (f"SCOPE-{index:03}", f"OUT-{index:03}") for index in range(1, 11)
    )
    assert tuple(binding.sha256 for binding in result.contract.source_bindings) == tuple(
        hashlib.sha256(source).hexdigest() for source in (intent_bytes, design_bytes)
    )
    expected_canonical = (
        json.dumps(
            result.contract.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
    assert result.canonical_bytes == expected_canonical
    assert result.digest == hashlib.sha256(result.canonical_bytes).hexdigest()

    changed_design = design_bytes + b"\nNon-normative architecture note.\n"
    changed = compile_delivery_contract("fixture-delivery", intent_bytes, changed_design)
    assert changed.diagnostics == ()
    assert changed.contract is not None
    assert changed.contract.title == result.contract.title
    assert changed.contract.commitments == result.contract.commitments
    assert changed.contract.outcomes == result.contract.outcomes
    assert changed.contract.plan_scopes == result.contract.plan_scopes
    assert changed.contract.source_bindings[1].sha256 == hashlib.sha256(changed_design).hexdigest()
    assert changed.contract.source_bindings[1] != result.contract.source_bindings[1]
    assert changed.digest != result.digest


@pytest.mark.parametrize(
    ("addition", "dependencies", "expected_codes"),
    [
        ("```yaml target-contract\nkind: [\n```\n", "", (DeliveryCompilationDiagnosticCode.YAML_INVALID,)),
        (
            "```yaml target-contract\nkind: limitation\nid: LIM-001\n```\n",
            "",
            (DeliveryCompilationDiagnosticCode.KIND_UNKNOWN,),
        ),
        (
            """```yaml target-contract
kind: commitment
id: COM-002
class: agreed-path
decisions: [DEC-001]
statement: Reject unknown keys.
warning: do not accept
```
""",
            "",
            (DeliveryCompilationDiagnosticCode.KEY_UNKNOWN,),
        ),
        (_COMMITMENT, "", (DeliveryCompilationDiagnosticCode.IDENTITY_DUPLICATE,)),
        (
            """```yaml target-contract
kind: outcome
id: OUT-002
title: Invalid references
promise: This definition must fail.
acceptance: [References resolve.]
commitments: [COM-999]
dependencies: [OUT-999]
```
""",
            "",
            (
                DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
                DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
            ),
        ),
        (
            """```yaml target-contract
kind: outcome
id: OUT-002
title: Cyclic outcome
promise: This definition must fail.
acceptance: [Dependencies are acyclic.]
commitments: [COM-001]
dependencies: [OUT-001]
```
""",
            "OUT-002",
            (DeliveryCompilationDiagnosticCode.DEPENDENCY_CYCLE,),
        ),
    ],
    ids=("malformed-yaml", "unknown-kind", "unknown-key", "duplicate", "unresolved", "cycle"),
)
def test_definition_failures_return_stable_diagnostics_without_partial_contract(
    addition: str,
    dependencies: str,
    expected_codes: tuple[DeliveryCompilationDiagnosticCode, ...],
) -> None:
    intent = (
        f"# Sample Change\n\n{_DECISION}\n{_COMMITMENT}\n{_OUTCOME.format(dependencies=dependencies)}\n{addition}"
    ).encode()

    result = compile_delivery_contract("sample-change", intent, b"# Sample Design\n")

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == expected_codes
    assert all(diagnostic.source_name == "intent.md" for diagnostic in result.diagnostics)
    assert result.contract is result.canonical_bytes is result.digest is None


def _decision(identity: str, origin: str, *, supersedes: str = "", basis: str = "askQuestions fixture") -> str:
    supersession = f"supersedes: [{supersedes}]\n" if supersedes else ""
    return f"""```yaml target-contract
kind: decision
id: {identity}
origin: {origin}
basis: {basis}
statement: Decision {identity}.
{supersession}```
"""


def _decision_change(decisions: str, commitment_decisions: str = "DEC-001") -> bytes:
    commitment = _COMMITMENT.replace("decisions: [DEC-001]", f"decisions: [{commitment_decisions}]")
    return f"# Sample Change\n\n{decisions}\n{commitment}\n{_OUTCOME.format(dependencies='')}".encode()


def test_decisions_compile_with_origin_supersession_history_and_active_links() -> None:
    decisions = "\n".join(
        (
            _decision("DEC-001", "approved"),
            _decision("DEC-002", "autonomous"),
            _decision("DEC-003", "approved", supersedes="DEC-002"),
            _decision("DEC-004", "decided", supersedes="REQ-ANSWERED", basis="request REQ-OTHER"),
        )
    )

    result = compile_delivery_contract("sample-change", _decision_change(decisions, "DEC-001, DEC-003"), b"# D\n")

    assert result.diagnostics == ()
    assert result.contract is not None
    assert result.contract.schema_version == 3
    assert [(item.decision_id, item.origin.value) for item in result.contract.decisions] == [
        ("DEC-001", "approved"),
        ("DEC-002", "autonomous"),
        ("DEC-003", "approved"),
        ("DEC-004", "decided"),
    ]
    assert [item.decision_id for item in result.contract.active_decisions()] == ["DEC-001", "DEC-003", "DEC-004"]
    assert result.contract.superseded_request_ids() == frozenset({"REQ-ANSWERED"})
    assert result.contract.commitments[0].decision_ids == ("DEC-001", "DEC-003")
    assert result.contract.commitments[0].provenance is None
    payload = json.loads(result.canonical_bytes or b"{}")
    assert "provenance" not in payload["commitments"][0]
    assert payload["decisions"][2]["supersedes"] == ["DEC-002"]


_DECIDED = _decision("DEC-001", "decided")


@pytest.mark.parametrize(
    ("decisions", "links", "expected"),
    [
        (_decision("DEC-001", "unsure"), "DEC-001", (DeliveryCompilationDiagnosticCode.VALUE_INVALID,)),
        (
            _DECIDED.replace("basis: askQuestions fixture\n", ""),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.KEY_MISSING,),
        ),
        (
            _DECIDED + _decision("DEC-001", "approved"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.IDENTITY_DUPLICATE,),
        ),
        (
            _DECIDED + _decision("DEC-002", "decided", supersedes="DEC-404"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,),
        ),
        (
            _decision("DEC-001", "decided", supersedes="DEC-001"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID,),
        ),
        (
            _DECIDED
            + _decision("DEC-002", "decided", supersedes="DEC-003")
            + _decision("DEC-003", "decided", supersedes="DEC-002"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID,),
        ),
        (
            _decision("DEC-001", "approved")
            + _decision("DEC-002", "decided", supersedes="DEC-001")
            + _decision("DEC-003", "decided", supersedes="DEC-001"),
            "DEC-002",
            (DeliveryCompilationDiagnosticCode.SUPERSESSION_INVALID,),
        ),
        (
            _DECIDED + _decision("DEC-002", "approved", supersedes="DEC-001"),
            "DEC-002",
            (DeliveryCompilationDiagnosticCode.DECISION_ORIGIN_REQUIRED,),
        ),
        (
            _decision("DEC-001", "approved")
            + _decision("DEC-002", "autonomous", supersedes="DEC-001")
            + _decision("DEC-003", "approved", supersedes="DEC-002"),
            "DEC-003",
            (DeliveryCompilationDiagnosticCode.DECISION_ORIGIN_REQUIRED,),
        ),
        (
            _DECIDED + _decision("DEC-002", "approved", supersedes="REQ-ANSWERED"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.DECISION_ORIGIN_REQUIRED,),
        ),
        (
            _decision("DEC-001", "approved") + _decision("DEC-002", "approved", supersedes="DEC-001"),
            "DEC-001",
            (DeliveryCompilationDiagnosticCode.DECISION_INACTIVE,),
        ),
        (_DECIDED, "", (DeliveryCompilationDiagnosticCode.VALUE_INVALID,)),
        (
            "",
            "DEC-001",
            (
                DeliveryCompilationDiagnosticCode.DEFINITION_MISSING,
                DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
            ),
        ),
    ],
    ids=(
        "unknown-origin",
        "missing-basis",
        "reused-id",
        "dangling-supersession",
        "self-supersession",
        "supersession-cycle",
        "superseded-twice",
        "decided-superseded-without-user",
        "second-reversal-without-user",
        "request-superseded-without-user",
        "commitment-on-superseded-decision",
        "commitment-without-decision",
        "no-decision",
    ),
)
def test_decision_rules_return_stable_diagnostics(
    decisions: str,
    links: str,
    expected: tuple[DeliveryCompilationDiagnosticCode, ...],
) -> None:
    result = compile_delivery_contract("sample-change", _decision_change(decisions, links), b"# D\n")

    codes = tuple(diagnostic.code for diagnostic in result.diagnostics)
    assert codes[: len(expected)] == expected
    assert set(codes[len(expected) :]) <= {
        DeliveryCompilationDiagnosticCode.DEFINITION_MISSING,
        DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
    }
    assert result.contract is None


def test_legacy_provenance_commitment_no_longer_compiles() -> None:
    legacy = _COMMITMENT.replace("decisions: [DEC-001]", "provenance: test source")
    intent = f"# Sample Change\n\n{_DECISION}\n{legacy}\n{_OUTCOME.format(dependencies='')}".encode()

    result = compile_delivery_contract("sample-change", intent, b"# D\n")

    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        DeliveryCompilationDiagnosticCode.KEY_UNKNOWN,
        DeliveryCompilationDiagnosticCode.KEY_MISSING,
        DeliveryCompilationDiagnosticCode.DEFINITION_MISSING,
        DeliveryCompilationDiagnosticCode.REFERENCE_UNRESOLVED,
    }


def test_stored_schema_2_contract_reads_and_keeps_its_exact_bytes() -> None:
    stored = (
        Path(__file__).with_name("fixtures") / "state_formats/golden/runtime/changes/source-bound-change/contract.json"
    ).read_bytes()

    contract = parse_delivery_contract(stored)

    assert contract.schema_version == 2
    assert contract.decisions == ()
    assert all(item.provenance and not item.decision_ids for item in contract.commitments)
    assert contract_canonical_bytes(contract) == stored
