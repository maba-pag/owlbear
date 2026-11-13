from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_tools.dependency_environment import dep_status, dep_sync


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".nvmrc").write_text("24.19.0\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    return tmp_path


@pytest.mark.parametrize(
    ("python_exit", "node", "exit_code"),
    [(0, "24.19.0", 0), (1, "24.19.0", 1), (0, "22.0.0", 1)],
    ids=["success", "python-fails-npm-still-runs", "wrong-node-blocks-npm"],
)
def test_dep_sync_installs_python_and_root_npm_after_node_check(
    checkout: Path, monkeypatch: pytest.MonkeyPatch, python_exit: int, node: str, exit_code: int
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def run(command: list[str], *, cwd: Path, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command, python_exit if command[0] == "uv" else 0, f"v{node}\n", "failed" if python_exit else ""
        )

    monkeypatch.setattr("owlbear_tools.dependency_environment._run", run)
    monkeypatch.setattr(sys, "argv", ["dep-sync"])
    with pytest.raises(SystemExit) as exited:
        dep_sync()

    assert exited.value.code == exit_code
    expected = [
        (["uv", "sync", "--locked", "--all-packages", "--all-groups"], checkout),
        (["node", "--version"], checkout),
    ]
    if node == "24.19.0":
        expected.append((["npm", "ci"], checkout))
    assert calls == expected


@pytest.mark.parametrize(
    ("npm_output", "changes"),
    [
        (
            "change is-number 7.0.0 => 6.0.0\n"
            + json.dumps({"change": [{"name": "is-number", "from": {"version": "7.0.0"}, "to": {"version": "6.0.0"}}]}),
            [{"package": "is-number", "kind": "change", "from": "7.0.0", "to": "6.0.0"}],
        ),
        (json.dumps({"add": [], "added": 1, "remove": [], "removed": 0, "change": [], "changed": 0}), []),
    ],
    ids=["prefixed-records", "numeric-counts"],
)
@pytest.mark.usefixtures("checkout")
def test_dep_status_json_has_short_json_alias_and_npm_changes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    npm_output: str,
    changes: list[dict[str, str]],
) -> None:
    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        output = "v24.19.0\n" if command == ["node", "--version"] else npm_output
        if command[0] == "uv":
            output = "" if command[:2] == ["uv", "lock"] else "Would make no changes\n"
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr("owlbear_tools.dependency_environment._run", run)
    monkeypatch.setattr(sys, "argv", ["dep-status", "-j"])
    with pytest.raises(SystemExit) as exited:
        dep_status()

    assert exited.value.code == 1
    document = json.loads(capsys.readouterr().out)
    assert set(document) == {"command", "results"}
    npm_result = next(item for item in document["results"] if item["name"] == "Root npm")
    assert npm_result["status"] == "stale"
    assert npm_result["changes"] == changes
