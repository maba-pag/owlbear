"""The machine host's Metrics page on fixture data only, for the visual check: ``metrics_preview.py <port>``.

Launch recipe for the visual check: directory ``serve/delivery-next``, command
``uv run python tests/metrics_preview.py {port}``, ready URL ``http://127.0.0.1:{port}/``; the state paths (e.g.
``/metrics?period=all&by=agent``) open without ``#token=`` because SEED supplies the token.

It never reads the owner's data: ``main`` replaces HOME with a fresh temporary folder before it imports OwlBear,
drops ``OWLBEAR_DATA`` and ``COPILOT_HOME``, and keeps Git from reaching GitHub (D-01M68Z8Q740BSN13D1R06JX6DW);
importing this file changes nothing. The page is ``http://127.0.0.1:<port>/metrics#token=preview``; every HTML page it
serves also seeds that token itself (``SEED``), so a capture that opens a state path without the fragment still renders
the fixture, never the page's missing-token notice. The fixture holds 8 agents in 2 projects, 4 models, 5 steps and
"No step", 14 days of 2 runs each, 7 tools covering every outcome, and session logs: compactions with timing shares
for 4 agents, a compacted session without a share, and an agent whose sessions are readable but never compacted.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

TOKEN = "preview"  # noqa: S105 - a fixture host on 127.0.0.1 only
SEED = f'<script>sessionStorage.setItem("token", "{TOKEN}")</script>'
DAYS = 14
DAILY = 2  # runs a day: the runs list stays short enough for one capture of each state
AGENTS = (  # (agent, step, its sessions' logs: "compacts", "never" compacts, or None without a log)
    ("shaper", "shape", "compacts"), ("planner", "plan", "compacts"), ("builder", "build", "compacts"),
    ("reviewer", "review", "compacts"), ("challenger", "plan", "never"), ("preparer", "check", None),
    ("repairer", "build", None), ("updater", "", None),
)  # fmt: skip
MODELS = ("claude-opus-5.5", "gpt-6.1-sol", "claude-haiku-5.5", "gpt-6-luna")
PROJECTS = (("shop", "shop-site"), ("owlbear", "owlbear"))
TOOLS = {  # one run's tally per tool: together every outcome (accepted, invalid, checks, order, unsplit, lint, late)
    "submit_result": {"calls": 4, "rejected": 2, "invalid": 1, "checks": 1, "lint": 1, "retries": 1},
    "ask_question": {"calls": 2, "rejected": 1, "order": 1},
    "report_wrong_premise": {"calls": 2, "rejected": 1},
    "report_missing_tool": {"calls": 3, "rejected": 1, "invalid": 1, "late": 1},
    "lookup_decisions": {"calls": 5},
    "scan_design": {"calls": 3, "rejected": 1, "checks": 1, "lint": 1},
    "record_decision": {"calls": 2, "late": 1},
}


def _isolate() -> Path:
    """A fresh HOME for this process, the owner's data and Copilot folders dropped, Git kept off GitHub."""
    home = Path(tempfile.mkdtemp(prefix="owlbear-metrics-preview-"))
    os.environ["HOME"] = str(home)
    for name in ("OWLBEAR_DATA", "COPILOT_HOME", *(n for n in os.environ if n.startswith("GIT_CONFIG_"))):
        os.environ.pop(name, None)
    offline, github = "/nonexistent/offline-in-preview/", "https://github.com/"
    (home / ".gitconfig").write_text(f'[url "{offline}"]\n\tinsteadOf = {github}\n')
    os.environ |= {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": f"url.{offline}.insteadOf",
                   "GIT_CONFIG_VALUE_0": github}  # fmt: skip
    return home


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
    from owlbear_delivery_next.improvement import chatlogs  # noqa: PLC0415 - only once HOME is replaced

    path = chatlogs.state() / session / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines))


def seed() -> None:
    """The ledger's runs and their sessions' logs, all written into the temporary HOME."""
    from owlbear_delivery_next.state_store import spend_ledger  # noqa: PLC0415 - only once HOME is replaced

    now = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    lines: list[dict] = []
    unshared: list[str] = []
    k = 0
    for day in range(DAYS):
        for i, (agent, step, logs) in enumerate(AGENTS):
            if (day + i) % (every := len(AGENTS) // DAILY):
                continue
            k += 1
            rid, model = f"r{k}", MODELS[(day // 2 + i + i // every) % len(MODELS)]
            project, name = PROJECTS[day // 2 % 2]
            at = (now - timedelta(days=day, minutes=i)).isoformat(timespec="seconds")
            spent = round(0.4 + (day * 7 + i * 3) % 11 * 0.37, 2)
            counts = {"credits": spent, "input": 900 * k, "output": 40 * k}
            usage = {"error": "TimeoutError"} if k == 5 else {"credits": spent, "models": {model: counts}}  # 5: unknown
            place = {"run": rid, "session": f"s-{rid}", "clone": "", "project": project, "name": name,
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
    assert not spend_ledger.append(lines), "the fixture ledger could not be written"


def seed_pages(pages) -> None:
    """Each page *pages* serves gets ``SEED`` right after ``<head>``, before the page's own modules run."""
    served = pages.pages
    pages.pages = lambda: {path: html.replace("<head>", "<head>" + SEED, 1) for path, html in served().items()}


def main() -> None:
    port = int(sys.argv[1])
    home = _isolate()
    import uvicorn  # noqa: PLC0415 - OwlBear and its server only once HOME is replaced

    from owlbear_delivery_next.local_system import codebase  # noqa: PLC0415
    from owlbear_delivery_next.machine_host import app  # noqa: PLC0415
    from owlbear_delivery_next.machine_host.machine import Machine  # noqa: PLC0415
    from owlbear_delivery_next.project_host import pages  # noqa: PLC0415
    from owlbear_delivery_next.project_host.host import HostRecord  # noqa: PLC0415

    def gone() -> None:
        shutil.rmtree(home, ignore_errors=True)

    seed()
    seed_pages(pages)
    base = f"http://127.0.0.1:{port}"
    record = HostRecord(url=f"{base}/", token=TOKEN, pid=os.getpid(), started_at=datetime.now(UTC),
                        code=codebase.CURRENT)  # fmt: skip
    print(f"Metrics preview: {base}/metrics#token={TOKEN}", flush=True)  # noqa: T201 - the recipe's address
    try:  # Uvicorn replays a stop signal once it returns: the app's own end removes HOME
        uvicorn.run(app.create(Machine(record), gone), host="127.0.0.1", port=port, log_level="warning")
    finally:
        gone()


if __name__ == "__main__":
    main()
