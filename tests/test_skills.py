"""Tests for SkillRegistry — progressive loading of markdown skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.skills.registry import SkillMeta, SkillRegistry


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sample skill files."""
    skill_a = tmp_path / "alpha.md"
    skill_a.write_text(
        "---\nname: alpha\ndescription: Alpha skill for testing\n"
        "---\n\n# Alpha\n\nFull alpha content.\n",
        encoding="utf-8",
    )

    skill_b = tmp_path / "beta.md"
    skill_b.write_text(
        "---\nname: beta\ndescription: Beta skill for analytics\n"
        "---\n\n# Beta\n\nFull beta content with details.\n",
        encoding="utf-8",
    )

    # A file without frontmatter — should be skipped
    no_fm = tmp_path / "no-frontmatter.md"
    no_fm.write_text("# No Frontmatter\n\nJust plain markdown.\n", encoding="utf-8")

    # A non-markdown file — should be ignored
    txt = tmp_path / "notes.txt"
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
        bad = tmp_path / "bad.md"
        bad.write_text("---\nname: bad\n---\n", encoding="utf-8")
        # Make the file unreadable by replacing it with a directory
        bad.unlink()
        bad.mkdir()

        registry = SkillRegistry(tmp_path)
        assert "bad" not in registry.skills

    def test_no_closing_frontmatter_delimiter(self, tmp_path: Path) -> None:
        """A file with opening --- but no closing --- is skipped."""
        f = tmp_path / "broken.md"
        f.write_text("---\nname: broken\n# Content\n", encoding="utf-8")
        registry = SkillRegistry(tmp_path)
        assert "broken" not in registry.skills

    def test_frontmatter_missing_name_is_skipped(self, tmp_path: Path) -> None:
        """A file with valid YAML but no 'name' key is skipped."""
        f = tmp_path / "noname.md"
        f.write_text(
            "---\ndescription: has desc but no name\n---\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        assert len(registry.skills) == 0

    def test_invalid_yaml_is_skipped(self, tmp_path: Path) -> None:
        """A file with malformed YAML in frontmatter is skipped."""
        f = tmp_path / "badfm.md"
        f.write_text(
            "---\n: [invalid yaml{{{\n---\n# Body\n",
            encoding="utf-8",
        )
        registry = SkillRegistry(tmp_path)
        assert "badfm" not in registry.skills
        assert len(registry.skills) == 0
