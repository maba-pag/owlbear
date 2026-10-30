"""Which CI suites a pull request touches; the one source of the path lists the suites' workflows held (TD-278).

Prints ``suites=<JSON list>`` for ``$GITHUB_OUTPUT``. Without a base commit (a manual run) every suite runs, and a
change to the gate itself runs every suite. Globs follow GitHub's path filters: ``**`` crosses directories, ``*``
and ``?`` do not.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HOME = "maba-pag/owlbear"  # Snyk's token reaches only changes from OwlBear's own repository (TD-363)
SUITES: dict[str, tuple[str, ...]] = {
    "python": (
        ".github/workflows/python.yml",
        ".github/scripts/ci_shard.py",
        ".github/scripts/flaky_issues.py",
        ".python-version",
        "conftest.py",
        "pyproject.toml",
        "uv.lock",
        "serve/*/pyproject.toml",
        "serve/*/src/**",
        "serve/*/tests/**",
        "tests/**",
    ),
    "python-browser": (
        ".github/workflows/python-browser.yml",
        ".github/scripts/ci_shard.py",
        ".github/scripts/flaky_issues.py",
        ".python-version",
        "conftest.py",
        "serve/tools/src/owlbear_tools/flaky.py",
        "pyproject.toml",
        "uv.lock",
        "serve/browser/**",
        "serve/browser-mcp/**",
        "serve/web-content/**",
        "serve/delivery-next/**",
        "serve/decisions/**",
        "serve/memory/**",
    ),
    "static": ("**",),  # `uv run lint` checks every text file, EditorConfig included
    "tooling": (
        "renovate.json",
        ".github/scripts/**",
        ".github/workflows/**",
        ".pre-commit-config.yaml",
        ".python-version",
        ".nvmrc",
        "biome.json",
        "package.json",
        "package-lock.json",
        "pyproject.toml",
        "serve/*/pyproject.toml",
        "serve/tools/src/owlbear_tools/dependency_ci.py",
        "tests/test_dependency_verification_workflow.py",
        "uv.lock",
    ),
    "agent-ecosystem": (
        ".github/workflows/agent-ecosystem.yml",
        ".owlbear/agents/**",
        ".owlbear/instructions/**",
        ".owlbear/scripts/validate_agents.py",
        ".owlbear/scripts/validate_skills.py",
        ".owlbear/skills/**",
        ".github/scripts/check_uv_version.py",
        ".pre-commit-config.yaml",
        ".mcp.json",
        "serve/*-mcp/**",
        "share/agents/**",
        "share/instructions/**",
        "share/skills/**",
        "tests/test_agent_ecosystem_validation.py",
        "serve/knowledge/**",
        "tests/test_knowledge_ops_contract.py",
    ),
    "security": (  # TD-382: Snyk Code on every change to code; .snyk can exclude paths from it
        ".github/workflows/security.yml",
        ".snyk",
        "**/*.py",
        "**/*.js",
        "**/*.mjs",
        "**/*.ts",
        "**/*.tsx",
        "**/*.html",
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


def tokened() -> bool:
    """Whether GitHub gives this run Snyk's token: OwlBear's own run of a change from OwlBear itself (TD-363)."""
    if os.environ.get("GITHUB_REPOSITORY", HOME) != HOME:
        return False
    return os.environ.get("EVENT") != "pull_request" or os.environ.get("SOURCE_REPOSITORY") == HOME


def main(argv: list[str]) -> None:
    """Print the touched suites for a base and head commit; every suite without a base."""
    names = suites(changed(argv[0], argv[1])) if len(argv) == 2 and argv[0] else list(SUITES)  # noqa: PLR2004
    if not tokened():
        names = [name for name in names if name != "security"]
    sys.stdout.write(f"suites={json.dumps(names)}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
