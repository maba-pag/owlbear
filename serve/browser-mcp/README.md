# owlbear-browser-mcp — Browser MCP Server

MCP server that exposes browser automation tools for rendered web content. On macOS it selects
stable Microsoft Edge with a fixed OwlBear-owned profile by default; elsewhere it selects Chromium.
The browser launches on the first action call and relaunches after the last OwlBear-owned window
closes. Closing a shared page while another owned window remains open keeps status `ready`; the next
action reopens the page.
`read_text` and `snapshot` only read an open page and never launch it. Managed Edge never reads,
copies, or controls the operator's daily Edge profile. Both `navigate` and `acquire` apply the
explicit domain allowlist and DNS/IP preflight checks.

**Use this guide when:** you need to configure browser modes, allowlisted actions, or the
accessibility-snapshot boundary.

Package map: [serve/README.md](../README.md) · Project README: [README.md](../../README.md)

**Status:** Alpha. Browser startup and visible sign-in are implemented; authenticated access remains
target-specific and requires the [managed Mac pilot](#managed-mac-pilot).
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

OwlBear's own `.mcp.json` uses this wildcard so the Browser can be exercised immediately. Replace it
with exact hostnames before using it against production or sensitive sites.

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
| `BROWSER_ALLOWED_DOMAINS` | _(empty; OwlBear's `.mcp.json` uses `*`)_ | Comma-separated list of permitted hostnames; navigation and acquisition to any other domain are blocked. Exact entries explicitly permit that hostname's private/internal DNS results (not reserved or unspecified addresses); **required** — all domains are blocked when unset. Use `*` only for local testing; it does not permit private destinations. |
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
| `startup_state` | `not-launched` before the first action or after the last OwlBear-owned window closes; `ready` while an owned window remains open, including after the shared page closes (the next action reopens it); otherwise `unavailable` |
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
> `uv run --project ../owlbear playwright install chromium` when selecting Chromium mode.
> Managed Edge uses stable Microsoft Edge already installed on macOS.

Both tools now apply the same MCP-side policy before delegating to Playwright. Exact allowlist
entries are the explicit approval for private, loopback, or link-local results from that hostname;
wildcard mode is a public-site testing convenience and does not grant that approval. The preflight
checks cannot fully prevent DNS rebinding or an allowlisted server redirecting to a private address;
keep the allowlist narrow for production use. A running MCP process proves startup only, not that
Chromium is installed, an approved session is authenticated, or a Knowledge source can be refreshed.

## Readiness

Chromium is optional. Install it when you select Browser MCP Chromium mode; the default managed Edge
mode needs stable Microsoft Edge.

Check MCP startup, browser capability, and Knowledge ingestion separately. A running MCP process
does not prove that the selected browser launched, that a target is authenticated, or that a
Browser-to-Knowledge round is ready.

1. **MCP process startup:** Run **MCP: List Servers** and confirm `owlbear-browser` and
   `owlbear-knowledge` show `running`.

   **Expected result:** both stdio processes are available; this confirms startup only.
2. **Browser readiness:** An unset `BROWSER_MODE` selects managed Edge and its fixed OwlBear
   profile. Confirm stable Microsoft Edge is installed before starting the Browser MCP. For
   Chromium mode, install Chromium for the OwlBear runtime:

    ```shell
    uv run --project ~/.owlbear/runtime playwright install chromium
    ```

   This download is not required for managed Edge mode. To select Chromium explicitly, set
   `BROWSER_MODE` to `chromium` in the local `owlbear-browser` server environment; an
   invalid mode is reported as `invalid-mode` rather than silently falling back to another browser.
   `PLAYWRIGHT_USER_DATA_DIR` only affects Chromium and should be an absolute path; managed Edge
   always uses `~/.owlbear/edge-profile` and ignores that override.

   Check `BROWSER_ALLOWED_DOMAINS` in the `owlbear-browser` entry of the MCP configuration.
   OwlBear's own `.mcp.json` uses `"*"` for local testing across public sites; use exact hostnames
   for normal or production use.

   Restart the `owlbear-browser` MCP server and call `browser_status`; it reports `not-launched`
   before any browser action. The first `acquire` or `navigate` call against an allowed URL launches
   the selected visible browser; complete the organization's login flow manually if needed.

    **Expected result:** `acquire` on an allowed URL returns rendered content or a structured
    acquisition result. `browser_status` reports `ready` while an OwlBear-owned window remains open;
    closing a shared page while another owned window remains open keeps it `ready`, and the next
    action reopens that page. It reports `not-launched` before first use or after the last owned
    window closes, and `unavailable` with a startup reason when launch fails. Readiness does not prove
    sign-in or authenticated access. Exact-host entries explicitly
   permit private, loopback, and link-local DNS results for that hostname; wildcard mode does not.
   Reserved and unspecified addresses are always rejected. The current SSRF preflight does not
   fully prevent DNS rebinding or an allowlisted server redirecting to a private address; these
   are accepted limits, so keep the allowlist narrow. See [Launch / Usage](#launch--usage) for the
   full policy.
3. **Managed SSO readiness:** The default is a visible managed Edge session using the
   fixed `~/.owlbear/edge-profile`; `PLAYWRIGHT_USER_DATA_DIR` and `SSO_EXTENSION_PATH` do not
   configure managed Edge. Call an allowed `navigate` or `acquire` action to launch the browser,
   then verify one permitted target site with the organization's normal login flow. Chromium mode
   uses a separate profile and can load only an explicitly configured extension directory. A ready
   browser or loaded extension is not proof of tenant authentication, MFA, Conditional Access, or
   device compliance. Do not collect cookies or tokens, weaken enterprise policy, or claim SSO
   support from MCP startup.
4. **Knowledge ingestion readiness:** Register an approved browser source with
   `register_knowledge_source` as `kind: "url_list"` and `fetch_method: "browser"`. Call
   `list_knowledge_sources` to get its `source_id` and registered `urls`; acquire each URL and
   submit the captures together in one bound `knowledge_ingest` call for that source. Call
   `list_knowledge_sources` again to check its health.

   **Expected result:** a fully successful round reports `ok`. See the
   [Knowledge operations guide](../../share/skills/h-knowledge-ops/SKILL.md) for the source and
   capture contract, including other health outcomes.

See the [Browser-to-Knowledge vertical test](../../tests/test_browser_knowledge_vertical.py) for the
exercised end-to-end workflow.

### Managed Mac pilot

Run this pilot on the managed Mac before relying on SharePoint or Confluence access. Keep the two
approved target URLs local; do not put URLs, hostnames, page content, credentials, or session files in
the repository or in a Change's brief, answers, or status.

1. Install stable Microsoft Edge and start the `owlbear-browser` MCP server. Leave
  `BROWSER_MODE` and `PLAYWRIGHT_USER_DATA_DIR` unset for the managed default. Configure
  `BROWSER_ALLOWED_DOMAINS` locally for only the two approved target hosts.

  **Expected result:** before any browser action, `browser_status` reports `managed-edge`,
  `per-user-owned`, `not-launched`, null startup reason, and unavailable visible authentication.
  Stop if the mode is invalid; do not switch to Chromium or the operator's daily Edge profile.
2. Call `acquire` with one locally supplied, operator-approved SharePoint URL. The first action
  launches the visible Edge window with the fixed OwlBear profile. Complete first-use sign-in, site
  trust, consent, or MFA directly in that window; no interactive MCP tool participates.
  Do not send credentials or session material through an OwlBear request or result.

  **Expected result:** the Edge window is live and the operator confirms authenticated SharePoint
  content. Browser readiness alone does not count as authentication.
3. Repeat the action with one locally supplied, operator-approved Confluence URL and confirm its
  authenticated content in the owned Edge window.

  **Expected result:** the operator confirms authenticated Confluence content in the same owned
  session; record no page content, URL, or hostname.
4. Close the last OwlBear-owned Edge window and call `browser_status`, then call `acquire` for one
  approved target. Closing only the shared page while another owned window remains open keeps status
  `ready`; the next `acquire` reopens that page without relaunching the browser.

  **Expected result:** status reports `not-launched` after the last owned window closes; the next
  `acquire` relaunches the fixed profile and the operator confirms the target remains authenticated.
5. Restart the `owlbear-browser` MCP server, repeat an allowed action for each target, and confirm
  that the fixed profile retains session availability. Stop the server normally afterward.

  **Expected result:** both targets remain authenticated after restart, no `--no-sandbox` or
  unsupported-flag warning appears, and only OwlBear-owned browser resources close. Record only each
  target class (`SharePoint` or `Confluence`) and `pass` or `fail`; include no URL, hostname, page
  content, credential, or session data.

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
