# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes browser automation tools for rendered web content. On macOS it selects
stable Microsoft Edge with a fixed OwlBear-owned profile by default; elsewhere it selects Chromium.
The browser launches on the first action call and launches again after its window is closed.
`read_text` and `snapshot` only read an open page and never launch it. Managed Edge never reads,
copies, or controls the operator's daily Edge profile. Both `navigate` and `acquire` apply the
explicit domain allowlist and DNS/IP preflight checks.

**Use this guide when:** you need to configure browser modes, allowlisted actions, or the
accessibility-snapshot boundary.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Browser startup and visible sign-in are implemented; authenticated access remains
target-specific and requires the [managed Mac pilot](../../setup/setup-guide.md#browser-readiness).
Browser readiness and extension presence do not prove authentication.

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
| `browser_status` | Report bounded process-local browser readiness and latest acquisition state |

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

`browser_status` describes selected browser mechanics, startup state, visible authentication
availability, and the most recent acquisition status for this process. It has no global
authenticated field: `ready` means the browser launched, not that a user is signed in or any target
is accessible. Confirm authenticated access for each target separately.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `BROWSER_MODE` | `managed-edge` on macOS; `chromium` elsewhere | Select `managed-edge` or `chromium`. An unset or blank value uses the platform default; any other value prevents browser startup and reports `invalid-mode`. |
| `BROWSER_ALLOWED_DOMAINS` | _(empty; consumer seed uses `*`)_ | Comma-separated list of permitted hostnames; navigation and acquisition to any other domain are blocked. Exact entries explicitly permit that hostname's private/internal DNS results (not reserved or unspecified addresses); **required** — all domains are blocked when unset. Use `*` only for local testing; it does not permit private destinations. |
| `PLAYWRIGHT_USER_DATA_DIR` | `~/.owlbear/chromium-profile` in Chromium mode | Selects the Chromium profile only; use an absolute path for an override. Managed Edge always uses `~/.owlbear/edge-profile` and ignores this setting. |
| `SSO_EXTENSION_PATH` | unset | Optional explicit extension directory used only in Chromium mode; extension presence does not prove authentication. |

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
| `startup_state` | `not-launched` before the first action or after the window closes; `ready` when live; otherwise `unavailable` |
| `startup_reason` | A bounded startup reason above, or `null` |
| `visible_authentication` | Whether a visible browser is available for interactive sign-in; not proof of sign-in |
| `latest_acquisition_status` | The latest `acquire` result for this process, or `null` before an acquisition |
| `startup_diagnostic` | A bounded startup diagnostic, or `null`; it does not expose profile paths or session values |

The optional SSO extension is used only by Chromium startup. The core launcher requires an explicit
`SSO_EXTENSION_PATH`; it does not search platform-specific locations.

## Dependencies

| Package | Purpose |
| --- | --- |
| `mcp` | MCPServer framework |
| `owlbear-browser` | Playwright-based content fetcher (workspace package) |

> **First-time setup:** Install Playwright Chromium with
> `uv run --project ../owlbear playwright install chromium` when selecting Chromium mode or running
> Cockpit browser-backed tests. Managed Edge uses stable Microsoft Edge already installed on macOS.

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
