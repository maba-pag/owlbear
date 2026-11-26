"""The demo's Metrics scenario: spend ledger runs and their sessions' logs for the two example projects.

8 agents in the two example projects, 4 models, 5 steps and "No step", 14 days of 2 runs each, 7 tools covering every
outcome, and session logs: compactions with timing shares for 4 agents, a compacted session without a share, and an
agent whose sessions are readable but never compacted. Context at start is measured for every role but the updater,
in both projects, over the last 10 days only (older sessions ran before measuring began), with one failed read and a
reviewer whose skills stay in their category. Each line names its project by its registered name and its clone by
its fixed id, as the Metrics page links rows to the served projects.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.machine_host.demo_home import PROJECTS
from owlbear_delivery_next.state_store import spend_ledger

DAYS = 14
DAILY = 2  # runs a day: the runs list stays short enough for one capture of each state
AGENTS = (  # (agent, step, its sessions' logs: "compacts", "never" compacts, or None without a log)
    ("shaper", "shape", "compacts"), ("planner", "plan", "compacts"), ("builder", "build", "compacts"),
    ("reviewer", "review", "compacts"), ("challenger", "plan", "never"), ("preparer", "check", None),
    ("repairer", "build", None), ("updater", "", None),
)  # fmt: skip
MODELS = ("claude-opus-5.5", "gpt-6.1-sol", "claude-haiku-5.5", "gpt-6-luna")
TOOLS = {  # one run's tally per tool: together every outcome (accepted, invalid, checks, order, unsplit, lint, late)
    "submit_result": {"calls": 4, "rejected": 2, "invalid": 1, "checks": 1, "lint": 1, "retries": 1},
    "ask_question": {"calls": 2, "rejected": 1, "order": 1},
    "report_wrong_premise": {"calls": 2, "rejected": 1},
    "report_missing_tool": {"calls": 3, "rejected": 1, "invalid": 1, "late": 1},
    "lookup_decisions": {"calls": 5},
    "scan_design": {"calls": 3, "rejected": 1, "checks": 1, "lint": 1},
    "record_decision": {"calls": 2, "late": 1},
}
WINDOWS = {"claude-opus-5.5": 952_000, "gpt-6.1-sol": 400_000, "claude-haiku-5.5": 200_000, "gpt-6-luna": 272_000}
MEASURED = 10  # days back that context at start was measured: older sessions ran before this release
TIER = "default"  # a tier context_start.Start writes: "default" or "long"
UNKNOWN = 5  # the run whose usage could not be read: its credits are unknown
FAILED = 3  # days back that the preparer's context read failed
KEPT = "skills: 2100 tokens stay in their category, which nesting does not name"


def _event(kind: str, **data: object) -> str:
    return json.dumps({"type": kind, "data": data, "id": "e", "timestamp": "2026-11-01T09:00:00.000Z"}) + "\n"


def _log(session: str, calls: int, before: int | None) -> None:
    """A session's runtime log: *calls* model calls, one applied compaction after *before* of them (None: none)."""
    lines = [_event("assistant.turn_start")] * calls
    if before is not None:
        lines[before:before] = [
            _event("session.compaction_start", compactionAttemptId="a", trigger="threshold"),
            _event("session.compaction_complete", compactionAttemptId="a", success=True, outcome="applied"),
        ]
    path = chatlogs.state() / session / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines))


def _context(place: dict[str, Any], at: str, model: str, *, size: tuple[int, int], failed: bool) -> dict[str, Any]:
    """A run's context line (``spend_ledger.context``): seven parts that add up to its total, or a failed read."""
    (i, k), agent = size, place["agent"]
    line = place | {"id": f"context:{place['run']}", "type": "context", "at": at, "model": model, "tier": TIER}
    if failed:
        return line | {"measured": False, "error": "TimeoutError: the context attribution read took over 10 s"}
    parts = {"system_prompt": 7_000 + i * 300, "custom_instructions": 3_500 + i * 500, "skills": 2_000 * (i % 3),
             "subagents": 900 * (i % 2), "built_in_tools": 12_000 + i * 400, "mcp_tools": 4_000 + 1_500 * (i % 4),
             "messages": 3_000 + k * 370 % 5_000}  # fmt: skip
    return line | {"measured": True, "window": WINDOWS[model], "total": sum(parts.values()), "parts": parts,
                   "kept": KEPT if agent == "reviewer" else ""}  # fmt: skip


def seed() -> None:
    """The ledger's runs and their sessions' logs, written into the demo's home."""
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    lines: list[dict[str, Any]] = []
    unshared: list[str] = []
    k = 0
    for day in range(DAYS):
        for i, (agent, step, logs) in enumerate(AGENTS):
            if (day + i) % (every := len(AGENTS) // DAILY):
                continue
            k += 1
            rid, model = f"r{k}", MODELS[(day // 2 + i + i // every) % len(MODELS)]
            name, clone = PROJECTS[day // 2 % 2]
            at = (now - timedelta(days=day, minutes=i)).isoformat(timespec="seconds")
            spent = round(0.4 + (day * 7 + i * 3) % 11 * 0.37, 2)
            counts = {"credits": spent, "input": 900 * k, "output": 40 * k}
            usage = {"error": "TimeoutError"} if k == UNKNOWN else {"credits": spent, "models": {model: counts}}
            place = {"run": rid, "session": f"s-{rid}", "clone": clone, "project": name, "name": name,
                     "change": "" if agent == "updater" else f"change-{day % 3}", "step": step, "job": "",
                     "agent": agent}  # fmt: skip
            tools = {t: tally for j, (t, tally) in enumerate(TOOLS.items()) if (k + j) % 3}
            lines += [
                place | {"id": f"start:{rid}", "type": "start", "at": at, "model": model, "before": {}},
                place | {"id": f"end:{rid}", "type": "end", "at": at, "usage": usage, "ending": "result",
                         "limit": None, "stopped": "", "subagents": 0, "tools": tools,
                         "wrong": {"denied": 1} if k % 9 == 0 else {}},
            ]  # fmt: skip
            if logs:
                calls = 6 + k % 9
                if agent == "builder" and not unshared:  # compacted before any model call: no timing share
                    unshared.append(rid)
                    _log(f"s-{rid}", 0, 0)
                else:
                    _log(f"s-{rid}", calls, None if logs == "never" else 1 + k * 5 % calls)
            if agent != "updater" and day < MEASURED:
                lines.append(_context(place, at, model, size=(i, k), failed=agent == "preparer" and day == FAILED))
    if spend_ledger.append(lines):
        msg = "the demo's spend ledger could not be written"
        raise RuntimeError(msg)
