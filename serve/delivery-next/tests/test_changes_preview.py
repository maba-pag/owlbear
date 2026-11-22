"""The Changes preview: only its fixture project, the c8-shaped stop's rerun offer, and a confirmation that spawns
nothing."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

SCRIPT = Path(__file__).with_name("changes_preview.py")
LAUNCH = "Changes preview: a runner would start now; none starts"  # changes_preview.LAUNCH


def test_the_preview_serves_its_stop_and_a_confirmed_rerun_spawns_nothing(tmp_path) -> None:
    home, data = tmp_path / "sentinel-home", tmp_path / "sentinel-data"
    (home / ".owlbear").mkdir(parents=True)
    (home / ".owlbear" / "machine.json").write_text('{"projects": [{"id": "sentinel", "path": "/sentinel-project"}]}\n')
    data.mkdir()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ | {"HOME": str(home), "OWLBEAR_DATA": str(data)}
    log = tmp_path / "preview.log"
    with log.open("w") as out:
        argv = [sys.executable, str(SCRIPT), str(port)]
        preview = subprocess.Popen(argv, env=env, stdout=out, stderr=subprocess.STDOUT)  # noqa: S603 - this interpreter, the adjacent script
    base, auth = f"http://127.0.0.1:{port}", {"authorization": "Bearer preview"}
    try:
        deadline = time.monotonic() + 30
        while True:
            assert preview.poll() is None, log.read_text()
            try:
                projects = httpx.get(f"{base}/api/next/projects", headers=auth, timeout=10).json()["projects"]
                break
            except httpx.TransportError:
                assert time.monotonic() < deadline, "the preview did not answer in 30 s"
                time.sleep(0.2)
        [clone] = projects
        change = f"{base}/p/{clone['id']}/api/next/changes/c1"
        recovery = httpx.get(change, headers=auth, timeout=10).json()["recovery"]
        confirm = {"action": recovery["action"], "at": recovery["at"]}
        accepted = httpx.post(f"{change}/recovery", json=confirm, headers=auth, timeout=10)
        while LAUNCH not in log.read_text():
            assert time.monotonic() < deadline + 30, log.read_text()
            time.sleep(0.2)
        after = httpx.get(change, headers=auth, timeout=10).json()
    finally:
        preview.terminate()
        preview.wait(timeout=20)
    said = log.read_text()
    assert ([c["name"] for c in projects], "sentinel" in str(projects) + said) == (["preview-shop"], False)
    rerun = recovery["rerun"]
    assert (recovery["action"], rerun["step"], rerun["role"], rerun["repairer"]) == (
        "Run the step again",
        "build",
        "builder",
        True,
    )
    assert (accepted.status_code, after["recovery"], after["stopped"]) == (200, None, False)
    assert ("runner" in said.replace(LAUNCH, ""), "pass failed" in said) == (False, False)
