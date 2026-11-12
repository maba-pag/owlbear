"""The project's check commands, settled with the owner once before a Change is planned (#968).

Every planned task runs the check commands of its packages, so a plan names only commands the owner confirmed. Before
the plan step starts its session, each package the brief's scope touches needs a confirmed check command, its own or
the root's (`.`). Otherwise the owner gets one question about the project: it names every package still unconfirmed,
so one answer settles them all and later Changes plan without asking.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import Answer, ErrorKind, Option, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import asking, loop, worktree
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import github_writer
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.state_store.store import Lock, Store

ROOT = "."
TYPED = asking.READ_BACK
PREFIX = cause_key(ErrorKind.GATE, StepKind.PLAN, "checks-")
_PAUSE = Option(id="pause", label="Pause this Change; nothing is planned until you answer", next="pause")


def profile_for(store: Store, lock: Lock, change: Change, repo: Path) -> Profile | None:
    """The profile the step runs with; None once the step recorded its result: a question or a provider failure."""
    prof = store.read_profile()
    if change.step.kind != StepKind.PLAN:
        return prof or Profile()
    now = datetime.now(UTC)
    if prof is None:
        try:
            gh = profile.provider(Profile(), repo, github_writer.of(store, repo, detecting=True))
            prof = profile.detect(repo, gh, None)
        except ProviderError as exc:
            store.write(lock, loop.apply(change, engine.failed(change, exc, now), now))
            return None
        _save(store, lock, change.slug, prof, [])
    scope = change.brief.scope
    if not (missing := _uncovered(prof, scope)):
        return profile.vouched(prof)
    cause = _cause(prof, missing)
    latest = next((q for q in reversed(change.questions) if q.answer and (q.cause or "").startswith(cause)), None)
    if commands := _answered(change, prof, missing, latest, cause):
        for home, command in commands.items():
            prof = profile.confirm(prof, f"check:{home}", command, now)
        _save(store, lock, change.slug, prof, [f"check:{home}" for home in commands])
        if not (missing := _uncovered(prof, scope)):
            return profile.vouched(prof)
        cause, latest = _cause(prof, missing), None  # typed lines that left part of the scope unconfirmed
    typed = latest is not None and latest.cause == cause and latest.answer.option == "typed"
    question = _read_back(prof, missing, latest, cause) if typed else _first(prof, missing, cause)
    store.write(lock, loop.apply(change, question, now))
    return None


def settle(store: Store, change: Change, now: datetime) -> None:
    """Close a Change's checks question another Change's answer made needless, so it plans without another answer."""
    q = loop.open_question(change)
    if q is None or not (q.cause or "").startswith(PREFIX):
        return
    if (prof := store.read_profile()) is not None and not _uncovered(prof, change.brief.scope):
        why = "the project's check commands were confirmed on another Change"
        q.answer = Answer(option="settled", text=why, at=now)
        q.effect_observed_at, change.outcome = now, None


def _packages(prof: Profile) -> set[str]:
    return {key.removeprefix("check:") for key in prof.entries if key.startswith("check:")}


def _homes(prof: Profile, scope: Sequence[str]) -> set[str]:
    """The packages whose checks the scope's tasks run: per path its deepest holding package and those inside it."""
    packages = _packages(prof)
    if not scope:
        return packages or {ROOT}
    homes: set[str] = set()
    for path in scope:
        holding = [d for d in packages if PurePosixPath(path).is_relative_to(d)]
        inside = {d for d in packages if PurePosixPath(d).is_relative_to(path)}
        deepest = {max(holding, key=lambda d: len(PurePosixPath(d).parts))} if holding else set()
        homes |= deepest | inside or {ROOT}  # a path in no package: every task needs a check, so the root's
    return homes


def _uncovered(prof: Profile, scope: Sequence[str]) -> list[str]:
    """Every unconfirmed package of the project once the scope touches one, with the root when the scope needs it."""
    homes, covered = _homes(prof, scope), {p for p, _ in worktree.checks(profile.vouched(prof))}
    if ROOT in covered or homes <= covered:
        return []
    return sorted((_packages(prof) | (homes & {ROOT})) - covered)


def _cause(prof: Profile, missing: list[str]) -> str:
    """The question's cause, bound to what was detected for each home it names: a new detection asks again."""
    seen = [[h, *((e.state, e.value) if (e := prof.entries.get(f"check:{h}")) else ("absent", ""))] for h in missing]
    return PREFIX + hashlib.sha256(json.dumps(seen).encode()).hexdigest()[:12]


def _detected(prof: Profile, home: str) -> str:
    entry = prof.entries.get(f"check:{home}")
    return entry.value if entry is not None and entry.state == "known" else ""


def _parsed(text: str, prof: Profile) -> tuple[dict[str, str], list[str]]:
    """The typed ``package: command`` lines, and the lines naming no package of the profile or no command."""
    homes, parsed, unparsed = _packages(prof) | {ROOT}, {}, []
    for line in filter(None, (raw.strip() for raw in text.splitlines())):
        home, sep, command = line.partition(": ")
        if sep and home.strip() in homes and command.strip():
            parsed[home.strip()] = command.strip()
        else:
            unparsed.append(line)
    return parsed, unparsed


def _answered(
    change: Change, prof: Profile, missing: list[str], latest: Question | None, cause: str
) -> dict[str, str] | None:
    """The commands the latest answer confirms: the detected ones, or the typed ones the owner saved."""
    if latest is None:
        return None
    if latest.cause == cause and latest.answer.option == "detected":
        return _proposed(prof, missing)
    first = next((q for q in change.questions if q.answer and latest.cause == f"{cause}{TYPED}{q.id}"), None)
    return _parsed(first.answer.text, prof)[0] if latest.answer.option == "save" and first else None


def _first(prof: Profile, missing: list[str], cause: str) -> loop.StepResult:
    """Once per project: yes or no on the detected commands (#1062); none detected is Delivery's to repair."""
    typed = (
        "No, I'll type the commands: one `package: command` per line (`.: command` covers every package); "
        "you see them again before anything is saved"
    )
    if not (proposed := _proposed(prof, missing)):
        named = ", ".join(f"`{h}`" for h in missing if not _detected(prof, h))
        text = f"No check command was detected for {named}: propose one for the project profile."
        result = engine.ask(StepKind.PLAN, text, cause)
        if result.question is not None:
            result.question.subject = "internal"  # its repair proposes a profile check, his yes or no
        return result
    said = {ROOT: "which covers every package"}
    named = "; ".join(f"`{c}`, {said.get(h, f'for `{h}`')}" for h, c in proposed.items())
    text = (
        f"Before a task's work counts as done, Delivery runs this project's own tests on it. It found {named}. "
        "Every task of every Change then waits for these tests to pass; what they leave out is tested only "
        "in CI before merge. Use it?"
    )
    detected = "Yes, use it: if it is wrong or slow, every task fails or slows with it"
    options = [Option(id="detected", label=detected, next="retry"), Option(id="typed", label=typed, next="retry")]
    result = engine.ask(StepKind.PLAN, text, cause, options)
    if result.question is not None:
        result.question.subject = "reserved"
    return result


def _proposed(prof: Profile, missing: list[str]) -> dict[str, str]:
    """The detected commands to propose: each missing package's, else the root's alone, which covers every package."""
    if all(_detected(prof, h) for h in missing):
        return {h: _detected(prof, h) for h in missing}
    return {ROOT: c} if ROOT in missing and (c := _detected(prof, ROOT)) else {}


def _read_back(prof: Profile, missing: list[str], first: Question, cause: str) -> loop.StepResult:
    parsed, unparsed = _parsed(first.answer.text, prof)
    left = [h for h in missing if h not in parsed and ROOT not in parsed]
    lines = [
        "These check commands will be saved to the project profile, and every Change's tasks will run them:",
        *([f"- `{h}`: `{c}`" for h, c in parsed.items()] or ["- none"]),
        *([f"Still not confirmed (asked next): {', '.join(f'`{h}`' for h in left)}"] if left else []),
        *(f"Not understood: {line}" for line in unparsed),
    ]
    save = [Option(id="save", label="Save these commands", next="retry")] if parsed and not unparsed else []
    options = [*save, Option(id="again", label="Type them again", next="retry"), _PAUSE]
    return engine.ask(StepKind.PLAN, "\n".join(lines), f"{cause}{TYPED}{first.id}", options)


def _save(store: Store, lock: Lock, slug: str, prof: Profile, keys: list[str]) -> None:
    """Save the profile; a raised store error propagates, and the answer, still the latest, is applied again."""
    notice = store.write_profile(prof)
    at = datetime.now(UTC).isoformat(timespec="seconds")
    for key in keys:
        store.log(lock, slug, {"event": "profile-confirmed", "at": at, "key": key})
    if notice:
        store.log(lock, slug, {"event": "profile-unpublished", "at": at, "notice": notice})
