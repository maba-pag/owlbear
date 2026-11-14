"""The merge report contract and context of an integration build or its review repair."""

from __future__ import annotations

from textwrap import indent
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_flow.moves import integration_of

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Task


def result(change: Change, task: Task, message: str) -> tuple[str, tools.Spec]:
    """Require the merge report for an integration family, with its ancestor's context for a fresh repair."""
    root = integration_of(change, task)
    if root and root is not task:
        message += (
            f"\n\n## Integration being repaired\n{indent(root.title, '> ')}\n"
            f"Original integration base: {root.base}\n"
            "Report what combining the branches did to behaviour, including this repair, in `merge`."
        )
    submit = tools.MERGED if root or change.step.kind == StepKind.INTEGRATE else tools.SUBMIT
    return message, submit
