"""Tests for owlbear.planning package-root exports and docstring.

RED-phase tests for task #889. All tests must fail until task #572
implements the package-root __init__.py with docstring, explicit re-exports,
and a string-based __all__.
"""

from __future__ import annotations


class TestFromAC_PlanningDocstring:
    """AC: import owlbear.planning succeeds and planning.__doc__ is a non-empty str."""

    def test_docstring_is_str(self) -> None:
        from owlbear import planning

        assert isinstance(planning.__doc__, str)

    def test_docstring_is_non_empty_after_strip(self) -> None:
        from owlbear import planning

        assert planning.__doc__ is not None
        assert planning.__doc__.strip() != ""


class TestFromAC_PlanningImports:
    """AC: from owlbear.planning import ... succeeds for all four public symbols."""

    def test_import_project_definition(self) -> None:
        from owlbear.planning import ProjectDefinition  # noqa: F401

    def test_import_requirement(self) -> None:
        from owlbear.planning import Requirement  # noqa: F401

    def test_import_project_definition_extractor(self) -> None:
        from owlbear.planning import ProjectDefinitionExtractor  # noqa: F401

    def test_import_project_definition_to_markdown(self) -> None:
        from owlbear.planning import project_definition_to_markdown  # noqa: F401


class TestFromAC_PlanningSymbolIdentity:
    """AC: each package-root symbol is identical to its canonical submodule definition."""

    def test_project_definition_identity(self) -> None:
        from owlbear.planning import ProjectDefinition
        from owlbear.planning.models import ProjectDefinition as _Canonical

        assert ProjectDefinition is _Canonical

    def test_requirement_identity(self) -> None:
        from owlbear.planning import Requirement
        from owlbear.planning.models import Requirement as _Canonical

        assert Requirement is _Canonical

    def test_project_definition_extractor_identity(self) -> None:
        from owlbear.planning import ProjectDefinitionExtractor
        from owlbear.planning.extractor import (
            ProjectDefinitionExtractor as _Canonical,
        )

        assert ProjectDefinitionExtractor is _Canonical

    def test_project_definition_to_markdown_identity(self) -> None:
        from owlbear.planning import project_definition_to_markdown
        from owlbear.planning.markdown import (
            project_definition_to_markdown as _canonical,
        )

        assert project_definition_to_markdown is _canonical


class TestFromAC_PlanningAll:
    """AC: __all__ is exactly the four-name string list in the specified order."""

    def test_all_attribute_exists(self) -> None:
        from owlbear import planning

        assert hasattr(planning, "__all__")

    def test_all_is_exact_four_name_list_in_order(self) -> None:
        from owlbear import planning

        expected = [
            "ProjectDefinition",
            "ProjectDefinitionExtractor",
            "Requirement",
            "project_definition_to_markdown",
        ]
        assert planning.__all__ == expected

    def test_extraction_prompt_not_in_all(self) -> None:
        """EXTRACTION_PROMPT is an internal helper and must never appear in __all__."""
        from owlbear import planning

        assert "EXTRACTION_PROMPT" not in planning.__all__
