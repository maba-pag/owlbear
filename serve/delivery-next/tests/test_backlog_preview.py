"""The Backlog preview's data boundary: it serves its fixture only, never the owner's HOME, data or Copilot folder."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

from owlbear_delivery_next.git.git_executable import resolve_git_executable


def _get(url: str, **headers: str) -> httpx.Response:
    answer = httpx.get(url, headers=headers, timeout=10)
    answer.raise_for_status()
    return answer


def _sentinel_data(path: Path) -> None:
    """A data checkout whose origin, settings and files all say ``sentinel``."""
    path.mkdir(parents=True)
    (path / "config.json").write_text('{"sentinel": "sentinel-setting"}\n')
    (path / "sentinel-project").mkdir()
    (path / "sentinel-project" / "repository").write_text("github.com/sentinel/sentinel-project\n")
    git = [resolve_git_executable(), "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(path)]
    for args in (
        ["init", "-q"],
        ["remote", "add", "origin", "https://github.com/sentinel/sentinel-data.git"],
        ["add", "-A"],
        ["commit", "-qm", "sentinel"],
    ):
        subprocess.run([*git, *args], check=True)  # noqa: S603 - fixture Git argv on a temporary path


def test_the_preview_serves_its_fixture_and_never_the_owners_data(tmp_path, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).parent))  # a script beside the tests, not a package module
    import backlog_preview  # noqa: PLC0415 - importing it changes nothing; it runs in its own process below

    home, data, copilot = tmp_path / "sentinel-home", tmp_path / "sentinel-data", tmp_path / "sentinel-copilot"
    _sentinel_data(home / ".owlbear" / "data")
    _sentinel_data(data)
    (home / ".owlbear" / "machine.json").write_text('{"projects": [{"id": "sentinel", "path": "/sentinel-project"}]}\n')
    for folder in (home / ".copilot", copilot):
        (folder / "session-state" / "sentinel-session").mkdir(parents=True)
        (folder / "session-state" / "sentinel-session" / "events.jsonl").write_text('{"type": "sentinel"}\n')
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ | {"HOME": str(home), "OWLBEAR_DATA": str(data), "COPILOT_HOME": str(copilot)}
    argv = [sys.executable, backlog_preview.__file__, str(port)]
    pipes = {"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
    preview = subprocess.Popen(argv, env=env, **pipes)  # noqa: S603 - this interpreter runs the adjacent script, no shell
    base, auth = f"http://127.0.0.1:{port}", {"authorization": f"Bearer {backlog_preview.TOKEN}"}
    try:
        deadline = time.monotonic() + 30
        while True:
            assert preview.poll() is None, preview.stdout.read() if preview.stdout else ""
            try:
                projects = _get(f"{base}/api/next/projects", **auth).json()["projects"]
                break
            except httpx.TransportError:
                assert time.monotonic() < deadline, "the preview did not answer in 30 s"
                time.sleep(0.2)
        [clone] = projects
        listed = _get(f"{base}/p/{clone['id']}/api/next/backlog", **auth)
        page = _get(f"{base}/backlog?reviews=open").text  # a visual state's path, without #token=
    finally:
        preview.terminate()
        out, _ = preview.communicate(timeout=20)
    assert [t for t in (listed.text, page, out, str(projects)) if "sentinel" in t] == []
    assert page.index(backlog_preview.SEED) < page.index(backlog_preview.OPEN) < page.index('type="module"')
    entries = listed.json()["entries"]
    reviews = [e["status"] for e in entries if e["suppression_review"]]
    assert (reviews.count("inbox") >= 3, set(reviews)) == (True, {"inbox", "open", "dropped"})
    assert {e["origin"] for e in entries} == {clone["name"]}  # every review links to the registered clone
    assert [e for e in entries if e["status"] == "inbox" and not e["suppression_review"]] != []
