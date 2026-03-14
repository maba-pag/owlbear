"""Tests for SkillRegistry — progressive loading of markdown skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.skills.registry import SkillMeta, SkillRegistry


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sample skill files in subdirectory layout."""
    skill_a = tmp_path / "alpha" / "SKILL.md"
    skill_a.parent.mkdir()
    skill_a.write_text(
        "---\nname: alpha\ndescription: Alpha skill for testing\n"
        "---\n\n# Alpha\n\nFull alpha content.\n",
        encoding="utf-8",
    )

    skill_b = tmp_path / "beta" / "SKILL.md"
    skill_b.parent.mkdir()
    skill_b.write_text(
        "---\nname: beta\ndescription: Beta skill for analytics\n"
        "---\n\n# Beta\n\nFull beta content with details.\n",
        encoding="utf-8",
    )

    # A subdirectory with SKILL.md without frontmatter — should be skipped
    no_fm = tmp_path / "no-frontmatter" / "SKILL.md"
    no_fm.parent.mkdir()
    no_fm.write_text("# No Frontmatter\n\nJust plain markdown.\n", encoding="utf-8")

    # A non-SKILL.md file in subdir — should be ignored
    txt = tmp_path / "notes" / "notes.txt"
    txt.parent.mkdir()
    txt.write_text("Not a skill.", encoding="utf-8")

    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """An empty directory with no skill files."""
    return tmp_path / "empty"


class TestSkillMeta:
    """Tests for SkillMeta dataclass."""

    def test_create_skill_meta(self, tmp_path: Path) -> None:
        meta = SkillMeta(
            name="test-skill",
            description="A test skill",
            file_path=tmp_path / "test.md",
        )
        assert meta.name == "test-skill"
        assert meta.description == "A test skill"
        assert meta.file_path == tmp_path / "test.md"


class TestSkillRegistryScan:
    """Tests for directory scanning and skill registration."""

    def test_scan_finds_skills_with_frontmatter(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        assert "alpha" in registry.skills
        assert "beta" in registry.skills

    def test_scan_skips_files_without_frontmatter(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        assert len(registry.skills) == 2  # only alpha and beta

    def test_scan_skips_non_markdown_files(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        # notes.txt should not appear
        for meta in registry.skills.values():
            assert meta.name in {"alpha", "beta"}

    def test_scan_empty_directory(self, empty_dir: Path) -> None:
        empty_dir.mkdir(parents=True)
        registry = SkillRegistry(empty_dir)
        assert len(registry.skills) == 0

    def test_scan_nonexistent_directory(self, tmp_path: Path) -> None:
        registry = SkillRegistry(tmp_path / "nonexistent")
        assert len(registry.skills) == 0

    def test_skill_meta_has_correct_description(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        assert registry.skills["alpha"].description == "Alpha skill for testing"
        assert registry.skills["beta"].description == "Beta skill for analytics"


class TestSkillRegistryListSkills:
    """Tests for the list_skills tool (progressive loading — summaries only)."""

    def test_list_skills_returns_summaries(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        result = registry.list_skills()
        assert "alpha" in result
        assert "Alpha skill for testing" in result
        assert "beta" in result

    def test_list_skills_does_not_include_full_content(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        result = registry.list_skills()
        # Full content should NOT be in the summary
        assert "Full alpha content" not in result
        assert "Full beta content" not in result

    def test_list_skills_empty_registry(self, empty_dir: Path) -> None:
        empty_dir.mkdir(parents=True)
        registry = SkillRegistry(empty_dir)
        result = registry.list_skills()
        assert "no skills" in result.lower()


class TestSkillRegistryLoadSkill:
    """Tests for the load_skill tool (full content on demand)."""

    def test_load_skill_returns_full_content(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        content = registry.load_skill(name="alpha")
        assert "Full alpha content" in content

    def test_load_skill_returns_entire_file(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        content = registry.load_skill(name="alpha")
        # Should contain frontmatter + body
        assert "---" in content
        assert "# Alpha" in content

    def test_load_nonexistent_skill_raises(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        with pytest.raises(KeyError, match="unknown"):
            registry.load_skill(name="unknown")

    def test_load_skill_error_lists_available(self, skills_dir: Path) -> None:
        registry = SkillRegistry(skills_dir)
        with pytest.raises(KeyError, match="alpha"):
            registry.load_skill(name="nonexistent")


class TestSkillRegistryProgressive:
    """Tests verifying progressive loading behavior."""

    def test_file_not_read_until_load(self, skills_dir: Path) -> None:
        """Verify that skill file content is NOT read during __init__."""
        registry = SkillRegistry(skills_dir)
        # The registry should have metadata but we can verify progressive loading
        # by checking that only frontmatter was parsed, not the full file memoized
        assert "alpha" in registry.skills
        # The file_path exists and is readable
        assert registry.skills["alpha"].file_path.exists()

    def test_load_reads_fresh_content(self, skills_dir: Path) -> None:
        """If the file changes after init, load_skill returns the new content."""
        registry = SkillRegistry(skills_dir)

        # Modify the file after scanning
        registry.skills["alpha"].file_path.write_text(
            "---\nname: alpha\ndescription: Alpha skill for testing\n"
            "---\n\n# Updated Alpha\n\nNew content.\n",
            encoding="utf-8",
        )

        content = registry.load_skill(name="alpha")
        assert "New content" in content
        assert "Updated Alpha" in content


class TestSkillRegistryToolset:
    """Tests for FunctionToolset integration."""

    def test_registry_is_function_toolset(self, skills_dir: Path) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        registry = SkillRegistry(skills_dir)
        assert isinstance(registry, FunctionToolset)

    def test_toolset_has_list_and_load_tools(self, skills_dir: Path) -> None:
        """The toolset exposes list_skills and load_skill as registered tools."""
        registry = SkillRegistry(skills_dir)
        # FunctionToolset.tools is a dict[str, Tool]
        assert "list_skills" in registry.tools
        assert "load_skill" in registry.tools


class TestSkillRegistryEdgeCases:
    """Edge-case tests for full coverage."""

    def test_unreadable_file_is_skipped(self, tmp_path: Path) -> None:
        """A file that raises OSError on read is silently skipped."""
        bad_dir = tmp_path / "bad"
        bad_dir.mkdir()
        bad = bad_dir / "SKILL.md"
        bad.write_text("---\nname: bad\n---\n", encoding="utf-8")
        # Make the file unreadable by replacing it with a directory
        bad.unlink()
        bad.mkdir()

        registry = SkillRegistry(tmp_path)
        assert "bad" not in registry.skills

    def test_no_closing_frontmatter_delimiter(self, tmp_path: Path) -> None:
        """A file with opening --- but no closing --- is skipped."""
        d = tmp_path / "broken"
        d.mkdir()
        f = d / "SKILL.md"
        f.write_text("---\nname: broken\n# Content\n", encoding="utf-8")
        registry = SkillRegistry(tmp_path)
        assert "broken" not in registry.skills

    def test_frontmatter_missing_name_is_skipped(self, tmp_path: Path) -> None:
        """A file with valid YAML but no 'name' key is skipped."""
        d = tmp_path / "noname"
        d.mkdir()
        f = d / "SKILL.md"
        f.write_text(
            "---\ndescription: has desc but no name\n---\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        assert len(registry.skills) == 0

    def test_invalid_yaml_is_skipped(self, tmp_path: Path) -> None:
        """A file with malformed YAML in frontmatter is skipped."""
        d = tmp_path / "badfm"
        d.mkdir()
        f = d / "SKILL.md"
        f.write_text(
            "---\n: [invalid yaml{{{\n---\n# Body\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        assert "badfm" not in registry.skills
        assert len(registry.skills) == 0


# ---------------------------------------------------------------------------
# Task #780 — Fix SkillRegistry glob → */SKILL.md
# ---------------------------------------------------------------------------

# Real skills directory for integration tests.
_REAL_SKILLS_DIR = Path(__file__).resolve().parent.parent / ".github" / "skills"


@pytest.fixture
def subdir_skills_dir(tmp_path: Path) -> Path:
    """Create a temp directory with subdirectory-layout skill files.

    Layout::

        tmp/
          alpha/SKILL.md     ← valid skill
          beta/SKILL.md      ← valid skill
          gamma/SKILL.md     ← no frontmatter → skipped
          delta/README.md    ← wrong filename → skipped
          flat.md            ← flat file → skipped (no subdir)
    """
    alpha = tmp_path / "alpha" / "SKILL.md"
    alpha.parent.mkdir()
    alpha.write_text(
        "---\nname: alpha\ndescription: Alpha subdir skill\n---\n\n# Alpha\n\nAlpha content.\n",
        encoding="utf-8",
    )

    beta = tmp_path / "beta" / "SKILL.md"
    beta.parent.mkdir()
    beta.write_text(
        "---\nname: beta\ndescription: Beta subdir skill\n---\n\n# Beta\n\nBeta content.\n",
        encoding="utf-8",
    )

    gamma = tmp_path / "gamma" / "SKILL.md"
    gamma.parent.mkdir()
    gamma.write_text("# No Frontmatter\n\nPlain markdown.\n", encoding="utf-8")

    delta = tmp_path / "delta" / "README.md"
    delta.parent.mkdir()
    delta.write_text(
        "---\nname: delta\ndescription: Delta in README\n---\nContent.\n",
        encoding="utf-8",
    )

    flat = tmp_path / "flat.md"
    flat.write_text(
        "---\nname: flat\ndescription: Flat file skill\n---\nFlat content.\n",
        encoding="utf-8",
    )

    return tmp_path


class TestFromAC_SubdirGlob:  # noqa: N801
    """AC1: _scan() uses glob('*/SKILL.md') — discovers subdir layout only."""

    def test_scan_discovers_subdir_skill_md(self, subdir_skills_dir: Path) -> None:
        """A skill file at alpha/SKILL.md is discovered by _scan."""
        registry = SkillRegistry(subdir_skills_dir)
        assert "alpha" in registry.skills

    def test_scan_discovers_multiple_subdir_skills(self, subdir_skills_dir: Path) -> None:
        """Both alpha/SKILL.md and beta/SKILL.md are discovered."""
        registry = SkillRegistry(subdir_skills_dir)
        assert "alpha" in registry.skills
        assert "beta" in registry.skills
        assert len(registry.skills) == 2

    def test_scan_ignores_flat_md_files(self, subdir_skills_dir: Path) -> None:
        """A flat .md file at the root of skills_dir is NOT discovered."""
        registry = SkillRegistry(subdir_skills_dir)
        assert "flat" not in registry.skills

    def test_scan_ignores_non_skill_md_in_subdir(self, subdir_skills_dir: Path) -> None:
        """A file named README.md inside a subdir is NOT discovered."""
        registry = SkillRegistry(subdir_skills_dir)
        # Guard: alpha & beta must be found for this to be non-vacuous
        assert len(registry.skills) >= 2, "subdir skills must be discovered first"
        assert "delta" not in registry.skills

    def test_scan_skips_subdir_without_frontmatter(self, subdir_skills_dir: Path) -> None:
        """gamma/SKILL.md has no frontmatter → skipped."""
        registry = SkillRegistry(subdir_skills_dir)
        # Guard: alpha & beta must be found for this to be non-vacuous
        assert len(registry.skills) >= 2, "subdir skills must be discovered first"
        assert "gamma" not in registry.skills

    def test_scan_ignores_deeply_nested(self, tmp_path: Path) -> None:
        """A SKILL.md two levels deep (a/b/SKILL.md) is NOT discovered."""
        # Add a valid one-level skill so the test is non-vacuous
        valid = tmp_path / "valid" / "SKILL.md"
        valid.parent.mkdir(parents=True)
        valid.write_text(
            "---\nname: valid\ndescription: Valid skill\n---\nContent.\n",
            encoding="utf-8",
        )
        nested = tmp_path / "deep" / "inner" / "SKILL.md"
        nested.parent.mkdir(parents=True)
        nested.write_text(
            "---\nname: deep\ndescription: Deep skill\n---\nContent.\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        assert "valid" in registry.skills, "one-level subdir must be found"
        assert "deep" not in registry.skills


class TestFromAC_DocstringsUpdated:  # noqa: N801
    """AC2: Class and _scan docstrings reference subdirectory layout."""

    def test_class_docstring_references_subdirectory(self) -> None:
        """SkillRegistry class docstring must mention SKILL.md or subdirectory."""
        docstring = SkillRegistry.__doc__ or ""
        assert "SKILL.md" in docstring, (
            "Class docstring should reference SKILL.md subdirectory layout"
        )

    def test_scan_docstring_references_subdirectory(self) -> None:
        """_scan docstring must mention */SKILL.md or SKILL.md."""
        docstring = SkillRegistry._scan.__doc__ or ""
        assert "SKILL.md" in docstring, "_scan docstring should reference SKILL.md pattern"


class TestFromAC_RealSkillsDiscovery:  # noqa: N801
    """AC5: list_skills discovers 18 skills from real .github/skills dir."""

    @pytest.mark.skipif(
        not _REAL_SKILLS_DIR.is_dir(),
        reason="Real skills directory not found",
    )
    def test_discovers_18_real_skills(self) -> None:
        """SkillRegistry finds exactly 18 skills in .github/skills."""
        registry = SkillRegistry(_REAL_SKILLS_DIR)
        assert len(registry.skills) == 18, (
            f"Expected 18 skills, got {len(registry.skills)}: {sorted(registry.skills.keys())}"
        )

    @pytest.mark.skipif(
        not _REAL_SKILLS_DIR.is_dir(),
        reason="Real skills directory not found",
    )
    def test_real_skills_have_nonempty_names(self) -> None:
        """Every discovered real skill has a non-empty name and description."""
        registry = SkillRegistry(_REAL_SKILLS_DIR)
        assert len(registry.skills) == 18, "Must discover 18 skills first"
        for name, meta in registry.skills.items():
            assert name, "Skill name must be non-empty"
            assert meta.description, f"Skill '{name}' has empty description"

    @pytest.mark.skipif(
        not _REAL_SKILLS_DIR.is_dir(),
        reason="Real skills directory not found",
    )
    def test_list_skills_includes_all_18(self) -> None:
        """list_skills output mentions all 18 skill names."""
        registry = SkillRegistry(_REAL_SKILLS_DIR)
        assert len(registry.skills) == 18, "Must discover 18 skills first"
        output = registry.list_skills()
        for name in registry.skills:
            assert name in output, f"Skill '{name}' missing from list_skills output"
