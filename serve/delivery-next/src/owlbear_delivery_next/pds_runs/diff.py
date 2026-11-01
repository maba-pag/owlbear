"""A PDS update's release evidence (#777): the changelog between the two versions and the deprecations' diff.

Both are what the updater and the challenger read about the release, never a verdict on the pages: the audit and the
browser tests judge those.
"""

from __future__ import annotations

import re

from owlbear_delivery_next.impeccable_runs import pack_gates

CHANGELOG = "CHANGELOG.md"
DEPRECATIONS = "skills/pds-knowledge-js/references/deprecations.md"
HEADING = re.compile(r"^## \[(\d+)\.(\d+)\.(\d+)[^\]]*\]", re.MULTILINE)  # a release's section, its candidates too
CAP = 20000  # characters of each part the sessions are shown


def _number(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def changelog(text: str, since: str, to: str) -> str:
    """The changelog's sections for the releases after *since* up to *to*, newest first, as the file orders them."""
    marks = list(HEADING.finditer(text))
    old, new = _number(since), _number(to)
    kept = []
    for i, m in enumerate(marks):
        if old < tuple(int(n) for n in m.groups()) <= new:
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            kept.append(text[m.start() : end].strip())
    return "\n\n".join(kept)


def evidence(old: bytes | None, new: dict[str, bytes], since: str, to: str) -> str:
    """The changelog from *since* to *to* and the deprecations' diff, from the pinned *old* file to the release's."""
    log = changelog(new.get(CHANGELOG, b"").decode("utf-8", "replace"), since, to) or "(no changelog sections)"
    diff = pack_gates.diff(DEPRECATIONS, old, new.get(DEPRECATIONS))
    return f"Changelog {since} to {to}:\n{_cut(log)}\n\nDeprecations' diff:\n{_cut(diff)}"


def _cut(text: str) -> str:
    return text if len(text) <= CAP else f"{text[:CAP]}\n… ({len(text) - CAP} more characters cut)"
