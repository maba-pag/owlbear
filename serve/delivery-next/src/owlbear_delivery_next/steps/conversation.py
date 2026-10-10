"""Pull-request conversation items: which comments are Delivery's, and which item versions are open or handled."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.models import Exit, Handling, ItemRef, Response

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from datetime import datetime

    from owlbear_delivery_next.github.provider import ConversationItem, ThreadComment
    from owlbear_delivery_next.models import Change, Task

MARKER = "<!-- delivery:"

type Published = Callable[[str], bool]


@dataclass(frozen=True)
class State:
    """One item at its current version: ``rec`` is its valid handling, None while it is open for ``task``."""

    item: ConversationItem
    version: str
    task: str
    rec: Handling | None


def marker(slug: str, item: str, task: str) -> str:
    """The hidden line that ends every Delivery reply."""
    return f"{MARKER}{slug}:{item}:{task} -->"


def _tasks(c: Change) -> list[Task]:
    return c.plan.tasks if c.plan else []


def ours(c: Change, login: str, x: ConversationItem | ThreadComment, thread: str | None = None) -> bool:
    """Delivery wrote it: a recorded reply, or a replay by Delivery's login carrying one of its complete markers.

    In a thread only that thread's markers count; every other comment is a person's, whatever it quotes.
    """
    if any(h.reply_id == x.id for h in c.handled):
        return True
    if x.author != login:
        return False
    refs = {(t.item.id, t.item.task) for t in _tasks(c) if t.item and thread in {None, t.item.id}}
    return any(marker(c.slug, item, task) in x.body for item, task in refs)


def human(c: Change, item: ConversationItem, login: str) -> list[tuple[str, str]]:
    """The ids and bodies of the item's comments a person wrote."""
    if item.kind == "thread":
        return [(x.id, x.body) for x in item.comments if not ours(c, login, x, item.id)]
    return [] if ours(c, login, item) else [(item.id, item.body)]


def version(item: ConversationItem, humans: list[tuple[str, str]]) -> str:
    """A digest of the item's human comments (and a review's state): any edit, addition or deletion changes it."""
    data = json.dumps([item.state, humans], separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def _valid(rec: Handling, item: ConversationItem, published: Published | None) -> bool:
    if rec.how == "fixed" and rec.commit and published is not None and not published(rec.commit):
        return False  # the fix is no longer in the PR head
    return not (item.kind == "thread" and rec.resolved and not item.resolved)  # a person reopened the thread


def assess(c: Change, item: ConversationItem, login: str, published: Published | None = None) -> State | None:
    """The item's state; None for Delivery's own items and resolved threads without a valid handling.

    Each invalidated handling of the same version opens a new round with its own task.
    """
    humans = human(c, item, login)
    if not humans:
        return None
    v = version(item, humans)
    rounds = [h for h in c.handled if h.item == item.id and h.version == v]
    if rounds and _valid(rounds[-1], item, published):
        return State(item, v, rounds[-1].task, rounds[-1])
    if item.kind == "thread" and item.resolved:
        return None
    return State(item, v, f"pr-{item.id}-{v[:8]}" + (f"-{len(rounds) + 1}" if rounds else ""), None)


def states(c: Change, items: Iterable[ConversationItem], login: str, published: Published | None = None) -> list[State]:
    """Every person's item with its state."""
    return [s for i in items if (s := assess(c, i, login, published)) is not None]


def open_items(
    c: Change, items: Iterable[ConversationItem], login: str, published: Published | None = None
) -> list[State]:
    """Every item whose current version is not handled."""
    return [s for s in states(c, items, login, published) if s.rec is None]


def reply_missing(s: State, items: Iterable[ConversationItem]) -> bool:
    """A handled item whose required Delivery reply is not in the conversation (deleted or never posted)."""
    if s.rec is None or s.rec.how == "no-action":
        return False
    ids = {x.id for x in s.item.comments} if s.item.kind == "thread" else {i.id for i in items}
    return s.rec.reply_id not in ids


def unresolved(s: State) -> bool:
    """A handled thread Delivery has not yet seen resolved: the only resolution Delivery retries."""
    rec = s.rec
    return (
        rec is not None
        and s.item.kind == "thread"
        and not s.item.resolved
        and not rec.resolved
        and (rec.reply_id is not None or rec.how == "no-action")
    )


def ref(s: State) -> ItemRef:
    """The item reference an open item's task carries."""
    return ItemRef(id=s.item.id, kind=s.item.kind, version=s.version, task=s.task, url=s.item.url)


def group(c: Change, root: str) -> list[Task]:
    """A conversation task and its review repairs, in plan order."""
    return [t for t in _tasks(c) if t.item and t.item.task == root]


def response(c: Change, root: str) -> Response | None:
    """The item's effective response: the latest done task's of its group."""
    done = [t.response for t in group(c, root) if t.done and t.response]
    return done[-1] if done else None


def pending(c: Change) -> list[tuple[Task, Response]]:
    """Done conversation tasks whose reply or no-action is not yet recorded, with their effective response."""
    recorded = {h.task for h in c.handled}
    roots = [t for t in _tasks(c) if t.item and t.id == t.item.task and t.id not in recorded]
    return [(t, r) for t in roots if all(g.done for g in group(c, t.id)) and (r := response(c, t.id)) is not None]


def posted(items: Iterable[ConversationItem], item: str, mark: str, login: str) -> str | None:
    """The id of Delivery's reply already carrying *mark* (an earlier post whose acknowledgement was lost)."""
    for i in items:
        if i.kind != "thread" and i.author == login and mark in i.body:
            return i.id
        if i.kind == "thread" and i.id == item:
            hit = next((x for x in i.comments if x.author == login and mark in x.body), None)
            if hit:
                return hit.id
    return None


def reply_body(r: Response, head: str, mark: str) -> str:
    """A reply: the response, the published PR head containing a fix, and the marker."""
    fixed = f"\n\nFixed in {head[:7]}." if r.how == "fixed" else ""
    return f"{r.text}{fixed}\n\n{mark}"


def record(c: Change, task: Task, r: Response, now: datetime, reply_id: str | None = None) -> Change:
    """Append the handling of the task's item version once its reply was observed (or none is due)."""
    assert task.item  # noqa: S101 - only pending tasks are recorded
    item = task.item
    c.handled.append(
        Handling(
            item=item.id,
            kind=item.kind,
            url=item.url,
            version=item.version,
            how=r.how,
            text=r.text,
            commit=r.commit,
            task=task.id,
            reply_id=reply_id,
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
