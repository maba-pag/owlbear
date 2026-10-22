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

    picked: list[PickedId] = Field(
        description="Every decision you pick; empty when none governs the work",
        examples=[[{"id": "D-01JC0000000000000000000000"}]],
    )  # no size limit: the list it picks from has none (TD-456)


SUBMIT = tools.Spec("submit_result", "Submit the decisions you pick once, by id.", PickResult, "result")
LIMIT = 600.0  # seconds a lookup's picker session may run: a pick takes about a minute
WAIT = 900.0  # seconds a caller waits for a lookup's answer: its session's limit, its start and its end


class Question(tools.Args):
    """``lookup_decisions``: one question about the work, answered with the decisions that govern it."""

    question: str = Field(
        min_length=1, max_length=1000, description="What you need to decide, in a sentence or two",
        examples=["May the farewell page load a web font from a CDN?"],
    )  # fmt: skip


LOOKUP = tools.Spec(
    tools.LOOKUP,
    "Ask which decisions govern a choice you are unsure of. The picker reads every decision in force and answers "
    "in about a minute with those that apply, each whole. Your turn goes on. A reply with `failed` means nothing "
    "was looked up: report it in your result, never take it for no decision applying.",
    Question,
    "result",
)
