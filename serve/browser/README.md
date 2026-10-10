# owlbear-browser — Browser Content Fetcher

Public and authenticated web content acquisition through Playwright's persistent browser context.
The Browser MCP selects stable Microsoft Edge by default on macOS and Chromium elsewhere, using an
OwlBear-owned profile. A standalone `PlaywrightLauncher()` defaults to Chromium. Managed Edge uses
its fixed OwlBear profile and never reads, copies, or controls the operator's daily Edge profile.

**Use this guide when:** you need to extend the alpha authenticated page acquisition or its cleaned
content extraction API.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Typed acquisition results and launch mechanics are implemented; authentication
must be confirmed for each target. Browser readiness or extension presence does not prove sign-in.

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
| `AuthenticationCapabilities` | Reports browser mechanics without claiming authentication |
| `AcquisitionRequest` | Validated URL, selector, and timeout inputs for structured acquisition |
| `AcquisitionSuccess` / `AcquisitionFailure` | Typed success and failure result variants |
| `AcquisitionStatus` | Status enum carried by each acquisition result |
| `extract_content(html, url)` | Convert rendered HTML to normalized Markdown through the shared web-content package |
| `find_sso_extension()` | Locate the explicitly configured extension directory |
| `AuthenticationRequired` | Authentication exception used by interactive page-control callers; structured acquisition reports an `AcquisitionFailure` instead |
| `SSOExtensionNotFoundError` | Raised when the explicit extension path is missing or invalid |

## Configuration

| Setting | Default | Description |
| --- | --- | --- |
| `mode` constructor argument | `chromium` | Selects Chromium or managed Edge; the standalone launcher defaults to Chromium |
| `user_data_dir` constructor argument | `~/.owlbear/browser-profile` | Persistent Chromium profile; managed Edge always uses `~/.owlbear/edge-profile` and ignores this argument |
| `headless` constructor argument | `false` | Chromium may run headless; managed Edge is always visible |
| `SSO_EXTENSION_PATH` environment variable | unset | Optional explicit extension directory loaded only in Chromium mode |

The launcher does not search platform-specific extension locations. Set `SSO_EXTENSION_PATH` to an
approved existing directory when the extension is needed. Finding or loading an extension proves
only configuration, not successful tenant authentication, Conditional Access, MFA, or device
compliance. The Browser MCP's platform default and its Chromium profile override are documented in
the [Browser MCP guide](../browser-mcp/README.md#configuration).

## Acquisition Contract

`BrowserContentFetcher.acquire()` returns a typed `AcquisitionSuccess` or `AcquisitionFailure`.
Successful content is normalized Markdown, not plain text. The request supports an optional content
selector, readiness selector, and bounded navigation/readiness timeouts. It does not follow discovered
links, execute caller-supplied scripts, accept credentials, or ingest content into Knowledge.
The Browser-to-Knowledge path is agent-mediated: an agent can combine Browser captures for a
registered source in one bound `knowledge_ingest` round. See the [Knowledge operations guide](../../share/skills/h-knowledge-ops/SKILL.md)
for that contract.

Authentication-required failures retain the page for a retry within the same fetcher. Callers must
provide their own user interaction and cancellation policy; the package does not claim a complete
managed-SSO workflow or concurrent session ownership model. Any main-document status of 400 or above
other than 401 and 403 returns `http_error`. A 401 or 403 page with a
login-form or authentication-title signal returns `authentication_required` before the fallback
`access_denied` classification. See the [acquisition tests](tests/test_acquisition.py) for synthetic
acquisition behavior and the [Browser-to-Knowledge vertical test](../../tests/test_browser_knowledge_vertical.py)
for the agent-mediated round.

`AcquisitionSuccess` applies URL redaction at construction: userinfo and fragments are removed;
values for exact sensitive keys and normalized keys ending in `token`, `secret`, `signature`,
`password`, `credential`, or `assertion` become `%5BREDACTED%5D`; `state`, `session_state`, and `nonce` values
become `%5BCORRELATION%5D`. The `code` key is exact-match only. Other query bytes and paths remain
for document identity. Diagnostic URLs with secret-like paths are replaced in full.

## Dependencies

| Package | Purpose |
| --- | --- |
| `playwright` | Chromium browser automation and persistent contexts |
| `owlbear-web-content` | Shared HTML-to-Markdown extraction (workspace package) |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Playwright
> Chromium with `uv run --project ../owlbear playwright install chromium` only when selecting
> Chromium mode or running Cockpit browser-backed tests. Managed Edge uses stable Microsoft Edge
> already installed on macOS.
