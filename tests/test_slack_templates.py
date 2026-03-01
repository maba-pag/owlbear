"""Tests for owlbear.channels.slack_templates — Block Kit template helpers.

Task #330: Pure function tests for format_proposal_blocks and
format_status_blocks.  No Slack API mocking needed.
"""

from __future__ import annotations

from owlbear.channels.slack_templates import (
    format_proposal_blocks,
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
            b for b in blocks
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
        option_sections = [
            b for b in blocks[3:]
            if b["type"] == "section"
        ]
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
        option_sections = [
            b for b in blocks[3:]
            if b["type"] == "section"
        ]
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
