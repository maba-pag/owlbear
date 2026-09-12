# macOS Managed-Browser Authentication

> Status: formal candidate; final challenge pending
> Origin: B1 planning disposition for GitHub issue #228
> Governing research: `.owlbear/research/browser-package-audit-2026-09-05.md`

## Problem And Actors

OwlBear began this capability on Windows, where managed Edge and its permitted Microsoft SSO extension worked. OwlBear now runs on macOS, where Edge remains the operator's default browser and automatically signs the operator into SharePoint, Jira, Confluence, and other internal services through managed Edge and device identity.

Current OwlBear code launches bundled Chromium, uses Windows-oriented extension discovery, and treats extension presence as `microsoft_sso` without proving browser or session identity. The primary operator needs an isolated authenticated browser that respects MDM and Conditional Access without copying credentials, cookies, tokens, profile files, or session material through B1's onboarding or status interfaces.

## Product Promise

On macOS, OwlBear defaults to stable Microsoft Edge with one fixed per-user OwlBear-owned persistent profile. The visible owned Edge window provides first-use sign-in, trust, consent, and MFA interaction. Browser MCP exposes truthful read-only readiness, fails closed when Edge is unavailable or the profile is already owned by another workspace, and never touches the operator's daily Edge profile or silently substitutes Chromium.

B1 proves browser/profile authentication and session availability at the launcher and lifespan-owned page boundary. B2/#231 separately owns whether structured acquisition classifies a rendered target as complete, authenticated, denied, or erroneous. B5/#233 separately governs the safety and continued existence of generic interactive browser tools.

## Normal Workflow

1. On macOS, Browser MCP selects managed Edge and opens the fixed per-user OwlBear profile with supported sandbox settings.
2. On first use, the operator completes authentication directly in the visible lifespan-owned Edge window. No interactive MCP tool is required or used by B1 onboarding.
3. `knowledge-ingestor` may call `browser_status` before `acquire` to distinguish ready browser mechanics from unavailable startup.
4. `acquire` remains authoritative for one target result. Status never turns prior success into global authentication.
5. Restart reuses the dedicated profile, subject to company policy and normal session expiry.
6. Missing Edge, invalid configuration, or profile contention fails closed. Chromium runs only when explicitly selected.

## Scope

### In Scope

- Stable Edge as the macOS default using a fixed per-user OwlBear profile.
- Explicit `chromium` override with its existing separate profile behavior.
- Edge channel and Chromium sandbox configuration.
- Visible first-use interaction through the existing lifespan-owned page.
- Fail-closed startup with distinct safe reasons for missing Edge, invalid mode, profile contention, and other startup failure.
- Read-only `browser_status` plus a `knowledge-ingestor` grant.
- Removal of extension-derived authentication claims from macOS mode.
- Managed-Mac pilot proof for SharePoint, Jira, restart persistence, and owned shutdown.
- Focused Browser, Browser MCP, agent, setup, seed, and README updates.

### Out Of Scope

- Target readiness and page classification owned by B2/#231.
- Private destination policy owned by #226.
- General partial-startup and cleanup redesign delivered through #234.
- Generic interactive browser tools and their sensitive-input behavior owned by B5/#233; B1's onboarding does not invoke them.
- Knowledge ingestion and registered browser refresh.
- CDP attachment, daily-profile automation, session export, or policy bypass.
- Changes to non-macOS defaults.

### Preserved Behavior

- Structured acquisition result types and package boundaries.
- Closed-by-default destination controls.
- Explicit Chromium mode.
- Existing non-macOS behavior, including Windows extension support and its current core environment reads where still used.
- Existing exception-safe launcher and MCP lifespan cleanup.

### Accepted Exclusions

- The Windows extension mechanism is not a macOS requirement.
- CDP and daily-profile reuse are excluded.
- One active Browser MCP workspace may own the per-user Edge profile; concurrent workspaces receive bounded contention.
- Pilot evidence is bounded to the selected Mac, tenant, Edge version, and approved targets.
- B1 does not resolve whether existing generic interactive tools can accept or echo sensitive values; B5 must resolve that independently before such tools are granted for authentication.

## Confirmed Decisions

- macOS defaults to managed Edge and fails closed when unavailable.
- The managed Edge profile is per-user, fixed under OwlBear ownership, and cannot be overridden to the daily profile.
- The visible lifespan-owned page is the first-use authentication surface.
- Chromium remains explicit; non-macOS defaults remain unchanged.
- Browser MCP adds `browser_status`; `knowledge-ingestor` receives access.
- Status reports mechanics and current process state, never global authentication or a hostname.
- B1 proves session availability; B2 owns target classification; B5 owns generic interaction safety.

## Evidence And Limits

The 2026-09-07 managed-Mac pilot used Playwright 1.62.0 and a new isolated Edge profile. SharePoint displayed authenticated Carrera Online immediately. Jira required `Login Windows` and one Microsoft trust confirmation, then opened AUDIT-124 without credential entry. Both remained authenticated after Edge restart. Three temporary-profile Edge launch/close cycles passed with `chromium_sandbox=True`. One interactive pilot close lost the driver connection; a later close passed, and #234 remains the general cleanup owner.

Microsoft documents signed-in Edge integration with managed macOS SSO. Playwright documents stable Edge channels, exclusive user-data directories, and unsupported concurrent profile use. Current source confirms bundled Chromium launch, Windows extension inference, divergent profile defaults, no status tool, and a visible lifespan-owned page.

The pilot confirms browser/session availability through the owned page, not B2's structured classification. Device policy can change. First-use trust, consent, MFA, or profile sign-in can require operator interaction. The authenticated disposable pilot profile is not a durable artifact and must be removed outside the agent write boundary.

## Success And Proof

Automated proof covers platform mode resolution, explicit Chromium override, fixed profile custody, Edge channel/sandbox arguments, distinct startup reason codes, fail-closed startup, status projection, agent grant, and maintained cleanup behavior. A bounded managed-device procedure proves visible first-use interaction, authenticated session availability for SharePoint and Jira, restart persistence, absence of the rejected launch warning, and owned shutdown without retaining page content or session files.

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

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-confirmed architecture and managed-Mac pilot
statement: On macOS, Browser MCP selects stable Microsoft Edge with one fixed per-user OwlBear-owned persistent profile and never reads, copies, or controls the operator's daily Edge profile.
```

```yaml target-contract
kind: commitment
id: COM-002
class: dealbreaker
provenance: user-confirmed fail-closed policy
statement: Missing Edge, invalid mode, unusable Edge, or profile contention produces bounded unavailable state and never silently substitutes Chromium for the managed authentication path.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: user-confirmed onboarding and security boundary
statement: B1 first-use sign-in, site trust, consent, or MFA occurs directly in the visible lifespan-owned Edge window without B1 sending session material through an agent or MCP tool.
```

```yaml target-contract
kind: commitment
id: COM-004
class: important-reviewed
provenance: source-grounded trust semantics
statement: Browser readiness describes configured mechanics and process state, while authenticated success remains evidence for one target acquisition at one time and never becomes a universal authenticated claim.
```

```yaml target-contract
kind: commitment
id: COM-005
class: protected-request
provenance: user-confirmed compatibility boundary
statement: Bundled Chromium remains explicitly selectable and non-macOS defaults remain unchanged; CDP attachment and daily-profile reuse are excluded from this Change.
```

```yaml target-contract
kind: commitment
id: COM-006
class: agreed-path
provenance: observed pilot and existing package ownership
statement: Managed Edge uses supported sandbox configuration, integrates with the maintained exception-safe cleanup boundary, and is accepted through deterministic tests plus a bounded managed-device pilot.
```

No admission approval has been requested.
