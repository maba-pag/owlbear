"""RED phase tests — stale dict-form mock fix in test_mcp_lifecycle_tools.py (#1173).

The mock helper ``_make_engine_mock`` in ``test_mcp_lifecycle_tools.py`` sets::

    engine.board_config.return_value.statuses = [{"name": s} for s in [...]]

Post-Brief-C ``BoardConfig.statuses`` is ``list[str]``, so this dict-form
mock is stale.  It is harmless for existing tests (the AgentView path returns
before L481 is reached), but it prevents any new test from verifying that
guidance flows correctly through the fallback path.

The builder must update the mock to::

    engine.board_config.return_value.statuses = [
        "research", "backlog", "todo", "in-progress", "review", "docs", "done"
    ]

Tests in this file import ``_make_engine_mock`` directly from
``test_mcp_lifecycle_tools.py`` so they automatically pass once the builder
fixes the mock.

AC coverage:
- AC2: mock returns ``list[str]`` not ``list[dict]`` for statuses
- AC4: ``move_task`` adapter returns non-empty guidance for forward-skip
  when the fallback path is active (``engine.agent_view = None``)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_kanban.server import move_task

# ---------------------------------------------------------------------------
# Import _make_engine_mock from the file under test
# ---------------------------------------------------------------------------

_LIFECYCLE_TOOLS_PATH = Path(__file__).parent.parent / "serve" / "mcp-kanban" / "tests" / "test_mcp_lifecycle_tools.py"
_spec = importlib.util.spec_from_file_location("_lifecycle_tools", _LIFECYCLE_TOOLS_PATH)
assert _spec is not None
assert _spec.loader is not None
_lifecycle_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lifecycle_mod)  # type: ignore[union-attr]
_make_engine_mock = _lifecycle_mod._make_engine_mock  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Shared task dict helpers
# ---------------------------------------------------------------------------

_RESEARCH_TASK: dict = {
    "id": 1,
    "title": "Alpha",
    "status": "research",
    "priority": "needed",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T01:00:00+00:00",
    "claimed": False,
    "tags": [],
    "body": None,
    "blocked": False,
    "block_reason": None,
    "parent": None,
    "depends_on": [],
}

_TODO_TASK: dict = {**_RESEARCH_TASK, "status": "todo"}


def _make_fallback_ctx(
    *,
    before_dict: dict,
    after_dict: dict,
) -> MagicMock:
    """Build a MCP Context whose engine mock forces the L481 fallback path.

    ``engine.agent_view = None`` disables both AgentView paths so
    ``move_task`` falls through to the L481 ``board_config().statuses``
    guidance collection.  ``show_task`` returns *before_dict*; ``move_task``
    returns *after_dict*.
    """
    av = MagicMock()
    engine = _make_engine_mock(av)
    # Disable AgentView to ensure the fallback path at L481 executes
    engine.agent_view = None
    # Pre-read task (used by _show_validated)
    engine.show_task.return_value.model_dump.return_value = before_dict
    # Post-move task
    engine.move_task.return_value.model_dump.return_value = after_dict

    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_StatusNamesMockContract
# AC2: _make_engine_mock must provide list[str] statuses, not list[dict].
# ---------------------------------------------------------------------------


class TestFromAC_StatusNamesMockContract:
    """``_make_engine_mock`` must return ``list[str]`` for ``board_config().statuses``.

    These tests fail until the builder updates the mock in
    ``test_mcp_lifecycle_tools.py`` to use string-form statuses.
    """

    def test_engine_mock_statuses_are_list_of_strings(self) -> None:
        """board_config().statuses returns list[str], not list[dict].

        FAILS: stale mock returns ``[{"name": "research"}, ...]`` (dict-form).
        PASSES: after builder changes mock to ``["research", "backlog", ...]``.
        """
        av = MagicMock()
        engine = _make_engine_mock(av)
        statuses = engine.board_config().statuses
        assert all(isinstance(s, str) for s in statuses), (
            f"Expected list[str] for statuses but got {statuses!r}. "
            f"Fix: replace dict-comprehension in test_mcp_lifecycle_tools._make_engine_mock "
            f"with plain list[str]: ['research', 'backlog', ...]"
        )

    def test_engine_mock_statuses_contain_expected_pipeline_columns(self) -> None:
        """board_config().statuses contains the standard 7-column pipeline.

        FAILS: stale dict-form elements are not equal to plain strings, so
        the membership check fails for every column name.
        PASSES: after builder changes mock to list[str].
        """
        av = MagicMock()
        engine = _make_engine_mock(av)
        statuses = engine.board_config().statuses
        for expected in ("research", "todo", "done"):
            assert expected in statuses, (
                f"Expected {expected!r} in statuses list, got {statuses!r}. "
                f"Stale dict-form mock does not compare equal to plain strings."
            )


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskGuidanceViaMock
# AC4: move_task adapter returns non-empty guidance for forward-skip via
#      the fallback path, with the mock providing correct list[str] statuses.
# ---------------------------------------------------------------------------
