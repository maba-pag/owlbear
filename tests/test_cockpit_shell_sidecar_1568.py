"""Failing tests for P2-05 GREEN: Shell/sidecar inspector verification gate (#1568).

RED phase — all tests must fail until the builder implements the required changes.

AC coverage:
  - AC-1: All 18 Playwright tests in shell-sidecar-inspector-1562.spec.ts pass
          (covered by existing E2E spec — no new Python tests required for this AC;
          see serve/cockpit/web/e2e/shell-sidecar-inspector-1562.spec.ts)
  - AC-2: Nav-rail PButton in Shell.tsx no longer uses tabIndex={-1}
          (source inspection — Shell.tsx:168 currently has tabIndex={-1})
  - AC-3: Desktop screenshot artifact exists at .owlbear/scratch/1568-sidecar-desktop.png
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TSX = _REPO_ROOT / "serve" / "cockpit" / "web" / "src" / "Shell.tsx"
_SCREENSHOT_PATH = _REPO_ROOT / ".owlbear" / "scratch" / "1568-sidecar-desktop.png"


class TestFromAC_NavRailTabIndex:
    """AC-2: Nav-rail PButton in Shell.tsx must not carry tabIndex={-1}.

    Shell.tsx:168 currently has `tabIndex={-1}` on the <PButton data-surface="kanban">
    inside <nav className="shell__nav-rail">.  This excludes the button from the natural
    keyboard tab order, making the nav surface unreachable via Tab.  The builder must
    remove the attribute so the button participates in normal focus traversal.

    Exception per AC-2: tabIndex={-1} on role="dialog" containers (HealthBadge popover,
    DRStatusIndicator popover, ResolveModal, ConfirmDialog) is focus-management for
    modals/popovers and must NOT be removed.  Tests in this class check ONLY the
    nav-rail PButton context, not modal containers.
    """

    def test_shell_tsx_nav_rail_pbutton_has_no_tabindex_negative_one(self) -> None:
        """AC-2: The nav-rail PButton must not use tabIndex={-1}.

        RED: Shell.tsx:168 has `tabIndex={-1}` on the PButton nested inside
        <nav className="shell__nav-rail">.  This test isolates the nav-rail <nav>
        block and asserts that no tabIndex={-1} attribute appears within it.

        Isolation strategy: extract the content between the opening
        <nav class="shell__nav-rail"> and its matching </nav> so that excepted
        tabIndex={-1} usages elsewhere (modals, popovers) do not cause false failures.
        """
        text = _SHELL_TSX.read_text(encoding="utf-8")

        nav_rail_match = re.search(
            r"<nav[^>]+shell__nav-rail[^>]*>(.*?)</nav>",
            text,
            re.DOTALL,
        )
        assert nav_rail_match is not None, (
            "Shell.tsx must contain a <nav> element with class shell__nav-rail. "
            "If the nav-rail was removed entirely, update this test to reflect the "
            "new keyboard-navigation strategy."
        )

        nav_rail_content = nav_rail_match.group(1)
        assert "tabIndex={-1}" not in nav_rail_content, (
            "Nav-rail PButton must not use tabIndex={-1}. "
            "Shell.tsx:168 currently has this attribute, which removes the button "
            "from the keyboard tab order. Remove tabIndex={-1} from the PButton "
            "inside <nav className=shell__nav-rail> to restore keyboard accessibility."
        )

    def test_shell_tsx_nav_rail_pbutton_has_tab_reachable_pbutton(self) -> None:
        """AC-2: Nav-rail PButton must exist and have no tab-exclusion attribute.

        Complements the previous test: confirms the PButton is present (not removed)
        and does not carry tabIndex with any negative value.

        RED: Currently fails because `tabIndex={-1}` IS present on the PButton
        at Shell.tsx:168 — the regex match for a tab-excluded PButton succeeds
        when it should not.
        """
        text = _SHELL_TSX.read_text(encoding="utf-8")

        nav_rail_match = re.search(
            r"<nav[^>]+shell__nav-rail[^>]*>(.*?)</nav>",
            text,
            re.DOTALL,
        )
        assert nav_rail_match is not None, "Shell.tsx must contain a <nav> with class shell__nav-rail."
        nav_rail_content = nav_rail_match.group(1)

        # PButton must be present inside nav-rail (not removed)
        assert "<PButton" in nav_rail_content, "Nav-rail must contain a PButton element for keyboard navigation."

        # Assert there is NO PButton inside nav-rail that carries a negative tabIndex.
        # This catches both tabIndex={-1} and tabIndex={-2} etc.
        tab_excluded_pbutton = re.search(
            r"<PButton[^>]*tabIndex=\{-\d+\}",
            nav_rail_content,
        )
        assert tab_excluded_pbutton is None, (
            f"Nav-rail PButton must not carry a negative tabIndex. "
            f"Found: {tab_excluded_pbutton.group(0) if tab_excluded_pbutton else 'N/A'}. "
            "Remove the tabIndex={-1} attribute from the PButton at Shell.tsx:168."
        )


class TestFromAC_ScreenshotArtifact:
    """AC-3: Builder must capture and save desktop screenshot evidence.

    AC-3 requires a screenshot showing (a) the selected-task sidecar with header,
    metadata, body, and actions regions visible and (b) the status bar with product
    identity heading and labeled controls.  The screenshot must be saved at:
        .owlbear/scratch/1568-sidecar-desktop.png

    RED: The file does not exist yet — all tests in this class fail with FileNotFoundError
    or assertion failure until the builder captures and saves the screenshot.
    """

    def test_sidecar_desktop_screenshot_artifact_exists(self) -> None:
        """AC-3: Screenshot artifact must exist at the specified path.

        RED: .owlbear/scratch/1568-sidecar-desktop.png does not exist.
        Builder must run: await page.screenshot({ path: '.owlbear/scratch/1568-sidecar-desktop.png' })
        (or equivalent) during the E2E session and commit the file.
        """
        assert _SCREENSHOT_PATH.exists(), (
            f"Desktop screenshot artifact not found at {_SCREENSHOT_PATH}. "
            "Builder: capture a Playwright desktop screenshot showing the sidecar "
            "inspector and status bar, and save it to .owlbear/scratch/1568-sidecar-desktop.png."
        )

    def test_sidecar_desktop_screenshot_is_valid_png(self) -> None:
        """AC-3: Screenshot artifact must be a valid PNG file.

        RED: File does not exist — the exists() assertion fails first, preventing
        the PNG-signature check.  After the builder creates the file, this test
        validates that the file is not empty or corrupt.
        """
        assert _SCREENSHOT_PATH.exists(), f"Screenshot artifact must exist before PNG validation: {_SCREENSHOT_PATH}"
        header = _SCREENSHOT_PATH.read_bytes()[:8]
        # PNG magic bytes: 0x89 'P' 'N' 'G' \r \n 0x1a \n
        assert header == b"\x89PNG\r\n\x1a\n", (
            f"Screenshot artifact at {_SCREENSHOT_PATH} is not a valid PNG file. "
            "Expected PNG magic bytes 89 50 4E 47 0D 0A 1A 0A."
        )

    def test_sidecar_desktop_screenshot_has_nonzero_size(self) -> None:
        """AC-3: Screenshot artifact must not be an empty file.

        RED: File does not exist — the exists() assertion fails first.
        After the builder creates the file, this test guards against a 0-byte artifact
        written by a failed screenshot call that still created the file.
        """
        assert _SCREENSHOT_PATH.exists(), f"Screenshot artifact must exist: {_SCREENSHOT_PATH}"
        size = _SCREENSHOT_PATH.stat().st_size
        assert size > 1024, (  # A real desktop screenshot is several KB at minimum
            f"Screenshot artifact at {_SCREENSHOT_PATH} is too small ({size} bytes). "
            "Expected a real desktop-viewport PNG (>1 KB). "
            "Capture the screenshot at 1280x800 viewport or larger."
        )
