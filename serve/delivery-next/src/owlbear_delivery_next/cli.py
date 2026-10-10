"""Commands: ``setup``, ``host`` starts Delivery, ``status`` reads the state; ``seed``, ``answer``, ``show`` for dev."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from owlbear_delivery_next import host, profile, setup
from owlbear_delivery_next.models import (
    AnswerItem,
    Brief,
    Change,
    Criterion,
    Exit,
    Names,
    PersonCheck,
    Plan,
    Profile,
    ProfileEntry,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.status import status, unloadable
from owlbear_delivery_next.store import Store, StoreError

START = "run `owlbear-next host`"


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
    for kind, cmds in ((StepKind.BUILD, a.allow), (StepKind.CHECK, a.launch)):
        if cmds:
            entries[f"allow:{kind}"] = ProfileEntry(state="known", value="\n".join(cmds), evidence="dev seed")
    models = dict.fromkeys((StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK), a.model)
    old = store.read_profile() or Profile()
    entries = {k: v for k, v in old.entries.items() if not k.startswith(("install:", "allow:"))} | entries
    store.write_profile(Profile(version=old.version + 1, confirmed_at=now, entries=entries, models=models))
    criteria = [Criterion(id=f"AC-{i}", text=t) for i, t in enumerate(a.criterion, 1)]
    brief = Brief(version=1, outcome=a.outcome, scope=a.scope, criteria=criteria)
    brief.approved = [brief.model_copy(deep=True)]
    brief.approved_version, brief.approved_at = 1, now
    change = Change(
        slug=a.change,
        profile_version=old.version + 1,
        brief=brief,
        plan=Plan(tasks=[Task(id="t1", title=a.title, scope=a.scope, checks=a.check)]),
        checks=[PersonCheck(id=i, criteria=[c.id for c in criteria], steps=[s]) for i, s in a.person_check],
        step=Step(kind=StepKind.BUILD, task="t1"),
        names=Names(branch=f"owlbear/{a.change}", target=a.target),
    )
    with store.lock(a.change) as lock:
        store.write(lock, change)


def show_status(store: Store, now: datetime) -> str:
    """Return every Change's status line and next action from the state files, with the host-down overlay."""
    record = host.running(store)
    lines = [] if record else [f"Delivery is not running — {START}"]
    lines += [f"Readiness: {r}" for r in (record and record.ready) or []]
    for slug in store.slugs():
        try:
            s = status(store.read(slug), host.activity(store, slug, record), now)
        except StoreError as exc:
            s = unloadable(exc.stop(now))
        action = f"{s.action} ({START})" if s.action == "Start Delivery" else s.action
        lines.append(
            f"{slug}: {s.line}"
            + (f"\n  next: {action}" + (f" ({s.actor})" if s.actor != "you" else "") if action else "")
        )
    return "\n".join(lines)


def show_profile(store: Store, repo: Path, confirms: list[tuple[str, str]]) -> str:
    """Detect the profile, apply the owner's confirmations and return every entry with its evidence."""
    prof = profile.detect(repo, profile.provider(store.read_profile() or Profile(), repo), store.read_profile())
    for key, value in confirms:
        prof = profile.confirm(prof, key, value, datetime.now(UTC))
    store.write_profile(prof)
    lines = [f"profile v{prof.version}"]
    lines += [f"  {k}: {e.state} {e.value!r} ({e.evidence})" for k, e in sorted(prof.entries.items())]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run one command."""
    parser = argparse.ArgumentParser(prog="owlbear-next")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("host", help="start Delivery for this clone, or print the running host's URL")
    sub.add_parser("status", help="print every Change's status line and next action")
    up = sub.add_parser("setup", help="check readiness, confirm the profile, register the host task and chat server")
    up.add_argument("--yes", action="store_true", help="confirm the profile (only the profile)")
    choices = ("yes", "no", "ask")
    up.add_argument("--local-files", choices=choices, default="ask", help="write .vscode/tasks.json and .mcp.json")
    up.add_argument("--skill", choices=choices, default="ask", help="install the chat skill in ~/.copilot/skills")
    up.add_argument("--confirm", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="KEY=VALUE")
    p = sub.add_parser("profile", help="detect the project profile; --confirm KEY=VALUE records the owner's answer")
    p.add_argument("--confirm", action="append", default=[], type=lambda v: tuple(v.split("=", 1)))
    s = sub.add_parser("seed", help="seed a pre-approved one-task Change and a minimal profile")
    s.add_argument("change")
    s.add_argument("--title", required=True)
    s.add_argument("--outcome", required=True)
    s.add_argument("--criterion", action="append", default=[])
    s.add_argument("--scope", action="append", default=[])
    s.add_argument("--check", action="append", default=[])
    s.add_argument("--install", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="DIR=CMD")
    s.add_argument("--allow", action="append", default=[], help="extra shell command allowed in build")
    s.add_argument("--launch", action="append", default=[], help="launch command allowed for check environments")
    s.add_argument(
        "--person-check", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="ID=STEPS"
    )
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
    if a.command == "host":
        return host.serve(a.repo.resolve())
    if a.command == "setup":
        return setup.run(a.repo.resolve(), a.confirm, yes=a.yes, local_files=a.local_files, skill=a.skill)
    store = Store.open(a.repo.resolve())
    if a.command == "status":
        sys.stdout.write(show_status(store, datetime.now(UTC)) + "\n")
        return 0
    if a.command == "profile":
        sys.stdout.write(show_profile(store, a.repo.resolve(), a.confirm) + "\n")
        return 0
    if a.command == "seed":
        seed(store, a)
    elif a.command == "answer":
        item = AnswerItem(at=datetime.now(UTC), question=a.question, option=a.option, text=a.text)
        store.put_inbox(a.change, item)
    sys.stdout.write(describe(store.read(a.change)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
