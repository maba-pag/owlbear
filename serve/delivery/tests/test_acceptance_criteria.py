"""Acceptance identities: authored and legacy derivation, compiler diagnostics and first admission."""

from __future__ import annotations

import hashlib

import pytest

from owlbear_delivery.acceptance_criteria import (
    DeliveryAcceptanceRef,
    acceptance_criteria,
    acceptance_version,
    is_near_miss_acceptance_item,
    parse_acceptance_item,
)
from owlbear_delivery.target_contract import (
    DeliveryCompilationDiagnosticCode,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
    compile_delivery_contract,
)

_INTENT = b"# Acceptance identities\n"


def _design(*items: tuple[str, list[str]]) -> bytes:
    blocks = [
        (
            "```yaml target-contract\nkind: decision\nid: DEC-001\norigin: approved\nbasis: fixture\n"
            "statement: Fixture decision.\n```\n"
            "```yaml target-contract\nkind: commitment\nid: COM-001\nclass: dealbreaker\ndecisions: [DEC-001]\n"
            "statement: Keep identities stable.\n```\n"
        )
    ]
    for index, (outcome_id, acceptance) in enumerate(items, start=1):
        listed = "\n".join(f"  - {item!r}" for item in acceptance)
        blocks.append(
            f"```yaml target-contract\nkind: outcome\nid: {outcome_id}\ntitle: Outcome {index}\n"
            f"promise: Deliver outcome {index}.\nacceptance:\n{listed}\ncommitments: [COM-001]\ndependencies: []\n```\n"
        )
    return "\n".join(blocks).encode()


def _contract(*items: tuple[str, tuple[str, ...]]) -> DeliveryContract:
    outcomes = tuple(
        DeliveryOutcome(
            outcome_id=outcome_id,
            title=outcome_id,
            promise="Deliver it.",
            acceptance=acceptance,
            commitment_ids=(),
            dependency_ids=(),
        )
        for outcome_id, acceptance in items
    )
    return DeliveryContract(
        change_id="acceptance-ids",
        title="Acceptance identities",
        commitments=(),
        outcomes=outcomes,
        plan_scopes=tuple(
            DeliveryPlanScope(scope_id=f"SCOPE-{outcome.outcome_id[4:]}", outcome_id=outcome.outcome_id)
            for outcome in outcomes
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def test_authored_identities_derive_stable_ids_and_content_versions() -> None:
    contract = _contract(
        ("OUT-001", ("AC-001: The report renders.", "AC-002: The export works.")),
        ("OUT-002", ("AC-003: The dependent view loads.",)),
    )

    criteria = acceptance_criteria(contract)

    assert [(item.acceptance_id, item.outcome_id, item.identity_source) for item in criteria] == [
        ("AC-001", "OUT-001", "authored"),
        ("AC-002", "OUT-001", "authored"),
        ("AC-003", "OUT-002", "authored"),
    ]
    assert criteria[0].statement == "The report renders."
    assert criteria[0].acceptance_version == hashlib.sha256(b"The report renders.").hexdigest()
    assert criteria[0].ref == DeliveryAcceptanceRef(
        acceptance_id="AC-001", acceptance_version=acceptance_version("The report renders.")
    )


def test_identity_survives_revision_while_the_version_changes_with_the_statement() -> None:
    before = acceptance_criteria(_contract(("OUT-001", ("AC-001: The report renders.",))))[0]
    moved = acceptance_criteria(_contract(("OUT-001", ("AC-002: Other.", "AC-001: The report renders."))))[1]
    revised = acceptance_criteria(_contract(("OUT-001", ("AC-001: The report renders quickly.",))))[0]

    assert moved.ref == before.ref
    assert revised.acceptance_id == before.acceptance_id
    assert revised.acceptance_version != before.acceptance_version


def test_legacy_contract_gets_position_ids_valid_only_within_its_contract() -> None:
    criteria = acceptance_criteria(_contract(("OUT-001", ("First.", "Second.")), ("OUT-002", ("Third.",))))

    assert [(item.acceptance_id, item.identity_source) for item in criteria] == [
        ("OUT-001.01", "legacy-position"),
        ("OUT-001.02", "legacy-position"),
        ("OUT-002.01", "legacy-position"),
    ]
    assert criteria[1].acceptance_version == acceptance_version("Second.")


def test_parse_and_near_miss_rules() -> None:
    assert parse_acceptance_item("AC-007: Works.") == ("AC-007", "Works.")
    assert parse_acceptance_item("Works.") == (None, "Works.")
    for near_miss in ("AC-7: Works.", "AC-007:Works.", "AC-0071: Works.", "AC-007:  "):
        assert is_near_miss_acceptance_item(near_miss), near_miss
    assert not is_near_miss_acceptance_item("ACME works.")
    assert not is_near_miss_acceptance_item("AC-007: Works.")


@pytest.mark.parametrize(
    ("items", "code"),
    [
        ((("OUT-001", ["AC-001: One.", "Two."]),), DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_MIXED),
        (
            (("OUT-001", ["AC-001: One."]), ("OUT-002", ["AC-001: Two."])),
            DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_DUPLICATE,
        ),
        ((("OUT-001", ["AC-01: One."]),), DeliveryCompilationDiagnosticCode.ACCEPTANCE_IDENTITY_INVALID),
    ],
)
def test_compiler_rejects_mixed_duplicate_and_near_miss_identities(
    items: tuple[tuple[str, list[str]], ...],
    code: DeliveryCompilationDiagnosticCode,
) -> None:
    result = compile_delivery_contract("acceptance-ids", _INTENT, _design(*items))

    assert result.contract is None
    assert code in {diagnostic.code for diagnostic in result.diagnostics}


def test_compiler_output_is_unchanged_for_valid_authored_and_legacy_contracts() -> None:
    for items in ((("OUT-001", ["AC-001: One.", "AC-002: Two."]),), (("OUT-001", ["One.", "Two."]),)):
        result = compile_delivery_contract("acceptance-ids", _INTENT, _design(*items))

        assert result.diagnostics == ()
        assert result.contract is not None
        assert result.contract.outcomes[0].acceptance == tuple(items[0][1])
