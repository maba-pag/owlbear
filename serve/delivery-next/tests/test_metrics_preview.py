"""The Metrics preview's data boundary: it serves its fixture only, never the owner's HOME, data or Copilot folder."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def _metrics(base: str, by: str, token: str) -> str:
    url = f"{base}/api/next/metrics?by={by}"
    asked = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})  # noqa: S310 - http to 127.0.0.1
    with urllib.request.urlopen(asked, timeout=10) as answer:  # noqa: S310 - the preview on 127.0.0.1
        return answer.read().decode()


def test_the_preview_serves_its_fixture_and_never_the_owners_data(tmp_path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).parent))  # a script beside the tests, not a package module
    import metrics_preview  # noqa: PLC0415 - importing it changes nothing; it runs in its own process below

    home, data, copilot = tmp_path / "sentinel-home", tmp_path / "sentinel-data", tmp_path / "sentinel-copilot"
    trap = {"run": "sentinel-run", "session": "sentinel-session", "project": "sentinel-project", "agent": "sentinel"}
    at = datetime.now(UTC).isoformat(timespec="seconds")
    ledger = "".join(json.dumps(trap | line) + "\n" for line in (
        {"id": "start:sentinel", "type": "start", "at": at, "model": "sentinel-model", "before": {}},
        {"id": "end:sentinel", "type": "end", "at": at, "usage": {"credits": 99.0, "models": {}},
         "tools": {"sentinel_tool": {"calls": 1}}, "wrong": {}},
    ))  # fmt: skip
    for spend in (home / ".owlbear" / "spend", data / "spend"):
        spend.mkdir(parents=True)
        (spend / f"spend-{datetime.now(UTC):%Y-%m}.jsonl").write_text(ledger)
    for folder in (home / ".copilot", copilot):
        (folder / "session-state" / "sentinel-session").mkdir(parents=True)
        (folder / "session-state" / "sentinel-session" / "events.jsonl").write_text('{"type": "sentinel"}\n')
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ | {"HOME": str(home), "OWLBEAR_DATA": str(data), "COPILOT_HOME": str(copilot)}
    preview = subprocess.Popen([sys.executable, metrics_preview.__file__, str(port)], env=env, stdout=subprocess.PIPE,  # noqa: S603
                               stderr=subprocess.STDOUT, text=True)  # fmt: skip
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 20
        while True:
            assert preview.poll() is None, preview.stdout.read() if preview.stdout else ""
            try:
                answers = {by: _metrics(base, by, metrics_preview.TOKEN) for by in ("agent", "model", "step", "day")}
                break
            except OSError:
                assert time.monotonic() < deadline, "the preview did not answer in 20 s"
                time.sleep(0.2)
    finally:
        preview.terminate()
        out, _ = preview.communicate(timeout=10)
    assert [by for by, text in answers.items() if "sentinel" in text] == []
    assert "sentinel" not in out
    found = {by: json.loads(text) for by, text in answers.items()}
    least = {"agent": 8, "model": 3, "step": 3, "day": 14}
    assert [by for by, n in least.items() if len(found[by]["rows"]) < n] == []
    tools = found["agent"]["tool_use"]
    outcomes = ("accepted", "invalid", "checks", "order", "unsplit", "lint", "late")
    assert len(tools["tools"]) >= 6
    assert [k for k in outcomes if not tools["totals"][k]] == []
    compaction = found["agent"]["compaction"]["rows"]
    assert len({r["agent"] for r in compaction if r["shares"]}) >= 3
    assert [r["agent"] for r in compaction if r["unshared"] and r["project"]] == ["builder"]
    assert [r["agent"] for r in compaction if r["logs"] and not r["compacted"] and r["project"]] != []
