"""Section-based predicate DSL for kanban task gates (Brief C §6).

Provides:
- ``required_sections(task, section_names)`` — check task body has all named sections
- ``require_list_in_section(task, section_name)`` — check a section contains a list

Operates on ``Task.body`` which may be a raw markdown string or a list of
Section objects (Brief C C1 transition). Both forms are handled transparently.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from owlbear_kanban.body_parser import parse_body

if TYPE_CHECKING:
    from owlbear_kanban.models import Section, Task

# CommonMark list item: up to 3 leading spaces, then marker + space.
# Four-space or tab-indented lines are indented code blocks, not lists.
_MAX_INDENT = 3
_BULLET_RE = re.compile(r"^ {0,3}[-*+] ", re.MULTILINE)
_ORDERED_RE = re.compile(r"^ {0,3}\d{1,9}[\.)] ", re.MULTILINE)
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})", re.MULTILINE)


def _get_sections(task: Task) -> list[Section]:
    """Return sections from task.body, handling both str and list[Section]."""
    if isinstance(task.body, list):
        return task.body  # type: ignore[return-value]
    return parse_body(task.body)


def _section_matches(section: Section, name: str) -> bool:
    """Return True if *section*'s heading matches *name* (case-insensitive, stripped)."""
    if section.heading is None:
        return False
    return section.heading.strip().casefold() == name.strip().casefold()


def required_sections(task: Task, section_names: list[str]) -> bool:
    """Return True if *task* body contains all of the named sections.

    Comparison is case-insensitive and whitespace-stripped (Brief B D56).

    Args:
        task:          Task to inspect.
        section_names: List of required section heading names.

    Returns:
        ``True`` if all sections are present, ``False`` otherwise.
    """
    if not section_names:
        return True
    sections = _get_sections(task)
    return all(any(_section_matches(s, name) for s in sections) for name in section_names)


def require_list_in_section(task: Task, section_name: str) -> bool:
    """Return True if the named section contains at least one CommonMark list item.

    List items inside fenced code blocks do NOT count (AC-C40).

    Args:
        task:         Task to inspect.
        section_name: Section heading to look inside (case-insensitive).

    Returns:
        ``True`` if the section exists and contains a list, ``False`` otherwise.
    """
    sections = _get_sections(task)
    target = next(
        (s for s in sections if _section_matches(s, section_name)),
        None,
    )
    if target is None:
        return False
    return _has_list_outside_fences(target.content)


def _has_list_outside_fences(content: str) -> bool:
    """Return True if *content* has a CommonMark list item outside code fences."""
    if not content:
        return False
    # Remove fenced code blocks, then check for list items
    stripped = _remove_fenced_blocks(content)
    return bool(_BULLET_RE.search(stripped) or _ORDERED_RE.search(stripped))


def _remove_fenced_blocks(text: str) -> str:
    """Return *text* with all fenced code block contents replaced by blank lines."""
    result: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in text.split("\n"):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        fence_match = _FENCE_RE.match(line)
        if fence_match and not in_fence:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            result.append("")  # blank placeholder
        elif in_fence:
            closing = (
                indent <= _MAX_INDENT
                and stripped.rstrip() == fence_char * len(stripped.rstrip())
                and len(stripped.rstrip()) >= fence_len
            )
            if closing:
                in_fence = False
                fence_char = ""
                fence_len = 0
            result.append("")  # blank placeholder
        else:
            result.append(line)
    return "\n".join(result)
