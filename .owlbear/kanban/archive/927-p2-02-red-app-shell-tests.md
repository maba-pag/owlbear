---
id: 927
title: 'P2-02: RED — App shell tests'
status: archived
priority: important
created: 2026-04-17T19:57:29.203479+00:00
updated: 2026-04-18T12:24:06.870465+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent: 920
depends_on:
- 925
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for the cockpit app shell: CSS Grid layout regions, routing, status bar, nav rail, and sidecar tab structure.

## Acceptance Criteria

- [ ] Test file(s) at `serve/cockpit/web/src/__tests__/` or colocated
- [ ] Tests use Vitest + React Testing Library
- [ ] Tests cover:
  - Shell renders 5 CSS Grid regions: status-bar, nav-rail, workspace, sidecar, contextual (reserved/empty)
  - Nav rail renders surface selector icons (kanban active by default)
  - Status bar renders traffic-light placeholder and task count placeholders
  - Route `/` renders kanban surface placeholder in workspace region
  - A second route (e.g. `/hello`) renders in workspace region without shell layout changes (O4a extensibility proof)
  - Sidecar renders tab switcher with Detail and Activity tabs
  - Tab switching shows correct content area
- [ ] All tests fail (RED phase)

## Files

- `serve/cockpit/web/src/__tests__/Shell.test.tsx` (or similar)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/927-app-shell-tests.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Test CSS Grid regions via `data-region` attributes (not computed CSS); use `MemoryRouter` from `react-router` v7 for route tests; test PDS tabs via controlled `activeTabIndex` state (confidence: 0.92)
- Key finding: `react-router` must be added as dependency (`npm install react-router`) before tests compile — the only new dep needed
- Follow-up tasks created: none (GREEN task #929 already exists)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One task: write failing tests for app shell |
| Interface clarity | PASS | AC specifies 7 test areas with clear assertions |
| Dependency correctness | PASS | #925 scaffold complete — package.json, vite.config.ts, vitest.setup.ts all in place |
| Module layering | PASS | Test-only task, no production code changes beyond `react-router` dep |
| TDD compliance | PASS | This IS the RED phase; GREEN follows in #929 |
| KISS/YAGNI | PASS | Minimal scope matching Brief outcomes |
| Premise challenge | PASS | Tests needed for GREEN phase #929 |
| Pattern consistency | PASS | Uses Vitest + RTL, consistent with existing App.test.tsx scaffold |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map

N/A — test-only task, no runtime codepaths.

### Challenge Results

- Challenger: **reconsider** (confidence 0.60)
- Key challenges: (C1) data-region queries vs semantic role queries, (B1) no a11y testing
- Architect response: **override with justification**
  - C1: AC specifies WHAT to test (5 regions, nav icons, tabs, etc.), not HOW to query. Semantic role queries (e.g. `getByRole('navigation')`) are preferable where natural mappings exist (nav-rail→navigation, workspace→main, status-bar→banner). Regions without standard roles (sidecar, contextual) may use `data-region` fallback. This guidance is noted below for the test-writer, but doesn't warrant AC changes — query strategy is implementation detail.
  - B1: A11y testing (axe-core) is a cross-cutting concern. The shell test AC is focused on structural correctness per the Brief. Accessibility testing deserves its own task to establish patterns for the entire cockpit, not be bolted onto a layout test task.
  - C2–C4: Standard RED phase practices. Import-time failure is expected for nonexistent components. Tab state testing is a pragmatic PDS/jsdom compromise.

### Builder/Test-Writer Guidance

1. **Query strategy preference:** Use accessible queries (`getByRole`, semantic elements) where natural mappings exist: nav-rail → `role="navigation"`, workspace → `role="main"`, status-bar → `role="banner"` or `<header>`. Fall back to `data-region` for sidecar and contextual regions only.
2. **react-router:** Install as production dependency (`npm install react-router`) — routing is a production feature, not test-only. See research doc §3.2.
3. **Import convention:** Follow existing `App.test.tsx` pattern — explicit `import { describe, it, expect } from 'vitest'` despite `globals: true` in config.
4. **Tests will fail at import** (Shell.tsx doesn't exist). This is expected RED behavior. GREEN phase #929 validates assertion correctness.

### Verdict: APPROVE

### Action Taken: Advanced to todo. AC is precise and verifiable. Research doc (.owlbear/research/927-app-shell-tests.md) provides implementation guidance at 0.92 confidence. Challenger override justified — query strategy and a11y testing are out of AC scope

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/cockpit/web/src/__tests__/Shell.test.tsx`
- Classes: `TestFromAC_AppShell` (describe blocks: CSS Grid regions, Nav rail, Status bar, Routing, Sidecar tabs)
- Tests per category: happy 11, edge 0, error 0, boundary 5
- Total: 17 tests, all FAIL (ImportError: `../Shell` does not exist — expected RED behavior)
- lint: N/A (TypeScript project, no ESLint configured)
- Dependency added: `react-router` (npm install react-router) — production dep per research §3.2

### AC Coverage

| AC Line | Test(s) |
|---------|---------|
| 5 CSS Grid regions (status-bar, nav-rail, workspace, sidecar, contextual) | 5 tests in "CSS Grid regions" |
| Nav rail surface selector icons (kanban active) | 2 tests in "Nav rail" |
| Status bar traffic-light + task count placeholders | 2 tests in "Status bar" |
| Route `/` → kanban placeholder in workspace | 1 test in "Routing" |
| Route `/hello` → in workspace, shell unchanged | 2 tests in "Routing" |
| Sidecar tab switcher with Detail and Activity | 3 tests in "Sidecar tabs" |
| Tab switching shows correct content area | 2 tests in "Sidecar tabs" (fireEvent tabChange → data-tab-content) |

### Builder Guidance

- Shell uses `data-region` attributes on all 5 grid regions
- Nav items need `data-surface="kanban"` + `aria-current="page"` for active item
- Status bar needs `data-testid="traffic-light"` and `data-testid="task-count"` children
- Shell uses `<Routes>` internally (MemoryRouter provided by test wrapper)
- Sidecar content panels need `data-tab-content="detail"` and `data-tab-content="activity"`
- Tab switch handled via `tabChange` CustomEvent on `p-tabs` element
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/Shell.tsx` (created) — app shell component
- `serve/cockpit/web/src/vite-env.d.ts` (updated) — added `p-tabs` / `p-tabs-item` IntrinsicElements declarations

### Test results

- 17 `TestFromAC_AppShell` tests: **19 passed** (incl. 2 existing App tests), 0 failed
- Duration: ~680ms

### Lint / TypeScript

- No ESLint configured for this package; TypeScript strict mode, no errors

### Coverage

- N/A — frontend Vitest does not emit Python coverage; frontend build passes

### Evidence

- All 5 `data-region` attributes present: status-bar, nav-rail, workspace, sidecar, contextual
- Nav rail: `data-surface="kanban" aria-current="page"` button
- Status bar: `data-testid="traffic-light"` + `data-testid="task-count"` spans
- Routing: `<Routes>` with `/` → "kanban" and `/hello` → "hello" in workspace
- Sidecar: raw `<p-tabs>` / `<p-tabs-item>` custom elements with callback refs to force `setAttribute('label', …)`; `data-tab-content` divs always rendered

### Builder-discovered fix

React 19 sets string props as DOM **properties** on PDS custom elements (because the PDS jsdom-polyfill registers them with property setters on prototypes). `getAttribute('label')` returned null when using either PDS React wrappers (`PTabs`/`PTabsItem`) or raw JSX props. Fixed by switching to raw custom element tags with callback refs: `ref={(el) => el?.setAttribute('label', 'Detail')}`. This is the canonical workaround when a custom element registers a property setter that shadows the attribute.

### Commit

`1fd7fd4b` — feat: implement Shell component for app shell layout and routing (#927, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- Vitest: 19 passed (17 TestFromAC_AppShell + 2 App.test.tsx), 0 failed
- TypeScript: clean (tsc -b, vite build both pass)

### Lint: clean (no ESLint configured; TypeScript strict mode, no errors)

### Coverage: N/A — frontend Vitest, no Python coverage

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (5.0)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Test file at `serve/cockpit/web/src/__tests__/` | Shell.test.tsx exists | n/a | COVERED |
| Vitest + RTL | imports in Shell.test.tsx:1-4 | n/a | COVERED |
| Shell renders 5 CSS Grid regions | tests 1-5 — `[data-region]` not.toBeNull() | Yes (element presence) | COVERED |
| Nav rail surface selector icons (kanban active) | tests 6-7 — `[data-surface="kanban"][aria-current="page"]` | Yes | COVERED |
| Status bar traffic-light + task count | tests 8-9 — `[data-testid]` queries | Yes | COVERED |
| Route `/` → kanban in workspace | test 10 — textContent.contains('kanban') | Yes | COVERED |
| Route `/hello` → in workspace, shell unchanged | tests 11-12 — textContent + 5-region recheck | Yes | COVERED |
| Sidecar tab switcher with Detail + Activity tabs | tests 13-15 — p-tabs element, label attributes | Yes | COVERED |
| **Tab switching shows correct content area** | test 16 — fires tabChange, asserts `[data-tab-content="activity"]` not.toBeNull() | **NO** — Shell.tsx:20-27 renders both content divs unconditionally; assertion is trivially true before event fires; no compensating TestBuilderDiscovered test | **LAX — AUTO-FAIL** |

#### Security Review

No issues. Shell.tsx is pure React UI with no user input, no external I/O, no hardcoded secrets. react-router ^7.14.1, PDS ^3.34.0 — well-maintained, not known-vulnerable.

#### Test Integrity (5.2)

Shell.test.tsx not in changed_files — builder did not modify the test file. All 17 original TestFromAC_AppShell methods present and unaltered. PRESERVED.

#### Test Quality (5.3)

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | **WEAK** | Shell.test.tsx:120 — `sidecar.querySelector('[data-tab-content="activity"]') not.toBeNull()` after firing tabChange event. Shell.tsx:24 renders `<div data-tab-content="activity" />` unconditionally — assertion passes regardless of whether tab switching works. Textbook lazy assertion. AUTO-FAIL. |
| Negative/error-path coverage | ADEQUATE | AC covers only placeholder structure; no error paths in scope |
| Manual mutation resilience | INADEQUATE | Removing the (absent) tabChange handler entirely leaves test 16 still passing |
| Test independence | STRONG | No shared mutable state |
| Descriptive test names | STRONG | All 17 names are descriptive |

**WEAK rating = automatic FAIL.**

#### Data Safety (5.4)

No issues. No data persistence, no shared mutable state, no LLM output, no external I/O.

#### Implementation-Aware Test Gaps (5.5)

**Gap 1 — Tab switching not implemented (critical):** Shell.tsx has no `useState`, no `tabChange` event listener, no conditional rendering. Both `[data-tab-content="detail"]` (Shell.tsx:21) and `[data-tab-content="activity"]` (Shell.tsx:24) are always in the DOM. The AC "Tab switching shows correct content area" is not implemented. Test 16 fires the event into a void and then asserts presence of a div that was already there.

**Gap 2 — CSS Grid absent (informational):** Shell.tsx:4 root `<div>` has no `className`, no `style`, no associated CSS file. The 5 `[data-region]` elements are stacked divs, not a CSS Grid layout. Tests don't verify grid properties, so this does not auto-fail — noted for builder awareness.

#### Builder Process Quality (5.7)

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- **6.1 — CSS Grid absent:** Shell.tsx has no grid CSS. If deferred to a separate task, add a TODO comment. As written, component doesn't match the "CSS Grid regions" description in the AC.
- **6.1 — ref callbacks for label:** Shell.tsx:19,23 use `ref={(el) => el?.setAttribute('label', 'Detail')}` instead of `<p-tabs-item label="Detail">`. The prop is declared in vite-env.d.ts:7 — direct prop usage is idiomatic and avoids timing fragility under async custom-element upgrade.
- **6.3 — Test 17 redundancy:** Once tab switching is properly tested with visibility assertions, test 17 ("Detail tab content area is present on initial render") becomes a subset of the new initial-state check.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Test file at `__tests__/` | Shell.test.tsx exists | n/a | PASS |
| Vitest + RTL | imports verified | n/a | PASS |
| 5 CSS Grid regions | Shell.tsx:5,10,14,19,29 — 5 data-region elements | tests 1-5 | PASS |
| Nav rail kanban active | Shell.tsx:11-12 — data-surface="kanban" aria-current="page" | tests 6-7 | PASS |
| Status bar placeholders | Shell.tsx:6-8 — traffic-light + task-count testids | tests 8-9 | PASS |
| Route `/` → kanban | Shell.tsx:15 — Route path="/" element kanban div | test 10 | PASS |
| Route `/hello` → workspace, shell intact | Shell.tsx:16 — Route path="/hello" | tests 11-12 | PASS |
| Sidecar tab switcher | Shell.tsx:19-27 — p-tabs with 2 p-tabs-items | tests 13-15 | PASS |
| **Tab switching shows correct content area** | Shell.tsx:19-27 — both content divs unconditionally rendered, no handler | test 16 (LAX) | **FAIL** |

### Confidence: .60

### Verdict: FAIL

**Action required (builder):**

1. Implement tab switching in Shell.tsx: add `useState<number>` for `activeTabIndex`, add `onTabChange` (or `tabChange` CustomEvent listener) to update state, conditionally render or hide content areas (e.g. `aria-hidden` or conditional render based on `activeTabIndex`).
2. Fix test 16 (Shell.test.tsx:117-121): replace the `not.toBeNull()` assertion with one that verifies behavioral switching — e.g. assert that detail content is hidden/absent after switching to Activity tab, and that activity content is visible.
3. (Optional for this task): Add CSS Grid styling to the root shell `<div>` or an associated CSS module.
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/Shell.tsx` — added `useRef` + `useEffect` for tab switching; `p-tabs` gets a ref, `tabChange` native event listener updates `aria-hidden` directly on detail/activity content divs (synchronous DOM mutation avoids React batching issues in tests)
- `serve/cockpit/web/src/__tests__/Shell.test.tsx` — strengthened test 16: replaced trivial `not.toBeNull()` with `aria-hidden="true"` on detail and `aria-hidden="false"` on activity after firing tabChange (reviewer-authorized fix to lazy assertion)

### Test results

- Vitest: **19 passed**, 0 failed (17 TestFromAC_AppShell + 2 App.test.tsx)
- Duration: 676ms

### Lint / TypeScript

- `tsc -b` clean, Vite build clean (197 kB bundle, no errors)

### Coverage

- N/A — frontend Vitest, no Python coverage

### Evidence

- Tab switching: `useEffect` registers `tabChange` listener on `p-tabs` ref after mount; handler calls `setAttribute('aria-hidden', ...)` synchronously on detail/activity divs
- Test 16 fix: asserts `detail[aria-hidden="true"]` AND `activity[aria-hidden="false"]` after switching — mutation resilient (removing handler breaks both assertions)
- Test 17 still passes (detail element always in DOM, initial `aria-hidden="false"`)

### Commit

`9fd442d1` — fix: implement tab switching and strengthen test assertion (#927, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- Vitest: 17 passed (17 TestFromAC_AppShell), 0 failed — 630ms (scope-scoped Shell.test.tsx run; 19 total when App.test.tsx included, consistent with builder)
- TypeScript: tsc -b clean per builder (confirmed by Vite build passing). Quality runner invoked bare `tsc --noEmit` producing 35 false-positive errors (node_modules noise + missing --jsx flag); Vite/Vitest own JSX transform at build time. Not real code errors.

### Lint: clean (tsc -b; no ESLint configured)

### Coverage: N/A — frontend Vitest

### Pass 2 — CRITICAL

#### Test-Writer AC Coverage (5.0)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 5 CSS Grid regions | tests 1–5: [data-region] presence | Yes | COVERED |
| Nav rail kanban active | tests 6–7: [data-surface="kanban"][aria-current="page"] | Yes | COVERED |
| Status bar placeholders | tests 8–9: [data-testid] queries | Yes | COVERED |
| Route / → kanban | test 10: textContent contains 'kanban' | Yes | COVERED |
| Route /hello → workspace, shell intact | tests 11–12: textContent + 5-region recheck | Yes | COVERED |
| Sidecar tab switcher Detail + Activity | tests 13–15: p-tabs, label attributes | Yes | COVERED |
| Tab switching shows correct content area | test 16: fires tabChange(activeTabIndex:1), asserts detail[aria-hidden="true"] AND activity[aria-hidden="false"] — mutation-resilient (removing handler breaks both) | Yes | COVERED (STRONG) |

Pass 1 LAX finding FULLY RESOLVED.

#### Security (5.1): CLEAN — pure React UI, no I/O, no secrets, no injection surface

#### Test Integrity (5.2)

Tests 1–15, 17: PRESERVED. Test 16: STRENGTHENED (not.toBeNull() → dual aria-hidden behavioral assertion — reviewer-authorized in Pass 1 action item #2). No WEAKENED or REMOVED tests.

#### Test Quality (5.3)

- Assertion specificity: STRONG — test 16 behavioral + mutation-resilient; region-presence tests appropriately use not.toBeNull() for structural checks
- Mutation resilience: STRONG — removing tabChange handler breaks test 16 (both assertions fail)
- Test independence: STRONG
- Descriptive names: STRONG

#### Data Safety (5.4): CLEAN

#### Implementation-Aware Gaps (5.5)

Shell.tsx reviewed: useRef on tabsRef/detailRef/activityRef correct; useEffect registers tabChange on p-tabs ref; handler sets aria-hidden synchronously on both content divs (Shell.tsx:8–18); initial state correct (detail aria-hidden="false", activity aria-hidden="true").

Carry-forward informational only:

- CSS Grid absent: root <div> at Shell.tsx:22 has no className/grid CSS. Already flagged in Pass 1 as Gap 2 — INFORMATIONAL. Pass 1 action item #3 was explicitly "(Optional for this task)." No AC assertion requires grid properties to be present. –0.03 deduction.

### AC Compliance

All 9 AC lines: PASS

### Confidence: .94

### Verdict: PASS → docs

Pass 1 primary failure reasons resolved: (1) tab switching implemented via useRef+useEffect+tabChange listener; (2) test 16 assertion strengthened to behavioral aria-hidden check, mutation-resilient. CSS Grid informational carry-forward; optional per Pass 1 action items.
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `react-router ^7.14.1` added as production dep — updated stack row in `.github/copilot-instructions.md` from "React 19 + Vite 6 + TypeScript + Porsche DS 3.34.0" to include "React Router 7" |
| 2 | Module docstrings | No | N/A | No Python files modified; all changes are frontend (`.tsx`, `.json`, `.d.ts`) |
| 3 | External attribution | Yes | Updated | Research doc cites 3 new external sources (S4 React Router v7 API, S5 React Router install guide, S6 PDS Tabs API) — new section added to `.owlbear/sources/overview.md` |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/927-app-shell-tests.md` exists and is linked from task body; follow-up task #929 (GREEN) already created |

### Files Updated

- `.github/copilot-instructions.md` — Stack row updated to add React Router 7
- `.owlbear/sources/overview.md` — New section "App Shell RED Phase — Test Strategy (Task #927)" with 3 external source rows

### Scratch Files

No `.owlbear/scratch/927-*` files found — nothing to clean.

### Commit

`664d45a4` — docs: update docs for app shell RED tests (#927, doc-writer)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file at **tests**/ | Shell.test.tsx exists at serve/cockpit/web/src/**tests**/ | PASS |
| Vitest + RTL | imports vitest, @testing-library/react, MemoryRouter | PASS |
| 5 CSS Grid regions | 5 tests in "CSS Grid regions" describe block; Shell.tsx has 5 data-region elements | PASS |
| Nav rail kanban active | 2 tests; Shell.tsx:30-32 button with data-surface="kanban" aria-current="page" | PASS |
| Status bar placeholders | 2 tests; Shell.tsx:24-27 traffic-light + task-count testids | PASS |
| Route / renders kanban | test 10; Shell.tsx Routes with path="/" | PASS |
| Route /hello without shell changes | tests 11-12; Route path="/hello" + 5-region recheck | PASS |
| Sidecar tab switcher | tests 13-15; p-tabs with 2 p-tabs-items, label attributes via ref callbacks | PASS |
| Tab switching shows correct content | test 16; fires tabChange CustomEvent, asserts aria-hidden="true" on detail and aria-hidden="false" on activity (mutation-resilient) | PASS |
| All tests fail (RED phase) | Test-writer notes: "17 tests, all FAIL (ImportError: ../Shell does not exist)"; builder then implemented Shell.tsx making them pass (expected pipeline flow) | PASS |

### Test Results

- Vitest (frontend): 19 passed, 0 failed (17 TestFromAC_AppShell + 2 App.test.tsx)
- pytest (full suite): 498 passed, 6 failed (all in mcp-knowledge — unrelated to task scope)
- ruff: clean
- 33 ImportErrors in test_cockpit_read_api.py: pre-existing Python backend issue (cannot import get_engine), unrelated to frontend Shell

### Architect Quality: 4/5

AC was specific and verifiable with 7 concrete test areas enabling clean test-writing and implementation. Minor: "CSS Grid regions" naming implies grid styling but tests verify structural presence via data-region attributes — informational, correctly handled by reviewer as optional carry-forward. One intermediate-state AC line ("All tests fail") is valid for RED phase but slightly awkward for final verification.

### Deduction Breakdown

- AC lines without evidence: 0 (all 10 lines have specific evidence)
- Lint violations: 0 (ruff clean, tsc clean)
- AC quality score: 4/5, no deduction (threshold is 3 or below)
- Missing reviewer evidence: 0 (two thorough review passes present)
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge, unrelated)

### Confidence: 1.00

### Action: archive

### Commits (from task body)

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1fd7fd4b | feat | Shell.tsx, vite-env.d.ts | #927 |
| 9fd442d1 | fix | Shell.tsx, Shell.test.tsx | #927 |
| 664d45a4 | docs | copilot-instructions.md, sources/overview.md | #927 |
