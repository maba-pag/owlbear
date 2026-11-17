"""Canonical, commit-bound changes to owner-controlled lint, CI and hook configuration."""

from __future__ import annotations

import configparser
import hashlib
import json
import posixpath
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
        "mypy.ini",
        ".mypy.ini",
        "pyrightconfig.json",
        "pylintrc",
        ".pylintrc",
        ".flake8",
        ".isort.cfg",
    }
)
LINTERS = re.compile(
    r"^\.(?:eslintrc|prettierrc|stylelintrc)(?:\..*)?$|^(?:eslint|prettier|stylelint)\.config\.\w+$"
    r"|^\.yamllint(?:\.ya?ml)?$|^\.markdownlint(?:-cli2)?\.(?:jsonc?|ya?ml|[cm]js)$"
)
TABLES = ("ruff", "mypy", "pyright", "pylint", "flake8", "isort", "black")
SECTIONS = ("flake8", "mypy", "isort", "pycodestyle")
KEYS = ("eslintConfig", "prettier", "stylelint", "lint-staged", "husky")


@dataclass(frozen=True)
class Protected:
    """The complete canonical before/after evidence and its approval digest."""

    text: str
    digest: str
    paths: tuple[str, ...]


def _invoked(command: Sequence[str]) -> str:
    executable = PurePosixPath(command[0]).name
    wrappers = {"uv", "npm", "pnpm", "yarn", "bun", "poetry", "pdm"}
    if executable not in wrappers:
        return executable
    marker = next((i for i, word in enumerate(command) if word in {"run", "run-script"}), None)
    if marker is None and executable not in {"npm", "pnpm", "yarn", "bun"}:
        return ""
    words = iter(command[(marker + 1) if marker is not None else 1 :])
    with_value = {
        "--project",
        "--directory",
        "--package",
        "--python",
        "-p",
        "--with",
        "--with-editable",
        "--with-requirements",
        "--group",
        "--extra",
        "--env-file",
        "--workspace",
        "-w",
    }
    for word in words:
        if word in with_value:
            next(words, None)
        elif not word.startswith("-"):
            return word
    return ""


def _scripts(scripts: dict, commands: Sequence[Sequence[str]], prefixes: tuple[str, ...]) -> dict:
    invoked = {_invoked(command) for command in commands if command}
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
        return {s: dict(parser[s]) for s in parser.sections() if s in SECTIONS or s.startswith("mypy-")}
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


def _target(path: str, link: str, tree: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    """The tracked regular file a protected link names inside the repository, with its blob, if there is one."""
    at = posixpath.normpath(posixpath.join(posixpath.dirname(path), link))
    entry = tree.get(at)
    return (at, entry[1]) if entry and entry[0] in {"100644", "100755"} else None


def _content(
    run: trees.Git, repo: Path, path: str, tree: dict[str, tuple[str, str]], commands: Sequence[Sequence[str]]
) -> object:
    entry = tree.get(path)
    if entry is None:
        return None
    mode, oid = entry
    source = trees.blob(run, repo, oid)
    if mode == "120000":  # the link is configuration, and so is the tracked file it names
        aim = _target(path, source, tree)
        return {"symlink": source, "target": trees.blob(run, repo, aim[1]) if aim else None}
    try:
        data = _parts(path, source, commands)
    except tomllib.TOMLDecodeError, json.JSONDecodeError, configparser.Error, AttributeError, TypeError:
        # A file that does not parse, or parses to another shape, is compared whole: no part can be told apart.
        data = source
    if not data and PurePosixPath(path).name in {"pyproject.toml", "package.json", "setup.cfg", "tox.ini"}:
        return None
    return {"mode": mode, "content": data}


def protected(
    run: trees.Git,
    repo: Path,
    base: str,
    head: str,
    commands: Sequence[Sequence[str]] = (),
) -> Protected | None:
    """Compare protected data in two commits; dependency-only edits produce no change."""
    before, after = trees.entries(run, repo, base), trees.entries(run, repo, head)
    changes, paths = {}, set()
    for path in sorted(before.keys() | after.keys()):
        entries = before.get(path), after.get(path)
        linked = any(e is not None and e[0] == "120000" for e in entries)
        if not _protected(path) or (entries[0] == entries[1] and not linked):
            continue
        old, new = [_content(run, repo, path, tree, commands) for tree in (before, after)]
        if old != new:
            changes[path] = {"before": old, "after": new}
            aims = [_target(path, c["symlink"], t) for c, t in ((old, before), (new, after)) if c and "symlink" in c]
            paths |= {path, *(aim[0] for aim in aims if aim)}
    if not changes:
        return None
    text = json.dumps(changes, sort_keys=True, indent=2, ensure_ascii=False, default=str)
    return Protected(text, hashlib.sha256(text.encode()).hexdigest(), tuple(sorted(paths)))
