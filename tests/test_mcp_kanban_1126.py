"""Structural regression guard — TypeError fallback chain removal in MCP server (#1126).

AC3 (surviving): Verifies 'except TypeError' blocks have been removed from server.py.
AC1/AC2 behavioral tests removed — _canonical_agent_view_for was deleted in #1360.
"""

from __future__ import annotations

from pathlib import Path

import owlbear_mcp_kanban.server as _server_mod

# ---------------------------------------------------------------------------
# TestFromAC_DeadTypeErrorFallback
# ---------------------------------------------------------------------------


class TestFromAC_DeadTypeErrorFallback:
    """Dead TypeError fallback chains must be removed from end_work and move_task."""

    # ------------------------------------------------------------------
    # AC3 — structural: 'except TypeError' absent from server source
    # ------------------------------------------------------------------

    def test_no_except_typeerror_in_server_source(self) -> None:
        """AC3: After cleanup, 'except TypeError' must not appear anywhere in server.py.

        Expected (GREEN): both 'except TypeError' blocks removed.  String absent
        from source.  Assertion passes.

        Structural evidence requirement: behavioral tests prove the fallbacks are
        unreachable but cannot prove the dead branches are actually gone from the
        source.  This test satisfies that evidence gap (see review-dead-code-
        structural-evidence).
        """
        source = Path(_server_mod.__file__).read_text(encoding="utf-8")
        assert "except TypeError" not in source

