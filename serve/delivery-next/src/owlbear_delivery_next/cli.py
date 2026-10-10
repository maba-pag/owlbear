"""Development commands: seed a pre-approved one-task Change with a minimal profile, answer, show."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from owlbear_delivery_next.models import (
    AnswerItem,
    Brief,
    Change,
    Criterion,
    Exit,
    Names,
    Plan,
    Profile,
    ProfileEntry,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.store import Store


def describe(change: Change) -> str:
    """Return the Change's step, exit and open question options or stop action."""
    o, s = change.outcome, change.step
    text = f"{change.slug}: step {s.kind}{f' {s.task}' if s.task else ''}, exit {o.exit if o else 'none'}"
    if o and o.reason:
        text += f" - {o.reason}"
    if o and o.exit == Exit.ASK:
        q = next(q for q in change.questions if q.id == o.question)
        text += "".join(f"\n  {q.id} option {opt.id}: {opt.label}" for opt in q.options)
    if o and o.exit == Exit.STOP and change.stop:
        text += f"\n  action: {change.stop.action}"
    return text


def seed(store: Store, a: argparse.Namespace) -> None:
    """Write a minimal confirmed profile and one Change whose approved brief and one-task plan start at build."""
    now = datetime.now(UTC)
    entries = {f"install:{pkg}": ProfileEntry(state="known", value=cmd, evidence="dev seed") for pkg, cmd in a.install}
    if a.allow:
        entries["allow:build"] = ProfileEntry(state="known", value="\n".join(a.allow), evidence="dev seed")
    store.write_profile(Profile(version=1, confirmed_at=now, entries=entries, models={StepKind.BUILD: a.model}))
    criteria = [Criterion(id=f"AC-{i}", text=t) for i, t in enumerate(a.criterion, 1)]
    brief = Brief(version=1, outcome=a.outcome, scope=a.scope, criteria=criteria)
    brief.approved = [brief.model_copy(deep=True)]
    brief.approved_version, brief.approved_at = 1, now
    change = Change(
        slug=a.change,
        profile_version=1,
        brief=brief,
        plan=Plan(tasks=[Task(id="t1", title=a.title, scope=a.scope, checks=a.check)]),
        step=Step(kind=StepKind.BUILD, task="t1"),
        names=Names(branch=f"owlbear/{a.change}", target=a.target),
    )
    with store.lock(a.change) as lock:
        store.write(lock, change)


def main(argv: list[str] | None = None) -> int:
    """Run one development command."""
    parser = argparse.ArgumentParser(prog="python -m owlbear_delivery_next.cli")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("seed", help="seed a pre-approved one-task Change and a minimal profile")
    s.add_argument("change")
    s.add_argument("--title", required=True)
    s.add_argument("--outcome", required=True)
    s.add_argument("--criterion", action="append", default=[])
    s.add_argument("--scope", action="append", default=[])
    s.add_argument("--check", action="append", default=[])
    s.add_argument("--install", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="DIR=CMD")
    s.add_argument("--allow", action="append", default=[], help="extra shell command allowed in build")
    s.add_argument("--model", default="auto")
    s.add_argument("--target", default="main")
    ans = sub.add_parser("answer", help="write an answer into the Change inbox")
    ans.add_argument("change")
    ans.add_argument("--question", required=True)
    ans.add_argument("--option")
    ans.add_argument("--text", default="")
    show = sub.add_parser("show", help="print the Change's step, exit and open question")
    show.add_argument("change")
    a = parser.parse_args(argv)
    store = Store.open(a.repo.resolve())
    if a.command == "seed":
        seed(store, a)
    elif a.command == "answer":
        item = AnswerItem(at=datetime.now(UTC), question=a.question, option=a.option, text=a.text)
        store.put_inbox(a.change, item)
    sys.stdout.write(describe(store.read(a.change)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
