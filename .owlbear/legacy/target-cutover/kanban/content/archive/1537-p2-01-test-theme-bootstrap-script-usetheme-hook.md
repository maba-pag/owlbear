---
id: 1537
title: 'P2-01: test — theme bootstrap script + useTheme hook'
status: archived
priority: medium
created: 2026-05-13T18:41:58.250976+00:00
updated: 2026-05-14T01:31:50.669089+00:00
tags:
  - phase-2
  - scope:cockpit
  - theme
  - test
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Tests for synchronous bootstrap script behavior, useTheme hook API, localStorage handling, OS preference fallback, 3-state toggle cycle
- **Out:** Implementation of bootstrap/hook, toggle UI, PDS compatibility verification, reactive OS-change listener (future task if needed)

## Acceptance Criteria

- AC-1: Vitest verifies an exported `applyTheme()` function reads localStorage key `owlbear-theme`, validates value against `["dark", "light"]`, and sets `document.documentElement.dataset.theme` to that value. Test cases: key="dark" → attribute "dark"; key="light" → attribute "light".
- AC-2: Vitest verifies `useTheme()` via `renderHook` returns `{ theme: 'light' | 'dark' | 'auto', toggle: () => void, isDark: boolean }`. Assertions: (a) when localStorage has `"dark"`, `theme === 'dark'`, `isDark === true`, and `document.documentElement.dataset.theme === 'dark'`; (b) when localStorage has `"light"`, `theme === 'light'`, `isDark === false`, and `document.documentElement.dataset.theme === 'light'`; (c) when localStorage key is absent/cleared, `theme === 'auto'` and `isDark` reflects OS preference (true when `prefers-color-scheme: dark` matches, false otherwise), and `document.documentElement.dataset.theme` equals the resolved value (`'dark'` or `'light'` per OS); (d) calling `toggle()` cycles through `light → dark → auto → light` with DOM proof — tests assert all three transitions: starting at `'light'`, first toggle produces `theme === 'dark'`, localStorage `"dark"`, `dataset.theme === 'dark'`; second toggle produces `theme === 'auto'`, localStorage key removed, `dataset.theme` equals OS-resolved value; third toggle produces `theme === 'light'`, localStorage `"light"`, `dataset.theme === 'light'`; (e) `isDark` always equals `theme === 'dark' || (theme === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches)`.
- AC-3: Vitest verifies when localStorage key `owlbear-theme` is absent or contains an invalid value (not in `["dark", "light"]`), `applyTheme()` reads `window.matchMedia('(prefers-color-scheme: dark)')` and sets attribute to `'dark'` when matched, `'light'` otherwise. Tests mock `matchMedia` via `Object.defineProperty` (manual mock, no deps) for both OS preference states.

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/theme-bootstrap-usetheme-testing.md
- Sources: 6 studied, 4 high-relevance (next-themes tests, next-themes script, tanstack-themes FOUC, existing Cockpit tests)
- Recommendation: Manual matchMedia mock + extracted bootstrap function testing + renderHook for useTheme (confidence: 0.87)
- Follow-up tasks created: none needed — AC is well-scoped for single test-writer pass
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial testing strategy research with established patterns; no novel architectural decisions
- Confidence in original: 0.87
- Key findings: (1) Manual matchMedia mock preferred over vitest-matchmedia-mock (0 deps, proven at scale in next-themes), (2) Bootstrap testable as extracted function — "before React" timing is architectural, verified by E2E not unit tests, (3) jsdom's built-in localStorage suffices, no custom mock needed
2026-05-13T21:37:09+00:00
## Architecture Review (REFINE cycle — post-reviewer rejection)

### Context
Task returned from review with two blocking findings: (1) toggle test only proved light→dark, not reverse; (2) hook contract narrowed to 2-state (dark/light) but brief mandates 3-state (dark/light/auto).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, single concern: theme bootstrap + useTheme hook tests |
| Interface clarity | PASS | Refined: ACs now specify 3-state type (`'light' | 'dark' | 'auto'`), full toggle cycle, DOM attribute assertions per transition, localStorage states, isDark resolution formula |
| Dependency correctness | PASS | No deps needed — RED phase, implementation doesn't exist yet |
| Module layering | PASS | Frontend test files in established `__tests__/` directory |
| TDD compliance | PASS | This IS the RED phase task; #1545 depends on it |
| KISS/YAGNI | PASS | Three focused ACs, no over-engineering. Reactive OS-change listener explicitly scoped out |
| Premise challenge | PASS | Custom tests required — no existing theme test infrastructure |
| Pattern consistency | PASS | Uses established `renderHook`, `vitest`, jsdom, manual matchMedia mock patterns |
| Security surface | N/A | Test files only |
| Single domain | PASS | Frontend/cockpit domain exclusively |

### Changes from previous approval
1. AC-2 type expanded: `'light' | 'dark'` → `'light' | 'dark' | 'auto'` (matches brief D6 and #1545 AC-3)
2. AC-2(c) added: auto state when localStorage absent, isDark reflects OS preference, DOM resolves
3. AC-2(d) replaced: single one-way toggle test → full 3-transition cycle proof (light→dark→auto→light) with localStorage + DOM assertions at each step
4. AC-2(e) added: isDark resolution formula explicit
5. AC-2(a/b/c/d) now include `document.documentElement.dataset.theme` DOM assertions (addresses "DOM source-of-truth gap")

### Challenge Results
- Challenger: reconsider (0.64) — raised 5 findings
- Architect response: partially accepted. DOM attribute assertions added to all toggle transitions (addresses "DOM source-of-truth gap" and "full-cycle proof overstated"). Dismissed 3 findings referencing `stances/` debate artifacts (non-authoritative; brief is the spec). OS-listener reactivity explicitly scoped out (not in #1545 ACs either).

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through via `test` tag — builder writes Vitest tests)

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC-2 to encode 3-state toggle contract matching brief, added DOM assertions for falsifiability, advanced to todo.
2026-05-13T21:57:06+00:00
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`

**Classes:** `TestFromAC_ThemeBootstrap_1537`, `TestFromAC_UseThemeHook_1537`

**Tests per category (behavioral proof bundle):**

| Category | Count | Notes |
|----------|-------|-------|
| Happy path | 5 | AC-1 dark/light, AC-2a localStorage dark, AC-2b localStorage light, AC-2c auto resolved |
| Edge cases | 2 | AC-2c OS light/dark when localStorage absent |
| Error paths | 2 | AC-3 missing key, AC-3 invalid value ('sepia') |
| Boundary | 5 | AC-2d full 3-transition cycle (light→dark→auto→light), AC-2e isDark formula × 4 |

**Total: 14 tests, all FAIL** — Vitest exits 1 (import resolution fails: `../hooks/useTheme` does not exist). Lint: clean.

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-1 | it.each dark + light → dataset.theme assertion |
| AC-2(a) | localStorage='dark' → theme/isDark/dataset.theme |
| AC-2(b) | localStorage='light' → theme/isDark/dataset.theme |
| AC-2(c) | localStorage absent → theme='auto', OS dark + OS light with dataset.theme proof |
| AC-2(d) | Single test, all 3 transitions: light→dark→auto→light, localStorage + DOM at each step |
| AC-2(e) | 4 tests covering all formula combinations (dark/auto+OS-dark/light/auto+OS-light) |
| AC-3 | OS fallback when key missing, key invalid, key absent + OS light |

**Commit:** `2d676801` — `test: add theme bootstrap and useTheme hook tests (#1537, test-writer)`
2026-05-13T22:25:09+00:00
## Builder Notes

### Files Changed
- serve/cockpit/web/src/hooks/useTheme.ts

### Implementation Summary
- Added exported `applyTheme()` that reads localStorage key `owlbear-theme`, validates `dark|light`, and falls back to OS preference via `matchMedia('(prefers-color-scheme: dark)')` for missing/invalid values.
- Added exported `useTheme()` hook returning `{ theme, toggle, isDark }` with 3-state behavior (`light|dark|auto`), DOM `data-theme` synchronization, localStorage persistence/removal, and toggle cycle `light -> dark -> auto -> light`.

### RED Verification (pre-implementation)
- quality-runner scoped run on `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`:
  - failed: module-load import failure for `../hooks/useTheme` (expected RED)
  - lint: clean

### GREEN Verification (post-implementation)
- quality-runner scoped run:
  - tests: 14 passed, 0 failed
  - lint: clean (0 violations)
  - coverage: `src/hooks/useTheme.ts` = 93.18% statements, 90.32% branches, 100% functions, 100% lines

### Module-Level Durable Test Check
- No dedicated durable module-level `useTheme` test file found outside task-scoped tests; skipped per workflow guidance.

### Commit
- 7a63ffe82df521cad9655c0b5453399a0000b8dd
- feat: implement theme bootstrap hook (#1537, builder)

### Evidence Summary
- AC-1 satisfied by `applyTheme` stored-value and dataset assignment behavior.
- AC-2 satisfied by `useTheme` return contract, auto fallback semantics, full toggle cycle, and `isDark` formula alignment.
- AC-3 satisfied by `applyTheme` OS preference fallback for absent/invalid storage values.
2026-05-13T22:42:23+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1537 -> backlog | second-cycle review found remaining proof gaps in AC-2(e) and AC-3 despite source/code alignment.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/hooks/useTheme.ts:30-35` validates stored `dark|light` and writes `document.documentElement.dataset.theme`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:41-53` covers stored dark/light values. | PASS |
| AC-2(a/b/c/d) | `serve/cockpit/web/src/hooks/useTheme.ts:44-78` returns `{ theme, toggle, isDark }`, persists/removes storage, syncs DOM, and cycles `light -> dark -> auto -> light`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:99-177` covers stored dark/light, auto OS fallback, and full toggle cycle with DOM/localStorage assertions. | PASS |
| AC-2(e) | `serve/cockpit/web/src/hooks/useTheme.ts:73-78` computes `isDark` from `theme === 'dark' || (theme === 'auto' && prefersDark())`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:182-229` asserts the formula only on fresh mounts; the cycle test at `:145-177` never checks `isDark` after toggles. | FAIL |
| AC-3 | `serve/cockpit/web/src/hooks/useTheme.ts:14,30-35` falls back through `window.matchMedia('(prefers-color-scheme: dark)')` for absent/invalid storage. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:57-79` covers absent+dark, invalid+light, absent+light, but no invalid+dark case; the manual mock at `:11-28` accepts any query string and does not falsify the required `(prefers-color-scheme: dark)` query. | FAIL |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-3 | Proof is insufficient for the invalid-value fallback branch: the suite never exercises invalid localStorage with dark OS preference, and the `matchMedia` mock is query-insensitive, so a wrong media query string or invalid-branch regression could still pass. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:11-28`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:57-79`, `serve/cockpit/web/src/hooks/useTheme.ts:14,30-35` | backlog |
| 2 | AC-2(e) | `isDark` proof is mount-only. The toggle-cycle test proves theme/storage/DOM transitions but never asserts `isDark`, so a stale derived value after `toggle()` would still pass. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:145-177`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:182-229`, `serve/cockpit/web/src/hooks/useTheme.ts:73-78` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC/proof contract for AC-3 so the retry must include falsifiable proof of the invalid-value + dark-OS branch and an assertion that `matchMedia('(prefers-color-scheme: dark)')` is the queried media string before the task returns to RED/GREEN. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` | Blocking finding #1 |
| 2 | architect | Refine the AC/proof contract for AC-2(e) so the retry must assert `isDark` after state transitions, not only on fresh mounts, before the task returns to RED/GREEN. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` | Blocking finding #2 |

## Observations
- The current implementation itself appears aligned with the refined task contract on storage validation, 3-state theme, DOM synchronization, toggle order, and `isDark` formula. This rejection is about proof quality, not a demonstrated source defect.
- Builder evidence was otherwise coherent: both task commits are present in `.git/logs`, the behavioral bundle included scoped tests/lint/coverage, and no downstream usages of `applyTheme` or `useTheme` were found in the workspace.
2026-05-13T23:16:32+00:00

## AC Refinement (Proof Gaps — reviewer cycle 2)

The following refine the original AC lines. These are authoritative — test-writer must follow these when adding the missing proof:

**AC-2(e) REFINED:** `isDark` always equals `theme === 'dark' || (theme === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches)` — tests must assert `isDark` both on fresh mounts (4 formula-combination tests) AND after each toggle transition in the AC-2(d) cycle test (`isDark` must be checked at every transition step alongside theme/localStorage/DOM).

**AC-3 REFINED:** Vitest verifies when localStorage key `owlbear-theme` is absent or contains an invalid value (not in `["dark", "light"]`), `applyTheme()` reads `window.matchMedia('(prefers-color-scheme: dark)')` and sets attribute to `'dark'` when matched, `'light'` otherwise. Tests mock `matchMedia` via `Object.defineProperty` (manual mock, no deps) and must: (a) cover all 4 combinations — absent+OS-dark→'dark', absent+OS-light→'light', invalid+OS-dark→'dark', invalid+OS-light→'light'; (b) use a query-sensitive mock that returns `matches: true` only for the exact query string `'(prefers-color-scheme: dark)'` (any other query returns `matches: false`), proving the implementation queries the correct media string.

### What must change in tests
1. Add test: `AC-3: applyTheme falls back to OS dark when localStorage contains invalid value` — `localStorage.setItem('owlbear-theme', 'sepia')` + mock dark OS → attribute `'dark'`
2. Replace `setMatchMedia` helper with query-sensitive variant: only return `matches: true` when `query === '(prefers-color-scheme: dark)'` and dark is configured
3. Add `isDark` assertions to the AC-2(d) toggle cycle test at each transition step (3 assertions total: `isDark === true` after light→dark, `isDark === false` after dark→auto with OS-light, `isDark === false` after auto→light)

2026-05-13T23:16:53+00:00
## Architecture Review (REFINE cycle 2 — post-reviewer proof-gap rejection)

### Context
Task returned from review with two blocking findings: (1) AC-3 missing invalid+OS-dark test case and query-insensitive mock; (2) AC-2(e) isDark asserted only on fresh mounts, not after toggle transitions. Implementation is sound — reviewer explicitly noted "about proof quality, not a demonstrated source defect."

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task, single concern |
| Interface clarity | PASS | Refined: AC-2(e) now requires post-toggle isDark assertions; AC-3 requires all 4 combos + query-sensitive mock |
| Dependency correctness | PASS | No deps |
| Module layering | PASS | Tests in established `__tests__/` |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | Minimal additions: 1 new test case, mock sensitivity fix, 3 assertions in existing cycle test |
| Premise challenge | PASS | Gaps are real — invalid+dark-OS untested, isDark post-toggle untested |
| Pattern consistency | PASS | Query-sensitive mock aligns with next-themes testing patterns from research |
| Security surface | N/A | Test files only |
| Single domain | PASS | Frontend/cockpit exclusively |

### Changes from previous approval
1. AC-2(e): Added requirement to assert isDark after each toggle transition (not just fresh mounts)
2. AC-3: Expanded from "both OS preference states" to explicit 4-combination matrix (absent×{dark,light} + invalid×{dark,light})
3. AC-3: Added query-sensitive mock requirement — mock must only match `'(prefers-color-scheme: dark)'`
4. Added explicit "What must change in tests" section for test-writer clarity

### Challenge Results
- Challenger: reconsider (0.57)
- Architect response: partially accepted. Language correction (no overclaim of implementation correctness) and contract-drift persistence accepted. Dismissed: query-sensitivity coupling for AC-2(e) (shared helper proven via AC-3), toggle+OS-dark scenario (covered by dedicated formula tests). Verdict unchanged.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through via `test` tag)

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC-2(e) and AC-3 to close proof gaps identified by reviewer, advanced to todo.
2026-05-13T23:24:47+00:00
## Test-Writer Notes

**Retry — test-only cycle (direct to review per Step 1b.1)**

**Test file:** `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`

**Changes made:**
1. Replaced `setMatchMedia(matches: boolean)` helper with query-sensitive variant: `matches: darkPreferred && query === '(prefers-color-scheme: dark)'` — any other media query returns `false`, proving the implementation queries the exact expected string.
2. Added `isDark` assertions to AC-2(d) toggle-cycle test at all three transitions: `isDark === true` after light→dark, `isDark === false` after dark→auto (OS-light), `isDark === false` after auto→light.
3. Added new test: `AC-3: applyTheme falls back to OS dark when localStorage contains invalid value and OS prefers dark` — covers the `invalid+OS-dark → 'dark'` combination missing from the previous cycle.

**Tests per category:**

| Category | Count | Notes |
|----------|-------|-------|
| Happy path | 5 | AC-1 dark/light, AC-2a/b/c stored states |
| Edge cases | 2 | AC-2c OS dark/light when localStorage absent |
| Error paths | 3 | AC-3: absent+dark, invalid+light (pre-existing), invalid+dark (new), absent+light |
| Boundary | 5 | AC-2d full 3-transition cycle + isDark at each step, AC-2e formula × 4 |

**Total: 15 tests, all PASS** — implementation already handles all cases (proof-gap-only retry). Builder skip: test-only retry, all tests green.

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-1 | it.each dark + light → dataset.theme assertion |
| AC-2(a) | localStorage='dark' → theme/isDark/dataset.theme |
| AC-2(b) | localStorage='light' → theme/isDark/dataset.theme |
| AC-2(c) | localStorage absent → theme='auto', OS dark + OS light with dataset.theme proof |
| AC-2(d) | Full 3-transition cycle with isDark at each step (new) |
| AC-2(e) | 4 formula-combination mounts + isDark in toggle cycle (new) |
| AC-3 | absent+dark, absent+light, invalid+light (pre-existing), invalid+dark (new), query-sensitive mock |

**Commit:** `ab4d80c3` — `test: add retry coverage for AC-2(e) toggle isDark and AC-3 invalid+OS-dark (#1537, test-writer)`
2026-05-13T23:57:47+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1537 -> docs | AC mapped to code and evidence sufficient.
- Review scope: Direct inspection of `serve/cockpit/web/src/hooks/useTheme.ts`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`, and adjacent consumer proof surface in `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx`.
- Independent verification: Builder-skip retry notes did not include explicit lint/coverage evidence for this cycle, so reviewer ran `quality-runner` scoped verification. Result: 15/15 tests passed on `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`; ESLint clean on `serve/cockpit/web/src/hooks/useTheme.ts` and `serve/cockpit/web/src/__tests__/theme_1537.test.tsx`; coverage for `serve/cockpit/web/src/hooks/useTheme.ts` = 93.18% statements, 90.32% branches, 100% functions, 100% lines.
- Challenger cross-check: `proceed` at confidence 0.84; no blocking findings.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/hooks/useTheme.ts:30-34` validates stored `dark|light` and writes `document.documentElement.dataset.theme`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:47-53` covers stored dark/light bootstrap behavior. | PASS |
| AC-2(a/b) | `serve/cockpit/web/src/hooks/useTheme.ts:44-78` returns `{ theme, toggle, isDark }`, reads stored theme, persists explicit values, and syncs DOM. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:108-127` proves stored `dark` and `light` return values, `isDark`, and `dataset.theme`. | PASS |
| AC-2(c) | `serve/cockpit/web/src/hooks/useTheme.ts:44-56,73-78` resolves absent storage to `auto`, derives DOM theme from OS preference, and computes `isDark` from theme/OS. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:132-149` proves absent-storage `auto` behavior for OS-dark and OS-light. | PASS |
| AC-2(d) | `serve/cockpit/web/src/hooks/useTheme.ts:51-69` removes storage for `auto`, persists `light|dark`, syncs DOM, and toggles `light -> dark -> auto -> light`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:154-187` proves the full toggle cycle, including `isDark` after each transition, storage writes/removal, and DOM state. | PASS |
| AC-2(e) | `serve/cockpit/web/src/hooks/useTheme.ts:14,73-78` implements `isDark === theme === 'dark' || (theme === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches)`. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:167,177,187,194-241` proves the formula across the cycle transitions and all four mount-state combinations. | PASS |
| AC-3 | `serve/cockpit/web/src/hooks/useTheme.ts:14,30-34` falls back through `window.matchMedia('(prefers-color-scheme: dark)')` when storage is absent/invalid and writes the resolved DOM theme. | `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:13-28,57-86` uses a query-sensitive manual `matchMedia` mock and covers absent+dark, absent+light, invalid+dark, and invalid+light. | PASS |

- Blocking findings: none.

## Observations
- The earlier review note stating there were no downstream usages is now stale: `useTheme` is referenced by `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:5-19`, but only through a mock. This does not widen the proof obligation for #1537.
- The retry note’s category summary undercounts AC-3 error-path cases as 3; the current suite exercises 4 combinations at `serve/cockpit/web/src/__tests__/theme_1537.test.tsx:57-86`. This is bookkeeping-only and not a review blocker.
- Residual risk remains that there is no live consumer integration proof for auto+OS-dark outside the hook test suite. That is outside this task’s accepted AC and not a blocker for advancing to docs.
2026-05-14T00:14:24+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A (no update needed) | `serve/cockpit/README.md` full-read: documents package at API/launch level — individual frontend hooks not enumerated. Layer 1: no removed symbols/flags, no orphan references to `useTheme`/`applyTheme`/`owlbear-theme`. Layer 2: README coherent; no contradictions from the new hook addition. |
| 2 | External attribution | Yes | Already done | `.owlbear/sources/overview.md` line 169: "Theme Bootstrap + useTheme Hook Testing Research (Task #1537)" — 4 external sources (next-themes test suite, next-themes script, tanstack-themes FOUC, vitest-matchmedia-mock) already listed with URLs and research-doc cross-refs. |
| 3 | Research doc | Yes | Verified | `.owlbear/research/theme-bootstrap-usetheme-testing.md` exists and is linked in task body under `## Research` section. |
| 4 | Deletion detection | No | N/A | No files deleted — only `serve/cockpit/web/src/hooks/useTheme.ts` and `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` were added. |

### Verification Layers
- Layer 1 — grep: no orphan refs (`useTheme|applyTheme|owlbear-theme`) in README; no removed symbols; sources entry confirmed at line 169 of overview.md.
- Layer 2 — editorial: README accurately describes cockpit at API/launch/stack level; hook implementation is an internal frontend detail below README granularity; no contradictions, gaps, or stale content caused by this task.

### Scratch cleanup
No `.owlbear/scratch/1537-*` files found. Nothing to delete.
2026-05-14T01:31:50+00:00
## Audit
### Regression Detection
- quality-runner mode full: 2848 passed, 94 failed, 11 skipped (Python + frontend)
- All 94 failures are pre-existing RED-phase tests from other tasks (#1540 ThemeToggle, #1541 SidecarCollapse, #1542 ShellSecondaryCSS, #1539 Column, #1543 TokenArchitecture, #1544 CardSignalModel, plus background engine/cockpit-view/server failures unrelated to #1537)
- 1 ESLint violation in unrelated `computeSignal.test.ts` (no-unused-vars)
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: `serve/cockpit/web/src/hooks/useTheme.ts`, `serve/cockpit/web/src/__tests__/theme_1537.test.tsx` — both cockpit frontend domain)
- purpose match: PASS (theme bootstrap function + useTheme hook with 3-state toggle, matching task scope)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC required two REFINE cycles to close proof gaps (AC-2(e) isDark mount-only, AC-3 missing invalid+dark-OS combo). Architect responded promptly and precisely to reviewer feedback, but the original AC had notable coverage gaps that required significant reviewer intervention to surface. Final AC is specific and falsifiable.

### Commit Integrity
- upstream commit presence: PASS (4 commits: `543ddcef` RED tests, `2d676801` test-writer, `7a63ffe8` builder impl, `ab4d80c3` test-writer retry)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
- AC quality score 3/5: -.03
- All other criteria: no deduction

### Confidence: .97
### Action: archive