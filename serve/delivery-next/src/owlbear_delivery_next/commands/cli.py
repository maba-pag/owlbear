"""Project commands, which `owlbear` runs too: ``setup``, ``status``; ``seed``, ``answer``, ``show`` for dev."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CalledProcessError

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
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
from owlbear_delivery_next.change_contracts.profile_record import (
    PAUSED_NOTE,
    Profile,
    ProfileEntry,
    RoleModel,
    Runtime,
    in_window,
)
from owlbear_delivery_next.change_flow.status import status, unloadable
from owlbear_delivery_next.commands import replay_client, setup
from owlbear_delivery_next.design_packs import design_pack, pack_update
from owlbear_delivery_next.design_packs.detector import DetectorError
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.pack_runs import pack_replay
from owlbear_delivery_next.project_host import answers, host
from owlbear_delivery_next.settings import profile, roles
from owlbear_delivery_next.settings.config import Agent, Layer
from owlbear_delivery_next.state_store import (
    backlog_migrate,
    offline_protocol,
    prefs_import,
    profile_share,
    project_home,
)
from owlbear_delivery_next.state_store.backlog import Backlog, BacklogError
from owlbear_delivery_next.state_store.config_save import Prepared
from owlbear_delivery_next.state_store.store import Store, StoreError

START = "run `owlbear start`, then add this project on its page"


def show_data(path: Path | None) -> str:
    """Record the shared settings repository when given, then say which one this machine uses."""
    try:
        shared = data_repo.point(path) if path else data_repo.locate()
    except data_repo.DataRepoError as exc:
        return f"Not set: {exc}"
    if shared is None:
        return "No shared settings repository; settings stay in each clone. Set one: `owlbear-next data PATH`"
    return f"Shared data repository: {shared.root} (pointer {data_repo.pointer()}). Run `owlbear restart` to use it."


def show_home() -> str:
    """Say where OwlBear keeps its files on this machine."""
    return f"OwlBear's folder: {local_home.root()}"


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
            ok, text = replay_client.replay(repo)
            sys.stdout.write(text + "\n")
            return 0 if ok else 1
        sys.stdout.write(pack_update.said(pack_update.notice(refresh=True)) + "\n")
    except (
        design_pack.PackError,
        pack_replay.ReplayError,
        DetectorError,
        data_repo.DataRepoError,
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


def answer(store: Store, a: argparse.Namespace) -> int:
    """Queue the owner's answer, classed and checked as the Changes page's is (TD-461); a refused one writes nothing."""
    q = next((q for q in store.read(a.change).questions if q.id == a.question and q.answer is None), None)
    kind = a.kind.replace("-", "_") if a.kind else None
    try:
        body = answers.AnswerBody(
            question=a.question, option=a.option, text=a.text, kind=kind, statement=a.statement, confirmed=a.confirmed
        )
    except ValidationError as exc:
        why = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
    else:
        why = f"question {a.question} is not open" if q is None else answers.classed(q, body)
        if not why:
            said = {"classed": body.kind, "statement": body.statement.strip()}
            item = AnswerItem(at=datetime.now(UTC), question=a.question, option=a.option, text=a.text, **said)
            store.put_inbox(a.change, item)
            return 0
    sys.stderr.write(f"not answered: {why}\n")
    return 1


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
    prefs_import.run(store)
    notice = (
        store.update_config(
            Prepared(profile_share.config_digest(store.config_path), lambda cur: _overridden(cur, overrides)),
            "role overrides from the CLI",
        )
        if overrides
        else ""
    )
    lines = [f"profile v{prof.version}", *([f"Notice: {notice}"] if notice else [])]
    lines += [f"  {k}: {e.state} {e.value!r} ({e.evidence})" for k, e in sorted(prof.entries.items())]
    paused = f" ({PAUSED_NOTE})" if prof.runtime == "vscode" and not in_window(prof) else ""
    return "\n".join([*lines, roles.table(store.settings()), f"Runtime: {prof.runtime}{paused}"])


def add_backlog(store: Store, a: argparse.Namespace) -> int:
    """Add a finding to the backlog issues (TD-84, TD-103), or count up the entry it repeats; print which."""
    if a.action == "migrate":
        if store.shared is None:
            sys.stdout.write("no shared repository is set up: nothing to migrate\n")
            return 1
        return backlog_migrate.migrate(store.shared, lambda said: sys.stdout.write(said + "\n"))
    try:
        entry, new = Backlog.of(store).add(a.title, a.text, a.source, a.evidence)
    except (BacklogError, data_repo.DataRepoError) as exc:
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
    elif a.runtime == "vscode" and not in_window(Profile(runtime="vscode")):
        sys.stderr.write(f"Runtime not switched: {PAUSED_NOTE}.\n")
        return 1
    else:
        try:
            sys.stdout.write(show_profile(store, a.repo.resolve(), a.confirm, a.role, a.runtime) + "\n")
        except ValueError as exc:  # a moved preference is refused before anything is recorded
            sys.stderr.write(f"Not recorded: {exc}.\n")
            return 1
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


def prepare_move(repo: Path) -> int:
    """Bind the clone's store id, then record its boot session and fence the move; nothing is copied or switched."""
    try:
        offline_protocol.prepare_clone(repo)
    except StoreError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write("prepared: reboot, then run owlbear-next finish; nothing has moved\n")
    return 0


def finish_move(repo: Path) -> int:
    """After a reboot: prove the preparation, switch to the target store and keep the old source in place."""
    source = project_home.clone_dir(repo)
    try:
        offline_protocol.finish_clone(repo)
        store = Store.open(repo)
    except StoreError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    sys.stdout.write(f"moved: authoritative store {store.root}; retained non-authoritative source {source}\n")
    return 0


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911, PLR0915 - one parser and one branch per command
    """Run one command."""
    parser = argparse.ArgumentParser(prog="owlbear-next")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="print every Change's status line and next action")
    up = sub.add_parser("setup", help="check readiness, confirm the profile, register the chat server")
    up.add_argument("--yes", action="store_true", help="confirm the profile (only the profile)")
    choices = ("yes", "no", "ask")
    up.add_argument("--local-files", choices=choices, default="ask", help="write .mcp.json and .vscode/settings.json")
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
    ans.add_argument("--kind", choices=("event", "clarification", "brief-change"), help="a worker's question's class")
    ans.add_argument("--statement", default="", help="a clarification's intent the owner confirmed when read back")
    ans.add_argument("--confirmed", action="store_true", help="the owner confirmed the statement as read back")
    show = sub.add_parser("show", help="print the Change's step, exit and open question")
    show.add_argument("change")
    shared = sub.add_parser("data", help="show or set the shared settings repository (TD-57)")
    shared.add_argument("path", nargs="?", type=Path)
    sub.add_parser("home", help="show OwlBear's folder on this machine (TD-198)")
    sub.add_parser("prepare", help="before a reboot: bind the clone's store id and fence the offline move")
    sub.add_parser("finish", help="after a reboot: prove the preparation and move the store; the source stays in place")
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
    add.add_argument(
        "--source", choices=("owner", "spotter", "retro", "assistant", "review", "run"), default="assistant"
    )
    add.add_argument("--evidence", action="append", default=[], help="a Change, step, session, path or URL")
    found.add_parser("migrate", help="once: move the file entries into GitHub issues, then delete the files")
    a = parser.parse_args(argv)
    if a.command == "design-pack" and bool(a.diff) != bool(a.to):
        parser.error("--diff and --to go together")
    if a.command in {"data", "home"}:
        sys.stdout.write((show_data(a.path) if a.command == "data" else show_home()) + "\n")
        return 0
    if a.command == "design-pack":
        updating = a.check or a.diff or a.golden or a.replay
        return update_pack(a, a.repo.resolve()) if updating else show_pack(install=a.install)
    if a.command == "setup":
        say, repo = lambda t: sys.stdout.write(t + "\n"), a.repo.resolve()
        found = setup.project_folder(repo, a.folder, setup.ask_tty, say)
        return setup.run(repo, a.confirm, yes=a.yes, local_files=a.local_files) if found else 1
    if a.command in {"prepare", "finish"}:
        return (prepare_move if a.command == "prepare" else finish_move)(a.repo.resolve())
    store = Store.open(a.repo.resolve())
    if a.command in {"backlog", "status", "profile"}:
        return report(store, a)
    if a.command == "seed":
        seed(store, a)
    elif a.command == "answer" and (code := answer(store, a)):
        return code
    sys.stdout.write(describe(store.read(a.change)) + "\n")
    return 0
