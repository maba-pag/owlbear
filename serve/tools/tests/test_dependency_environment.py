from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_tools.dependency_environment import dep_status, dep_sync


def _checkout(tmp_path: Path, *, all_roots: bool = False) -> Path:
    (tmp_path / "serve/cockpit/web").mkdir(parents=True)
    (tmp_path / "serve/cockpit/web/.nvmrc").write_text("24.19.0\n", encoding="utf-8")
    (tmp_path / "serve/cockpit/web/package-lock.json").write_text("{}\n", encoding="utf-8")
    if all_roots:
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
        (tmp_path / "package-lock.json").write_text("{}\n", encoding="utf-8")
        diagrams = tmp_path / ".owlbear/scripts/export-diagrams"
        diagrams.mkdir(parents=True)
        (diagrams / "package-lock.json").write_text("{}\n", encoding="utf-8")
        (tmp_path / "serve/cockpit/web/public").mkdir(parents=True)
    return tmp_path


def _successful_process(command: list[str], *, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, 0, stdout, "")


def test_dep_sync_default_uses_short_profile_and_node_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    calls: list[tuple[list[str], Path]] = []

    def run(command: list[str], *, cwd: Path, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        return _successful_process(command)

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-sync"])
        with pytest.raises(SystemExit, match="0"):
            dep_sync()

    commands = [command for command, _ in calls]
    assert ["uv", "sync", "--locked", "--all-packages", "--all-extras", "--all-groups"] in commands
    assert ["npm", "ci"] in commands
    assert all("export-diagrams" not in str(cwd) for command, cwd in calls if command != ["npm", "ci"])


def test_dep_sync_all_includes_every_root_pds_and_browsers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path, all_roots=True)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    calls: list[tuple[list[str], Path]] = []

    def run(command: list[str], *, cwd: Path, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        return _successful_process(command)

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-sync", "-a"])
        with pytest.raises(SystemExit, match="0"):
            dep_sync()

    npm_cwds = {cwd.relative_to(repository).as_posix() for command, cwd in calls if command == ["npm", "ci"]}
    assert npm_cwds == {"serve/cockpit/web", ".", ".owlbear/scripts/export-diagrams"}
    assert sum(command[:3] == ["npx", "--no-install", "playwright"] for command, _ in calls) == 2
    assert ["npm", "run", "sync:pds"] in [command for command, _ in calls]


def test_dep_sync_browsers_installs_only_browser_package_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path, all_roots=True)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    calls: list[tuple[list[str], Path]] = []

    def run(command: list[str], *, cwd: Path, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        return _successful_process(command)

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-sync", "-b"])
        with pytest.raises(SystemExit, match="0"):
            dep_sync()

    npm_cwds = {cwd.relative_to(repository).as_posix() for command, cwd in calls if command == ["npm", "ci"]}
    assert npm_cwds == {"serve/cockpit/web", ".owlbear/scripts/export-diagrams"}
    browser_cwds = {
        cwd.relative_to(repository).as_posix()
        for command, cwd in calls
        if command[:3] == ["npx", "--no-install", "playwright"]
    }
    assert browser_cwds == {"serve/cockpit/web", ".owlbear/scripts/export-diagrams"}


def test_dep_sync_attempts_later_roots_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path, all_roots=True)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        return subprocess.CompletedProcess(command, 1 if command[0] == "uv" else 0, "", "failed")

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-sync", "-a"])
        with pytest.raises(SystemExit, match="1"):
            dep_sync()

    assert ["npm", "ci"] in calls
    assert any(command[:3] == ["npx", "--no-install", "playwright"] for command in calls)


def test_dep_sync_blocks_node_surfaces_when_runtime_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path, all_roots=True)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)
    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v22.0.0\n")
        return _successful_process(command)

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-sync", "-a"])
        with pytest.raises(SystemExit, match="1"):
            dep_sync()

    assert ["npm", "run", "sync:pds"] not in calls
    assert not any(command == ["npm", "ci"] for command in calls)
    assert not any(command[:3] == ["npx", "--no-install", "playwright"] for command in calls)


def test_dep_status_json_has_short_json_alias_and_npm_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _checkout(tmp_path)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        if command[:2] == ["uv", "lock"]:
            return _successful_process(command)
        if command[0] == "uv":
            return _successful_process(command, stdout="Would make no changes\n")
        return _successful_process(
            command,
            stdout=(
                "change is-number 7.0.0 => 6.0.0\n"
                + json.dumps(
                    {
                        "change": [
                            {
                                "name": "is-number",
                                "from": {"name": "is-number", "version": "7.0.0"},
                                "to": {"name": "is-number", "version": "6.0.0"},
                            }
                        ]
                    }
                )
            ),
        )

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-status", "-j"])
        with pytest.raises(SystemExit, match="1"):
            dep_status()

    document = json.loads(capsys.readouterr().out)
    assert document["recommendation"] == "uv run dep-sync --all"
    npm_result = next(item for item in document["results"] if item["name"] == "Cockpit npm")
    assert npm_result["status"] == "stale"
    assert npm_result["changes"] == [{"package": "is-number", "kind": "change", "from": "7.0.0", "to": "6.0.0"}]


def test_dep_status_marks_numeric_npm_change_counts_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = _checkout(tmp_path)
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        if command[:2] == ["uv", "lock"]:
            return _successful_process(command)
        if command[0] == "uv":
            return _successful_process(command, stdout="Would make no changes\n")
        return _successful_process(
            command,
            stdout=json.dumps({"add": [], "added": 1, "remove": [], "removed": 0, "change": [], "changed": 0}),
        )

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-status", "-j"])
        with pytest.raises(SystemExit, match="1"):
            dep_status()

    document = json.loads(capsys.readouterr().out)
    npm_result = next(item for item in document["results"] if item["name"] == "Cockpit npm")
    assert npm_result["status"] == "stale"


def test_dep_status_pds_compares_generated_assets_without_mutating_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _checkout(tmp_path, all_roots=True)
    target = repository / "serve/cockpit/web/public/porsche-design-system"
    target.mkdir()
    sentinel = target / "checked-in.js"
    sentinel.write_text("checked in\n", encoding="utf-8")
    monkeypatch.chdir(repository)
    monkeypatch.setattr("owlbear_tools.dependency_environment._require_development", lambda _name: None)

    def run(
        command: list[str], *, env: dict[str, str] | None = None, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command == ["node", "--version"]:
            return _successful_process(command, stdout="v24.19.0\n")
        if command[:2] == ["uv", "lock"]:
            return _successful_process(command)
        if command[0] == "uv":
            return _successful_process(command, stdout="Would make no changes\n")
        if command[:3] == ["npm", "run", "sync:pds"]:
            assert env is not None
            generated = Path(env["PDS_OUTPUT_DIR"])
            generated.mkdir(parents=True, exist_ok=True)
            (generated / "generated.js").write_text("generated\n", encoding="utf-8")
            return _successful_process(command)
        return _successful_process(command, stdout="{}\n")

    with patch("owlbear_tools.dependency_environment._run", side_effect=run):
        monkeypatch.setattr(sys, "argv", ["dep-status", "-p"])
        with pytest.raises(SystemExit, match="1"):
            dep_status()

    assert sentinel.read_text(encoding="utf-8") == "checked in\n"
    assert not (target / "generated.js").exists()
