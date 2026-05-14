---
id: 1545
title: 'P2-02: impl — theme bootstrap script + useTheme hook'
status: archived
priority: needed
created: 2026-05-13T18:42:22.373573+00:00
updated: 2026-05-14T05:48:33.130806+00:00
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
claimed_at:
archival_reason: completed
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
2026-05-14T03:38:35+00:00
## Test-Writer Notes (retry cycle 2)
- Test file: serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts
- Classes: TestFromAC_ThemeBootstrapFile_1545, TestFromAC_ThemeBootstrapBehavior_1545, TestFromAC_IndexHtmlBootstrap_1545, TestFromAC_OsListenerBehavior_1545
- Tests per category: happy 6, edge 5, error 4, boundary 1, html-wiring 3 (total new/updated: 8 FAIL, 12 prior unchanged PASS)
- Total: 20 tests; 8 updated/new FAIL, 12 pre-existing PASS
- ESLint: clean

### Retry Changes (addresses reviewer findings via arch cycle 2)

| Reviewer Finding | Action |
|-----------------|--------|
| AC-1 head placement fails HTMLHint `head-script-disabled` | Replaced `<head>` html-wiring test with `<body>` first-child test → FAIL (script still in head) |
| AC-4 OS listener not tested | Added 7 new tests: 4 happy, 3 edge for matchMedia addEventListener lifecycle → all FAIL (hook has no listener) |

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1: file exists in public/ | file-existence test → PASS (unchanged) |
| AC-1: reads localStorage, validates, sets data-theme | 9 behavior tests → PASS (unchanged, implementation exists) |
| AC-1: script in first child of `<body>`, before `<div id="root">`, not in `<head>` | 1 updated html-wiring test → FAIL (script currently in head) |
| AC-1: no type="module" | 1 html-wiring test → PASS (unchanged) |
| AC-2/AC-3: useTheme return shape + toggle cycle | Covered by 15 passing tests in theme_1537.test.tsx (pre-existing, no new tests needed) |
| AC-4: addEventListener('change') on matchMedia when theme=auto | 4 happy tests → FAIL (no listener registered) |
| AC-4: same MQL instance for add/remove (stable reference) | 1 edge test → FAIL (never added) |
| AC-4: removeEventListener on theme transition away from auto | 1 edge test → FAIL (never added) |
| AC-4: removeEventListener on unmount when theme=auto | 1 edge test → FAIL (never removed) |

- Commit: `8c1edde1`
2026-05-14T03:43:41+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/index.html`
  - `serve/cockpit/web/src/hooks/useTheme.ts`
- Implementation summary:
  - Moved `<script src="/theme-bootstrap.js"></script>` from `<head>` to the first child of `<body>` before `<div id="root">` to satisfy AC-1 retry contract.
  - Updated `useTheme` to keep a stable `MediaQueryList` instance, register `addEventListener('change', ...)` only when `theme === 'auto'`, update `data-theme` and state on OS preference changes, and remove the listener from the same instance on cleanup/theme transition away from `auto`.
- RED verification (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`: 8 failed / 12 passed (expected pre-implementation retry baseline).
  - Failures mapped to AC-1 body placement + AC-4 listener lifecycle tests.
- GREEN verification (quality-runner, scoped):
  - `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`: PASS
  - `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`: PASS
  - Combined: 35 passed / 0 failed.
- Lint status:
  - Clean (ESLint clean in scoped quality-runner run).
- Coverage:
  - `serve/cockpit/web/src/hooks/useTheme.ts`: 100% (quality-runner scoped coverage module report).
- Evidence summary:
  - AC-1 body-first script placement assertion now passes.
  - AC-4 listener registration, OS-change update behavior, stable-instance cleanup, and transition/unmount cleanup assertions all pass.
- Commit:
  - `e9a116ee` — `feat: implement theme bootstrap body placement + auto listener lifecycle (#1545, builder)`
2026-05-14T04:03:17+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1545 -> backlog | implementation aligns with the refined contract, but the retry proofs still do not falsify all AC-1 and AC-4 clauses.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The retry html-wiring assertion is too weak to prove the bootstrap script is the first child of `<body>`. It only proves the script appears somewhere in `<body>`, before `#root`, and outside `<head>`, so it would still pass if another element appeared before the bootstrap script. | AC-1: `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:31`; weak proof: `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:196`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:203`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:204`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:207`; current implementation is correct but only by direct file inspection: `serve/cockpit/web/index.html:9` | backlog |
| 2 | AC-4 | The retry suite still leaves explicit AC-4 behavior under-proved. It proves auto-mode registration and cleanup, but it does not falsifiably prove that explicit `'dark'`/`'light'` mounts have no active listener, and it only asserts `isDark` updates on OS darkening, not on the reverse OS-lightening transition required by AC-4. | AC-4: `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:34`; source contract is implemented at `serve/cockpit/web/src/hooks/useTheme.ts:60`, `serve/cockpit/web/src/hooks/useTheme.ts:66`, `serve/cockpit/web/src/hooks/useTheme.ts:67`, `serve/cockpit/web/src/hooks/useTheme.ts:68`, `serve/cockpit/web/src/hooks/useTheme.ts:71`, `serve/cockpit/web/src/hooks/useTheme.ts:74`, `serve/cockpit/web/src/hooks/useTheme.ts:92`; existing proof gaps: `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:16`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:17`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:108`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:120`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:241`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:268`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:282`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:333`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:343` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the executable proof requirement for AC-1 and send the task back through RED/GREEN with a structural assertion that fails unless the bootstrap script is the first `<body>` child, not merely before `#root`. | `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts` | AC-1 at `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:31`; current matcher only checks positions at `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:203-207` |
| 2 | architect | Refine the executable proof requirement for AC-4 and return it through RED/GREEN with spy-based negative proof for explicit `'dark'`/`'light'` mounts plus a reverse-direction assertion that `isDark` updates on OS lightening as well as darkening. | `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` | AC-4 at `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:34`; no-op listener stubs at `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:16-17`; current positive-only assertions at `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:241`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:268`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:282`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:333`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:343` |

## Observations
- Builder evidence was internally consistent for the implementation itself: scoped GREEN reported 35 passed / 0 failed, ESLint clean, and 100% scoped coverage for `useTheme.ts`.
- Direct inspection supports the builder's implementation summary: `serve/cockpit/web/public/theme-bootstrap.js:2-10` satisfies the storage validation and fallback logic, `serve/cockpit/web/index.html:9` places the external bootstrap script before React mount, and `serve/cockpit/web/src/hooks/useTheme.ts:60-74` plus `serve/cockpit/web/src/hooks/useTheme.ts:92-95` implement the AC-4 listener lifecycle and derived state updates.
- This is a proof-quality rejection, not a demonstrated runtime defect. On a first review cycle it would normally route to `todo`; because this task is already on review cycle 2, reviewer routing escalates the retry to `backlog`.
2026-05-14T04:17:00+00:00

## Architecture Review (cycle 3 — proof-quality remediation)

**Verdict:** APPROVED (after REFINE)
**Proof bundle:** behavioral

### Reviewer Findings Addressed

| # | Reviewer Finding | Resolution |
|---|-----------------|------------|
| 1 | AC-1 html-wiring assertion too weak — only proves script before `#root`, not structural first-child | Added explicit proof sub-obligation AC-1p1 below |
| 2 | AC-4 no negative proof for explicit `dark`/`light` mounts; missing reverse-direction `isDark` assertion | Added proof sub-obligations AC-4p1 and AC-4p2 below |

### Proof Sub-Obligations (cycle 3)

These refine the existing AC text into explicit, non-optional proof requirements. The AC meaning is unchanged — these make implicit structural obligations explicit for the test-writer.

- **AC-1p1 (structural first-child):** The test for "first child of `<body>`" must parse the `<body>` element content and assert the bootstrap `<script>` is the very first child element — not just "appears before `#root`". The test must fail if any other element, comment, or script precedes it.
- **AC-4p1 (negative listener):** Tests must prove that when `theme` is `'dark'` or `'light'` (via localStorage), `addEventListener` is NOT called on the `MediaQueryList` spy. One test per explicit theme. This proves the "no `matchMedia` listener is active" clause.
- **AC-4p2 (bidirectional isDark):** Tests must prove `isDark` updates in both directions: existing test covers OS darkening (`isDark` → `true`); add a test that starts with OS dark preference and simulates lightening, asserting `isDark` → `false`.

### Source-Hierarchy Note

`.owlbear/research/1545-theme-bootstrap-impl.md` still recommends inline `<head>` script (Options A/B). The **task AC is authoritative** — use external `public/theme-bootstrap.js` in first-child `<body>` position. The research doc was written before the cycle 1 CSP/HTMLHint discoveries.

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | Precise — "first child of `<body>`" was always explicit. Proof sub-obligation AC-1p1 now makes the structural verification requirement unambiguous. | Added AC-1p1 |
| AC-2 | Unchanged — pre-existing from #1537, 15 tests passing. | No action |
| AC-3 | Unchanged — pre-existing from #1537, 15 tests passing. | No action |
| AC-4 | Precise — "no matchMedia listener is active" and "isDark reflects the new value" were already bidirectional. Proof sub-obligations AC-4p1 and AC-4p2 now decompose into explicit test obligations. | Added AC-4p1, AC-4p2 |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Theme bootstrap + hook — one domain (cockpit frontend) |
| Interface clarity | PASS | `{ theme, toggle, isDark }` return shape; `data-theme` DOM contract |
| Dependency correctness | PASS | #1537 (hook impl archived), #1543 (tokens archived) |
| Module layering | PASS | Frontend-only, no backend imports |
| TDD compliance | PASS | 35 tests exist (20 task + 15 pre-existing); cycle 3 adds proof-strengthening tests that will PASS immediately |
| KISS/YAGNI | PASS | Minimal — one JS file + one HTML edit + one hook enhancement |
| Premise challenge | PASS | Bootstrap script necessary for FOUC prevention |
| Pattern consistency | PASS | Follows existing hook patterns in `src/hooks/` |
| Security surface | PASS | `script-src 'self'` CSP satisfied by external `public/` file |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results (cycle 3)

- Challenger: reconsider (confidence 0.72)
- Key concerns: (1) test-writer guidance alone insufficient after 2 cycles, (2) AC line density causes missed sub-clauses, (3) research doc still recommends contradicted approach, (4) AC-2 softness on non-consumer clause
- Architect response: Accepted findings 1–3. (1) Replaced informal guidance with explicit, numbered proof sub-obligations (AC-1p1, AC-4p1, AC-4p2) in the task body — these are inspectable by the reviewer. (2) Proof sub-obligations decompose dense AC lines into single-obligation items. (3) Added source-hierarchy note explicitly flagging the stale research doc. (4) AC-2 is pre-existing from #1537 and not in scope for this cycle — the "non-consumer" clause describes architecture, not a testable assertion for this task.

### Proof-Bundle Validation

- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (add AC-1p1, AC-4p1, AC-4p2 proof tests; all expected to PASS immediately since implementation is correct)

### Consolidation Test Coverage

- #1554 (consolidation test: board visual design) exists with depends_on including #1545 ✓

### Verdict: APPROVE
### Action Taken: Added 3 proof sub-obligations (AC-1p1, AC-4p1, AC-4p2) to make implicit AC requirements explicitly testable. Noted research doc drift. Advanced backlog → todo for cycle 3 RED/GREEN pass.
2026-05-14T04:17:05+00:00
Cycle 3 architecture review — proof-quality remediation. Added 3 explicit proof sub-obligations (AC-1p1 structural first-child, AC-4p1 negative listener, AC-4p2 bidirectional isDark) to break the proof-quality rejection loop. Noted research doc source-hierarchy drift. Challenger accepted at 0.72 with all findings incorporated. Implementation is correct — cycle 3 tests are expected to PASS immediately.
2026-05-14T04:25:17+00:00
## Test-Writer Notes (retry cycle 3 — proof-quality remediation)
- Test file: serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts
- Classes: TestFromAC_ThemeBootstrapFile_1545, TestFromAC_ThemeBootstrapBehavior_1545, TestFromAC_IndexHtmlBootstrap_1545, TestFromAC_OsListenerBehavior_1545
- Added 4 proof-gap tests, all PASS (test-only retry, implementation correct)
- ESLint: clean
- Commit: 3725494f

### Retry Changes (addresses reviewer cycle 2 findings via arch cycle 3 proof sub-obligations)

| Proof Sub-Obligation | Test Added | Result |
|---------------------|-----------|--------|
| AC-1p1: structural first-child | `DOMParser` → `body.firstElementChild` asserts tag=script and src=/theme-bootstrap.js | PASS |
| AC-4p1: no listener when theme=dark | `localStorage='dark'` → `addEventListener` not called | PASS |
| AC-4p1: no listener when theme=light | `localStorage='light'` → `addEventListener` not called | PASS |
| AC-4p2: isDark bidirectional | OS dark initial → simulateChange(false) → `isDark===false` | PASS |

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1: file exists | PASS (unchanged) |
| AC-1: storage → validation → DOM mutation | 9 behavior tests → PASS (unchanged) |
| AC-1p1: structural first element child of `<body>` | 1 new DOMParser test → PASS |
| AC-1: no type="module" | PASS (unchanged) |
| AC-4: addEventListener on auto | PASS (unchanged) |
| AC-4: OS darkening → data-theme + isDark | PASS (unchanged) |
| AC-4: OS lightening → data-theme | PASS (unchanged) |
| AC-4p1: no listener for explicit dark/light | 2 new negative-proof tests → PASS |
| AC-4p2: OS lightening → isDark=false | 1 new bidirectional test → PASS |
| AC-2/AC-3 | Pre-existing 15 tests in theme_1537.test.tsx (unchanged) |

- Total: 24 tests, all PASS (builder skip: test-only retry, implementation correct)
2026-05-14T04:44:49+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1545 -> backlog | cycle-3 proof sub-obligations AC-1p1 and AC-4p1 remain under-proved by the current retry tests.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1p1 | The new structural-first-child test still does not satisfy the explicit cycle-3 proof requirement. It asserts `doc.body.firstElementChild`, which ignores preceding comment nodes, so it would still pass if a comment appeared before the bootstrap script even though AC-1p1 says the test must fail when any element, comment, or script precedes it. | task proof requirement: `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:311`; weak matcher: `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:221`; implementation currently correct only by direct file inspection: `serve/cockpit/web/index.html:9` | backlog |
| 2 | AC-4p1 | The new explicit-theme negative tests do not yet prove that `addEventListener` is never called on the `MediaQueryList` spy. They only assert `not.toHaveBeenCalledWith('change', expect.any(Function))`, which would still pass if a broken implementation registered the listener with another signature or extra options. AC-4p1 requires proof that `addEventListener` is not called on the spy at all for `theme='dark'` and `theme='light'`. | task proof requirement: `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:312`; weak negative assertions: `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:363`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:373`; implementation currently gates listener registration correctly: `serve/cockpit/web/src/hooks/useTheme.ts:60-74` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC-1p1 executable proof requirement and route the task back through RED/GREEN with a body-node assertion that fails if any comment, element, or script precedes the bootstrap script in `<body>`. | `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts` | AC-1p1 at `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:311`; current matcher at `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:221` ignores comment nodes |
| 2 | architect | Refine the AC-4p1 executable proof requirement and route the task back through RED/GREEN with negative assertions that fail on any `MediaQueryList.addEventListener` call for explicit `dark` and `light` mounts, not only the current two-argument `change` matcher. | `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md`, `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts` | AC-4p1 at `.owlbear/kanban/tasks/1545-p2-02-impl-theme-bootstrap-script-usetheme-hook.md:312`; current assertions at `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:363` and `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:373` only deny one call shape |

## Observations
- Current implementation evidence remains favorable: `serve/cockpit/web/index.html:9` places the bootstrap script before React mount, `serve/cockpit/web/public/theme-bootstrap.js:1-10` satisfies the storage validation and fallback logic, and `serve/cockpit/web/src/hooks/useTheme.ts:60-74` implements the auto-mode listener lifecycle correctly.
- AC-4p2 is now adequately proved by the bidirectional `isDark` test in `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:380`; it is not part of this rejection.
- Upstream execution evidence is internally consistent (`24` task tests passing, ESLint clean). I did not rerun quality-runner because the remaining blockers are matcher-strength proof gaps, not contradictory runtime evidence.
- Because this task is already in cycle 3+, reviewer routing keeps the rejection at `backlog` rather than `todo`.
2026-05-14T04:54:01+00:00
2026-05-14T12:00:00+00:00
## Architecture Review (cycle 4 — proof sub-obligation correction)

**Verdict:** APPROVED (after REFINE)
**Proof bundle:** behavioral

### Reviewer Findings Addressed

| # | Reviewer Finding | Resolution |
|---|-----------------|------------|
| 1 | AC-1p1 test uses `firstElementChild` which ignores comments; cycle-3 AC-1p1 text required comment sensitivity | **Architect error in cycle 3.** AC-1p1 mixed element-level and node-level semantics: "very first child element" vs "fail if any comment precedes it." `firstElementChild` is the correct DOM API — it proves no other *element* precedes the script. HTML comments don't affect script execution order. Rewrote AC-1p1 to drop comment sensitivity. Existing test is already correct. |
| 2 | AC-4p1 tests use `not.toHaveBeenCalledWith('change', fn)` instead of `not.toHaveBeenCalled()` | **AC-4p1 text is already sufficient** ("addEventListener is NOT called on the MediaQueryList spy"). Test-writer used a weaker matcher. Added explicit matcher note to prevent recurrence. |

### Proof Sub-Obligations (cycle 4 — corrected)

- **AC-1p1 (structural first-child):** The test must assert `body.firstElementChild` is a `<script>` element with `src='/theme-bootstrap.js'`, proving no other element precedes the bootstrap script in `<body>`. Comment nodes are irrelevant to execution order and need not be tested. **NOTE: The existing test at `ThemeBootstrap_1545.test.ts:220-224` already satisfies this — no test changes needed for AC-1p1.**
- **AC-4p1 (negative listener — matcher correction):** Tests must assert `mql.addEventListener` was `not.toHaveBeenCalled()` (bare, no arguments), proving no listener is registered for any event type or call signature. Do NOT use `not.toHaveBeenCalledWith('change', ...)` — that only denies one call shape and was the cause of the cycle-3 rejection. Two tests required: one for `localStorage='dark'`, one for `localStorage='light'`.
- **AC-4p2:** Already satisfied in cycle 3. No changes.

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | Precise — unchanged from cycle 2. | No action |
| AC-1p1 | REFINED — dropped contradictory comment-sensitivity requirement from cycle 3. Existing `firstElementChild` test is correct. | Rewrote proof sub-obligation |
| AC-2 | Unchanged — pre-existing from #1537. | No action |
| AC-3 | Unchanged — pre-existing from #1537. | No action |
| AC-4 | Unchanged from cycle 2. | No action |
| AC-4p1 | CLARIFIED — added explicit matcher guidance. AC text was already correct; test-writer misimplemented. | Added matcher note |
| AC-4p2 | Satisfied — cycle 3 test passes. | No action |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Theme bootstrap + hook — one domain |
| Interface clarity | PASS | `{ theme, toggle, isDark }` return shape; `data-theme` DOM contract |
| Dependency correctness | PASS | #1537, #1543 archived/done |
| Module layering | PASS | Frontend-only |
| TDD compliance | PASS | 24 tests exist; only AC-4p1 matcher needs 2-line fix |
| KISS/YAGNI | PASS | Minimal scope |
| Pattern consistency | PASS | Follows existing hook patterns |
| Security surface | PASS | CSP satisfied |
| Single domain | PASS | Cockpit frontend |

### Challenge Results (cycle 4)

- Challenger: reconsider (confidence 0.57)
- Key concerns: (1) AC-1p1 mixed element/node semantics, (2) AC-4p1 is test-writer error not AC gap, (3) proof sub-obligations are process instructions not product behavior, (4) childNodes[0] would hit whitespace
- Architect response: All accepted and incorporated. (1) Dropped contradictory comment requirement — `firstElementChild` is correct. (2) Agreed: AC-4p1 text was sufficient, adding matcher note as implementation guidance. (3) Proof sub-obligations are test-writer guidance, not product AC — they refine verification method, not behavior. (4) `childNodes[0]` approach abandoned; `firstElementChild` retained.

### Proof-Bundle Validation

- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED (AC-1p1 test unchanged; AC-4p1 needs 2-line matcher fix `not.toHaveBeenCalledWith(...)` → `not.toHaveBeenCalled()`)

### Scope of Cycle 4

This is the minimal possible cycle. The implementation is correct. AC-1p1's existing test is correct — only the cycle-3 proof text was wrong. AC-4p1 requires exactly 2 assertion changes in existing tests. Expected: all 24 tests PASS immediately after matcher fix.

### Verdict: APPROVE
### Action Taken: Corrected AC-1p1 proof sub-obligation (architect error in cycle 3), added matcher guidance to AC-4p1, advanced backlog → todo.
2026-05-14T04:54:06+00:00
Cycle 4 architecture review — proof sub-obligation correction. AC-1p1 had contradictory element/comment semantics from cycle 3 (architect error); dropped comment requirement, existing `firstElementChild` test is already correct. AC-4p1 text was already sufficient but test-writer used weak matcher; added explicit `not.toHaveBeenCalled()` guidance. Only 2 assertion lines need changing in AC-4p1 tests. Implementation unchanged.
2026-05-14T04:59:58+00:00
## Test-Writer Notes (retry cycle 4 — proof sub-obligation correction)
- Test file: serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts
- Classes: TestFromAC_ThemeBootstrapFile_1545, TestFromAC_ThemeBootstrapBehavior_1545, TestFromAC_IndexHtmlBootstrap_1545, TestFromAC_OsListenerBehavior_1545
- Changed: 2 assertion lines (AC-4p1 tests, lines ~363 and ~373)
- Tests per category: happy 6, edge 5, error 4, boundary 1, html-wiring 3
- Total: 24 tests, all PASS (test-only retry — implementation is correct)
- ESLint: clean
- Commit: fce4a0e0

### Retry Changes (addresses reviewer cycle 3 findings via arch cycle 4)

| Proof Sub-Obligation | Change | Result |
|---------------------|--------|--------|
| AC-1p1: structural first-child | No change — existing `firstElementChild` test already correct per arch cycle 4 | PASS |
| AC-4p1: dark mount — no listener | `not.toHaveBeenCalledWith('change', expect.any(Function))` → `not.toHaveBeenCalled()` | PASS |
| AC-4p1: light mount — no listener | `not.toHaveBeenCalledWith('change', expect.any(Function))` → `not.toHaveBeenCalled()` | PASS |

### AC Coverage

| AC | Tests |
|----|-------|
| AC-1: file exists | PASS (unchanged) |
| AC-1: storage → validation → DOM mutation | 9 behavior tests → PASS |
| AC-1p1: structural first element child of `<body>` | `firstElementChild` DOMParser test → PASS |
| AC-1: no type="module" | PASS (unchanged) |
| AC-4: addEventListener on auto | PASS (unchanged) |
| AC-4: OS darkening → data-theme + isDark | PASS (unchanged) |
| AC-4: OS lightening → data-theme | PASS (unchanged) |
| AC-4p1: no listener for dark/light (strengthened to `not.toHaveBeenCalled()`) | 2 tests → PASS |
| AC-4p2: OS lightening → isDark=false | PASS (unchanged) |
| AC-2/AC-3 | Pre-existing 15 tests in theme_1537.test.tsx (unchanged) |
2026-05-14T05:11:37+00:00
## Builder Notes
- Files changed: none (no implementation edits required in this builder cycle)
- Rationale: task is in retry cycle with implementation already present; this builder pass focused on independent GREEN verification against current AC/test contract.
- Verification (quality-runner, scoped frontend):
  - Tests:
    - `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts`
    - `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`
  - Result: 39 passed, 0 failed, 0 skipped
  - Lint status: clean (`eslint`, `htmlhint`, `stylelint` all exit 0)
  - Coverage: `serve/cockpit/web/src/hooks/useTheme.ts` = 100%
- Evidence summary:
  - AC-1 wiring and bootstrap behavior tests are passing in task-scoped suite.
  - AC-4 listener lifecycle/bidirectional behavior remains passing.
  - Durable hook suite remains green; no regressions detected.
- Fixes applied: none
- Commit: none (no source change in this cycle)
2026-05-14T05:21:03+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1545 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence sufficiency: scoped quality-runner verification is internally consistent for the current contract: 39 passed / 0 failed / 0 skipped, `eslint` / `htmlhint` / `stylelint` clean, and `serve/cockpit/web/src/hooks/useTheme.ts` at 100% coverage.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/public/theme-bootstrap.js:2-11` reads `owlbear-theme`, validates `dark|light`, falls back to `matchMedia`, and sets `document.documentElement.dataset.theme`; `serve/cockpit/web/index.html:9-11` places the external bootstrap script as the first body child before `#root` and keeps the React entrypoint as the later module script; `serve/cockpit/web/.htmlhintrc:7` still enforces `head-script-disabled`; `serve/cockpit/web/vite.config.ts:10` keeps `script-src 'self'`. | `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:103`, `:111`, `:121`, `:129`, `:139`, `:147`, `:155`, `:163`, `:174`, `:196`, `:210`, `:218` prove valid/invalid storage resolution, OS fallback, body placement, non-head placement, non-module wiring, and structural first-child proof. | PASS |
| AC-2 | `serve/cockpit/web/src/hooks/useTheme.ts:1-97` imports only hook primitives, not React Context; `serve/cockpit/web/src/hooks/useTheme.ts:37-97` returns `{ theme, toggle, isDark }` and manages `data-theme`; `serve/cockpit/web/src/tokens.css:56` and `:84` provide `[data-theme="dark"]` and `:root:not([data-theme])` selector-based restyling for non-consumers. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:108`, `:120`, `:132`, `:142`, `:154`, `:194`, `:207`, `:221`, `:234` prove return shape, DOM mutation, toggle-driven consumer rerenders, and `isDark` derivation across explicit and auto themes. | PASS |
| AC-3 | `serve/cockpit/web/src/hooks/useTheme.ts:17-26` resolves stored vs OS theme; `serve/cockpit/web/src/hooks/useTheme.ts:51-53` persists explicit themes and removes the key for `auto`; `serve/cockpit/web/src/hooks/useTheme.ts:78-89` implements the light -> dark -> auto cycle. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:57`, `:65`, `:74`, `:83`, `:154` prove OS fallback for absent/invalid storage and the full light -> dark -> auto -> light toggle cycle with localStorage and DOM assertions. | PASS |
| AC-4 | `serve/cockpit/web/src/hooks/useTheme.ts:37` memoizes a stable `MediaQueryList`; `serve/cockpit/web/src/hooks/useTheme.ts:63-74` registers/removes the `change` listener on that instance; `serve/cockpit/web/src/hooks/useTheme.ts:66-68` updates both DOM theme and state on OS changes; `serve/cockpit/web/src/hooks/useTheme.ts:92-97` returns the updated `isDark`. | `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:248`, `:256`, `:268`, `:283`, `:299`, `:321`, `:348`, `:358`, `:368`, `:380` prove auto-mode listener registration, darkening/lightening updates, same-instance cleanup on unmount/transition, no listener for explicit dark/light mounts, and bidirectional `isDark` updates. | PASS |

## Observations
- Challenger returned `reconsider` on a possible hardening opportunity around rerender-specific stable-reference proof. I treated it as non-blocking because the final cycle-4 contract explicitly accepted `firstElementChild` for AC-1p1 and `not.toHaveBeenCalled()` for AC-4p1, the source directly proves the memoized `MediaQueryList` at `serve/cockpit/web/src/hooks/useTheme.ts:37`, and the current proof packet already exercises same-instance cleanup at `serve/cockpit/web/src/__tests__/ThemeBootstrap_1545.test.ts:299`, `:321`, and `:348`.
- `.owlbear/research/1545-theme-bootstrap-impl.md` still contains the superseded head-script recommendation from pre-refinement research. The task AC, implementation, and passing proof surface now consistently use the external `public/theme-bootstrap.js` body-first approach.
2026-05-14T05:30:14+00:00
## Docs Gate

### Checklist

| Item | Finding | Action |
|------|---------|--------|
| 1. README Verification | `serve/cockpit/README.md` verified. Task added `public/theme-bootstrap.js`, `index.html` wiring, and `useTheme.ts` listener lifecycle — all internal frontend implementation details. README documents launch commands, stack table, backend API surface, and product boundary; none of these are touched by this task. No contradictions found. No update needed. | None |
| 2. External Attribution | `.owlbear/sources/overview.md` already contains a "Theme Bootstrap Script Implementation Research (Task #1545)" section with all 4 high-relevance sources (Static Signal, dev.to/gaisdav, next-themes script.ts, next-themes index.tsx). Present before this gate pass. | None |
| 3. Research Doc | `.owlbear/research/1545-theme-bootstrap-impl.md` exists and is linked from the task body. Section 4 still recommended Option A (inline IIFE in `<head>`) — superseded by pipeline refinements. Updated: added bold warning callout to Section 4 and new Section 6 (Outcome Note) documenting the two arch refinements (CSP→external file, HTMLHint→body first child). | Updated research doc |
| 4. Deletion Detection | No files deleted. No orphaned references. | None |

### Files Updated
- `.owlbear/research/1545-theme-bootstrap-impl.md` — added warning callout to Section 4, added Section 6 documenting superseded recommendation (commit `6cc9b3cd`)

### Scratch Cleanup
- No `1545-*` scratch files found.

DONE #1545 -> done | docs gate passed
2026-05-14T05:48:33+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 6318 passed, 219+ failed, 25 skipped\n- All failures in unrelated domains (Python engine/migration/ideation/memory tests, frontend ResponsiveLayout/KanbanBoard filter). Zero failures in task-scoped files or theme domain.\n- Task-scoped evidence: 39 passed / 0 failed (24 task + 15 pre-existing hook tests)\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (all 6 commits touch only cockpit frontend: `public/theme-bootstrap.js`, `index.html`, `useTheme.ts`, `ThemeBootstrap_1545.test.ts`, research doc)\n- purpose match: PASS (theme bootstrap script + auto listener lifecycle matches stated task purpose)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 3/5\n- 4 architecture review cycles to reach stable AC\n- Cycle 1 missed HTMLHint `head-script-disabled` policy conflict and OS preference listener gap (both caught by reviewer)\n- Cycle 3 introduced contradictory proof sub-obligation (AC-1p1 mixed element/node semantics), self-corrected in cycle 4\n- Final AC is solid with well-defined proof sub-obligations\n\n### Commit Integrity\n- upstream commit presence: PASS (researcher: `cb3863cb`, builder: `10842b67` + `e9a116ee`, test-writer: `cc389652` + `8c1edde1` + `3725494f` + `fce4a0e0`, doc-writer: `6cc9b3cd`)\n- kanban commit packaging: pending (this audit)\n\n### Reviewer Evidence\n- Present and detailed: PASS verdict with full AC-to-code mapping for AC-1 through AC-4, including proof sub-obligations AC-1p1, AC-4p1, AC-4p2\n- Builder evidence: 39 passed / 0 failed, ESLint/HTMLHint/Stylelint clean, 100% coverage on useTheme.ts\n\n### Deduction Breakdown\n- AC quality score 3/5: -.03\n- No other deductions\n\n### Confidence: 0.97\n### Action: archive