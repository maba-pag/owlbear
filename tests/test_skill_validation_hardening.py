"""Failing tests for task #511: Harden skill validation with deer-flow patterns.

Covers:
  - AC: directory name naming convention (lowercase, digits, hyphens only;
        no leading/trailing/consecutive hyphens)
  - AC: naming convention applies to directory name unconditionally
        (not just optional name metadata field)
  - AC: name metadata field, if present, must also pass naming convention
  - AC: skill directory name must not exceed 64 characters
  - AC: description must not contain angle brackets (<  or >) per deer-flow pattern
  - AC: description must not exceed 1024 characters (Agent Skills Spec)
  - AC: each new rule produces a distinct error message including the offending value
  - AC: regression guard — all existing skills/ still pass enhanced validation

All error-path tests fail on current HEAD because validate_metadata() does not yet
implement the new naming, length, or angle-bracket rules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — import from scripts/ directory
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent / ".owlbear" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from skills_ref.validator import validate_metadata  # noqa: E402
from validate_skills import validate_skill  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_SKILLS_DIR = Path(__file__).parent.parent / "share" / "skills"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _meta(description: str = "A valid description.") -> dict:
    """Return minimal valid metadata with the given description."""
    return {"description": description}


def _write_skill(skill_dir: Path, frontmatter: str) -> None:
    """Write a SKILL.md with the given YAML frontmatter into skill_dir."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}\n---\n\n# Body\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# TestFromAC_DirectoryNamingConvention
# ---------------------------------------------------------------------------
class TestFromAC_DirectoryNamingConvention:
    """AC: skill directory names must contain only lowercase letters, digits, and
    hyphens; must not start or end with a hyphen; must not contain consecutive
    hyphens.  Applies unconditionally (no name field required).
    """

    # --- Error paths — all FAIL on current HEAD (no naming checks exist yet) ---

    def test_uppercase_dir_name_produces_error(self, tmp_path: Path) -> None:
        """Uppercase characters in directory name must produce an error."""
        skill_dir = tmp_path / "MySkill"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_underscore_in_dir_name_produces_error(self, tmp_path: Path) -> None:
        """Underscore in directory name must produce an error."""
        skill_dir = tmp_path / "my_skill"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_dir_name_starting_with_hyphen_produces_error(self, tmp_path: Path) -> None:
        """Directory name starting with a hyphen must produce an error."""
        skill_dir = tmp_path / "-skill"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_dir_name_ending_with_hyphen_produces_error(self, tmp_path: Path) -> None:
        """Directory name ending with a hyphen must produce an error."""
        skill_dir = tmp_path / "skill-"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_dir_name_with_consecutive_hyphens_produces_error(self, tmp_path: Path) -> None:
        """Consecutive hyphens in directory name must produce an error."""
        skill_dir = tmp_path / "my--skill"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_dir_name_with_special_chars_produces_error(self, tmp_path: Path) -> None:
        """Non-alphanumeric/hyphen characters (e.g. dot) must produce an error."""
        skill_dir = tmp_path / "my.skill"
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_naming_error_message_includes_offending_dir_name(self, tmp_path: Path) -> None:
        """Error message for naming convention violation must cite the dir name."""
        skill_dir = tmp_path / "Bad_Dir_Name"
        errors = validate_metadata(_meta(), skill_dir)
        assert any("Bad_Dir_Name" in e for e in errors)

    # --- Boundary ---

    def test_dir_name_with_single_valid_char_passes(self, tmp_path: Path) -> None:
        """Single lowercase letter is a valid directory name."""
        skill_dir = tmp_path / "a"
        errors = validate_metadata(_meta(), skill_dir)
        # Must not produce a naming-convention error
        assert not any(
            "naming" in e.lower() or "convention" in e.lower() or "invalid" in e.lower()
            for e in errors
        )

    def test_dir_name_with_digits_and_hyphens_passes(self, tmp_path: Path) -> None:
        """Digits and hyphens combined with lowercase letters are valid."""
        skill_dir = tmp_path / "skill-v2"
        errors = validate_metadata(_meta(), skill_dir)
        assert not any(
            "naming" in e.lower() or "convention" in e.lower() or "invalid" in e.lower()
            for e in errors
        )


# ---------------------------------------------------------------------------
# TestFromAC_NamingAppliedUnconditionally
# ---------------------------------------------------------------------------
class TestFromAC_NamingAppliedUnconditionally:
    """AC: naming convention applies to directory name even when no 'name'
    metadata field is present.
    """

    def test_invalid_dir_no_name_field_produces_error(self, tmp_path: Path) -> None:
        """Invalid dir name must produce error even when 'name' field is absent."""
        skill_dir = tmp_path / "UpperCaseDir"
        metadata = {"description": "A valid description."}  # no 'name' field
        errors = validate_metadata(metadata, skill_dir)
        assert len(errors) >= 1

    def test_valid_dir_no_name_field_passes(self, tmp_path: Path) -> None:
        """Valid dir name with no 'name' field produces no errors."""
        skill_dir = tmp_path / "valid-dir"
        metadata = {"description": "A valid description."}
        errors = validate_metadata(metadata, skill_dir)
        assert errors == []


# ---------------------------------------------------------------------------
# TestFromAC_NameFieldNamingConvention
# ---------------------------------------------------------------------------
class TestFromAC_NameFieldNamingConvention:
    """AC: if the 'name' metadata field is present, it must also pass the same
    naming convention rules.
    """

    def test_valid_name_field_passes(self, tmp_path: Path) -> None:
        """Name field with a valid kebab-case value produces no additional errors."""
        skill_dir = tmp_path / "my-skill"
        metadata = {"name": "my-skill", "description": "Valid."}
        errors = validate_metadata(metadata, skill_dir)
        assert errors == []

    def test_name_field_with_uppercase_produces_error(self, tmp_path: Path) -> None:
        """Name field containing uppercase must produce a naming convention error."""
        # dir_name valid, name field MATCHES dir (so current mismatch check won't fire),
        # but naming convention on the name value should fire.
        skill_dir = tmp_path / "MySkill"
        metadata = {"name": "MySkill", "description": "Valid."}
        # Current code: name == dir_name → no mismatch error; no naming check → empty
        errors = validate_metadata(metadata, skill_dir)
        assert len(errors) >= 1
        # Verify naming-convention check fires specifically for the name field (not just dir check)
        assert any("name field" in e and "lowercase" in e for e in errors)

    def test_name_field_with_underscore_produces_error(self, tmp_path: Path) -> None:
        """Name field containing underscore must produce an error."""
        skill_dir = tmp_path / "my-skill"
        # name differs from dir_name AND violates naming convention
        metadata = {"name": "my_skill", "description": "Valid."}
        errors = validate_metadata(metadata, skill_dir)
        assert len(errors) >= 1
        # Verify naming-convention check fires for the name field (not just mismatch)
        assert any("name field" in e and "lowercase" in e for e in errors)

    def test_name_field_starting_with_hyphen_produces_error(self, tmp_path: Path) -> None:
        """Name field starting with a hyphen must produce an error."""
        skill_dir = tmp_path / "my-skill"
        metadata = {"name": "-my-skill", "description": "Valid."}
        errors = validate_metadata(metadata, skill_dir)
        assert len(errors) >= 1
        # Verify naming-convention check fires for the name field (not just mismatch)
        assert any("name field" in e and "hyphen" in e and "does not match" not in e for e in errors)

    def test_name_field_with_consecutive_hyphens_produces_error(self, tmp_path: Path) -> None:
        """Name field with consecutive hyphens must produce an error."""
        skill_dir = tmp_path / "my-skill"
        metadata = {"name": "my--skill", "description": "Valid."}
        errors = validate_metadata(metadata, skill_dir)
        assert len(errors) >= 1
        # Verify naming-convention check fires for the name field (not just mismatch)
        assert any("name field" in e and "consecutive" in e for e in errors)

    def test_naming_error_for_name_field_includes_offending_value(self, tmp_path: Path) -> None:
        """Naming error for the name field must include the offending value."""
        skill_dir = tmp_path / "myskill"
        bad_name = "My_BadName"
        metadata = {"name": bad_name, "description": "Valid."}
        errors = validate_metadata(metadata, skill_dir)
        assert any(bad_name in e for e in errors)
        # Verify naming-convention check fires for the name field specifically (not just mismatch)
        assert any("name field" in e and bad_name in e and "lowercase" in e for e in errors)


# ---------------------------------------------------------------------------
# TestFromAC_MaxNameLength
# ---------------------------------------------------------------------------
class TestFromAC_MaxNameLength:
    """AC: skill directory name must not exceed 64 characters."""

    def test_exactly_64_chars_passes(self, tmp_path: Path) -> None:
        """A directory name of exactly 64 lowercase letters must not produce a
        length error.
        """
        name = "a" * 64
        skill_dir = tmp_path / name
        errors = validate_metadata(_meta(), skill_dir)
        assert not any("64" in e or "length" in e.lower() or "character" in e.lower() for e in errors)

    def test_65_chars_produces_error(self, tmp_path: Path) -> None:
        """A directory name of 65 characters must produce an error."""
        name = "a" * 65
        skill_dir = tmp_path / name
        errors = validate_metadata(_meta(), skill_dir)
        assert len(errors) >= 1

    def test_length_error_includes_offending_length_or_name(self, tmp_path: Path) -> None:
        """Length error message must include useful context (the name or the limits)."""
        long_name = "a" * 65
        skill_dir = tmp_path / long_name
        errors = validate_metadata(_meta(), skill_dir)
        # Error should name either the limit (64) or the offending value
        assert any("64" in e or "65" in e or long_name[:20] in e for e in errors)

    def test_63_chars_passes(self, tmp_path: Path) -> None:
        """63-char lowercase name must not trigger a length error."""
        name = "a" * 63
        skill_dir = tmp_path / name
        errors = validate_metadata(_meta(), skill_dir)
        assert not any("64" in e or "length" in e.lower() or "character" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# TestFromAC_DescriptionAngleBrackets
# ---------------------------------------------------------------------------
class TestFromAC_DescriptionAngleBrackets:
    """AC: descriptions must not contain angle brackets (< or >) as defense-in-depth
    against accidental HTML injection, per deer-flow pattern.
    """

    def test_description_without_brackets_passes(self, tmp_path: Path) -> None:
        """Clean description with no angle brackets must produce no errors."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "A clean, safe description."}, skill_dir)
        assert errors == []

    def test_description_with_opening_angle_bracket_produces_error(self, tmp_path: Path) -> None:
        """Description containing '<' must produce an error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "Must be <type> safe"}, skill_dir)
        assert len(errors) >= 1

    def test_description_with_closing_angle_bracket_produces_error(self, tmp_path: Path) -> None:
        """Description containing '>' must produce an error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "score > 0.9 required"}, skill_dir)
        assert len(errors) >= 1

    def test_description_with_html_tag_produces_error(self, tmp_path: Path) -> None:
        """Description containing an HTML tag must produce an error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "Use <b>bold</b> text"}, skill_dir)
        assert len(errors) >= 1

    def test_angle_bracket_error_is_descriptive(self, tmp_path: Path) -> None:
        """Error message for angle bracket violation must be descriptive."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "Has <injected> content"}, skill_dir)
        assert any(
            "<" in e or "angle" in e.lower() or "bracket" in e.lower() or "html" in e.lower()
            for e in errors
        )

    def test_angle_bracket_error_includes_offending_description_fragment(
        self, tmp_path: Path
    ) -> None:
        """Error message must include some representation of the offending value."""
        skill_dir = tmp_path / "my-skill"
        desc = "Has <bad> content"
        errors = validate_metadata({"description": desc}, skill_dir)
        # Error must include either the full description or the angle-bracket fragment
        assert any(desc in e or "<bad>" in e or "<" in e for e in errors)

    # --- Boundary ---

    def test_description_with_only_dashes_and_arrows_passes(self, tmp_path: Path) -> None:
        """Descriptions using '->' (text arrow, no angle brackets) must be allowed."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "step A -> step B -> result"}, skill_dir)
        assert errors == []


# ---------------------------------------------------------------------------
# TestFromAC_MaxDescriptionLength
# ---------------------------------------------------------------------------
class TestFromAC_MaxDescriptionLength:
    """AC: skill descriptions must not exceed 1024 characters (Agent Skills Spec)."""

    def test_exactly_1024_chars_passes(self, tmp_path: Path) -> None:
        """Description of exactly 1024 characters must not produce a length error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "a" * 1024}, skill_dir)
        assert not any("1024" in e for e in errors)

    def test_1025_chars_produces_error(self, tmp_path: Path) -> None:
        """Description of 1025 characters must produce an error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "a" * 1025}, skill_dir)
        assert len(errors) >= 1

    def test_length_error_includes_limit_or_actual_length(self, tmp_path: Path) -> None:
        """Length error must include either the 1024 limit or the actual count."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "a" * 1025}, skill_dir)
        assert any("1024" in e or "1025" in e for e in errors)

    def test_1023_chars_passes(self, tmp_path: Path) -> None:
        """Description of 1023 characters must not produce a length error."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "a" * 1023}, skill_dir)
        assert not any("1024" in e for e in errors)


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMessageDistinctness
# ---------------------------------------------------------------------------
class TestFromAC_ErrorMessageDistinctness:
    """AC: each new rule produces a distinct, descriptive error message including
    the offending value, following the existing pattern
    ('Missing required field: ...' includes the field name).
    """

    def test_each_violated_rule_produces_distinct_error(self, tmp_path: Path) -> None:
        """When multiple rules are violated, each produces a separate error entry."""
        # Uppercase dir name (naming violation) + description with angle bracket
        skill_dir = tmp_path / "BadName"
        errors = validate_metadata({"description": "Has <html> tag"}, skill_dir)
        # At least two distinct errors (one for naming, one for angle brackets)
        assert len(errors) >= 2

    def test_direction_arrow_descriptions_not_confused_with_angle_brackets(
        self, tmp_path: Path
    ) -> None:
        """'→' (unicode arrow) in description must not be treated as angle bracket."""
        skill_dir = tmp_path / "my-skill"
        errors = validate_metadata({"description": "step → result"}, skill_dir)
        assert errors == []


# ---------------------------------------------------------------------------
# TestFromAC_RegressionGuard
# ---------------------------------------------------------------------------
class TestFromAC_RegressionGuard:
    """AC: all existing skills in skills/ must pass the enhanced validation
    without false positives.  Parametrised over the live skills/ directory.
    """

    @pytest.mark.parametrize(
        "skill_dir",
        sorted(_SKILLS_DIR.iterdir()) if _SKILLS_DIR.exists() else [],
        ids=lambda p: p.name,
    )
    def test_existing_skill_passes_enhanced_validation(self, skill_dir: Path) -> None:
        """No existing skill in skills/ must fail the enhanced validation rules."""
        if not skill_dir.is_dir():
            pytest.skip(f"{skill_dir} is not a directory")
        errors = validate_skill(skill_dir)
        assert errors == [], (
            f"Skill '{skill_dir.name}' unexpectedly fails enhanced validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
