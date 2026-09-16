"""Derive local linter pins from one exact MegaLinter release."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import yaml

if TYPE_CHECKING:
    from collections.abc import Mapping

MANIFEST = "pyproject.toml"
PRE_COMMIT = ".pre-commit-config.yaml"
BIOME_CONFIG = "biome.json"
NPM_MANIFEST = "serve/cockpit/web/package.json"
NPM_LOCK = "serve/cockpit/web/package-lock.json"
MEGALINTER_CONFIG = ".mega-linter.yml"
MEGALINTER_WORKFLOW = ".github/workflows/megalinter.yml"
OUTPUT_PATHS = (MANIFEST, PRE_COMMIT, BIOME_CONFIG, NPM_MANIFEST, "uv.lock", NPM_LOCK)
_VERSION = r"[0-9]+\.[0-9]+\.[0-9]+"
_PATTERNS = {
    MANIFEST: rf"ruff==(?P<version>{_VERSION})",
    PRE_COMMIT: rf"repo: https://github.com/astral-sh/ruff-pre-commit\s+rev: v(?P<version>{_VERSION})",
    BIOME_CONFIG: rf'"\$schema":\s*"https://biomejs.dev/schemas/(?P<version>{_VERSION})/schema.json"',
    NPM_MANIFEST: rf'"@biomejs/biome":\s*"(?P<version>{_VERSION})"',
    MEGALINTER_CONFIG: rf"(?m)^MEGALINTER_VERSION:\s*v(?P<version>{_VERSION})\s*$",
    MEGALINTER_WORKFLOW: (
        r"uses: oxsecurity/megalinter(?:/flavors/(?P<flavor>[a-z0-9-]+))?@"
        rf"(?P<digest>[a-f0-9]{{40}})\s+# v(?P<version>{_VERSION})\b"
    ),
}


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


def _run(root: Path, command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        _fail(f"Required executable is unavailable: {command[0]}")
    result = subprocess.run(  # noqa: S603
        [executable, *command[1:]],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _match(path: str, text: str) -> re.Match[str]:
    matches = list(re.finditer(_PATTERNS[path], text))
    if len(matches) != 1:
        _fail(f"{path} must contain exactly one supported version declaration")
    return matches[0]


def _replace_version(path: str, text: str, version: str) -> str:
    match = _match(path, text)
    return text[: match.start("version")] + version + text[match.end("version") :]


def _read(root: Path, path: str) -> str:
    target = root / path
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        _fail(f"Refusing symlink or out-of-root path: {path}")
    return target.read_text(encoding="utf-8")


def _normalise(path: str, text: str) -> str:
    result = _replace_version(path, text, "0.0.0")
    if path == MEGALINTER_WORKFLOW:
        match = _match(path, result)
        result = result[: match.start("digest")] + "0" * 40 + result[match.end("digest") :]
    return result


def validate_candidate(root: Path, base_ref: str) -> None:
    """Reject non-toolchain edits before running any resolver on PR inputs."""
    if re.fullmatch(r"[a-f0-9]{40}", base_ref) is None:
        _fail("The base reference must be a full commit SHA")
    merge_base = _run(root, ["git", "merge-base", base_ref, "HEAD"]).strip()
    paths = _run(root, ["git", "diff", "--name-only", "-z", merge_base, "HEAD"]).split("\0")
    allowed = {*OUTPUT_PATHS, MEGALINTER_CONFIG, MEGALINTER_WORKFLOW}
    for path in filter(None, paths):
        if path not in allowed:
            _fail(f"Unexpected change in MegaLinter PR: {path}")
        entry = _run(root, ["git", "ls-tree", "HEAD", "--", path])
        if not entry.startswith("100644 blob "):
            _fail(f"Refusing deleted, executable, or symlink input: {path}")
        before = _run(root, ["git", "show", f"{merge_base}:{path}"])
        if path in _PATTERNS and _normalise(path, before) != _normalise(path, _read(root, path)):
            _fail(f"Non-version edits in MegaLinter PR: {path}")
        if path in {"uv.lock", NPM_LOCK}:
            (root / path).write_text(before, encoding="utf-8")


def load_versions(root: Path) -> dict[str, str]:
    """Fetch version metadata for the proposed release, never a moving latest tag."""
    config = yaml.safe_load(_read(root, MEGALINTER_CONFIG))
    native = _match(MEGALINTER_CONFIG, _read(root, MEGALINTER_CONFIG)).group("version")
    action = _match(MEGALINTER_WORKFLOW, _read(root, MEGALINTER_WORKFLOW))
    if native != action.group("version") or config["MEGALINTER_FLAVOR"] != (action.group("flavor") or "all"):
        _fail("Native and action MegaLinter declarations diverge")
    url = (
        f"https://raw.githubusercontent.com/oxsecurity/megalinter/v{native}/.automation/generated/linter-versions.json"
    )
    document = json.loads(
        _run(root, ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "30", url])
    )
    return _validated_versions(document)


def _validated_versions(document: object) -> dict[str, str]:
    if not isinstance(document, dict):
        _fail("MegaLinter version metadata must be an object")
    versions = {}
    for tool in ("ruff", "ruff-format", "biome"):
        version = document.get(tool)
        if not isinstance(version, str) or re.fullmatch(_VERSION, version) is None:
            _fail(f"Missing or invalid MegaLinter {tool} version")
        versions[tool] = version
    if versions["ruff"] != versions["ruff-format"]:
        _fail("MegaLinter Ruff and Ruff formatter versions diverge")
    return versions


def _lock_matches(root: Path, path: str, version: str) -> bool:
    text = _read(root, path)
    if path == "uv.lock":
        packages = tomllib.loads(text)["package"]
        return [package["version"] for package in packages if package["name"] == "ruff"] == [version]
    packages = json.loads(text)["packages"]
    return (
        packages[""]["devDependencies"]["@biomejs/biome"] == version
        and packages["node_modules/@biomejs/biome"]["version"] == version
        and all(
            package["version"] == version
            for name, package in packages.items()
            if name.startswith("node_modules/@biomejs/cli-")
        )
    )


def synchronize(root: Path, metadata: Mapping[str, str], *, check: bool = False) -> None:
    """Update exact pins and stale locks, or report drift without modifying files."""
    versions = _validated_versions(metadata)
    targets = {
        MANIFEST: versions["ruff"],
        PRE_COMMIT: versions["ruff"],
        BIOME_CONFIG: versions["biome"],
        NPM_MANIFEST: versions["biome"],
    }
    updates = {}
    for path, version in targets.items():
        text = _read(root, path)
        updated = _replace_version(path, text, version)
        if text != updated:
            updates[path] = updated
    locks = {
        path
        for path, version in {"uv.lock": versions["ruff"], NPM_LOCK: versions["biome"]}.items()
        if not _lock_matches(root, path, version)
    }
    if check and (updates or locks):
        _fail(f"MegaLinter toolchain drift: {', '.join(sorted(set(updates) | locks))}")
    if PRE_COMMIT in updates:
        _run(
            root,
            [
                "git",
                "ls-remote",
                "--exit-code",
                "--tags",
                "https://github.com/astral-sh/ruff-pre-commit",
                f"refs/tags/v{versions['ruff']}",
            ],
        )
    for path, text in updates.items():
        (root / path).write_text(text, encoding="utf-8")
    if "uv.lock" in locks or MANIFEST in updates:
        _run(root, ["uv", "lock", "--no-build"])
    if NPM_LOCK in locks or NPM_MANIFEST in updates:
        _run(
            root / "serve/cockpit/web",
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"],
        )
    if not check:
        synchronize(root, versions, check=True)


def main() -> int:
    """Synchronize or verify the repository's bundled linter versions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--base-ref")
    args = parser.parse_args()
    try:
        if args.base_ref:
            if args.check:
                parser.error("--check cannot reset PR lockfiles with --base-ref")
            validate_candidate(args.root, args.base_ref)
        versions = load_versions(args.root)
        synchronize(args.root, versions, check=args.check)
        print(f"MegaLinter toolchain aligned: Ruff {versions['ruff']}, Biome {versions['biome']}")
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError, yaml.YAMLError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        parser.error(detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
