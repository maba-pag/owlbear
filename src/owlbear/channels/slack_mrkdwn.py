"""Markdown to Slack mrkdwn converter — regex-based, pure function."""

from __future__ import annotations

import re

_BOLD_PLACEHOLDER = "\x01"


def markdown_to_mrkdwn(text: str) -> str:
    """Convert Markdown formatting to Slack mrkdwn syntax.

    Conversions performed (in order):

    - ``**bold**``      → ``*bold*``
    - ``*italic*``      → ``_italic_``
    - ``~~strike~~``    → ``~strike~``
    - ``[text](url)``   → ``<url|text>``

    Code blocks (fenced and inline) pass through unchanged.
    """
    if not text:
        return text

    # -- Protect code blocks and inline code from conversion -----------------
    protected: list[str] = []

    def _protect(m: re.Match[str]) -> str:
        protected.append(m.group(0))
        return f"\x00{len(protected) - 1}\x00"

    result = re.sub(r"```[\s\S]*?```", _protect, text)
    result = re.sub(r"`[^`]+`", _protect, result)

    # -- Convert links: [text](url) → <url|text> ----------------------------
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<\2|\1>", result)

    # -- Convert strikethrough: ~~text~~ → ~text~ ---------------------------
    result = re.sub(r"~~(.+?)~~", r"~\1~", result)

    # -- Convert bold: **text** → placeholder+text+placeholder ---------------
    result = re.sub(r"\*\*(.+?)\*\*", rf"{_BOLD_PLACEHOLDER}\1{_BOLD_PLACEHOLDER}", result)

    # -- Convert italic: *text* → _text_ ------------------------------------
    result = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", result)

    # -- Restore bold placeholders to single asterisks -----------------------
    result = result.replace(_BOLD_PLACEHOLDER, "*")

    # -- Restore protected code segments -------------------------------------
    for i, code in enumerate(protected):
        result = result.replace(f"\x00{i}\x00", code)

    return result
