"""Spotter cases (Improvement design §4): frozen cards with the right call and why, in stages and versions.

A case is a frozen card (never changed), its facts (source, local provenance, session family, whether it is in the
reserve, whether it is scored, the assumption it rests on) and, in each version, its stage (candidate, test case,
active example), its call (a finding category or ``none``), why, the example text the prompt shows, and its review.
Every change appends a whole version to ``versions.jsonl``; a rollback appends a copy of an earlier one. Kept on this
machine, owner-only, in ``~/.owlbear/spotter/cases/``.

Rules every version keeps: a test case or an example has a call, a why and a review of exactly its current card, call
and why; an example has its text and is neither in the reserve, nor synthetic, nor unscored; all examples together
stay within ``EXAMPLES`` characters. A case whose assumption was retired is in no new version. A version whose active
examples differ from its parent's is written only with a passed regression run bound to that very parent and change
(``case_replay``): nothing else changes what the Spotter is shown.

The prompt a look sends is one immutable ``Prompt`` snapshot (the prompt file, the verbose line, the examples), frozen
when a step starts or a chat turn begins; its hash is of exactly those bytes.
"""

from __future__ import annotations

import contextlib
import fcntl
import gzip
import hashlib
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.settings.improvement import CATEGORIES

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

PROMPT = Path(__file__).with_name("spotter_prompt.md")
VERBOSE = "\n\nVerbose: also give a short `rationale` (at most 5 sentences) naming the evidence."
STAGES = ("candidate", "test", "example")
CALLS = (*CATEGORIES, "none")
SOURCES = ("pilot", "record", "synthetic")
EXAMPLES, EXAMPLE, WHY = 6000, 800, 600  # characters of all examples in the prompt, of one example, of a why
LOCK = 20.0  # seconds the store's lock is waited for

type Entry = dict[str, Any]  # a case in one version: stage, call, why, example, review
type Cases = dict[str, Entry]


class CaseError(Exception):
    """A refused change of the cases, said as the owner should read it."""


class Stale(CaseError):  # noqa: N818 - says what happened
    """The cases changed since the change was asked for."""


def place() -> Path:
    """Where the cases are kept; nothing is created."""
    return local_home.root() / "spotter" / "cases"


def ready() -> Path:
    """The cases' folder, created owner-only with its cards' folder if needed."""
    folder = place()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    (folder / "cards").mkdir(exist_ok=True, mode=0o700)
    return folder


_held = threading.local()
_thread_lock = threading.RLock()


@contextlib.contextmanager
def locked() -> Iterator[None]:
    """The store's one writer, across threads and processes; re-entrant within a thread.

    Raises:
        CaseError: Another writer holds it past ``LOCK``.
    """
    if getattr(_held, "depth", 0):
        _held.depth += 1
        try:
            yield
        finally:
            _held.depth -= 1
        return
    with _thread_lock:
        fd = os.open(ready() / "cases.lock", os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            until = time.monotonic() + LOCK
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > until:
                        msg = "another change of the Spotter cases is still running; try again"
                        raise CaseError(msg) from None
                    time.sleep(0.05)
            _held.depth = 1
            try:
                yield
            finally:
                _held.depth = 0
        finally:
            os.close(fd)


def now() -> str:
    """The time, as every file here writes it."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def digest(value: object) -> str:
    """The start of the hash of *value*'s canonical JSON."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def append(name: str, line: Mapping[str, Any]) -> None:
    """Append *line* to the store's file *name*, owner-only; the caller holds ``locked``."""
    fd = os.open(ready() / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as out:
        out.write(json.dumps(line, ensure_ascii=False) + "\n")


def lines(name: str) -> list[dict[str, Any]]:
    """Every line of the store's file *name*; none when it is missing.

    Raises:
        CaseError: A line cannot be read.
    """
    try:
        text = (place() / name).read_text()
    except FileNotFoundError:
        return []
    try:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        msg = f"{name} cannot be read: {exc}"
        raise CaseError(msg) from exc


# The cases' facts and cards: written once, never changed


def freeze(card: dict[str, Any], fact: dict[str, Any]) -> str:
    """Keep a new case's *card* and *fact* (source, provenance, family, reserve, unscored, assumption); its id."""
    if fact.get("source") not in SOURCES:
        msg = f"a case's source is one of {', '.join(SOURCES)}"
        raise CaseError(msg)
    cid = f"c-{uuid.uuid4().hex[:10]}"
    folder = ready()
    fd = os.open(folder / "cards" / f"{cid}.json.gz", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as raw, gzip.open(raw, "wt") as out:
        json.dump(card, out, ensure_ascii=False)
    fact = {
        "id": cid,
        "made": now(),
        "provenance": {},
        "family": "",
        "reserve": False,
        "unscored": "",
        "assumption": "",
        **fact,
        "card": digest(card),
    }
    fd = os.open(folder / f"{cid}.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(fact, out, ensure_ascii=False, indent=1)
    return cid


def fact(cid: str) -> dict[str, Any]:
    """A case's facts.

    Raises:
        CaseError: There is no such case, or it cannot be read.
    """
    try:
        return json.loads((place() / f"{cid}.json").read_text())
    except (OSError, ValueError) as exc:
        msg = f"case {cid} cannot be read: {exc}"
        raise CaseError(msg) from exc


def card(cid: str) -> dict[str, Any]:
    """A case's frozen card, checked against the hash its facts keep.

    Raises:
        CaseError: It is missing, unreadable or not the card frozen.
    """
    try:
        with gzip.open(place() / "cards" / f"{cid}.json.gz", "rt") as fh:
            the_card = json.load(fh)
    except (OSError, ValueError) as exc:
        msg = f"the card of case {cid} cannot be read: {exc}"
        raise CaseError(msg) from exc
    if digest(the_card) != fact(cid)["card"]:
        msg = f"the card of case {cid} is not the one frozen"
        raise CaseError(msg)
    return the_card


def content(cid: str, entry: Entry) -> str:
    """What a review vouches for: the case's card with its call and why."""
    return digest([fact(cid)["card"], entry.get("call", ""), entry.get("why", "")])


# Versions


def versions() -> list[dict[str, Any]]:
    """Every version, oldest first."""
    return lines("versions.jsonl")


def current() -> dict[str, Any]:
    """The newest version; version 0, with no case, before any."""
    found = versions()
    return found[-1] if found else {"n": 0, "cases": {}}


def version(n: int) -> dict[str, Any]:
    """Version *n*.

    Raises:
        CaseError: There is no such version.
    """
    if n == 0:
        return {"n": 0, "cases": {}}
    for v in versions():
        if v["n"] == n:
            return v
    msg = f"there is no version {n} of the Spotter cases"
    raise CaseError(msg)


def examples(cases: Cases) -> dict[str, Entry]:
    """The active examples of *cases*, by id."""
    return {cid: e for cid, e in cases.items() if e.get("stage") == "example"}


def shown(cases: Cases) -> list[tuple[str, str, str, str]]:
    """What the prompt shows of *cases*' examples: id, text, call and why, in a stable order."""
    return [(cid, e["example"], e["call"], e["why"]) for cid, e in sorted(examples(cases).items())]


def applied(cases: Cases, edits: Mapping[str, Entry | None]) -> Cases:
    """*cases* with *edits* (an entry, or None to remove the case) applied, cases of retired assumptions left out."""
    out = dict(cases)
    for cid, entry in edits.items():
        if entry is None:
            out.pop(cid, None)
        else:
            out[cid] = dict(entry)
    return {cid: e for cid, e in out.items() if _standing(cid)}


def _standing(cid: str) -> bool:
    name = fact(cid).get("assumption") or ""
    return not name or assumptions.active(name)


def problems(cases: Cases) -> list[str]:  # noqa: C901 - one rule after another
    """Every rule *cases* break."""
    out, total = [], 0
    for cid, e in sorted(cases.items()):
        f = fact(cid)
        stage, call = e.get("stage"), e.get("call", "")
        if stage not in STAGES:
            out.append(f"{cid}: the stage is one of {', '.join(STAGES)}")
            continue
        if call and call not in CALLS:
            out.append(f"{cid}: the call is one of {', '.join(CALLS)}")
        if len(e.get("why", "")) > WHY:
            out.append(f"{cid}: why has at most {WHY} characters")
        if stage == "candidate":
            continue
        if not call or not e.get("why", "").strip():
            out.append(f"{cid}: a {stage} needs its call and why")
        review = e.get("review") or {}
        if not review.get("by") or review.get("content") != content(cid, e):
            out.append(f"{cid}: a {stage} needs a review of its card with this call and why")
        if stage == "example":
            text = e.get("example", "").strip()
            if not text or len(text) > EXAMPLE:
                out.append(f"{cid}: an example needs its text, at most {EXAMPLE} characters")
            if f["reserve"] or f["source"] == "synthetic" or f["unscored"]:
                out.append(f"{cid}: a reserve, synthetic or unscored case is never an example")
            total += len(text) + len(e.get("why", ""))
    if total > EXAMPLES:
        out.append(f"the examples have {total} characters, more than the prompt's {EXAMPLES}")
    return out


def commit(parent: int, edits: Mapping[str, Entry | None], by: str, reason: str, run: str = "") -> int:
    """Write the version *edits* make of version *parent*; its number.

    A change of the active examples needs *run*: a passed regression run of exactly this parent and change.

    Raises:
        Stale: The newest version is no longer *parent*.
        CaseError: The change breaks a rule, or changes the examples without its passed run.
    """
    with locked():
        cur = current()
        if cur["n"] != parent:
            msg = f"the Spotter cases are at version {cur['n']} now, not {parent}"
            raise Stale(msg)
        cases = applied(cur["cases"], edits)
        if found := problems(cases):
            raise CaseError("; ".join(found))
        if shown(cases) != shown(cur["cases"]) and not passed(run, parent, edits):
            msg = "a change of the active examples needs its regression run to pass first"
            raise CaseError(msg)
        n = parent + 1
        append(
            "versions.jsonl",
            {"n": n, "at": now(), "by": by, "reason": reason, "parent": parent, "run": run, "cases": cases},
        )
        return n


def passed(run: str, parent: int, edits: Mapping[str, Entry | None]) -> bool:
    """Whether *run* is a passed regression run of *edits* to version *parent*."""
    if not run:
        return False
    return any(
        r.get("id") == run
        and r.get("kind") == "regression"
        and r.get("result") == "passed"
        and r.get("parent") == parent
        and r.get("edits") == digest(edits)
        for r in lines("runs.jsonl")
    )


def rollback_edits(n: int) -> dict[str, Entry | None]:
    """The edits that make the newest version a copy of version *n* (cases of retired assumptions stay out)."""
    old, cur = version(n)["cases"], current()["cases"]
    return {**{cid: None for cid in cur if cid not in old}, **old}


def reset() -> tuple[list[str], int | None]:
    """Retire every marked assumption, then leave out every case resting on one; the ids retired, the new version.

    Synthetic cases are never examples, so leaving them out never changes what the Spotter is shown.
    """
    retired = assumptions.reset()
    with locked():
        cur = current()
        gone = [cid for cid in cur["cases"] if not _standing(cid)]
        if not gone:
            return retired, None
        return retired, commit(cur["n"], dict.fromkeys(gone), "reset", "marked assumptions retired")


# The prompt


@dataclass(frozen=True)
class Prompt:
    """What a look sends before its card, frozen once: exactly these bytes, their hash and the cases they show."""

    text: str
    cases: int  # the version its examples come from; 0: none
    hash: str
    gap: str = ""  # why the examples are missing, else nothing


def render(cases: Cases, n: int, *, verbose: bool) -> Prompt:
    """The prompt showing *cases*' examples as version *n*.

    Raises:
        OSError: The prompt file cannot be read.
    """
    text = PROMPT.read_text() + (VERBOSE if verbose else "")
    if shown_ := shown(cases):
        text += (
            "\n\n## Examples\n\nPast moments with the right call and why. They illustrate and never limit: judge "
            "the card in front of you."
        )
        for i, (_cid, example, call, why) in enumerate(shown_, 1):
            text += f"\n\n### Example {i}\n\nMoment: {example}\n\nRight call: `{call}`\n\nWhy: {why}"
    return Prompt(text, n, hashlib.sha256(text.encode()).hexdigest()[:12])


def snapshot(*, verbose: bool) -> Prompt:
    """The prompt with the newest version's examples; never raises.

    An unreadable store gives the prompt without examples and says why; an unreadable prompt file gives no text,
    which fails the look.
    """
    try:
        cur = current()
        return render(cur["cases"], cur["n"], verbose=verbose)
    except (CaseError, OSError, ValueError, KeyError, TypeError) as exc:
        gap = f"the Spotter cases could not be read, so no examples were shown ({type(exc).__name__})"
    try:
        base = render({}, 0, verbose=verbose)
    except OSError:
        return Prompt("", 0, "unreadable", "the Spotter's prompt could not be read")
    return Prompt(base.text, 0, base.hash, gap)


def of_version(n: int, *, verbose: bool = False) -> Prompt:
    """The prompt of version *n*, for a replay; never another version's.

    Raises:
        CaseError: Version *n* or the prompt file cannot be read.
    """
    try:
        return render(version(n)["cases"], n, verbose=verbose)
    except OSError as exc:
        msg = f"the Spotter's prompt cannot be read: {exc}"
        raise CaseError(msg) from exc


# Changes the owner asks for


def edited(  # noqa: PLR0913 - what the owner may change, each optional
    cid: str,
    entry: Entry,
    *,
    stage: str = "",
    call: str = "",
    why: str = "",
    example: str = "",
    reviewed_by: str = "",
    note: str = "",
) -> Entry:
    """*entry* of case *cid* with what is given changed; a review by *reviewed_by* vouches for the result."""
    given = {"stage": stage, "call": call, "why": why, "example": example}
    out = {**entry, **{k: v for k, v in given.items() if v}}
    if (call or why) and not reviewed_by:
        out["review"] = None  # a changed call or why is no longer what was reviewed
    if reviewed_by:
        out["review"] = {"by": reviewed_by, "at": now(), "note": note[:600], "content": content(cid, out)}
    return out
