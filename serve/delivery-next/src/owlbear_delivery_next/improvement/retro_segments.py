"""What Retro's judge reads (#715, Improvement design §5): a unit's captured logs, prepared and bounded.

Judging is tool-less, so its evidence is prepared here. A segment is one requester turn of a chat, or one session of
a Change; its main-agent events become lines reduced as a Spotter card reduces them (failures and test results kept
fuller), each line prefixed with its reference ``s<segment>.e<event>`` (the event counted as the Spotter's intake
counts it). A segment is cut into parts at ``PART`` characters. After an event that names a saved output, a bounded
excerpt of the output follows when the capture kept it, else a marker saying why it is missing. Each part comes with
the unit's later course: what happened after it, reduced to outcome lines, ending with the unit's outcome. Every cut
leaves a marker of what it omitted; all text is masked. A finding's quote must appear in the prepared text it cites,
or it is dropped; a finding with no quote left, or resting on an omission or gap, is ``unknown``. The bounds and the
reduction are marked assumption ``retro-segments-1``.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from owlbear_delivery_next.improvement import events as ev
from owlbear_delivery_next.improvement import retro_units
from owlbear_delivery_next.local_system import mask
from owlbear_delivery_next.runtimes import chatlogs

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

PART, LATER, OUTPUT = 24_000, 6_000, 4_000  # characters: a part, its later course, one saved output's excerpt
SAID, ASKED, RESULT, FULL = 1_500, 6_000, 2_000, 6_000  # a message, a request, a result, a failure or test result
BRIEF, QUOTE, OUTCOME = 300, 600, 3_000  # an outcome line's text; a finding's quote; the unit's outcome
TESTS = re.compile(r"\b\d+ (?:passed|failed|errors?)\b|\bFAIL(?:ED)?\b|Traceback \(most recent call last\)")
REF = re.compile(r"\bs\d+\.e\d+\b")


def cut(text: str, n: int) -> str:
    """*text* within *n* characters, its start and end kept, the cut marked with what it omitted."""
    if len(text) <= n:
        return text
    left = n - 40
    marker = f" [… {len(text) - left} chars omitted] "
    return text[: left // 2] + marker + text[len(text) - left + left // 2 :]


def masked[T](value: T) -> T:
    """*value* with every string in it masked: what leaves the machine in a message."""
    if isinstance(value, str):
        return cast("T", mask.redact(value))
    if isinstance(value, dict):
        return cast("T", {k: masked(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return cast("T", [masked(v) for v in value])
    return value


@dataclass
class Part:
    """One bounded piece of a segment with its later course: what one judging batch carries."""

    ref: str  # ``s<segment>.p<part>``
    session: str
    first: int  # the first and last event it holds, counted as records' ``cutoff``
    last: int
    text: str = ""
    later: str = ""


@dataclass
class Prepared:
    """A unit revision's evidence: its parts, the earlier course as context, and what is missing."""

    parts: list[Part] = field(default_factory=list)
    earlier: str = ""
    gaps: list[str] = field(default_factory=list)


@dataclass
class _Line:
    n: int
    session: str
    segment: int
    text: str
    brief: str = ""  # its outcome line, when it says how things went


def _excerpt(session: str, path: str, said: Mapping[str, Any]) -> str:
    name = Path(path).name
    state = next((o.get("state") for o in said.get("outputs") or () if o.get("path") == path), "not captured")
    if state != "kept":
        return f"[output {name}: {state}]"
    try:
        with gzip.open(retro_units.folder(session) / "outputs" / f"{name}.gz", "rt", errors="replace") as fh:
            body = fh.read()  # the capture bounded every output it kept
    except (OSError, EOFError) as exc:
        return f"[output {name}: unreadable ({type(exc).__name__})]"
    return f"[output {name}]\n{cut(ev.clean(body), OUTPUT)}"


def _message(d: Mapping[str, Any], data: Mapping[str, Any]) -> tuple[str, str]:
    if d.get("type") == "user.message":
        text = ev.clean(str(data.get("content") or ""))
        who = "requester" if ev.requester(dict(d)) else "system message"
        return f"{who}: {cut(text, ASKED if who == 'requester' else SAID)}", f"{who}: {cut(text, BRIEF)}"
    text = ev.clean(str(data.get("content") or ""))
    return (f"agent: {cut(text, SAID)}", f"agent: {cut(text, BRIEF)}") if text.strip() else ("", "")


def _result(data: Mapping[str, Any], tool: str, said: Mapping[str, Any], session: str) -> tuple[str, str]:
    result = ev.clean(str(ev.result_text(dict(data))))
    failed, tests = data.get("success") is False, bool(TESTS.search(result))
    line = f"result {tool} {'failed' if failed else 'ok'}: {cut(result, FULL if failed or tests else RESULT)}"
    outputs = [_excerpt(session, p, said) for p in dict.fromkeys(chatlogs.SAVED.findall(result))]
    brief = f"{tool} {'failed' if failed else 'test result'}: {cut(result, BRIEF)}" if failed or tests else ""
    return "\n".join([line, *outputs]), brief


def _say(d: Mapping[str, Any], calls: dict[str, str], said: Mapping[str, Any], session: str) -> tuple[str, str]:
    """An event's line and its outcome line; "" for an event that says nothing."""
    kind, data = d.get("type"), d.get("data") or {}
    line, brief = "", ""
    if kind in {"user.message", "assistant.message"}:
        line, brief = _message(d, data)
    elif kind == "tool.execution_start":
        tool = str(data.get("toolName") or "")
        calls[str(data.get("toolCallId"))] = tool
        line = f"call {tool}: {cut(ev.clean(ev.kept_text(data.get('arguments'), ev.RAW)), SAID)}"
    elif kind == "tool.execution_complete":
        line, brief = _result(data, calls.get(str(data.get("toolCallId")), "?"), said, session)
    elif kind in {"subagent.started", "subagent.completed"}:
        line = f"{kind.split('.')[1]} subagent {data.get('agentName', '')}"
    elif kind == "skill.invoked":
        line = f"skill {data.get('name', '')}"
    elif kind in ev.STOPS:
        line = brief = "the session stopped"
    return line, brief


def _lines(sessions: Iterable[str], high: int, *, per_turn: bool, gaps: list[str]) -> list[_Line]:
    found: list[_Line] = []
    segment = 0
    for session in sessions:
        said, calls, n = retro_units.sidecar(session), {}, 0
        segment, fresh = segment + 1, True
        try:
            for d in retro_units.events(session):
                n += 1
                if high and n > high:
                    break
                if not ev.main_agent(d):
                    continue
                if per_turn and not fresh and d.get("type") == "user.message" and ev.requester(d):
                    segment, fresh = segment + 1, True  # a requester turn starts the next segment
                text, brief = _say(d, calls, said, session)
                if text:
                    found.append(_Line(n, session, segment, text, brief))
                    fresh = False
        except OSError as exc:
            gaps.append(f"session {session}'s capture cannot be read ({type(exc).__name__})")
    return found


def prepare(sessions: list[str], outcome: str, *, low: int = 0, high: int = 0, per_turn: bool = False) -> Prepared:
    """A unit revision's evidence: the events after *low* up to *high* (0: all) of its *sessions*, in parts.

    *per_turn* makes each requester turn a segment (a chat); else each session is one (a Change). Events up to *low*
    were judged before: they are the earlier course, context only.
    """
    out, outcome = Prepared(), cut(outcome, OUTCOME)
    lines = _lines(sessions, high, per_turn=per_turn, gaps=out.gaps)
    before = [x for x in lines if x.n <= low]
    lines = [x for x in lines if x.n > low]
    out.earlier = mask.redact(cut("\n".join(x.brief for x in before if x.brief), LATER))
    ends: list[int] = []  # each part's last line, by position: event numbers restart with each session
    for i, x in enumerate(lines):
        text = f"s{x.segment}.e{x.n} {x.text}"
        part = out.parts[-1] if out.parts else None
        if part is None or part.ref.split(".")[0] != f"s{x.segment}" or len(part.text) + len(text) + 1 > PART:
            index = sum(p.ref.startswith(f"s{x.segment}.") for p in out.parts) + 1
            part = Part(f"s{x.segment}.p{index}", x.session, x.n, x.n)
            out.parts.append(part)
            ends.append(i)
        part.text = f"{part.text}\n{text}" if part.text else text
        part.last, ends[-1] = x.n, i
    for part, end in zip(out.parts, ends, strict=True):
        after = "\n".join(y.brief for y in lines[end + 1 :] if y.brief)
        part.text = mask.redact(cut(part.text, PART))
        part.later = mask.redact(cut(after, LATER - len(outcome) - 20) + f"\noutcome: {outcome}")
    return out


def verify(finding: Mapping[str, Any], parts: Iterable[Part]) -> dict[str, Any]:
    """*finding* with only the quotes found in the prepared text its references cite.

    It is ``unknown`` when no quote is left or it rests on an omission or gap.
    """
    refs = set(finding.get("refs") or ())
    texts = [f"{p.text}\n{p.later}" for p in parts if refs.intersection(REF.findall(p.text))]
    quotes = [
        cut(q, QUOTE)
        for q in finding.get("quotes") or ()
        if isinstance(q, str) and q.strip() and any(q in t for t in texts)
    ]
    unknown = not quotes or bool(finding.get("rests_on_gap"))
    return {**finding, "quotes": quotes, "status": "unknown" if unknown else "known"}
