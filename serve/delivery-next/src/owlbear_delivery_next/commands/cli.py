"""Project commands, which `owlbear` runs too: ``setup``, ``status``, ``cases``; ``seed``, ``answer``, ``show``: dev."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Names,
    PersonCheck,
    Plan,
    Role,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import (
    Profile,
    ProfileEntry,
    RoleModel,
)
from owlbear_delivery_next.change_flow.status import status, unloadable
from owlbear_delivery_next.commands import cases_cli, project_commands, replay_client, setup
from owlbear_delivery_next.commands.answer_console import answer, describe
from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable.detector import DetectorError
from owlbear_delivery_next.impeccable_runs import pack_replay
from owlbear_delivery_next.local_system import data_place, data_repo, local_home
from owlbear_delivery_next.project_host import host
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

if TYPE_CHECKING:
    import argparse

START = "run `owlbear start`, then add this project on its page"


def show_data(target: str | Path | None) -> tuple[int, str]:
    """Use the shared data repository *target* names, then say which one this machine uses; 1 on a problem.

    A clone address is adopted from a checkout of it or cloned into ``~/.owlbear/data``; a folder is recorded as the
    override. Without one it finishes an interrupted move and shows what only this checkout holds.
    """
    if target is None:
        return _shown()
    try:
        if isinstance(target, str) and data_place.is_url(target):
            shared, done = data_place.provision(target, show=True)
        else:
            shared, done = data_place.point(Path(target)), ""
    except data_repo.DataRepoError as exc:
        return 1, f"Not set: {exc}"
    root = shared.root if shared else data_place.default()
    said = f"{done[:1].upper()}{done[1:]}. " if done else ""
    return 0, f"{said}Shared data repository: {root} (pointer {data_place.pointer()}). Run `owlbear restart` to use it."


def _shown() -> tuple[int, str]:
    finished = ""
    try:
        with data_place.pointer_lock():
            finished = data_place.recover()
    except data_place.BusyError:
        pass
    except data_repo.DataRepoError as exc:
        return 1, f"Shared data: problem: {exc}"
    found = data_place.describe()
    lines = [f"{finished[:1].upper()}{finished[1:]}."] if finished else []
    if found.kind == "none":
        lines.append(
            "No shared settings repository; settings stay in each clone. Set one: `owlbear data URL` clones it into "
            f"{data_place.default()}, `owlbear data PATH` uses a checkout you keep elsewhere"
        )
    else:
        lines.append(found.line.replace("shared data:", "Shared data repository:", 1))
    if found.root is not None:
        held = data_place.inventory(data_repo.DataRepo(found.root))
        lines += ["Only on this machine, so back it up:", *(f"  {line}" for line in held)] if held else []
    return (1 if found.kind == "problem" else 0), "\n".join(lines)


def show_home() -> str:
    """Say where OwlBear keeps its files on this machine."""
    return f"OwlBear's folder: {local_home.root()}"


def show_pack(*, install: bool) -> int:
    """Print Impeccable's state; with ``install``, download and verify what is missing first."""
    if install:
        try:
            pack_files.install()
        except pack_files.PackError as exc:
            sys.stdout.write(f"Not installed: {exc}\n")
            return 1
    sys.stdout.write(pack_files.status() + "\n")
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
        pack_files.PackError,
        pack_replay.ReplayError,
        DetectorError,
        data_repo.DataRepoError,
        CalledProcessError,
        OSError,
        ValueError,
    ) as exc:
        sys.stdout.write(f"Impeccable: {type(exc).__name__}: {exc}\n")
        return 1
    return 0


def _golden() -> int:
    pack = pack_files.installed()
    if pack is None:
        sys.stdout.write("Impeccable not installed: run `owlbear-next impeccable --install`\n")
        return 1
    wrong = pack_update.golden(pack)
    for page, w in wrong.items():
        missing, unexpected = ", ".join(w["missing"]) or "none", ", ".join(w["unexpected"]) or "none"
        sys.stdout.write(f"golden page {page}: missing {missing}; unexpected {unexpected}\n")
    sys.stdout.write("golden pages: " + ("differ" if wrong else "as expected") + "\n")
    return 1 if wrong else 0


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
    store.write_profile(Profile(version=old.version + 1, confirmed_at=now, entries=entries))
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
) -> str:
    """Detect the profile, apply the owner's confirmations and role overrides to the project settings."""
    prof = profile.detect(repo, profile.provider(store.read_profile() or Profile(), repo), store.read_profile())
    for key, value in confirms:
        prof = profile.confirm(prof, key, value, datetime.now(UTC))
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
    return "\n".join([*lines, roles.table(store.settings())])


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
    else:
        try:
            sys.stdout.write(show_profile(store, a.repo.resolve(), a.confirm, a.role) + "\n")
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


def main(argv: list[str] | None = None) -> int:
    """Run one command; a usage error exits 2."""
    a = project_commands.app.meta(argv)
    return 0 if a is None else run(a)


def run(a: argparse.Namespace) -> int:  # noqa: PLR0911 - one branch per command
    """Run the command *a* names, as :mod:`project_commands` parsed it."""
    if a.command in {"cases", "improvement"}:
        return cases_cli.main(a)
    if a.command in {"data", "home"}:
        code, said = show_data(a.target) if a.command == "data" else (0, show_home())
        sys.stdout.write(said + "\n")
        return code
    if a.command == "impeccable":
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
    sys.stdout.write(describe(store.read(a.change), store) + "\n")
    return 0
