"""Pull-request conversation items: which are Delivery's, open, or awaiting their reply or resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.github.provider import MARKER
from owlbear_delivery_next.models import Exit, Handling, ItemRef, Response

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from owlbear_delivery_next.github.provider import ConversationItem, ThreadComment
    from owlbear_delivery_next.models import Change, Task


def marker(slug: str, item: str, task: str) -> str:
    """The hidden line that ends every Delivery reply."""
    return f"{MARKER}{slug}:{item}:{task} -->"


def latest(c: Change, item: str) -> Handling | None:
    """The newest handling record of one item."""
    return next((h for h in reversed(c.handled) if h.item == item), None)


def newer(item: ConversationItem, since: str | None) -> list[ThreadComment]:
    """A thread's comments after *since* (all when unknown) that Delivery did not write."""
    ids = [x.id for x in item.comments]
    start = ids.index(since) + 1 if since in ids else 0
    return [x for x in item.comments[start:] if MARKER not in x.body]


def opened_at(c: Change, item: ConversationItem) -> str | None:
    """The latest comment id an open item must be handled at; None when it is not open."""
    rec = latest(c, item.id)
    if item.kind != "thread":
        if MARKER in item.body or (rec and rec.last_id == item.last_id):
            return None
        return item.last_id
    if item.resolved or (rec is None and item.last_by_delivery):
        return None
    fresh = newer(item, rec.last_id if rec else None)
    return fresh[-1].id if fresh else None


def open_items(c: Change, items: Iterable[ConversationItem]) -> list[tuple[ConversationItem, str]]:
    """Every open item with the comment id it is open at."""
    return [(i, at) for i in items if (at := opened_at(c, i)) is not None]


def unresolved(c: Change, item: ConversationItem) -> bool:
    """A handled thread still unresolved with no newer human comment: its resolution is pending."""
    rec = latest(c, item.id)
    return item.kind == "thread" and not item.resolved and rec is not None and not newer(item, rec.last_id)


def task_id(item: ConversationItem, at: str) -> str:
    """One task per item and latest comment."""
    return f"pr-{item.id}" + ("" if at == item.id else f"-{at}")


def ref(item: ConversationItem, at: str) -> ItemRef:
    """The item reference a conversation task carries."""
    return ItemRef(id=item.id, kind=item.kind, last_id=at, url=item.url)


def pending(c: Change) -> list[Task]:
    """Done conversation tasks whose reply or no-action is not yet recorded."""
    recorded = {h.task for h in c.handled}
    tasks = c.plan.tasks if c.plan else []
    return [t for t in tasks if t.done and t.item and t.response and t.id not in recorded]


def posted(items: Iterable[ConversationItem], item: str, mark: str) -> str | None:
    """The id of a reply already carrying *mark* (an earlier post whose acknowledgement was lost)."""
    for i in items:
        if i.kind != "thread" and MARKER in i.body and mark in i.body:
            return i.id
        if i.kind == "thread" and i.id == item:
            hit = next((x for x in i.comments if mark in x.body), None)
            if hit:
                return hit.id
    return None


def record(c: Change, task: Task, now: datetime, reply_id: str | None = None, *, resolved: bool = False) -> Change:
    """Append the handling record once its effect was observed."""
    assert task.item  # noqa: S101 - only pending tasks are recorded
    assert task.response  # noqa: S101
    item, r = task.item, task.response
    c.handled.append(
        Handling(
            item=item.id,
            kind=item.kind,
            url=item.url,
            last_id=item.last_id,
            how=r.how,
            text=r.text,
            task=task.id,
            reply_id=reply_id,
            resolved=resolved,
            at=now,
        )
    )
    return c


def respond(task: Task | None, payload: object, head: str | None, exit_: Exit) -> None:
    """Keep an accepted Builder response on its conversation task, bound to the accepted HEAD."""
    r = getattr(payload, "response", None)
    if task is not None and task.item is not None and r is not None and exit_ == Exit.DONE:
        task.response = Response(how=r.how, text=r.text, commit=head)


def summary(item: ConversationItem) -> str:
    """The task title naming the item."""
    where = f" on {item.path}" if item.path else ""
    noun = {"comment": "PR comment", "review": "review", "thread": "review thread"}[item.kind]
    return f"Respond to the {noun} by {item.author}{where}"
