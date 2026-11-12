"""The decision picker's one tool (TD-459): the ids it picks from the list, each with an optional note."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools

REMINDER = "Your turn ended without a result. Call submit_result once, as the Finish section of your message says."


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


class ClarificationResult(tools.Args):
    """``submit_result`` for the check of an owner's clarification against the approved brief (TD-461)."""

    changes_brief: bool = Field(
        description="True when following the clarification changes the approved brief: its outcome, scope, "
        "criteria or non-goals",
        examples=[False],
    )
    why: str = Field(
        min_length=1, max_length=600, description="One or two sentences: the part of the brief it keeps or changes",
        examples=["It only names the wording criterion AC-1 already asks for."],
    )  # fmt: skip


CLARIFY = tools.Spec("submit_result", "Submit your verdict on the clarification once.", ClarificationResult, "result")


class OptionJudgment(tools.Args):
    """Whether one exact option is carried by the engine action it names."""

    index: int = Field(ge=0, le=4, description="The option's zero-based index", examples=[0])
    executable: bool = Field(description="The engine can carry out the whole visible promise", examples=[True])
    why: str = tools.bounded(600, "Why the promise is executable or which part is not", "It only pauses the Change.")
    check_related: bool = Field(
        description="The recommendation addresses a check problem or claims a check benefit", examples=[False]
    )
    recommends: bool = Field(
        description="The label or effect presents this option as a recommendation", examples=[False]
    )


class QuestionJudgment(tools.Args):
    """A complete pre-publication judgment: the question's subject and words, and every option (#1062, #1064)."""

    subject: Literal["product", "reserved", "internal"] = Field(
        description="product: it changes what the owner gets (scope, look, behaviour, risk); reserved: a decision "
        "reserves it for him (lint, format, CI or hook configuration, security, project setup); internal: anything "
        "else, such as a tool, test run or check Delivery must get working",
        examples=["product"],
    )
    plain: bool = Field(
        description="The question and each effect say in plain words what the owner gets or allows; a reserved "
        "proposal may name its exact file or setting after that, but no logs, test or function names or output",
        examples=[True],
    )
    follows: str = Field(
        default="",
        max_length=10,
        description="The id of an answered question whose problem this one asks about again; empty for none",
        examples=["q4"],
    )
    why: str = tools.bounded(
        600,
        "The reservation it falls under, what is not plain, and for follows why that answer did not resolve it",
        "It asks to exclude one vendored file from the large-file hook, a hook configuration change.",
    )
    options: list[OptionJudgment] = tools.bounded(
        5,
        "One verdict for every option, by its zero-based index",
        [{"index": 0, "executable": True, "why": "It pauses.", "check_related": False, "recommends": False}],
        least=2,
    )


ADMIT = tools.Spec(
    "submit_result",
    "Submit the question's subject and words verdict and every option's verdict once.",
    QuestionJudgment,
    "result",
)
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
