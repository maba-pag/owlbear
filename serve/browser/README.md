# owlbear-browser — Browser Content Fetcher

Public and authenticated web content acquisition through Playwright's persistent Chromium context.
A dedicated OwlBear profile is created by default; callers can provide an existing profile when a
permitted logged-in session is required. This package does not select Microsoft Edge or attach to an
existing browser through CDP.

**Use this guide when:** you need to extend the alpha authenticated page acquisition or its cleaned
content extraction API.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Basic rendered-page acquisition, explicit readiness checks, and typed success or
failure results are implemented. Managed enterprise SSO, target-site compatibility, and production
profile policies still need real-world validation.

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
| `AcquisitionRequest` | Validated URL, selector, and timeout inputs for structured acquisition |
| `AcquisitionSuccess` / `AcquisitionFailure` | Typed success and failure result variants |
| `AcquisitionStatus` | Status enum carried by each acquisition result |
| `extract_content(html, url)` | Convert rendered HTML to normalized Markdown through the shared web-content package |
| `find_sso_extension()` | Locate an explicitly configured or platform-discovered extension directory |
| `AuthenticationRequired` | Authentication exception used by interactive page-control callers; structured acquisition reports an `AcquisitionFailure` instead |
| `SSOExtensionNotFoundError` | Raised when an explicitly requested or discovered extension cannot be found |

## Configuration

| Setting | Default | Description |
| --- | --- | --- |
| `user_data_dir` constructor argument | `~/.owlbear/browser-profile` | Persistent Chromium profile owned by the launcher; provide an existing profile only when its use is approved |
| `headless` constructor argument | `false` | A visible context permits manual authentication; headless acquisition cannot provide an interactive login step |
| `SSO_EXTENSION_PATH` environment variable | unset | Explicit path to an extension directory loaded into the Chromium context |

When `SSO_EXTENSION_PATH` is unset, discovery checks a Windows-style Chrome extension location.
On macOS and other platforms, do not infer managed SSO support from that fallback. An extension
path being found or loaded proves only configuration, not successful tenant authentication,
Conditional Access, MFA, or device compliance.

## Acquisition Contract

`BrowserContentFetcher.acquire()` returns a typed `AcquisitionSuccess` or `AcquisitionFailure`.
Successful content is normalized Markdown, not plain text. The request supports an optional content
selector, readiness selector, and bounded navigation/readiness timeouts. It does not follow discovered
links, execute caller-supplied scripts, accept credentials, or ingest content into Knowledge.

Authentication-required failures retain the page for a retry within the same fetcher. Callers must
provide their own user interaction and cancellation policy; the package does not claim a complete
managed-SSO workflow or concurrent session ownership model. See the maintained
[acquisition tests](tests/test_acquisition.py) for the exercised synthetic behavior.

## Dependencies

| Package | Purpose |
| --- | --- |
| `playwright` | Chromium browser automation and persistent contexts |
| `owlbear-web-content` | Shared HTML-to-Markdown extraction (workspace package) |
| `lxml` | Direct HTML parsing for diagnostic sanitization |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Chromium
> with `uv run --project ../owlbear playwright install chromium`.
