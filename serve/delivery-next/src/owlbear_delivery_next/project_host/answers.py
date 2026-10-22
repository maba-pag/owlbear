"""The Changes page's and the chat's answer to an open question, and why the host refuses one.

A worker's question takes its relayer's class: an event, a clarification or a brief change (TD-461). A clarification
carries the statement the owner confirmed when it was read back to him; without that confirmation nothing is stored.
A visual round's decision names what the page showed (TD-79), a final retry its tasks (TD-217).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_decisions.models import STATEMENT_LIMIT
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import AnswerKind
from owlbear_delivery_next.change_flow import answer_kinds, loop, rebuilds
from owlbear_delivery_next.workflow_steps import decision, held

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.inbox import InboxItem
    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.state_store.store import Store

T6 = "This is a recovery decision; make it in the Changes page"
KIND = (
    "How the owner's answer bears on the approved brief: event (it only settles how the work goes on), "
    "clarification (it settles intent within the brief; read it back first) or brief_change (it changes the "
    "brief; the work stops and asks)"
)
STATEMENT = "For a clarification: the intent the owner confirmed when you read it back, at most two lines"
CONFIRMED = "For a clarification: true only when the owner confirmed the statement as you read it back"
UNCLASSED = "classify the answer to a worker's question: kind is event, clarification or brief_change"
UNCONFIRMED = (
    "a clarification needs the statement the owner confirmed when it was read back to him, at most two lines, with "
    "confirmed true; nothing was stored"
)


class AnswerBody(BaseModel):
    """Answer one open question; a visual decision names the round, capture and pack the page showed (TD-79).

    A final retry names the plan tasks to rebuild and the loop attempt and head the page showed (TD-217).
    """

    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=16)
    option: str | None = Field(default=None, max_length=64)
    text: str = Field(default="", max_length=2000)
    channel: Literal["status-view", "chat"] = "status-view"
    round: int | None = Field(default=None, ge=1)
    head: str = Field(default="", max_length=40)
    pack: str = Field(default="", max_length=200)
    findings: list[Annotated[str, Field(max_length=40)]] = Field(default_factory=list, max_length=60)
    tasks: list[Annotated[str, Field(max_length=16)]] = Field(default_factory=list, max_length=200)
    attempt: int | None = Field(default=None, ge=1)
    kind: AnswerKind | None = None  # a worker's question only (TD-461)
    statement: str = Field(default="", max_length=STATEMENT_LIMIT)
    confirmed: bool = False


def router(store: Store, read: Callable[[str], Change], put: Callable[[str, InboxItem], dict[str, str]]) -> APIRouter:
    """POST /changes/{slug}/answers: one answer, checked against the open question, queued for the runner."""
    routes = APIRouter()

    @routes.post("/changes/{slug}/answers")
    def answer(slug: str, body: AnswerBody) -> dict[str, str]:
        c = read(slug)
        q = next((q for q in c.questions if q.id == body.question and q.answer is None), None)
        if q is None:
            raise HTTPException(409, f"question {body.question} is not open")
        if why := _checked(store, c, q, body) or refused(c, q, body):
            raise HTTPException(*why)
        item = AnswerItem(
            at=datetime.now(UTC), channel=body.channel, question=q.id, option=body.option, text=body.text,
            round=body.round, findings=body.findings, tasks=body.tasks, attempt=body.attempt, head=body.head,
            classed=body.kind, statement=body.statement.strip(),
        )  # fmt: skip
        return put(slug, item)

    return routes


def _checked(store: Store, c: Change, q: Question, body: AnswerBody) -> tuple[int, str] | None:  # noqa: PLR0911
    """The status and reason an answer to the open *q* is refused with, before its selection is judged."""
    if q.cause == loop.CONSENT:
        return 409, "consent to merge goes through merge-consent with the exact head"
    if body.channel == "chat" and not loop.ordinary(q):
        return 403, T6
    if why := classed(q, body):
        return 422, why
    if body.option is not None and body.option not in {o.id for o in held.offered(store, c, q)}:
        if body.option in {o.id for o in q.options}:  # an accept its hold no longer supports
            return 409, "the held result no longer matches its step, brief or commit; run it again"
        return 422, f"option {body.option} is not one of {[o.id for o in q.options]}"
    if q.repair and ((now_open := loop.open_question(c)) is None or now_open.id != q.id):
        return 409, "the Change moved on since this round gate asked; reload"
    chosen = {o.next for o in q.options} & loop.DECISIONS - {"retry"} or q.repair or answer_kinds.owned(q)
    if body.option is None and chosen:
        return 422, f"choose one of {[o.label for o in q.options]}"
    if any(o.id == body.option and o.next == "reconsider" for o in q.options) and not body.text.strip():
        return 422, "a reconsideration needs your note: what the reviewer should weigh"
    return None


def classed(q: Question, body: AnswerBody) -> str:
    """Why the answer's class does not fit *q*: a worker's question needs one, a clarification its confirmed intent."""
    said = body.statement.strip()
    if not loop.ordinary(q):
        return "only a worker's question takes a kind" if body.kind or said or body.confirmed else ""
    if body.kind is None:
        return UNCLASSED
    if body.kind != "clarification":
        return "only a clarification has a statement" if said or body.confirmed else ""
    return "" if said and body.confirmed and len(said.splitlines()) <= 2 else UNCONFIRMED  # noqa: PLR2004 - two lines


def refused(c: Change, q: Question, body: AnswerBody) -> tuple[int, str] | None:
    """The status and reason a Changes-page answer is refused with, or None."""
    if q.cause == decision.CAUSE and body.option in {"pass", "fail"}:
        return _visual(c, body)
    return rebuilds.refused(c, q, body.option, body.tasks, (body.attempt, body.head))


def _visual(c: Change, body: AnswerBody) -> tuple[int, str] | None:
    """Why a Pass or Fail is refused: its round, capture or pack changed since the page showed them, or it is empty."""
    kept = c.visual_rounds[-1] if c.visual_rounds else None
    shown = (body.round, body.head, body.pack)
    if kept is None or kept.outcome != "ask" or kept.decision or shown != (kept.number, kept.head, kept.pack):
        return 409, "the capture or the design pack changed since the page was shown; reload"
    if unknown := sorted(set(body.findings) - {f.id for v in kept.verdicts for f in v.findings}):
        return 422, f"findings {unknown} are not in round {kept.number}"
    if body.option == "fail" and not body.findings and not body.text.strip():
        return 422, "a Fail ticks a finding or says what is wrong"
    return None
