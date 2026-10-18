"""Which CI suites a pull request touches; the one source of the path lists the suites' workflows held (TD-278).

Prints ``suites=<JSON list>`` for ``$GITHUB_OUTPUT``. Without a base commit (a manual run) every suite runs, and a
change to the gate itself runs every suite. Globs follow GitHub's path filters: ``**`` crosses directories, ``*``
and ``?`` do not.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

SUITES: dict[str, tuple[str, ...]] = {
    "python": (
        ".github/workflows/python.yml",
        ".python-version",
        "conftest.py",
        "pyproject.toml",
        "uv.lock",
        "serve/*/pyproject.toml",
        "serve/*/src/**",
        "serve/*/tests/**",
        "tests/**",
        "setup/**",
        "seed/**",
    ),
    "python-browser": (
        ".github/workflows/python-browser.yml",
        ".python-version",
        "conftest.py",
        "pyproject.toml",
        "uv.lock",
        "serve/browser/**",
        "serve/browser-mcp/**",
        "serve/web-content/**",
        "serve/delivery-next/**",
        "serve/memory/**",
    ),
    "cockpit": (
        ".github/workflows/cockpit.yml",
        ".github/scripts/check_node_runtime.py",
        "biome.json",
        "serve/cockpit/web/**",
    ),
    "static": (
        ".github/workflows/static.yml",
        "**/*.py",
        "**/*.json",
        "**/*.jsonc",
        "**/.editorconfig",
        "**/.gitignore",
        "biome.json",
        "pyproject.toml",
        "uv.lock",
        "serve/cockpit/web/**",
    ),
    "tooling": (
        ".github/renovate.json",
        ".github/scripts/**",
        ".github/workflows/**",
        ".mega-linter.yml",
        ".pre-commit-config.yaml",
        ".python-version",
        ".owlbear/scripts/diagrams/**",
        "share/diagrams/**",
        "biome.json",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "serve/*/pyproject.toml",
        "serve/cockpit/web/.nvmrc",
        "serve/cockpit/web/package.json",
        "serve/cockpit/web/package-lock.json",
        "serve/tools/src/owlbear_tools/dependency_ci.py",
        "serve/tools/src/owlbear_tools/megalinter.py",
        "tests/test_archify_diagrams.py",
        "tests/test_dependency_verification_workflow.py",
        "uv.lock",
    ),
    "agent-ecosystem": (
        ".github/workflows/agent-ecosystem.yml",
        ".owlbear/hooks/**",
        ".owlbear/agents/**",
        ".owlbear/instructions/**",
        ".owlbear/prompts/**",
        ".owlbear/scripts/validate_agents.py",
        ".owlbear/scripts/validate_prompts.py",
        ".owlbear/scripts/validate_skills.py",
        ".owlbear/skills/**",
        ".github/scripts/check_uv_version.py",
        ".pre-commit-config.yaml",
        ".vscode/mcp.json",
        "seed/.vscode/mcp.json",
        "serve/*-mcp/**",
        "share/agents/**",
        "share/instructions/**",
        "share/prompts/**",
        "share/skills/**",
        "tests/test_agent_ecosystem_validation.py",
        "tests/test_write_guard_hooks.py",
        "serve/knowledge/**",
        "tests/test_knowledge_ops_contract.py",
    ),
    "security": (  # TD-319: Snyk Code and Open Source on every change to code, manifests or locks
        ".github/workflows/security.yml",
        ".snyk",
        "**/*.py",
        "**/*.js",
        "**/*.mjs",
        "**/*.ts",
        "**/*.tsx",
        "**/*.html",
        "**/pyproject.toml",
        "**/package.json",
        "**/package-lock.json",
        "uv.lock",
    ),
}
GATE = (".github/workflows/ci.yml", ".github/scripts/ci_scope.py")


def pattern(glob: str) -> re.Pattern[str]:
    """The regular expression of one path-filter glob."""
    parts, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            parts.append(".*")
            i += 2
        elif glob[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(parts) + r"\Z")


def suites(paths: list[str]) -> list[str]:
    """The suites whose globs match any changed path; every suite when the gate itself changed."""
    if any(p in GATE for p in paths):
        return list(SUITES)
    return [name for name, globs in SUITES.items() if any(pattern(g).match(p) for g in globs for p in paths)]


def changed(base: str, head: str) -> list[str]:
    """Paths the pull request changes, from the merge base of *base* and *head* to *head*, unquoted by ``-z``."""
    done = subprocess.run(  # noqa: S603 - fixed git argument vector
        ["git", "diff", "--name-only", "-z", f"{base}...{head}"],  # noqa: S607 - git from the runner's PATH
        capture_output=True,
        text=True,
        check=True,
    )
    return [path for path in done.stdout.split("\0") if path]


def main(argv: list[str]) -> None:
    """Print the touched suites for a base and head commit; every suite without a base."""
    names = suites(changed(argv[0], argv[1])) if len(argv) == 2 and argv[0] else list(SUITES)  # noqa: PLR2004
    sys.stdout.write(f"suites={json.dumps(names)}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
