# owlbear-web-content - Shared HTML to Markdown Converter

Pure structural HTML extraction and Markdown normalization without browser or knowledge-system
coupling. The package provides extraction, noise removal, and Markdown conversion for HTML content.

Package map: [serve/README.md](../README.md) - [Project README](../../README.md)

## Launch / Usage

This package is a library and has no standalone launch command. Import its public API:

```python
from owlbear_web_content import clean, extract, extract_content, normalize

markdown = extract(html_string)
markdown_with_url = extract_content(html_string, url="https://example.com/article")
normalized_text = normalize(plain_or_markdown_text)
cleaned_html = clean(html_string)
```

## Configuration

The converter accepts HTML strings and an optional source URL. It reads no environment variables,
files, credentials, or browser configuration.

## Dependencies

The package uses `lxml` for structural parsing and `trafilatura` for main-content extraction. It
does not import Browser, Knowledge, Playwright, or any other OwlBear package.

## Public API

| Symbol | Purpose |
| --- | --- |
| `extract(html)` | Extract main content from HTML as normalized Markdown |
| `extract_content(html, url)` | Extract content with an optional source URL |
| `strip_noise(html_str)` | Remove navigation, scripts, cookies, and known page chrome |
| `html_to_markdown(html_str)` | Convert HTML while preserving structural elements |
| `normalize(text)` | Normalize plain text or Markdown without parsing HTML |
| `clean(html_str)` | Strip noise, convert HTML to Markdown, and normalize the result |
