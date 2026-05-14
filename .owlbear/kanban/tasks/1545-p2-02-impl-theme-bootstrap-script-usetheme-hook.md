---
id: 1545
title: 'P2-02: impl — theme bootstrap script + useTheme hook'
status: todo
priority: needed
created: 2026-05-13T18:42:22.373573+00:00
updated: 2026-05-14T03:31:26.521142+00:00
tags:
  - phase-2
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1537
  - 1543
blocked: false
block_reason:
claimed_at: 2026-05-14T03:31:26.521142+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Synchronous bootstrap script in `index.html`, `useTheme` React hook, localStorage persistence, OS preference listener, `data-theme` DOM attribute management
- **Out:** Theme toggle UI button (separate task), PDS component compatibility verification (separate task)

## Acceptance Criteria

- AC-1: `public/theme-bootstrap.js` reads `localStorage.getItem('owlbear-theme')`, validates the value is in `['dark','light']`, falls back to `matchMedia('(prefers-color-scheme: dark)')` when absent or invalid, and sets `document.documentElement.dataset.theme` to the resolved value before React mount. `index.html` loads it via `<script src="/theme-bootstrap.js"></script>` as the first child of `<body>` (before `<div id="root">`) — not `type="module"`, not in `<head>`. Satisfies the `head-script-disabled` HTMLHint rule and the existing `script-src 'self'` CSP without relaxation.
- AC-2: `useTheme` hook returns `{ theme, toggle, isDark }` and manages `data-theme` DOM attribute without React Context. Hook consumers re-render on `toggle()` calls; non-consumer components restyle via CSS `[data-theme]` attribute selectors without React re-rendering. (Already implemented in #1537)
- AC-3: `useTheme().toggle` cycles light → dark → auto and persists explicit choices via `localStorage.setItem('owlbear-theme', …)`; `auto` removes the key; absent or invalid localStorage defaults to OS preference via `prefers-color-scheme`. (Already implemented in #1537)
- AC-4: When `theme === 'auto'`, `useTheme` registers a `matchMedia('(prefers-color-scheme: dark)')` change event listener via `addEventListener('change', …)` on a stable `MediaQueryList` reference. On change: updates `document.documentElement.dataset.theme` to match the new OS preference and triggers a state update so `isDark` reflects the new value. The listener is removed from the same `MediaQueryList` instance on unmount or when `theme` transitions away from `auto`. When `theme` is `'dark'` or `'light'`, no `matchMedia` listener is active.

Proof bundle: behavioral
2026-05-14T02:26:50+00:00
## Research
- Research doc: .owlbear/research/1545-theme-bootstrap-impl.md
- Sources: 6 studied, 4 high-relevance (Static Signal, dev.to gaisdav, next-themes script.ts, next-themes ThemeScript)
- Recommendation: Inline IIFE in `<head>` of `index.html` — ~10-line synchronous script reading localStorage + matchMedia + setting `data-theme` before paint (confidence: 0.90)
- Follow-up tasks created: none needed — existing decomposition under #1534 covers all downstream work
- Decision requests: none

### Key Findings
1. **AC-2 and AC-3 are already complete.** `useTheme` hook at `serve/cockpit/web/src/hooks/useTheme.ts` was implemented in dependency #1537 (archived, confidence 0.97). Exports `applyTheme()` and `useTheme()`, passing 15 tests.
2. **AC-1 requires a new file `public/theme-bootstrap.js` and a single edit to `index.html`.** The bootstrap file reads localStorage `owlbear-theme`, validates against `['dark','light']`, falls back to `matchMedia('(prefers-color-scheme: dark)')`, and sets `document.documentElement.dataset.theme`. The `index.html` loads it via `<script src="/theme-bootstrap.js"></script>` in `<head>`.
3. **`type="module"` scripts are always deferred** — calling `applyTheme()` from `main.tsx` cannot prevent FOUC. External synchronous script is the only viable approach.
4. **~10 LOC duplication is intentional and accepted industry-wide** — the bootstrap script is a frozen subset of `applyTheme()` logic. next-themes ships a separate `script.ts` for exactly this reason.
5. **CSP constraint (architect refinement):** The build injects `script-src 'self'` via `cspPlugin` in `vite.config.ts`. Inline `<script>` would be blocked in production. Using an external file in `public/` satisfies `'self'` with no CSP relaxation needed.

## Challenge Results
- Challenger: FALLBACK — trivial implementation with unanimous source consensus; no novel architectural decisions
- Confidence in original: 0.90
- Key findings: all 4 sources agree on inline blocking script in `<head>`; no alternatives viable
- Researcher response: N/A (no challenge needed)
2026-05-14T02:43:35+00:00
## Architecture Review (cycle 1)

**Verdict:** APPROVED (after REFINE)
**Proof bundle:** behavioral

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | REFINED — original specified inline `<script>` which conflicts with build-time `script-src 'self'` CSP policy from `cspPlugin` in `vite.config.ts`. Rewrote to use external file `public/theme-bootstrap.js` loaded via `<script src="/theme-bootstrap.js">`. Also added explicit localStorage key name `owlbear-theme` per B2. | Rewrote in task body |
| AC-2 | Precise after wording fix — removed misleading "zero re-renders" (hook consumer does re-render; non-consumers restyle via CSS selectors). Already implemented in #1537. | Tightened wording |
| AC-3 | Precise after wording fix — clarified `auto` removes key rather than "persists." Already implemented in #1537. | Tightened wording |

### Architecture Notes
- **Single responsibility:** Yes — theme bootstrap is tightly coupled to theme hook. One domain (cockpit frontend).
- **CSP compatibility (critical fix):** The `cspPlugin` in `vite.config.ts` injects `script-src 'self'` at build time. An inline `<script>` would be blocked in production. Refined AC-1 to use an external file in `public/` which satisfies `'self'` without CSP relaxation — aligned with brief security stance §3.
- **Duplication accepted:** ~10 LOC duplication between `theme-bootstrap.js` and `applyTheme()` is intentional — the bootstrap script is a frozen subset. Industry standard pattern (next-themes ships `script.ts`).
- **Module layering:** Frontend-only, no backend imports. No upward imports.
- **KISS/YAGNI:** Minimal — one small JS file + one `<script>` tag in HTML.

### Dependency Analysis
- #1537 (test task): archived/completed ✓ — 15 tests passing for `applyTheme()` and `useTheme()`
- #1543 (token architecture): archived/completed ✓ — CSS uses `[data-theme="dark"]` selectors
- Consolidation test #1554 exists with depends_on including #1545 ✓

### Challenger Results
- Confidence: 0.58 → reconsider
- Key concerns: CSP conflict (addressed by AC-1 rewrite to external file), AC wording precision (addressed), localStorage key naming (addressed)
- Architect response: All challenger findings accepted and incorporated. CSP was the real architectural issue — resolved by switching from inline to external script. AC wording tightened for downstream clarity. Override justified: all concerns addressed in the refined AC.
2026-05-14T02:50:26+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts
- Classes: TestFromAC_ThemeBootstrapFile_1545, TestFromAC_ThemeBootstrapBehavior_1545, TestFromAC_IndexHtmlBootstrap_1545
- Tests per category: happy 3, edge 2, error 4, boundary 1, html-wiring 3
- Total: 13 tests, all FAIL
- ruff: clean (frontend — ESLint clean)

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1: file exists in public/ | file-existence test → FAIL (ENOENT) |
| AC-1: reads localStorage 'dark'/'light', validates, sets data-theme | happy path × 2, error × 4, boundary × 1 → FAIL (ENOENT) |
| AC-1: falls back to matchMedia when absent/invalid | edge × 2 → FAIL (ENOENT) |
| AC-1: index.html loads via `<script src>` in `<head>`, not `type="module"` | html-wiring × 3 → FAIL (missing tag) |
| AC-2/AC-3: useTheme hook return shape and toggle cycle | Already covered by 15 passing tests in theme_1537.test.tsx — no new tests needed (would pass, not RED) |

### Notes
- AC-2 and AC-3 pre-exist from #1537 — any regression guards would immediately pass. Skipped per RED-phase rules.
- Bootstrap behavior tests fail with ENOENT (file not yet created by builder); index.html tests fail on missing script tag.
2026-05-14T03:01:11+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/public/theme-bootstrap.js`
  - `serve/cockpit/web/index.html`
- Implementation summary:
  - Added synchronous bootstrap script in `public/theme-bootstrap.js` to read `window.localStorage['owlbear-theme']`, validate `dark|light`, fall back to `window.matchMedia('(prefers-color-scheme: dark)')`, and set `window.document.documentElement.dataset.theme`.
  - Wired `<script src="/theme-bootstrap.js"></script>` in `<head>` of `index.html` before React mount.
  - Left AC-2/AC-3 hook behavior untouched (already implemented in #1537).
- RED verification (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`: 13 failed / 0 passed (expected, pre-implementation).
- GREEN verification (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`: 13 passed / 0 failed.
- Durable regression check (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`: 15 passed / 0 failed.
- Lint status:
  - Clean on task-scoped and durable scoped runs (ESLint clean).
- Coverage:
  - quality-runner reported no coverage metrics for these scoped frontend runs.
- Fixes applied during GREEN retry:
  - Initial script used bare globals (`localStorage`, `document`) which caused runtime/lint failures in the test harness.
  - Updated to explicit `window.localStorage` and `window.document` references; rerun passed.
- Commit:
  - `10842b67` — `feat: implement theme bootstrap script + index wiring (#1545, builder)`
2026-05-14T03:17:29+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1545 -> backlog | task contract conflicts with enforced HTML policy and leaves OS-preference listener behavior undefined/unproved.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The approved head-script implementation fails the enforced HTML quality gate. The current task contract requires `<script src="/theme-bootstrap.js"></script>` in `<head>`, but the shared Cockpit HTML policy forbids scripts in `<head>`, so the work cannot pass review as currently specified. | `serve/cockpit/web/index.html:6`; `serve/cockpit/web/.htmlhintrc:7`; `serve/cockpit/web/package.json:14`; `.mega-linter.yml:69-71`; independent quality-runner rerun: `htmlhint=1`, `head-script-disabled` at `index.html:6` | backlog |
| 2 | Scope / AC-2 / AC-3 | Upstream task scope and architecture still require an OS preference listener for auto theme, but the current hook only samples `matchMedia` synchronously and never registers a change listener. Existing tests stub listener APIs as no-ops and never prove live OS-theme updates. This is a contract/test-design gap, not just a builder retry. | `.owlbear/briefs/draft-board-visual-design/brief.md:36`; `.owlbear/briefs/draft-board-visual-design/stances/architect.md:102-103`; `serve/cockpit/web/src/hooks/useTheme.ts:14,45-57,74-76`; `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:15-19,108-154`; `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:20-24` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC-1 with the enforced HTMLHint/CI policy: either codify an allowed bootstrap-script exception or redesign the bootstrap approach so `lint:html` passes without implicit policy drift. | `serve/cockpit/web/index.html`, `serve/cockpit/web/.htmlhintrc`, `serve/cockpit/web/package.json`, `.mega-linter.yml` | quality-runner htmlhint failure `head-script-disabled` at `index.html:6`; `.htmlhintrc:7`; AC-1 requires head script |
| 2 | architect | Refine the theme contract so OS preference listening is either explicit, testable AC or removed from scope/brief; if retained, send the task back through RED/GREEN with listener proof. | `.owlbear/briefs/draft-board-visual-design/brief.md`, `.owlbear/briefs/draft-board-visual-design/stances/architect.md`, `serve/cockpit/web/src/hooks/useTheme.ts`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` | brief:36 and architect:102-103 require listener; hook has no listener registration; tests never assert it |

## Observations
- Independent quality-runner rerun resolved the missing builder coverage proof: 28 tests passed, 0 failed, and frontend coverage reported 93.18% for `useTheme.ts`.
- The current implementation does satisfy the refined storage/theme-resolution parts of AC-1: `serve/cockpit/web/public/theme-bootstrap.js:2-11` reads `owlbear-theme`, validates `dark|light`, falls back to `matchMedia`, and sets `documentElement.dataset.theme`; `serve/cockpit/web/index.html:6,11` wires the bootstrap script before React mount.
- `.owlbear/research/1545-theme-bootstrap-impl.md` still recommends inline head-script language even though the task AC was refined to an external public script; update that artifact when the contract is reconciled.
2026-05-14T03:30:52+00:00
## Architecture Review (cycle 2 — post-reviewer rejection)

**Verdict:** APPROVED (after REFINE)
**Proof bundle:** behavioral

### Reviewer Findings Addressed

| # | Reviewer Finding | Resolution |
|---|-----------------|------------|
| 1 | AC-1 head-script placement conflicts with `head-script-disabled` HTMLHint rule (`.htmlhintrc:7`, `.mega-linter.yml:69-71`, `package.json:14`) | Rewrote AC-1: script moves from `<head>` to first child of `<body>` (before `<div id="root">`). Synchronous scripts at `<body>` start block parsing/rendering — `data-theme` is set before any visible element paints. Satisfies `head-script-disabled` without lint config changes. |
| 2 | OS preference listener missing from AC and implementation; brief and architect stance require it | Added AC-4: explicit `matchMedia` change listener with same-instance cleanup, theme-gated activation, and `isDark` state update. Task must go through RED/GREEN for AC-4. |

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | REFINED — moved script placement from `<head>` to first child of `<body>`; removed unverifiable "preventing FOUC" claim (CSS `@media` fallback in `tokens.css:81` already handles the no-`data-theme` case); retained CSP and HTMLHint compliance as testable outcomes. B1: names `theme-bootstrap.js` and `index.html`. B2: storage read → validation → fallback → DOM mutation, all concrete. B3: clean. | Rewrote in task body |
| AC-2 | REFINED — clarified re-render scope: hook consumers DO re-render on toggle; non-consumers restyle via CSS only. Eliminates contradiction with new AC-4 listener behavior. Already implemented in #1537. B1/B2/B3: pass. | Tightened wording |
| AC-3 | Unchanged — precise as-is. Already implemented in #1537. | No action |
| AC-4 | NEW — closes brief gap. Specifies: `addEventListener('change', …)` on stable `MediaQueryList` reference; same-instance cleanup on unmount and theme transition; `isDark` state update; no listener when theme is explicit. B1: names `useTheme`. B2: `theme=auto` + OS change → DOM update + `isDark` update. B3: clean. | Added to task body |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Theme bootstrap + hook — one domain (cockpit frontend) |
| Interface clarity | PASS | `{ theme, toggle, isDark }` return shape; `data-theme` DOM contract |
| Dependency correctness | PASS | #1537 (hook impl), #1543 (tokens) — both archived/done |
| Module layering | PASS | Frontend-only, no backend imports |
| TDD compliance | PASS | Existing 13 tests need update (head→body); new tests for AC-4; test-writer processes next |
| KISS/YAGNI | PASS | One JS file + one HTML edit + one hook enhancement |
| Premise challenge | PASS | Bootstrap script necessary — `type="module"` always deferred, CSS `@media` doesn't cover stored manual preference |
| Pattern consistency | PASS | Follows existing hook patterns in `src/hooks/` |
| Security surface | PASS | `script-src 'self'` CSP satisfied by external `public/` file; no new input boundaries |
| Single domain | PASS | Cockpit frontend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Bootstrap: localStorage read | localStorage disabled/blocked | N/A (try/catch in IIFE) | Yes — falls back to matchMedia | None — auto theme applies |
| Bootstrap: matchMedia unavailable | Legacy browser/SSR | N/A | Partial — defaults to light | Acceptable degradation |
| Listener: OS theme change while `auto` | Race with user toggle | N/A | AC-4 specifies: listener removed on theme transition | No stale listener |
| Listener: component unmount | Leaked listener | N/A | AC-4 specifies: same-instance cleanup on unmount | No leak |
| Dual resolution: bootstrap vs hook | Different theme resolved | N/A | Both use same key + validation logic (~10 LOC frozen subset) | Accepted duplication |

### Architecture Notes
- **HTMLHint resolution:** Moving `<script>` from `<head>` to first `<body>` child is the simplest fix. The `head-script-disabled` rule targets `<head>` only. No lint config changes needed. Synchronous blocking script still executes before any visible DOM.
- **CSS fallback synergy:** `tokens.css:81-95` provides `@media (prefers-color-scheme: dark)` with `:root:not([data-theme])` selector — handles the auto/no-JS case. Bootstrap script handles stored manual preferences. These are complementary, not redundant.
- **AC-4 listener lifecycle:** Specified same-instance `MediaQueryList` reference to prevent the common leak pattern where `matchMedia()` is called again for removal, creating a different instance. StrictMode safety is an implementation detail — the tests will prove correctness regardless.
- **Existing tests need update:** The 3 html-wiring tests in `ThemeBootstrap_1545.test.ts` assert `<head>` placement — test-writer will update for `<body>` placement. New tests for AC-4 listener behavior needed.

### Challenge Results (cycle 2)
- Challenger: reconsider (confidence 0.56)
- Key concerns: (1) AC-2/AC-4 re-render conflict, (2) unverifiable FOUC claim in AC-1, (3) AC-4 listener lifecycle underspecified, (4) dual-resolution parity, (5) stale test evidence
- Architect response: All five findings accepted and incorporated. (1) AC-2 clarified: hook consumers DO re-render, non-consumers don't. (2) Removed "preventing flash-of-wrong-theme" from AC-1 — kept only testable outcomes. (3) AC-4 now specifies same-instance cleanup and theme-gated activation. (4) Dual resolution parity is accepted known duplication (~10 LOC frozen subset) — not an AC concern. (5) Tests will be updated by test-writer in next pipeline cycle.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (AC-1 tests need body-placement update; AC-4 needs new listener tests)

### Verdict: APPROVE
### Action Taken: Refined AC-1 (head→body placement), tightened AC-2 (re-render clarity), added AC-4 (OS listener), advanced backlog → todo. Cycle 2 re-entry after reviewer rejection.