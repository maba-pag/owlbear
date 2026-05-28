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
