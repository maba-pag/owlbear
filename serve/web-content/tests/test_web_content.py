import pytest

import owlbear_web_content.cleaner as cleaner_module
import owlbear_web_content.extractor as extractor_module
from owlbear_web_content import (
    clean,
    extract,
    extract_content,
    html_to_markdown,
    normalize,
    strip_noise,
)

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


ENTERPRISE_SOURCE_URL = "https://intranet.example.test/handbook/guide.html"

ENTERPRISE_HTML = """
<html>
  <head><title>Enterprise guide</title></head>
  <body>
    <nav>Enterprise navigation</nav>
    <div role="navigation">Secondary navigation</div>
  <aside>Unrelated page furniture</aside>
  <main>
      <h1>Enterprise guide</h1>
      <h2>Deployment</h2>
      <p>Use the <a href="../api/v1?format=html">deployment API</a>.</p>
      <ul>
        <li>Prepare the service
          <ul>
            <li>Set the environment</li>
            <li>Run <code>owlbear serve --check</code></li>
          </ul>
        </li>
      </ul>
      <pre><code class="language-python">def ready():
    return True
</code></pre>
      <p><img src="./images/runbook.png" alt="Deployment runbook diagram"></p>
      <table>
        <tr><th>Setting</th><th>Value</th></tr>
        <tr><td>Allowed | hosts</td><td>intranet</td></tr>
        <tr><td colspan="2">Shared policy row</td></tr>
      </table>
      <p hidden>Hidden tab content</p>
      <p aria-hidden="true">Screen-reader-hidden content</p>
      <p style="display: none">CSS-hidden content</p>
      <p style="visibility: hidden">Visibility-hidden content</p>
      <p aria-hidden="false">Visible explanatory content</p>
    </main>
    <script>Enterprise script payload</script>
    <div class="cookie-banner">Cookie consent</div>
    <footer>Enterprise footer</footer>
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


def test_enterprise_fallback_preserves_structure_and_resolves_relative_urls() -> None:
    markdown = html_to_markdown(strip_noise(ENTERPRISE_HTML), url=ENTERPRISE_SOURCE_URL)

    assert "# Enterprise guide" in markdown
    assert "## Deployment" in markdown
    assert "[deployment API](https://intranet.example.test/api/v1?format=html)" in markdown
    assert "- Prepare the service" in markdown
    assert "  - Set the environment" in markdown
    assert "  - Run `owlbear serve --check`" in markdown
    assert "```python\ndef ready():\n    return True\n```" in markdown
    assert "![Deployment runbook diagram](https://intranet.example.test/handbook/images/runbook.png)" in markdown
    assert "| Allowed \\| hosts | intranet |" in markdown
    assert "| Shared policy row |  |" in markdown
    assert "Visible explanatory content" in markdown
    assert "Hidden tab content" not in markdown
    assert "Screen-reader-hidden content" not in markdown
    assert "CSS-hidden content" not in markdown
    assert "Visibility-hidden content" not in markdown
    assert "Enterprise navigation" not in markdown
    assert "Unrelated page furniture" not in markdown
    assert "Enterprise script payload" not in markdown
    assert "Cookie consent" not in markdown
    assert "Enterprise footer" not in markdown


def test_relative_urls_remain_relative_without_a_source_url() -> None:
    markdown = html_to_markdown(strip_noise(ENTERPRISE_HTML))

    assert "[deployment API](../api/v1?format=html)" in markdown
    assert "![Deployment runbook diagram](./images/runbook.png)" in markdown


def test_extract_content_preserves_the_enterprise_corpus() -> None:
    markdown = extract_content(ENTERPRISE_HTML, url=ENTERPRISE_SOURCE_URL)

    assert "# Enterprise guide" in markdown
    assert "  - Set the environment" in markdown
    assert "```python\ndef ready():\n    return True\n```" in markdown
    assert "![Deployment runbook diagram](https://intranet.example.test/handbook/images/runbook.png)" in markdown
    assert "| Allowed \\| hosts | intranet |" in markdown
    assert "Hidden tab content" not in markdown
    assert "Enterprise navigation" not in markdown


def test_normalize_preserves_nested_list_indentation_and_code_whitespace() -> None:
    markdown = normalize("- parent\n  - child\n\n```python\n  indented()\n    nested()\n```")

    assert markdown == "- parent\n  - child\n\n```python\n  indented()\n    nested()\n```"


def test_extract_prefers_trafilatura_when_all_fallback_links_are_retained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "[deployment API](https://intranet.example.test/api/v1?format=html)"

    def fake_extract(*_args: object, **_kwargs: object) -> str:
        return expected

    monkeypatch.setattr(extractor_module.trafilatura, "extract", fake_extract)

    assert (
        extract_content(
            '<main><p><a href="../api/v1?format=html">deployment API</a></p></main>',
            url=ENTERPRISE_SOURCE_URL,
        )
        == expected
    )


def test_extract_falls_back_when_trafilatura_drops_a_link_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_extract(*_args: object, **_kwargs: object) -> str:
        return "Deployment API"

    monkeypatch.setattr(extractor_module.trafilatura, "extract", fake_extract)

    markdown = extract_content(
        '<main><p><a href="../api/v1?format=html">deployment API</a></p></main>',
        url=ENTERPRISE_SOURCE_URL,
    )

    assert markdown == "[deployment API](https://intranet.example.test/api/v1?format=html)"


def test_strip_noise_removes_known_page_chrome() -> None:
    stripped = strip_noise(REPRESENTATIVE_HTML)

    assert "Fixture article" in stripped
    assert "Fixture navigation" not in stripped
    assert "Fixture script payload" not in stripped
    assert "Fixture cookie chrome" not in stripped


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "  Plain\u200b  text\r\n\r\n\r\nwith\u00a0  spaces ",
            "Plain text\n\nwith spaces",
        ),
        (
            "#  Heading\ufeff\r\n\r\n\r\n-  Markdown\u200c item\u200d",
            "# Heading\n\n- Markdown item",
        ),
    ],
)
def test_normalize_direct_text(text: str, expected: str) -> None:
    assert normalize(text) == expected


def test_normalize_is_idempotent() -> None:
    normalized = normalize("Text\u200b  with\r\n\r\n\r\nspaces")

    assert normalize(normalized) == normalized


def test_normalize_does_not_parse_html(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        pytest.fail("normalize must not parse HTML")

    monkeypatch.setattr(cleaner_module.lxml_html, "document_fromstring", fail_if_called)
    monkeypatch.setattr(cleaner_module.lxml_html, "fromstring", fail_if_called)

    assert normalize("Plain\u00a0  text") == "Plain text"


def test_extractors_return_article_content() -> None:
    _assert_article_content(extract(REPRESENTATIVE_HTML))
    _assert_article_content(extract_content(REPRESENTATIVE_HTML, url="https://example.com/article"))


@pytest.mark.parametrize("converter", [clean, extract, extract_content, html_to_markdown, normalize, strip_noise])
def test_public_callables_return_empty_for_empty_input(converter) -> None:
    assert converter("") == ""


def test_extract_rejects_non_string_input() -> None:
    with pytest.raises(TypeError, match="html must be str"):
        extract(123)
