---
id: 1537
title: 'P2-01: test — theme bootstrap script + useTheme hook'
status: backlog
priority: needed
created: 2026-05-13T18:41:58.250976+00:00
updated: 2026-05-13T22:42:23.976244+00:00
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
archival_reason:
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