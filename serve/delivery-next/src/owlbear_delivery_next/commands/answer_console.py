"""The owner's console answer, and the open question as the Changes page shows it (#676).

The console answers with the page's authority: ``answers.answer_item`` checks it, and nothing is queued when it
refuses. Its answer binds to what ``show`` printed, as the page's binds to what the page showed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Exit
from owlbear_delivery_next.change_flow import rebuilds
from owlbear_delivery_next.project_host import answers
from owlbear_delivery_next.workflow_steps import decision, held

if TYPE_CHECKING:
    import argparse

    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.change_contracts.visual_records import JudgeFinding
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
        why = got[1] if isinstance(got, tuple) else store.put_answer(a.change, got)
        if why is None:
            return 0
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
    """The question's text and the options it offers now, and the round or task list the page shows beside it."""
    said = q.text.replace("\n", "\n    ")
    offered = [f"{q.id} option {o.id}: {o.label}" for o in held.offered(store, c, q)]
    return [f"{q.id}: {said}", *offered, *_round(c, q), *_retry(c, q)]


def _round(c: Change, q: Question) -> list[str]:
    """A visual decision's round (TD-79): its verdicts, its findings, and the ones the page ticks for a Fail."""
    if q.cause != decision.CAUSE or not c.visual_rounds:
        return []
    kept = c.visual_rounds[-1]
    ticked = set(decision.proposed(kept))
    lines = [f"visual round {kept.number} at {kept.head}, pack {kept.pack or 'none'}"]
    for v in kept.verdicts:
        lines.append(f"  {v.lens} {v.verdict or 'no verdict'}{f': {v.reason}' if v.reason else ''}")
        lines += [f"    [{'x' if f.id in ticked else ' '}] {_finding(f)}" for f in v.findings]
    pack = f" --pack {kept.pack}" if kept.pack else ""
    return [*lines, f"answer with --round {kept.number} --head {kept.head}{pack}; a Fail adds --finding ID or --text"]


def _finding(f: JudgeFinding) -> str:
    where = f"{f.state} at {f.width}px" if f.width else f.state
    made = "existing" if f.introduced is False else "introduced"  # as the page groups them
    return f"{f.id} {f.severity or '-'} {made} {where}: {f.text}".replace("\n", "\n      ")


def _retry(c: Change, q: Question) -> list[str]:
    """A final retry's plan tasks (TD-217), the ones the page ticks, and the criteria Accept as done leaves unmet."""
    if (shown := rebuilds.shown(c, q)) is None:
        return []
    attempt, head = shown["attempt"], shown["head"]
    lines = [f"final retry attempt {attempt} at {head}"]
    for t in cast("list[dict[str, Any]]", shown["tasks"]):
        shares = f" (shares files with {', '.join(t['shares'])})" if t["shares"] else ""
        lines.append(f"  [{'x' if t['ticked'] else ' '}] {t['id']} {t['title']}{shares}")
    lines += [f"  unmet: {u}" for u in cast("list[str]", shown["unmet"])]
    return [*lines, f"answer with --attempt {attempt} --head {head}; a Rebuild adds --task ID for each task"]
