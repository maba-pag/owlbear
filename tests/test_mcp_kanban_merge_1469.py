"""RED-phase tests — mcp_kanban task-scoped test file merge (#1469).

AC1 (td:1): All unique def test_* from 7 source files present in test_mcp_kanban.py.
  Known collision rename: test_edit_task_has_no_status_parameter (1091)
  → test_edit_task_has_no_status_parameter_1091 in durable.

AC4 (td:1): All 7 source files deleted after merge.
"""

from __future__ import annotations

import ast
import pathlib
from typing import ClassVar

import pytest

TESTS_DIR = pathlib.Path(__file__).parent
DURABLE = TESTS_DIR / "test_mcp_kanban.py"

_SOURCE_FILES = [
    TESTS_DIR / "test_mcp_kanban_1091.py",
    TESTS_DIR / "test_mcp_kanban_1092.py",
    TESTS_DIR / "test_mcp_kanban_1126.py",
    TESTS_DIR / "test_mcp_kanban_1196.py",
    TESTS_DIR / "test_mcp_kanban_1197.py",
    TESTS_DIR / "test_mcp_kanban_1360.py",
    TESTS_DIR / "test_mcp_kanban_1450.py",
]


def _collect_test_names(filepath: pathlib.Path) -> set[str]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


class TestFromAC_SourceFilesDeleted:
    """AC4 (td:1): All 7 source files deleted after merge."""

    @pytest.mark.parametrize(
        "filepath",
        _SOURCE_FILES,
        ids=[f.name for f in _SOURCE_FILES],
    )
    def test_source_file_does_not_exist(self, filepath: pathlib.Path) -> None:
        assert not filepath.exists(), (
            f"{filepath.name} still exists — must be deleted after merge"
        )


class TestFromAC_AllSourceTestsPresent:
    """AC1 (td:1): All unique def test_* from 7 source files present in test_mcp_kanban.py.

    Collision rename: test_edit_task_has_no_status_parameter (source 1091 collides with
    durable L171) → merged as test_edit_task_has_no_status_parameter_1091.
    """

    _FROM_1091: ClassVar[list[str]] = [
        "test_create_task_calls_map_kanban_error_helper",
        "test_edit_task_calls_map_kanban_error_helper",
        "test_edit_task_has_no_status_parameter_1091",  # collision rename
    ]
    _FROM_1092: ClassVar[list[str]] = [
        "test_move_task_kanban_error_routed_via_helper",
        "test_start_work_kanban_error_routed_via_helper",
        "test_end_work_kanban_error_routed_via_helper",
        "test_move_task_no_local_archival_validation_in_source",
        "test_end_work_adapter_no_param_normalization_in_source",
        "test_end_work_adapter_no_tag_mutation_in_source",
        "test_start_work_adapter_no_business_logic_in_source",
    ]
    _FROM_1126: ClassVar[list[str]] = [
        "test_no_except_typeerror_in_server_source",
    ]
    _FROM_1196: ClassVar[list[str]] = [
        "test_empty_string_rejected_with_tool_error",
        "test_wildcard_rejected_with_tool_error",
        "test_path_traversal_rejected_with_tool_error",
        "test_non_numeric_string_rejected_with_tool_error",
        "test_mixed_alphanumeric_rejected_with_tool_error",
        "test_wildcard_does_not_reach_decisions_create_dr",
        "test_empty_string_does_not_reach_decisions_create_dr",
        "test_path_traversal_does_not_reach_decisions_create_dr",
        "test_non_numeric_string_does_not_reach_decisions_create_dr",
        "test_mixed_alphanumeric_does_not_reach_decisions_create_dr",
        "test_numeric_string_coerced_to_int_before_forwarding",
        "test_literal_int_task_id_forwarded_unchanged",
    ]
    _FROM_1197: ClassVar[list[str]] = [
        "test_server_has_no_unittest_mock_import",
        "test_server_has_no_isinstance_mock_check",
        "test_agent_view_for_not_defined_in_server",
        "test_server_1170_make_engine_mock_uses_noncallable_agent_view",
        "test_lifecycle_tools_mock_av_fixture_uses_noncallable_agent_view",
    ]
    _FROM_1360: ClassVar[list[str]] = [
        "test_canonical_agent_view_for_helper_removed",
        "test_invoke_view_move_task_removed",
        "test_invoke_view_end_work_removed",
        "test_invoke_engine_end_work_removed",
        "test_server_module_line_count_reduced",
        "test_move_task_not_implemented_propagates_without_fallback",
        "test_start_work_not_implemented_propagates_without_fallback",
        "test_end_work_not_implemented_propagates_without_fallback",
    ]
    _FROM_1450: ClassVar[list[str]] = [
        "test_empty_ids_returns_empty_task_list",
        "test_empty_ids_returns_empty_for_multi_task_board",
        "test_empty_ids_returns_missing_ids_is_none",
        "test_archival_reason_without_status_finds_archived_task",
        "test_archival_reason_filter_all_returned_tasks_match",
        "test_archival_reason_duplicate_excludes_completed_reason",
        "test_move_task_invalid_status_raises_tool_error_with_json_payload",
        "test_move_task_invalid_status_json_has_code_and_message",
        "test_end_work_reject_invalid_move_to_raises_tool_error_with_json_payload",
        "test_end_work_reject_invalid_move_to_json_has_code_and_message",
        "test_move_task_idempotent_hint_is_false",
        "test_pick_tasks_read_only_hint_is_true",
        "test_pick_tasks_idempotent_hint_is_true",
        "test_non_numeric_id_raises_tool_error_with_json_payload",
        "test_malformed_id_json_has_code_and_message_fields",
        "test_stale_write_via_edit_task_returns_json_envelope",
        "test_stale_write_json_has_code_and_message",
    ]

    @pytest.fixture(scope="class")
    def durable_names(self) -> set[str]:
        return _collect_test_names(DURABLE)

    @pytest.mark.parametrize("name", _FROM_1091)
    def test_merged_from_1091(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1091.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1092)
    def test_merged_from_1092(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1092.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1126)
    def test_merged_from_1126(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1126.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1196)
    def test_merged_from_1196(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1196.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1197)
    def test_merged_from_1197(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1197.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1360)
    def test_merged_from_1360(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1360.py)"
        )

    @pytest.mark.parametrize("name", _FROM_1450)
    def test_merged_from_1450(self, durable_names: set[str], name: str) -> None:
        assert name in durable_names, (
            f"test_mcp_kanban.py missing '{name}' (origin: test_mcp_kanban_1450.py)"
        )
