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
from owlbear_delivery_next.change_contracts.models import ErrorKind, Option, StepKind
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import loop
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
TYPED = "-typed-"
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
    typed = latest is not None and latest.cause == cause and _option(latest) == "typed"
    question = _read_back(prof, missing, latest, cause) if typed and latest else _first(prof, missing, cause)
    store.write(lock, loop.apply(change, question, now))
    return None


def _packages(prof: Profile) -> set[str]:
    return {key.removeprefix("check:") for key in prof.entries if key.startswith("check:")}


def _vouched(prof: Profile, home: str) -> bool:
    """Whether the owner confirmed a check command that covers *home*: its own or the root's."""
    entries = (prof.entries.get(f"check:{key}") for key in (home, ROOT))
    return any(e is not None and e.state == "known" and e.value and profile.is_confirmed(e) for e in entries)


def _homes(prof: Profile, scope: Sequence[str]) -> set[str]:
    """The packages whose checks the scope's tasks run: per path its deepest holding package and those inside it."""
    packages = _packages(prof)
    if not scope:
        return packages or {ROOT}
    homes: set[str] = set()
    for path in scope:
        parts = PurePosixPath(path).parts
        holding = [d for d in packages if parts[: len(dp := PurePosixPath(d).parts)] == dp]
        inside = {d for d in packages if PurePosixPath(d).parts[: len(parts)] == parts}
        deepest = {max(holding, key=lambda d: len(PurePosixPath(d).parts))} if holding else set()
        homes |= deepest | inside or {ROOT}  # a path in no package: every task needs a check, so the root's
    return homes


def _uncovered(prof: Profile, scope: Sequence[str]) -> list[str]:
    """Every unconfirmed package of the project once the scope touches one, with the root when the scope needs it."""
    homes = _homes(prof, scope)
    if all(_vouched(prof, home) for home in homes):
        return []
    return sorted(home for home in _packages(prof) | (homes & {ROOT}) if not _vouched(prof, home))


def _cause(prof: Profile, missing: list[str]) -> str:
    """The question's cause, bound to what was detected for each home it names: a new detection asks again."""
    seen = [[h, *((e.state, e.value) if (e := prof.entries.get(f"check:{h}")) else ("absent", ""))] for h in missing]
    digest = hashlib.sha256(json.dumps(seen).encode()).hexdigest()[:12]
    return cause_key(ErrorKind.GATE, StepKind.PLAN, f"checks-{digest}")


def _option(q: Question) -> str | None:
    return q.answer.option if q.answer else None


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
    if latest.cause == cause and _option(latest) == "detected":
        return {home: _detected(prof, home) for home in missing}
    asked = (latest.cause or "").removeprefix(f"{cause}{TYPED}")
    first = next((q for q in change.questions if q.id == asked and q.answer), None)
    return _parsed(first.answer.text, prof)[0] if _option(latest) == "save" and first and first.answer else None


def _first(prof: Profile, missing: list[str], cause: str) -> loop.StepResult:
    named = ", ".join(
        f"`{h}` ({f'detected: `{c}`' if (c := _detected(prof, h)) else 'none detected'})" for h in missing
    )
    text = (
        "Which commands check this project's code? Every planned task runs them before its work counts as done; "
        f"tests no command runs are left to CI. Not confirmed yet: {named}. Nothing is planned until you answer."
    )
    typed = (
        "Use commands I type in the answer, one `package: command` per line (`.: command` covers every package); "
        "you see them again before anything is saved"
    )
    detected = "Use the detected commands: every task runs them, and a wrong or slow one fails or slows every task"
    options = [Option(id="detected", label=detected, next="retry")] if all(_detected(prof, h) for h in missing) else []
    options += [Option(id="typed", label=typed, next="retry"), _PAUSE]
    return engine.ask(StepKind.PLAN, text, cause, options)


def _read_back(prof: Profile, missing: list[str], first: Question, cause: str) -> loop.StepResult:
    parsed, unparsed = _parsed(first.answer.text if first.answer else "", prof)
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
