"""Commands: ``setup``, ``host`` starts Delivery, ``status`` reads the state; ``seed``, ``answer``, ``show`` for dev."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CalledProcessError

from owlbear_delivery_next import (
    backlog_migrate,
    common,
    design_pack,
    host,
    pack_replay,
    pack_update,
    profile,
    roles,
    setup,
)
from owlbear_delivery_next.backlog import Backlog, BacklogError
from owlbear_delivery_next.config import Agent, Layer
from owlbear_delivery_next.detector import DetectorError
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    Names,
    PersonCheck,
    Plan,
    Role,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.profile_record import Profile, ProfileEntry, RoleModel, Runtime
from owlbear_delivery_next.status import status, unloadable
from owlbear_delivery_next.store import Store, StoreError

START = "run `owlbear-next host`"


def show_common(path: Path | None) -> str:
    """Record the shared settings repository when given, then say which one this machine uses."""
    try:
        shared = common.point(path) if path else common.locate()
    except common.CommonError as exc:
        return f"Not set: {exc}"
    if shared is None:
        return "No shared settings repository; settings stay in each clone. Set one: `owlbear-next common PATH`"
    return f"Shared settings repository: {shared.root} (pointer {common.pointer()}). Restart a running host to use it."


def show_pack(*, install: bool) -> int:
    """Print the design pack's state; with ``install``, download and verify what is missing first."""
    if install:
        try:
            design_pack.install()
        except design_pack.PackError as exc:
            sys.stdout.write(f"Not installed: {exc}\n")
            return 1
    sys.stdout.write(design_pack.status() + "\n")
    return 0


def update_pack(a: argparse.Namespace, repo: Path) -> int:
    """The update tooling (design skill research §3.5): notice, rule diff, golden pages, calibration replay."""
    try:
        if a.diff:
            sys.stdout.write(pack_update.diff(a.diff.resolve(), a.to) + "\n")
            return 0
        if a.golden:
            return _golden()
        if a.replay:
            r = pack_replay.replay(Store.open(repo))
            verdict = "advisory: too few rounds" if r.advisory else "within the margin" if r.ok else "below the margin"
            sys.stdout.write(
                f"calibration replay: {r.rounds} decided rounds, {r.left_out} left out; the design judge agreed with "
                f"the owner {r.before:.0%} as recorded, {r.after:.0%} with this pack ({verdict})\n"
            )
            return 0 if r.ok else 1
        sys.stdout.write(pack_update.said(pack_update.notice(refresh=True)) + "\n")
    except (
        design_pack.PackError,
        pack_replay.ReplayError,
        DetectorError,
        common.CommonError,
        CalledProcessError,
        OSError,
        ValueError,
    ) as exc:
        sys.stdout.write(f"design pack: {type(exc).__name__}: {exc}\n")
        return 1
    return 0


def _golden() -> int:
    pack = design_pack.installed()
    if pack is None:
        sys.stdout.write("design pack not installed: run `owlbear-next design-pack --install`\n")
        return 1
    wrong = pack_update.golden(pack)
    for page, w in wrong.items():
        missing, unexpected = ", ".join(w["missing"]) or "none", ", ".join(w["unexpected"]) or "none"
        sys.stdout.write(f"golden page {page}: missing {missing}; unexpected {unexpected}\n")
    sys.stdout.write("golden pages: " + ("differ" if wrong else "as expected") + "\n")
    return 1 if wrong else 0


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
    old = store.read_profile() or Profile()
    entries = old.entries | entries
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
    store.write_profile(Profile(version=old.version + 1, confirmed_at=now, entries=entries, runtime=old.runtime))
    with store.lock(a.change) as lock:
        store.write(lock, change)


def show_status(store: Store, now: datetime) -> str:
    """Return every Change's status line and next action from the state files, with the host-down overlay."""
    record = host.running(store)
    lines = [] if record else [f"Delivery is not running — {START}"]
    lines += [host.RESTART] if host.stale(record) else []
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
    return "\n".join([*lines, roles.table(store.settings())])


def show_profile(
    store: Store,
    repo: Path,
    confirms: list[tuple[str, str]],
    overrides: list[tuple[Role, RoleModel]] | None = None,
    runtime: Runtime | None = None,
) -> str:
    """Detect the profile, apply the owner's confirmations and runtime, and role overrides to the project settings."""
    prof = profile.detect(repo, profile.provider(store.read_profile() or Profile(), repo), store.read_profile())
    for key, value in confirms:
        prof = profile.confirm(prof, key, value, datetime.now(UTC))
    prof = prof.model_copy(update={"runtime": runtime or prof.runtime})
    store.write_profile(prof)
    notice = (
        store.update_config(lambda cur: _overridden(cur, overrides), "role overrides from the CLI") if overrides else ""
    )
    lines = [f"profile v{prof.version}", *([f"Notice: {notice}"] if notice else [])]
    lines += [f"  {k}: {e.state} {e.value!r} ({e.evidence})" for k, e in sorted(prof.entries.items())]
    return "\n".join([*lines, roles.table(store.settings()), f"Runtime: {prof.runtime}"])


def add_backlog(store: Store, a: argparse.Namespace) -> int:
    """Add a finding to the backlog issues (TD-84, TD-103), or count up the entry it repeats; print which."""
    if a.action == "migrate":
        if store.shared is None:
            sys.stdout.write("no shared repository is set up: nothing to migrate\n")
            return 1
        return backlog_migrate.migrate(store.shared, lambda said: sys.stdout.write(said + "\n"))
    try:
        entry, new = Backlog.of(store).add(a.title, a.text, a.source, a.evidence)
    except (BacklogError, common.CommonError) as exc:
        sys.stdout.write(f"not added: {exc}\n")
        return 1
    said = (
        f"added #{entry.id}: {entry.title}" if new else f"seen again #{entry.id}: {entry.title} ({entry.count} times)"
    )
    sys.stdout.write(said + "\n")
    return 0


def report(store: Store, a: argparse.Namespace) -> int:
    """Run ``backlog add``, or print every Change's status or the detected profile."""
    if a.command == "backlog":
        return add_backlog(store, a)
    if a.command == "status":
        sys.stdout.write(show_status(store, datetime.now(UTC)) + "\n")
    else:
        sys.stdout.write(show_profile(store, a.repo.resolve(), a.confirm, a.role, a.runtime) + "\n")
    return 0


def _overridden(layer: Layer, overrides: list[tuple[Role, RoleModel]]) -> Layer:
    """Set model and effort per role; the agent's other settings stay."""
    agents = dict(layer.agents)
    for role, rm in overrides:
        agents[role] = (agents.get(role) or Agent()).model_copy(update={"model": rm.model, "effort": rm.effort})
    return layer.model_copy(update={"agents": agents})


def _role(text: str) -> tuple[Role, RoleModel]:
    try:
        return roles.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0915 - one parser and one branch per command
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
    up.add_argument("--folder", default="", help="the project's folder in the shared settings when its name is taken")
    p = sub.add_parser("profile", help="detect the project profile; --confirm KEY=VALUE records the owner's answer")
    p.add_argument("--confirm", action="append", default=[], type=lambda v: tuple(v.split("=", 1)))
    p.add_argument("--role", action="append", default=[], type=_role, help="ROLE=MODEL:EFFORT model override")
    p.add_argument(
        "--runtime", choices=("managed", "vscode"), help="where agent steps run from the next one on (TD-35)"
    )
    s = sub.add_parser("seed", help="seed a pre-approved one-task Change and a minimal profile")
    s.add_argument("change")
    s.add_argument("--title", required=True)
    s.add_argument("--outcome", required=True)
    s.add_argument("--criterion", action="append", default=[])
    s.add_argument("--scope", action="append", default=[])
    s.add_argument("--check", action="append", default=[])
    s.add_argument("--install", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="DIR=CMD")
    s.add_argument(
        "--person-check", action="append", default=[], type=lambda v: tuple(v.split("=", 1)), help="ID=STEPS"
    )
    s.add_argument("--target", default="main")
    ans = sub.add_parser("answer", help="write an answer into the Change inbox")
    ans.add_argument("change")
    ans.add_argument("--question", required=True)
    ans.add_argument("--option")
    ans.add_argument("--text", default="")
    show = sub.add_parser("show", help="print the Change's step, exit and open question")
    show.add_argument("change")
    shared = sub.add_parser("common", help="show or set the shared settings repository (TD-57)")
    shared.add_argument("path", nargs="?", type=Path)
    pack = sub.add_parser("design-pack", help="show, install or update the pinned design pack (TD-76)")
    pack.add_argument("--install", action="store_true", help="download and verify what is missing")
    pack.add_argument("--check", action="store_true", help="count upstream releases since the pinned one")
    pack.add_argument(
        "--diff", type=Path, metavar="CLONE", help="rules and skill files changed, from an upstream clone"
    )
    pack.add_argument("--to", metavar="TAG", help="the candidate tag --diff compares with")
    pack.add_argument("--golden", action="store_true", help="run the engine and the in-page bundle on the golden pages")
    pack.add_argument("--replay", action="store_true", help="rerun the design judge on decided rounds (costs requests)")
    found = sub.add_parser("backlog", help="the improvement backlog: issues in the shared repository (TD-84, TD-103)")
    found = found.add_subparsers(dest="action", required=True)
    add = found.add_parser("add", help="add a finding; a repeat counts up its entry")
    add.add_argument("--title", required=True)
    add.add_argument("--text", default="")
    add.add_argument("--source", choices=("owner", "watcher", "assistant", "review", "run"), default="assistant")
    add.add_argument("--evidence", action="append", default=[], help="a Change, step, session, path or URL")
    found.add_parser("migrate", help="once: move the file entries into GitHub issues, then delete the files")
    a = parser.parse_args(argv)
    if a.command == "design-pack" and bool(a.diff) != bool(a.to):
        parser.error("--diff and --to go together")
    if a.command == "common":
        sys.stdout.write(show_common(a.path) + "\n")
        return 0
    if a.command == "design-pack":
        updating = a.check or a.diff or a.golden or a.replay
        return update_pack(a, a.repo.resolve()) if updating else show_pack(install=a.install)
    if a.command == "host":
        return host.serve(a.repo.resolve())
    if a.command == "setup":
        say, repo = lambda t: sys.stdout.write(t + "\n"), a.repo.resolve()
        found = setup.project_folder(repo, a.folder, setup.ask_tty, say)
        return setup.run(repo, a.confirm, yes=a.yes, local_files=a.local_files, skill=a.skill) if found else 1
    store = Store.open(a.repo.resolve())
    if a.command in {"backlog", "status", "profile"}:
        return report(store, a)
    if a.command == "seed":
        seed(store, a)
    elif a.command == "answer":
        item = AnswerItem(at=datetime.now(UTC), question=a.question, option=a.option, text=a.text)
        store.put_inbox(a.change, item)
    sys.stdout.write(describe(store.read(a.change)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
