"""Tests for the project-definition skill file — YAML frontmatter + content."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.skills.registry import SkillRegistry

# Resolve the actual skill file relative to the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SKILL_FILE = _REPO_ROOT / ".github" / "skills" / "project-definition" / "SKILL.md"


class TestProjectDefinitionSkillFrontmatter:
    """Verify the project-definition SKILL.md is loadable by SkillRegistry."""

    def test_skill_file_exists(self) -> None:
        assert _SKILL_FILE.exists(), f"Expected skill file at {_SKILL_FILE}"

    def test_frontmatter_parses_without_error(self) -> None:
        """SkillRegistry._parse_frontmatter must return valid SkillMeta."""
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None, "Frontmatter parsing returned None"

    def test_frontmatter_name(self) -> None:
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        assert meta.name == "project-definition"

    def test_frontmatter_description_references_llm_scoping(self) -> None:
        meta = SkillRegistry._parse_frontmatter(_SKILL_FILE)
        assert meta is not None
        # AC: description references LLM-guided project scoping
        desc_lower = meta.description.lower()
        assert "project" in desc_lower
        assert "scoping" in desc_lower or "definition" in desc_lower

    def test_user_invokable_false_in_frontmatter(self) -> None:
        """YAML frontmatter should contain user-invocable: false."""
        import yaml

        text = _SKILL_FILE.read_text(encoding="utf-8")
        end = text.find("---", 3)
        data = yaml.safe_load(text[3:end])
        assert data.get("user-invocable") is False


class TestProjectDefinitionSkillContent:
    """Verify the SKILL.md body meets acceptance criteria."""

    @pytest.fixture(autouse=True)
    def _load_content(self) -> None:
        self.content = _SKILL_FILE.read_text(encoding="utf-8")

    def test_has_six_workflow_steps(self) -> None:
        """Workflow template must have 6 numbered steps."""
        import re

        steps = re.findall(r"^\d+\.\s+\*\*", self.content, re.MULTILINE)
        assert len(steps) == 6, f"Expected 6 workflow steps, found {len(steps)}"

    def test_workflow_step_topics(self) -> None:
        """Steps must cover: receive idea, clarify, research, propose, iterate, finalize."""
        lower = self.content.lower()
        assert "receive" in lower or "idea" in lower
        assert "clarify" in lower or "ask_user" in lower
        assert "research" in lower or "knowledge" in lower
        assert "propos" in lower  # propose / proposed
        assert "iterate" in lower or "feedback" in lower
        assert "finalize" in lower or "final" in lower

    def test_has_field_reference_table(self) -> None:
        """Must contain a ProjectDefinition field reference table."""
        assert "| Field" in self.content or "| field" in self.content

    def test_field_table_has_required_fields(self) -> None:
        """Table must list key ProjectDefinition fields."""
        lower = self.content.lower()
        for field in ("name", "description", "goals", "requirements", "acceptance_criteria"):
            assert field in lower, f"Field '{field}' missing from content"

    def test_has_ask_user_example(self) -> None:
        """Must contain an example ask_user interaction with multi-option pattern."""
        assert "ask_user" in self.content
        # Multi-option pattern: numbered options or lettered options
        assert "Option" in self.content or "option" in self.content or "1." in self.content

    def test_follows_skill_structure(self) -> None:
        """Must start with --- frontmatter and have markdown body."""
        assert self.content.startswith("---")
        # Body follows after closing ---
        end = self.content.find("---", 3)
        body = self.content[end + 3 :].strip()
        assert len(body) > 100, "Body too short — expected substantial content"
