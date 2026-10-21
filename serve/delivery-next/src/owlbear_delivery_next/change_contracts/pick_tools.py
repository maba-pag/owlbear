"""The decision picker's one tool (TD-459): the ids it picks from the list, each with an optional note."""

from __future__ import annotations

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools

REMINDER = "Your turn ended without a result. Call submit_result once with the ids you pick."


class PickedId(tools.Args):
    """One decision of the list the work must respect or that determines what it must do."""

    id: str = tools.bounded(40, "The decision's id as the list shows it", "D-01JC0000000000000000000000")
    note: str = Field(default="", max_length=300, description="Optional: how it governs this work")


class PickResult(tools.Args):
    """``submit_result`` for the decision pick."""

    picked: list[PickedId] = tools.bounded(
        1000, "Every decision you pick; empty when none governs the work", [{"id": "D-01JC0000000000000000000000"}], 0
    )


SUBMIT = tools.Spec("submit_result", "Submit the decisions you pick once, by id.", PickResult, "result")
