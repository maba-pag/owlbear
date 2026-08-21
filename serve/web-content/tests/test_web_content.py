import pytest
from owlbear_web_content import clean, extract, extract_content, html_to_markdown, strip_noise

REPRESENTATIVE_HTML = """
<html>
  <head><title>Fixture</title><style>.hidden { display: none; }</style></head>
  <body>
    <nav>Fixture navigation</nav>
    <main>
      <h1>Fixture article</h1>
      <p>Meaningful article text with a <a href="https://example.com/target">source link</a>.</p>
      <ul><li>First fixture item</li><li>Second fixture item</li></ul>
      <table>
        <tr><th>Field</th><th>Value</th></tr>
        <tr><td>Answer</td><td>42</td></tr>
      </table>
    </main>
    <script>Fixture script payload</script>
    <div class="cookie-banner">Fixture cookie chrome</div>
  </body>
</html>
"""


def _assert_article_content(markdown: str) -> None:
    assert "Fixture article" in markdown
    assert "First fixture item" in markdown
    assert "https://example.com/target" in markdown
    assert "Field" in markdown
    assert "42" in markdown
    assert "Fixture navigation" not in markdown
    assert "Fixture script payload" not in markdown
    assert "Fixture cookie chrome" not in markdown


def test_clean_preserves_structure_and_removes_noise() -> None:
    _assert_article_content(clean(REPRESENTATIVE_HTML))


def test_html_to_markdown_preserves_structure() -> None:
    markdown = html_to_markdown(
        "<h1>Heading</h1><p>Text <a href='/target'>link</a></p>"
        "<ol><li>Item</li></ol><table><tr><th>A</th></tr><tr><td>B</td></tr></table>"
    )

    assert "# Heading" in markdown
    assert "[link](/target)" in markdown
    assert "1. Item" in markdown
    assert "| A |" in markdown
    assert "| B |" in markdown


def test_strip_noise_removes_known_page_chrome() -> None:
    stripped = strip_noise(REPRESENTATIVE_HTML)

    assert "Fixture article" in stripped
    assert "Fixture navigation" not in stripped
    assert "Fixture script payload" not in stripped
    assert "Fixture cookie chrome" not in stripped


def test_extractors_return_article_content() -> None:
    _assert_article_content(extract(REPRESENTATIVE_HTML))
    _assert_article_content(extract_content(REPRESENTATIVE_HTML, url="https://example.com/article"))


@pytest.mark.parametrize("converter", [clean, extract, extract_content, html_to_markdown, strip_noise])
def test_public_callables_return_empty_for_empty_input(converter) -> None:
    assert converter("") == ""


def test_extract_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="html must be str"):
        extract(123)
