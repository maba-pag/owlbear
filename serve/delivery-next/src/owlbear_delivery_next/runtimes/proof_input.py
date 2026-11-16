"""Proof feasibility for brief and plan challenges and their planner."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.models import PersonCheck

CONTEXT = (
    "Delivery sessions execute the installed runtime, not this Change's branch code. Workers get no owner token; "
    "checks must not use the live HOME or stores. For each criterion, verify an executable witness at its claimed "
    "boundary with the runtime, authentication and isolated data actually available. A nominal command, a fixture "
    "or a later ordinary Delivery session does not prove a real Delivery session on changed branch runtime code. "
    "A feasible approved person-only check supplies its stated criterion coverage without a Delivery task. "
    "If no available proof covers it, the criterion and its timing need the owner's choice of a person check or a "
    "look after release, not a workaround that widens these boundaries."
)
AMENDMENT = (
    "A criterion with no executable witness under these constraints and no feasible approved person-only check "
    "covering it needs a brief amendment, not "
    "another task: report_wrong_premise stage brief with that criterion in amendment, the proposed "
    "change and evidence. A repairable tool or setup defect that leaves acceptance unchanged is "
    "stage setup, never a reason to weaken the brief."
)


def person_checks(checks: Sequence[PersonCheck]) -> list[str]:
    """The owner checks' proof, operation and criterion coverage for shaping and planning."""
    return [
        f"- {p.id}: covers {', '.join(p.criteria) or 'all criteria'}; expect {' '.join(p.expect.split())}"
        + "".join(f"\n  - {' '.join(s.split())}" for s in p.steps)
        for p in checks
    ]
