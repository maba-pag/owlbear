---
id: 929
title: 'P2-03: GREEN — App shell implementation'
status: archived
priority: important
created: 2026-04-17T19:57:46.937827+00:00
updated: 2026-04-18T13:25:27.997534+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 927
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement the cockpit app shell layout and routing to pass RED tests from #927.

## Acceptance Criteria

- [ ] CSS Grid layout with 5 regions per O4b: status-bar (top), nav-rail (left ~56px), workspace (center), sidecar (right ~360px), contextual (reserved, empty)
- [ ] React Router (or equivalent) with `/` (kanban surface) and extensible route registration
- [ ] Nav rail with icon-based surface selectors; kanban icon active by default
- [ ] Status bar with traffic-light placeholder and task count placeholders (wired to live data in board task)
- [ ] Sidecar container with tab switching: Detail / Activity tabs
- [ ] Hello-world `/hello` route proves O4a extensibility (no shell layout changes needed)
- [ ] All PDS tokens used; no hand-rolled colour hex outside `tokens.css`
- [ ] All RED tests from #927 pass

## Files

- `serve/cockpit/web/src/Shell.tsx`
- `serve/cockpit/web/src/components/NavRail.tsx`
- `serve/cockpit/web/src/components/StatusBar.tsx`
- `serve/cockpit/web/src/components/Sidecar.tsx`
- `serve/cockpit/web/src/Shell.css` (or CSS module)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/929-app-shell-green.md
- Sources: 9 studied, 7 high-relevance
- Recommendation: Straightforward GREEN — CSS Grid with named areas (56px / 1fr / 360px), extract 3 components using Pattern A (Shell owns regions), BrowserRouter in main.tsx. All 14 RED tests already pass; implementation adds visual layout + component structure + PDS token usage. (confidence: 0.90)
- Follow-up tasks created: none (AC is self-contained)
- Decision requests: none
[[2026-04-18]]

## Architecture Review

### AC Refinements Applied

1. **AC line 2 clarified:** "extensible route registration" → added specificity: extensibility proven by `/hello` route requiring no shell layout changes (already captured in AC 6, cross-referenced).
2. **AC line added:** `App.test.tsx` must be updated to reflect Shell integration (PHeading assertions replaced).
3. **Builder guidance added:** AC lines 1, 3, 7 (CSS Grid layout, PDS tokens, pixel widths) are reviewer-enforced — JSDOM cannot compute CSS layout. Reviewer must verify these during code review.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One feature: app shell layout + routing. CSS, extraction, and wiring are coupled parts of the same shell. |
| Interface clarity | PASS | 5 data-regions define the DOM contract. Tests specify exact attributes. Routes defined by path. |
| Dependency correctness | PASS | Depends on #927 (RED tests) — archived/done. react-router ^7.14.1 in package.json. |
| Module layering | PASS | Frontend-only, no backend deps. Shell.tsx → components/ is a clean extraction. |
| TDD compliance | PASS | #927 is the preceding RED phase with 14 tests. |
| KISS/YAGNI | PASS | Minimal: Grid + 3 components + Router wiring. No speculative features. |
| Premise challenge | PASS | App shell is a fundamental UI structure with no existing equivalent. |
| Pattern consistency | PASS | PDS components (p-tabs), React Router, CSS custom properties from tokens.css. |
| Security surface | PASS | No system boundaries, no user input, pure layout. |
| Single domain | PASS | All cockpit/frontend domain. |

### Failure Mode Map

N/A — pure UI layout with no failure-prone codepaths.

### Challenge Results

- Challenger: **reconsider** (confidence: 0.60)
- Key concerns: (C2) App.test.tsx breakage not in AC; (A3) "extensible route registration" vague; (C1) tests already pass before GREEN work
- Architect response: **revised** — added AC for App.test.tsx update, clarified extensibility meaning. Rebutted C1 (normal GREEN pattern — tests define DOM contract, CSS/visual AC is reviewer-enforced). Rebutted A2 split proposal (tightly coupled changes must land together). Rebutted B2 responsive (out of scope for D14 spec).

### Builder Notes

- `App.test.tsx` will break when App renders Shell — update assertions to match Shell content
- Pattern A (Shell owns region wrappers) or Pattern B (component owns root element) — builder's choice, tests are pattern-agnostic
- `Shell.css` import should go in `Shell.tsx` (co-located convention)
- `contextual` region: `display: none` is acceptable for reserved/empty state
- AC lines 1, 3, 7 are reviewer-enforced (JSDOM cannot verify CSS layout or token-only colors)

### Verdict: APPROVE

### Action Taken: Advanced to todo with AC clarifications and builder guidance in end_work note

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/cockpit/web/src/App.test.tsx`
- Classes: `TestFromAC_AppShellIntegration`
- Tests per category: happy 5, edge 0, error 0, boundary 0
- Total: 5 tests, all FAIL ✓
- lint: clean (TypeScript, no ruff scope)
- Commit: `test: replace App PHeading assertions with Shell integration tests (#929, test-writer)`

### AC Coverage

| AC | Test |
|----|------|
| CSS Grid 5 regions | 5 tests: status-bar, nav-rail, workspace, sidecar, contextual all queried via `[data-region="..."]` on `render(<App />)` — fail because App still renders PHeading, not Shell |
| App.test.tsx updated (architect AC) | All 5 PHeading assertions replaced with Shell region assertions |

### Context

- Shell.test.tsx (17 tests) already exists and **passes** — these test Shell in isolation and were the #927 RED deliverable. Not duplicated.
- New tests verify App.tsx renders Shell as its tree (BrowserRouter + Shell integration) — the architect-added AC not covered by Shell's own tests.
- All 5 new tests fail with `expected null not to be null` — App currently renders `<PHeading>OwlBear Cockpit</PHeading>` with no `data-region` attributes.
[[2026-04-18]]

## Builder Notes

### Files Changed

- `serve/cockpit/web/src/App.tsx` — replaced PHeading with BrowserRouter + Shell (PorscheDesignSystemProvider kept as outer wrapper)
- `serve/cockpit/web/src/Shell.tsx` — added `Shell.css` import; added CSS class names (`shell`, `shell__status-bar`, etc.) to all regions
- `serve/cockpit/web/src/Shell.css` (new) — CSS Grid with named areas: `status-bar` full-width top, `nav-rail` 56px left, `workspace` 1fr center, `sidecar` 360px right, `contextual` hidden (display:none); all colours use PDS tokens from tokens.css

### Test Results

- App.test.tsx: 5/5 passed (was 5 FAIL — verified RED before fix)
- Shell.test.tsx: 17/17 passed (unchanged — was already GREEN)
- Total: 22 passed, 0 failed
- Build: tsc -b + vite build clean (134 modules, no TS errors)

### Lint / TypeScript

- TypeScript: clean (tsc -b passes)
- No ruff scope (frontend-only task)

### Evidence

- RED verified: 5 `expected null not to be null` failures in App.test.tsx before change
- GREEN: `npm test` → 22 passed after App.tsx update
- Commit: `feat: integrate Shell into App with BrowserRouter and CSS Grid layout (#929, builder)` [dev 25856606]

### AC Coverage

| AC | Status |
|----|--------|
| CSS Grid 5 regions (status-bar/nav-rail/workspace/sidecar/contextual) | Shell.css grid-template-areas; reviewer-enforced |
| BrowserRouter + extensible routes | App.tsx wraps Shell in BrowserRouter; /hello route in Shell |
| Nav rail with kanban active default | data-surface="kanban" aria-current="page" |
| Status bar traffic-light + task-count | data-testid attrs present |
| Sidecar Detail/Activity tabs | p-tabs with p-tabs-item labels |
| PDS tokens only, no hand-rolled hex | Shell.css uses var(--pds-theme-light-*) throughout |
| All 5 App.test.tsx RED tests pass | 5/5 GREEN ✓ |
[[2026-04-18]]

## Review Evidence

### Test Results

- App.test.tsx: 5 passed, 0 failed (vitest, independently verified)
- Shell.test.tsx: 17 passed, 0 failed (vitest, independently verified — file is at `src/__tests__/Shell.test.tsx`, not `src/Shell.test.tsx`)
- Total: 22 passed, 0 failed
- tsc: clean (exit 0)

### Lint: clean (TypeScript; no ruff scope)

### Coverage: n/a (frontend, no coverage tooling in scope)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: CSS Grid 5 regions | Shell.test.tsx CSS Grid group (5 tests); App.test.tsx (5 tests) | YES — `[data-region="..."]` selectors return null | COVERED |
| AC2: React Router `/` + extensibility | Shell.test.tsx Routing:3 tests | YES | COVERED |
| AC3: Nav rail icon-based selectors; kanban active default | Shell.test.tsx Nav rail:2 tests (`[data-surface][aria-current="page"]`) | PARTIAL — active state covered; icon requirement absent | **LAX** |
| AC4: Status bar placeholders | Shell.test.tsx Status bar:2 tests (data-testid traffic-light, task-count) | YES | COVERED |
| AC5: Sidecar tab switching | Shell.test.tsx Sidecar tabs:5 tests (incl. tabChange CustomEvent) | YES | COVERED |
| AC6: /hello extensibility + layout intact | Shell.test.tsx Routing:2,3 | YES | COVERED |
| AC7: PDS tokens only, no hand-rolled hex | Reviewer-enforced (code read) | N/A — code confirmed | COVERED |
| AC8: All RED tests from #927 pass | 17 Shell tests intact and passing | YES | COVERED |

**LAX AC3 — No compensating TestBuilderDiscovered test.** Shell.tsx L28: `<button data-surface="kanban" aria-current="page">Kanban</button>` — text label only, no `<svg>`, `<img>`, or `<p-icon>` present. AC3 explicitly says "icon-based surface selectors." The test queries for `[data-surface="kanban"][aria-current="page"]` and passes for a text-only button. A text-only nav rail satisfies the test but violates the AC.

#### Security Review

- Hardcoded secrets: None.
- Injection: Shell.tsx L13 — `CustomEvent<{activeTabIndex: number}>.detail.activeTabIndex` consumed only to compute boolean for `aria-hidden`. No user input reaches innerHTML or external sink.
- Shell.tsx L44,47 — `el?.setAttribute('label', 'Detail'/'Activity')` sets hardcoded string literals; no user input involved.
- No new dependencies introduced.
- No issues found.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 17 Shell.test.tsx tests (from #927 RED) | Read directly; all 17 present with original assertions | PRESERVED |
| `switching to Activity tab` (Shell.test.tsx:118) | CustomEvent fireEvent + both aria-hidden checks | PRESERVED |
| `kanban surface selector active` (Shell.test.tsx:53) | `[data-surface="kanban"][aria-current="page"]` | PRESERVED |

No WEAKENED or REMOVED tests.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | `.not.toBeNull()`, `.toContain()`, exact `aria-hidden` string checks |
| Negative/error-path coverage | WEAK | No test for unmatched route, invalid tabIndex, missing regions |
| Mutation resilience | ADEQUATE | Removing any `data-region` attribute breaks corresponding test; removing `aria-current` breaks nav-rail test |
| Test independence | STRONG | `renderShell()` called fresh per test; no shared mutable state |
| Descriptive names | STRONG | All test names self-describing |

WEAK dimension: no test for unmatched routes or edge inputs. However this is informational-only (low-severity UI shell concern) and does NOT auto-fail on its own. The determinative WEAK finding is on AC3 coverage above.

#### Data Safety

- Shell.tsx manages only `aria-hidden` string values via DOM refs. No LLM output, no persisted state, no multi-step ops.
- No issues found.

#### Implementation-Aware Gaps

1. **MEANINGFUL — AC3 icon absence.** Shell.tsx:28 `<button data-surface="kanban" aria-current="page">Kanban</button>` — AC3 explicitly requires "icon-based surface selectors." The nav rail button contains only the text "Kanban"; no icon element (p-icon, svg, img) is present. No test exercises this path. A mutation removing icons entirely would not be caught.
2. **INFORMATIONAL — One-directional tab-switch test only.** Shell.test.tsx fires `activeTabIndex: 1` (Detail→Activity) and checks both `aria-hidden` values. No test fires `activeTabIndex: 0` after switching. A mutation swapping `index !== 0` / `index !== 1` in the detail/activity branches would not be caught.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- **Shell.css grid row mismatch:** `grid-template-areas` defines 3 rows; `grid-template-rows: auto 1fr` defines only 2. The third row receives an implicit `auto` height from `grid-auto-rows`. `nav-rail`, `workspace`, `sidecar` span rows 2–3 (both are the same areas), resulting in effective height of `1fr + auto`. Valid CSS but consider `grid-template-rows: auto 1fr auto` or collapsing to 2 rows for explicit intent.
- **Shell.tsx ref callbacks recreated per render:** `ref={(el: HTMLElement | null) => el?.setAttribute('label', '...')}` at L44,47 creates new function references on each render, causing React to re-run the callback (null → element) each cycle. Harmless for label-setting but `useCallback` or a stable ref pattern avoids churn.
- **Shell() function length:** ~53 lines including JSX, marginally above the 50-line guidance. The `useEffect` tab-switching block (lines 6–20) could become `useTabVisibility(tabsRef, detailRef, activityRef)` if Shell grows.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: CSS Grid 5 regions | Shell.css:1–11 `grid-template-areas` defines all 5 regions; columns: 56px / 1fr / 360px; Shell.tsx `data-region` on all 5 elements | Shell.test.tsx CSS Grid 5 tests | PASS |
| AC2: React Router `/` + extensible | App.tsx wraps Shell in `<BrowserRouter>`; Shell.tsx `<Routes>` with `/` and `/hello` | Shell.test.tsx Routing:3 | PASS |
| AC3: Nav rail icon-based, kanban active | Shell.tsx:27–30 — button has `data-surface="kanban" aria-current="page"` but **no icon element** | Shell.test.tsx nav-rail:2 (does not test icons) | **FAIL** |
| AC4: Status bar placeholders | Shell.tsx:24–25 `<span data-testid="traffic-light"/>`, `<span data-testid="task-count"/>` | Shell.test.tsx status-bar:2 | PASS |
| AC5: Sidecar tab switching | Shell.tsx:36–51 `<p-tabs>` with 2 `<p-tabs-item>` + `tabChange` useEffect | Shell.test.tsx Sidecar tabs:5 | PASS |
| AC6: /hello extensibility | Shell.tsx:34 `<Route path="/hello" element={<div>hello</div>}/>` ; all 5 regions preserved on /hello route | Shell.test.tsx Routing:2,3 | PASS |
| AC7: PDS tokens only | Shell.css — all color values are `var(--pds-theme-light-*)` ; no hex, rgb(), hsl() present; size fallbacks (8px, 16px) are non-color | Reviewer-enforced (code read) | PASS |
| AC8: RED tests from #927 pass | Shell.test.tsx 17/17 passed independently | Shell.test.tsx all 17 | PASS |

### Confidence: .68

### Verdict: FAIL

**Failing criteria:**

- **Step 5.0 AC3 LAX (no compensating test):** The "icon-based surface selectors" portion of AC3 has no test that would fail if icons are absent. The only test checks `[data-surface="kanban"][aria-current="page"]` which passes for a text-only button.
- **Step 5.5 Implementation Gap:** Shell.tsx:28 — nav rail button contains only text "Kanban"; AC3 requires icon-based selectors. The AC line is not met.

**Action required (builder):**

1. Add an icon element to the kanban nav-rail button (e.g., `<p-icon name="dashboard" aria-hidden="true" />` or equivalent PDS icon, inside the `<button data-surface="kanban">` element in Shell.tsx).
2. Update Shell.test.tsx to add an assertion verifying icon presence inside the nav-rail button (e.g., `expect(navRail?.querySelector('[data-surface="kanban"] p-icon, [data-surface="kanban"] svg')).not.toBeNull()`).
3. No other changes needed — all other AC lines are met.
[[2026-04-18]]

## Builder Notes (Review Fix)

### Files Changed

- `serve/cockpit/web/src/Shell.tsx` — added `<p-icon name="list" aria-hidden="true" />` inside the kanban nav-rail button
- `serve/cockpit/web/src/__tests__/Shell.test.tsx` — added `TestBuilderDiscovered` test: "kanban nav-rail button contains an icon element (p-icon or svg)"
- `serve/cockpit/web/src/vite-env.d.ts` — added `'p-icon'` type declaration to IntrinsicElements

### RED → GREEN

- TestBuilderDiscovered test added first → verified 1 FAIL (`expected null not to be null`) → fixed Shell.tsx → 18 Shell tests pass

### Test Results

- Shell.test.tsx: 18/18 passed (17 original + 1 TestBuilderDiscovered)
- App.test.tsx: 5/5 passed
- Total: 23 passed, 0 failed

### Lint / TypeScript

- TypeScript: clean (tsc --noEmit, exit 0)
- No ruff scope (frontend-only)

### AC Coverage

| AC | Status |
|----|--------|
| AC3: icon-based surface selectors | p-icon in kanban button; TestBuilderDiscovered test covers it |
| All other AC lines | Unchanged — already passing |

### Commit

`fix: add p-icon to nav-rail kanban button; TestBuilderDiscovered icon test (#929, builder)` [dev 7ba43d23]
[[2026-04-18]]

## Review Evidence (Pass 2)

### Test Results

- Shell.test.tsx: 18 passed, 0 failed (17 TestFromAC_AppShell + 1 TestBuilderDiscovered — independently verified)
- App.test.tsx: 5 passed, 0 failed (TestFromAC_AppShellIntegration — independently verified)
- Total: 23 passed, 0 failed

### Lint: clean (TypeScript; no ruff scope)

### Coverage: n/a (frontend, no coverage tooling in scope)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: CSS Grid 5 regions | Shell.test.tsx CSS Grid group (5 tests); App.test.tsx (5 tests) | YES — `[data-region="…"]` selectors return null | COVERED |
| AC2: React Router `/` + extensible | Shell.test.tsx Routing:3 tests | YES | COVERED |
| AC3: Nav rail icon-based; kanban active | Shell.test.tsx Nav rail:2 tests + TestBuilderDiscovered (icon query) | YES — `querySelector('p-icon, svg')` returns null if icon removed | COVERED |
| AC4: Status bar placeholders | Shell.test.tsx Status bar:2 tests | YES | COVERED |
| AC5: Sidecar tab switching | Shell.test.tsx Sidecar tabs:5 tests | YES | COVERED |
| AC6: /hello extensibility + layout intact | Shell.test.tsx Routing:2,3 | YES | COVERED |
| AC7: PDS tokens only, no hand-rolled hex | Reviewer-enforced (code read) — Shell.css confirmed all color values are `var(--pds-theme-light-*)` | N/A | COVERED |
| AC8: All RED tests from #927 pass | 17 Shell tests + 5 App tests intact and passing | YES | COVERED |

**AC3 fix confirmed:** Shell.tsx:29 `<p-icon name="list" aria-hidden="true" />` inside `<button data-surface="kanban" aria-current="page">`. TestBuilderDiscovered queries `kanbanBtn?.querySelector('p-icon, svg')` — would fail on removal. Prior cycle's determinative finding resolved.

#### Security Review

- Hardcoded secrets: None.
- p-icon attribute `name="list"` is a hardcoded PDS icon name — no user input involved.
- tabChange handler: `CustomEvent<{activeTabIndex: number}>.detail.activeTabIndex` consumed only for boolean `aria-hidden` string — no sink risk.
- ref callbacks: `el?.setAttribute('label', 'Detail'/'Activity')` — hardcoded string literals only.
- No new external dependencies introduced.
- No issues found.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 17 TestFromAC_AppShell tests (Shell.test.tsx) | Read directly; all 17 present with original assertions | PRESERVED |
| All 5 TestFromAC_AppShellIntegration tests (App.test.tsx) | Read directly; all 5 present and unchanged | PRESERVED |
| TestBuilderDiscovered (new) | Added: `querySelector('p-icon, svg')` on kanban button | ADDED (strengthens coverage) |

No WEAKENED or REMOVED tests.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | `.not.toBeNull()`, `.toContain()`, exact `aria-hidden` string checks |
| Negative/error-path coverage | N/A | Pure UI layout — no error paths or defensive code exist; moot dimension |
| Mutation resilience | ADEQUATE | Removing any `data-region`, `aria-current`, or `p-icon` breaks corresponding test |
| Test independence | STRONG | `renderShell()` called fresh per test; no shared mutable state |
| Descriptive names | STRONG | All test names self-describing |

#### Data Safety

- No persisted state, no LLM output, no multi-step ops, no shared mutable state.
- No issues found.

#### Implementation-Aware Gaps

- None remaining. Prior cycle's AC3 implementation gap (icon absent) resolved.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 (original build + targeted review fix) |
| Approach variation | Yes — fix was targeted and minimal |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL (carried from prior cycle, no new items)

- **Shell.css grid row mismatch:** `grid-template-areas` defines 3 rows; `grid-template-rows: auto 1fr` covers 2. Third row is implicit `auto`. Valid CSS; nav-rail/workspace/sidecar effectively span `1fr + auto` combined.
- **Ref callbacks recreated per render:** `ref={(el) => el?.setAttribute('label', '...')}` creates new function per render. Harmless for label-setting.
- **One-directional tab-switch test:** `activeTabIndex: 1` direction only; no test for `0` after switching. Low-impact mutation gap for a symmetric boolean handler.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: CSS Grid 5 regions | Shell.css:1–11 `grid-template-areas` defines all 5; columns 56px/1fr/360px; Shell.tsx `data-region` on all 5 elements | Shell.test.tsx CSS Grid 5 tests | PASS |
| AC2: React Router `/` + extensible | App.tsx:4 `<BrowserRouter>`; Shell.tsx:33-37 `<Routes>` with `/` and `/hello` | Shell.test.tsx Routing:3 | PASS |
| AC3: Nav rail icon-based, kanban active | Shell.tsx:28-31 `<button data-surface="kanban" aria-current="page"><p-icon name="list" aria-hidden="true" />Kanban</button>` | TestBuilderDiscovered | PASS |
| AC4: Status bar placeholders | Shell.tsx:24-25 `data-testid="traffic-light"` and `data-testid="task-count"` | Shell.test.tsx status-bar:2 | PASS |
| AC5: Sidecar tab switching | Shell.tsx:40-51 `<p-tabs>` + `tabChange` useEffect | Shell.test.tsx Sidecar tabs:5 | PASS |
| AC6: /hello extensibility | Shell.tsx:36 `/hello` route; all 5 regions preserved on `/hello` | Shell.test.tsx Routing:2,3 | PASS |
| AC7: PDS tokens only | Shell.css — all color values `var(--pds-theme-light-*)`; no hex/rgb/hsl present | Reviewer-enforced (code read) | PASS |
| AC8: RED tests from #927 pass | Shell.test.tsx 17 original tests + TestBuilderDiscovered pass; App.test.tsx 5/5 pass | All 23 passing | PASS |

### Deductions

- (-0.03) CSS grid row mismatch (implicit third row) — informational
- (-0.02) Ref callbacks recreated per render — minor pattern concern
- (-0.02) One-directional tab-switch test only — low-impact mutation gap

### Confidence: .93

### Verdict: PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Frontend-only (Shell.tsx, App.tsx, Shell.css). copilot-instructions.md tech stack table already accurate (React 19, Vite 6, TypeScript, Porsche DS 3.34.0, React Router 7). No convention changes. |
| 2 | Module docstrings | No | N/A | No Python files changed. TypeScript/CSS task only. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains "App Shell GREEN Phase (Task #929)" section with 2 React Router v7 source entries added during research phase. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/929-app-shell-green.md` exists and linked from task body. Follow-ups: none (AC self-contained). |

### Files Updated

- None

### Scratch Files Cleaned

- None found (no `.owlbear/scratch/929-*` files present)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: CSS Grid 5 regions | Shell.css grid-template-areas with 5 named areas; Shell.tsx 5 `data-region` elements; columns 56px/1fr/360px | PASS |
| AC2: React Router + extensible routes | App.tsx `<BrowserRouter>` wrapping Shell; Shell.tsx `<Routes>` with `/` and `/hello` | PASS |
| AC3: Nav rail icon-based, kanban active | Shell.tsx `<p-icon name="list" aria-hidden="true" />` inside `<button data-surface="kanban" aria-current="page">`; TestBuilderDiscovered covers icon presence | PASS |
| AC4: Status bar placeholders | Shell.tsx `data-testid="traffic-light"` and `data-testid="task-count"` spans; Shell.test.tsx status-bar:2 tests | PASS |
| AC5: Sidecar tab switching | Shell.tsx `<p-tabs>` + `tabChange` useEffect; Shell.test.tsx Sidecar tabs:5 tests | PASS |
| AC6: /hello extensibility | Shell.tsx `/hello` route, 5 regions preserved; Shell.test.tsx Routing:2,3 | PASS |
| AC7: PDS tokens only | Shell.css — all color values `var(--pds-theme-light-*)`; no hex/rgb/hsl found (spot-checked) | PASS |
| AC8: RED tests from #927 pass | Shell.test.tsx 18 tests (17 original + 1 TestBuilderDiscovered) + App.test.tsx 5 tests = 23 passing | PASS |

### Test Results

- Python (pytest): 557 passed, 6 failed (all knowledge domain — pre-existing, not task scope), lint clean
- Frontend (vitest): 23 passed, 0 failed (reviewer-verified x2, builder-verified; no independent auditor run — quality-runner covers Python only)
- tsc: clean (builder + reviewer verified)

### Architect Quality: 4/5

Specific AC (8 lines). Challenge process caught 3 concerns and produced AC revisions. AC3 was precise enough to catch missing icons during review. Minor gaps: "Files" section listed unneeded component files; "extensible route registration" required clarification.

### Deduction Breakdown

- No AC line without evidence: 0
- Lint clean: 0
- AC quality >3: 0
- Reviewer evidence present and detailed: 0
- Full-suite test failures in task scope: 0
- Frontend vitest not independently run by auditor (quality-runner Python-only): -.02

### Confidence: .98

### Action: archive
