"""Failing tests for task #1433: P1-05 — Panel Output Phrasing section in h-ideation-panel/SKILL.md.

All tests must FAIL on the current codebase; they pass once the builder adds the section.

AC coverage:
  AC1 — test_panel_output_phrasing_section_exists
  AC2 — test_section_instructs_descriptive_headers,
         test_section_discourages_protocol_coded_headers
  AC3 — test_section_mentions_mediator_quoting,
         test_section_mentions_user_readability
  AC4 — test_section_length_within_bounds
  AC5 — test_new_section_does_not_displace_existing_sections
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / "share" / "skills" / "h-ideation-panel" / "SKILL.md"

_SECTION_HEADING = "## Panel Output Phrasing"

# Top-level section headers present before this task — must remain after the edit (AC5).
_EXPECTED_EXISTING_SECTIONS = (
    "## Panel Surface Map",
    "## Early Challenge Lane",
    "## Late Domain Panel",
    "## Critic Loop Protocol",
    "## Pragmatist Modes",
    "## Disagreement Resolution",
    "## Panelist References",
)


def _read_skill() -> str:
    return _SKILL_FILE.read_text(encoding="utf-8")


def _extract_section_body(content: str) -> str | None:
    """Return body text of '## Panel Output Phrasing', or None if the heading is absent.

    Stops at the next ``## ``-level heading so the count is bounded to the section.
    """
    lines = content.splitlines()
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == _SECTION_HEADING:
            start_idx = i
            break
    if start_idx is None:
        return None
    body: list[str] = []
    for line in lines[start_idx + 1 :]:
        if re.match(r"^##\s", line):
            break
        body.append(line)
    return "\n".join(body)


class TestFromAC_PanelOutputPhrasing:
    """Content verification for the Panel Output Phrasing section. Task #1433."""

    # ---- AC1: section heading present ------------------------------------------------------

    def test_panel_output_phrasing_section_exists(self) -> None:
        """'## Panel Output Phrasing' heading must exist in h-ideation-panel/SKILL.md."""
        content = _read_skill()
        assert _SECTION_HEADING in content, (
            f"Section '{_SECTION_HEADING}' is missing from {_SKILL_FILE.name}"
        )

    # ---- AC2: descriptive vs. protocol-coded header guidance -------------------------------

    def test_section_instructs_descriptive_headers(self) -> None:
        """Section must instruct panelists to use descriptive section headers."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        assert re.search(r"\bdescriptive\b", body, re.IGNORECASE), (
            "Section must include the word 'descriptive' to guide header style"
        )

    def test_section_discourages_protocol_coded_headers(self) -> None:
        """Section must convey that protocol-coded or jargon headers should be avoided."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        # The guidance must contrast descriptive with coded/jargon/protocol formats.
        assert re.search(
            r"protocol.coded|coded header|jargon|O\d+[\-:]|avoid|rather than|instead of",
            body,
            re.IGNORECASE,
        ), (
            "Section must reference the anti-pattern (protocol-coded / jargon headers) "
            "so panelists know what to avoid"
        )

    # ---- AC3: mediator quoting and user readability ----------------------------------------

    def test_section_mentions_mediator_quoting(self) -> None:
        """Section must state that stance files may be quoted by the mediator."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        assert re.search(r"\bmediator\b", body, re.IGNORECASE), (
            "Section must mention the mediator in the context of stance file quoting"
        )

    def test_section_mentions_user_readability(self) -> None:
        """Headers must be described as readable to the user without translation."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        assert re.search(r"\buser\b|\breadable\b|\btranslation\b", body, re.IGNORECASE), (
            "Section must convey that headers should be readable to the user without translation"
        )

    # ---- AC4: section brevity (5-10 non-blank lines) ----------------------------------------

    def test_section_length_within_bounds(self) -> None:
        """Section body must be 5-10 non-blank lines (AC4 brevity: light addition, not rewrite)."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        non_blank = [ln for ln in body.splitlines() if ln.strip()]
        count = len(non_blank)
        assert 5 <= count <= 10, (
            f"Section must have 5-10 non-blank lines; found {count}"
        )

    # ---- AC5: existing sections must not be displaced -------------------------------------

    def test_new_section_does_not_displace_existing_sections(self) -> None:
        """New section must be added without removing any pre-existing top-level sections."""
        content = _read_skill()
        # Fails on current codebase because the new section is absent.
        assert _SECTION_HEADING in content, (
            f"New section '{_SECTION_HEADING}' is missing — required for AC5 guard to apply"
        )
        missing = [h for h in _EXPECTED_EXISTING_SECTIONS if h not in content]
        assert not missing, (
            f"Existing sections were removed or renamed (AC5 violation): {missing}"
        )
