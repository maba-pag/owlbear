"""Worker question admission: executable actions rather than unrestricted promises."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.tools import AskQuestion


def check_question(question: AskQuestion, checks: Sequence[str] = ()) -> list[str]:
    """Field errors for unmappable actions, undeclared trials and ambiguous answer options."""
    labels = [o.label.strip().lower() for o in question.options]
    if len(set(labels)) < len(labels):
        return ["options: labels repeat - give each option a distinct answer"]
    errors = [
        f"options[{i}].action: required - name continue, retry, pause or abandon; "
        "Delivery cannot waive a failed check or open a separate PR"
        for i, o in enumerate(question.options)
        if o.action is None
    ]
    errors += [
        f"options[{i}].check: not a current declared check - select its exact command"
        for i, o in enumerate(question.options)
        if o.check and o.check not in checks
    ]
    if question.recommended is not None and question.recommended >= len(question.options):
        errors.append("recommended: not an option index - select one of the listed options, starting at 0")
    return errors
