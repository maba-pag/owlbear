"""Project setup, diagnostics, dependency, and maintenance commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from owlbear_delivery.storage_io import atomic_write
from owlbear_tools.commands import command_footer
from owlbear_tools.megalinter import load_megalinter_image

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_DELIVERY_CONFIG = Path(".owlbear/delivery/config.json")
_CHANGE_GLOB = ".owlbear/delivery/runtime/changes/*"
_FRONTIER_GLOB = ".owlbear/delivery/runtime/changes/*/frontier.json"
_COORDINATION_GLOB = ".owlbear/delivery/runtime/claims/changes/*.json"
_PACKAGE_GLOB = ".owlbear/delivery/packages/*"
_LEGACY_DELIVERY_ROOTS = (Path(".owlbear/target"), Path(".owlbear/worktrees"))
_DELIVERY_CONFIG_SCHEMA_VERSION = 2


def _run(command: list[str], *, cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode  # noqa: S603


def _finish(exit_code: int) -> None:
    print(command_footer(), file=sys.stderr)  # noqa: T201
    raise SystemExit(exit_code)


def hooks_install() -> None:
    """Install the Git hook and all configured hook environments."""
    install = _run(["pre-commit", "install"])
    environments = _run(["pre-commit", "install-hooks"]) if install == 0 else install
    _finish(environments)


def setup_project() -> None:
    """Run the repository initializer for a target project."""
    parser = argparse.ArgumentParser(prog="setup-project")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--remote", default="origin", metavar="NAME")
    parser.add_argument("--target-branch", metavar="BRANCH")
    parser.add_argument("--github-repository", metavar="OWNER/NAME")
    parser.add_argument("--replace-hooks", action="store_true")
    args = parser.parse_args()
    target = args.path.expanduser().resolve()
    command = [sys.executable, str(_REPOSITORY_ROOT / "setup/init.py")]
    command.extend(["--remote", args.remote])
    if args.target_branch:
        command.extend(["--target-branch", args.target_branch])
    if args.github_repository:
        command.extend(["--github-repository", args.github_repository])
    if args.replace_hooks:
        command.append("--replace-hooks")
    _finish(_run(command, cwd=target))


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
        failures.append(f"unsupported Delivery config schema: {schema_version}")
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
        elif frontier.get("integration_completion") is None:
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


def doctor() -> None:
    """Check the shallow prerequisites and tracked project policy."""
    parser = argparse.ArgumentParser(prog="doctor")
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.path.expanduser().resolve()
    failures: list[str] = []
    warnings: list[str] = []

    for executable in ("git", "uv"):
        if shutil.which(executable):
            print(f"PASS  {executable} is available")  # noqa: T201
        else:
            failures.append(f"{executable} is not available")
    config_failures, config_success = _delivery_config_status(root)
    failures.extend(config_failures)
    if config_success is not None:
        print(f"PASS  {config_success}")  # noqa: T201
    failures.extend(_legacy_delivery_blockers(root))
    for relative in (Path(".vscode/mcp.json"),):
        if (root / relative).is_file():
            print(f"PASS  {relative}")  # noqa: T201
        else:
            failures.append(f"missing {relative}")
    if (root / "package-lock.json").is_file() and shutil.which("npm") is None:
        warnings.append("npm is unavailable for this Node project")

    for warning in warnings:
        print(f"WARN  {warning}")  # noqa: T201
    for failure in failures:
        print(f"FAIL  {failure}")  # noqa: T201
    _finish(1 if failures else 0)


def deps_status() -> None:
    """Check lock consistency and report available dependency updates."""
    print("Dependency status is informational; manifests and lockfiles will not be changed.")  # noqa: T201
    lock_status = _run(["uv", "lock", "--check"])
    python_status = _run(["uv", "tree", "--outdated"])
    npm_status = 0
    web = Path("serve/cockpit/web")
    if (web / "package-lock.json").is_file():
        print(  # noqa: T201
            "npm: Current is installed, Wanted is the newest version allowed by package.json, "
            "and Latest is the newest published version."
        )
        npm_status = _run(["npm", "outdated"], cwd=web)
    if python_status == 1 or npm_status == 1:
        print(  # noqa: T201
            "Updates remain available. deps-sync may restore Current from the existing locks, "
            "but it does not update locks or manifest ranges."
        )
    _finish(1 if lock_status or python_status not in {0, 1} or npm_status not in {0, 1} else 0)


def deps_sync() -> None:
    """Install the exact locked Python and npm dependency sets."""
    print(  # noqa: T201
        "Installing existing Python and npm lockfiles exactly; versions and manifest ranges will not be updated."
    )
    python_status = _run(["uv", "sync", "--locked", "--all-extras"])
    if python_status:
        _finish(python_status)
    web = Path("serve/cockpit/web")
    npm_status = _run(["npm", "ci"], cwd=web) if (web / "package-lock.json").is_file() else 0
    if npm_status == 0:
        print(  # noqa: T201
            "Installed dependencies now match the existing locks. Any remaining deps-status entries "
            "require a lock or manifest update."
        )
    _finish(npm_status)


def pds_sync() -> None:
    """Refresh PDS assets in a temporary tree and replace only on success."""
    web = Path("serve/cockpit/web").resolve()
    public = web / "public"
    target = public / "porsche-design-system"
    with tempfile.TemporaryDirectory(dir=public, prefix=".pds-sync-") as temporary:
        temporary_path = Path(temporary)
        environment = {**os.environ, "PDS_OUTPUT_DIR": str(temporary_path)}
        result = subprocess.run(
            ["npm", "run", "sync:pds"],  # noqa: S607
            cwd=web,
            env=environment,
            check=False,
        )
        if result.returncode:
            _finish(result.returncode)
        backup = public / ".pds-sync-backup"
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.replace(backup)
        try:
            temporary_path.replace(target)
        except Exception:
            if backup.exists():
                backup.replace(target)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    _finish(0)


def megalint_clean() -> None:
    """Preview and remove obsolete MegaLinter Docker images."""
    parser = argparse.ArgumentParser(prog="megalint-clean")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    image = load_megalinter_image()
    current = image.tag
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "image",
            "ls",
            "--filter",
            f"reference={image.repository}:*",
            "--format",
            "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        print(result.stderr, file=sys.stderr, end="")  # noqa: T201
        _finish(result.returncode)
    obsolete = [line for line in result.stdout.splitlines() if line.split("\t")[1] != current]
    if not obsolete:
        print(f"No obsolete MegaLinter images found; preserving {current}.")  # noqa: T201
        return
    print("Obsolete MegaLinter images:")  # noqa: T201
    for line in obsolete:
        print(f"  {line}")  # noqa: T201
    if not args.yes and (
        not sys.stdin.isatty() or input("Remove these images? [y/N] ").strip().lower() not in {"y", "yes"}
    ):
        print("No images removed.")  # noqa: T201
        return
    image_ids = list(dict.fromkeys(line.split("\t")[2] for line in obsolete))
    _finish(_run(["docker", "image", "rm", *image_ids]))
