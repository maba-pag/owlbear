"""A design pack update's invocations: each run of a stage kept in order, by phase, with what runs now and next.

A stage that runs again starts a new invocation; it never overwrites an earlier one. An invocation another one has
superseded is stale: a re-run of the same operation in its phase supersedes that earlier run and everything after it
there, and a candidate that changed in the rounds supersedes the evidence about the one before it. A record from
before invocations has none: it shows its stages alone, with no history made up for it.
"""

from __future__ import annotations

from typing import Any

from owlbear_delivery_next.pack_runs.pack_state import STAGES
from owlbear_delivery_next.state_store.pack_run_record import now

PREPARE, CHALLENGE, PUBLISH = "prepare", "challenge", "publish"
OWNER = "owner"  # the owner's answer to a stop: a gate, not a stage
OPERATIONS = {
    "notice": "Notice: newer upstream release",
    "candidate": "Candidate: detector pins and skills",
    "diff": "Diff: rules and skill files",
    "initial-golden": "Golden pages with the package's expectations (the updater's evidence)",
    "update": "Updater session",
    "candidate-golden": "Golden pages on the candidate",
    "replay": "Calibration replay",
    "full-challenge": "Challenger on the whole pack",
    "rejection-recheck": "Challenger rechecks the updater's rejections",
    "reconsideration": "Challenger reconsiders with your notes",
    OWNER: "Your answer",
    "unchanged-check": "Check the package's files are as the update found them",
    "commit": "Commit on the pack branch",
    "push": "Push the branch",
    "pull-request": "Pull request to main",
    "merge": "CI and merge",
}
PREPARED = frozenset({"notice", "candidate", "diff", "initial-golden"})
PUBLISHED = frozenset({"unchanged-check", "commit", "push", "pull-request", "merge"})
SESSIONS = frozenset({"update", "full-challenge", "rejection-recheck", "reconsideration"})
JUDGED = frozenset({"candidate-golden", "replay", "full-challenge", "rejection-recheck"})  # a pass is the candidate's
ACTIONS = {  # the controller's next action (pack_run.Action) as the operation it starts
    "update": "update", "replay": "replay", "challenge": "full-challenge", "recheck": "rejection-recheck",
    "reconsider": "reconsideration", "wait": OWNER, "activate": "unchanged-check",
}  # fmt: skip
FOLLOWS = {  # what the run does after each operation whatever it found; absent: a verdict or the owner decides
    "notice": "candidate", "candidate": "diff", "diff": "initial-golden", "initial-golden": "update",
    "update": "candidate-golden", "unchanged-check": "commit", "commit": "push", "push": "pull-request",
    "pull-request": "merge",
}  # fmt: skip
OPEN = frozenset({"running", "waiting"})


def phase(op: str) -> str:
    """The phase an operation belongs to; the owner's gates take the phase of the stop they answer."""
    return PREPARE if op in PREPARED else PUBLISH if op in PUBLISHED else CHALLENGE


def key(inv: dict[str, Any]) -> str:
    """The phase an invocation is grouped under: prepare, round-<n> or publish."""
    return f"round-{inv['round']}" if inv["phase"] == CHALLENGE else inv["phase"]


def title(inv: dict[str, Any]) -> str:
    """The phase's words: Prepare, Challenge round n or Publish."""
    return f"Challenge round {inv['round']}" if inv["phase"] == CHALLENGE else inv["phase"].capitalize()


def opened(  # noqa: PLR0913 - the record's invocations, the stage slot and what this invocation is
    invocations: list[dict[str, Any]],
    stage: str,
    op: str,
    *,
    at: str = "",
    round_: int | None = None,
    identity: str = "",
    result: str = "running",
) -> dict[str, Any]:
    """A new invocation of *op*, appended in order; a re-run supersedes the earlier run and what followed it.

    *at* overrides the phase (an owner's gate); a challenge round not given is the last one's, else the first.
    """
    at = at or phase(op)
    if at == CHALLENGE and round_ is None:
        round_ = next((i["round"] for i in reversed(invocations) if i["phase"] == CHALLENGE), 1)
    inv = {
        "n": len(invocations) + 1, "phase": at, "round": round_ if at == CHALLENGE else 0, "attempt": 1,
        "stage": stage, "operation": op, "identity": identity, "result": result, "detail": "",
        "started_at": now(), "ended_at": None if result in OPEN else now(), "stale": False,
    }  # fmt: skip
    same = [i for i in invocations if key(i) == key(inv) and i["operation"] == op]
    inv["attempt"] = len(same) + 1
    rerun = next((i for i in same if not i["stale"]), None)
    if rerun is not None and op != OWNER and result != "reused":  # a reuse stands on the earlier run, never over it
        for i in invocations[invocations.index(rerun) :]:
            if key(i) == key(inv) and i["operation"] != OWNER:
                i["stale"] = True
    invocations.append(inv)
    return inv


def closed(
    invocations: list[dict[str, Any]], inv: dict[str, Any], result: str, detail: str = "", identity: str = ""
) -> None:
    """End *inv* with its result; an identity learned now supersedes evidence about an earlier candidate."""
    inv |= {"result": result, "detail": detail[:4000], "ended_at": now()}
    if identity:
        identified(invocations, inv, identity)


def identified(invocations: list[dict[str, Any]], inv: dict[str, Any], identity: str) -> None:
    """Record the candidate *inv* made or judged; what the rounds found about another candidate is stale now."""
    inv["identity"] = identity
    if inv["phase"] != CHALLENGE:
        return
    for i in invocations:
        if i is not inv and i["phase"] == CHALLENGE and i["operation"] != OWNER and i["identity"] not in {"", identity}:
            i["stale"] = True


def asked(invocations: list[dict[str, Any]], stage: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
    """The owner's gate for *questions*, in the phase of the stop they hold."""
    at = PUBLISH if stage in PUBLISHED else ""
    inv = opened(invocations, stage, OWNER, at=at or CHALLENGE, result="waiting")
    inv["detail"] = "; ".join(sorted({str(q.get("kind", "")) for q in questions}))
    return inv


def answered(invocations: list[dict[str, Any]], said: str, *, last: bool) -> None:
    """Note the owner's answer at his open gate; with his *last* answer the gate is answered."""
    gate = next((i for i in reversed(invocations) if i["operation"] == OWNER and i["result"] == "waiting"), None)
    if gate is None:
        return
    gate["detail"] = f"{gate['detail']}; {said}".strip("; ")[:4000]
    if last:
        gate |= {"result": "answered", "ended_at": now()}


def stopped(invocations: list[dict[str, Any]], reason: str) -> None:
    """A run held for the owner: whatever was still running stopped with it."""
    for i in invocations:
        if i["result"] == "running":
            i |= {"result": "stopped", "detail": reason[:4000], "ended_at": now()}


def words(op: str, result: str) -> str:
    """An invocation's outcome in words: a session that completed is not a candidate that passed."""
    return {
        "running": "running",
        "completed": "session completed" if op in SESSIONS else "done",
        "passed": "candidate passed" if op in JUDGED else "passed",
        "findings": "findings",
        "reused": "reused for this identity",
        "failed": "failed",
        "waiting": "waiting for you",
        "answered": "answered by you",
        "discarded": "discarded by you",
        "stopped": "stopped",
    }.get(result, result)


def progress(state: dict[str, Any]) -> dict[str, Any]:
    """What the page shows of the run's progress: its phases with their invocations in order, now and next.

    A record from before invocations is ``legacy``: no phases, its stages shown as they are.
    """
    invocations = state.get("invocations")
    shown: dict[str, dict[str, Any]] = {}
    for inv in invocations or []:
        group = shown.setdefault(key(inv), {"key": key(inv), "label": title(inv), "invocations": []})
        op = inv["operation"]
        group["invocations"].append(inv | {"label": OPERATIONS.get(op, op), "outcome": words(op, inv["result"])})
    return {
        "legacy": invocations is None,
        "phases": list(shown.values()),
        "now": _now(state, invocations),
        "next": _next(state, invocations),
    }


def _now(state: dict[str, Any], invocations: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if state["state"] == "waiting":
        gate = next((i for i in reversed(invocations or []) if i["result"] == "waiting"), None)
        n = len(state.get("questions") or [])
        return {"phase": title(gate) if gate else "", "operation": OWNER, "since": gate["started_at"] if gate else "",
                "label": f"Waiting for your answer to {n} question(s) below"}  # fmt: skip
    if state["state"] != "running":
        return None
    if invocations is None:  # a legacy record: its running stage, nothing more
        label = dict(STAGES).get(state.get("stage") or "", "Running")
        return {"phase": "", "operation": state.get("stage") or "", "label": label, "since": ""}
    current = next((i for i in reversed(invocations) if i["result"] == "running"), None)
    if current is not None:
        op = current["operation"]
        return {"phase": title(current), "operation": op, "label": OPERATIONS[op], "since": current["started_at"]}
    action = ACTIONS.get(str((state.get("context") or {}).get("next") or ""), "" if invocations else "notice")
    words_ = {"": "Starting the next step", OWNER: "Preparing your questions"}
    label = words_.get(action, f"Starting: {OPERATIONS.get(action)}")
    return {"phase": "", "operation": action, "label": label, "since": ""}


def _next(state: dict[str, Any], invocations: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """The controller's next step after now: fixed by the run, by a session's verdict, or by the owner's answer."""
    if state["state"] == "waiting":
        options = list(dict.fromkeys(o["label"] for q in state.get("questions") or [] for o in q.get("options", [])))
        return {"operation": "", "by": "owner", "label": "Your answer decides what runs next", "options": options}
    current = next((i for i in reversed(invocations or []) if i["result"] == "running"), None)
    if state["state"] != "running" or current is None:
        return None
    op, by = current["operation"], "run"
    if op in FOLLOWS:
        then = FOLLOWS[op]
        label = OPERATIONS[then]
    elif op == "candidate-golden":
        then, label = "replay", "Calibration replay, after your decision if the candidate changed golden evidence"
    elif op == "replay":
        then = ACTIONS.get(str((state.get("context") or {}).get("after") or ""), "")
        label = OPERATIONS.get(then, "Decided by the rounds")
    elif op == "merge":
        then, label = "", "Done: the pack is merged into main"
    else:
        then, by = "", "verdict"
        label = "Decided by the verdict: findings go back to the updater or to you; a pass goes to publication"
    return {"operation": then, "by": by, "label": label, "options": []}
