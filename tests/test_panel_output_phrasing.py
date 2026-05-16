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
        assert _SECTION_HEADING in content, f"Section '{_SECTION_HEADING}' is missing from {_SKILL_FILE.name}"

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
        ), "Section must reference the anti-pattern (protocol-coded / jargon headers) so panelists know what to avoid"

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
        assert 5 <= count <= 10, f"Section must have 5-10 non-blank lines; found {count}"

    # ---- AC5: existing sections must not be displaced -------------------------------------

    def test_new_section_does_not_displace_existing_sections(self) -> None:
        """New section must be added without removing any pre-existing top-level sections."""
        content = _read_skill()
        # Fails on current codebase because the new section is absent.
        assert _SECTION_HEADING in content, (
            f"New section '{_SECTION_HEADING}' is missing — required for AC5 guard to apply"
        )
        missing = [h for h in _EXPECTED_EXISTING_SECTIONS if h not in content]
        assert not missing, f"Existing sections were removed or renamed (AC5 violation): {missing}"

    # =========================================================================
    # Tightened tests added in retry cycle (cycle 2) — stronger AC2/AC3/AC5
    # =========================================================================

    # ---- AC2 (tightened): both-sides contrast + inline examples on each side ---------------

    def test_ac2_contrast_both_terms_coexist(self) -> None:
        """Section must contain BOTH 'descriptive' AND 'protocol-coded'/'jargon' — not just one side.

        Existing test only required one side; tightened AC2 requires the full contrast.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        has_descriptive = bool(re.search(r"\bdescriptive\b", body, re.IGNORECASE))
        has_negative_term = bool(re.search(r"\bprotocol.coded\b|\bjargon\b", body, re.IGNORECASE))
        assert has_descriptive, "Section must contain 'descriptive' guidance (positive side of contrast)"
        assert has_negative_term, (
            "Section must contain 'protocol-coded' or 'jargon' to establish the contrast — "
            "having 'avoid' alone is insufficient; the specific anti-pattern term is required"
        )

    def test_ac2_positive_side_has_inline_example(self) -> None:
        """The descriptive-header guidance line must include an inline 'for example' illustration."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        descriptive_lines = [ln for ln in lines if re.search(r"\bdescriptive\b", ln, re.IGNORECASE)]
        assert descriptive_lines, "No line containing 'descriptive' found in section body"
        assert any(re.search(r"for example|e\.g\.", ln, re.IGNORECASE) for ln in descriptive_lines), (
            "The descriptive-header guidance must include an inline 'for example' so "
            "panelists know what a good header looks like"
        )

    def test_ac2_negative_side_has_inline_example(self) -> None:
        """The protocol-coded-header guidance line must include an inline 'for example' illustration."""
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        negative_lines = [ln for ln in lines if re.search(r"\bprotocol.coded\b|\bjargon\b", ln, re.IGNORECASE)]
        assert negative_lines, "No line referencing 'protocol-coded' or 'jargon' found in section body"
        assert any(re.search(r"for example|e\.g\.", ln, re.IGNORECASE) for ln in negative_lines), (
            "The protocol-coded-header guidance must include an inline negative example "
            "so panelists know what pattern to avoid"
        )

    # ---- AC3 (tightened): same-line co-occurrence of key terms ----------------------------

    def test_ac3_quoted_and_mediator_same_line(self) -> None:
        """'quoted' and 'mediator' must co-occur on the same line/bullet.

        Existing test only required 'mediator' anywhere; tightened AC3 requires both terms
        to appear together to confirm the quoting-by-mediator statement is present.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        assert any(
            re.search(r"\bquoted\b", ln, re.IGNORECASE) and re.search(r"\bmediator\b", ln, re.IGNORECASE)
            for ln in lines
        ), (
            "No single line contains both 'quoted' and 'mediator' — "
            "AC3 requires their co-occurrence to confirm the stance-file-quoting statement"
        )

    def test_ac3_readable_and_without_translation_same_line(self) -> None:
        """'readable' and 'without translation' must co-occur on the same line/bullet.

        Existing test accepted any one of the three tokens; tightened AC3 requires both
        'readable' and 'without translation' on the same line to prove the full statement.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        assert any(
            re.search(r"\breadable\b", ln, re.IGNORECASE) and re.search(r"without translation", ln, re.IGNORECASE)
            for ln in lines
        ), (
            "No single line contains both 'readable' and 'without translation' — "
            "AC3 requires their co-occurrence to confirm the user-readability statement"
        )

    # ---- AC5 (tightened): section-count invariant + explicit scope-boundary phrase --------

    def test_ac5_heading_count_equals_original_plus_one(self) -> None:
        """Total top-level ## heading count must be exactly 7 pre-existing + 1 new = 8.

        Existing test only checked named headings remain; this adds the count invariant
        to catch any heading insertions or deletions beyond the single allowed addition.
        """
        content = _read_skill()
        headings = re.findall(r"^## ", content, re.MULTILINE)
        expected = len(_EXPECTED_EXISTING_SECTIONS) + 1  # 7 + 1 = 8
        assert len(headings) == expected, (
            f"Expected {expected} top-level ## headings (7 pre-existing + 1 new = 8); found {len(headings)}"
        )

    def test_ac5_scope_boundary_phrase_present(self) -> None:
        """Section body must contain 'phrasing only' (or equivalent) as an explicit scope boundary.

        Existing test only checked named headings remain; tightened AC5 requires an
        in-section statement confirming the guidance does not alter panel mechanics or
        stance file structure.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        assert re.search(r"phrasing only|phrasing-only|only phrasing", body, re.IGNORECASE), (
            "Section must include a scope-boundary statement containing 'phrasing only' "
            "or equivalent to confirm it does not alter panel mechanics or stance file structure"
        )

    # =========================================================================
    # Tightened tests added in retry cycle (cycle 3) — verb-direction AC2, line-start AC5
    # =========================================================================

    # ---- AC2 (cycle 3): affirmative bullet verb-direction --------------------------------

    def test_ac2_affirmative_bullet_starts_with_use_or_prefer(self) -> None:
        """A bullet with affirmative intent must start with 'Use' or 'Prefer', co-occur with
        'descriptive' and 'header(s)', and include an inline example.

        Cycle 2 tests checked token presence only. This verifies the polarity: the positive
        guidance line begins with an affirmative verb so reversed semantics would fail.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        affirmative_lines = [ln for ln in lines if re.match(r"[-*]\s+(Use|Prefer)\b", ln)]
        assert affirmative_lines, (
            "Section must contain a bullet starting with 'Use' or 'Prefer' (affirmative positive guidance)"
        )
        target_lines = [
            ln
            for ln in affirmative_lines
            if re.search(r"\bdescriptive\b", ln, re.IGNORECASE) and re.search(r"\bheaders?\b", ln, re.IGNORECASE)
        ]
        assert target_lines, (
            "The affirmative bullet must co-occur with 'descriptive' and 'header(s)' "
            "to target the correct guidance surface"
        )
        assert any(re.search(r"for example|e\.g\.", ln, re.IGNORECASE) for ln in target_lines), (
            "The affirmative descriptive-header guidance must include an inline 'for example' "
            "so panelists know what a good header looks like"
        )

    # ---- AC2 (cycle 3): prohibitive bullet verb-direction --------------------------------

    def test_ac2_prohibitive_bullet_starts_with_avoid(self) -> None:
        """A bullet with prohibitive intent must start with 'Avoid', co-occur with
        'protocol-coded' or 'jargon' and 'header(s)', and include an inline example.

        Cycle 2 tests checked token presence only. This verifies the polarity: the negative
        guidance line begins with a prohibitive verb so reversed semantics would fail.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        prohibitive_lines = [ln for ln in lines if re.match(r"[-*]\s+Avoid\b", ln)]
        assert prohibitive_lines, "Section must contain a bullet starting with 'Avoid' (prohibitive guidance)"
        target_lines = [
            ln
            for ln in prohibitive_lines
            if re.search(r"\bprotocol.coded\b|\bjargon\b", ln, re.IGNORECASE)
            and re.search(r"\bheaders?\b", ln, re.IGNORECASE)
        ]
        assert target_lines, (
            "The 'Avoid' bullet must co-occur with 'protocol-coded' or 'jargon' "
            "and 'header(s)' to target the correct anti-pattern"
        )
        assert any(re.search(r"for example|e\.g\.", ln, re.IGNORECASE) for ln in target_lines), (
            "The prohibitive header guidance must include an inline negative example "
            "so panelists know what pattern to avoid"
        )

    # ---- AC5 (cycle 3): line-start heading verification ---------------------------------

    def test_ac5_existing_headings_are_top_level_lines(self) -> None:
        """Each of the 7 pre-existing sections must exist as an exact top-level '## ' line.

        Cycle 2 test used substring match — a heading demoted to '### ' would still pass.
        This verifies each name appears as a line beginning with '^## ' (line-start regex).
        """
        content = _read_skill()
        top_level = {line.rstrip() for line in content.splitlines() if re.match(r"^## ", line)}
        missing = [h for h in _EXPECTED_EXISTING_SECTIONS if h not in top_level]
        assert not missing, f"These sections are no longer top-level '## ' headings (AC5 violation): {missing}"

    # ---- AC5 (cycle 3): scope-boundary co-occurrence ------------------------------------

    def test_ac5_scope_boundary_mentions_mechanics_or_structure(self) -> None:
        """The scope-boundary line must contain 'phrasing only' AND at least one of
        'panel mechanics' or 'stance file structure'.

        Cycle 2 test only required 'phrasing only' in the body; tightened AC5 requires the
        full disclaimer — the specific domains excluded must also be named on the same line.
        """
        body = _extract_section_body(_read_skill())
        assert body is not None, "Section not found — AC1 prerequisite"
        lines = body.splitlines()
        boundary_lines = [ln for ln in lines if re.search(r"phrasing only|phrasing-only", ln, re.IGNORECASE)]
        assert boundary_lines, "No line containing 'phrasing only' found — required by AC5 scope-boundary contract"
        assert any(re.search(r"panel mechanics|stance file structure", ln, re.IGNORECASE) for ln in boundary_lines), (
            "The 'phrasing only' line must also reference 'panel mechanics' or "
            "'stance file structure' to confirm the full scope disclaimer"
        )
