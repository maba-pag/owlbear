"""Block Kit template helpers — pure dict construction, no external deps.

Provides ``format_proposal_blocks`` and ``format_status_blocks`` for building
Slack Block Kit payloads used by OwlBear's channel adapters.
"""

from __future__ import annotations

_SECTION_TEXT_LIMIT = 3000
_HEADER_TEXT_LIMIT = 150


def format_proposal_blocks(
    title: str,
    description: str,
    options: list[str],
) -> list[dict]:
    """Build Block Kit blocks for a proposal / decision prompt.

    Returns a list containing: header, description section, divider,
    numbered option sections, and a context footer.

    Parameters
    ----------
    title:
        Proposal title (displayed as header).
    description:
        Rich-text description (mrkdwn-compatible).
    options:
        List of option strings to present as numbered choices.
    """
    blocks: list[dict] = []

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": title[:_HEADER_TEXT_LIMIT]},
    })

    # Description section
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": description[:_SECTION_TEXT_LIMIT]},
    })

    # Divider + numbered options
    if options:
        blocks.append({"type": "divider"})
        for i, option in enumerate(options, 1):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{i}.* {option}"},
            })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": "Reply with the option number to choose."},
        ],
    })

    return blocks


def format_status_blocks(  # noqa: PLR0913
    task_name: str,
    step: int,
    total_steps: int,
    status: str,
    eta: str,
    last_tool: str,
) -> list[dict]:
    """Build Block Kit blocks for a task status update.

    Returns a list containing: header, 2-column fields section, and a
    last-action section.

    Parameters
    ----------
    task_name:
        Name of the task being tracked.
    step:
        Current step number.
    total_steps:
        Total number of steps.
    status:
        Current status label.
    eta:
        Estimated time remaining.
    last_tool:
        Name of the last tool invoked.
    """
    blocks: list[dict] = []

    # Header (truncated to Slack's 150-char limit)
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": task_name[:_HEADER_TEXT_LIMIT]},
    })

    # Fields section — 2-column layout
    blocks.append({
        "type": "section",
        "fields": [
            {"type": "mrkdwn", "text": f"*Task:*\n{task_name}"},
            {"type": "mrkdwn", "text": f"*Step:*\n{step}/{total_steps}"},
            {"type": "mrkdwn", "text": f"*Status:*\n{status}"},
            {"type": "mrkdwn", "text": f"*ETA:*\n{eta}"},
        ],
    })

    # Last action section
    action_text = f"*Last action:* `{last_tool}`" if last_tool else "*Last action:* —"
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": action_text},
    })

    return blocks
