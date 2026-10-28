"""``owlbear cases`` and ``owlbear improvement``: the narrow local commands for the Spotter cases and Retro (§4, §5).

The Improvement page will call the same functions. A stage move that changes the active examples, a reserve
comparison and a check of candidates cost credits: the command only queues them, on the owner's word, for the machine
host's job, which runs them within their run credit limit (D-01M5XCE8ZEX5WPSCBZ5Y9S4K96). A Retro run is queued the
same way, for the host's Retro job; its plan view reads what a run would ask without asking.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import case_intake, case_replay, cases, pilot_seed, retro_evidence
from owlbear_delivery_next.improvement import retro_store as retro
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.cases import CaseError, Stale
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    import argparse

BY = "owner (command)"
QUEUED = "queued {}: the machine host runs it once OwlBear runs; `owlbear cases runs` shows its result"


def parsers(sub: Any) -> None:  # noqa: ANN401 - argparse's subparsers
    """Add ``cases`` and ``improvement`` to the command's parser."""
    c = sub.add_parser("cases", help="the Spotter cases: stages, versions, replays (Improvement design §4)")
    cs = c.add_subparsers(dest="action", required=True)
    cs.add_parser("list", help="the newest version's cases").add_argument("--version", type=int)
    s = cs.add_parser("seed", help="seed candidates: the pilot's moments, the synthetic cases, or both")
    s.add_argument("--pilot", type=Path, help="the pilot's folder (watcher-replay)")
    s.add_argument("--calls", type=Path, help="JSON: each should moment's finding category")
    s.add_argument("--synthetic", action="store_true", help="the synthetic cases (a marked assumption)")
    a = cs.add_parser("add", help="a candidate from a Spotter record")
    a.add_argument("record")
    a.add_argument("--call", required=True, choices=cases.CALLS)
    a.add_argument("--why", required=True)
    m = cs.add_parser("move", help="change a case's stage, call, why or example; examples changed: a paid regression")
    m.add_argument("case")
    m.add_argument("stage", choices=(*cases.STAGES, "removed"))
    m.add_argument("--call", default="", choices=("", *cases.CALLS))
    m.add_argument("--why", default="")
    m.add_argument("--example", default="", help="the minimised moment the prompt shows (an example)")
    m.add_argument("--reviewed-by", default="", help="who checked that the frozen card supports the call")
    m.add_argument("--note", default="")
    cs.add_parser("rollback", help="a new version copying an earlier one").add_argument("version", type=int)
    k = cs.add_parser("check", help="retro-review checks candidates' cards against their calls (paid)")
    k.add_argument("ids", nargs="*", help="cases to check; every candidate when none")
    cs.add_parser("release", help="freeze the reviewed corpus as a release (a marked assumption)")
    p = cs.add_parser("compare", help="two versions on a release's reserve, once per release (paid)")
    p.add_argument("a", type=int)
    p.add_argument("b", type=int)
    p.add_argument("--release", default="", help="the release; the newest by default")
    cs.add_parser("runs", help="every run's result").add_argument("--last", type=int, default=10)
    i = sub.add_parser("improvement", help="Improvement's marked assumptions and Retro")
    ia = i.add_subparsers(dest="action", required=True)
    ia.add_parser("reset", help="retire every marked assumption")
    rs = ia.add_parser("retro", help="Retro: judge a finished Change or chat (Improvement design §5)")
    rs = rs.add_subparsers(dest="retro", required=True)
    one = rs.add_parser("run", help="queue a run of one unit for the host's Retro job (paid)")
    which = one.add_mutually_exclusive_group(required=True)
    which.add_argument("--change", metavar="PROJECT/SLUG", help="a finished Change; PROJECT is its folder's name or id")
    which.add_argument("--chat", metavar="SESSION", help="an enrolled chat, quiet for a day")
    which.add_argument("--synthetic", nargs="?", const=True, metavar="NAME", help="the synthetic units, or one")
    st = rs.add_parser("status", help="the latest runs, or with --plan what a run of a unit would ask (not paid)")
    st.add_argument("--last", type=int, default=10)
    st.add_argument("--plan", metavar="UNIT", help="a unit id (chg:…, chat:…, syn:…) or PROJECT/SLUG")


def _say(text: str) -> None:
    sys.stdout.write(text + "\n")


def main(a: argparse.Namespace) -> int:
    """Run one ``cases`` or ``improvement`` command; 1 when it was refused."""
    try:
        if a.command == "improvement" and a.action == "retro":
            _retro(a)
        elif a.command == "improvement":
            retired, n = cases.reset()
            _say(f"retired: {', '.join(retired) or 'nothing'}" + (f"; cases version {n}" if n else ""))
        else:
            return _cases(a)
    except (CaseError, retro.RetroError, registry.RegistryError, StoreError) as exc:
        _say(f"refused: {exc}")
        return 1
    return 0


def _cases(a: argparse.Namespace) -> int:  # noqa: C901, PLR0912 - one branch per action
    if a.action == "list":
        _list(a.version)
    elif a.action == "seed":
        if not (a.pilot or a.synthetic) or bool(a.pilot) != bool(a.calls):
            msg = "give --pilot with --calls, --synthetic, or both"
            raise CaseError(msg)
        if a.pilot:
            _say(json.dumps(pilot_seed.seed(a.pilot, json.loads(a.calls.read_text()), BY)))
        if a.synthetic:
            _say(json.dumps(pilot_seed.synthetic(BY)))
    elif a.action == "add":
        _say(f"candidate {case_intake.from_record(a.record, a.call, a.why, BY)}")
    elif a.action == "move":
        return _move(a)
    elif a.action == "rollback":
        with cases.locked():  # the copy is made of the version it is written onto
            edits = cases.rollback_edits(a.version)
            return _change(edits, f"rollback to version {a.version}", cases.current()["n"])
    elif a.action == "check":
        _check(a.ids)
    elif a.action == "release":
        rid, new = case_replay.release(BY)
        _say(f"release {rid}" + ("" if new else " (the same corpus as before: no new release)"))
    elif a.action == "compare":
        rid = a.release or _newest_release()
        _say(QUEUED.format(case_replay.ask(case_replay.comparison(rid, a.a, a.b, BY))))
    elif a.action == "runs":
        for r in case_replay.results()[-a.last :]:
            _say(json.dumps({k: r.get(k) for k in ("id", "kind", "result", "applied", "counts", "credits") if k in r}))
    return 0


def _list(n: int | None) -> None:
    v = cases.current() if n is None else cases.version(n)
    _say(f"version {v['n']}")
    for cid, e in sorted(v["cases"].items()):
        f = cases.fact(cid)
        marks = [
            m
            for m, on in (
                ("reserve", f["reserve"]),
                ("synthetic", f["source"] == "synthetic"),
                ("unscored", f["unscored"]),
            )
            if on
        ]
        _say(f"{cid} {e['stage']:<9} {e.get('call') or '-':<22} {' '.join(marks)}")


def _move(a: argparse.Namespace) -> int:
    with cases.locked():  # the edit is made of the version it is written onto
        cur = cases.current()
        if a.case not in cur["cases"]:
            msg = f"case {a.case} is not in version {cur['n']}"
            raise CaseError(msg)
        if a.stage == "removed":
            return _change({a.case: None}, f"{a.case} removed", cur["n"])
        entry = cases.edited(
            a.case,
            cur["cases"][a.case],
            stage=a.stage,
            call=a.call,
            why=a.why,
            example=a.example,
            reviewed_by=a.reviewed_by,
            note=a.note,
        )
        return _change({a.case: entry}, f"{a.case} to {a.stage}", cur["n"])


def _change(edits: dict[str, Any], reason: str, parent: int) -> int:
    """Write *edits*, made of version *parent*, or queue their regression when they change the active examples.

    Raises:
        Stale: The newest version is no longer *parent*: nothing is written or queued.
    """
    with cases.locked():
        cur = cases.current()
        if cur["n"] != parent:
            msg = f"the Spotter cases are at version {cur['n']} now, not {parent}: look again and retry"
            raise Stale(msg)
        after = cases.applied(cur["cases"], edits)
        if cases.shown(after) == cases.shown(cur["cases"]):
            _say(f"version {cases.commit(cur['n'], edits, BY, reason)}")
            return 0
        request = case_replay.regression(edits, BY, reason)
    _say(QUEUED.format(case_replay.ask(request)))
    return 0


def _check(ids: list[str]) -> None:
    cur = cases.current()["cases"]
    chosen = ids or [cid for cid, e in sorted(cur.items()) if e["stage"] == "candidate" and e.get("call")]
    if bad := [cid for cid in chosen if cur.get(cid, {}).get("stage") != "candidate" or not cur[cid].get("call")]:
        msg = f"only candidates with a call are checked: {', '.join(bad)}"
        raise CaseError(msg)
    if not chosen:
        msg = "no candidate to check"
        raise CaseError(msg)
    request = {
        "id": f"r-{cases.digest([chosen, cases.now()])[:10]}",
        "kind": "check",
        "at": cases.now(),
        "by": BY,
        "ids": {cid: cases.content(cid, cur[cid]) for cid in chosen},
    }
    _say(QUEUED.format(case_replay.ask(request)))


def _newest_release() -> str:
    found = cases.lines("releases.jsonl")
    if not found:
        msg = "no release yet: `owlbear cases release` freezes one"
        raise CaseError(msg)
    return found[-1]["id"]


def _retro(a: argparse.Namespace) -> None:
    if a.retro == "run":
        change = None
        if a.change:
            pid, _ = _project(_slash(a.change)[0])
            change = f"{pid}:{_slash(a.change)[1]}"
        if a.synthetic:  # one request per unit: a host that stops loses none still queued
            named = a.synthetic if isinstance(a.synthetic, str) else ""
            rids = [retro.request(BY, synthetic=s["name"]) for s in syn.specs(named)]
        else:
            rids = [retro.request(BY, change, a.chat)]
        said = "the machine host's Retro job runs it; `owlbear improvement retro status` shows its result"
        _say(f"queued {', '.join(rids)}: {said}")
    elif a.plan:
        uid, projects = _unit(a.plan)
        _say(json.dumps(retro_evidence.plan(uid, projects)))
    else:
        _say(f"queued: {len(retro.queued())}")
        keep = ("id", "unit", "trigger", "by", "state", "why", "result", "spent", "known", "calls")
        for r in retro.runs(a.last, synthetic=True)[::-1]:
            _say(json.dumps({k: r[k] for k in keep if k in r}))


def _slash(text: str) -> tuple[str, str]:
    name, _, slug = text.partition("/")
    if not name or not slug:
        msg = f"{text!r} is not PROJECT/SLUG"
        raise CaseError(msg)
    return name, slug


def _project(name: str) -> tuple[str, Path]:
    """The id and folder of the registered project *name* names, by its folder's name or its id."""
    for p in registry.load().projects:
        if name in {p.id, Path(p.path).name}:
            return p.id, Path(p.path)
    msg = f"no registered project is named {name!r}"
    raise CaseError(msg)


def _unit(text: str) -> tuple[str, units.Projects]:
    """The unit *text* names (a unit id or ``PROJECT/SLUG``), with the project its Change is in."""
    if text.startswith(("chat:", "syn:")):
        return text, {}
    name, _, slug = text.removeprefix("chg:").partition(":")
    if not text.startswith("chg:"):
        name, slug = _slash(text)
    elif not name or not slug:
        msg = f"{text!r} is not chg:PROJECT:SLUG"
        raise CaseError(msg)
    pid, path = _project(name)  # a folder's name is resolved to its project's id
    return units.change_id(pid, slug), {pid: (Store.open(path), path)}
