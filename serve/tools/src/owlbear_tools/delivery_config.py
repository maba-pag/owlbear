"""Delivery target-branch configuration and project-state diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from owlbear_delivery.storage_io import atomic_write
from owlbear_tools.commands import command_footer

_DELIVERY_CONFIG = Path(".owlbear/delivery/config.json")
_CHANGE_GLOB = ".owlbear/delivery/runtime/changes/*"
_FRONTIER_GLOB = ".owlbear/delivery/runtime/changes/*/frontier.json"
_COORDINATION_GLOB = ".owlbear/delivery/runtime/claims/changes/*.json"
_PACKAGE_GLOB = ".owlbear/delivery/packages/*"
_LEGACY_DELIVERY_ROOTS = (Path(".owlbear/target"), Path(".owlbear/worktrees"))
_DELIVERY_CONFIG_SCHEMA_VERSION = 2


def _run(command: list[str], *, cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode  # noqa: S603


def _load_json(path: Path) -> dict[str, object]:
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        msg = f"{path} must contain a JSON object"
        raise TypeError(msg)
    return content


def _remote_target_exists(root: Path, remote: str, branch: str) -> bool:
    syntax = _run(["git", "check-ref-format", f"refs/heads/{branch}"], cwd=root)
    exists = _run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}"],
        cwd=root,
    )
    return syntax == 0 and exists == 0


def _has_terminal_completion(frontier: dict[str, object]) -> bool:
    if frontier.get("change_abandonment") is not None or frontier.get("change_completion") is not None:
        return True
    completion = frontier.get("integration_completion")
    result_id = frontier.get("integration_result_id")
    return isinstance(completion, dict) and isinstance(result_id, str) and completion.get("completion_id") == result_id


def _remote_github_repository(root: Path, remote: str) -> str | None:
    completed = subprocess.run(  # noqa: S603
        ["git", "remote", "get-url", remote],  # noqa: S607
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    match = re.fullmatch(
        r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^\s/]+/[^\s/]+?)(?:\.git)?",
        completed.stdout.strip(),
    )
    return match.group(1) if match else None


def _delivery_config_status(root: Path) -> tuple[list[str], str | None]:
    config_path = root / _DELIVERY_CONFIG
    try:
        config = _load_json(config_path)
    except (OSError, TypeError, json.JSONDecodeError) as exc:
        return [f"Delivery config is unavailable: {exc}"], None
    failures: list[str] = []
    schema_version = config.get("schema_version")
    remote = config.get("remote")
    target = config.get("target_branch")
    github_repository = config.get("github_repository")
    if schema_version != _DELIVERY_CONFIG_SCHEMA_VERSION:
        return [f"unsupported Delivery config schema: {schema_version}"], None
    valid_target = isinstance(remote, str) and isinstance(target, str) and _remote_target_exists(root, remote, target)
    if not valid_target:
        failures.append(f"configured remote-tracking target is unavailable: {remote}/{target}")
    elif not isinstance(github_repository, str) or _remote_github_repository(root, remote) != github_repository:
        failures.append(f"configured GitHub repository does not match remote {remote}: {github_repository}")
    if failures:
        return failures, None
    return [], f"Delivery target is {remote}/{target} in {github_repository}"


def _legacy_delivery_blockers(root: Path) -> list[str]:
    blockers: list[str] = []
    if (root / ".owlbear").is_symlink() or (root / ".owlbear/delivery").is_symlink():
        blockers.append("Delivery state parents must not be symlinks")
    for relative in _LEGACY_DELIVERY_ROOTS:
        legacy_root = root / relative
        try:
            has_legacy_state = legacy_root.exists() and any(legacy_root.iterdir())
        except OSError:
            has_legacy_state = True
        if has_legacy_state:
            blockers.append(f"unmigrated Delivery state: {relative}")
    return blockers


def _delivery_blockers(root: Path) -> list[str]:
    blockers = _legacy_delivery_blockers(root)
    for path in sorted(root.glob(_CHANGE_GLOB)):
        if not (path / "frontier.json").is_file():
            blockers.append(f"incomplete Delivery change: {path.name}")
    for path in sorted(root.glob(_FRONTIER_GLOB)):
        try:
            frontier = _load_json(path)
        except OSError, TypeError, json.JSONDecodeError:
            blockers.append(f"unreadable Delivery frontier: {path.relative_to(root)}")
            continue
        active_claims = [
            binding.get("active_claim") for binding in frontier.get("bindings", []) if isinstance(binding, dict)
        ]
        if any(claim is not None for claim in active_claims) or frontier.get("integration_repair_claim") is not None:
            blockers.append(f"active Delivery claim: {path.parent.name}")
        elif not _has_terminal_completion(frontier):
            blockers.append(f"unfinished Delivery change: {path.parent.name}")
    for path in sorted(root.glob(_COORDINATION_GLOB)):
        try:
            _load_json(path)
        except OSError, TypeError, json.JSONDecodeError:
            blockers.append(f"unreadable Delivery coordination: {path.relative_to(root)}")
            continue
        blockers.append(f"unfinished Delivery coordination: {path.stem}")
    for path in sorted(root.glob(_PACKAGE_GLOB)):
        blockers.append(f"unfinished Delivery package: {path.name}")
    return blockers


def target_branch() -> None:
    """Show or safely update the Delivery pull-request target branch."""
    parser = argparse.ArgumentParser(prog="target-branch")
    parser.add_argument("branch", nargs="?")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    path = root / _DELIVERY_CONFIG
    try:
        config = _load_json(path)
        current = config["target_branch"]
        remote = config["remote"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(f"cannot read {path}: {exc}")
    if not isinstance(current, str) or not current or not isinstance(remote, str) or not remote:
        parser.error(f"{path} has an invalid target_branch or remote")
    if args.branch is None:
        print(current)  # noqa: T201
        return
    if args.branch == current:
        print(f"Target branch is already {current}.")  # noqa: T201
        return
    if not _remote_target_exists(root, remote, args.branch):
        parser.error(f"remote-tracking target does not exist or is invalid: {remote}/{args.branch}")
    blockers = _delivery_blockers(root)
    if blockers:
        parser.error("cannot change target while Delivery work exists:\n  " + "\n  ".join(blockers))
    config["target_branch"] = args.branch
    atomic_write(path, json.dumps(config, indent=2) + "\n")
    print(f"Target branch changed: {current} -> {args.branch}")  # noqa: T201
    print(command_footer(), file=sys.stderr)  # noqa: T201
