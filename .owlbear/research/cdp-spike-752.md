# Edge CDP Validation Spike — Research

> **Owning task:** #752 — P0-01: Write Edge CDP validation spike script
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

Phase 0 go/no-go gate for the Authenticated Content Pipeline (#751). Can a script launch
Edge with `--remote-debugging-port=9222`, connect via Playwright CDP, navigate to an
SSO-protected SharePoint page, and extract cleaned text? What blockers exist?

## 2. Sources Studied

| # | Source | URL/Location | Relevance |
|---|--------|-------------|-----------|
| 1 | Playwright `connect_over_cdp` API | playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp | .95 |
| 2 | Chrome 136 remote-debugging-port security change | developer.chrome.com/blog/remote-debugging-port | .95 |
| 3 | Playwright `launch_persistent_context` API | playwright.dev/python/docs/api/class-browsertype#browser-type-launch-persistent-context | .85 |
| 4 | Playwright Chrome Extensions docs | playwright.dev/python/docs/chrome-extensions | .70 |
| 5 | Prior research #264 (browser automation) | .owlbear/research/browser-automation.md | .90 |
| 6 | Prior research #495 (CDP context isolation) | .owlbear/research/cdp-context-isolation.md | .85 |
| 7 | Prior research #684 (Playwright v2 integration) | .owlbear/research/playwright-browser-integration-v2.md | .85 |
| 8 | Brief security voice (#751) | .owlbear/briefs/draft-browser-knowledge-extraction/voices/security.md | .90 |

## 3. Analysis

### 3.1 Critical Finding: Chrome 136 `--remote-debugging-port` Restriction

From Chrome 136 (March 2025), `--remote-debugging-port` and `--remote-debugging-pipe`
**no longer work with the default Chrome/Edge data directory** [2]. The flag now requires
`--user-data-dir` pointing to a non-standard directory. Without it, the flag is silently
ignored. Edge versions track Chromium — Edge 136+ is deployed.

**Impact on CDP-SSO approach:**

| Scenario | SSO cookies available? | CDP works? | Outcome |
|----------|----------------------|------------|---------|
| Default profile, no `--user-data-dir` | Yes (in profile) | No (flag ignored) | **Blocked** |
| Custom `--user-data-dir` (fresh) | No (empty profile) | Yes | No SSO |
| Custom `--user-data-dir` + Windows Integrated Auth | Auto-negotiated | Yes | **May work** |

**Windows Integrated Auth (Kerberos/NTLM)** is the key variable. Corporate environments
using Entra ID with Windows Hello + conditional access often negotiate auth at the OS
level — independent of browser cookies. If the corporate SSO stack uses this, a fresh
Edge profile with `--user-data-dir` and `--remote-debugging-port` will still authenticate
to SharePoint automatically. The spike must test this empirically.

### 3.2 Spike Script Approach Comparison

| Criterion | A: Manual launch + `connect_over_cdp` | B: `launch_persistent_context` |
|-----------|--------------------------------------|--------------------------------|
| Edge lifecycle control | Full (find → launch → probe → connect) | Playwright-managed |
| `--user-data-dir` handling | Explicit subprocess arg | Playwright's `user_data_dir` param |
| CDP port binding | Explicit `--remote-debugging-port=9222` | Internal (no exposed port) |
| Error diagnosis | High — each step logged independently | Lower — Playwright abstracts launch |
| SSO session reuse | Via default context `browser.contexts[0]` | Via persistent context (same profile) |
| v1 precedent | Matches v1 launcher pattern | Different from v1 |
| Code complexity | ~120 LOC | ~60 LOC |
| Diagnostic value | **High** — tests every assumption | Medium — only tests the combined path |

**Recommendation: Approach A (manual launch + connect)** for the spike. The purpose is to
diagnose which steps work and which fail. Approach B abstracts away the very things we
need to test. If A succeeds, B can be used for production simplification later.

### 3.3 Spike Script Design

```
Step 1: Find Edge — check standard paths, log version
Step 2: Check port 9222 — detect if already in use
Step 3: Launch Edge — subprocess with:
  --remote-debugging-port=9222
  --user-data-dir=.owlbear/scratch/cdp-spike-profile
  (fresh profile to comply with Chrome 136)
Step 4: Poll CDP endpoint — GET http://127.0.0.1:9222/json/version
Step 5: Connect — playwright.chromium.connect_over_cdp(
  "http://127.0.0.1:9222", is_local=True)
Step 6: Navigate — page.goto(TARGET_URL, wait_until="domcontentloaded")
Step 7: Detect SSO — check if URL redirected to IdP, check for login form
Step 8: Extract text — page.inner_text("body")
Step 9: Report — log: URL, title, text length, SSO status, timing
Step 10: Cleanup — disconnect, terminate Edge subprocess
```

### 3.4 Error Handling Matrix

| Error | Detection | Message |
|-------|-----------|---------|
| Edge not found | Path check fails | `Edge not found at standard paths. Install Edge or set EDGE_PATH.` |
| Port 9222 in use | Socket probe or HTTP GET succeeds before launch | `Port 9222 already in use. Close other Edge instances or CDP clients.` |
| CDP flag silently ignored | HTTP GET to 9222 times out after launch | `CDP endpoint not responding. Chrome 136+ may be blocking.` |
| Connection timeout | `connect_over_cdp` raises TimeoutError | `CDP connection failed within {N}s.` |
| SSO redirect | `page.url` differs from target, matches IdP pattern | `SSO redirect detected to {url}. Auth required.` |
| SSO login page (200) | Page contains password field or IdP-specific markers | `SSO login page returned (not auto-authenticated).` |
| Page load timeout | `page.goto` raises TimeoutError | `Page load timed out after {N}s for {url}.` |
| EDR/DLP intervention | Process terminated externally, or page blocked | `Edge process terminated unexpectedly. Check EDR logs.` |

### 3.5 EDR/DLP Observation

The spike cannot programmatically detect EDR/DLP alerts — these are monitored via
separate corporate tooling. The spike should:
1. Log timestamps for each step (for correlation with EDR event logs)
2. Print a clear "CHECK EDR/DLP" reminder after completion
3. Run for 5+ minutes to give EDR time to react before declaring success
4. The user should check Windows Event Viewer and any corporate security dashboard

### 3.6 Dependencies

| Dependency | Status | Installation |
|------------|--------|-------------|
| `playwright` | Not in v2 deps | `uv pip install playwright` |
| Playwright browser binaries | Not needed for CDP connect | Skip `playwright install` |
| Edge browser | Corporate-installed | Standard paths |

**Key insight:** `connect_over_cdp` does NOT require Playwright's bundled browser binaries [1].
It connects to the existing Edge installation. No `playwright install chromium` or
`playwright install msedge` needed. This makes the spike dependency-light.

## 4. Recommendation (.80 confidence)

Proceed with implementing the spike script using Approach A (manual launch + `connect_over_cdp`).
The Chrome 136 `--remote-debugging-port` restriction [2] is the primary risk — the spike
must use `--user-data-dir` with a fresh profile and test whether Windows Integrated Auth
provides SSO to SharePoint automatically.

If Windows Integrated Auth works: **GO** — the CDP approach is viable with a dedicated
profile. If it doesn't: the spike surfaces a **NO-GO** for cookie-based SSO reuse,
escalating to alternative approaches (SharePoint REST API, manual auth workflow).

Challenge: FALLBACK — spike validation has no controversial recommendation to challenge;
it's a binary empirical test.

## 5. Follow-up Tasks

1. Implement the spike script at `.owlbear/scratch/cdp-spike.py` per §3.3 design
2. Run the spike and document results (go/no-go determination for #751)
