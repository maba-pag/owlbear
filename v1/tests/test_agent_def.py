"""Tests for agent_def — AgentDefinition model and parse_agent_definition."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.core.agent_def import AgentDefinition, parse_agent_definition


class TestAgentDefinition:
    """Tests for the AgentDefinition Pydantic model."""

    def test_all_fields_populated(self) -> None:
        defn = AgentDefinition(
            name="builder",
            description="Builds code via TDD",
            role="validator",
            tools=["file_read", "file_write"],
            skills=["kanban-md"],
            model="gpt-4o",
            max_delegation_depth=5,
            system_prompt="You are a validator.",
        )
        assert defn.name == "builder"
        assert defn.description == "Builds code via TDD"
        assert defn.role == "validator"
        assert defn.tools == ["file_read", "file_write"]
        assert defn.skills == ["kanban-md"]
        assert defn.model == "gpt-4o"
        assert defn.max_delegation_depth == 5
        assert defn.system_prompt == "You are a validator."

    def test_defaults(self) -> None:
        defn = AgentDefinition(
            name="test-agent",
            description="A test agent",
            system_prompt="Hello.",
        )
        assert defn.role == "builder"
        assert defn.tools == []
        assert defn.skills == []
        assert defn.model is None
        assert defn.max_delegation_depth == 3


class TestParseAgentDefinition:
    """Tests for parse_agent_definition function."""

    def test_parse_valid_all_fields(self, tmp_path: Path) -> None:
        md = tmp_path / "agent.md"
        md.write_text(
            "---\n"
            "name: builder\n"
            "description: Builds code via TDD\n"
            "role: validator\n"
            "tools:\n"
            "  - file_read\n"
            "  - file_write\n"
            "skills:\n"
            "  - kanban-md\n"
            "model: gpt-4o\n"
            "max_delegation_depth: 5\n"
            "---\n"
            "You are a disciplined builder agent.\n",
            encoding="utf-8",
        )
        defn = parse_agent_definition(md)
        assert defn.name == "builder"
        assert defn.description == "Builds code via TDD"
        assert defn.role == "validator"
        assert defn.tools == ["file_read", "file_write"]
        assert defn.skills == ["kanban-md"]
        assert defn.model == "gpt-4o"
        assert defn.max_delegation_depth == 5
        assert defn.system_prompt == "You are a disciplined builder agent.\n"

    def test_parse_defaults(self, tmp_path: Path) -> None:
        md = tmp_path / "minimal.md"
        md.write_text(
            "---\nname: minimal\ndescription: Minimal agent\n---\nBody here.\n",
            encoding="utf-8",
        )
        defn = parse_agent_definition(md)
        assert defn.name == "minimal"
        assert defn.description == "Minimal agent"
        assert defn.role == "builder"
        assert defn.tools == []
        assert defn.skills == []
        assert defn.model is None
        assert defn.max_delegation_depth == 3
        assert defn.system_prompt == "Body here.\n"

    def test_missing_name_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "no_name.md"
        md.write_text(
            "---\ndescription: Has no name\n---\nBody.\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="name"):
            parse_agent_definition(md)

    def test_missing_description_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "no_desc.md"
        md.write_text(
            "---\nname: test\n---\nBody.\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="description"):
            parse_agent_definition(md)

    def test_empty_body_sets_empty_system_prompt(self, tmp_path: Path) -> None:
        md = tmp_path / "empty_body.md"
        md.write_text(
            "---\nname: empty\ndescription: No body\n---\n",
            encoding="utf-8",
        )
        defn = parse_agent_definition(md)
        assert defn.system_prompt == ""

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "bad_yaml.md"
        md.write_text(
            "---\nname: [unclosed\n---\nBody.\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"[Ii]nvalid YAML"):
            parse_agent_definition(md)

    def test_no_frontmatter_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "no_fm.md"
        md.write_text("Just plain markdown.\n", encoding="utf-8")
        with pytest.raises(ValueError, match="frontmatter"):
            parse_agent_definition(md)

    def test_multiline_system_prompt(self, tmp_path: Path) -> None:
        body = "# Builder\n\nYou build things.\n\n## Rules\n\n- Be precise.\n"
        md = tmp_path / "multi.md"
        md.write_text(
            f"---\nname: multi\ndescription: Multi-line body\n---\n{body}",
            encoding="utf-8",
        )
        defn = parse_agent_definition(md)
        assert defn.system_prompt == body

    def test_no_closing_delimiter_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "unclosed.md"
        md.write_text("---\nname: oops\ndescription: Missing close\n", encoding="utf-8")
        with pytest.raises(ValueError, match="closing frontmatter delimiter"):
            parse_agent_definition(md)

    def test_yaml_not_mapping_raises(self, tmp_path: Path) -> None:
        md = tmp_path / "list_yaml.md"
        md.write_text("---\n- item1\n- item2\n---\nBody.\n", encoding="utf-8")
        with pytest.raises(TypeError, match="not a mapping"):
            parse_agent_definition(md)
