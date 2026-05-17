"""Source-level shell and sidecar inspector regression tests."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TSX = _REPO_ROOT / "serve" / "cockpit" / "web" / "src" / "Shell.tsx"


class TestNavRailTabIndex:
    """Nav-rail PButton in Shell.tsx must not carry tabIndex={-1}.

    Exception: tabIndex={-1} on role="dialog" containers (HealthBadge popover,
    DRStatusIndicator popover, ResolveModal, ConfirmDialog) is focus-management for
    modals/popovers and must NOT be removed.  Tests in this class check ONLY the
    nav-rail PButton context, not modal containers.
    """

    def _nav_rail_content(self) -> str:
        text = _SHELL_TSX.read_text(encoding="utf-8")
        nav_rail_match = re.search(
            r"<nav[^>]+data-region=\"nav-rail\"[^>]*>(.*?)</nav>",
            text,
            re.DOTALL,
        )
        assert nav_rail_match is not None, (
            'Shell.tsx must contain a <nav> element with data-region="nav-rail". '
            "If the nav rail was removed entirely, update this test to reflect the "
            "new keyboard-navigation strategy."
        )
        return nav_rail_match.group(1)

    def test_shell_tsx_nav_rail_pbutton_has_no_tabindex_negative_one(self) -> None:
        """The nav-rail PButton must not use tabIndex={-1}."""
        nav_rail_content = self._nav_rail_content()
        assert "tabIndex={-1}" not in nav_rail_content, (
            "Nav-rail PButton must not use tabIndex={-1}. "
            "Shell.tsx:168 currently has this attribute, which removes the button "
            "from the keyboard tab order. Remove tabIndex={-1} from the PButton "
            "inside <nav className=shell__nav-rail> to restore keyboard accessibility."
        )

    def test_shell_tsx_nav_rail_pbutton_has_tab_reachable_pbutton(self) -> None:
        """Nav-rail PButton must exist and have no tab-exclusion attribute."""
        nav_rail_content = self._nav_rail_content()

        assert 'data-surface="kanban"' in nav_rail_content, "Nav-rail must contain the Kanban navigation control."

        tab_excluded_pbutton = re.search(
            r"<(?:PButton|button)[^>]*tabIndex=\{-\d+\}",
            nav_rail_content,
        )
        assert tab_excluded_pbutton is None, (
            f"Nav-rail PButton must not carry a negative tabIndex. "
            f"Found: {tab_excluded_pbutton.group(0) if tab_excluded_pbutton else 'N/A'}. "
            "Remove the tabIndex={-1} attribute from the PButton at Shell.tsx:168."
        )
