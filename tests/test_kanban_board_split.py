"""Failing tests for #1225: Frontend — split KanbanBoard into Card + Column + Board.

Covers AC lines with (td:1) — smoke tests only:
- AC#1 (td:1): Card component and CardProps extracted to components/Card.tsx;
               PRIORITY_COLORS co-located there (Card's only consumer);
               Task imported from ../hooks/useBoard
- AC#2 (td:1): Column component and ColumnProps extracted to components/Column.tsx;
               imports Card from ./Card and Task from ../hooks/useBoard
- AC#4 (td:1): Card.tsx and Column.tsx introduce no React.memo/useMemo/useCallback
               (React Compiler handles memoisation automatically)
"""

from __future__ import annotations

from pathlib import Path

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"
_COMPONENTS = _WEB / "src" / "components"


class TestFromAC_CardExtraction:
    """Smoke tests for AC#1: Card component extracted to components/Card.tsx."""

    def test_card_tsx_exists(self) -> None:
        """Card.tsx must exist at serve/cockpit/web/src/components/Card.tsx."""
        assert (_COMPONENTS / "Card.tsx").exists(), (
            "components/Card.tsx not found — extract Card component from KanbanBoard.tsx "
            "to serve/cockpit/web/src/components/Card.tsx"
        )

    def test_card_tsx_has_priority_colors(self) -> None:
        """PRIORITY_COLORS must be co-located in Card.tsx (Card is its only consumer)."""
        src = (_COMPONENTS / "Card.tsx").read_text()
        assert "PRIORITY_COLORS" in src, (
            "PRIORITY_COLORS not found in Card.tsx — move the constant from "
            "KanbanBoard.tsx to Card.tsx (Card is its only consumer)"
        )

    def test_card_tsx_imports_task_from_useboard(self) -> None:
        """Card.tsx must import the Task type from ../hooks/useBoard."""
        src = (_COMPONENTS / "Card.tsx").read_text()
        assert "../hooks/useBoard" in src, (
            "Card.tsx does not import from '../hooks/useBoard' — the Task type must be imported from that path"
        )


class TestFromAC_ColumnExtraction:
    """Smoke tests for AC#2: Column component extracted to components/Column.tsx."""

    def test_column_tsx_exists(self) -> None:
        """Column.tsx must exist at serve/cockpit/web/src/components/Column.tsx."""
        assert (_COMPONENTS / "Column.tsx").exists(), (
            "components/Column.tsx not found — extract Column component from KanbanBoard.tsx "
            "to serve/cockpit/web/src/components/Column.tsx"
        )

    def test_column_tsx_imports_card_from_card(self) -> None:
        """Column.tsx must import Card from ./Card (sibling file)."""
        src = (_COMPONENTS / "Column.tsx").read_text()
        assert "./Card" in src, (
            "Column.tsx does not import Card from './Card' — "
            "add the sibling import from the extracted Card component file"
        )

    def test_column_tsx_imports_task_from_useboard(self) -> None:
        """Column.tsx must import the Task type from ../hooks/useBoard."""
        src = (_COMPONENTS / "Column.tsx").read_text()
        assert "../hooks/useBoard" in src, (
            "Column.tsx does not import from '../hooks/useBoard' — the Task type must be imported from that path"
        )


class TestFromAC_NoMemoWrappers:
    """Smoke tests for AC#4: Card.tsx and Column.tsx must not introduce memo wrappers.

    React Compiler handles memoisation automatically — manual wrappers must not be added.
    See also: test_cockpit_react_compiler_1015.py (TestFromAC_KanbanBoardMemoRemoval).
    """

    def test_card_tsx_no_memo_wrappers(self) -> None:
        """Card.tsx must not use React.memo, useMemo, or useCallback."""
        src = (_COMPONENTS / "Card.tsx").read_text()
        assert "React.memo" not in src, (
            "Card.tsx uses React.memo — React Compiler handles memoisation automatically; remove the wrapper"
        )
        assert "useMemo" not in src, (
            "Card.tsx uses useMemo — React Compiler handles memoisation automatically; remove the wrapper"
        )
        assert "useCallback" not in src, (
            "Card.tsx uses useCallback — React Compiler handles memoisation automatically; remove the wrapper"
        )

    def test_column_tsx_no_memo_wrappers(self) -> None:
        """Column.tsx must not use React.memo, useMemo, or useCallback."""
        src = (_COMPONENTS / "Column.tsx").read_text()
        assert "React.memo" not in src, (
            "Column.tsx uses React.memo — React Compiler handles memoisation automatically; remove the wrapper"
        )
        assert "useMemo" not in src, (
            "Column.tsx uses useMemo — React Compiler handles memoisation automatically; remove the wrapper"
        )
        assert "useCallback" not in src, (
            "Column.tsx uses useCallback — React Compiler handles memoisation automatically; remove the wrapper"
        )
