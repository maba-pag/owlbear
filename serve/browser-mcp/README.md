# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes browser automation tools to pipeline agents for authenticated web content
fetching. Uses Playwright with a persistent Chromium profile; a dedicated profile is created by
default, while `PLAYWRIGHT_USER_DATA_DIR` can point to an existing profile. Both `navigate` and
`acquire` apply the explicit domain allowlist and SSRF checks.

**Use this guide when:** you need to configure the alpha browser server or change its allowlisted
Edge/CDP actions and accessibility-snapshot boundary.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Authenticated browser acquisition is implemented, but the server still needs
real-world validation across target sites, Edge profiles, and SSO environments.

---

## Launch / Usage

```bash
BROWSER_ALLOWED_DOMAINS="sharepoint.example.com,wiki.example.com" \
  uv run python -m owlbear_browser_mcp
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

For local testing across multiple public sites, set `BROWSER_ALLOWED_DOMAINS="*"` in the Browser
server's `env` object. This is a testing convenience, not a production policy: exact hostnames
remain the recommended configuration. The wildcard does not disable SSRF protection; DNS results
for private, loopback, link-local, reserved, or unspecified addresses are still rejected.

Fresh consumer setup seeds this wildcard so the Browser can be exercised immediately. Replace it
with exact hostnames before using the project against production or sensitive sites.

### Tools

| Tool | Description |
| --- | --- |
| `acquire` | Acquire one rendered page and return its structured success or failure result |
| `navigate` | Navigate to a URL and return the page's plain-text content |
| `click` | Click an element identified by CSS selector |
| `type_input` | Type text into an input field identified by CSS selector |
| `select` | Select an option in a `<select>` element by value |
| `read_text` | Return the current page's plain-text content without navigating |
| `snapshot` | Return the current page's Markdown accessibility snapshot |

`acquire` accepts a URL, optional readiness/content selectors, timeouts, and an explicit
diagnostic-HTML opt-in. It does not accept arbitrary browser actions, scripts, credentials, or
session inputs. Its failure status is returned as part of the structured result rather than being
converted into a generic transport error.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BROWSER_ALLOWED_DOMAINS` | _(empty; consumer seed uses `*`)_ | Comma-separated list of permitted hostnames; navigation and acquisition to any other domain are blocked. **Required** — all domains are blocked when unset. Use `*` only for local testing. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` | Path to an existing browser profile directory for authenticated sessions |

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Chromium
> with `uv run --project ../owlbear playwright install chromium` before starting the server.

Both tools now apply the same MCP-side policy before delegating to Playwright. The preflight checks
cannot fully prevent DNS rebinding or an allowlisted server redirecting to a private address;
keep the allowlist narrow for production use.
