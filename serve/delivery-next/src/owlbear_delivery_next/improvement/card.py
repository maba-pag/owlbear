"""A Spotter look's card (design §4): what a look sees, built from a frozen intake snapshot; pure, redacted, bounded.

The card holds the intent (the step's task and the requester's later messages and answers; the latest one rules), the
agent's plan (its first message after the latest request, and its latest), the moment (the hand-off or the sampled
call), the recent actions, evidence (full outputs of failed calls, tests, waits and edits, the edit's change itself
included), timing (minutes since the request and the last edit, real waiting in the last 30 minutes), the open work and
the decisions in force that the step's worker has, and the gaps: what it cannot show. Every text is redacted
(credentials, emails, browser context) before anything leaves the machine; the whole card stays within ``BOUND``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from owlbear_delivery_next.improvement.events import clip
from owlbear_delivery_next.local_system.mask import redact

BOUND = 30000  # characters of the whole card
KEEP_RECENT, KEEP_DECISIONS, KEEP_TASK = 5, 1000, 500  # what ``bounded`` cuts down to, at least
EACH, EVIDENCE = 4000, 16000  # characters of one piece of evidence, and of all
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
BROWSER = re.compile(r"<browser_context>.*?</browser_context>", re.DOTALL)
TEST = re.compile(r"\b(pytest|npm (run )?test|vitest|jest|uv run test|go test|cargo test|node --test)\b")
WAITS = frozenset({"read_bash", "read_agent"})
WAIT = re.compile(r"\bsleep\s+\d|--watch\b|gh pr checks|gh run (watch|view)")
EDITS = frozenset({"edit", "create", "apply_patch", "str_replace_editor", "write"})
GAPS = ["the agent's instructions and loaded skills are not in its event stream",
        "the agent's full reasoning is encrypted; only its messages show"]  # fmt: skip


PROTECT = re.compile(r"(?:/(?:Users|private|var|tmp|Library|home)/[^\s\"'`:;,)\]}]+)|\b[0-9a-f]{40}\b")


def clean(text: str) -> str:
    """*text* without credentials, emails or browser context.

    File paths and commit ids are no secrets, so they are shielded from the long-value rule (as the pilot's cards were).
    """
    kept: list[str] = []

    def hold(m: re.Match[str]) -> str:
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    text = redact(PROTECT.sub(hold, BROWSER.sub("[browser context omitted]", text)))
    return EMAIL.sub("<email>", re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], text))


def _time(at: str) -> datetime | None:
    try:
        return datetime.fromisoformat(at)
    except ValueError:
        return None


def _minutes(since: str, now: datetime | None) -> int | None:
    then = _time(since)
    return round((now - then).total_seconds() / 60) if then and now else None


def _waited(actions: list[dict[str, Any]], now: datetime | None) -> int:
    """Minutes of the last 30 the agent's waits (delayed reads, sleeps, watch loops) covered, overlaps merged."""
    if now is None:
        return 0
    spans, start = [], now.timestamp() - 1800
    for a in actions:
        if a.get("tool") in WAITS or (a.get("tool") == "bash" and WAIT.search(a.get("args", ""))):
            lo, hi = _time(a.get("at", "")), _time(a.get("done_at", "")) or now
            if lo and hi.timestamp() > max(lo.timestamp(), start):
                spans.append((max(lo.timestamp(), start), hi.timestamp()))
    total, edge = 0.0, 0.0
    for lo, hi in sorted(spans):
        if hi > max(lo, edge):
            total, edge = total + hi - max(lo, edge), hi
    return round(total / 60)


def _brief(a: dict[str, Any]) -> dict[str, Any]:
    if "kind" in a:
        return {"at": a.get("at"), "kind": a["kind"]}
    out = {"at": a.get("at"), "tool": a.get("tool"), "args": clip(a.get("args", ""), 300)}
    if "result" in a:
        out |= {"ok": a.get("ok"), "result": clip(a["result"], 300)}
    else:
        out["result"] = "not completed at this moment"
    return out


def _evidence(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Newest first: failed calls, tests, waits and edits (with the change), each and all within their bounds."""
    out, used = [], 0
    for a in reversed(actions[-40:]):
        tool, args = a.get("tool", ""), a.get("args", "")
        why = ("failed" if a.get("ok") is False else "test" if TEST.search(args) else "edit" if tool in EDITS
               else "wait" if tool in WAITS or WAIT.search(args) else "")  # fmt: skip
        if not why:
            continue
        body = clip(args if why == "edit" else a.get("result", ""), EACH)
        if used + len(body) > EVIDENCE:
            break
        used += len(body)
        out.append({"at": a.get("at"), "why": why, "tool": tool, "args": clip(args, 400), "output": body})
    return out


def _plan(said: list[dict[str, Any]], requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last = requests[-1]["n"] if requests else 0
    first = next((s for s in said if s["n"] > last), None)
    plan = [{"role": "first reply to the latest request", **first}] if first else []
    if said and said[-1] is not first:
        plan.append({"role": "latest message", **said[-1]})
    return [{k: v for k, v in p.items() if k != "n"} for p in plan]


def build(snapshot: dict[str, Any], moment: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """The card for one look at *moment*; *context* holds what the runner knows: open work, decisions, the step."""
    actions, now = snapshot.get("actions", []), _time(str(moment.get("at") or ""))
    edits = [a for a in actions if a.get("tool") in EDITS]
    requests = snapshot.get("requests", [])
    card = {
        "step": context.get("step", ""),
        "intent": {
            "task": snapshot.get("task", ""),
            "later_requests": [r["text"] for r in requests[1:]],
            "answers": snapshot.get("answers", []),
        },
        "plan": _plan(snapshot.get("said", []), requests),
        "moment": moment,
        "recent": [_brief(a) for a in actions[-15:]],
        "evidence": _evidence(actions),
        "timing": {
            "now": moment.get("at"),
            "minutes_since_request": _minutes(requests[-1]["at"], now) if requests else None,
            "minutes_since_edit": _minutes(edits[-1]["at"], now) if edits else None,
            "minutes_waiting_in_last_30": _waited(actions, now),
        },
        "open_work": context.get("open_work", []),
        "decisions": clip("\n".join(context.get("decisions", [])), 6000),
        "gaps": [*GAPS, *([f"{snapshot['dropped']} earlier actions were dropped"] if snapshot.get("dropped") else [])],
    }
    return bounded(_cleaned(card))


def _cleaned(value: Any) -> Any:  # noqa: ANN401 - the card's JSON values
    """Every string of *value* cleaned, the structure kept."""
    if isinstance(value, str):
        return clean(value)
    if isinstance(value, list):
        return [_cleaned(v) for v in value]
    if isinstance(value, dict):
        return {k: _cleaned(v) for k, v in value.items()}
    return value


def bounded(card: dict[str, Any]) -> dict[str, Any]:
    """*card* within ``BOUND``: evidence goes first, then recent actions, then the decisions' text is cut."""
    while len(json.dumps(card, ensure_ascii=False)) > BOUND:
        if card["evidence"]:
            card["evidence"].pop()
        elif len(card["recent"]) > KEEP_RECENT:
            card["recent"].pop(0)
        elif len(card["decisions"]) > KEEP_DECISIONS:
            card["decisions"] = clip(card["decisions"], len(card["decisions"]) // 2)
        else:
            card["intent"]["task"] = clip(card["intent"]["task"], len(card["intent"]["task"]) // 2)
            if len(card["intent"]["task"]) < KEEP_TASK:
                break
    return card
