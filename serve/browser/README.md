# owlbear-browser — Browser Content Fetcher

Authenticated web content extraction via Playwright. The Browser MCP selects stable Microsoft Edge
by default on macOS and Chromium elsewhere, using an OwlBear-owned persistent profile. It never
reads, copies, or controls the operator's daily Edge profile.

**Use this guide when:** you need to extend the alpha authenticated page acquisition or its cleaned
content extraction API.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Launch mechanics are implemented; authentication must be confirmed for each
target. Browser readiness or extension presence does not prove that sign-in succeeded.

---

## Launch / Usage

No standalone launch. Use via `BrowserContentFetcher` or call `extract_content` directly.

### Fetch a page with Playwright

```python
from owlbear_browser import AcquisitionRequest, PlaywrightLauncher

async with PlaywrightLauncher() as launcher:
    result = await launcher.acquire(AcquisitionRequest(url="https://example.com/page"))
    print(result.status)
```

### Public API

| Symbol | Purpose |
| --- | --- |
| `BrowserContentFetcher` | Async fetcher backed by a Playwright `BrowserContext` |
| `PlaywrightLauncher` | Manages Playwright browser lifecycle |
| `BrowserMode` | Selects Chromium or managed Edge |
| `extract_content(html, url)` | Clean raw HTML to plain text via trafilatura |
| `find_sso_extension()` | Locate the optional Microsoft SSO extension used by Chromium |
| `AuthenticationRequired` | Raised when a page requires login and no session is available |
| `SSOExtensionNotFoundError` | Raised when the SSO extension cannot be found |

## Configuration

`PlaywrightLauncher()` defaults to Chromium; pass `mode=BrowserMode.MANAGED_EDGE` to launch
Microsoft Edge with the fixed `~/.owlbear/edge-profile`. Managed Edge ignores `user_data_dir`.
Chromium accepts a dedicated `user_data_dir` and defaults to `~/.owlbear/browser-profile` when none
is supplied. The Browser MCP's `BROWSER_MODE` and `PLAYWRIGHT_USER_DATA_DIR` behavior is documented
in the [Browser MCP guide](../browser-mcp/README.md#configuration).

In Chromium mode, extension discovery reads `SSO_EXTENSION_PATH` when set, then uses
`LOCALAPPDATA` on Windows to locate the bundled Microsoft SSO extension. The optional extension is
a launch aid only: finding it does not establish that SSO works or that any target is authenticated.

## Dependencies

| Package | Purpose |
| --- | --- |
| `playwright` | Browser automation (Edge CDP) |
| `trafilatura` | HTML-to-text extraction |
| `lxml` | HTML parsing (trafilatura dependency) |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Playwright
> Chromium with `uv run --project ../owlbear playwright install chromium` only when selecting
> Chromium mode or running Cockpit browser-backed tests. Managed Edge uses stable Microsoft Edge
> already installed on macOS.
