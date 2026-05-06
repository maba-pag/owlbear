---
id: 1366
title: 'P1-03: Test Cockpit PDS runtime loading under CSP'
status: review
priority: critical
created: 2026-05-06T00:58:33.557890+00:00
updated: 2026-05-06T15:55:51.394127+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- design-system
- runtime
- csp
parent: 1363
depends_on:
- 1365
blocked: false
block_reason:
claimed_at: 2026-05-06T15:55:51.394127+00:00
archival_reason:
archival_refs: []
---

## Purpose
Write the failing runtime smoke proof that Cockpit loads Porsche Design System components in a CSP-compatible way.

## Problem Evidence
- The built Cockpit dist can load while Porsche Design System custom elements are not defined.
- Runtime currently relies on a Porsche CDN script that is blocked by script-src self.
- A visually usable Cockpit shell requires the intended PDS components to be registered without violating CSP.

## Acceptance Criteria
- Playwright E2E test verifies that after the shell renders `[data-region="workspace"]` visible, `customElements.get()` returns defined constructors for at least: `p-button`, `p-icon`, `p-tabs`, `p-tabs-item` (the PDS elements Shell.tsx directly renders). All app API routes (`/api/*`) and SSE (`/api/events`) must be stubbed via `page.route()` to isolate the proof from backend availability. (td:2)
- Playwright E2E test listens for the browser `securitypolicyviolation` event during shell load and fails if any violation fires with a `blockedURI` matching a Porsche CDN origin (`cdn.ui.porsche.com` or `cdn.ui.porsche.cn`). (td:2)
- Playwright E2E test asserts that at least one PDS custom element rendered by Shell (e.g., the `p-button` element) has a non-empty `shadowRoot` after the page stabilizes, proving the component's internal rendering activated — not just the tag existing as an undefined/empty element. (td:1)

## Scope
- In scope: Playwright E2E runtime loading and smoke verification for PDS custom elements under CSP.
- Out of scope: TypeScript build compatibility already covered by #1364/#1365, dashboard redesign, cache/SSE invalidation from #1346, and unit/jsdom tests (jsdom does not enforce CSP).
- Test file location: `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`

## Counterpart
Implementation task: #1367.

## Builder Guidance
- Use existing `e2e/smoke.spec.ts` and `playwright.config.ts` as structural templates.
- Stub ALL `/api/*` routes with minimal valid JSON responses (see `e2e/kanban-board.spec.ts` for pattern).
- For timing: use `page.waitForSelector('[data-region="workspace"]')` then evaluate `customElements.get('p-button')` in page context.
- For CSP detection: register a `securitypolicyviolation` listener via `page.addInitScript()` before navigation, collect violations into a page-level array, assert on it after load.
- These tests are expected to FAIL (RED phase) because PorscheDesignSystemProvider currently triggers CDN loading. Task #1367 will fix this.

[[2026-05-06]]

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: prove PDS runtime registration works under CSP |
| Interface clarity | PASS (after refinement) | AC refined to specify exact elements, detection method, and timing |
| Dependency correctness | PASS | #1365 archived (done). Dep satisfied. |
| Module layering | N/A | Test-only task, no production module changes |
| TDD compliance | PASS | This IS the test task; counterpart #1367 is the implementation |
| KISS/YAGNI | PASS | Minimal smoke proof scope, no extra features |
| Premise challenge | PASS | Real problem: PorscheDesignSystemProvider triggers CDN script via loader (confirmed in node_modules); CSP blocks it |
| Pattern consistency | PASS | Follows existing e2e/smoke.spec.ts pattern with Playwright |
| Security surface | PASS | Tests CSP enforcement — security-positive |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Architect response: ACCEPTED all four findings. Refined AC to: (1) enumerate Shell's actual PDS elements, (2) scope CSP detection to securitypolicyviolation event with all /api/* routes stubbed, (3) replace vague "styling signals" with shadowRoot existence proof, (4) add timing contract via componentsReady() or visible element wait.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE (with AC refinement)
### Action Taken: Rewrote AC to address challenger findings. Approved to todo.
[[2026-05-06]]
Architecture review complete. Refined all 3 AC lines from vague ("required PDS custom elements", "intended styling signals") to mechanically testable criteria with specific element names, detection methods, timing contracts, and isolation requirements. Challenger reconsider findings all accepted and incorporated. Approved to todo.
[[2026-05-06]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`
**Commit:** `8ba02911`

### Test Classes

| Class | Tests | Category |
|-------|-------|----------|
| `TestFromAC_PDSCustomElementsRegistered` | 2 | happy |
| `TestFromAC_NoCDNCSPViolations` | 2 | boundary |
| `TestFromAC_PDSShadowRootActivation` | 1 | happy |

**Total: 5 tests — all 5 FAIL ✅**

### RED Phase Evidence

```
5 failed
  [chromium] › TestFromAC_PDSCustomElementsRegistered › p-button custom element is defined after workspace renders
    AssertionError: Expected: true, Received: false
  [chromium] › TestFromAC_PDSCustomElementsRegistered › p-icon, p-tabs, and p-tabs-item are defined after workspace renders
    Timeout: locator('[data-region="workspace"]') never visible (CDN blocked → app fails to render)
  [chromium] › TestFromAC_NoCDNCSPViolations › no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.com
    Timeout: same cause
  [chromium] › TestFromAC_NoCDNCSPViolations › no securitypolicyviolation fires with blockedURI from cdn.ui.porsche.cn
    Timeout: same cause
  [chromium] › TestFromAC_PDSShadowRootActivation › p-button element has non-empty shadowRoot after page stabilizes
    Timeout: same cause
```

PDS provider triggers CDN loading at startup; the CSP `script-src 'self'` meta tag (injected by `cspPlugin` on build) blocks those requests, preventing the app from rendering. All failures are structurally caused by the same root problem task #1367 will fix.

### AC Coverage

| AC Line | Tests |
|---------|-------|
| AC1 — `customElements.get()` defined for p-button, p-icon, p-tabs, p-tabs-item after workspace visible | `test_p-button…`, `test_p-icon…` |
| AC2 — no `securitypolicyviolation` from Porsche CDN origins | `test_no…cdn.ui.porsche.com`, `test_no…cdn.ui.porsche.cn` |
| AC3 — p-button has non-empty `shadowRoot` | `test_p-button…shadowRoot` |

### Implementation Notes for Builder (#1367)

- API stubs cover all `/api/*` routes; backend not required to run these tests
- CSP violation collector uses `page.addInitScript()` so it fires before any page JS
- Tests use `page.locator('[data-region="workspace"]').waitFor({ state: 'visible' })` as timing contract
- `p-button` lookup uses `document.querySelector('p-button')` (rendered unconditionally in nav-rail)
[[2026-05-06]]
## Builder Notes
- No code changes applied.
- Attempted mandatory GREEN verification via quality-runner for `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`.
- quality-runner returned `TOOL_UNAVAILABLE` because it supports pytest/ruff and vitest/eslint, but not Playwright E2E.
- Per pipeline protocol tool-availability rule, task cannot be advanced from builder in this run.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Execute RED/GREEN verification with Playwright-capable runner (`npx playwright test e2e/pds-runtime-csp.spec.ts`) and continue implementation on counterpart runtime task if failures persist | serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | quality-runner result: `TOOL_UNAVAILABLE` (Playwright out of scope) |
| 2 | architect | Clarify routing between test task #1366 and implementation task #1367 so builder receives implementation scope tied to this failing E2E proof | serve/cockpit/web/src/App.tsx, serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | Task body indicates #1366 is test task with RED evidence; counterpart implementation listed as #1367 |