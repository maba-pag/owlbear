# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes browser automation tools for web content fetching. It selects stable
Microsoft Edge with a fixed OwlBear-owned profile by default on macOS and Chromium elsewhere.
Managed Edge never reads, copies, or controls the operator's daily Edge profile; both `navigate` and
`acquire` apply the explicit domain allowlist and SSRF checks.

**Use this guide when:** you need to configure browser modes, allowlisted actions, or the
accessibility-snapshot boundary.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Browser startup and visible sign-in are implemented; authenticated access remains
target-specific and requires the [managed Mac pilot](../../setup/setup-guide.md#managed-mac-browser-pilot).
Readiness and extension presence do not prove authentication.

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
| `navigate` | Navigate to a URL and return the page's plain-text content |
| `click` | Click an element identified by CSS selector |
| `type_input` | Type text into an input field identified by CSS selector |
| `select` | Select an option in a `<select>` element by value |
| `read_text` | Return the current page's plain-text content without navigating |
| `snapshot` | Return the current page's Markdown accessibility snapshot |
| `browser_status` | Report bounded process-local startup and latest acquisition state |

`acquire` accepts a URL, optional readiness/content selectors, timeouts, and an explicit
diagnostic-HTML opt-in. It does not accept arbitrary browser actions, scripts, credentials, or
session inputs. Its failure status is returned as part of the structured result rather than being
converted into a generic transport error.

`browser_status` describes selected browser mechanics, startup state, visible authentication
availability, and the most recent acquisition status for this process. It has no global
authenticated field: `ready` means the browser launched, not that a user is signed in or any target
is accessible. Confirm authenticated access for each target separately.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BROWSER_MODE` | `managed-edge` on macOS; `chromium` elsewhere | Select `managed-edge` or `chromium`. An unset or blank value uses the platform default; any other value prevents browser startup and reports `invalid-mode`. |
| `BROWSER_ALLOWED_DOMAINS` | _(empty; consumer seed uses `*`)_ | Comma-separated list of permitted hostnames; navigation and acquisition to any other domain are blocked. Exact entries explicitly permit that hostname's private/internal DNS results (not reserved or unspecified addresses); **required** — all domains are blocked when unset. Use `*` only for local testing; it does not permit private destinations. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` in Chromium mode | Selects the Chromium profile only. Managed Edge always uses `~/.owlbear/edge-profile` and ignores this override. |

### Startup reason codes

When `startup_state` is `unavailable`, `startup_reason` is one of these bounded values:

| Reason | Meaning |
| --- | --- |
| `edge-unavailable` | Stable Microsoft Edge is missing or cannot be launched in managed Edge mode |
| `profile-in-use` | The OwlBear-managed Edge profile is already in use |
| `invalid-mode` | `BROWSER_MODE` is not `managed-edge` or `chromium` |
| `startup-failed` | Another browser startup failure occurred |

### `browser_status` fields

| Field | Meaning |
| --- | --- |
| `browser_mode` | Selected mode: `managed-edge` or `chromium` |
| `ownership` | `per-user-owned`; the server uses an OwlBear-owned profile |
| `startup_state` | `ready` when the browser and page started; otherwise `unavailable` |
| `startup_reason` | A bounded startup reason above, or `null` |
| `visible_authentication` | Whether a visible browser is available for interactive sign-in; not proof of sign-in |
| `latest_acquisition_status` | The latest `acquire` result for this process, or `null` before an acquisition |
| `startup_diagnostic` | A bounded startup diagnostic, or `null`; it does not expose profile paths or session values |

The optional SSO extension is used only by Chromium startup. Its presence does not prove that SSO
works or that a SharePoint, Confluence, or other target is authenticated.

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** Install Playwright Chromium with
> `uv run --project ../owlbear playwright install chromium` when selecting Chromium mode or running
> Cockpit browser-backed tests. Managed Edge uses stable Microsoft Edge already installed on macOS.

Both tools now apply the same MCP-side policy before delegating to Playwright. The preflight checks
cannot fully prevent DNS rebinding or an allowlisted server redirecting to a private address;
keep the allowlist narrow for production use.
