"""Each run's own share of its session's cumulative usage, split exclusively by agent and model (spend metrics).

The ledger's lines (``spend_ledger``) become runs: a live ``start`` and ``end`` pair by ``run``, or one line
``spend_reconcile`` imported: an ``event`` (a step's usage at a known time), a ``mark`` (a session's latest totals
a Change kept, time unknown), a ``residual`` (a Change's spend no session holds) or a ``look`` (a Spotter look before
the ledger). Every run names the ``session`` whose totals it reports; the totals only grow. A look the ledger has
from its own lines and from its Spotter record (one ``look`` id, its meter's) counts once: as its own lines, plus,
when the record names an SDK session those lines lack (``sdk_sessions``), what the record holds beyond them. An
imported checkpoint that repeats a live run's totals exactly adds nothing. A run with several ends (its runtime log's
corrections) keeps its largest usage, a final one over a provisional one of as much, and its recorded ending's time;
a run whose ending is itself a log checkpoint dates each later checkpoint's growth between the two checkpoints. Each
piece of a Spotter look's run names its ``look``, so a look's retries, each its own run, group under it.

Shares are derived per session before anything is filtered or grouped, so a filter never hands a resumed run the
spend of earlier ones. The runs go in time order (unknown times last, as imported). High-water marks start at zero
at three levels, each deciding only what the one above leaves open: the session's totals per field (credits and
each token count) decide how much a run spent; each model's totals decide which models that went to; each cell's
(agent instance and model) decide which agent within a model. A level that does not add up, as when an unsplit
legacy total is later split between agents, leaves the rest ``unallocated`` (agent or model unknown), never an
invented proportional split. For each run:

1. Its ``before``, when known, is its session's totals when it started: what exceeds the marks was spent between
   the last run reported and this one. It goes to the latest earlier run whose usage is unknown (``recovered``, in
   that run's agent and time window, which is then no longer unknown), else stands as a ``gap``, its agent known and
   its time not.
2. Its usage, when read: what exceeds the marks is its own share (``run``). A run whose ``before`` was unread takes
   all growth since the last report, in the window from that report to its end. Unread: one ``unknown`` piece, its
   credits None; a ``start`` alone is ``open``. An invocation that spent nothing still keeps one piece, of zero
   credits (or None when its credits were not reported), so it counts as a run with its ending and its stop.
3. The marks rise to its usage.

A run whose final usage read failed records its earlier sample, and a read that may be short (``LOWER_BOUNDS``) is
marked too: both ``incomplete``, a lower bound until reconciled, and only the first ``failed``. A run with subagents
but no split leaves its pieces' agent unknown, under its role. A piece's time is the window ``[lo, hi]`` it certainly
lies in: one instant for a run, the run's end; wider or open-ended when uncertain, never a made-up day.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

FIELDS = ("credits", "input", "output", "cache_read", "cache_write")
# what producers mark on a read that worked but may be short; any other mark names a failed read
LOWER_BOUNDS = frozenset({"turn running", "tasks unsettled", "lower final read", "interrupted", "checkpoint",
                          "unconfirmed"})  # fmt: skip
EPS = 1e-9
LIVE = ("start", "end")
LOG = "import:runtime-log"  # a line the runtime's log gave
CHECKPOINTS = ("event", "mark", "residual")  # imported line types that repeat a session's totals: never a run
VOID = "void"  # a Spotter record's ``look`` line imported although no look ran (``spend_reconcile``): no run at all
OWNER = "owner"  # a recovered Spotter look session's owner, known after it was recovered (``spend_logs``)
PLACE = ("project", "name", "clone", "change", "step", "job")
RECOVERED = ("id", "type", "at", "session", "usage", "source")  # what a recovered line adds to a run its own lines name
CONTINUED = ("usage", "at", "started", "before", "continued", "source", "settled")  # a continuation's own

type Fields = dict[str, float | None]
type Cell = tuple[str, str]
type Marks = dict[str, float]


def _fields(m: dict[str, Any]) -> Fields:
    c = m.get("credits")
    return {"credits": None if c is None else float(c)} | {f: float(m.get(f) or 0) for f in FIELDS[1:]}


def _reported(usage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Each model's totals as reported; older step events list only their models' names (D-01M63C6PMQD4TXK6HN5YANP5DN).

    A one-name list counts the usage's credits as that model's; any other list reports no model, so its total
    credits stand alone.
    """
    found = usage.get("models") or {}
    if isinstance(found, list):
        return {found[0]: {"credits": usage.get("credits")}} if len(found) == 1 else {}
    return found


def cells(usage: dict[str, Any], model: str) -> dict[Cell, tuple[str, Fields]]:
    """A cumulative usage as cells: (agent instance, model) to (subagent name, "" for the main agent; fields)."""
    out: dict[Cell, tuple[str, Fields]] = {}
    if agents := usage.get("agents"):
        for key, a in agents.items():
            name = "" if key == "main" else (a.get("agent") or "subagent")
            for m, mm in (a.get("models") or {}).items():
                out[key, m] = (name, _fields(mm))
    else:
        for m, mm in _reported(usage).items():
            out["main", m] = ("", _fields(mm))
    if not out and (total := usage.get("credits")) is not None:
        return {("main", model): ("", _fields({"credits": total}))}
    return out


def models(usage: dict[str, Any], split: dict[Cell, tuple[str, Fields]]) -> dict[str, Fields]:
    """Each model's cumulative totals: as the runtime reported them per model, else the sum of its cells."""
    if reported := _reported(usage):
        return {m: _fields(mm) for m, mm in reported.items()}
    out: dict[str, Fields] = {}
    for (_, m), (_, v) in split.items():
        was = out.setdefault(m, dict.fromkeys(FIELDS, 0.0))
        for f in FIELDS:
            was[f] = None if was[f] is None or v[f] is None else was[f] + v[f]  # type: ignore[operator]
    return out


def totals(usage: dict[str, Any], per: dict[str, Fields]) -> Fields:
    """The session's own cumulative totals: its reported credits (else its models' when all are known) and tokens."""
    known = [v["credits"] for v in per.values()]
    spent = usage.get("credits")
    if spent is None and per and None not in known:
        spent = sum(known)  # type: ignore[arg-type]
    out: Fields = {"credits": None if spent is None else float(spent)}
    return out | {f: sum(v[f] or 0.0 for v in per.values()) for f in FIELDS[1:]}


def _print(usage: dict[str, Any] | None) -> str | None:
    """A cumulative usage's totals, to tell an exact repeat; None for an unread one."""
    if not usage or "error" in usage:
        return None
    split = cells(usage, "")
    per = models(usage, split)
    return repr((totals(usage, per), sorted(per.items())))


def runs(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ledger's lines as runs, in the order their first line came; a run's later log checkpoints after them.

    A run's ``end`` from the runtime's log (``import:runtime-log``) corrects its usage, never lowering it. A run ended
    as it ran keeps its own time. A run whose ending is itself a log checkpoint (a killed run, a session only the log
    names) takes each later, larger checkpoint as a continuation: one more entry of the same run, at that checkpoint's
    time, whose growth lies between the two checkpoints; an ending recorded as it ran, arriving after them, dates the
    run alone. Once the run's latest usage is final, none of its entries is a lower bound any more (``settled``).
    A ``void`` line takes back a Spotter record's run (``import:spotter``) imported although no look ran; never another.

    A Spotter look's session recovered from its runtime's log (``log:<session>``, carrying its ``look``) and its own
    lines, when they come after all, are one run: the recovered lines join the run its own lines name and add their
    usage and time only, so the run's id and the place its own lines record stand for every entry of it, its
    continuations included, whichever came first; the agent the recovery named stands only where they name none, as an
    end alone does. Until they come, an ``owner`` line gives the recovered run its owner's place, known after it was
    recovered.
    """
    alias = _surrogates(lines)
    by: dict[str, dict[str, Any]] = {}
    later: dict[str, list[dict[str, Any]]] = {}  # each run's continuations, in time order
    void: set[str] = set()
    owned: dict[str, dict[str, Any]] = {}
    for line in lines:
        kind = line.get("type")
        if kind in {VOID, OWNER}:
            _aside(line, void, owned)
            continue
        rid = str(line.get("run") or line.get("id")) if kind in LIVE else str(line.get("id"))
        if rid in alias:  # a recovered line of a run whose own lines came: its usage only, never its place
            rid, joined = alias[rid], {"run": alias[rid], "recovered_agent": line.get("agent")}  # its agent: a fallback
            line = {k: line[k] for k in RECOVERED if k in line} | joined  # noqa: PLW2901
        run = by.setdefault(rid, {"run": rid, "usage": None, "at": None, "started": None, "before": None})
        if kind == "start":
            run |= {k: v for k, v in line.items() if k not in {"id", "type", "at"}} | {"started": line.get("at")}
            run.setdefault("source", "recorded")
        elif line.get("source") == LOG and run.get("checkpointed") and line.get("at"):
            _continue(run, line, later.setdefault(rid, []))
        else:
            if line.get("source") != LOG and (kept := later.pop(rid, None)):  # its own ending came after all
                run["usage"] = kept[-1]["usage"]  # it alone dates the run
            _end(run, line)
    _joined(by, later, owned, alias)
    return _settled(by, later, void)


def _joined(
    by: dict[str, dict[str, Any]],
    later: dict[str, list[dict[str, Any]]],
    owned: dict[str, dict[str, Any]],
    alias: dict[str, str],
) -> None:
    """Place recovered runs: by their owner until their own lines join them; then every entry as those lines say."""
    for rid, fields in owned.items():
        if rid in by:  # a recovered run its own lines never joined: they, once in, say where it ran
            for entry in (by[rid], *later.get(rid, ())):
                entry.update(fields)
    for rid in alias.values():  # the agent the manifest named, when its own lines name none (an end names none)
        by[rid]["agent"] = by[rid].get("agent") or by[rid].get("recovered_agent") or ""
    for rid in set(alias.values()) & later.keys():  # its own lines' run, id and place, whenever they came
        for entry in later[rid]:
            entry.update({k: v for k, v in by[rid].items() if k not in CONTINUED})


def _surrogates(lines: list[dict[str, Any]]) -> dict[str, str]:
    """Each recovered Spotter look session's run (``log:<session>``) to the run its own lines name, once they came."""
    recovered: set[str] = set()
    live: dict[str, str] = {}
    for line in lines:
        if line.get("type") not in LIVE or not line.get("look"):
            continue
        session = str(line.get("session") or "")
        if line.get("source") != LOG:
            live.setdefault(session, str(line.get("run") or line.get("id")))
        elif line.get("run") == f"log:{session}":
            recovered.add(session)
    return {f"log:{s}": live[s] for s in recovered if s in live}


def _aside(line: dict[str, Any], void: set[str], owned: dict[str, dict[str, Any]]) -> None:
    """A line that changes another run: a ``void`` takes it back, an ``owner`` places it."""
    if line.get("type") == VOID:
        void.add(str(line.get("run")))
    else:
        owned[str(line.get("run"))] = {k: line.get(k) or "" for k in PLACE}


def _settled(
    by: dict[str, dict[str, Any]], later: dict[str, list[dict[str, Any]]], void: set[str]
) -> list[dict[str, Any]]:
    """The runs and their continuations; a run whose latest usage is final settled, and a voided record dropped."""
    for rid, kept in later.items():
        if kept and not (kept[-1].get("usage") or {}).get("incomplete"):
            for entry in (by[rid], *kept):
                entry["settled"] = True
    for rid in void:
        if by.get(rid, {}).get("source") == "import:spotter":
            del by[rid]
    return [*by.values(), *(x for kept in later.values() for x in kept)]


def _continue(run: dict[str, Any], line: dict[str, Any], kept: list[dict[str, Any]]) -> None:
    """A later, larger log checkpoint of *run*, whose ending is a checkpoint itself: one more entry at its time."""
    last = kept[-1] if kept else run
    if _larger(last.get("usage"), line.get("usage")) and line["at"] >= (last.get("at") or ""):
        kept.append(run | {"usage": line["usage"], "at": line["at"], "started": None, "before": None,
                           "continued": True, "source": LOG})  # fmt: skip


def _end(run: dict[str, Any], line: dict[str, Any]) -> None:
    """Another ending line of *run*: its time unless a log correction of an ending recorded as it ran."""
    kind, logged = line.get("type"), line.get("source") == LOG
    skip = {"id", "type", "at"} if logged and run.get("ended") and not run.get("checkpointed") else {"id", "type"}
    keep = {k: v for k, v in line.items() if k not in skip and (v not in ("", None) or k not in run)}
    if "usage" in keep and not _larger(run.get("usage"), keep["usage"]):
        del keep["usage"]  # a correction never lowers what a run is known to have spent
    if kind == "end" and not (logged and run.get("ended")):
        run["checkpointed"] = logged  # its ending is a log checkpoint, not one recorded as it ran
    run |= keep | {"ended": True, "line": kind}
    run.setdefault("source", "recorded" if kind == "end" else f"import:{kind}")


def unread(usage: dict[str, Any]) -> bool:
    """Whether a usage says nothing of the credits spent: unread, or read without them."""
    return "error" in usage or usage.get("credits") is None


def _larger(old: dict[str, Any] | None, new: dict[str, Any] | None) -> bool:
    """Whether another end's *new* usage replaces a run's *old*: known over unread, else at least as many credits."""
    if new is None:
        return False
    if old is None or unread(old):
        return True
    if unread(new) or (more := float(new["credits"]) - float(old["credits"])) < -EPS:
        return False
    return more > EPS or not new.get("incomplete") or bool(old.get("incomplete"))  # a tie: final over provisional


def _time(run: dict[str, Any]) -> str | None:
    return run.get("at") or run.get("started")


def _base(run: dict[str, Any]) -> dict[str, Any]:
    keys = ("run", "session", "project", "name", "clone", "change", "step", "job", "ending", "stopped", "stopped_by",
            "limit", "source", "look")  # fmt: skip
    why = (run.get("usage") or {}).get("incomplete")
    incomplete = bool(why) and not run.get("settled")  # a lower bound
    return {k: run.get(k) or ("" if k != "limit" else None) for k in keys} | {
        "role": run.get("agent") or "",
        "incomplete": incomplete,
        "failed": incomplete and str(why) not in LOWER_BOUNDS,
    }


def _piece(  # noqa: PLR0913, PLR0917 - the run and each part of its piece
    run: dict[str, Any], kind: str, name: str, model: str, share: dict[str, float | None],
           window: tuple[str | None, str | None], uncertain: list[str]) -> dict[str, Any]:  # fmt: skip
    role = run.get("agent") or ""
    if name == "" and run.get("subagents") and not (run.get("usage") or {}).get("agents"):
        name = "?"  # its subagents' share is not split from its own: the agent is unknown, under its role
    agent, under = (role, "") if name == "" else ("", role) if name == "?" else (name, role)
    if name == "?":
        uncertain = [*uncertain, "agent"]
    if not agent and "agent" not in uncertain:
        uncertain = [*uncertain, "agent"]
    return _base(run) | share | {"kind": kind, "agent": agent, "under": under, "model": model, "lo": window[0],
                                 "hi": window[1], "uncertain": sorted(set(uncertain))}  # fmt: skip


class _Marks:
    """A session's high-water marks: its totals, each model's and each cell's, per field."""

    def __init__(self) -> None:
        self.session: Marks = {}
        self.models: dict[str, Marks] = {}
        self.cells: dict[Cell, Marks] = {}

    def grow(self, usage: dict[str, Any], model: str) -> tuple[dict[Cell, tuple[str, Fields]], bool]:
        """What *usage* adds, by cell (agent instance and model; "?" unknown), and whether its credits are known.

        Each level splits only what the one above decided; one that does not add up leaves its rest unknown. The
        marks rise to *usage*.
        """
        split = cells(usage, model)
        per = models(usage, split)
        whole = totals(usage, per)
        out: dict[Cell, tuple[str, Fields]] = {}

        def add(cell: Cell, name: str, f: str, value: float | None) -> None:
            out.setdefault(cell, (name, dict.fromkeys(FIELDS, 0.0)))[1][f] = value

        for f in FIELDS:
            if (now := whole[f]) is None:
                for cell, (name, _) in split.items():
                    add(cell, name, f, None)
                continue
            own = max(0.0, now - self.session.get(f, 0.0))
            by_model = {m: _over(v[f], self.models.get(m, {}).get(f)) for m, v in per.items()}
            seen = sum(g for g in by_model.values() if g is not None)
            if seen > own + _slack(own):  # the models re-split earlier spend: which model is unknown
                add(("?", ""), "?", f, own)
                continue
            if own - seen > _slack(own):
                add(("?", ""), "?", f, own - seen)
            for m, g in by_model.items():
                if g is not None and g > EPS:
                    self._agents(split, m, f, g, add)
        self._rise(whole, per, split)
        return out, whole["credits"] is not None

    def _agents(
        self, split: dict[Cell, tuple[str, Fields]], m: str, f: str, grew: float, add: Callable[..., None]
    ) -> None:
        """Model *m*'s growth *grew* in field *f*, by agent when its cells add up to it, else to an unknown agent."""
        mine = {c: _over(v[f], self.cells.get(c, {}).get(f)) for c, (_, v) in split.items() if c[1] == m}
        found = [x for x in mine.values() if x is not None]
        if len(found) == len(mine) and abs(sum(found) - grew) <= _slack(grew):
            for c, x in mine.items():
                add(c, split[c][0], f, x)
        else:  # its agents re-split earlier spend, or one's is unknown
            add(("?", m), "?", f, grew)

    def _rise(self, whole: Fields, per: dict[str, Fields], split: dict[Cell, tuple[str, Fields]]) -> None:
        for marks, now in ((self.session, whole), *((self.models.setdefault(m, {}), v) for m, v in per.items()),
                           *((self.cells.setdefault(c, {}), v) for c, (_, v) in split.items())):  # fmt: skip
            for f in FIELDS:
                if (value := now[f]) is not None:
                    marks[f] = max(marks.get(f, 0.0), value)


def _over(now: float | None, mark: float | None) -> float | None:
    return None if now is None else max(0.0, now - (mark or 0.0))


def _slack(amount: float) -> float:
    return max(EPS, abs(amount) * 1e-9)


def _spent(share: Fields) -> bool:
    """Whether a share holds spend: credits or tokens, or tokens whose credits are unknown."""
    tokens = any((share.get(f) or 0.0) > EPS for f in FIELDS[1:])
    return (share.get("credits") or 0.0) > EPS or tokens


def _pieces(
    owner: dict[str, Any],
    kind: str,
    grown: dict[Cell, tuple[str, Fields]],
    window: tuple[str | None, str | None],
    uncertain: list[str],
) -> list[dict[str, Any]]:
    """One piece per cell that grew, in *owner*'s run."""
    return [_piece(owner, kind, name, cell[1], share, window, uncertain)
            for cell, (name, share) in grown.items() if _spent(share)]  # fmt: skip


def _invocation(run: dict[str, Any]) -> bool:
    """A run that was itself a session's work, as against a checkpoint imported from another record."""
    return run.get("started") is not None or run.get("line") not in CHECKPOINTS


def derive(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every piece of spend the ledger holds: exclusive, additive, each in one run, agent and model."""
    found = runs(lines)
    live: dict[str, set[str]] = {}  # each look's sessions its own lines record
    for r in found:
        if r.get("look") and r.get("source") != "import:spotter":
            live.setdefault(str(r["look"]), set()).add(str(r.get("session") or ""))
    sessions: dict[str, list[dict[str, Any]]] = {}
    records: list[dict[str, Any]] = []  # Spotter records of looks whose own lines the ledger also has
    for n, run in enumerate(found):
        run["n"] = n
        if run.get("source") == "import:spotter" and str(run.get("look") or "") in live:
            records.append(run)
            continue
        sessions.setdefault(str(run.get("session") or run["run"]), []).append(run)
    pieces: list[dict[str, Any]] = []
    for group in sessions.values():
        prints = {_print(r.get("usage")) for r in group if _invocation(r)} - {None}
        group = [r for r in group if _invocation(r) or _print(r.get("usage")) not in prints]  # noqa: PLW2901
        group.sort(key=lambda r: (_time(r) is None, _time(r) or "", r["n"]))
        pieces += _session(group)
    return pieces + [p for r in records for p in _beyond(r, live[str(r["look"])], pieces)]


def _beyond(record: dict[str, Any], sessions: set[str], pieces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What a look's Spotter record holds beyond its own lines: only when it names a session they lack."""
    if set(record.get("sdk_sessions") or ()) <= sessions:
        return []
    own = sum(p["credits"] or 0.0 for p in pieces if p["session"] in sessions)
    spent = (record.get("usage") or {}).get("credits")
    when = (record.get("at"), record.get("at"))
    if spent is None:  # unknown: so is what the session its lines lack spent
        unknown: Fields = {"credits": None} | dict.fromkeys(FIELDS[1:], 0.0)
        return [_piece(record, "unknown", "", record.get("model") or "", unknown, when, [])]
    if (rest := float(spent) - own) <= EPS:
        return []
    share: Fields = {"credits": rest} | dict.fromkeys(FIELDS[1:], 0.0)
    return [_piece(record, "run", "", record.get("model") or "", share, when, [])]


def _session(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marks = _Marks()
    out: list[dict[str, Any]] = []
    lost: dict[str, Any] | None = None  # the latest run whose usage is unknown: later growth may be its own
    placeholder: dict[str, Any] = {}  # its unknown piece, dropped once its spend is recovered
    last: str | None = None  # the latest known time in this session: its last report
    credited: list[dict[str, Any]] = []  # the pieces of the latest run that spent
    for run in group:
        model = run.get("model") or ""
        if (before := run.get("before")) is not None and "error" not in before:
            grown, _ = marks.grow(before, model)
            if lost is not None:
                found = _pieces(lost, "recovered", grown, (lost.get("started") or last, run.get("started")),
                                ["at"])  # fmt: skip
                if found and placeholder in out:  # what it spent is known now: no longer unknown
                    out.remove(placeholder)
            else:
                found = _pieces(run, "gap", grown, (last, run.get("started")), ["at"])
            out += found
        usage = run.get("usage")
        if usage is None or "error" in usage:
            kind = "open" if usage is None else "unknown"
            window = (run.get("at"), run.get("at")) if run.get("at") else (run.get("started"), None)
            placeholder = _piece(run, kind, "", model, {f: None if f == "credits" else 0.0 for f in FIELDS}, window, [])
            out.append(placeholder)
            lost = run
            last = _time(run) or last
            continue
        timed = bool(run.get("at"))
        exact = timed and not run.get("continued") and (before is not None or run.get("source") != "recorded")
        window = (run["at"], run["at"]) if exact else (last, run.get("at"))  # unread baseline: since the last report
        grown, known = marks.grow(usage, model)
        found = _pieces(run, "run", grown, window, [] if exact else ["at"])
        own = _invocation(run) and not run.get("continued")  # a run with a piece of its own, holding its read
        if not found and (bound := _base(run))["incomplete"]:
            for piece in credited:  # a lower bound repeating what they credited: they are lower bounds too
                piece["incomplete"] = True
                piece["failed"] = piece["failed"] or (bound["failed"] and not own)
        if not found and own:
            # nothing spent, or nothing known: still a run, with its ending and stop
            zero = {f: (0.0 if known else None) if f == "credits" else 0.0 for f in FIELDS}
            found = [_piece(run, "run" if known else "unknown", "", model, zero, window, [] if exact else ["at"])]
        credited = [p for p in found if (p["credits"] or 0.0) > EPS] or credited
        out += found
        lost = None
        last = run.get("at") or last
    return out
