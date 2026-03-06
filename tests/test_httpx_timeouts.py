"""Regression test: every httpx.AsyncClient in src/ must have an explicit timeout."""

from __future__ import annotations

import re
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"

# Locate the start of each AsyncClient( call.
_CLIENT_START_RE = re.compile(r"httpx\.AsyncClient\(")


def _extract_call(text: str, start: int) -> str:
    """Return the full ``httpx.AsyncClient(...)`` call with balanced parens."""
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return text[start - len("httpx.AsyncClient(") : i]


# Files where timeout is set per-request instead of on the constructor.
# AC explicitly marks these as already correct.
_EXCLUDED_FILES: frozenset[str] = frozenset({"web_search.py"})


def test_all_async_clients_have_timeout() -> None:
    """Every httpx.AsyncClient() instantiation must include timeout=."""
    violations: list[str] = []

    for py_file in sorted(SRC_ROOT.rglob("*.py")):
        if py_file.name in _EXCLUDED_FILES:
            continue
        text = py_file.read_text(encoding="utf-8")
        for match in _CLIENT_START_RE.finditer(text):
            # Position right after the opening '('
            snippet = _extract_call(text, match.end())
            if "timeout=" not in snippet:
                # Find line number for a useful error message
                line_no = text[: match.start()].count("\n") + 1
                rel = py_file.relative_to(SRC_ROOT.parent)
                violations.append(f"{rel}:{line_no}  →  {snippet.strip()}")

    assert not violations, "httpx.AsyncClient() calls without explicit timeout=:\n" + "\n".join(
        f"  {v}" for v in violations
    )
