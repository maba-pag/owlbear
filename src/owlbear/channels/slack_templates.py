"""Block Kit template helpers — pure dict construction, no external deps.

Provides Block Kit and plain-text template functions for building Slack
payloads and text fallbacks used by OwlBear's channel adapters.

Block Kit functions (interactive):
    - ``format_proposal_blocks`` — numbered option list (text-only)
    - ``format_interactive_proposal_blocks`` — clickable option buttons
    - ``format_approval_blocks`` — approve/deny buttons
    - ``format_progress_blocks`` — emoji progress bar
    - ``format_status_blocks`` — task status update fields

Text fallback functions (for non-interactive channels):
    - ``format_proposal_text``
    - ``format_approval_text``
    - ``format_progress_text``
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
    blocks.append(
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title[:_HEADER_TEXT_LIMIT]},
        }
    )

    # Description section
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": description[:_SECTION_TEXT_LIMIT]},
        }
    )

    # Divider + numbered options
    if options:
        blocks.append({"type": "divider"})
        for i, option in enumerate(options, 1):
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{i}.* {option}"},
                }
            )

    # Context footer
    blocks.append(
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Reply with the option number to choose."},
            ],
        }
    )

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
    blocks.append(
        {
            "type": "header",
            "text": {"type": "plain_text", "text": task_name[:_HEADER_TEXT_LIMIT]},
        }
    )

    # Fields section — 2-column layout
    blocks.append(
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Task:*\n{task_name}"},
                {"type": "mrkdwn", "text": f"*Step:*\n{step}/{total_steps}"},
                {"type": "mrkdwn", "text": f"*Status:*\n{status}"},
                {"type": "mrkdwn", "text": f"*ETA:*\n{eta}"},
            ],
        }
    )

    # Last action section
    action_text = f"*Last action:* `{last_tool}`" if last_tool else "*Last action:* —"
    blocks.append(
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": action_text},
        }
    )

    return blocks


# ---------------------------------------------------------------------------
# Task #413 — Interactive Block Kit templates
# ---------------------------------------------------------------------------

_FILLED = "■"
_UNFILLED = "□"


def format_interactive_proposal_blocks(
    title: str,
    description: str,
    options: list[dict],
) -> list[dict]:
    """Build Block Kit blocks for a proposal with clickable option buttons.

    Each option becomes a button in an ``actions`` block.  Unlike
    :func:`format_proposal_blocks` (which lists numbered text), this variant
    produces interactive elements that Slack can post back via action payloads.

    Parameters
    ----------
    title:
        Proposal title (displayed as header).
    description:
        Rich-text description (mrkdwn-compatible).
    options:
        Each dict must have ``text`` (display label) and ``value`` keys.
        Buttons receive ``action_id`` = ``"option_{index}"``.
    """
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title[:_HEADER_TEXT_LIMIT]},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": description[:_SECTION_TEXT_LIMIT]},
        },
    ]

    if options:
        blocks.append({"type": "divider"})
        elements = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": str(opt["text"])},
                "action_id": f"option_{i}",
                "value": str(opt["value"]),
            }
            for i, opt in enumerate(options)
        ]
        blocks.append({"type": "actions", "elements": elements})

    return blocks


def format_approval_blocks(
    action_description: str,
    action_id_prefix: str,
) -> list[dict]:
    """Build Block Kit blocks with approve / deny buttons.

    Parameters
    ----------
    action_description:
        Human-readable description of the action awaiting approval.
    action_id_prefix:
        Prefix for button ``action_id`` values.  Produces
        ``"{prefix}_approve"`` and ``"{prefix}_deny"``.
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Approval required:* {action_description}",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "action_id": f"{action_id_prefix}_approve",
                    "value": "approved",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Deny"},
                    "style": "danger",
                    "action_id": f"{action_id_prefix}_deny",
                    "value": "denied",
                },
            ],
        },
    ]


def format_progress_blocks(
    task_name: str,
    current_step: int,
    total_steps: int,
    eta: str | None = None,
) -> list[dict]:
    """Build Block Kit blocks with an emoji progress bar.

    Parameters
    ----------
    task_name:
        Name of the task being tracked.
    current_step:
        Completed steps so far (0-based OK).
    total_steps:
        Total number of steps.
    eta:
        Optional estimated time remaining.  Omitted from output when *None*.
    """
    bar = (_FILLED * current_step) + (_UNFILLED * (total_steps - current_step))
    progress_line = f"{bar}  {current_step}/{total_steps}"

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": task_name[:_HEADER_TEXT_LIMIT]},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": progress_line},
        },
    ]

    if eta is not None:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"ETA: {eta}"},
                ],
            }
        )

    return blocks


# ---------------------------------------------------------------------------
# Task #417 — Text fallback helpers for non-interactive channels
# ---------------------------------------------------------------------------


def format_proposal_text(
    title: str,
    description: str,
    options: list[str] | list[dict],
) -> str:
    """Plain-text proposal for non-interactive channels (CLI, logging).

    Parameters
    ----------
    title:
        Proposal title.
    description:
        Description body.
    options:
        Either plain strings or dicts with a ``text`` key.
    """
    lines = [title, "", description, ""]
    for i, opt in enumerate(options, 1):
        label = opt["text"] if isinstance(opt, dict) else str(opt)
        lines.append(f"  {i}. {label}")
    if options:
        lines.append("")
        lines.append("Reply with the option number to choose.")
    return "\n".join(lines)


def format_approval_text(action_description: str) -> str:
    """Plain-text approval prompt for non-interactive channels.

    Parameters
    ----------
    action_description:
        Human-readable description of the action awaiting approval.
    """
    return f"Approval required: {action_description}\nReply 'approve' to approve or 'deny' to deny."


def format_progress_text(
    task_name: str,
    current_step: int,
    total_steps: int,
    eta: str | None = None,
) -> str:
    """Plain-text progress update for non-interactive channels.

    Parameters
    ----------
    task_name:
        Name of the task being tracked.
    current_step:
        Completed steps so far.
    total_steps:
        Total number of steps.
    eta:
        Optional estimated time remaining.
    """
    bar = (_FILLED * current_step) + (_UNFILLED * (total_steps - current_step))
    line = f"{task_name}: {bar} {current_step}/{total_steps}"
    if eta is not None:
        line += f" (ETA: {eta})"
    return line
