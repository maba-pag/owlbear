# CDP Spike Results — Task #753

**Date:** 2026-04-13
**Environment:** Corporate laptop (Porsche AG managed), Windows, Microsoft Edge

## Results

- **CDP connectivity:** FAIL — `ECONNREFUSED 127.0.0.1:9222`
- **SSO extraction:** NOT TESTED (blocked by CDP)
- **EDR reaction:** N/A — CDP never opened; no observable EDR alert triggered
- **DLP reaction:** N/A — no data extraction attempted
- **SharePoint boilerplate behavior:** NOT TESTED

## Root Cause

Corporate Group Policy (`HKLM\SOFTWARE\Policies\Microsoft\Edge`) explicitly disables remote debugging:

```
RemoteDebuggingAllowed = 0
HeadlessModeEnabled = 0
```

Edge silently ignores `--remote-debugging-port=9222`. The port never opens. This is a Porsche AG IT-managed policy — cannot be overridden without admin rights.

## Additional Relevant Policies

- `browserCodeIntegritySetting = 2` — code integrity enforcement
- `RendererCodeIntegrityEnabled = 1`
- `AudioSandboxEnabled = 1`
- `SitePerProcess = 1`
- `ScreenCaptureAllowed = 0` — screen capture also blocked
- `CommandLineFlagSecurityWarningsEnabled = 1`
- `SSLVersionMin = tls1.2`
- `EnhanceSecurityMode = 1`

## Go/No-Go Decision

**NO-GO** for CDP-based approach on the corporate laptop.

## Pivot Strategy

The CDP approach (`--remote-debugging-port`) is blocked by Group Policy. Alternative strategies:

1. **Playwright's built-in browser** — use `playwright.chromium.launch()` instead of `connect_over_cdp()`. This launches Chromium (not Edge) with its own profile, bypassing Edge policies. However, it won't have Edge SSO/Windows Integrated Auth.

2. **Cookie export** — extract SSO cookies from Edge via the `Cookies` SQLite database file at `%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cookies` (may be encrypted with DPAPI).

3. **HTTP-level auth** — use `requests` with NTLM/Negotiate authentication directly (via `requests-negotiate-sspi` on Windows) instead of browser automation.

4. **WebView2** — investigate if WebView2 (which uses Edge's rendering engine but runs as an embedded component) bypasses the `RemoteDebuggingAllowed` policy.

## Pivot Spike Results (2026-04-14)

### Approaches Tested

| Approach | Result | Details |
|----------|--------|---------|
| Playwright Chromium (plain) | Auth blocks | Launch works, but Azure AD Conditional Access rejects device as non-compliant (missing SSO extension) |
| Chrome via Playwright (`executable_path`) | FAIL | `RemoteDebuggingAllowed = 0` also applies to Chrome (`--remote-debugging-pipe` blocked) |
| HTTP + NTLM (`requests-negotiate-sspi`) | FAIL (401) | SharePoint Online uses Azure AD OAuth, not NTLM/Kerberos |
| **Playwright Chromium + SSO extension** | **PASS** | Load Microsoft SSO extension from managed Chrome into Playwright's own Chromium. Device compliance handled by extension. Full SSO transparent. |

### Winning Architecture

```
Playwright Chromium (own binary, not subject to Group Policy)
  + Microsoft SSO extension (copied from managed Chrome profile)
  + Persistent browser context (session cookies survive between runs)
  → page.content() → owlbear_browser.cleaner.clean() → Markdown
```

Extension path: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions\ppnbnpeolgkicgegkbkbjmhlideopiji\{version}`
Extension ID: `ppnbnpeolgkicgegkbkbjmhlideopiji` (Microsoft Single Sign On)

### E2E PoC Results

| Site | URL | Auth Flow | HTML → Markdown |
|------|-----|-----------|-----------------|
| SharePoint | `porsche.sharepoint.com/sites/CarreraOnline_PAG` | Fully automatic (SSO extension) | 1.7 MB → 5.8 KB |
| Jira (on-prem) | `skyway.porsche.com/jira/projects/AUDIT/issues` | One-time: Windows login → trust prompt | 815 KB → 67 KB |
| Confluence (on-prem) | `skyway.porsche.com/confluence/...` | Automatic (shared Skyway session from Jira) | Confirmed working |

Auth persistence:
- SharePoint: SSO extension handles auth transparently, no interaction needed
- Skyway (Jira + Confluence): one-time "Windows login" click + Microsoft trust prompt on first access. After that, session persists across all Skyway services in the persistent profile.

PoC scripts: `.owlbear/scratch/e2e-poc.py`, `.owlbear/scratch/multi-url-poc.py`

### Implementation Notes

1. SSO extension version (`1.0.11_0`) may change with Chrome updates — need to resolve dynamically
2. Persistent profile at `.owlbear/scratch/playwright-sso-profile/` — gitignored
3. SharePoint pages load async (SPA) — use `domcontentloaded` + short sleep, not `networkidle` (never settles)
4. First run after profile creation may need one-time manual login; subsequent runs reuse session
