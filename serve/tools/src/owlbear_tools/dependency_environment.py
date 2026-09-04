"""Reconcile the checked-out dependency environment."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from owlbear_tools.commands import command_footer
from owlbear_tools.quality_runtime import _require_development

_NODE_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_UV_SYNC = (
    "uv",
    "sync",
    "--locked",
    "--all-packages",
    "--all-extras",
    "--all-groups",
)
_NPM_ROOTS = (
    ("Cockpit npm", Path("serve/cockpit/web")),
    ("Root npm", Path()),
)
_BROWSER_ROOTS = (_NPM_ROOTS[0],)


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Describe one synchronization or status operation."""

    name: str
    status: str
    detail: str = ""
    changes: tuple[dict[str, str], ...] = ()


def _run(
    command: list[str],
    *,
    cwd: Path,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one package-management command."""
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            check=False,
            capture_output=capture,
            text=capture,
            env=env,
        )
    except OSError as error:
        return subprocess.CompletedProcess(command, 2, "", str(error))


def _captured_output(result: subprocess.CompletedProcess[str]) -> str:
    """Combine captured stdout and stderr for one operation."""
    return "\n".join(part for part in (result.stdout or "", result.stderr or "") if part).strip()


def _version(value: str, source: str) -> tuple[int, int, int]:
    """Parse one complete Node version."""
    match = _NODE_VERSION.fullmatch(value.strip())
    if match is None:
        message = f"{source} must contain a complete Node version"
        raise ValueError(message)
    return tuple(int(match.group(index)) for index in range(1, 4))


def _check_node_runtime(root: Path) -> OperationResult:
    """Check the running Node version against the checked-in exact version."""
    version_file = root / "serve/cockpit/web/.nvmrc"
    try:
        expected = _version(version_file.read_text(encoding="utf-8"), str(version_file))
    except (OSError, ValueError) as error:
        return OperationResult("Node runtime", "failed", str(error))
    result = _run(["node", "--version"], cwd=root, capture=True)
    if result.returncode:
        return OperationResult("Node runtime", "failed", _captured_output(result))
    try:
        actual = _version(result.stdout or "", "node --version")
    except ValueError as error:
        return OperationResult("Node runtime", "failed", str(error))
    if actual != expected:
        expected_text = ".".join(str(value) for value in expected)
        actual_text = ".".join(str(value) for value in actual)
        return OperationResult(
            "Node runtime",
            "failed",
            f"running Node {actual_text}; checkout requires {expected_text} from {version_file}",
        )
    return OperationResult("Node runtime", "ok", f"Node {actual[0]}.{actual[1]}.{actual[2]}")


def _selected_npm_roots(*, include_all: bool, include_browsers: bool) -> tuple[tuple[str, Path], ...]:
    """Return npm roots needed by one command profile."""
    if include_all:
        return _NPM_ROOTS
    if include_browsers:
        return _BROWSER_ROOTS
    return _NPM_ROOTS[:1]


def _process_result(name: str, result: subprocess.CompletedProcess[str]) -> OperationResult:
    """Convert one sync process result to a public operation result."""
    return OperationResult(name, "ok" if result.returncode == 0 else "failed")


def _sync_npm(root: Path, name: str, repository: Path) -> OperationResult:
    """Install one npm lockfile exactly."""
    package_root = repository / root
    if not (package_root / "package-lock.json").is_file():
        return OperationResult(name, "failed", f"missing package-lock.json in {package_root}")
    return _process_result(name, _run(["npm", "ci"], cwd=package_root))


def _sync_pds(repository: Path) -> OperationResult:
    """Regenerate checked-in PDS assets transactionally."""
    web = repository / "serve/cockpit/web"
    public = web / "public"
    target = public / "porsche-design-system"
    public.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=public, prefix=".dep-pds-") as temporary:
        temporary_path = Path(temporary)
        result = _run(
            ["npm", "run", "sync:pds"],
            cwd=web,
            env={**os.environ, "PDS_OUTPUT_DIR": str(temporary_path)},
        )
        if result.returncode:
            return _process_result("PDS assets", result)
        temporary_path.chmod(0o755)
        backup = public / ".dep-pds-backup"
        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            target.replace(backup)
        try:
            temporary_path.replace(target)
        except OSError as error:
            if backup.exists() and not target.exists():
                backup.replace(target)
            return OperationResult("PDS assets", "failed", str(error))
        if backup.exists():
            shutil.rmtree(backup)
    return OperationResult("PDS assets", "ok")


def _sync_browsers(root: Path, name: str, repository: Path) -> OperationResult:
    """Install Chromium for one local Playwright package root."""
    package_root = repository / root
    return _process_result(
        name,
        _run(["npx", "--no-install", "playwright", "install", "chromium"], cwd=package_root),
    )


def _sync_results(repository: Path, options: argparse.Namespace) -> list[OperationResult]:
    """Run the selected synchronization operations and aggregate failures."""
    include_all = options.all
    include_browsers = options.browsers or include_all
    npm_roots = _selected_npm_roots(include_all=include_all, include_browsers=include_browsers)
    results = [_process_result("Python workspace", _run(list(_UV_SYNC), cwd=repository))]
    runtime = _check_node_runtime(repository)
    results.append(runtime)
    if runtime.status == "ok":
        results.extend(_sync_npm(path, name, repository) for name, path in npm_roots)
    else:
        results.extend(OperationResult(name, "blocked", "Node runtime check failed") for name, _ in npm_roots)
    if options.pds or include_all:
        results.append(
            _sync_pds(repository)
            if runtime.status == "ok"
            else OperationResult("PDS assets", "blocked", "Node runtime check failed")
        )
    if include_browsers:
        if runtime.status == "ok":
            results.extend(
                _sync_browsers(path, name.replace("npm", "Chromium"), repository) for name, path in _BROWSER_ROOTS
            )
        else:
            results.extend(
                OperationResult(name.replace("npm", "Chromium"), "blocked", "Node runtime check failed")
                for name, _ in _BROWSER_ROOTS
            )
    return results


def _uv_status(repository: Path) -> OperationResult:
    """Check Python lock and installed-environment agreement."""
    lock = _run(["uv", "lock", "--check"], cwd=repository, capture=True)
    if lock.returncode:
        return OperationResult("Python workspace", "lock-drifted", _captured_output(lock))
    result = _run([*list(_UV_SYNC), "--check"], cwd=repository, capture=True)
    status = "in-sync" if result.returncode == 0 else "stale"
    return OperationResult("Python workspace", status, _captured_output(result))


def _npm_changes(payload: object) -> tuple[dict[str, str], ...]:
    """Extract concise package changes from npm's dry-run JSON."""
    if not isinstance(payload, dict):
        return ()
    changes: list[dict[str, str]] = []
    for key, kind in (
        ("add", "add"),
        ("added", "add"),
        ("remove", "remove"),
        ("removed", "remove"),
        ("change", "change"),
        ("changed", "change"),
    ):
        records = payload.get(key)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            name = _npm_package_value(record)
            if name is None:
                name = _npm_package_value(record.get("to")) or _npm_package_value(record.get("from"))
            if not isinstance(name, str):
                continue
            item = {"package": name, "kind": kind}
            for field in ("from", "to"):
                value = _npm_package_version(record.get(field))
                if value is not None:
                    item[field] = value
            changes.append(item)
    return tuple(changes)


def _npm_package_value(value: object) -> str | None:
    """Read a package name from an npm record or nested package object."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    for field in ("name", "package", "id"):
        candidate = value.get(field)
        if isinstance(candidate, str):
            return candidate
    return None


def _npm_package_version(value: object) -> str | None:
    """Read a package version from a flat or nested npm package value."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None
    version = value.get("version")
    return version if isinstance(version, str) else None


def _npm_json(output: str) -> object | None:
    """Extract npm's JSON document from output with human-readable prefixes."""
    decoder = json.JSONDecoder()
    fallback: object | None = None
    for index, character in enumerate(output):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(output, index)
        except json.JSONDecodeError:
            continue
        if fallback is None:
            fallback = payload
        if isinstance(payload, dict) and any(
            key in payload for key in ("add", "added", "change", "changed", "remove", "removed")
        ):
            return payload
    return fallback


def _npm_reports_changes(payload: object) -> bool:
    """Return whether npm reports any package changes by count or record."""
    if not isinstance(payload, dict):
        return False
    for key in ("add", "remove", "change"):
        records = payload.get(key)
        if isinstance(records, list) and records:
            return True
    for key in ("added", "removed", "changed"):
        count = payload.get(key)
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            return True
    return False


def _npm_status(root: Path, name: str, repository: Path) -> OperationResult:
    """Check one npm environment without changing it."""
    package_root = repository / root
    if not (package_root / "package-lock.json").is_file():
        return OperationResult(name, "missing", f"missing package-lock.json in {package_root}")
    result = _run(
        ["npm", "ci", "--dry-run", "--json", "--ignore-scripts"],
        cwd=package_root,
        capture=True,
    )
    output = _captured_output(result)
    if result.returncode:
        return OperationResult(name, "error", output)
    payload = _npm_json(output)
    if payload is None:
        return OperationResult(name, "error", output or "npm dry-run did not return JSON")
    changes = _npm_changes(payload)
    if _npm_reports_changes(payload):
        return OperationResult(name, "stale", "npm dry-run reports changes", changes)
    return OperationResult(name, "in-sync", "npm dry-run reports no changes")


def _tree_files(root: Path) -> dict[str, bytes]:
    """Read one generated asset tree for comparison."""
    if not root.is_dir():
        return {}
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _pds_status(repository: Path) -> OperationResult:
    """Compare generated PDS assets without replacing the checked-in tree."""
    web = repository / "serve/cockpit/web"
    target = web / "public/porsche-design-system"
    with tempfile.TemporaryDirectory(prefix="dep-pds-status-") as temporary:
        generated = Path(temporary)
        result = _run(
            ["npm", "run", "sync:pds"],
            cwd=web,
            env={**os.environ, "PDS_OUTPUT_DIR": str(generated)},
            capture=True,
        )
        if result.returncode:
            return OperationResult("PDS assets", "error", _captured_output(result))
        expected = _tree_files(generated)
    actual = _tree_files(target)
    if expected == actual:
        return OperationResult("PDS assets", "in-sync")
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(path for path in set(expected) & set(actual) if expected[path] != actual[path])
    detail = f"missing={len(missing)}, extra={len(extra)}, changed={len(changed)}"
    return OperationResult("PDS assets", "stale", detail)


def _browser_status(root: Path, name: str, repository: Path) -> OperationResult:
    """Check whether one Playwright Chromium executable exists."""
    package_root = repository / root
    package = "@playwright/test" if root == _NPM_ROOTS[0][1] else "playwright"
    script = f"import {{ chromium }} from '{package}'; console.log(chromium.executablePath());"
    result = _run(
        ["node", "--input-type=module", "-e", script],
        cwd=package_root,
        capture=True,
    )
    if result.returncode:
        return OperationResult(name, "missing", _captured_output(result))
    executable = (result.stdout or "").strip().splitlines()[-1:]
    if not executable:
        return OperationResult(name, "missing", "Playwright returned no Chromium executable path")
    path = Path(executable[0])
    if not path.is_file() or not os.access(path, os.X_OK):
        return OperationResult(name, "missing", f"expected executable: {path}")
    return OperationResult(name, "in-sync", str(path))


def _status_results(repository: Path, options: argparse.Namespace) -> list[OperationResult]:
    """Inspect the selected environment surfaces without mutation."""
    include_all = options.all
    include_browsers = options.browsers or include_all
    npm_roots = _selected_npm_roots(include_all=include_all, include_browsers=include_browsers)
    results = [_uv_status(repository), _check_node_runtime(repository)]
    results.extend(_npm_status(path, name, repository) for name, path in npm_roots)
    if options.pds or include_all:
        results.append(_pds_status(repository))
    if include_browsers:
        results.extend(
            _browser_status(path, name.replace("npm", "Chromium"), repository) for name, path in _BROWSER_ROOTS
        )
    return results


def _add_profile_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared profile flags with short aliases."""
    parser.add_argument("-p", "--pds", action="store_true", help="include Porsche Design System assets")
    parser.add_argument("-b", "--browsers", action="store_true", help="include Playwright Chromium")
    parser.add_argument("-a", "--all", action="store_true", help="include every supported local surface")


def _successful(result: OperationResult) -> bool:
    """Return whether one result represents the requested healthy state."""
    return result.status in {"ok", "in-sync"}


def _print_results(title: str, results: list[OperationResult], *, verbose: bool) -> None:
    """Print a human-readable operation summary."""
    print(title)  # noqa: T201
    for result in results:
        line = f"- {result.name}: {result.status}"
        if result.changes:
            changes = ", ".join(
                f"{item['package']} {item.get('from', 'missing')} -> {item.get('to', 'removed')}"
                for item in result.changes
            )
            line += f" ({changes})"
        print(line)  # noqa: T201
        if verbose and result.detail:
            print(f"  {result.detail}")  # noqa: T201


def _print_recommendation(*, include_all: bool) -> None:
    """Recommend the complete local setup when it was not selected."""
    if not include_all:
        print("For the most complete local setup, run:")  # noqa: T201
        print("  uv run dep-sync --all")  # noqa: T201


def _finish(exit_code: int) -> None:
    """Print the command discovery footer and exit."""
    print(command_footer(), file=sys.stderr)  # noqa: T201
    raise SystemExit(exit_code)


def dep_sync() -> None:
    """Synchronize selected dependency and runtime surfaces."""
    parser = argparse.ArgumentParser(prog="dep-sync")
    _add_profile_arguments(parser)
    options = parser.parse_args()
    _require_development("dep-sync")
    results = _sync_results(Path.cwd(), options)
    _print_results("Dependency environment synchronization", results, verbose=False)
    print("Manifests and lockfiles were not changed.")  # noqa: T201
    _print_recommendation(include_all=options.all)
    _finish(0 if all(_successful(result) for result in results) else 1)


def dep_status() -> None:
    """Report whether selected dependency and runtime surfaces match the checkout."""
    parser = argparse.ArgumentParser(prog="dep-status")
    _add_profile_arguments(parser)
    parser.add_argument("-v", "--verbose", action="store_true", help="show native check details")
    parser.add_argument("-j", "--json", action="store_true", help="write machine-readable JSON")
    options = parser.parse_args()
    _require_development("dep-status")
    results = _status_results(Path.cwd(), options)
    exit_code = 0 if all(_successful(result) for result in results) else 1
    if options.json:
        document = {
            "command": "dep-status",
            "all": options.all,
            "results": [asdict(result) for result in results],
            "recommendation": None if options.all else "uv run dep-sync --all",
        }
        print(json.dumps(document, indent=2))  # noqa: T201
    else:
        _print_results("Dependency environment status", results, verbose=options.verbose)
        _print_recommendation(include_all=options.all)
    _finish(exit_code)
