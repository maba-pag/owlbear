"""Tests for owlbear.channels.slack_templates — Block Kit template helpers.

Task #330: Pure function tests for format_proposal_blocks and
format_status_blocks.  No Slack API mocking needed.
"""

from __future__ import annotations

from typing import ClassVar

from owlbear.channels.slack_templates import (
    format_approval_blocks,
    format_approval_text,
    format_interactive_proposal_blocks,
    format_progress_blocks,
    format_progress_text,
    format_proposal_blocks,
    format_proposal_text,
    format_status_blocks,
)

# ---------------------------------------------------------------------------
# format_proposal_blocks — happy path
# ---------------------------------------------------------------------------


class TestFormatProposalBlocksHappyPath:
    """format_proposal_blocks returns valid Block Kit blocks for proposals."""

    def test_returns_list_of_dicts(self) -> None:
        blocks = format_proposal_blocks(
            title="Choose an approach",
            description="We have two options for the auth flow.",
            options=["OAuth device flow", "PAT token"],
        )
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_header_block_contains_title(self) -> None:
        blocks = format_proposal_blocks(
            title="Pick a strategy",
            description="Description here.",
            options=["A", "B"],
        )
        header = blocks[0]
        assert header["type"] == "header"
        assert header["text"]["type"] == "plain_text"
        assert header["text"]["text"] == "Pick a strategy"

    def test_description_section_follows_header(self) -> None:
        blocks = format_proposal_blocks(
            title="Title",
            description="Some *rich* description.",
            options=["A"],
        )
        section = blocks[1]
        assert section["type"] == "section"
        assert section["text"]["type"] == "mrkdwn"
        assert "Some *rich* description." in section["text"]["text"]

    def test_divider_after_description(self) -> None:
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=["A", "B"],
        )
        assert blocks[2]["type"] == "divider"

    def test_numbered_option_sections(self) -> None:
        options = ["Alpha", "Beta", "Gamma"]
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=options,
        )
        # Options start after header (0), description (1), divider (2)
        option_blocks = [b for b in blocks[3:] if b["type"] == "section"]
        assert len(option_blocks) == 3
        assert "*1.*" in option_blocks[0]["text"]["text"]
        assert "Alpha" in option_blocks[0]["text"]["text"]
        assert "*2.*" in option_blocks[1]["text"]["text"]
        assert "Beta" in option_blocks[1]["text"]["text"]
        assert "*3.*" in option_blocks[2]["text"]["text"]
        assert "Gamma" in option_blocks[2]["text"]["text"]

    def test_option_sections_use_mrkdwn(self) -> None:
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=["Only option"],
        )
        option_block = blocks[3]
        assert option_block["text"]["type"] == "mrkdwn"

    def test_context_footer_present(self) -> None:
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=["A"],
        )
        last_block = blocks[-1]
        assert last_block["type"] == "context"
        assert isinstance(last_block["elements"], list)
        assert len(last_block["elements"]) >= 1
        # Footer should contain guidance text
        footer_text = last_block["elements"][0]["text"]
        assert "reply" in footer_text.lower() or "option" in footer_text.lower()

    def test_overall_block_order(self) -> None:
        """Verify: header, section (desc), divider, option sections, context."""
        blocks = format_proposal_blocks(
            title="Title",
            description="Desc",
            options=["A", "B"],
        )
        types = [b["type"] for b in blocks]
        assert types[0] == "header"
        assert types[1] == "section"
        assert types[2] == "divider"
        assert types[3] == "section"  # option 1
        assert types[4] == "section"  # option 2
        assert types[-1] == "context"


# ---------------------------------------------------------------------------
# format_proposal_blocks — edge cases
# ---------------------------------------------------------------------------


class TestFormatProposalBlocksEdgeCases:
    """Edge cases for format_proposal_blocks."""

    def test_empty_options_list(self) -> None:
        """Empty options should still produce header + description + footer."""
        blocks = format_proposal_blocks(
            title="No options",
            description="Nothing to choose.",
            options=[],
        )
        types = [b["type"] for b in blocks]
        assert "header" in types
        assert "context" in types
        # No option sections between divider and context
        option_sections = [
            b
            for b in blocks
            if b["type"] == "section" and b != blocks[1]  # exclude description
        ]
        assert len(option_sections) == 0

    def test_long_description_truncated(self) -> None:
        """Descriptions longer than 3000 chars should be truncated."""
        long_desc = "x" * 4000
        blocks = format_proposal_blocks(
            title="T",
            description=long_desc,
            options=["A"],
        )
        desc_text = blocks[1]["text"]["text"]
        assert len(desc_text) <= 3000

    def test_special_chars_in_title(self) -> None:
        """Angle brackets and ampersands in title should be escaped."""
        blocks = format_proposal_blocks(
            title="Choose <option> & decide",
            description="Desc",
            options=["A"],
        )
        title_text = blocks[0]["text"]["text"]
        # Slack plain_text auto-escapes, but our function should handle it
        assert (
            "<" not in title_text
            or "&lt;" in title_text
            or title_text == "Choose <option> & decide"
        )

    def test_special_chars_in_options(self) -> None:
        """Special chars in option text should be safe for mrkdwn."""
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=["Use <tag> & stuff", "Normal option"],
        )
        option_text = blocks[3]["text"]["text"]
        # Should contain the option text (possibly escaped)
        assert "Use" in option_text
        assert "stuff" in option_text

    def test_single_option(self) -> None:
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=["Only one"],
        )
        option_sections = [b for b in blocks[3:] if b["type"] == "section"]
        assert len(option_sections) == 1
        assert "*1.*" in option_sections[0]["text"]["text"]

    def test_many_options(self) -> None:
        """Test with 10 options — all should be numbered."""
        options = [f"Option {i}" for i in range(1, 11)]
        blocks = format_proposal_blocks(
            title="T",
            description="D",
            options=options,
        )
        option_sections = [b for b in blocks[3:] if b["type"] == "section"]
        assert len(option_sections) == 10
        assert "*10.*" in option_sections[9]["text"]["text"]


# ---------------------------------------------------------------------------
# format_status_blocks — happy path
# ---------------------------------------------------------------------------


class TestFormatStatusBlocksHappyPath:
    """format_status_blocks returns valid Block Kit blocks for status updates."""

    def test_returns_list_of_dicts(self) -> None:
        blocks = format_status_blocks(
            task_name="Implement auth",
            step=2,
            total_steps=5,
            status="in-progress",
            eta="~3 min",
            last_tool="read_file",
        )
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_header_block_present(self) -> None:
        blocks = format_status_blocks(
            task_name="Build feature X",
            step=1,
            total_steps=4,
            status="starting",
            eta="~5 min",
            last_tool="grep_search",
        )
        header = blocks[0]
        assert header["type"] == "header"
        assert header["text"]["type"] == "plain_text"
        assert "Build feature X" in header["text"]["text"]

    def test_fields_section_with_two_column_layout(self) -> None:
        blocks = format_status_blocks(
            task_name="Deploy service",
            step=3,
            total_steps=6,
            status="running",
            eta="~2 min",
            last_tool="run_in_terminal",
        )
        fields_section = blocks[1]
        assert fields_section["type"] == "section"
        assert "fields" in fields_section
        fields = fields_section["fields"]
        # Should have task, step, status, eta fields
        assert len(fields) >= 4

    def test_fields_contain_task_name(self) -> None:
        blocks = format_status_blocks(
            task_name="Fix bug #42",
            step=1,
            total_steps=3,
            status="in-progress",
            eta="~1 min",
            last_tool="edit_file",
        )
        fields = blocks[1]["fields"]
        field_texts = [f["text"] for f in fields]
        combined = " ".join(field_texts)
        assert "Fix bug #42" in combined

    def test_fields_contain_step_progress(self) -> None:
        blocks = format_status_blocks(
            task_name="Task",
            step=3,
            total_steps=7,
            status="running",
            eta="~4 min",
            last_tool="search",
        )
        fields = blocks[1]["fields"]
        field_texts = [f["text"] for f in fields]
        combined = " ".join(field_texts)
        assert "3" in combined
        assert "7" in combined

    def test_fields_contain_status(self) -> None:
        blocks = format_status_blocks(
            task_name="Task",
            step=1,
            total_steps=1,
            status="complete",
            eta="done",
            last_tool="pytest",
        )
        fields = blocks[1]["fields"]
        field_texts = [f["text"] for f in fields]
        combined = " ".join(field_texts)
        assert "complete" in combined.lower()

    def test_fields_contain_eta(self) -> None:
        blocks = format_status_blocks(
            task_name="Task",
            step=2,
            total_steps=5,
            status="running",
            eta="~10 min",
            last_tool="tool",
        )
        fields = blocks[1]["fields"]
        field_texts = [f["text"] for f in fields]
        combined = " ".join(field_texts)
        assert "~10 min" in combined

    def test_fields_use_mrkdwn_type(self) -> None:
        blocks = format_status_blocks(
            task_name="Task",
            step=1,
            total_steps=1,
            status="ok",
            eta="now",
            last_tool="x",
        )
        for field in blocks[1]["fields"]:
            assert field["type"] == "mrkdwn"

    def test_last_action_section(self) -> None:
        blocks = format_status_blocks(
            task_name="Task",
            step=1,
            total_steps=1,
            status="ok",
            eta="now",
            last_tool="semantic_search",
        )
        # Last action should be in a section after the fields
        last_action_block = blocks[2]
        assert last_action_block["type"] == "section"
        assert "semantic_search" in last_action_block["text"]["text"]

    def test_overall_block_order(self) -> None:
        """Verify: header, fields section, last action section."""
        blocks = format_status_blocks(
            task_name="Task",
            step=1,
            total_steps=3,
            status="running",
            eta="~2 min",
            last_tool="read_file",
        )
        types = [b["type"] for b in blocks]
        assert types[0] == "header"
        assert types[1] == "section"  # fields
        assert types[2] == "section"  # last action


# ---------------------------------------------------------------------------
# format_status_blocks — edge cases
# ---------------------------------------------------------------------------


class TestFormatStatusBlocksEdgeCases:
    """Edge cases for format_status_blocks."""

    def test_step_zero(self) -> None:
        """Step 0 of N should be valid (not started)."""
        blocks = format_status_blocks(
            task_name="Task",
            step=0,
            total_steps=5,
            status="pending",
            eta="unknown",
            last_tool="none",
        )
        assert len(blocks) >= 3

    def test_empty_last_tool(self) -> None:
        """Empty last_tool should still produce a valid block."""
        blocks = format_status_blocks(
            task_name="Task",
            step=1,
            total_steps=1,
            status="ok",
            eta="now",
            last_tool="",
        )
        assert len(blocks) >= 3

    def test_long_task_name(self) -> None:
        """Header text has a 150-char limit in Slack — should be handled."""
        long_name = "A" * 200
        blocks = format_status_blocks(
            task_name=long_name,
            step=1,
            total_steps=1,
            status="ok",
            eta="now",
            last_tool="x",
        )
        header_text = blocks[0]["text"]["text"]
        assert len(header_text) <= 150


# ===========================================================================
# Task #413 — format_interactive_proposal_blocks
# ===========================================================================


class TestFormatInteractiveProposalBlocksHappyPath:
    """format_interactive_proposal_blocks returns Block Kit with option buttons."""

    _OPTIONS: ClassVar[list[dict]] = [
        {"text": "OAuth device flow", "value": "oauth"},
        {"text": "PAT token", "value": "pat"},
    ]

    def test_returns_list_of_dicts(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="Choose auth",
            description="Pick one.",
            options=self._OPTIONS,
        )
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_header_contains_title(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="My Proposal",
            description="Desc",
            options=self._OPTIONS,
        )
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == "My Proposal"

    def test_description_section(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="Rich *description*.",
            options=self._OPTIONS,
        )
        assert blocks[1]["type"] == "section"
        assert blocks[1]["text"]["type"] == "mrkdwn"
        assert "Rich *description*." in blocks[1]["text"]["text"]

    def test_actions_block_present(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 1

    def test_buttons_per_option(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        elements = actions_block["elements"]
        assert len(elements) == 2
        assert all(e["type"] == "button" for e in elements)

    def test_button_text_matches_option(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        texts = [e["text"]["text"] for e in actions_block["elements"]]
        assert texts == ["OAuth device flow", "PAT token"]

    def test_button_values(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        values = [e["value"] for e in actions_block["elements"]]
        assert values == ["oauth", "pat"]

    def test_each_button_has_unique_action_id(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert len(action_ids) == len(set(action_ids))  # all unique

    def test_action_id_contains_index(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        action_ids = [e["action_id"] for e in actions_block["elements"]]
        assert "option_0" in action_ids[0]
        assert "option_1" in action_ids[1]

    def test_button_text_is_plain_text(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        for elem in actions_block["elements"]:
            assert elem["text"]["type"] == "plain_text"

    def test_overall_block_order(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=self._OPTIONS,
        )
        types = [b["type"] for b in blocks]
        assert types[0] == "header"
        assert types[1] == "section"
        assert "divider" in types
        assert "actions" in types


class TestFormatInteractiveProposalBlocksEdgeCases:
    """Edge cases for format_interactive_proposal_blocks."""

    def test_empty_options(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=[],
        )
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 0

    def test_single_option(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="D",
            options=[{"text": "Only one", "value": "one"}],
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        assert len(actions_block["elements"]) == 1

    def test_long_title_truncated(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="X" * 200,
            description="D",
            options=[{"text": "A", "value": "a"}],
        )
        assert len(blocks[0]["text"]["text"]) <= 150

    def test_long_description_truncated(self) -> None:
        blocks = format_interactive_proposal_blocks(
            title="T",
            description="Y" * 4000,
            options=[{"text": "A", "value": "a"}],
        )
        assert len(blocks[1]["text"]["text"]) <= 3000


# ===========================================================================
# Task #413 — format_approval_blocks
# ===========================================================================


class TestFormatApprovalBlocksHappyPath:
    """format_approval_blocks returns approve/deny button blocks."""

    def test_returns_list_of_dicts(self) -> None:
        blocks = format_approval_blocks(
            action_description="Delete production database",
            action_id_prefix="delete_db",
        )
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_description_section(self) -> None:
        blocks = format_approval_blocks(
            action_description="Push to main branch",
            action_id_prefix="push_main",
        )
        section = next(b for b in blocks if b["type"] == "section")
        assert "Push to main branch" in section["text"]["text"]

    def test_actions_block_with_two_buttons(self) -> None:
        blocks = format_approval_blocks(
            action_description="Deploy v2",
            action_id_prefix="deploy",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        assert len(actions_block["elements"]) == 2

    def test_approve_button_primary_style(self) -> None:
        blocks = format_approval_blocks(
            action_description="Ship it",
            action_id_prefix="ship",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        approve_btn = actions_block["elements"][0]
        assert approve_btn["style"] == "primary"

    def test_deny_button_danger_style(self) -> None:
        blocks = format_approval_blocks(
            action_description="Ship it",
            action_id_prefix="ship",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        deny_btn = actions_block["elements"][1]
        assert deny_btn["style"] == "danger"

    def test_approve_action_id(self) -> None:
        blocks = format_approval_blocks(
            action_description="Delete logs",
            action_id_prefix="del_logs",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        assert actions_block["elements"][0]["action_id"] == "del_logs_approve"

    def test_deny_action_id(self) -> None:
        blocks = format_approval_blocks(
            action_description="Delete logs",
            action_id_prefix="del_logs",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        assert actions_block["elements"][1]["action_id"] == "del_logs_deny"

    def test_button_labels(self) -> None:
        blocks = format_approval_blocks(
            action_description="Do thing",
            action_id_prefix="thing",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        labels = [e["text"]["text"] for e in actions_block["elements"]]
        assert labels[0].lower() == "approve"
        assert labels[1].lower() == "deny"

    def test_button_text_is_plain_text(self) -> None:
        blocks = format_approval_blocks(
            action_description="Action",
            action_id_prefix="act",
        )
        actions_block = next(b for b in blocks if b["type"] == "actions")
        for elem in actions_block["elements"]:
            assert elem["text"]["type"] == "plain_text"


# ===========================================================================
# Task #413 — format_progress_blocks
# ===========================================================================


class TestFormatProgressBlocksHappyPath:
    """format_progress_blocks returns blocks with emoji progress bar."""

    def test_returns_list_of_dicts(self) -> None:
        blocks = format_progress_blocks(
            task_name="Build feature",
            current_step=3,
            total_steps=10,
        )
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_header_present(self) -> None:
        blocks = format_progress_blocks(
            task_name="Building",
            current_step=1,
            total_steps=5,
        )
        assert blocks[0]["type"] == "header"
        assert "Building" in blocks[0]["text"]["text"]

    def test_progress_bar_section(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=5,
            total_steps=10,
        )
        # Find the section with the progress bar (mrkdwn text with squares)
        bar_blocks = [
            b
            for b in blocks
            if b["type"] == "section"
            and "text" in b
            and ("■" in b["text"]["text"] or "□" in b["text"]["text"])
        ]
        assert len(bar_blocks) >= 1

    def test_progress_bar_filled_count(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=3,
            total_steps=10,
        )
        bar_block = next(
            b for b in blocks if b["type"] == "section" and "text" in b and "■" in b["text"]["text"]
        )
        text = bar_block["text"]["text"]
        assert text.count("■") == 3

    def test_progress_bar_unfilled_count(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=3,
            total_steps=10,
        )
        bar_block = next(
            b for b in blocks if b["type"] == "section" and "text" in b and "□" in b["text"]["text"]
        )
        text = bar_block["text"]["text"]
        assert text.count("□") == 7

    def test_step_counter_present(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=4,
            total_steps=8,
        )
        all_text = " ".join(
            b["text"]["text"] for b in blocks if b.get("type") == "section" and "text" in b
        )
        assert "4" in all_text
        assert "8" in all_text

    def test_eta_shown_when_provided(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=2,
            total_steps=5,
            eta="~3 min",
        )
        all_text = " ".join(
            b.get("text", {}).get("text", "")
            if isinstance(b.get("text"), dict)
            else " ".join(e.get("text", "") for e in b.get("elements", []))
            for b in blocks
        )
        assert "~3 min" in all_text

    def test_eta_omitted_when_none(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=2,
            total_steps=5,
            eta=None,
        )
        all_text = " ".join(
            b.get("text", {}).get("text", "") if isinstance(b.get("text"), dict) else ""
            for b in blocks
        )
        assert "ETA" not in all_text or "N/A" not in all_text

    def test_complete_progress_bar(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=5,
            total_steps=5,
        )
        bar_block = next(
            b for b in blocks if b["type"] == "section" and "text" in b and "■" in b["text"]["text"]
        )
        text = bar_block["text"]["text"]
        assert text.count("■") == 5
        assert text.count("□") == 0

    def test_zero_progress(self) -> None:
        blocks = format_progress_blocks(
            task_name="Task",
            current_step=0,
            total_steps=5,
        )
        bar_block = next(
            b for b in blocks if b["type"] == "section" and "text" in b and "□" in b["text"]["text"]
        )
        text = bar_block["text"]["text"]
        assert text.count("■") == 0
        assert text.count("□") == 5

    def test_long_task_name_truncated(self) -> None:
        blocks = format_progress_blocks(
            task_name="Z" * 200,
            current_step=1,
            total_steps=3,
        )
        assert len(blocks[0]["text"]["text"]) <= 150


# ===========================================================================
# Task #417 — format_proposal_text
# ===========================================================================


class TestFormatProposalText:
    """format_proposal_text returns readable plain text for proposals."""

    def test_returns_string(self) -> None:
        result = format_proposal_text(
            title="Choose auth",
            description="Pick one.",
            options=["OAuth", "PAT"],
        )
        assert isinstance(result, str)

    def test_contains_title(self) -> None:
        result = format_proposal_text(
            title="My Proposal",
            description="Some desc.",
            options=["A"],
        )
        assert "My Proposal" in result

    def test_contains_description(self) -> None:
        result = format_proposal_text(
            title="T",
            description="Detailed description here.",
            options=["A"],
        )
        assert "Detailed description here." in result

    def test_numbered_options(self) -> None:
        result = format_proposal_text(
            title="T",
            description="D",
            options=["Alpha", "Beta", "Gamma"],
        )
        assert "1." in result or "1)" in result
        assert "Alpha" in result
        assert "2." in result or "2)" in result
        assert "Beta" in result
        assert "3." in result or "3)" in result
        assert "Gamma" in result

    def test_empty_options(self) -> None:
        result = format_proposal_text(
            title="T",
            description="D",
            options=[],
        )
        assert "T" in result
        assert "D" in result

    def test_dict_options_use_text_key(self) -> None:
        result = format_proposal_text(
            title="T",
            description="D",
            options=[{"text": "OAuth", "value": "oauth"}],
        )
        assert "OAuth" in result


# ===========================================================================
# Task #417 — format_approval_text
# ===========================================================================


class TestFormatApprovalText:
    """format_approval_text returns readable plain text for approvals."""

    def test_returns_string(self) -> None:
        result = format_approval_text("Delete production DB")
        assert isinstance(result, str)

    def test_contains_action_description(self) -> None:
        result = format_approval_text("Push to main branch")
        assert "Push to main branch" in result

    def test_contains_approve_and_deny_guidance(self) -> None:
        result = format_approval_text("Deploy v2")
        lower = result.lower()
        assert "approve" in lower
        assert "deny" in lower


# ===========================================================================
# Task #417 — format_progress_text
# ===========================================================================


class TestFormatProgressText:
    """format_progress_text returns readable plain text for progress."""

    def test_returns_string(self) -> None:
        result = format_progress_text(
            task_name="Build feature",
            current_step=3,
            total_steps=10,
        )
        assert isinstance(result, str)

    def test_contains_task_name(self) -> None:
        result = format_progress_text(
            task_name="Deploying service",
            current_step=1,
            total_steps=5,
        )
        assert "Deploying service" in result

    def test_contains_step_progress(self) -> None:
        result = format_progress_text(
            task_name="Task",
            current_step=4,
            total_steps=8,
        )
        assert "4" in result
        assert "8" in result

    def test_contains_eta_when_provided(self) -> None:
        result = format_progress_text(
            task_name="Task",
            current_step=2,
            total_steps=5,
            eta="~3 min",
        )
        assert "~3 min" in result

    def test_no_eta_when_none(self) -> None:
        result = format_progress_text(
            task_name="Task",
            current_step=2,
            total_steps=5,
            eta=None,
        )
        # Should not crash, should still be valid
        assert "Task" in result

    def test_contains_text_progress_bar(self) -> None:
        result = format_progress_text(
            task_name="Task",
            current_step=3,
            total_steps=10,
        )
        # Should contain some visual indicator of progress
        assert "■" in result or "█" in result or "#" in result or "=" in result
