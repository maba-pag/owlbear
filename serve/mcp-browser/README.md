# owlbear-mcp-browser — Browser MCP Server

MCP server that exposes browser automation tools to pipeline agents for authenticated web content fetching. Uses Playwright with an existing Edge profile so SSO-protected pages are accessible without re-authentication. Navigation is restricted to an explicit domain allowlist; SSRF protections block private and loopback addresses.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
BROWSER_ALLOWED_DOMAINS="sharepoint.example.com,wiki.example.com" \
  uv run python -m owlbear_mcp_browser
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json`.

### Tools

| Tool | Description |
|------|-------------|
| `navigate` | Navigate to a URL and return the page's plain-text content |
| `click` | Click an element identified by CSS selector |
| `type_input` | Type text into an input field identified by CSS selector |
| `select` | Select an option in a `<select>` element by value |
| `read_text` | Return the current page's plain-text content without navigating |
| `snapshot` | Return the current page's raw HTML |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BROWSER_ALLOWED_DOMAINS` | _(empty)_ | Comma-separated list of permitted hostnames; navigation to any other domain is blocked. **Required** — all domains are blocked when unset. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` | Path to an existing browser profile directory for authenticated sessions |
| `BROWSER_TOOLS_EXCLUDE` | _(none)_ | Comma-separated tool names to remove at startup |

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** Install Playwright browsers once with `playwright install chromium` before starting the server.
