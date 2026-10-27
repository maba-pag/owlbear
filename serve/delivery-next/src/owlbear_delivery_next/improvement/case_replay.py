"""Replays of Spotter cases (Improvement design §4): the regression gate, releases and the reserve comparison.

A replay is paid: each case's frozen card goes to a real look. It starts only on the owner's word (his command, or a
chat acting on it; D-01M5XCE8ZEX5WPSCBZ5Y9S4K96), runs as the machine host's job, and stops at its run credit limit:
every look is metered against what the run has left, a retry included, and unknown spend admits no further look
(D-01M5XCD49YHHR1NQKKY8TQD0C3).

**Regression** (a smoke check, not proof): a change of the active examples is replayed before it is written. The
scored cases and their expected calls are frozen when it is asked for (the current version's test cases that are
neither in the reserve, nor unscored, nor an example in either version), with both prompts. Each case gets one look
with each prompt. False notes, misses and wrong categories are counted apart; the change is refused when any of them
rises, with no trade between them (D-01M5XCDRZJQJW4JMAQQ5G371YV), and when the comparison is empty, incomplete or
stopped. A passing change is written only onto the very version it was asked against; else it is refused as stale and
nothing is rerun.

**Release** (a marked assumption, ``assumptions.RELEASE``): a frozen manifest of the reviewed corpus (each test case's
and example's card hash, expected call, family and reserve mark) and the grading contract. Equal manifests are one
release, so choosing examples makes none. **Comparison**: two versions' prompts on the release's reserve cases, claimed
once per release before its first look; a crash after it keeps the claim. The reserve was already seen in the pilot's
prompt experiments: it is historically exposed, not unseen.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import assumptions, cases
from owlbear_delivery_next.improvement.cases import CaseError, Prompt, Stale
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.improvement.events import clip
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.settings.improvement import CATEGORIES

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from owlbear_delivery_next.improvement.cases import Entry

GRADING = (
    "no-trade-1"  # silence right for `none`; false notes, misses and wrong categories counted apart, none may rise
)
SILENT = frozenset({"none", "insufficient-context"})
COUNTS = ("false_notes", "misses", "wrong_categories")

type Look = Callable[[dict[str, Any], Prompt, Meter], Awaitable[dict[str, Any]]]  # a parsed answer, or raises


def grade(expected: str, said: str) -> str:
    """One answer against its expected call: right, or which kind of wrong (``failed`` when it said nothing usable)."""
    if said not in SILENT and said not in CATEGORIES:
        return "failed"
    if expected == "none":
        return "right" if said in SILENT else "false_notes"
    if said in SILENT:
        return "misses"
    return "right" if said == expected else "wrong_categories"


def _prompt(p: Prompt) -> dict[str, Any]:
    return {"text": p.text, "cases": p.cases, "hash": p.hash}


# Asking: what is frozen when the owner asks


def regression(edits: Mapping[str, Entry | None], by: str, reason: str) -> dict[str, Any]:
    """The replay request of *edits* to the newest version, everything it compares frozen now.

    Raises:
        CaseError: The change breaks a rule, does not change the examples, or leaves nothing to compare.
    """
    with cases.locked():
        cur = cases.current()
        after = cases.applied(cur["cases"], edits)
        if found := cases.problems(after):
            raise CaseError("; ".join(found))
        if cases.shown(after) == cases.shown(cur["cases"]):
            msg = "the change leaves the active examples as they are: write it without a replay"
            raise CaseError(msg)
        shown = {cid for c in (cur["cases"], after) for cid in cases.examples(c)}
        frozen = {
            cid: {"call": e["call"], "card": cases.fact(cid)["card"]}
            for cid, e in sorted(cur["cases"].items())
            if e["stage"] == "test" and cid not in shown and _scored(cid)
        }
        if not frozen:
            msg = "no test case is left to compare the two prompts on: the change is refused"
            raise CaseError(msg)
        before = cases.render(cur["cases"], cur["n"], verbose=False)
        proposed = cases.render(after, cur["n"] + 1, verbose=False)
    return {
        "id": f"r-{uuid.uuid4().hex[:10]}",
        "kind": "regression",
        "at": cases.now(),
        "by": by,
        "reason": reason,
        "parent": cur["n"],
        "edits": dict(edits),
        "edits_hash": cases.digest(edits),
        "frozen": frozen,
        "prompts": {"before": _prompt(before), "after": _prompt(proposed)},
    }


def _scored(cid: str) -> bool:
    f = cases.fact(cid)
    return not f["reserve"] and not f["unscored"]


def manifest(n: int | None = None) -> dict[str, Any]:
    """The release manifest of version *n* (the newest by default): its reviewed corpus and the grading contract."""
    v = cases.current() if n is None else cases.version(n)
    corpus = {}
    for cid, e in sorted(v["cases"].items()):
        f = cases.fact(cid)
        if e["stage"] in {"test", "example"} and not f["unscored"]:
            corpus[cid] = {"card": f["card"], "call": e["call"], "family": f["family"], "reserve": f["reserve"]}
    return {"grading": GRADING, "assumption": assumptions.RELEASE, "corpus": corpus}


def release(by: str) -> tuple[str, bool]:
    """Freeze the newest version's corpus as a release; its id and whether it is new (equal manifests are one).

    Raises:
        CaseError: The release definition was reset, or nothing is reviewed yet.
    """
    if not assumptions.ensure(assumptions.RELEASE):
        msg = "the release definition was reset: a decided definition must replace it first"
        raise CaseError(msg)
    with cases.locked():
        m = manifest()
        if not m["corpus"]:
            msg = "no reviewed case to release yet"
            raise CaseError(msg)
        rid = f"rel-{cases.digest(m)}"
        if any(r["id"] == rid for r in cases.lines("releases.jsonl")):
            return rid, False
        cases.append(
            "releases.jsonl", {"id": rid, "at": cases.now(), "by": by, "version": cases.current()["n"], "manifest": m}
        )
        return rid, True


def _release(rid: str) -> dict[str, Any]:
    for r in cases.lines("releases.jsonl"):
        if r["id"] == rid:
            return r
    msg = f"there is no release {rid}"
    raise CaseError(msg)


def claimed(rid: str) -> bool:
    """Whether release *rid*'s one comparison was used."""
    return any(c.get("release") == rid for c in cases.lines("claims.jsonl"))


def comparison(rid: str, a: int, b: int, by: str) -> dict[str, Any]:
    """The reserve comparison request of versions *a* and *b* on release *rid*, frozen now.

    Raises:
        CaseError: The release definition was reset, the release is unknown or used, or it has no reserve case.
    """
    if not assumptions.active(assumptions.RELEASE):
        msg = "the release definition was reset: no release may be compared"
        raise CaseError(msg)
    rel = _release(rid)
    if claimed(rid):
        msg = f"release {rid} already used its one comparison on the reserve"
        raise CaseError(msg)
    frozen = {
        cid: {"call": c["call"], "card": c["card"]} for cid, c in rel["manifest"]["corpus"].items() if c["reserve"]
    }
    if not frozen:
        msg = f"release {rid} has no reserve case to compare on"
        raise CaseError(msg)
    return {
        "id": f"r-{uuid.uuid4().hex[:10]}",
        "kind": "compare",
        "at": cases.now(),
        "by": by,
        "release": rid,
        "versions": [a, b],
        "frozen": frozen,
        "prompts": {"before": _prompt(cases.of_version(a)), "after": _prompt(cases.of_version(b))},
    }


def _claim(request: dict[str, Any]) -> None:
    """Claim the release's one comparison, durably, before the first look.

    Raises:
        CaseError: It was claimed already, or the definition was reset.
    """
    with cases.locked():
        if not assumptions.active(assumptions.RELEASE):
            msg = "the release definition was reset: no release may be compared"
            raise CaseError(msg)
        if claimed(request["release"]):
            msg = f"release {request['release']} already used its one comparison on the reserve"
            raise CaseError(msg)
        cases.append("claims.jsonl", {"release": request["release"], "run": request["id"], "at": cases.now()})


# Running: the job's part


async def run(  # noqa: C901 - the run, its stop and its result
    request: dict[str, Any], look: Look, meter: Meter, look_limit: float, halt: Callable[[], str] = str
) -> dict[str, Any]:
    """Replay *request* within the run's *meter*, each look on its own meter of *look_limit*; its result, kept.

    *halt* says why no further look may start (OwlBear stopping), else nothing. A look meter or the run's meter that
    stopped (its limit reached, or its spend unknown), even on the final look, vetoes the result: a regression is then
    refused, a comparison incomplete. A passing regression is written onto the version it was asked against, under
    the store's lock.
    """
    out: dict[str, Any] = {k: request[k] for k in ("id", "kind", "by", "frozen") if k in request}
    out |= {
        "asked": request["at"],
        "started": cases.now(),
        "parent": request.get("parent"),
        "edits": request.get("edits_hash"),
        "release": request.get("release"),
        "versions": request.get("versions"),
        "prompts": {k: p["hash"] for k, p in request["prompts"].items()},
    }
    prompts = {k: Prompt(p["text"], p["cases"], p["hash"]) for k, p in request["prompts"].items()}
    answers: dict[str, dict[str, Any]] = {}
    looks: list[dict[str, Any]] = []  # each look meter's report
    why = ""
    try:
        if request["kind"] == "compare":
            _claim(request)
        for cid, want in request["frozen"].items():
            the_card = cases.card(cid)
            if cases.fact(cid)["card"] != want["card"]:
                msg = f"the card of case {cid} is not the one frozen"
                raise CaseError(msg)  # noqa: TRY301
            answers[cid] = {}
            for side, prompt in prompts.items():
                said = await _once(the_card, prompt, look, meter, look_limit, halt, looks)
                answers[cid][side] = {**said, "grade": grade(want["call"], said.get("category", ""))}
                if answers[cid][side]["grade"] == "failed":
                    why = why or f"case {cid} got no usable answer twice"
            if why:
                break
    except _Stopped as exc:
        why = f"stopped: {exc}"
    except CaseError as exc:
        why = str(exc)
    why = why or _vetoed(meter, looks)
    out |= {"answers": answers, "counts": _counts(answers), "credits": meter.report(), "ended": cases.now()}
    out["result"] = _result(request, answers, why, out["counts"])
    with cases.locked():
        cases.append("runs.jsonl", out)
        if request["kind"] == "regression" and out["result"] == "passed":
            try:
                n = cases.commit(request["parent"], request["edits"], request["by"], request["reason"], out["id"])
                cases.append("runs.jsonl", {"id": out["id"], "applied": n, "at": cases.now()})
            except Stale as exc:
                note = f"refused as stale: {exc}; nothing is rerun"
                cases.append("runs.jsonl", {"id": out["id"], "applied": None, "why": note, "at": cases.now()})
                out["applied"] = note
            else:
                out["applied"] = n
    return out


class _Stopped(Exception):  # noqa: N818 - the run's limit stopped it
    pass


def _vetoed(run_meter: Meter, looks: list[dict[str, Any]]) -> str:
    """Why the meters veto the result: a stopped or unknown spend anywhere, the final look's included; else nothing."""
    for report in (run_meter.report(), *looks):
        if report["stopped"] or not report["credits_known"]:
            return f"stopped: the {report['stopped_by'] or 'look'} spend is {report['stopped'] or 'unknown'}"
    return ""


async def _once(  # noqa: PLR0913, PLR0917 - the card, its prompt and look, the meters and the stop
    the_card: dict[str, Any],
    prompt: Prompt,
    look: Look,
    run_meter: Meter,
    look_limit: float,
    halt: Callable[[], str],
    looks: list[dict[str, Any]],
) -> dict[str, Any]:
    """One look, retried once on an unusable answer, on its own look meter inside the run's."""
    if stop := halt():
        raise _Stopped(stop)
    if not run_meter.admit():
        stop = f"the replay-run spend is {run_meter.report()['stopped']}"
        raise _Stopped(stop)
    meter = Meter(look_limit, "look", parent=run_meter)
    said: dict[str, Any] = {}
    for _ in range(2):
        if halt() or not meter.admit():
            break
        try:
            said = await look(the_card, prompt, meter)
        except Exception as exc:  # noqa: BLE001 - a failed look is retried once, then counted
            said = {"category": "failed", "note": f"{type(exc).__name__}: {exc}"[:300]}
        if said.get("category") in SILENT or said.get("category") in CATEGORIES:
            break
    looks.append(meter.report())
    if said.get("category") not in SILENT | set(CATEGORIES) and (stop := halt() or meter.report()["stopped"]):
        raise _Stopped(stop if halt() else f"the {meter.report()['stopped_by']} spend is {stop}")
    return {"category": said.get("category", "failed"), "note": clip(said.get("note") or "", 1200)}


def _counts(answers: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, dict[str, int]]:
    out = {side: dict.fromkeys(COUNTS, 0) for side in ("before", "after")}
    for sides in answers.values():
        for side, said in sides.items():
            if said["grade"] in COUNTS:
                out[side][said["grade"]] += 1
    return out


def _result(request: Mapping[str, Any], answers: Mapping[str, Any], why: str, counts: Mapping[str, Any]) -> str:
    if why:
        return f"refused: {why}" if request["kind"] == "regression" else f"incomplete: {why}"
    if len(answers) != len(request["frozen"]) or any(len(s) != 2 for s in answers.values()):  # noqa: PLR2004
        return "refused: the comparison is incomplete" if request["kind"] == "regression" else "incomplete"
    before, after = counts["before"], counts["after"]
    if request["kind"] == "compare":
        return "compared"
    risen = [k.replace("_", " ") for k in COUNTS if after[k] > before[k]]
    return f"refused: {', '.join(risen)} rose" if risen else "passed"


# The queue: the owner's command asks, the machine host's job takes


def ask(request: Mapping[str, Any]) -> str:
    """Queue *request* for the machine host's job; its id."""
    folder = cases.ready() / "queue"
    folder.mkdir(exist_ok=True, mode=0o700)
    atomic_write(folder / f"{request['id']}.json", json.dumps(request, ensure_ascii=False))
    return request["id"]


def queued() -> list[dict[str, Any]]:
    """Every queued request, oldest first; an unreadable one is set aside, never run."""
    folder = cases.place() / "queue"
    out = []
    for path in sorted(folder.glob("r-*.json"), key=lambda p: p.stat().st_mtime) if folder.is_dir() else []:
        try:
            out.append(json.loads(path.read_text()))
        except OSError, ValueError:
            path.replace(path.with_suffix(".unreadable"))
    return out


def take(rid: str) -> bool:
    """Take request *rid* off the queue before it runs, so a crash never runs it again; whether it was there."""
    folder = cases.place() / "queue"
    try:
        (folder / f"{rid}.json").replace(folder / f"{rid}.taken")
    except FileNotFoundError:
        return False
    return True


def done(rid: str) -> None:
    """Forget the taken request *rid*: its result is kept with the runs."""
    (cases.place() / "queue" / f"{rid}.taken").unlink(missing_ok=True)


def interrupted() -> list[dict[str, Any]]:
    """Requests taken by a host that ended before their result was kept; each is recorded stopped, never rerun."""
    folder, out = cases.place() / "queue", []
    for path in sorted(folder.glob("r-*.taken")) if folder.is_dir() else []:
        try:
            request = json.loads(path.read_text())
        except OSError, ValueError:
            request = {"id": path.stem, "kind": "unknown"}
        if not any(r.get("id") == request["id"] and "result" in r for r in cases.lines("runs.jsonl")):
            with cases.locked():
                cases.append(
                    "runs.jsonl",
                    {
                        "id": request["id"],
                        "kind": request.get("kind"),
                        "by": request.get("by"),
                        "asked": request.get("at"),
                        "ended": cases.now(),
                        "result": "stopped: OwlBear ended while it ran; it is not rerun",
                    },
                )
        path.unlink(missing_ok=True)
        out.append(request)
    return out


def results() -> list[dict[str, Any]]:
    """Every run's result, oldest first."""
    return cases.lines("runs.jsonl")
