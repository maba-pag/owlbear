import pytest

from owlbear_browser.cleaner import clean as browser_clean
from owlbear_browser.cleaner import html_to_markdown as browser_html_to_markdown
from owlbear_browser.cleaner import strip_noise as browser_strip_noise
from owlbear_browser.extractor import extract as browser_extract
from owlbear_browser.extractor import extract_content as browser_extract_content
from owlbear_web_content import clean as shared_clean
from owlbear_web_content import extract as shared_extract
from owlbear_web_content import extract_content as shared_extract_content
from owlbear_web_content import html_to_markdown as shared_html_to_markdown
from owlbear_web_content import strip_noise as shared_strip_noise

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


@pytest.mark.parametrize(
    ("browser_callable", "shared_callable", "uses_url"),
    [
        (browser_clean, shared_clean, False),
        (browser_extract, shared_extract, False),
        (browser_extract_content, shared_extract_content, True),
        (browser_html_to_markdown, shared_html_to_markdown, False),
        (browser_strip_noise, shared_strip_noise, False),
    ],
)
def test_browser_content_callables_match_shared_core(browser_callable, shared_callable, uses_url) -> None:
    kwargs = {"url": "https://example.com/article"} if uses_url else {}

    browser_result = browser_callable(REPRESENTATIVE_HTML, **kwargs)
    shared_result = shared_callable(REPRESENTATIVE_HTML, **kwargs)

    assert browser_result == shared_result
    assert "Fixture article" in browser_result


def test_browser_extract_preserves_documented_input_error() -> None:
    with pytest.raises(TypeError) as browser_error:
        browser_extract(123)
    with pytest.raises(TypeError) as shared_error:
        shared_extract(123)

    assert type(browser_error.value) is type(shared_error.value)
    assert str(browser_error.value) == str(shared_error.value)
