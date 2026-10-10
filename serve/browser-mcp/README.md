# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes Playwright-based browser tools to pipeline agents for rendered web content
fetching. It launches a persistent Chromium profile on the first `navigate`, `acquire`, `click`,
`type_input`, or `select` call rather than at server start, and launches or reopens it on the next
such call after the window is closed. `read_text` and `snapshot` only read an open page and never
launch the browser. A dedicated profile is created by default,
while `PLAYWRIGHT_USER_DATA_DIR` can point to an existing profile. It does not select Microsoft
Edge or attach to an existing browser through CDP. Both `navigate` and `acquire` apply the explicit
domain allowlist and DNS/IP preflight checks.

**Use this guide when:** you need to configure the alpha browser server or change its allowlisted
Playwright actions and accessibility-snapshot boundary.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Basic rendered-page acquisition and typed failure results are implemented, but
target-site compatibility, approved profile policies, and managed SSO environments still need
real-world validation.

---

## Launch / Usage

```bash
BROWSER_ALLOWED_DOMAINS="sharepoint.example.com,wiki.example.com" \
  uv run python -m owlbear_browser_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

For local testing across multiple public sites, set `BROWSER_ALLOWED_DOMAINS="*"` in the Browser
server's `env` object. This is a testing convenience, not a production policy: exact hostnames
remain the recommended configuration. An exact hostname entry is also the explicit approval for
that hostname's private, loopback, or link-local DNS results. Reserved and unspecified addresses
remain rejected. The wildcard does not grant that internal approval, so private destinations
remain rejected in testing mode.

Fresh consumer setup seeds this wildcard so the Browser can be exercised immediately. Replace it
with exact hostnames before using the project against production or sensitive sites.

### Tools

| Tool | Description |
| --- | --- |
| `acquire` | Acquire one rendered page and return its structured success or failure result |
| `navigate` | Navigate to a URL and return the page's normalized Markdown content |
| `click` | Click an element identified by CSS selector |
| `type_input` | Fill an input field identified by CSS selector |
| `select` | Select an option in a `<select>` element by value |
| `read_text` | Return the current page's normalized Markdown content without navigating |
| `snapshot` | Return the current page's Playwright ARIA accessibility snapshot in YAML |

Action tools (`navigate`, `acquire`, `click`, `type_input`, `select`) launch or reopen the browser
when needed; `read_text` and `snapshot` require an open page and raise a browser-unavailable error
otherwise. `type_input` never echoes typed text, and `snapshot` returns YAML.

`acquire` accepts a URL, optional readiness/content selectors, and bounded navigation/readiness
timeouts. It does not accept arbitrary browser actions, scripts, credentials, session inputs, or
diagnostic-HTML options. Its failure status and redacted diagnostics are returned as part of the
structured result rather than being converted into a generic transport error. The shared contract
applies URL redaction when constructing `AcquisitionSuccess`: userinfo and fragments are removed;
values for exact sensitive keys and normalized keys ending in `token`, `secret`, `signature`,
`password`, `credential`, or `assertion` become `%5BREDACTED%5D`; `state`, `session_state`, and `nonce` values
become `%5BCORRELATION%5D`. The `code` key is exact-match only, and other query bytes and paths
remain for document identity. Diagnostic URLs with secret-like paths are replaced in full; MCP
serialization projects the already-redacted fields.
Any main-document status of 400 or above other than 401 and 403 returns `http_error`. Login-form or
authentication-title detection takes precedence for 401/403, returning
`authentication_required` before `access_denied`.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BROWSER_ALLOWED_DOMAINS` | _(empty; consumer seed uses `*`)_ | Comma-separated list of permitted hostnames; navigation and acquisition to any other domain are blocked. Exact entries explicitly permit that hostname's private/internal DNS results (not reserved or unspecified addresses); **required** — all domains are blocked when unset. Use `*` only for local testing; it does not permit private destinations. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` | Path to an existing browser profile directory for authenticated sessions; provide an absolute path because a leading `~` is not expanded |
| `SSO_EXTENSION_PATH` | unset | Optional extension directory passed to the Chromium launcher; finding or loading it does not prove managed SSO readiness |

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Chromium
> with `uv run --project ../owlbear playwright install chromium` before starting the server.

Both tools now apply the same MCP-side policy before delegating to Playwright. Exact allowlist
entries are the explicit approval for private, loopback, or link-local results from that hostname;
wildcard mode is a public-site testing convenience and does not grant that approval. The preflight
checks cannot fully prevent DNS rebinding or an allowlisted server redirecting to a private address;
keep the allowlist narrow for production use. A running MCP process proves startup only, not that
Chromium is installed, an approved session is authenticated, or a Knowledge source can be refreshed.

## Browser and Knowledge Boundaries

`acquire` returns rendered Markdown and a structured success/failure mapping. It does not call the
Knowledge MCP server. An agent can acquire each URL from a registered Browser source, then submit
the captures together in one bound `knowledge_ingest` round. This is an agent-mediated capture
workflow, not an automatic refresh path; the Knowledge process does not own a live Browser session.
See the [Knowledge operations guide](../../share/skills/h-knowledge-ops/SKILL.md) for the ingest
contract and the [Browser-to-Knowledge vertical test](../../tests/test_browser_knowledge_vertical.py)
for the exercised workflow.

See the [Browser package guide](../browser/README.md), the [acquisition tests](tests/test_acquire.py),
and the [SSRF policy tests](tests/test_ssrf_preflight.py) for the exercised browser boundary.
