# macOS Managed-Browser Authentication

> Status: formal candidate; final challenge pending
> Origin: B1 planning disposition for GitHub issue #228
> Governing research: `.owlbear/research/browser-package-audit-2026-09-05.md`
> Decision source: user-confirmed resolution of `REQ-TASK-004-MANAGED-MAC-PILOT`; the approved pilot target set is revised from SharePoint/Jira to SharePoint/Confluence. User decisions of 2026-10-09 adopt dev's lazy browser launch (dev commit `d4ce5ffa8`) and a three-state `browser_status` startup state.
> Authority state: revision of previously admitted B1 authority, authored while the Change is paused; this candidate must be re-derived, challenged, checkpointed, validated, approved, and re-admitted before B1 resumes.

## Problem And Actors

OwlBear began this capability on Windows, where managed Edge and its permitted Microsoft SSO extension worked. OwlBear now runs on macOS, where Edge remains the operator's default browser and automatically signs the operator into SharePoint, Jira, Confluence, and other internal services through managed Edge and device identity.

Current OwlBear code launches bundled Chromium, uses Windows-oriented extension discovery, and treats extension presence as `microsoft_sso` without proving browser or session identity. The primary operator needs an isolated authenticated browser that respects MDM and Conditional Access without copying credentials, cookies, tokens, profile files, or session material through B1's onboarding or status interfaces.

Since dev commit `d4ce5ffa8`, Browser MCP no longer launches its browser at server start: the first action tool call launches it, and the next action call after the operator closes the window relaunches it. B1 builds on that lazy launch instead of restoring launch at server start.

## Operating Context

- **Actors and trust (inferred from the admitted B1 authority):** the operator is trusted; agents calling Browser MCP (`knowledge-ingestor`) are trusted but fallible; device policy (MDM, Conditional Access) is an external authority B1 must respect, not bypass.
- **Exposure (inferred):** rendered internal and public web content reaches the owned browser; Browser MCP results return to agents. Session material must never cross the MCP request/result boundary.
- **Stakes (inferred):** a leaked session or a daily-profile mutation affects the operator's company identity and is not locally reversible; a wrong readiness claim misroutes ingestion but is recoverable.
- **Guarded:** daily-profile use, silent Chromium substitution, session material in status or results, universal authentication claims, launching from read-only status. **Not guarded:** generic interactive-tool input safety (B5/#233), target classification (B2/#231), destination policy (#226).

## Product Promise

On macOS, OwlBear defaults to stable Microsoft Edge with one fixed per-user OwlBear-owned persistent profile. The first action tool call (normally `acquire`) opens the visible OwlBear-owned Edge window, which provides first-use sign-in, trust, consent, and MFA interaction; after the operator closes it, the next action call reopens it with the same profile. Browser MCP exposes truthful read-only readiness that distinguishes a not-yet-launched browser from a ready or failed one, fails closed when Edge is unavailable or the profile is already owned by another workspace, and never touches the operator's daily Edge profile or silently substitutes Chromium.

B1 proves browser/profile authentication and session availability at the launcher and the owned-window boundary. B2/#231 separately owns whether structured acquisition classifies a rendered target as complete, authenticated, denied, or erroneous. B5/#233 separately governs the safety and continued existence of generic interactive browser tools.

## Normal Workflow

1. On macOS, Browser MCP resolves managed Edge at server start without launching a browser; `browser_status` reports `not-launched`.
2. The first action tool call (normally `acquire`) launches managed Edge with the fixed per-user OwlBear profile and supported sandbox settings and opens the visible OwlBear-owned window.
3. On first use, the operator completes authentication directly in that visible window. No interactive MCP tool is required or used by B1 onboarding.
4. `knowledge-ingestor` may call `browser_status` before `acquire` to distinguish a not-launched browser (normal; `acquire` launches it), ready browser mechanics, and a failed launch.
5. `acquire` remains authoritative for one target result. Status never turns prior success into global authentication.
6. Closing the window returns status to `not-launched`; the next action call relaunches with the same profile. Restart reuses the dedicated profile, subject to company policy and normal session expiry.
7. Missing Edge, invalid configuration, or profile contention fails closed. A failed launch is retried on the next action call and never falls back to Chromium. Chromium runs only when explicitly selected.

## Scope

### In Scope

- Stable Edge as the macOS default using a fixed per-user OwlBear profile.
- Explicit `chromium` override with its existing separate profile behavior.
- Edge channel and Chromium sandbox configuration.
- Visible first-use interaction through the OwlBear-owned Edge window that the first action call opens under dev's lazy launch, including relaunch after window close.
- Fail-closed launch with distinct safe reasons for missing Edge, invalid mode, profile contention, and other startup failure; `invalid-mode` reported from server start.
- Read-only `browser_status` with `not-launched | ready | unavailable` startup state, plus a `knowledge-ingestor` grant and not-launched guidance.
- Removal of extension-derived authentication claims from macOS mode.
- Managed-Mac pilot proof for SharePoint, Confluence, window close and relaunch, restart persistence, and owned shutdown.
- Focused Browser, Browser MCP (including the existing acquire, interactive-tool, SSRF-preflight, and lifecycle tests), agent, setup, seed, and README updates.

### Out Of Scope

- Target readiness and page classification owned by B2/#231.
- Private destination policy owned by #226.
- General partial-startup and cleanup redesign delivered through #234.
- Generic interactive browser tools and their sensitive-input behavior owned by B5/#233; B1's onboarding does not invoke them.
- Knowledge ingestion and registered browser refresh.
- CDP attachment, daily-profile automation, session export, or policy bypass.
- Changes to non-macOS defaults.
- Restoring browser launch at server start.

### Preserved Behavior

- Structured acquisition result types and package boundaries.
- Closed-by-default destination controls.
- Explicit Chromium mode.
- Existing non-macOS behavior, including Windows extension support and its current core environment reads where still used.
- Existing exception-safe launcher and MCP lifespan cleanup.
- Dev's lazy launch: action tools (`acquire`, `navigate`, `click`, `type_input`, `select`) launch or relaunch the browser; `read_text` and `snapshot` never launch it.

### Accepted Exclusions

- The Windows extension mechanism is not a macOS requirement.
- CDP and daily-profile reuse are excluded.
- One active Browser MCP workspace may own the per-user Edge profile; concurrent workspaces receive bounded contention.
- Pilot evidence is bounded to the selected Mac, tenant, Edge version, and approved targets.
- B1 does not resolve whether existing generic interactive tools can accept or echo sensitive values; B5 must resolve that independently before such tools are granted for authentication.
- `browser_status` never launches the browser, so a status call alone cannot open the authentication window; the first action call does.

## Confirmed Decisions

- macOS defaults to managed Edge and fails closed when unavailable.
- The managed Edge profile is per-user, fixed under OwlBear ownership, and cannot be overridden to the daily profile.
- The visible OwlBear-owned Edge window is the first-use authentication surface.
- Chromium remains explicit; non-macOS defaults remain unchanged.
- Browser MCP adds `browser_status`; `knowledge-ingestor` receives access.
- Status reports mechanics and current process state, never global authentication or a hostname.
- B1 proves session availability; B2 owns target classification; B5 owns generic interaction safety.
- The managed-Mac acceptance pilot uses approved SharePoint and Confluence targets supplied by the operator through the documented pilot procedure. Before launching the pilot, the operator supplies one approved SharePoint URL and one approved Confluence URL through the local procedure and confirms authenticated access; the procedure records only bounded target-class outcomes and pass/fail evidence, not URLs, hostnames, page content, credentials, or session material.
- Browser MCP adopts dev's lazy launch: the first action call launches managed Edge and the next action call after window close relaunches it. This replaces the earlier launch-at-server-start choice.
- `browser_status` reports `startup_state` as `not-launched | ready | unavailable`; it never launches the browser.

The decision blocks below convert these schema-2 records. Each classification is best-effort: entries in this Confirmed Decisions list, the user-resolved pilot request, and the user's 2026-10-09 prompt are `decided`; the source-grounded trust semantics that the user approved only with the package are `approved`.

```yaml target-contract
kind: decision
id: DEC-001
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed architecture and fail-closed policy)
statement: On macOS, omitted BROWSER_MODE selects stable Microsoft Edge through Playwright's msedge channel with Chromium sandboxing, and managed Edge fails closed when unavailable instead of substituting Chromium.
```

```yaml target-contract
kind: decision
id: DEC-002
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed profile ownership)
statement: The managed Edge profile is one fixed per-user OwlBear-owned persistent profile that cannot be overridden to another path or to the daily profile, and one Browser MCP workspace owns it at a time.
```

```yaml target-contract
kind: decision
id: DEC-003
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed onboarding and security boundary)
statement: First-use sign-in, site trust, consent, and MFA happen directly in the visible OwlBear-owned Edge window; no interactive MCP tool participates and no session material crosses an agent or MCP tool.
```

```yaml target-contract
kind: decision
id: DEC-004
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed compatibility boundary)
statement: Bundled Chromium remains explicitly selectable, non-macOS defaults remain unchanged, and CDP attachment and daily-profile reuse are excluded.
```

```yaml target-contract
kind: decision
id: DEC-005
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed status tool and consumer)
statement: Browser MCP adds a read-only browser_status tool granted to knowledge-ingestor; status reports mechanics and current process state, never global authentication or a hostname.
```

```yaml target-contract
kind: decision
id: DEC-006
origin: decided
basis: intent.md Confirmed Decisions of the admitted B1 package (user-confirmed ownership split)
statement: "B1 proves browser/profile session availability; B2/#231 owns target classification; B5/#233 owns generic interactive-tool safety; #234 owns general cleanup."
```

```yaml target-contract
kind: decision
id: DEC-007
origin: decided
basis: user-confirmed resolution of the REQ-TASK-004-MANAGED-MAC-PILOT Decision Request, recorded in the admitted B1 intent
statement: The managed-Mac acceptance pilot runs fresh against one operator-approved SharePoint target and one operator-approved Confluence target supplied locally through the setup-guide procedure, retaining only bounded target-class and pass/fail outcomes; the historical SharePoint/Jira observation does not satisfy it.
```

```yaml target-contract
kind: decision
id: DEC-008
origin: approved
basis: designer source-grounded trust semantics (admitted COM-004 provenance), approved only with the admitted B1 package
statement: Readiness describes configured mechanics and process state; authenticated success is evidence for one target acquisition at one time, and the latest acquisition status is process-local and never persisted.
```

```yaml target-contract
kind: decision
id: DEC-009
origin: decided
basis: user prompt 2026-10-09, confirmed decision 1 (adopt dev lazy browser launch, dev commit d4ce5ffa8)
statement: Browser MCP launches the managed browser only on the first action tool call, normally acquire, and relaunches it on the next action call after the window is closed; the first action call opens the visible OwlBear-owned Edge window where the operator authenticates, replacing the earlier launch-at-server-start choice.
```

```yaml target-contract
kind: decision
id: DEC-010
origin: decided
basis: user prompt 2026-10-09, confirmed decision 2 (option A, three-state browser_status)
statement: browser_status startup_state is not-launched, ready, or unavailable; not-launched holds before the first action call and after window close with null reason and visible authentication unavailable; unavailable with a reason means the last launch failed and the next action call retries without Chromium fallback; invalid-mode is reported from server start; browser_status never launches the browser.
```

## Evidence And Limits

An earlier 2026-09-07 managed-Mac pilot used Playwright 1.62.0 and a new isolated Edge profile. SharePoint displayed authenticated Carrera Online immediately. Jira required `Login Windows` and one Microsoft trust confirmation, then opened AUDIT-124 without credential entry. Both remained authenticated after Edge restart. Three temporary-profile Edge launch/close cycles passed with `chromium_sandbox=True`. One interactive pilot close lost the driver connection; a later close passed, and #234 remains the general cleanup owner. This SharePoint/Jira observation is retained as historical browser/profile evidence and does not satisfy the revised SharePoint/Confluence acceptance target.

Microsoft documents signed-in Edge integration with managed macOS SSO. Playwright documents stable Edge channels, exclusive user-data directories, and unsupported concurrent profile use. Current source confirms bundled Chromium launch, Windows extension inference, divergent profile defaults, and no status tool. Observed on dev `b49039234`: since `d4ce5ffa8`, `app_lifespan` configures the allowlist and profile without launching; `_ensure_browser` launches on action calls, replaces a launcher that is no longer running, and reopens a closed shared page on a running launcher; `read_text` and `snapshot` use `_require_live_page` and never launch.

The earlier pilot confirms browser/session availability through the owned page, not B2's structured classification. Device policy can change. First-use trust, consent, MFA, or profile sign-in can require operator interaction. The authenticated disposable pilot profile is not a durable artifact and must be removed outside the agent write boundary. A revised managed-Mac pilot remains required for the approved SharePoint/Confluence targets. The setup-guide pilot procedure is the operator action boundary: it supplies the two approved URLs locally, requires the operator's confirmation that authenticated access is available, and retains only bounded non-sensitive outcome evidence.

## Success And Proof

Automated proof covers platform mode resolution, explicit Chromium override, fixed profile custody, Edge channel/sandbox arguments, distinct startup reason codes, fail-closed launch and retry, not-launched status before first use and after window close, relaunch, status projection, agent grant, and maintained cleanup behavior. A bounded managed-device procedure proves visible first-use interaction, authenticated session availability for SharePoint and Confluence, window close and relaunch, restart persistence, absence of the rejected launch warning, and owned shutdown without retaining page content or session files.

## Technically Done But Wrong

- Selecting Edge while retaining extension-presence authentication claims.
- Claiming B2 target correctness from launcher/page pilot evidence.
- Requiring an interactive MCP tool for sign-in.
- Claiming B1 makes the separate `type` tool safe for credentials.
- Reporting global `authenticated=true` or internal hostnames in status.
- Allowing managed Edge to use the legacy arbitrary profile override.
- Using the daily profile, silently falling back, or creating one profile per repository.
- Adding `browser_status` without granting and documenting its maintained consumer.
- Splitting launcher mode and Browser MCP readiness into separately acceptable outcomes that leave shared source or tests inconsistent.
- Accepting the historical SharePoint/Jira observation or substituting an unapproved second target instead of running a fresh pilot against operator-approved SharePoint and Confluence targets.
- Treating the setup-guide pilot procedure as permission to retain target URLs, hostnames, page content, credentials, or session material.
- Restoring browser launch at server start, or making `browser_status`, `read_text`, or `snapshot` launch the browser.
- Reporting a never-launched or closed browser as `ready` or as a failed `unavailable` launch.
- Falling back to Chromium after a failed lazy launch or when a retry fails again.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
decisions: [DEC-001, DEC-002]
statement: On macOS, Browser MCP selects stable Microsoft Edge with one fixed per-user OwlBear-owned persistent profile and never reads, copies, or controls the operator's daily Edge profile.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
decisions: [DEC-001, DEC-010]
statement: Missing Edge, invalid mode, unusable Edge, or profile contention produces bounded unavailable state and never silently substitutes Chromium for the managed authentication path.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
decisions: [DEC-003, DEC-009]
statement: B1 first-use sign-in, site trust, consent, or MFA occurs directly in the visible lifespan-owned Edge window without B1 sending session material through an agent or MCP tool.
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
decisions: [DEC-005, DEC-008, DEC-010]
statement: Browser readiness describes configured mechanics and process state, while authenticated success remains evidence for one target acquisition at one time and never becomes a universal authenticated claim.
```

```yaml target-contract
kind: commitment
id: COM-005
class: protected-request
decisions: [DEC-004]
statement: Bundled Chromium remains explicitly selectable and non-macOS defaults remain unchanged; CDP attachment and daily-profile reuse are excluded from this Change.
```

```yaml target-contract
kind: commitment
id: COM-006
class: agreed-path
decisions: [DEC-001, DEC-006, DEC-007]
statement: Managed Edge uses supported sandbox configuration, integrates with the maintained exception-safe cleanup boundary, and is accepted through deterministic tests plus a fresh bounded managed-device pilot against operator-approved SharePoint and Confluence targets.
```

This candidate revises previously admitted B1 authority; no new implementation claim is admitted until the revised contract completes its gates.
