"""Failing tests for task #84: skills-ref validation script filter logic.

Covers:
  - AC1: spec-compliant skill passes validation with no errors
  - AC2: VS Code vendor fields (user-invocable, argument-hint,
    disable-model-invocation) are filtered — no error returned
  - AC3: real spec errors (missing description, invalid name) survive the
    filter and are still reported
  - AC4: script exits 0 when all skills pass, exits 1 when any real error
    remains

All tests fail on current HEAD because scripts/validate_skills.py does
not exist yet.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ModuleNotFoundError until script exists (RED)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from validate_skills import validate_skill  # noqa: E402  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SCRIPT = _SCRIPTS_DIR / "validate_skills.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _write_skill(skill_dir: Path, frontmatter: str) -> None:
    """Write a SKILL.md with the given frontmatter into skill_dir."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n\n# Body\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def valid_skill(tmp_path: Path) -> Path:
    """Return a skill directory passing spec validation with no vendor fields."""
    skill_dir = tmp_path / "clean-skill"
    _write_skill(skill_dir, "name: clean-skill\ndescription: A valid test skill.")
    return skill_dir


# ---------------------------------------------------------------------------
# TestFromAC_ValidateSkillFilter
# ---------------------------------------------------------------------------
class TestFromAC_ValidateSkillFilter:
    """AC1-AC3: filter function returns empty for valid/vendor-only,
    non-empty for real spec errors."""

    # --- Happy paths (AC1) ---

    def test_spec_compliant_required_fields_passes(self, tmp_path: Path) -> None:
        """AC1: skill with only required name+description returns no errors."""
        skill_dir = tmp_path / "min-skill"
        _write_skill(skill_dir, "name: min-skill\ndescription: A minimal skill.")
        assert validate_skill(skill_dir) == []

    def test_spec_compliant_optional_fields_passes(self, tmp_path: Path) -> None:
        """AC1: skill with allowed optional fields (license, compatibility) passes."""
        skill_dir = tmp_path / "opt-skill"
        _write_skill(
            skill_dir,
            "name: opt-skill\ndescription: Optional fields skill.\n"
            "license: MIT\ncompatibility: VS Code 1.90+",
        )
        assert validate_skill(skill_dir) == []

    # --- Edge cases (AC2): each vendor field is filtered ---

    def test_user_invocable_false_filtered(self, tmp_path: Path) -> None:
        """AC2: user-invocable vendor field produces no errors after filtering."""
        skill_dir = tmp_path / "pipe-skill"
        _write_skill(
            skill_dir,
            "name: pipe-skill\ndescription: Pipeline skill.\nuser-invocable: false",
        )
        assert validate_skill(skill_dir) == []

    def test_argument_hint_filtered(self, tmp_path: Path) -> None:
        """AC2: argument-hint vendor field produces no errors after filtering."""
        skill_dir = tmp_path / "hint-skill"
        _write_skill(
            skill_dir,
            "name: hint-skill\ndescription: Hinted skill.\nargument-hint: '[scope]'",
        )
        assert validate_skill(skill_dir) == []

    def test_disable_model_invocation_filtered(self, tmp_path: Path) -> None:
        """AC2: disable-model-invocation vendor field produces no errors after filtering."""
        skill_dir = tmp_path / "dmi-skill"
        _write_skill(
            skill_dir,
            "name: dmi-skill\ndescription: A skill.\ndisable-model-invocation: true",
        )
        assert validate_skill(skill_dir) == []

    def test_all_three_vendor_fields_filtered(self, tmp_path: Path) -> None:
        """AC2: all three vendor fields together are fully filtered — no errors."""
        skill_dir = tmp_path / "full-vendor"
        _write_skill(
            skill_dir,
            "name: full-vendor\ndescription: Full vendor skill.\n"
            "user-invocable: false\nargument-hint: '[x]'\ndisable-model-invocation: true",
        )
        assert validate_skill(skill_dir) == []

    # --- Error paths (AC3): real spec errors survive filtering ---

    def test_missing_description_fails_after_filter(self, tmp_path: Path) -> None:
        """AC3: missing required description field survives the vendor filter."""
        skill_dir = tmp_path / "no-desc"
        _write_skill(skill_dir, "name: no-desc")
        errors = validate_skill(skill_dir)
        assert len(errors) > 0

    def test_name_directory_mismatch_fails_after_filter(self, tmp_path: Path) -> None:
        """AC3: name field that mismatches directory name is a real spec error."""
        skill_dir = tmp_path / "real-skill"
        _write_skill(skill_dir, "name: wrong-name\ndescription: A skill.")
        errors = validate_skill(skill_dir)
        assert len(errors) > 0

    # --- Boundary: vendor error mixed with real error ---

    def test_vendor_plus_missing_description_real_error_survives(
        self, tmp_path: Path
    ) -> None:
        """AC3 boundary: vendor field + missing description → real error still present."""
        skill_dir = tmp_path / "mixed-skill"
        _write_skill(
            skill_dir,
            "name: mixed-skill\nuser-invocable: false",  # no description
        )
        errors = validate_skill(skill_dir)
        assert len(errors) > 0
        # The vendor-field error must NOT appear in filtered output
        assert not any("user-invocable" in e for e in errors)

    def test_vendor_plus_name_mismatch_real_error_survives(
        self, tmp_path: Path
    ) -> None:
        """AC3 boundary: vendor field + name mismatch → mismatch error still present."""
        skill_dir = tmp_path / "name-mix"
        _write_skill(
            skill_dir,
            "name: wrong-name\ndescription: A skill.\nargument-hint: '[x]'",
        )
        errors = validate_skill(skill_dir)
        assert len(errors) > 0
        assert not any("argument-hint" in e for e in errors)


# ---------------------------------------------------------------------------
# TestFromAC_ExitCode
# ---------------------------------------------------------------------------
class TestFromAC_ExitCode:
    """AC4: script exit code is 0 when all skills pass, 1 when any real error remains."""

    def test_exit_code_zero_valid_skill(self, tmp_path: Path) -> None:
        """AC4: exit 0 when a single valid skill directory is supplied."""
        skill_dir = tmp_path / "ok-skill"
        _write_skill(skill_dir, "name: ok-skill\ndescription: An ok skill.")
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), str(skill_dir)],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_exit_code_zero_vendor_only_errors(self, tmp_path: Path) -> None:
        """AC4: exit 0 when only vendor-field errors exist (filtered to nothing)."""
        skill_dir = tmp_path / "vend-only"
        _write_skill(
            skill_dir,
            "name: vend-only\ndescription: Vendor-only skill.\nuser-invocable: false",
        )
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), str(skill_dir)],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_exit_code_one_missing_description(self, tmp_path: Path) -> None:
        """AC4: exit 1 when a skill has a real spec error (missing description)."""
        skill_dir = tmp_path / "err-skill"
        _write_skill(skill_dir, "name: err-skill")
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), str(skill_dir)],
            capture_output=True,
        )
        assert result.returncode == 1
