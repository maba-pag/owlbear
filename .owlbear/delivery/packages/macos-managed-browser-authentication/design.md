# macOS Managed-Browser Authentication Design

> Status: formal candidate; final challenge pending
> Governing intent: `macos-managed-browser-authentication`

## Current Ownership

`serve/browser/src/owlbear_browser/playwright_launcher.py` owns browser launch, persistent profiles, static capabilities, and launcher cleanup. `serve/browser-mcp/src/owlbear_browser_mcp/server.py` owns environment resolution, lifespan composition, the visible shared page, safe startup classification, and MCP operations. `BrowserContentFetcher.acquire()` remains the structured target interface; B2/#231 owns readiness and page classification. Current #234 code owns general partial-startup and cleanup behavior.

## Selected Architecture

On macOS, omitted mode resolves to `managed-edge`. The launcher uses Playwright's stable `msedge` channel, `chromium_sandbox=True`, and one fixed per-user profile, expected at `~/.owlbear/edge-profile`. Browser MCP keeps its lifespan-owned page visible; the operator interacts directly with that page for first-use authentication. No interactive MCP tool participates.

The managed profile does not accept `PLAYWRIGHT_USER_DATA_DIR`; that legacy override remains only for explicit Chromium and preserved non-macOS behavior. A second workspace encountering profile contention fails closed. Explicit Chromium uses its distinct current profile behavior. Non-macOS omitted mode remains Chromium.

CDP is excluded because the owned profile succeeded in the pilot and CDP would add lower fidelity, debugging policy, and shared-session ownership.

## Configuration Contract

Browser MCP resolves `BROWSER_MODE` and passes typed mode/profile settings to the core launcher. The core may retain existing non-macOS `SSO_EXTENSION_PATH` and `LOCALAPPDATA` reads solely for preserved Windows behavior.

```text
BROWSER_MODE=managed-edge | chromium
PLAYWRIGHT_USER_DATA_DIR=<Chromium/non-macOS override only>
```

Resolution rules:

- macOS plus omitted mode -> managed Edge and fixed per-user profile;
- macOS plus explicit Chromium -> bundled Chromium and current profile resolution;
- non-macOS plus omitted mode -> current Chromium behavior;
- invalid mode -> `invalid-mode`;
- missing Edge -> `edge-unavailable`;
- profile contention -> `profile-in-use`;
- other launch failure -> `startup-failed`;
- no unavailable managed mode falls back to Chromium.

The safe reason vocabulary is produced at Browser MCP composition using typed launcher exceptions or bounded classification rather than raw exception text.

## Launcher Contract

The launcher accepts resolved mode/profile inputs and owns channel selection, sandboxing, process/context/page custody, static capabilities, and integration with existing idempotent cleanup.

Replace `microsoft_sso` with capability semantics that do not imply authentication. Static capabilities describe mode, owned persistent-profile availability, and visible authentication availability. Keep `find_sso_extension`, `SSOExtensionNotFoundError`, `build_playwright_args`, and their environment behavior only where required to preserve existing non-macOS behavior. macOS managed mode never consumes them. Update current capability assertions while preserving their #234 cleanup meaning.

## First-Use And Adjacent Boundaries

The existing Browser MCP lifespan creates and retains a visible shared page for the server lifetime. That page is the first-use onboarding surface. The operator may complete Edge profile sign-in, site trust, consent, or MFA directly in the window. B1 does not invoke `click`, `type`, `navigate`, or another interactive MCP tool and does not claim those tools are suitable for secrets; B5/#233 owns them.

B1's pilot stops at launcher/page evidence: the requested host opens in the owned session, the operator confirms authenticated content, and session availability survives restart. B1 does not claim `BrowserContentFetcher.acquire()` recognizes delayed content, login shells, HTTP errors, redirects, or final article boundaries. B2 owns those guarantees.

## Browser Status Contract

Add `browser_status` as read-only, idempotent, and non-destructive. Grant it to `share/agents/knowledge-ingestor.agent.md`, the maintained caller already granted `acquire`.

Canonical fields:

```text
browser_mode: managed-edge | chromium
ownership: per-user-owned
startup_state: ready | unavailable
startup_reason: edge-unavailable | profile-in-use | invalid-mode | startup-failed | null
visible_authentication: available | unavailable
latest_acquisition_status: <AcquisitionStatus> | null
startup_diagnostic: <bounded safe string> | null
```

Omit identity-integration claims, profile paths, URLs, and hostnames. Status is process-local and not persisted. `latest_acquisition_status` is the last completed `acquire` status in this process and implies nothing about another target. `knowledge-ingestor` uses status only for diagnosis and routing, never as permission to ingest or proof of authenticated content.

## Failure And Compatibility

- Managed Edge never falls back to Chromium.
- Authentication-required and expired-session remain target outcomes, not startup failure.
- Managed Edge enables sandboxing and emits no rejected `--no-sandbox` warning in the managed-device procedure.
- Mode-specific shutdown crosses the existing #234 cleanup boundary; B1 adds no second cleanup framework.
- Current non-macOS and explicit Chromium behavior remains.
- Browser and setup documentation describes selected behavior without claiming extension presence proves SSO.

## Proof Approach

Automated proof crosses launcher and MCP public boundaries with browser/policy dependencies replaced below them:

- macOS default, explicit Chromium override, and preserved non-macOS mode;
- Edge channel, sandbox, and fixed profile;
- managed mode ignores arbitrary profile override;
- typed missing-Edge and contention classification;
- static capabilities contain no extension-derived authentication claim;
- `browser_status` schema, annotations, safe reason codes, process-local latest outcome, and `knowledge-ingestor` grant;
- maintained #234 cleanup behavior after capability changes.

The managed-device procedure uses the lifespan-owned Edge page to open approved SharePoint and Jira targets, records bounded host/status/title and operator-confirmed authenticated state, verifies no rejected sandbox warning, restarts the profile, and verifies session availability. It retains no page content or session files.

## Known Limits

One Browser MCP workspace owns the profile at a time. First use can require interaction. Device policy can change. The pilot proves one environment. B2 remains required before structured acquisition is trusted for automated ingestion or replacement. B5 remains responsible for generic interactive-tool input/output safety.

## Planning Scope

`SCOPE-001` binds `OUT-001` and maintains the complete atomic implementation and proof boundary:

- `serve/browser/src/owlbear_browser/playwright_launcher.py` and core exports;
- new or existing Browser tests for mode resolution, sandboxing, fixed profile custody, fail-closed launcher errors, and truthful static capabilities;
- `serve/browser-mcp/src/owlbear_browser_mcp/server.py`, public exports, status/configuration tests, and `serve/browser-mcp/tests/test_lifecycle.py` capability adaptation while retaining #234 cleanup assertions;
- `share/agents/knowledge-ingestor.agent.md` and `tests/test_agent_ecosystem_validation.py` for the status grant;
- `serve/browser/README.md`, `serve/browser-mcp/README.md`, `setup/setup-guide.md`, `seed/.vscode/mcp.json`, and `tests/test_setup_init_settings.py` for configuration, setup, and status parity.

Its proof boundary includes public launcher behavior, registered MCP schema/annotations, safe ready/unavailable projections, live agent grant validation, setup-seed parity, maintained lifecycle cleanup, and the bounded managed-Mac pilot. It excludes target classification, generic interactive tools, and cleanup redesign.

## Delivery Contract

```yaml target-contract
kind: outcome
id: OUT-001
title: Managed Edge authentication readiness
promise: macOS Browser MCP provides one isolated authenticated Edge session and truthful readiness for its maintained ingestion caller without touching the daily browser or implying universal authentication.
acceptance:
  - "Given macOS with omitted BROWSER_MODE and stable Edge installed, Browser MCP launches the msedge channel with Chromium sandboxing and the fixed per-user OwlBear profile."
  - "Given explicit BROWSER_MODE=chromium or a non-macOS host with omitted mode, Browser MCP launches the preserved Chromium mode and does not use the managed Edge profile."
  - "Given missing Edge, invalid mode, the per-user Edge profile owned by another workspace, or another startup failure, Browser MCP reports edge-unavailable, invalid-mode, profile-in-use, or startup-failed respectively and does not launch Chromium as a substitute."
  - "Given first use, the operator can complete sign-in, site trust, consent, or MFA directly in the visible lifespan-owned Edge window without B1 sending session material through an OwlBear request or result."
  - "Given ready managed Edge, browser_status returns managed-edge, per-user-owned, ready, null startup reason, visible authentication available, null startup diagnostic, and no global authenticated field."
  - "Given unavailable managed Edge, browser_status returns unavailable with its bounded reason and diagnostic and exposes no profile path, URL, hostname, page content, cookie, token, or session value."
  - "Given no completed acquisition, browser_status returns null latest acquisition status; given one completed acquire call, it returns that AcquisitionStatus for this process without a persisted authentication claim."
  - "Given the registered Browser MCP inventory and knowledge-ingestor definition, browser_status is read-only, idempotent, non-destructive, and granted beside acquire."
  - "Given the managed-Mac pilot procedure, the lifespan-owned Edge page opens approved SharePoint and Jira targets with operator-confirmed authenticated content, retains session availability after profile restart, emits no rejected no-sandbox warning, and closes only OwlBear-owned resources."
  - "Given the maintained Browser, Browser MCP, setup, seed, agent, and validation surfaces named in SCOPE-001, focused and routed checks pass without weakening #234 cleanup or claiming B2 target classification."
commitments: [COM-001, COM-002, COM-003, COM-004, COM-005, COM-006]
dependencies: []
```

## Formal Gates

Fresh derivation, source-grounded Design challenge, clean baselines, checkpoint, deterministic validation, and explicit admission approval remain pending.
