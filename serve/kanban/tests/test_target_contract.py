from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from owlbear_kanban import DeliveryCompilationDiagnosticCode, compile_delivery_contract

_COMMITMENT = """```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: test source
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
_CANONICAL_SOURCE_HASHES = (
    "bca743da07b4ca5ec6a48c5e52cc2ea45578948f1f644c3098ebff58cdc0a9a2",
    "de43d9fb3e31f8cf6f483bf1af324ddc1b5d2e764522ae1a36ff71526b828bde",
)
_CANONICAL_CONTRACT_DIGEST = "f2fb4744738f28222124ff2add50cb2562e52f4e73d94c796ec315708cfe1a9e"


def _canonical_sources() -> tuple[bytes, bytes]:
    relative = Path(".owlbear/design/target-delivery-cutover")
    source_root = next(
        (parent / relative for parent in Path(__file__).resolve().parents if (parent / relative).is_dir()),
        None,
    )
    if source_root is None:
        pytest.skip("canonical operational Design sources are not distributed")
    return (source_root / "intent.md").read_bytes(), (source_root / "design.md").read_bytes()


def test_real_specification_compiles_to_complete_replayable_contract() -> None:
    intent_bytes, design_bytes = _canonical_sources()

    result = compile_delivery_contract("target-delivery-cutover", intent_bytes, design_bytes)
    replay = compile_delivery_contract("target-delivery-cutover", intent_bytes, design_bytes)

    assert result.diagnostics == ()
    assert result.contract is not None
    assert result.canonical_bytes is not None
    assert result.digest is not None
    assert result == replay
    assert result.contract.title == "Target Delivery Cutover"
    assert len(result.contract.commitments) == 11
    assert len(result.contract.outcomes) == len(result.contract.plan_scopes) == 10
    assert result.contract.commitments[0].commitment_id == "COM-001"
    assert result.contract.commitments[-1].commitment_id == "COM-012"
    assert result.contract.outcomes[1].outcome_id == "OUT-002"
    assert result.contract.outcomes[1].commitment_ids[-1] == "COM-012"
    assert result.contract.plan_scopes[1].scope_id == "SCOPE-002"
    assert result.contract.plan_scopes[1].outcome_id == "OUT-002"
    assert tuple(binding.sha256 for binding in result.contract.source_bindings) == _CANONICAL_SOURCE_HASHES
    assert json.loads(result.canonical_bytes) == result.contract.model_dump(mode="json")
    assert result.digest == hashlib.sha256(result.canonical_bytes).hexdigest()
    assert result.digest == _CANONICAL_CONTRACT_DIGEST

    changed = compile_delivery_contract("target-delivery-cutover", intent_bytes, design_bytes + b"\n")
    assert changed.diagnostics == ()
    assert changed.contract is not None
    assert changed.contract.commitments == result.contract.commitments
    assert changed.contract.outcomes == result.contract.outcomes
    assert changed.contract.source_bindings[1].sha256 != result.contract.source_bindings[1].sha256
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
provenance: test source
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
    intent = f"# Sample Change\n\n{_COMMITMENT}\n{_OUTCOME.format(dependencies=dependencies)}\n{addition}".encode()

    result = compile_delivery_contract("sample-change", intent, b"# Sample Design\n")

    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == expected_codes
    assert all(diagnostic.source_name == "intent.md" for diagnostic in result.diagnostics)
    assert result.contract is result.canonical_bytes is result.digest is None
