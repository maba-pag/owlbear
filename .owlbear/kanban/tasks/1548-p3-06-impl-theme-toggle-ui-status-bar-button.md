---
id: 1548
title: 'P3-06: impl — theme toggle UI: status bar button'
status: done
priority: important
created: 2026-05-13T18:43:23.870309+00:00
updated: 2026-05-14T06:49:37.211445+00:00
tags:
  - phase-3
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1540
  - 1545
blocked: false
block_reason:
claimed_at: 2026-05-14T06:49:37.211445+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Theme toggle button component in status bar (right side), wired to `useTheme().toggle`, visual indication of current theme state
- **Out:** useTheme hook implementation (done in P2-02 #1545), theme bootstrap

## Acceptance Criteria

- AC-1: `ThemeToggle` default export from `components/ThemeToggle.tsx` renders a `button`-role element
- AC-2: Clicking the ThemeToggle button calls `useTheme().toggle` once per click
- AC-3: ThemeToggle button's combined descriptor (`aria-label` + `textContent`) is distinct for each theme state (`'light'`, `'dark'`, `'auto'`) — 3 unique values
- AC-4: `Shell.tsx` renders `<ThemeToggle />` in the status bar after `DRStatusIndicator`

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1548-theme-toggle-button.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: PButton-based ThemeToggle component with text label per state, placed as last child in Shell status bar (confidence: 0.88)
- Challenge: skipped — trivial component, no architecture decisions
- Follow-up tasks: none needed — #1548 is the impl task itself, tests exist at ThemeToggle.test.tsx
- Commit: 9f3c15c
2026-05-14T06:06:04+00:00
## Architecture Review

**Verdict:** APPROVE → todo

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 (original) | Bundled two targets: component rendering + Shell placement. B1 violation. | Split into AC-1 (component) + AC-4 (Shell placement) |
| AC-2 (original) | Used banned word "exactly" (B3). Count=1 is exhaustive enumeration, but reworded to avoid flag. | Reworded: "once per click" |
| AC-3 | Passes h-ac-quality. Maps directly to test assertion (3 unique descriptors). | Kept as-is |
| AC-1 (refined) | Single target: ThemeToggle default export, button-role element. B1/B2 pass. | New line |
| AC-4 (refined) | Single target: Shell.tsx placement after DRStatusIndicator. B1 pass. | New line |

### Architecture Notes
- **Pattern consistency:** Follows DRStatusIndicator convention — PButton with `variant="secondary"`, `aria-label`, `data-testid` in status bar. Codebase evidence: `serve/cockpit/web/src/components/DRStatusIndicator.tsx`.
- **Module layering:** ThemeToggle imports from `hooks/useTheme` (sibling) and PDS (external). No upward imports.
- **Single responsibility:** One component file + one Shell integration line. Atomic.
- **KISS/YAGNI:** ~20-30 lines, no new deps, no new CSS. Minimal scope.
- **Security surface:** None — pure UI component, no system boundaries.

### Dependency Analysis
- #1540 (test task): archived/completed — tests exist at `ThemeToggle.test.tsx`
- #1545 (useTheme hook): archived/completed — hook API: `{ theme, toggle, isDark }`
- Consolidation test #1554 exists under parent #1534

### Challenger Results
- Confidence: 0.41 → reconsider
- Critical findings: (1) AC-1 bundled two targets, (2) "exactly" banned word in AC-2
- Resolution: Split AC-1 into AC-1+AC-4, reworded AC-2. Both critical findings addressed.
- Override on Shell integration test gap: AC-4 is a single JSX line; behavioral bundle covers component behavior (AC-1/2/3). Shell placement verified at review.

Proof bundle: behavioral
2026-05-14T06:19:45+00:00
test-writer crashed once (no response returned); releasing claim before retry
2026-05-14T06:26:41+00:00
## Test-Writer Notes
- Test file 1: `serve/cockpit/web/src/__tests__/ThemeToggleComponent_1548.test.tsx`
- Test file 2: `serve/cockpit/web/src/__tests__/ThemeToggleShell_1548.test.tsx`
- Classes: `TestFromAC_ThemeToggleComponent_1548`, `TestFromAC_ShellThemeTogglePlacement_1548`
- Tests per category (component file): happy 3, edge 2, error 0, boundary 4 — 9 tests
- Tests per category (shell file): happy 2, edge 0, error 0, boundary 0 — 2 tests
- Total: 11 tests, all FAIL
- ruff: n/a (TypeScript); eslint: clean

**AC coverage table:**
| AC | Tests | Failure mode |
|----|-------|-------------|
| AC-1 (ThemeToggle renders button-role) | 2 (happy + edge) | ImportError — ThemeToggle.tsx missing |
| AC-2 (click calls toggle once) | 3 (happy + edge + boundary) | ImportError — ThemeToggle.tsx missing |
| AC-3 (distinct descriptors per state) | 4 (happy + 3 boundary) | ImportError — ThemeToggle.tsx missing |
| AC-4 (Shell renders ThemeToggle after DRStatusIndicator) | 2 (happy + DOM order) | AssertionError — Shell does not render ThemeToggle |

**Split rationale:** Component tests (AC-1/2/3) import the real ThemeToggle so they fail via ImportError when the module doesn't exist. Shell tests (AC-4) mock ThemeToggle to isolate Shell placement logic — they fail via AssertionError because Shell does not import/render ThemeToggle.

Commit: a3dde802
2026-05-14T06:32:04+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/src/components/ThemeToggle.tsx`
  - `serve/cockpit/web/src/Shell.tsx`
- Implementation summary:
  - Added `ThemeToggle` default export component with native `button` element, wired to `useTheme().toggle`.
  - Implemented explicit per-state descriptors (`aria-label` + text) for `light`, `dark`, and `auto` to guarantee uniqueness.
  - Integrated `<ThemeToggle />` into `Shell` status bar immediately after `DRStatusIndicator`.

- RED verification (quality-runner):
  - Scoped tests: `src/__tests__/ThemeToggleComponent_1548.test.tsx`, `src/__tests__/ThemeToggleShell_1548.test.tsx`
  - Result: expected failures confirmed (missing ThemeToggle import + Shell placement assertion failures)
  - Lint: clean

- GREEN verification (quality-runner):
  - First run exposed jsdom role mismatch with PDS `PButton` (tests could not resolve `role="button"`).
  - Applied same-context fix: switched ThemeToggle to native `<button>` while preserving behavior and descriptors.
  - Re-run result: 11 passed, 0 failed
  - Lint result: clean (eslint)
  - Coverage: not reported by scoped frontend run

- Commit:
  - `55e8d70d2da2485610e0e7781d1113b54f2d7cd5`
  - Message: `feat: add theme toggle status-bar control (#1548, builder)`
  - Committed files exactly:
    - `serve/cockpit/web/src/Shell.tsx`
    - `serve/cockpit/web/src/components/ThemeToggle.tsx`

- Evidence summary:
  - AC-1: ThemeToggle renders `button` role element (component tests pass)
  - AC-2: Click invokes `useTheme().toggle` once per click (component tests pass)
  - AC-3: Descriptor uniqueness across `light`/`dark`/`auto` verified (component tests pass)
  - AC-4: Shell renders ThemeToggle in status bar after DRStatusIndicator (shell placement tests pass)
2026-05-14T06:41:21+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1548 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: builder notes covered scoped tests and eslint but omitted coverage despite `Proof bundle: behavioral`; reviewer independently dispatched `quality-runner` to close that proof gap.
- Independent verification summary (`quality-runner`): 11 passed, 0 failed; eslint clean; coverage collected successfully in `serve/cockpit/web`.
- Challenger result: `proceed` with confidence 0.84; no blocking findings.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/ThemeToggle.tsx:18` default export; `:23-29` renders native `<button>` with label/text | `serve/cockpit/web/src/__tests__/ThemeToggleComponent_1548.test.tsx:49` asserts button role; `:55` asserts exactly one button | PASS |
| AC-2 | `serve/cockpit/web/src/components/ThemeToggle.tsx:19` reads `toggle` from `useTheme()`; `:27` wires `onClick={toggle}` | `serve/cockpit/web/src/__tests__/ThemeToggleComponent_1548.test.tsx:62-64` asserts one call on one click; `:76-79` asserts two calls on two clicks | PASS |
| AC-3 | `serve/cockpit/web/src/components/ThemeToggle.tsx:3-15` defines distinct per-state labels; `:26` binds `aria-label`; `:29` renders per-state text | `serve/cockpit/web/src/__tests__/ThemeToggleComponent_1548.test.tsx:32-36` builds combined descriptor from `aria-label + textContent`; `:85-90` asserts 3 unique descriptors; `:94`, `:98`, `:102` assert pairwise distinctness | PASS |
| AC-4 | `serve/cockpit/web/src/Shell.tsx:98` status bar header; `:140-145` renders `<ThemeToggle />` after `<DRStatusIndicator />` | `serve/cockpit/web/src/__tests__/ThemeToggleShell_1548.test.tsx:120-125` asserts ThemeToggle is inside status bar; `:131-140` asserts it follows `dr-indicator` in DOM order | PASS |

- Coverage note from independent rerun:
  - `src/components/ThemeToggle.tsx`: 87.5% statements, 40% branches, 100% functions, 100% lines
  - `src/Shell.tsx`: 81.48% statements, 78.78% branches, 20% functions, 78.4% lines
- Review conclusion: no blocking AC mismatch, no false-green test gap, and no security-relevant surface introduced by this task.

## Observations
- Builder proof packet should include coverage on the first pass for `behavioral` tasks so reviewer reruns are unnecessary.
- `Shell.tsx` whole-file coverage remains modest because the file is large and the task-scoped tests intentionally exercise only the status-bar placement contract. That is acceptable for AC-4, but it should not be treated as broader Shell regression proof.
2026-05-14T06:48:00+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | `serve/cockpit/README.md` read in full. No mentions of theme, ThemeToggle, or Shell status bar components — README documents stack, APIs, config vars, and domain boundaries, not individual UI components. Task added a frontend-internal UI control; no README drift caused. |
| 2 | External attribution | Yes | N/A — already complete | `sources/overview.md` line 101: `## Theme Toggle Button Research (Task #1548)` with web.dev and next-themes entries. No update needed. |
| 3 | Research doc | Yes | N/A — linked | `.owlbear/research/1548-theme-toggle-button.md` exists and is cited in task body under `## Scope` / Research block. |
| 4 | Deletion detection | No | N/A | Builder added `ThemeToggle.tsx` (new) and modified `Shell.tsx` (addition only). No files deleted; no orphaned references possible. |

### Verification Layers
- Layer 1 — grep: `grep_search` on `serve/cockpit/README.md` for `theme`, `ThemeToggle`, `dark`, `light` — 0 matches. No stale references to remove or add.
- Layer 2 — editorial: README Product Boundary section lists "viewing, editing, moving/archiving, user blocks, health/admin, activity, and decision resolution." ThemeToggle is a self-contained UI control; no product boundary description warrants update for a status-bar button addition.

### Scratch Cleanup
No `.owlbear/scratch/1548-*` files found.