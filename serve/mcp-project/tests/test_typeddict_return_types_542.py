"""Tests for task #542: TypedDict return types for outputSchema specificity on mcp-project.

AC coverage (tests written from AC — TDD RED phase):
  - AC1: ProjectInfoResult(TypedDict) at module scope with fields:
         name, type, project_path, owlbear_path, created_at (all str)
  - AC2: ProjectListItem(TypedDict) at module scope with fields: name, path (all str)
  - AC3: project_info return annotation is ProjectInfoResult (no | str union)
  - AC5: project_list return annotation is list[ProjectListItem]
  - AC6: project_readme and project_structure return annotations are str (unchanged)
  - AC7: TypedDicts NOT under if TYPE_CHECKING — importable at runtime
  - AC8: __all__ in server.py includes ProjectInfoResult and ProjectListItem

Pipeline note: implementation was committed (df21f2f) before RED-phase review.
All tests verify the completed implementation contract.
"""

from __future__ import annotations

import typing

import owlbear_mcp_project.server as server_mod
from owlbear_mcp_project.server import (
    ProjectInfoResult,
    ProjectListItem,
    project_info,
    project_list,
    project_readme,
    project_structure,
)


# ---------------------------------------------------------------------------
# TestFromAC_ProjectInfoResultTypedDict  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectInfoResultTypedDict:
    """AC1: ProjectInfoResult(TypedDict) at module scope with 5 typed fields."""

    def test_project_info_result_is_typeddict(self) -> None:
        """ProjectInfoResult is a TypedDict class (not a plain dict, dataclass, or BaseModel)."""
        assert typing.is_typeddict(ProjectInfoResult), "ProjectInfoResult must be a TypedDict"

    def test_project_info_result_has_exactly_5_fields(self) -> None:
        """ProjectInfoResult defines exactly 5 fields."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert len(annotations) == 5, f"Expected 5 fields, got {len(annotations)}: {list(annotations)}"

    def test_project_info_result_has_all_required_field_names(self) -> None:
        """ProjectInfoResult has exactly: name, type, project_path, owlbear_path, created_at."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        expected = {"name", "type", "project_path", "owlbear_path", "created_at"}
        assert set(annotations) == expected, f"Expected fields {expected}, got {set(annotations)}"

    def test_project_info_result_name_field_is_str(self) -> None:
        """ProjectInfoResult.name is annotated as str."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert annotations["name"] is str, f"Expected 'name: str', got {annotations['name']!r}"

    def test_project_info_result_type_field_is_str(self) -> None:
        """ProjectInfoResult.type is annotated as str."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert annotations["type"] is str, f"Expected 'type: str', got {annotations['type']!r}"

    def test_project_info_result_project_path_field_is_str(self) -> None:
        """ProjectInfoResult.project_path is annotated as str."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert annotations["project_path"] is str, f"Expected 'project_path: str', got {annotations['project_path']!r}"

    def test_project_info_result_owlbear_path_field_is_str(self) -> None:
        """ProjectInfoResult.owlbear_path is annotated as str."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert annotations["owlbear_path"] is str, f"Expected 'owlbear_path: str', got {annotations['owlbear_path']!r}"

    def test_project_info_result_created_at_field_is_str(self) -> None:
        """ProjectInfoResult.created_at is annotated as str."""
        annotations = typing.get_type_hints(ProjectInfoResult)
        assert annotations["created_at"] is str, f"Expected 'created_at: str', got {annotations['created_at']!r}"


# ---------------------------------------------------------------------------
# TestFromAC_ProjectListItemTypedDict  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_ProjectListItemTypedDict:
    """AC2: ProjectListItem(TypedDict) at module scope with 2 typed fields."""

    def test_project_list_item_is_typeddict(self) -> None:
        """ProjectListItem is a TypedDict class."""
        assert typing.is_typeddict(ProjectListItem), "ProjectListItem must be a TypedDict"

    def test_project_list_item_has_exactly_2_fields(self) -> None:
        """ProjectListItem defines exactly 2 fields."""
        annotations = typing.get_type_hints(ProjectListItem)
        assert len(annotations) == 2, f"Expected 2 fields, got {len(annotations)}: {list(annotations)}"

    def test_project_list_item_has_name_and_path(self) -> None:
        """ProjectListItem has exactly: name, path."""
        annotations = typing.get_type_hints(ProjectListItem)
        assert set(annotations) == {"name", "path"}, f"Expected {{'name', 'path'}}, got {set(annotations)}"

    def test_project_list_item_name_field_is_str(self) -> None:
        """ProjectListItem.name is annotated as str."""
        annotations = typing.get_type_hints(ProjectListItem)
        assert annotations["name"] is str, f"Expected 'name: str', got {annotations['name']!r}"

    def test_project_list_item_path_field_is_str(self) -> None:
        """ProjectListItem.path is annotated as str."""
        annotations = typing.get_type_hints(ProjectListItem)
        assert annotations["path"] is str, f"Expected 'path: str', got {annotations['path']!r}"


# ---------------------------------------------------------------------------
# TestFromAC_ReturnAnnotations  (AC3, AC5)
# ---------------------------------------------------------------------------


class TestFromAC_ReturnAnnotations:
    """AC3 + AC5: project_info → ProjectInfoResult; project_list → list[ProjectListItem]."""

    def test_project_info_return_annotation_is_project_info_result(self) -> None:
        """project_info return annotation resolves to ProjectInfoResult (not a union)."""
        hints = typing.get_type_hints(project_info)
        return_type = hints.get("return")
        assert return_type is ProjectInfoResult, f"Expected return type ProjectInfoResult, got {return_type!r}"

    def test_project_info_return_annotation_not_a_union(self) -> None:
        """project_info return annotation is not a Union — no | str fallback."""
        hints = typing.get_type_hints(project_info)
        return_type = hints.get("return")
        # A union type would have __args__ with str in it
        args = getattr(return_type, "__args__", None)
        if args is not None:
            assert str not in args, f"project_info return type must not include str in union; args: {args}"

    def test_project_list_return_annotation_origin_is_list(self) -> None:
        """project_list return annotation has __origin__ == list."""
        hints = typing.get_type_hints(project_list)
        return_type = hints.get("return")
        origin = getattr(return_type, "__origin__", None)
        assert origin is list, f"Expected list[...] return type (origin=list), got origin={origin!r} on {return_type!r}"

    def test_project_list_return_annotation_item_type_is_project_list_item(self) -> None:
        """project_list return annotation args contain ProjectListItem."""
        hints = typing.get_type_hints(project_list)
        return_type = hints.get("return")
        args = getattr(return_type, "__args__", ())
        assert len(args) == 1, f"Expected list[ProjectListItem] with 1 type arg, got {args!r}"
        assert args[0] is ProjectListItem, f"Expected list item type ProjectListItem, got {args[0]!r}"


# ---------------------------------------------------------------------------
# TestFromAC_UnchangedReturnTypes  (AC6)
# ---------------------------------------------------------------------------


class TestFromAC_UnchangedReturnTypes:
    """AC6: project_readme and project_structure return annotations remain str (unchanged)."""

    def test_project_readme_return_annotation_is_str(self) -> None:
        """project_readme return annotation is str (TypedDict not applied here)."""
        hints = typing.get_type_hints(project_readme)
        return_type = hints.get("return")
        assert return_type is str, f"project_readme must return str (unchanged), got {return_type!r}"

    def test_project_structure_return_annotation_is_str(self) -> None:
        """project_structure return annotation is str (TypedDict not applied here)."""
        hints = typing.get_type_hints(project_structure)
        return_type = hints.get("return")
        assert return_type is str, f"project_structure must return str (unchanged), got {return_type!r}"


# ---------------------------------------------------------------------------
# TestFromAC_TypedDictModuleScope  (AC7, AC8)
# ---------------------------------------------------------------------------


class TestFromAC_TypedDictModuleScope:
    """AC7 + AC8: TypedDicts at module scope (not under TYPE_CHECKING); in __all__."""

    def test_project_info_result_importable_at_runtime(self) -> None:
        """ProjectInfoResult is accessible in the server module namespace at runtime.

        If defined under 'if TYPE_CHECKING:', TYPE_CHECKING is False at runtime
        and the name would not exist in the module dict.
        """
        assert hasattr(server_mod, "ProjectInfoResult"), (
            "ProjectInfoResult not found in server module namespace — possibly defined under if TYPE_CHECKING: (wrong)"
        )

    def test_project_list_item_importable_at_runtime(self) -> None:
        """ProjectListItem is accessible in the server module namespace at runtime."""
        assert hasattr(server_mod, "ProjectListItem"), (
            "ProjectListItem not found in server module namespace — possibly defined under if TYPE_CHECKING: (wrong)"
        )

    def test_project_info_result_is_actual_typeddict_not_stub(self) -> None:
        """ProjectInfoResult at runtime is a real TypedDict class, not a stub/Any."""
        cls = server_mod.ProjectInfoResult
        assert typing.is_typeddict(cls), (
            "server_mod.ProjectInfoResult is not a TypedDict at runtime — may be a stub or Any from TYPE_CHECKING guard"
        )

    def test_dunder_all_includes_project_info_result(self) -> None:
        """server.__all__ includes 'ProjectInfoResult'."""
        assert hasattr(server_mod, "__all__"), "server.py has no __all__"
        assert "ProjectInfoResult" in server_mod.__all__, (
            f"'ProjectInfoResult' missing from __all__; got: {server_mod.__all__!r}"
        )

    def test_dunder_all_includes_project_list_item(self) -> None:
        """server.__all__ includes 'ProjectListItem'."""
        assert hasattr(server_mod, "__all__"), "server.py has no __all__"
        assert "ProjectListItem" in server_mod.__all__, (
            f"'ProjectListItem' missing from __all__; got: {server_mod.__all__!r}"
        )
