# owlbear-browser — Browser Content Fetcher

Authenticated web content extraction via Playwright and Edge CDP. Launches a browser with an existing user profile so that logged-in sessions (SSO, SharePoint, etc.) are available without re-authentication.

**Use this guide when:** you need to extend the alpha authenticated page acquisition or its cleaned
content extraction API.

Package map: [serve/README.md](../README.md) · Workspace guide: [README.md](../../README.md)

**Status:** Alpha. Authenticated acquisition is implemented, but Browser still needs
real-world validation across the target sites and session environments.

---

## Launch / Usage

No standalone launch. Use via `BrowserContentFetcher` or call `extract_content` directly.

### Fetch a page with Playwright

```python
from owlbear_browser import BrowserContentFetcher, PlaywrightLauncher

async with PlaywrightLauncher() as launcher:
    async with launcher.new_context() as context:
        fetcher = BrowserContentFetcher(context)
        text = await fetcher.fetch("https://example.com/page")
        print(text)  # cleaned plain-text content
```

### Public API

| Symbol | Purpose |
| --- | --- |
| `BrowserContentFetcher` | Async fetcher backed by a Playwright `BrowserContext` |
| `PlaywrightLauncher` | Manages Playwright browser lifecycle |
| `extract_content(html, url)` | Clean raw HTML to plain text via trafilatura |
| `find_sso_extension()` | Locate the Edge SSO extension for authenticated sessions |
| `AuthenticationRequired` | Raised when a page requires login and no session is available |
| `SSOExtensionNotFoundError` | Raised when the SSO extension cannot be found |

## Configuration

No environment variables. The `PlaywrightLauncher` accepts an optional `user_data_dir` path pointing to an existing browser profile directory (e.g. `~/.config/microsoft-edge`).

## Dependencies

| Package | Purpose |
| --- | --- |
| `playwright` | Browser automation (Edge CDP) |
| `trafilatura` | HTML-to-text extraction |
| `lxml` | HTML parsing (trafilatura dependency) |

> **First-time setup:** Install Playwright browsers once with `playwright install chromium` (or the relevant browser).
