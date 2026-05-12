"""RED phase tests — structured JSON error responses at MCP boundary (#1362).

Tests verify that _map_kanban_error emits JSON-structured ToolError messages,
enabling agents to programmatically distinguish error types.

AC coverage:
- AC1: _map_kanban_error emits json.dumps({"code": ..., "message": ...})
- AC2: ToolError text is structured JSON, not bare user_message (regression guards)
- AC3: agents can parse error codes from ToolError text
- AC4: human-readable message still present in JSON structure
"""

from __future__ import annotations

import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import (
    ConcurrencyError,
    MigrationRequiredError,
    NotFoundError,
    ValidationError,
)
from owlbear_mcp_kanban.server import _map_kanban_error


# ---------------------------------------------------------------------------
# TestFromAC_StructuredJsonErrors
# AC1: _map_kanban_error emits json.dumps({"code": exc.code, "message": exc.user_message})
# AC3: agents can parse error codes from ToolError text
# AC4: human-readable message still present in JSON structure
# ---------------------------------------------------------------------------


class TestFromAC_StructuredJsonErrors:
    """_map_kanban_error emits JSON-structured ToolError messages."""

    # -- happy path --

    def test_map_kanban_error_emits_parseable_json(self) -> None:
        """AC1: ToolError message from _map_kanban_error is valid JSON, not bare text."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message="task 99 not found")
            )
        # Currently raises ToolError("task 99 not found") — not valid JSON → json.JSONDecodeError
        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    def test_map_kanban_error_json_contains_code_field(self) -> None:
        """AC1: JSON payload has 'code' key."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message="task 99 not found")
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload, "JSON payload must contain 'code' field"

    def test_map_kanban_error_json_code_equals_exc_code(self) -> None:
        """AC1: JSON 'code' field value equals exc.code exactly."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message="task 99 not found")
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    def test_map_kanban_error_json_contains_message_field(self) -> None:
        """AC1/AC4: JSON payload has 'message' key for human-readable text."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                ValidationError(
                    code="ERR_INVALID_STATUS", user_message="invalid status"
                )
            )
        payload = json.loads(str(exc_info.value))
        assert "message" in payload, "JSON payload must contain 'message' field"

    def test_map_kanban_error_json_message_equals_user_message(self) -> None:
        """AC4: human-readable message preserved verbatim in JSON 'message' field."""
        user_msg = "task 42 not found"
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)
            )
        payload = json.loads(str(exc_info.value))
        assert payload["message"] == user_msg, (
            "message field must equal exc.user_message"
        )

    # -- edge cases --

    def test_map_kanban_error_err_stale_code_in_json(self) -> None:
        """AC3: ERR_STALE code appears as JSON 'code' — agents use this to trigger retry."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                ConcurrencyError(
                    code="ERR_STALE",
                    user_message="stale write; reload and retry",
                )
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_STALE", (
            "ERR_STALE must appear as 'code' in JSON for agent retry routing"
        )

    def test_map_kanban_error_err_already_claimed_code_in_json(self) -> None:
        """AC3: ERR_ALREADY_CLAIMED code parseable — agents use this to wait or skip."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                ConcurrencyError(
                    code="ERR_ALREADY_CLAIMED",
                    user_message="already claimed at 2026-01-01T00:00:00+00:00",
                )
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_ALREADY_CLAIMED"

    def test_map_kanban_error_err_not_found_stop_signal(self) -> None:
        """AC3: ERR_NOT_FOUND code parseable — agents use this to stop (no retry)."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message="task 999 not found")
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    # -- error paths --

    def test_map_kanban_error_validation_error_code_and_message_in_json(self) -> None:
        """ValidationError: both code and message preserved in JSON payload."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                ValidationError(
                    code="ERR_BLOCK_REASON_REQUIRED",
                    user_message="block_reason is required when outcome=block",
                )
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_BLOCK_REASON_REQUIRED"
        assert payload["message"] == "block_reason is required when outcome=block"

    def test_map_kanban_error_migration_required_code_in_json(self) -> None:
        """MigrationRequiredError: code and message both in JSON payload."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                MigrationRequiredError(
                    code="ERR_MIGRATION_REQUIRED",
                    user_message="board requires migration before use",
                )
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_MIGRATION_REQUIRED"
        assert "migration" in payload["message"].lower()

    # -- boundary conditions --

    def test_map_kanban_error_message_is_json_object_not_bare_string(self) -> None:
        """AC2: ToolError message is a JSON object, not the bare user_message string."""
        user_msg = "task 99 not found"
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)
            )
        err_str = str(exc_info.value)
        # Bare user_message string does not start with '{'
        assert err_str.startswith("{"), (
            "ToolError message must be a JSON object (starts with '{'), not a bare string"
        )

    def test_agent_can_parse_error_code_from_tool_error_text(self) -> None:
        """AC3: agent workflow — extract error code from ToolError text via json.loads."""
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message="task 1 not found")
            )
        # Simulate what an agent does: parse error code from ToolError text
        tool_error_text = str(exc_info.value)
        parsed = json.loads(tool_error_text)
        code = parsed["code"]
        assert code == "ERR_NOT_FOUND", (
            "agent must extract error code from JSON to determine routing (stop/retry/etc.)"
        )

    def test_map_kanban_error_user_message_with_special_chars_round_trips(self) -> None:
        """AC1: user_message containing quotes/slashes is safely JSON-encoded and round-trips."""
        user_msg = 'task "alpha/beta" not found'
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(
                NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)
            )
        payload = json.loads(str(exc_info.value))
        assert payload["message"] == user_msg, (
            "JSON encoding must preserve user_message including quotes and slashes"
        )
