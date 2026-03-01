"""Tests for owlbear.channels.slack_mrkdwn — Markdown to Slack mrkdwn conversion.

Task #332: Pure function tests for markdown_to_mrkdwn conversion.
No Slack API mocking needed.
"""

from __future__ import annotations

from owlbear.channels.slack_mrkdwn import markdown_to_mrkdwn

# ---------------------------------------------------------------------------
# Bold conversion: **text** -> *text*
# ---------------------------------------------------------------------------


class TestBoldConversion:
    """**bold** in Markdown becomes *bold* in Slack mrkdwn."""

    def test_simple_bold(self) -> None:
        assert markdown_to_mrkdwn("**bold**") == "*bold*"

    def test_bold_in_sentence(self) -> None:
        result = markdown_to_mrkdwn("This is **important** text.")
        assert result == "This is *important* text."

    def test_multiple_bold(self) -> None:
        result = markdown_to_mrkdwn("**one** and **two**")
        assert result == "*one* and *two*"

    def test_bold_with_spaces_inside(self) -> None:
        result = markdown_to_mrkdwn("**bold words**")
        assert result == "*bold words*"


# ---------------------------------------------------------------------------
# Italic conversion: *text* -> _text_ (when not bold)
# ---------------------------------------------------------------------------


class TestItalicConversion:
    """*italic* in Markdown becomes _italic_ in Slack mrkdwn."""

    def test_simple_italic(self) -> None:
        assert markdown_to_mrkdwn("*italic*") == "_italic_"

    def test_italic_in_sentence(self) -> None:
        result = markdown_to_mrkdwn("This is *emphasized* text.")
        assert result == "This is _emphasized_ text."

    def test_multiple_italic(self) -> None:
        result = markdown_to_mrkdwn("*one* and *two*")
        assert result == "_one_ and _two_"

    def test_italic_not_confused_with_bold(self) -> None:
        """Bold (**) should be converted first, then italic (*)."""
        result = markdown_to_mrkdwn("**bold** and *italic*")
        assert result == "*bold* and _italic_"


# ---------------------------------------------------------------------------
# Strikethrough: ~~text~~ -> ~text~
# ---------------------------------------------------------------------------


class TestStrikethroughConversion:
    """~~strike~~ in Markdown becomes ~strike~ in Slack mrkdwn."""

    def test_simple_strikethrough(self) -> None:
        assert markdown_to_mrkdwn("~~deleted~~") == "~deleted~"

    def test_strikethrough_in_sentence(self) -> None:
        result = markdown_to_mrkdwn("This is ~~wrong~~ correct.")
        assert result == "This is ~wrong~ correct."

    def test_multiple_strikethrough(self) -> None:
        result = markdown_to_mrkdwn("~~old~~ replaced by ~~older~~")
        assert result == "~old~ replaced by ~older~"


# ---------------------------------------------------------------------------
# Link conversion: [text](url) -> <url|text>
# ---------------------------------------------------------------------------


class TestLinkConversion:
    """[text](url) in Markdown becomes <url|text> in Slack mrkdwn."""

    def test_simple_link(self) -> None:
        result = markdown_to_mrkdwn("[Google](https://google.com)")
        assert result == "<https://google.com|Google>"

    def test_link_in_sentence(self) -> None:
        result = markdown_to_mrkdwn("Visit [our site](https://example.com) today.")
        assert result == "Visit <https://example.com|our site> today."

    def test_multiple_links(self) -> None:
        result = markdown_to_mrkdwn("[A](https://a.com) and [B](https://b.com)")
        assert result == "<https://a.com|A> and <https://b.com|B>"

    def test_link_with_special_chars_in_text(self) -> None:
        result = markdown_to_mrkdwn("[Click & go](https://example.com)")
        assert result == "<https://example.com|Click & go>"

    def test_link_with_path(self) -> None:
        result = markdown_to_mrkdwn("[docs](https://example.com/path/to/page)")
        assert result == "<https://example.com/path/to/page|docs>"


# ---------------------------------------------------------------------------
# Code blocks and inline code — pass through unchanged
# ---------------------------------------------------------------------------


class TestCodePassthrough:
    """Code blocks and inline code must not be modified."""

    def test_inline_code_unchanged(self) -> None:
        result = markdown_to_mrkdwn("Use `**not bold**` in code.")
        assert "`**not bold**`" in result

    def test_inline_code_with_italic(self) -> None:
        result = markdown_to_mrkdwn("Run `*not italic*` command.")
        assert "`*not italic*`" in result

    def test_fenced_code_block_unchanged(self) -> None:
        text = "Before\n```\n**bold** and *italic*\n```\nAfter"
        result = markdown_to_mrkdwn(text)
        assert "```\n**bold** and *italic*\n```" in result

    def test_fenced_code_block_with_language(self) -> None:
        text = "Code:\n```python\ndef **foo**():\n    pass\n```\nEnd."
        result = markdown_to_mrkdwn(text)
        assert "**foo**" in result  # Not converted inside code block

    def test_inline_code_alone(self) -> None:
        result = markdown_to_mrkdwn("`some code`")
        assert result == "`some code`"

    def test_code_block_alone(self) -> None:
        text = "```\nline1\nline2\n```"
        result = markdown_to_mrkdwn(text)
        assert result == text


# ---------------------------------------------------------------------------
# Plain text — pass through unchanged
# ---------------------------------------------------------------------------


class TestPlainTextPassthrough:
    """Text without Markdown formatting passes through unchanged."""

    def test_plain_text(self) -> None:
        assert markdown_to_mrkdwn("Hello, world!") == "Hello, world!"

    def test_empty_string(self) -> None:
        assert markdown_to_mrkdwn("") == ""

    def test_text_with_numbers(self) -> None:
        assert markdown_to_mrkdwn("Step 1 of 3") == "Step 1 of 3"

    def test_text_with_punctuation(self) -> None:
        text = "Hello! How are you? Fine, thanks."
        assert markdown_to_mrkdwn(text) == text

    def test_multiline_plain_text(self) -> None:
        text = "Line one\nLine two\nLine three"
        assert markdown_to_mrkdwn(text) == text


# ---------------------------------------------------------------------------
# Mixed formatting in a single message
# ---------------------------------------------------------------------------


class TestMixedFormatting:
    """Multiple formatting types combined in one message."""

    def test_bold_and_italic(self) -> None:
        result = markdown_to_mrkdwn("**bold** and *italic*")
        assert result == "*bold* and _italic_"

    def test_bold_italic_strikethrough(self) -> None:
        result = markdown_to_mrkdwn("**bold**, *italic*, ~~struck~~")
        assert result == "*bold*, _italic_, ~struck~"

    def test_all_formatting_types(self) -> None:
        text = "**bold** *italic* ~~strike~~ [link](https://x.com) `code`"
        result = markdown_to_mrkdwn(text)
        assert "*bold*" in result
        assert "_italic_" in result
        assert "~strike~" in result
        assert "<https://x.com|link>" in result
        assert "`code`" in result

    def test_formatting_with_plain_text(self) -> None:
        text = "Hello **world**, visit [site](https://example.com)!"
        result = markdown_to_mrkdwn(text)
        assert result == "Hello *world*, visit <https://example.com|site>!"

    def test_bold_inside_sentence_with_link(self) -> None:
        text = "The **quick** fox [jumped](https://example.com) over ~~lazy~~ dog."
        result = markdown_to_mrkdwn(text)
        assert "*quick*" in result
        assert "<https://example.com|jumped>" in result
        assert "~lazy~" in result

    def test_code_not_converted_in_mixed(self) -> None:
        """Inline code should be preserved even alongside other formatting."""
        text = "**bold** and `**not bold**` here"
        result = markdown_to_mrkdwn(text)
        assert result.startswith("*bold*")
        assert "`**not bold**`" in result
