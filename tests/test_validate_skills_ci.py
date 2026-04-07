"""Failing tests for task #44: skills-ref CI integration.

Covers:
  - AC1: skills-ref==0.1.1 listed in dependency-groups.validation in pyproject.toml
  - AC3: repo: local pre-commit hook with id: validate-skills in .pre-commit-config.yaml
  - AC4: all skills/*/ directories pass the filtered validator (exit 0)

These tests fail on current HEAD because:
  - AC1: skills-ref is absent from pyproject.toml [dependency-groups.validation]
  - AC3: .pre-commit-config.yaml has no validate-skills hook entry
  - AC4: skills-ref is not installed, so the script exits non-zero
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

# ---------------------------------------------------------------------------
# Repo-level paths — resolved relative to this test file
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_PRECOMMIT_CONFIG = _REPO_ROOT / ".pre-commit-config.yaml"
_SCRIPT = _REPO_ROOT / "scripts" / "validate_skills.py"
_SKILLS_DIR = _REPO_ROOT / "share" / "skills"


# ---------------------------------------------------------------------------
# TestFromAC_ValidationDependency
# ---------------------------------------------------------------------------
class TestFromAC_ValidationDependency:
    """AC1: skills-ref==0.1.1 is listed as a validation dependency in pyproject.toml."""

    def _validation_deps(self) -> list[str]:
        with _PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        return [
            str(dep) for dep in data.get("dependency-groups", {}).get("validation", [])
        ]

    def test_skills_ref_present_in_validation_group(self) -> None:
        """AC1: skills-ref entry exists in [dependency-groups.validation]."""
        deps = self._validation_deps()
        assert any("skills-ref" in dep for dep in deps), (
            f"skills-ref not found in [dependency-groups.validation]. "
            f"Current validation deps: {deps}"
        )

    def test_skills_ref_pinned_to_exact_version_0_1_1(self) -> None:
        """AC1: the entry is an exact pin to 0.1.1, not a range or other version."""
        deps = self._validation_deps()
        matching = [dep for dep in deps if "skills-ref" in dep]
        assert matching, "skills-ref not in validation deps"
        dep_str = matching[0]
        assert "==0.1.1" in dep_str, (
            f"Expected exact pin skills-ref==0.1.1, got: {dep_str!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_PreCommitHook
# ---------------------------------------------------------------------------
class TestFromAC_PreCommitHook:
    """AC3: .pre-commit-config.yaml has a repo: local hook with id: validate-skills."""

    def _precommit_text(self) -> str:
        return _PRECOMMIT_CONFIG.read_text(encoding="utf-8")

    def test_validate_skills_hook_id_present(self) -> None:
        """AC3: id: validate-skills line exists in .pre-commit-config.yaml."""
        content = self._precommit_text()
        assert "validate-skills" in content, (
            "No 'validate-skills' hook id found in .pre-commit-config.yaml"
        )

    def test_validate_skills_under_local_repo(self) -> None:
        """AC3: the validate-skills hook is under a repo: local entry."""
        content = self._precommit_text()
        # Find the block containing 'validate-skills' and verify it's preceded
        # by a 'repo: local' entry (not a remote repo).
        lines = content.splitlines()
        found_local_repo = False
        for line in lines:
            if "repo: local" in line:
                found_local_repo = True
            if found_local_repo and "validate-skills" in line:
                return  # hook present under repo: local
        msg = "validate-skills hook not found under a 'repo: local' section"
        raise AssertionError(msg)

    def test_validate_skills_hook_entry_references_script(self) -> None:
        """AC3: the hook entry command references the validate_skills.py script."""
        content = self._precommit_text()
        # The entry line for the hook must reference the script path.
        assert "validate_skills" in content, (
            "No reference to validate_skills script found in .pre-commit-config.yaml"
        )


# ---------------------------------------------------------------------------
# TestFromAC_IntegrationAllSkills
# ---------------------------------------------------------------------------
class TestFromAC_IntegrationAllSkills:
    """AC4: all skills/*/ directories pass the filtered validator (exit 0).

    This test is gated on the pre-commit hook being configured (AC3).
    Until the hook entry is added, it fails at the AC3 assertion.
    Once AC3 is done, it verifies the 22 real skills all pass the script.
    """

    def test_all_current_skills_pass_with_hook_configured(self) -> None:
        """AC4: hook is configured AND all 22 skills/ dirs pass with exit 0."""
        # Gate: pre-commit config must have the hook (AC3 must be done first)
        content = _PRECOMMIT_CONFIG.read_text(encoding="utf-8")
        assert "validate-skills" in content, (
            "validate-skills hook missing from .pre-commit-config.yaml — "
            "AC3 must be complete before AC4 can be verified"
        )
        # Integration: script must exit 0 on all real skill dirs
        skill_dirs = sorted(d for d in _SKILLS_DIR.iterdir() if d.is_dir())
        assert len(skill_dirs) >= 22, (
            f"Expected at least 22 skill dirs, found {len(skill_dirs)}"
        )
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), *[str(d) for d in skill_dirs]],
            capture_output=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"Validation failed (exit {result.returncode}).\n"
            f"stderr:\n{result.stderr.decode('utf-8', errors='replace')}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_AutoDiscovery  (retry: AC2a gap — no auto-discovery test existed)
# ---------------------------------------------------------------------------
class TestFromAC_AutoDiscovery:
    """AC2a: script invoked with no args discovers skills/*/ dirs automatically."""

    def test_script_auto_discovers_skill_directories(self) -> None:
        """AC2a: no-arg invocation uses auto-discovery — not a usage error."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_REPO_ROOT),
        )
        stderr = result.stderr.decode("utf-8", errors="replace")
        assert "Usage:" not in stderr, (
            "Script printed a Usage error instead of auto-discovering skill directories.\n"
            f"stderr: {stderr}"
        )

    def test_auto_discovery_exits_zero_for_valid_skills(self) -> None:
        """AC2a+AC4: script with no args discovers all valid skills and exits 0."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"Expected exit 0 after auto-discovery of valid skills. "
            f"exit={result.returncode}\n"
            f"stderr:\n{result.stderr.decode('utf-8', errors='replace')}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_PreCommitIntegration  (retry: AC4 gap — prior test used direct
# invocation, not pre-commit; identified as LAX by reviewer)
# ---------------------------------------------------------------------------
class TestFromAC_PreCommitIntegration:
    """AC4: actual pre-commit hook invocation exits 0 for all current skills."""

    def test_pre_commit_validate_skills_exits_zero(self) -> None:
        """AC4: pre-commit run validate-skills --all-files exits 0."""
        result = subprocess.run(
            ["uv", "run", "pre-commit", "run", "validate-skills", "--all-files"],
            capture_output=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"pre-commit run validate-skills --all-files failed "
            f"(exit {result.returncode}).\n"
            f"stdout:\n{result.stdout.decode('utf-8', errors='replace')}\n"
            f"stderr:\n{result.stderr.decode('utf-8', errors='replace')}"
        )
