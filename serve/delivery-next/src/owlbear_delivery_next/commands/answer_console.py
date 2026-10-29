"""The owner's console answer, and the open question as the Changes page shows it (#676).

The console answers with the page's authority: ``answers.answer_item`` checks it, and nothing is queued when it
refuses. Its answer binds to what ``show`` printed, as the page's binds to what the page showed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Exit
from owlbear_delivery_next.project_host import answers
from owlbear_delivery_next.workflow_steps import held

if TYPE_CHECKING:
    import argparse

    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.state_store.store import Store


def answer(store: Store, a: argparse.Namespace) -> int:
    """Queue the owner's answer once the Changes page's checks pass (TD-461); a refused one writes nothing."""
    kind = a.kind.replace("-", "_") if a.kind else None
    try:
        body = answers.AnswerBody(
            question=a.question, option=a.option, text=a.text, kind=kind, statement=a.statement,
            confirmed=a.confirmed, round=a.round, head=a.head, pack=a.pack, findings=a.findings, tasks=a.tasks,
            attempt=a.attempt,
        )  # fmt: skip
    except ValidationError as exc:
        why = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
    else:
        got = answers.answer_item(store, store.read(a.change), body)
        if not isinstance(got, tuple):
            store.put_inbox(a.change, got)
            return 0
        why = got[1]
    sys.stderr.write(f"not answered: {why}\n")
    return 1


def describe(change: Change, store: Store | None = None) -> str:
    """Return the Change's step, exit and open question or stop action; with its store, the question as shown."""
    o, s = change.outcome, change.step
    text = f"{change.slug}: step {s.kind}{f' {s.task}' if s.task else ''}, exit {o.exit if o else 'none'}"
    if o and o.reason:
        text += f" - {o.reason}"
    if o and o.exit == Exit.ASK:
        q = next(q for q in change.questions if q.id == o.question)
        lines = _asked(store, change, q) if store else [f"{q.id} option {opt.id}: {opt.label}" for opt in q.options]
        text += "".join(f"\n  {line}" for line in lines)
    if o and o.exit == Exit.STOP and change.stop:
        text += f"\n  action: {change.stop.action}"
    return text


def _asked(store: Store, c: Change, q: Question) -> list[str]:
    """The question's text and the options it offers now, as the page lists them."""
    said = q.text.replace("\n", "\n    ")
    return [f"{q.id}: {said}", *(f"{q.id} option {o.id}: {o.label}" for o in held.offered(store, c, q))]
