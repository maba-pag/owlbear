"""Canonical, commit-bound changes to owner-controlled lint, CI and hook configuration."""

from __future__ import annotations

import configparser
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_quality import trees

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

WHOLE = frozenset(
    {
        ".pre-commit-config.yaml",
        "ruff.toml",
        ".ruff.toml",
        "biome.json",
        "biome.jsonc",
        ".editorconfig",
        ".eslintignore",
        ".prettierignore",
        ".stylelintignore",
        ".markdownlint-cli2.jsonc",
        ".yamllint.yml",
        "lefthook.yml",
    }
)
LINTERS = re.compile(r"^\.(?:eslintrc|prettierrc|stylelintrc)(?:\..*)?$|^(?:eslint|prettier|stylelint)\.config\.\w+$")
TABLES = ("ruff", "mypy", "pyright", "pylint", "flake8", "isort", "black")
SECTIONS = ("flake8", "mypy", "isort", "pycodestyle")
KEYS = ("eslintConfig", "prettier", "stylelint", "lint-staged", "husky")


@dataclass(frozen=True)
class Protected:
    """The complete canonical before/after evidence and its approval digest."""

    text: str
    digest: str
    paths: tuple[str, ...]


def _scripts(scripts: dict, commands: Sequence[Sequence[str]], prefixes: tuple[str, ...]) -> dict:
    invoked = {PurePosixPath(arg).name for command in commands for arg in command if not arg.startswith("-")}
    return {k: v for k, v in scripts.items() if k.startswith(prefixes) or k in invoked}


def _parts(path: str, text: str, commands: Sequence[Sequence[str]]) -> object:
    name = PurePosixPath(path).name
    if name == "pyproject.toml":
        data = tomllib.loads(text)
        tool = data.get("tool", {})
        parts = {f"tool.{k}": tool[k] for k in TABLES if k in tool}
        if scripts := _scripts(data.get("project", {}).get("scripts", {}), commands, ("lint", "format", "quality")):
            parts["project.scripts"] = scripts
        return parts
    if name == "package.json":
        data = json.loads(text)
        parts = {k: data[k] for k in KEYS if k in data}
        if scripts := _scripts(data.get("scripts", {}), commands, ("lint", "format")):
            parts["scripts"] = scripts
        return parts
    if name in {"setup.cfg", "tox.ini"}:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(text)
        return {s: dict(parser[s]) for s in SECTIONS if parser.has_section(s)}
    return text


def _protected(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        p.name in WHOLE
        or bool(LINTERS.match(p.name))
        or any(part in {".husky", ".githooks"} for part in p.parts[:-1])
        or path.startswith(".github/workflows/")
        or p.name in {"pyproject.toml", "package.json", "setup.cfg", "tox.ini"}
    )


def protected(
    repo: Path,
    base: str,
    head: str,
    commands: Sequence[Sequence[str]] = (),
) -> Protected | None:
    """Compare protected data in two commits; dependency-only edits produce no change."""
    before, after = trees.files(repo, base), trees.files(repo, head)
    changes = {}
    for path in sorted(before.keys() | after.keys()):
        if not _protected(path) or before.get(path) == after.get(path):
            continue
        old, new = [
            _parts(path, trees.blob(repo, tree[path]), commands) if path in tree else None for tree in (before, after)
        ]
        # An absent shared file and one with no protected keys both hold no protected configuration.
        shared = PurePosixPath(path).name in {"pyproject.toml", "package.json", "setup.cfg", "tox.ini"}
        if old != new and (not shared or old or new):
            changes[path] = {"before": old, "after": new}
    if not changes:
        return None
    text = json.dumps(changes, sort_keys=True, indent=2, ensure_ascii=False, default=str)
    return Protected(text, hashlib.sha256(text.encode()).hexdigest(), tuple(changes))
