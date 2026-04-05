"""Tests for task #117: Delete .github/skills/ and remove dual-path settings.

Contract-level verification that ALL .github/skills/ dual-path references are
removed from every affected file after cleanup.

AC coverage:
  - AC1:  .github/skills/ directory is deleted
  - AC2:  .vscode/settings.json chat.agentSkillsLocations has no .github/skills entry
  - AC3:  scripts/setup.py generates no .github/skills path in agentSkillsLocations
  - AC4:  tests/test_monorepo_skeleton.py has no .github/skills assertion
  - AC5:  tests/test_setup_script.py has no .github/skills assertion
  - AC6:  tests/test_copy_skills_to_root.py is deleted (obsolete)
  - AC7:  tests/test_skill_sync_131.py is deleted (obsolete)
  - AC8:  docs/decisions/README.md references skills/ not .github/skills/
  - AC9:  All 22 skills load from skills/ only (implicit: AC1+AC2+AC3 remove .github/skills
          as a registered location; test_validate_skills_ci.py is the explicit gate)

All tests fail against the pre-cleanup state (current HEAD) and pass once task #117
is complete.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


class TestFromAC_GithubSkillsDirDeleted:
    """AC1: .github/skills/ directory must not exist after cleanup."""

    def test_github_skills_directory_does_not_exist(self) -> None:
        """.github/skills/ must be entirely deleted — no subdirectory, no files."""
        assert not (_REPO_ROOT / ".github" / "skills").exists(), (
            ".github/skills/ directory still exists — task #117 must delete it entirely"
        )


class TestFromAC_VscodeSettingsNoDualPath:
    """AC2: .vscode/settings.json must not reference .github/skills in agentSkillsLocations."""

    def _settings_text(self) -> str:
        return (_REPO_ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")

    def test_settings_json_no_github_skills_entry(self) -> None:
        """chat.agentSkillsLocations in .vscode/settings.json must not include .github/skills."""
        content = self._settings_text()
        assert ".github/skills" not in content, (
            ".vscode/settings.json still contains a .github/skills entry "
            "(line 37) — must be removed"
        )


class TestFromAC_SetupPyNoDualPath:
    """AC3: scripts/setup.py must not generate the .github/skills agentSkillsLocations path."""

    def _setup_py_text(self) -> str:
        return (_REPO_ROOT / "scripts" / "setup.py").read_text(encoding="utf-8")

    def test_setup_py_no_github_skills_reference(self) -> None:
        """scripts/setup.py must not contain a .github/skills key in agentSkillsLocations."""
        content = self._setup_py_text()
        assert ".github/skills" not in content, (
            "scripts/setup.py still contains a .github/skills reference "
            "(line 36) — must be removed"
        )


class TestFromAC_MonorepoTestUpdated:
    """AC4: test_monorepo_skeleton.py must not assert .github/skills presence."""

    def _monorepo_test_text(self) -> str:
        return (_REPO_ROOT / "tests" / "test_monorepo_skeleton.py").read_text(encoding="utf-8")

    def test_monorepo_skeleton_no_github_skills_assertion(self) -> None:
        """test_monorepo_skeleton.py must not contain a .github/skills assertion."""
        content = self._monorepo_test_text()
        assert ".github/skills" not in content, (
            "tests/test_monorepo_skeleton.py still asserts .github/skills presence "
            "(lines 273-278 — test_vscode_settings_agent_skills_locations_github_skills) "
            "— that test method must be removed"
        )


class TestFromAC_SetupScriptTestUpdated:
    """AC5: test_setup_init.py (replacement for test_setup_script.py) must not expect a .github/skills path."""

    def _setup_script_test_text(self) -> str:
        return (_REPO_ROOT / "tests" / "test_setup_init.py").read_text(encoding="utf-8")

    def test_setup_script_no_github_skills_assertion(self) -> None:
        """test_setup_init.py must not assert that agentSkillsLocations has a .github/skills key."""
        content = self._setup_script_test_text()
        assert ".github/skills" not in content, (
            "tests/test_setup_init.py still contains a .github/skills assertion "
            "— the has_github assertion must be removed"
        )


class TestFromAC_ObsoleteTestFilesDeleted:
    """AC6, AC7: Obsolete test files that read from .github/skills/ must be deleted."""

    def test_copy_skills_to_root_deleted(self) -> None:
        """tests/test_copy_skills_to_root.py must not exist (validated task #115, now obsolete)."""
        assert not (_REPO_ROOT / "tests" / "test_copy_skills_to_root.py").exists(), (
            "tests/test_copy_skills_to_root.py still exists — it reads from .github/skills/ "
            "and must be deleted once that directory is gone"
        )

    def test_skill_sync_131_deleted(self) -> None:
        """tests/test_skill_sync_131.py must not exist (validated task #131, now obsolete)."""
        assert not (_REPO_ROOT / "tests" / "test_skill_sync_131.py").exists(), (
            "tests/test_skill_sync_131.py still exists — it reads from .github/skills/ "
            "and must be deleted once that directory is gone"
        )


class TestFromAC_DecisionsReadmeUpdated:
    """AC8: docs/decisions/README.md must reference skills/ not .github/skills/."""

    def _readme_text(self) -> str:
        return (_REPO_ROOT / ".owlbear" / "decisions" / "README.md").read_text(encoding="utf-8")

    def test_decisions_readme_no_github_skills_ref(self) -> None:
        """docs/decisions/README.md must not reference .github/skills/ (line 49)."""
        content = self._readme_text()
        assert ".github/skills" not in content, (
            "docs/decisions/README.md still references .github/skills/ "
            "(line 49: See `.github/skills/w-decision-routing/SKILL.md`) "
            "— must be updated to reference .github/skills/w-decision-routing/SKILL.md"
        )
