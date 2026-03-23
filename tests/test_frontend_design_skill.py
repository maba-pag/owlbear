"""Tests for the frontend-design skill package — SKILL.md frontmatter + reference files.

RED phase for task #941. All tests fail until #934 creates the
.github/skills/frontend-design/ package.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import pytest

from owlbear.skills.registry import SkillRegistry

# Resolve repo root from this test file's location.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_FILE = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "SKILL.md"
_REFERENCES_DIR = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "references"

_EXPECTED_REFERENCE_FILES = [
    "typography.md",
    "color-and-contrast.md",
    "spatial-design.md",
    "motion-design.md",
    "interaction-design.md",
    "responsive-design.md",
    "ux-writing.md",
]


class TestFromAC_FrontendDesignSkillPackage:
    """Verify the frontend-design skill package exists and meets the AC contract."""

    # ------------------------------------------------------------------
    # AC1 + AC2: SKILL.md exists and is loadable by SkillRegistry
    # ------------------------------------------------------------------

    def test_skill_file_exists(self) -> None:
        """AC1: .github/skills/frontend-design/SKILL.md must exist on disk."""
        assert _SKILL_FILE.exists(), f"Expected skill file at {_SKILL_FILE}"

    def test_frontmatter_parses_without_error(self) -> None:
        """AC2: SkillRegistry._parse_frontmatter must return a non-None SkillMeta."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None, "Frontmatter parsing returned None"

    # ------------------------------------------------------------------
    # AC3: frontmatter name and description
    # ------------------------------------------------------------------

    def test_frontmatter_name_is_frontend_design(self) -> None:
        """AC3: parsed frontmatter name must equal 'frontend-design'."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        assert meta.name == "frontend-design", f"Expected name 'frontend-design', got '{meta.name}'"

    def test_frontmatter_description_is_nonempty(self) -> None:
        """AC3: parsed frontmatter description must be non-empty."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        assert meta.description, "Frontmatter description must not be empty"

    # ------------------------------------------------------------------
    # AC4: seven reference files exist under references/
    # ------------------------------------------------------------------

    def test_typography_reference_exists(self) -> None:
        """AC4: references/typography.md must exist."""
        assert (_REFERENCES_DIR / "typography.md").exists()

    def test_color_and_contrast_reference_exists(self) -> None:
        """AC4: references/color-and-contrast.md must exist."""
        assert (_REFERENCES_DIR / "color-and-contrast.md").exists()

    def test_spatial_design_reference_exists(self) -> None:
        """AC4: references/spatial-design.md must exist."""
        assert (_REFERENCES_DIR / "spatial-design.md").exists()

    def test_motion_design_reference_exists(self) -> None:
        """AC4: references/motion-design.md must exist."""
        assert (_REFERENCES_DIR / "motion-design.md").exists()

    def test_interaction_design_reference_exists(self) -> None:
        """AC4: references/interaction-design.md must exist."""
        assert (_REFERENCES_DIR / "interaction-design.md").exists()

    def test_responsive_design_reference_exists(self) -> None:
        """AC4: references/responsive-design.md must exist."""
        assert (_REFERENCES_DIR / "responsive-design.md").exists()

    def test_ux_writing_reference_exists(self) -> None:
        """AC4: references/ux-writing.md must exist."""
        assert (_REFERENCES_DIR / "ux-writing.md").exists()

    def test_all_seven_reference_files_exist(self) -> None:
        """AC4: all seven required reference files are present."""
        missing = [
            name for name in _EXPECTED_REFERENCE_FILES if not (_REFERENCES_DIR / name).exists()
        ]
        assert missing == [], f"Missing reference files: {missing}"


class TestFromAC_ForbiddenStrings:
    """AC4: No file under .github/skills/frontend-design/ mentions forbidden strings.

    AC4 states: "No file under .github/skills/frontend-design/ mentions
    .impeccable.md, /teach-impeccable, or provider-specific slash-command/setup
    instructions."
    """

    _SKILL_DIR = _REPO_ROOT / ".github" / "skills" / "frontend-design"

    def _all_skill_files(self) -> list[Path]:
        return sorted(self._SKILL_DIR.rglob("*.md"))

    def test_no_file_mentions_dotimpeccable_md(self) -> None:
        """AC4: the string '.impeccable.md' must not appear in any skill package file."""
        violations = [
            f"{p.relative_to(_REPO_ROOT)}:{i + 1}: {line.strip()}"
            for p in self._all_skill_files()
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
            if ".impeccable.md" in line
        ]
        assert violations == [], (
            "Forbidden '.impeccable.md' found in skill package files:\n" + "\n".join(violations)
        )

    def test_no_file_mentions_teach_impeccable(self) -> None:
        """AC4: the string '/teach-impeccable' must not appear in any skill package file."""
        violations = [
            f"{p.relative_to(_REPO_ROOT)}:{i + 1}: {line.strip()}"
            for p in self._all_skill_files()
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines())
            if "/teach-impeccable" in line
        ]
        assert violations == [], (
            "Forbidden '/teach-impeccable' found in skill package files:\n" + "\n".join(violations)
        )

    def test_forbidden_strings_not_present_together(self) -> None:
        """AC4 boundary: neither forbidden string exists anywhere in the skill package."""
        forbidden = [".impeccable.md", "/teach-impeccable"]
        all_violations: list[str] = [
            f"{p.relative_to(_REPO_ROOT)}: {token!r}"
            for p in self._all_skill_files()
            for token in forbidden
            if token in p.read_text(encoding="utf-8")
        ]
        assert all_violations == [], (
            "One or more forbidden strings found in skill package:\n" + "\n".join(all_violations)
        )


# ---------------------------------------------------------------------------
# Tests added in retry #2 for #934 — AC coverage gaps identified by reviewer
# ---------------------------------------------------------------------------


class TestFromAC_DesignContextPrompts:
    """AC1 (extension): SKILL.md has a top-of-body design-context section asking for
    target audience, primary use cases / jobs, and brand personality or tone.
    """

    def test_skill_body_has_design_context_section(self) -> None:
        """AC1: SKILL.md must contain a 'Design Context' section."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        assert "design context" in text.lower(), (
            "SKILL.md must contain a 'Design Context' section"
        )

    def test_skill_body_asks_for_target_audience(self) -> None:
        """AC1: Design Context section must ask for the target audience."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        assert "target audience" in text.lower(), (
            "SKILL.md Design Context must include a 'target audience' question"
        )

    def test_skill_body_asks_for_primary_use_cases(self) -> None:
        """AC1: Design Context section must ask for primary use cases or jobs."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        lower = text.lower()
        assert "use case" in lower or "primary use" in lower or "jobs" in lower, (
            "SKILL.md Design Context must ask for primary use cases / jobs"
        )

    def test_skill_body_asks_for_brand_personality_or_tone(self) -> None:
        """AC1: Design Context section must ask for brand personality or tone."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        lower = text.lower()
        has_brand_or_personality = "brand" in lower or "personality" in lower
        has_tone = "tone" in lower
        assert has_brand_or_personality, (
            "SKILL.md Design Context must mention 'brand' or 'personality'"
        )
        assert has_tone, "SKILL.md Design Context must mention 'tone'"

    def test_design_context_appears_before_reference_pack(self) -> None:
        """AC1: Design Context section must appear before the Reference Pack section."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        lower = text.lower()
        dc_pos = lower.find("design context")
        rp_pos = lower.find("reference pack")
        assert dc_pos != -1, "SKILL.md must have a 'Design Context' section"
        assert rp_pos != -1, "SKILL.md must have a 'Reference Pack' section"
        assert dc_pos < rp_pos, (
            "Design Context section must appear before the Reference Pack section"
        )


class TestFromAC_SkillLinkLayout:
    """AC3: SKILL.md links to references/*.md (plural) files; no singular reference/ links."""

    def test_skill_body_uses_plural_references_directory(self) -> None:
        """AC3: SKILL.md must link to the 'references/' (plural) directory."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        assert "references/" in text, (
            "SKILL.md must use 'references/' (plural) for reference file links"
        )

    def test_skill_body_does_not_link_to_singular_reference_directory(self) -> None:
        """AC3: SKILL.md must not contain link targets using singular 'reference/'."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        # Match markdown link targets like (reference/something)
        singular_links = re.findall(r"\(reference/[^)]*\)", text)
        assert singular_links == [], (
            f"SKILL.md must not link to 'reference/' (singular); found: {singular_links}"
        )

    def test_skill_links_to_all_seven_reference_files(self) -> None:
        """AC3: SKILL.md body must link to each of the seven expected reference files."""
        text = _SKILL_FILE.read_text(encoding="utf-8")
        missing = [
            fname for fname in _EXPECTED_REFERENCE_FILES
            if f"references/{fname}" not in text
        ]
        assert missing == [], (
            f"SKILL.md is missing links to reference files: {missing}"
        )


class TestFromAC_ProviderSetupInstructions:
    """AC4 (extended): No file in the skill package contains provider-specific
    slash-command instructions or a Setup/Installation section for provider config.
    """

    _SKILL_DIR = _REPO_ROOT / ".github" / "skills" / "frontend-design"

    def _all_skill_files(self) -> list[Path]:
        return sorted(self._SKILL_DIR.rglob("*.md"))

    def test_no_standalone_slash_commands_in_skill_package(self) -> None:
        """AC4: No file must have lines consisting of a bare provider slash-command."""
        # A standalone slash-command line: optional whitespace then /word (provider command).
        slash_cmd_re = re.compile(r"^\s*/[a-z][a-z0-9_-]+", re.IGNORECASE)
        violations: list[str] = []
        for p in self._all_skill_files():
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                if slash_cmd_re.match(line):
                    violations.append(f"{p.name}:{i}: {line.rstrip()}")
        assert violations == [], (
            "Provider slash-command instructions found in skill package:\n"
            + "\n".join(violations)
        )

    def test_no_provider_setup_or_installation_heading(self) -> None:
        """AC4: No file must have a 'Setup' or 'Installation' heading for provider config."""
        forbidden_headings = {"setup", "installation", "installing", "configure provider"}
        heading_re = re.compile(r"^#{1,3}\s+(.+)$", re.IGNORECASE)
        violations: list[str] = []
        for p in self._all_skill_files():
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                m = heading_re.match(line)
                if m and m.group(1).strip().lower() in forbidden_headings:
                    violations.append(f"{p.name}:{i}: {line.rstrip()}")
        assert violations == [], (
            "Provider setup/installation section headings found in skill package:\n"
            + "\n".join(violations)
        )


class TestFromAC_OwlBearAdaptation:
    """AC5: SKILL.md and reference files are OwlBear adaptations, not verbatim copies."""

    _NOTICE_FILE = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "NOTICE.md"

    def _attribution_text(self) -> str:
        text = ""
        if self._NOTICE_FILE.exists():
            text += self._NOTICE_FILE.read_text(encoding="utf-8").lower()
        text += _SKILL_FILE.read_text(encoding="utf-8").lower()
        return text

    def test_attribution_states_owlbear_adaptation(self) -> None:
        """AC5: NOTICE.md or SKILL.md must explicitly describe the content as an adaptation."""
        combined = self._attribution_text()
        assert "adaptation" in combined or "adapted" in combined, (
            "NOTICE.md or SKILL.md must explicitly state the content is an OwlBear adaptation"
        )

    def test_attribution_states_no_verbatim_copies(self) -> None:
        """AC5: Attribution must declare no file is a verbatim copy."""
        combined = self._attribution_text()
        assert "verbatim" in combined, (
            "NOTICE.md or SKILL.md must include a 'no verbatim copy' statement"
        )

    def test_reference_files_have_substantial_content(self) -> None:
        """AC5: Each reference file must have substantive content (≥ 20 non-empty lines)."""
        thin: list[str] = []
        for filename in _EXPECTED_REFERENCE_FILES:
            ref_path = _REFERENCES_DIR / filename
            if ref_path.exists():
                content_lines = [
                    ln for ln in ref_path.read_text(encoding="utf-8").splitlines()
                    if ln.strip()
                ]
                if len(content_lines) < 20:
                    thin.append(f"{filename}: only {len(content_lines)} non-empty lines")
        detail = "\n".join(thin)
        assert thin == [], (
            f"Reference files must be substantive OwlBear adaptations (≥ 20 lines):\n{detail}"
        )


class TestFromAC_Attribution:
    """AC6: Attribution in NOTICE.md or a clearly marked SKILL.md section credits
    both Impeccable (Paul Bakaus) and Anthropic.
    """

    _NOTICE_FILE = _REPO_ROOT / ".github" / "skills" / "frontend-design" / "NOTICE.md"
    _ATTRIBUTION_PATHS: ClassVar[list[Path]] = [
        _REPO_ROOT / ".github" / "skills" / "frontend-design" / "NOTICE.md",
        _REPO_ROOT / ".github" / "skills" / "frontend-design" / "SKILL.md",
    ]

    def test_attribution_file_or_section_exists(self) -> None:
        """AC6: NOTICE.md must exist, or SKILL.md must have an attribution/notice section."""
        if self._NOTICE_FILE.exists():
            return
        skill_lower = _SKILL_FILE.read_text(encoding="utf-8").lower()
        assert "attribution" in skill_lower or "notice" in skill_lower, (
            "NOTICE.md must exist, or SKILL.md must have an attribution/notice section"
        )

    def test_attribution_credits_impeccable(self) -> None:
        """AC6: 'Impeccable' must appear in NOTICE.md or SKILL.md attribution."""
        for p in self._ATTRIBUTION_PATHS:
            if p.exists() and "impeccable" in p.read_text(encoding="utf-8").lower():
                return
        pytest.fail("'Impeccable' must be credited in NOTICE.md or SKILL.md")

    def test_attribution_credits_anthropic(self) -> None:
        """AC6: 'Anthropic' must appear in NOTICE.md or SKILL.md attribution."""
        for p in self._ATTRIBUTION_PATHS:
            if p.exists() and "anthropic" in p.read_text(encoding="utf-8").lower():
                return
        pytest.fail("'Anthropic' must be credited in NOTICE.md or SKILL.md")


class TestFromAC_ScopeBoundary:
    """AC7: Skill package contains only .github/skills/frontend-design/** files and
    does not absorb scope from #937 (frontend.instructions.md) or #938 (anti-pattern taxonomy).
    """

    _SKILL_DIR = _REPO_ROOT / ".github" / "skills" / "frontend-design"

    def test_skill_package_contains_only_expected_files(self) -> None:
        """AC7: Skill package must contain only SKILL.md, NOTICE.md, and references/*.md."""
        allowed_root = {"SKILL.md", "NOTICE.md"}
        allowed_in_references = set(_EXPECTED_REFERENCE_FILES)
        extra: list[str] = []
        for f in self._SKILL_DIR.rglob("*"):
            if not f.is_file():
                continue
            rel = f.relative_to(self._SKILL_DIR)
            parts = rel.parts
            if len(parts) == 1 and parts[0] in allowed_root:
                continue
            if len(parts) == 2 and parts[0] == "references" and parts[1] in allowed_in_references:
                continue
            extra.append(str(rel))
        assert extra == [], (
            f"Unexpected files found in skill package (AC7 scope violation): {extra}"
        )

    def test_skill_package_has_no_anti_pattern_taxonomy(self) -> None:
        """AC7: SKILL.md must not contain an anti-pattern taxonomy (belongs to #938)."""
        skill_lower = _SKILL_FILE.read_text(encoding="utf-8").lower()
        assert "anti-pattern taxonomy" not in skill_lower, (
            "SKILL.md must not include an 'anti-pattern taxonomy' (that scope belongs to #938)"
        )

    def test_skill_package_has_no_instructions_files(self) -> None:
        """AC7: No .instructions.md files must exist inside the skill package (belongs to #937)."""
        instructions_in_package = list(self._SKILL_DIR.glob("*.instructions.md"))
        assert instructions_in_package == [], (
            f"Unexpected .instructions.md file(s) found in skill package (scope belongs to #937): "
            f"{[str(p.name) for p in instructions_in_package]}"
        )
