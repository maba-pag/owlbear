"""Failing tests for task #1340: set coherent Python runtime floor and Renovate policy.

AC1: Audit every synced Python package under serve/* for Python 3.13+ syntax/features
     AND for dependencies whose own requires-python floor exceeds 3.12.
AC2: If no justified newer-language feature found, all synced serve/*/pyproject.toml
     must set requires-python = ">=3.12".
AC3: If newer floor IS justified, document the feature and align all prerequisite refs.
     (Conditional — only applies when AC1 finds a justification; AC4 applies otherwise.)
AC4: .python-version, package metadata, README.md, README-consumer.md,
     setup/setup-guide.md aligned to Python 3.12.
AC5: .github/renovate.json has a Python floor-freeze package rule.
"""

from __future__ import annotations

import json
import re
import pathlib
import tomllib

_ROOT = pathlib.Path()
_PYTHON_VERSION_FILE = _ROOT / ".python-version"
_RENOVATE_JSON = _ROOT / ".github" / "renovate.json"

# All synced Python packages under serve/
_SYNCED_PACKAGES: dict[str, pathlib.Path] = {
    "browser": _ROOT / "serve/browser/pyproject.toml",
    "cockpit": _ROOT / "serve/cockpit/pyproject.toml",
    "kanban": _ROOT / "serve/kanban/pyproject.toml",
    "knowledge": _ROOT / "serve/knowledge/pyproject.toml",
    "mcp-browser": _ROOT / "serve/mcp-browser/pyproject.toml",
    "mcp-kanban": _ROOT / "serve/mcp-kanban/pyproject.toml",
    "mcp-knowledge": _ROOT / "serve/mcp-knowledge/pyproject.toml",
    "mcp-memory": _ROOT / "serve/mcp-memory/pyproject.toml",
    "tools": _ROOT / "serve/tools/pyproject.toml",
}

# Source dirs for syntax scanning (AC1)
_SYNCED_SOURCES: dict[str, pathlib.Path] = {
    "browser": _ROOT / "serve/browser/src/owlbear_browser",
    "cockpit": _ROOT / "serve/cockpit/src/owlbear_cockpit",
    "kanban": _ROOT / "serve/kanban/src/owlbear_kanban",
    "knowledge": _ROOT / "serve/knowledge/src/owlbear_knowledge",
    "mcp-browser": _ROOT / "serve/mcp-browser/src/owlbear_mcp_browser",
    "mcp-kanban": _ROOT / "serve/mcp-kanban/src/owlbear_mcp_kanban",
    "mcp-knowledge": _ROOT / "serve/mcp-knowledge/src/owlbear_mcp_knowledge",
    "mcp-memory": _ROOT / "serve/mcp-memory/src/owlbear_mcp_memory",
    "tools": _ROOT / "serve/tools/src/owlbear_tools",
}

# Python 3.13+/3.14+ exclusive feature patterns (broad audit)
_PY313_PLUS_PATTERNS = [
    r"\bTypeIs\b",  # PEP 742 — typing.TypeIs (Python 3.13+)
    r"\btyping\.ReadOnly\b",  # PEP 705 — typing.ReadOnly (Python 3.13+)
    r"\btyping\.deprecated\b",  # PEP 702 — typing.deprecated (Python 3.13+)
    r"\bwarnings\.deprecated\b",  # PEP 702 — warnings.deprecated (Python 3.13+)
    r"\bTypeForm\b",  # PEP 747 — typing.TypeForm (Python 3.14+)
]

# Prerequisite doc files that must state the Python 3.12 floor (AC4)
_PREREQUISITE_DOCS: dict[str, pathlib.Path] = {
    "README.md": _ROOT / "README.md",
    "README-consumer.md": _ROOT / "README-consumer.md",
    "setup/setup-guide.md": _ROOT / "setup/setup-guide.md",
    "owlbear-system.instructions.md": _ROOT / "share/instructions/owlbear-system.instructions.md",
}

_UV_LOCK = _ROOT / "uv.lock"


def _read_requires_python(path: pathlib.Path) -> str:
    with path.open("rb") as f:
        return tomllib.load(f)["project"]["requires-python"]


def _has_313_plus_features(src_dir: pathlib.Path) -> bool:
    """Return True if any .py file in src_dir uses Python 3.13+ exclusive syntax."""
    for py_file in src_dir.rglob("*.py"):
        text = py_file.read_text()
        for pattern in _PY313_PLUS_PATTERNS:
            if re.search(pattern, text):
                return True
    return False


class TestFromAC_PythonVersionAlignment:
    """AC4: .python-version must align to the project-wide Python 3.12 floor."""

    def test_python_version_file_says_3_12(self) -> None:
        content = _PYTHON_VERSION_FILE.read_text().strip()
        assert content.startswith("3.12"), (
            f".python-version contains {content!r} — must be '3.12' (or '3.12.x') "
            "to align with the project-wide Python 3.12 floor (AC4)."
        )


class TestFromAC_RenovatePythonPolicy:
    """AC5: .github/renovate.json must have a Python floor-freeze package rule."""

    def test_renovate_has_python_package_rule(self) -> None:
        data = json.loads(_RENOVATE_JSON.read_text())
        rules = data.get("packageRules", [])
        python_rules = [r for r in rules if "python" in r.get("matchPackageNames", [])]
        assert python_rules, (
            "No Renovate package rule targeting the 'python' package found in "
            ".github/renovate.json — AC5 requires a rule that suppresses automated "
            "Python floor-update churn."
        )

    def test_renovate_python_rule_has_allowed_versions(self) -> None:
        data = json.loads(_RENOVATE_JSON.read_text())
        rules = data.get("packageRules", [])
        python_rules = [r for r in rules if "python" in r.get("matchPackageNames", [])]
        has_allowed_versions = any("allowedVersions" in r for r in python_rules)
        assert has_allowed_versions, (
            "No Renovate python rule with 'allowedVersions' found — "
            "AC5 requires a rule that limits automated Python floor changes "
            "(e.g., 'allowedVersions': '<3.13.0')."
        )

    def test_renovate_python_rule_targets_pep621_or_uv_manager(self) -> None:
        data = json.loads(_RENOVATE_JSON.read_text())
        rules = data.get("packageRules", [])
        python_rules = [r for r in rules if "python" in r.get("matchPackageNames", [])]
        relevant_managers = {"pep621", "uv"}
        has_relevant_manager = any(bool(set(r.get("matchManagers", [])) & relevant_managers) for r in python_rules)
        assert has_relevant_manager, (
            "No Renovate python rule targets 'pep621' or 'uv' managers — "
            "AC5 requires matchManagers to include 'pep621' or 'uv' so the rule "
            "actually applies to pyproject.toml requires-python updates."
        )


class TestFromAC_PrerequisiteDocsAlignment:
    """AC4: Consumer-facing prerequisite docs must state the Python 3.12 floor."""

    def test_readme_states_python_3_12_floor(self) -> None:
        content = (_ROOT / "README.md").read_text()
        assert re.search(r"Python 3\.12", content), (
            "README.md does not mention 'Python 3.12' — AC4 requires all "
            "consumer-facing prerequisite docs to be aligned to the Python 3.12 floor."
        )

    def test_readme_consumer_states_python_3_12_floor(self) -> None:
        content = (_ROOT / "README-consumer.md").read_text()
        assert re.search(r"Python 3\.12", content), (
            "README-consumer.md does not mention 'Python 3.12' — AC4 requires all "
            "consumer-facing prerequisite docs to be aligned to the Python 3.12 floor."
        )

    def test_setup_guide_states_python_3_12_floor(self) -> None:
        content = (_ROOT / "setup/setup-guide.md").read_text()
        assert re.search(r"Python 3\.12", content), (
            "setup/setup-guide.md does not mention 'Python 3.12' — AC4 requires all "
            "consumer-facing prerequisite docs to be aligned to the Python 3.12 floor."
        )

    def test_system_instructions_states_python_3_12_floor(self) -> None:
        content = (_ROOT / "share/instructions/owlbear-system.instructions.md").read_text()
        assert re.search(r"Python 3\.12", content), (
            "share/instructions/owlbear-system.instructions.md does not mention "
            "'Python 3.12' — AC4 requires this synced prerequisite reference to be "
            "aligned to the Python 3.12 floor."
        )
