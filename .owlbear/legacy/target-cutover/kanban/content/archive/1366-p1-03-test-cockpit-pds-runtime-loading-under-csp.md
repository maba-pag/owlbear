---
id: 1366
title: 'P1-03: Test Cockpit PDS runtime loading under CSP'
status: archived
priority: medium
created: 2026-05-06T00:58:33.557890+00:00
updated: 2026-05-06T16:19:05.079524+00:00
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
claimed_at:
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
[[2026-05-06]]
## Review Evidence
### Test Results
- quality-runner (scoped) executed Playwright successfully against `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`.
- Playwright: 0 passed, 5 failed. Failures were functional, not infrastructure: `customElements.get('p-button')` was `undefined`, and the remaining tests timed out waiting for `[data-region="workspace"]` to become visible.
- This RED result matches the task contract for a `type:test` task whose purpose is to write failing runtime proof and whose builder guidance explicitly says the tests are expected to fail until counterpart task #1367 lands.
- Lint: clean (`serve/cockpit/web/e2e/pds-runtime-csp.spec.ts`).
- Coverage: N/A for Playwright E2E on this test-only task; no production module changes are in scope.

### Sequential Fallback
- `code-reader` subagent returned an execution error (`Sorry, no response was returned` / service disruption).
- Per review workflow fallback, I completed direct file inspection of the task-owned spec and the exercised frontend files instead.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — after `[data-region="workspace"]` is visible, `customElements.get()` returns defined constructors for `p-button`, `p-icon`, `p-tabs`, `p-tabs-item`; all `/api/*` + SSE stubbed | Spec stubs catch-all `/api/**`, `/api/events`, `/api/tasks`, `/api/board` at `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:63-80`; waits for workspace visibility at `:91`; exact element registration assertions at `:96-109`. Shell directly renders the named elements at `serve/cockpit/web/src/Shell.tsx:137-149`. Live RED evidence from quality-runner: `p-button` undefined, remaining registration checks blocked on workspace visibility. | `TestFromAC_PDSCustomElementsRegistered` | PASS |
| AC2 — listen for `securitypolicyviolation` during shell load and fail on Porsche CDN blockedURIs | Collector installed before navigation via `page.addInitScript()` at `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:120-130`; exact origin filters + zero-length assertions at `:134-158`. CSP source of truth is build-time `script-src 'self'` in `serve/cockpit/web/vite.config.ts:8-20`. | `TestFromAC_NoCDNCSPViolations` | PASS |
| AC3 — at least one Shell-rendered PDS element has non-empty `shadowRoot` after stabilization | Test waits for `p-button`, then converts missing/null/empty shadow roots to failing numeric sentinels at `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts:174-187`. Shell renders the `PButton`/`p-icon` nav entry at `serve/cockpit/web/src/Shell.tsx:137-140`. | `TestFromAC_PDSShadowRootActivation` | PASS |

### Test Quality Assessment
- Assertion specificity: STRONG. Assertions are exact (`toBe(true)`, `toHaveLength(0)`, `toBeGreaterThan(0)`) rather than presence-only checks.
- Negative/error-path coverage: ADEQUATE for a RED-phase smoke-proof task. The suite is intentionally written to fail on the current snapshot; AC2 also covers both Porsche CDN origins separately.
- Manual mutation reasoning: STRONG. If the app stopped stubbing APIs, stopped registering one named element, stopped collecting CSP violations, or rendered a null/empty shadowRoot, at least one mapped assertion would fail.
- Test independence: STRONG. Each describe block re-establishes stubs and navigation in `beforeEach`.
- Test names: STRONG. Test names are descriptive and AC-traceable.

### Test Integrity
- No direct evidence of weakened or removed `TestFromAC_*` assertions in the live file. Current classes and test count match the Test-Writer Notes.
- I could not perform a commit-diff immutability check from `8ba02911` with the available tool surface, so this carries a small confidence deduction only.

### Deductions
- `-0.03` `code-reader` execution error required manual fallback.
- `-0.02` TestFromAC immutability could not be proven via commit diff; assessed from live file vs task notes instead.

### Verdict
- PASS
- Confidence: 0.95
- Action: advance to docs.

### Post-task Reflection
- Builder note claiming Playwright was unsupported by quality-runner is stale or incorrect; reviewer execution produced valid Playwright evidence.
- For `type:test` tasks with explicit RED authority and a backlog counterpart build task, failing live tests can still be PASS review evidence when the assertions are AC-complete and discriminating.
- Playwright E2E coverage is not a meaningful gate for this task shape; assertion quality and executable RED evidence are the real proof surface.
[[2026-05-06]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task adds one E2E test file only; no behavior, API, CLI, config, or package structure change. No IN-scope docs reference E2E test internals. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Test follows internal templates (e2e/smoke.spec.ts, e2e/kanban-board.spec.ts); no external patterns imported. |
| 4 | Research doc | No | N/A | No research doc produced or referenced in task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | `cockpit.excalidraw` describes `serve/cockpit/web/src/**`; changed file is `serve/cockpit/web/e2e/pds-runtime-csp.spec.ts` (e2e/, not src/). No glob match. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/e2e/pds-runtime-csp.spec.ts | OUT | N/A — E2E test file, not IN-scope doc |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1366-* scratch files found)

No docs impact — all checklist items N/A. Task-only change: new Playwright E2E spec in e2e/ directory. Advancing to done.
[[2026-05-06]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: customElements.get() defined for p-button, p-icon, p-tabs, p-tabs-item; all /api/* stubbed | spec.ts:63-80 (stubs), :91 (workspace wait), :96-109 (assertions). Commit 8ba02911. | PASS |
| AC2: no securitypolicyviolation from Porsche CDN origins | spec.ts:120-130 (addInitScript collector), :134-158 (origin filter + toHaveLength(0)) | PASS |
| AC3: p-button has non-empty shadowRoot | spec.ts:174-187 (querySelector + shadowRoot.childElementCount > 0) | PASS |

### Test Results
- vitest: 992 passed, 0 failed (full frontend suite)
- eslint: 0 violations on task file
- pytest: 2783 passed, 174 failed (all failures in unrelated tasks: 1268, 1266, 1176, 1244, 1195 etc. Task 1366 adds only a .ts file with no Python changes)
- ruff: 12 violations in serve/knowledge/ and serve/tools/ (not in task scope)
- Playwright RED evidence: 5 expected failures confirmed by reviewer execution (correct for type:test RED phase)

### Upstream Commit
- 8ba02911 test: add PDS runtime CSP smoke tests (#1366, test-writer)

### Architect Quality: 5/5
Specific, complete, clean implementation path. Challenger raised 4 findings, architect accepted all and refined AC from vague to mechanically testable criteria. Excellent upstream work.

### Deduction Breakdown
- AC lines without evidence: 0 (all 3 verified)
- Lint violations in scope: 0
- AC quality: 5/5 (no deduction)
- Reviewer evidence: present, detailed, PASS
- Full-suite failures in scope: 0
- Total deductions: 0

### Confidence: 0.98
(conservative -0.02 for relying on reviewer Playwright execution rather than independent re-run; structural file verification confirms test content matches claims)

### Action: archive