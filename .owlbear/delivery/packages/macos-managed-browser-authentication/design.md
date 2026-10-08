# macOS Managed-Browser Authentication Design

> Status: formal candidate; final challenge pending
> Governing intent: `macos-managed-browser-authentication`

## Current Ownership

`serve/browser/src/owlbear_browser/playwright_launcher.py` owns browser launch, persistent profiles, static capabilities, and launcher cleanup. `serve/browser-mcp/src/owlbear_browser_mcp/server.py` owns environment resolution, lifespan composition, lazy launch and relaunch (`_launch_browser`, `_ensure_browser`, `_require_live_page` since dev `d4ce5ffa8`), the visible shared page, safe startup classification, and MCP operations. `BrowserContentFetcher.acquire()` remains the structured target interface; B2/#231 owns readiness and page classification. Current #234 code owns general partial-startup and cleanup behavior.

## Selected Architecture

On macOS, omitted mode resolves to `managed-edge`. The launcher uses Playwright's stable `msedge` channel, `chromium_sandbox=True`, and one fixed per-user profile, expected at `~/.owlbear/edge-profile`. Browser MCP keeps dev's lazy launch: `app_lifespan` resolves mode and profile without launching; the first action tool call (`acquire`, `navigate`, `click`, `type_input`, `select`) launches managed Edge through `_ensure_browser` and opens its visible OwlBear-owned page; after the operator closes the window the launcher stops running, and the next action call replaces it and relaunches with the same profile. "Lifespan-owned" means owned by the Browser MCP lifespan context, which closes it at shutdown. The operator interacts directly with that window for first-use authentication. No interactive MCP tool participates.

The managed profile does not accept `PLAYWRIGHT_USER_DATA_DIR`; that legacy override remains only for explicit Chromium and preserved non-macOS behavior. A second workspace encountering profile contention fails closed. Explicit Chromium uses its distinct current profile behavior. Non-macOS omitted mode remains Chromium.

CDP is excluded because the owned profile succeeded in the pilot and CDP would add lower fidelity, debugging policy, and shared-session ownership. Launch at server start is not restored: lazy launch is the selected dev behavior (DEC-009) and avoids opening a window for sessions that never browse.

## Configuration Contract

Browser MCP resolves `BROWSER_MODE` at server start and passes typed mode/profile settings to the core launcher when an action call launches it. The core may retain existing non-macOS `SSO_EXTENSION_PATH` and `LOCALAPPDATA` reads solely for preserved Windows behavior.

```text
BROWSER_MODE=managed-edge | chromium
PLAYWRIGHT_USER_DATA_DIR=<Chromium/non-macOS override only>
```

Resolution rules:

- macOS plus omitted mode -> managed Edge and fixed per-user profile;
- macOS plus explicit Chromium -> bundled Chromium and current profile resolution;
- non-macOS plus omitted mode -> current Chromium behavior;
- invalid mode -> `invalid-mode`, recorded at server start; action calls then fail with that bounded reason and launch nothing;
- missing Edge -> `edge-unavailable`;
- profile contention -> `profile-in-use`;
- other launch failure -> `startup-failed`;
- no unavailable managed mode falls back to Chromium, including on retry.

The safe reason vocabulary is produced at Browser MCP composition using typed launcher exceptions or bounded classification rather than raw exception text. A failed launch records its reason; the next action call retries the same mode and clears the reason only on success.

## Launcher Contract

The launcher accepts resolved mode/profile inputs and owns channel selection, sandboxing, process/context/page custody, static capabilities, its `is_running` signal, and integration with existing idempotent cleanup.

Replace `microsoft_sso` with capability semantics that do not imply authentication. Static capabilities describe mode, owned persistent-profile availability, and visible authentication availability. Keep `find_sso_extension`, `SSOExtensionNotFoundError`, `build_playwright_args`, and their environment behavior only where required to preserve existing non-macOS behavior. macOS managed mode never consumes them. Update current capability assertions while preserving their #234 cleanup meaning.

## First-Use And Adjacent Boundaries

Under lazy launch, the first action call creates the visible shared page and Browser MCP retains it until the window closes or the server stops. That window is the first-use onboarding surface. The operator may complete Edge profile sign-in, site trust, consent, or MFA directly in the window. B1 does not invoke `click`, `type`, `navigate`, or another interactive MCP tool and does not claim those tools are suitable for secrets; B5/#233 owns them. `browser_status`, `read_text`, and `snapshot` never launch the browser.

B1's pilot stops at launcher/page evidence: the requested host opens in the owned session, the operator confirms authenticated content, and session availability survives window close/relaunch and restart. B1 does not claim `BrowserContentFetcher.acquire()` recognizes delayed content, login shells, HTTP errors, redirects, or final article boundaries. B2 owns those guarantees.

## Browser Status Contract

Add `browser_status` as read-only, idempotent, and non-destructive. It only reads `AppContext` state; unlike action tools it never calls `_ensure_browser`, so it never launches, relaunches, reopens a page, or cleans up a stale launcher. Grant it to `share/agents/knowledge-ingestor.agent.md`, the maintained caller already granted `acquire`, with guidance that `not-launched` is the normal state before the first `acquire` (or after the window closed) and that `acquire` launches the browser.

Canonical fields:

```text
browser_mode: managed-edge | chromium
ownership: per-user-owned
startup_state: not-launched | ready | unavailable
startup_reason: edge-unavailable | profile-in-use | invalid-mode | startup-failed | null
visible_authentication: available | unavailable
latest_acquisition_status: <AcquisitionStatus> | null
startup_diagnostic: <bounded safe string> | null
```

State projection, evaluated in order:

| Condition | startup_state | startup_reason | visible_authentication |
| --- | --- | --- | --- |
| Invalid mode recorded at server start, or the last launch attempt failed (recorded failure reason) | `unavailable` | the bounded reason | unavailable |
| Launcher present and `is_running`, whether its shared page is live, closed, or not yet reopened | `ready` | null | available |
| Otherwise: no launch attempted yet, or the launched window was closed (launcher absent or not running) | `not-launched` | null | unavailable |

A running launcher whose shared page was closed stays `ready`: the next action call reopens the page through `_ensure_browser` without relaunching. A page-reopen failure is returned by that action call as a bounded browser-unavailable error and does not record a launch failure or change `startup_state`. A successful launch clears any recorded failure reason.

Omit identity-integration claims, profile paths, URLs, and hostnames. Status is process-local and not persisted. `latest_acquisition_status` is the last completed `acquire` status in this process and implies nothing about another target. `knowledge-ingestor` uses status only for diagnosis and routing, never as permission to ingest or proof of authenticated content.

## Failure And Compatibility

- Managed Edge never falls back to Chromium, on first launch, relaunch, or retry.
- Authentication-required and expired-session remain target outcomes, not startup failure.
- Managed Edge enables sandboxing and emits no rejected `--no-sandbox` warning in the managed-device procedure.
- Mode-specific shutdown and stale-launcher replacement cross the existing #234 cleanup boundary and dev's `_ensure_browser` replacement; B1 adds no second cleanup framework.
- Current non-macOS and explicit Chromium behavior remains, including its lazy launch.
- Browser and setup documentation describes selected behavior, lazy launch, and the three status states without claiming extension presence proves SSO.

## Migration

Implementation builds on dev's lazy-launch Browser MCP (`d4ce5ffa8`, dev `b49039234` or later). The Change branch head `e5cc2d0` predates it; Delivery's target sync must bring the integration target into the Change before implementation continues. A previous preserved target-sync conflict was aborted; resolving the next one belongs to Delivery's target-conflict workflow, not this Design. Existing Change work that assumed launch at server start is adapted, not preserved as behavior.

## Proof Approach

Automated proof crosses launcher and MCP public boundaries with browser/policy dependencies replaced below them:

- macOS default, explicit Chromium override, and preserved non-macOS mode;
- Edge channel, sandbox, and fixed profile;
- managed mode ignores arbitrary profile override;
- typed missing-Edge and contention classification, invalid mode at server start, and retry after a failed launch without Chromium fallback;
- lazy launch on the first action call, `not-launched` before it and after window close, relaunch with the same profile, `ready` with a closed shared page and its reopen on the next action call, and no launch from `browser_status`, `read_text`, or `snapshot`;
- static capabilities contain no extension-derived authentication claim;
- `browser_status` schema, annotations, three-state projection, safe reason codes, process-local latest outcome, and `knowledge-ingestor` grant;
- maintained #234 cleanup behavior after capability changes.

The revised managed-device procedure is maintained in `setup/setup-guide.md` under the managed-Mac browser pilot section. It instructs the operator to supply one approved SharePoint URL and one approved Confluence URL locally, confirm that authenticated access is available, let the first `acquire` open the OwlBear-owned Edge window, open both targets in it, and record only bounded target-class and pass/fail outcomes. The procedure verifies no rejected sandbox warning, closes the window and confirms `browser_status` reports `not-launched`, lets the next `acquire` relaunch it with session availability, restarts the profile, and verifies session availability. It retains no page content, target URLs, hostnames, credentials, or session files in Delivery authority or browser status. Prior SharePoint/Jira pilot observations remain historical evidence for launcher/profile behavior but do not satisfy this revised target set.

## Known Limits

One Browser MCP workspace owns the profile at a time. First use can require interaction. Device policy can change. The pilot proves one environment. B2 remains required before structured acquisition is trusted for automated ingestion or replacement. B5 remains responsible for generic interactive-tool input/output safety. `browser_status` cannot open the authentication window; an action call must. The `interactive-browser-tools` (B5) package refers to B1 `browser_status` as unchanged; reconciling it with the three-state contract belongs to B5. Window-close detection relies on the launcher's `is_running` signal; status between the close and the next action call reports `not-launched`. `ready` describes a running launcher, not a live shared page; a page-reopen failure surfaces only on the failing action call.

## Planning Scope

`SCOPE-001` binds `OUT-001` and maintains the complete atomic implementation and proof boundary:

- `serve/browser/src/owlbear_browser/playwright_launcher.py` and core exports;
- new or existing Browser tests for mode resolution, sandboxing, fixed profile custody, fail-closed launcher errors, and truthful static capabilities;
- `serve/browser-mcp/src/owlbear_browser_mcp/server.py`, public exports, status/configuration tests, and `serve/browser-mcp/tests/test_lifecycle.py` capability and lazy-launch adaptation while retaining #234 cleanup assertions;
- `serve/browser-mcp/tests/test_acquire.py`, `serve/browser-mcp/tests/test_interactive_tools.py`, and `serve/browser-mcp/tests/test_ssrf_preflight.py`, which construct `AppContext` or patch `PlaywrightLauncher` and must follow its mode/status changes;
- `share/agents/knowledge-ingestor.agent.md` (status grant and not-launched guidance) and `tests/test_agent_ecosystem_validation.py` for the status grant;
- `serve/browser/README.md`, `serve/browser-mcp/README.md`, `setup/setup-guide.md`, `seed/.vscode/mcp.json`, and `tests/test_setup_init_settings.py` for configuration, setup, and status parity.

Its proof boundary includes public launcher behavior, registered MCP schema/annotations, safe not-launched/ready/unavailable projections, lazy launch and relaunch, live agent grant validation, setup-seed parity, maintained lifecycle cleanup, and the bounded managed-Mac pilot. It excludes target classification, generic interactive tools, and cleanup redesign.

## Delivery Contract

```yaml target-contract
kind: outcome
id: OUT-001
title: Managed Edge authentication readiness
promise: macOS Browser MCP provides one isolated authenticated Edge session and truthful readiness for its maintained ingestion caller without touching the daily browser or implying universal authentication.
acceptance:
  - "Given macOS with omitted BROWSER_MODE and stable Edge installed, Browser MCP launches the msedge channel with Chromium sandboxing and the fixed per-user OwlBear profile."
  - "Given explicit BROWSER_MODE=chromium or a non-macOS host with omitted mode, Browser MCP launches the preserved Chromium mode and does not use the managed Edge profile."
  - "Given managed mode with PLAYWRIGHT_USER_DATA_DIR set to another path, Browser MCP ignores that override and uses the fixed per-user OwlBear Edge profile."
  - "Given missing Edge, invalid mode, the per-user Edge profile owned by another workspace, or another startup failure, Browser MCP reports edge-unavailable, invalid-mode, profile-in-use, or startup-failed respectively and does not launch Chromium as a substitute."
  - "Given first use, the first action tool call (normally acquire) opens the visible OwlBear-owned Edge window and the operator can complete sign-in, site trust, consent, or MFA directly in it without an interactive MCP tool and without B1 sending session material through an OwlBear request or result."
  - "Given ready managed Edge, browser_status returns managed-edge, per-user-owned, ready, null startup reason, visible authentication available, null startup diagnostic, and no global authenticated field."
  - "Given unavailable managed Edge, browser_status returns unavailable with its bounded reason and diagnostic and exposes no profile path, URL, hostname, page content, cookie, token, or session value."
  - "Given no completed acquisition, browser_status returns null latest acquisition status; given one completed acquire call, it returns that AcquisitionStatus for this process without a persisted authentication claim."
  - "Given the registered Browser MCP inventory and knowledge-ingestor definition, browser_status is read-only, idempotent, non-destructive, and granted beside acquire."
  - "Given the maintained setup/setup-guide.md managed-Mac browser pilot procedure, the operator supplies one approved SharePoint URL and one approved Confluence URL locally, confirms authenticated access, and the procedure records only bounded target-class and pass/fail outcomes without persisting target URLs, hostnames, page content, credentials, or session material."
  - "Given the revised managed-Mac pilot procedure, the first acquire opens the OwlBear-owned Edge window, which opens operator-approved SharePoint and Confluence targets with operator-confirmed authenticated content; after the operator closes the window, browser_status reports not-launched and the next acquire relaunches it with session availability retained; session availability also survives profile restart; no rejected no-sandbox warning is emitted; and only OwlBear-owned resources are closed."
  - "Given the maintained Browser, Browser MCP, setup, seed, agent, and validation surfaces named in SCOPE-001, focused and routed checks pass without weakening #234 cleanup or claiming B2 target classification."
  - "Given managed Edge before its first action tool call, or after the operator closes its window, browser_status returns managed-edge, per-user-owned, not-launched, null startup reason, visible authentication unavailable, and null startup diagnostic without launching the browser, read_text and snapshot fail with a bounded browser-unavailable error without launching it, and the next action tool call launches or relaunches managed Edge with the same fixed per-user OwlBear profile, after which browser_status returns ready; given a running managed Edge whose shared page was closed, browser_status returns ready and the next action tool call reopens the page without relaunching the browser."
  - "Given a managed Edge launch that failed with edge-unavailable, profile-in-use, or startup-failed, browser_status returns unavailable with that reason without launching, the next action tool call retries managed Edge and never launches Chromium, and a successful retry makes browser_status return ready with null startup reason; given an invalid BROWSER_MODE, browser_status returns unavailable with invalid-mode from server start before any action call, and action tool calls fail with that bounded reason without launching Edge or Chromium."
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005, COM-006]
dependencies: []
```

## Formal Gates

This package revises previously admitted B1 authority. Fresh derivation, source-grounded Design challenge, clean baselines, checkpoint, deterministic validation, explicit approval, and re-admission are required before B1 resumes.
