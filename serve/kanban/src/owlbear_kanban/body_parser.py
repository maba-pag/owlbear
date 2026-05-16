"""Markdown body parser for kanban task bodies (Brief C §2.4).

Parses raw markdown text into a list of Section objects and renders
Section objects back to markdown. Uses a hand-rolled CommonMark-compatible
state machine that handles ATX headings, Setext headings, fenced code
blocks, and indented code blocks.

Round-trip guarantee: parse_body(render_body(sections)) == sections
for all sections produced by parse_body.
"""

from __future__ import annotations

import re

from owlbear_kanban.models import Section

__all__ = ["Section", "parse_body", "render_body"]

# ATX heading: 1-6 '#' followed by a space
_ATX_RE = re.compile(r"^(#{1,6}) (.*)$")

# Setext underline: line of only `=` or `-` (3+ chars)
_SETEXT_EQ_RE = re.compile(r"^={3,}\s*$")
_SETEXT_DASH_RE = re.compile(r"^-{3,}\s*$")

# Fenced code block opening: ``` or ~~~
_FENCE_RE = re.compile(r"^(`{3,}|~{3,})")

# Indented code block: 4 spaces or 1 tab
_INDENT_RE = re.compile(r"^(    |\t)")


def _normalize_atx_heading(raw_heading: str) -> str:
    """Return CommonMark-normalized ATX heading text."""
    stripped = raw_heading.strip()
    if stripped and set(stripped) == {"#"}:
        return ""
    # Optional closing hash run is removed only when preceded by whitespace.
    return re.sub(r"[ \t]+#+[ \t]*$", "", raw_heading).strip()


def parse_body(markdown: str) -> list[Section]:  # noqa: C901, PLR0915
    """Parse *markdown* into a list of :class:`Section` objects.

    Section boundaries:
    - ATX headings ``# H1`` through ``###### H6`` (space required after #).
    - Setext headings (text + underline of ``===`` or ``---``).
    - Content before the first heading is a Section(heading=None, level=0).
    - Heading-like lines inside fenced or indented code blocks are NOT sections.
    - ``##NoSpace`` lines are NOT headings — they become content.

    CRLF is normalised to LF before processing (AC-C6).

    Args:
        markdown: Raw markdown text.

    Returns:
        List of Section objects.
    """
    # Normalise CRLF → LF
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    sections: list[Section] = []
    current_heading: str | None = None
    current_level: int = 0
    current_lines: list[str] = []

    in_fence = False
    fence_char = ""
    fence_len = 0

    def _flush() -> None:
        """Append current section — skips empty preamble sections."""
        content = "\n".join(current_lines)
        # Skip empty preamble (heading=None, no real content) to avoid ghost sections
        if current_heading is None and not content.strip():
            return
        sections.append(Section(heading=current_heading, level=current_level, content=content))

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- Fenced code block toggle ---
        fence_match = _FENCE_RE.match(line)
        if fence_match and not in_fence:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            current_lines.append(line)
            i += 1
            continue
        if in_fence:
            current_lines.append(line)
            # Closing fence: same character, same or greater length
            closing = re.match(rf"^[{re.escape(fence_char)}]{{{fence_len},}}\s*$", line)
            if closing:
                in_fence = False
                fence_char = ""
                fence_len = 0
            i += 1
            continue

        # --- Indented code block: treat as content ---
        if _INDENT_RE.match(line):
            current_lines.append(line)
            i += 1
            continue

        # --- ATX heading ---
        atx_match = _ATX_RE.match(line)
        if atx_match:
            # Flush current section; append "" so the content includes the
            # blank-line separator (preserving round-trip fidelity, AC-C12).
            current_lines.append("")
            _flush()
            current_heading = _normalize_atx_heading(atx_match.group(2))
            current_level = len(atx_match.group(1))
            current_lines = []
            i += 1
            continue

        # --- Setext heading (look-ahead at next line) ---
        if i + 1 < len(lines) and line.strip():
            next_line = lines[i + 1]
            if _SETEXT_EQ_RE.match(next_line):
                # Level-1 Setext heading
                current_lines.append("")
                _flush()
                current_heading = line.strip()
                current_level = 1
                current_lines = []
                i += 2  # skip heading + underline
                continue
            if _SETEXT_DASH_RE.match(next_line):
                # Level-2 Setext heading
                current_lines.append("")
                _flush()
                current_heading = line.strip()
                current_level = 2
                current_lines = []
                i += 2
                continue

        # Normal content line
        current_lines.append(line)
        i += 1

    # Flush final section (no extra append — content already includes trailing
    # newline from the split; adding another would double it).
    _flush()

    return sections


def render_body(sections: list[Section]) -> str:
    """Render a list of :class:`Section` objects back to markdown.

    Heading normalisation:
    - All headings are written as ATX style (``## Heading``) regardless of
      their original form (AC-C53).
    - Preamble sections (heading=None, level=0) are written without a heading
      line.

    Args:
        sections: List of Section objects to render.

    Returns:
        Rendered markdown string.
    """
    parts: list[str] = []
    for sec in sections:
        if sec.heading is not None:
            prefix = "#" * sec.level
            parts.append(f"{prefix} {sec.heading}\n")
        content = sec.content
        if content:
            parts.append(content)
    return "".join(parts)
