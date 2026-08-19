# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes browser automation tools to pipeline agents for authenticated web content
fetching. Uses Playwright with a persistent Chromium profile; a dedicated profile is created by
default, while `PLAYWRIGHT_USER_DATA_DIR` can point to an existing profile. The `navigate` tool is
restricted to an explicit domain allowlist and applies SSRF checks.

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
| `BROWSER_ALLOWED_DOMAINS` | _(empty)_ | Comma-separated list of permitted hostnames; navigation to any other domain is blocked. **Required** — all domains are blocked when unset. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` | Path to an existing browser profile directory for authenticated sessions |

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** From a consumer project using a sibling OwlBear checkout, install Chromium
> with `uv run --project ../owlbear playwright install chromium` before starting the server.

`acquire` currently does not apply the same MCP-side allowlist and SSRF preflight as `navigate`.
Treat it as a separate capability and do not use it for untrusted URLs until those boundaries are
unified.
