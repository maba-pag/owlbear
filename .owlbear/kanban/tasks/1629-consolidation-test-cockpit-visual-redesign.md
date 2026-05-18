---
id: 1629
title: 'Consolidation test: cockpit visual redesign'
status: review
priority: important
created: 2026-05-16T03:37:57.297125+00:00
updated: 2026-05-18T03:19:01.227001+02:00
tags:
  - frontend
  - pds
  - consolidation-test
parent: 1590
depends_on:
  - 1594
  - 1595
  - 1596
  - 1603
  - 1604
  - 1605
  - 1606
  - 1607
  - 1614
  - 1615
  - 1616
  - 1617
  - 1618
  - 1624
  - 1625
  - 1626
  - 1627
  - 1628
  - 1636
  - 1637
ac:
  - Vitest unit tests (`npm test`), full Playwright e2e suite (`npm run 
    test:e2e:all`), and production build (`npm run build`) complete with zero 
    failures
  - 'JSX inline-style attributes (`style={…}`) in `serve/cockpit/web/src/**/*.tsx`
    total at most 4; each has a `// inline-justified: {reason}` code comment documenting
    why CSS/Tailwind cannot replace it'
  - Playwright AxeBuilder scans with tags `['wcag2a', 'wcag2aa', 'wcag21a', 
    'wcag21aa']` produce zero violations across board, sidecar, and modal 
    surfaces under both `.scheme-light` and `.scheme-dark` document themes
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Full-surface consolidation test across all 4 batches of the cockpit visual redesign. Verifies cross-cutting quality: test suites green, inline style budget, theme correctness, accessibility compliance.

Scope: Integration verification of all component migration, token migration, layout, and polish work.
Out of scope: Individual component behavior (covered by per-task tests).

[[2026-05-17T23:18:46+02:00]]
## Architecture Review

**Verdict:** APPROVED (after REFINE)

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1: Full test suites + production build | REFINED — original used `npm run test:e2e` (fast-gate: 3 specs only). Changed to `npm run test:e2e:all` (full 17-spec Playwright suite). Added `npm run build` (`tsc -b && vite build`) as production build gate. | Rewrote to close false-green path |
| AC-2: Inline style budget | REFINED — original grep `style={{` misses 3 `style={OVERLAY_STYLE}` instances in RepairPanel.tsx (object-backed inline styles). Changed pattern to `style={…}` (catches both forms). Adjusted budget from 3 to 4 to account for runtime-positioned elements (context menu, DRStatusIndicator/HealthBadge popovers, dynamic grid columns) that cannot be CSS-ified. Added justification comment requirement. | Rewrote to prevent false-green |
| AC-3: Dual-theme axe-core scan | REFINED — original contained B3 banned word "correctly." Removed vague rendering check. Specified exact axe-core tags matching existing e2e/accessibility-sweep.spec.ts. Expanded from single board route to "board, sidecar, and modal surfaces" matching the existing accessibility sweep scope. Added dual-theme axis (`.scheme-light` + `.scheme-dark`) — the existing sweep only tests default theme. | Rewrote for B3 compliance + scope parity |

### Architecture Notes

1. **Proof bundle: `critical`** — Confirmed. Final quality gate for 19-task visual redesign. Full TDD + challenger + code-reader + full reviewer scope is warranted.
2. **Dependencies:** All 19 dependencies archived (completed/duplicate). Dep chain is satisfied.
3. **Single responsibility:** Consolidation testing only — no implementation work beyond converting remaining convertible inline styles. ✓
4. **Testing infrastructure:** Vitest (87 unit tests), Playwright (17 e2e specs), @axe-core/playwright@^4.11.3 installed. Infrastructure supports all ACs.
5. **Theme mechanism:** `.scheme-light`/`.scheme-dark` on `document.documentElement` via `useTheme()` hook. PDS components respond to `data-theme` attribute. Both mechanisms set by `setDocumentTheme()` in `useTheme.ts`.
6. **Inline style inventory:** 14 total JSX inline-style instances (11 `style={{`, 3 `style={VAR}`). ~4 are dynamic positioning (must remain inline), ~10 convertible to CSS/Tailwind. Budget of 4 is achievable.

### Dependency Analysis

- Parent #1590 (umbrella) depends_on [1629]. This task completing unblocks the parent.
- No circular dependencies detected.

### Challenger Results

Challenger confidence: 0.31 (block recommendation). Three critical/moderate findings, all addressed:
- **AC-1 e2e scope (critical):** `npm run test:e2e` → `npm run test:e2e:all`. RESOLVED.
- **AC-2 false-green (critical):** `style={{` → `style={…}` pattern. RESOLVED.
- **Missing build gate (moderate):** Added `npm run build` to AC-1. RESOLVED.
- **AC-3 scope regression (moderate):** Expanded to multi-surface, dual-theme. RESOLVED.
- **Theme ambiguity (minor):** Builder-level detail, not AC-level concern. ACCEPTED as-is.

[[2026-05-17T23:36:31+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/tests/test_visual_redesign.py (durable, consolidation-test)
- Playwright spec: serve/cockpit/web/e2e/accessibility-dual-theme.spec.ts
- Classes: TestCockpitVisualRedesignSuiteGates, TestCockpitVisualRedesignInlineStyleBudget, TestCockpitVisualRedesignDualTheme
- Tests per category: happy 0, edge 0, error 0, boundary 4 Python + 8 Playwright
- Total: 4 Python tests + 8 Playwright spec tests, all FAIL
- ruff: clean

**AC coverage:**
| AC | Python test(s) | Playwright spec |
|----|----------------|-----------------|
| AC-1: Playwright e2e:all zero failures | test_playwright_e2e_all_passes (FAILS: RepairPanel span-onClick violation in existing sweep) | — |
| AC-2: ≤4 inline styles with justification | test_inline_style_count_at_most_four, test_each_inline_style_has_justification_comment (FAIL: 14 styles, 0 justified) | — |
| AC-3: dual-theme axe zero violations | test_dual_theme_axe_spec_passes (FAILS: RepairPanel violation) | accessibility-dual-theme.spec.ts (8 tests, all FAIL: RepairPanel span-onClick under both themes) |

**RED evidence:**
- AC-2 tests: AssertionError — 14 inline style attributes found (budget is 4); all 14 lack `// inline-justified:` comment
- AC-1/AC-3 tests: Will fail via subprocess (RepairPanel `<span onClick>` interactive-supports-focus violation in both accessibility-sweep.spec.ts and accessibility-dual-theme.spec.ts)
- Vitest (npm test) and build (npm run build) currently PASS — removed per w-tdd-red §5 (tests that pass in RED must be removed or refined)

**Playwright dual-theme spec design:**
- Parametrised over ['light', 'dark'] themes — 2 describe blocks × 4 surfaces = 8 tests
- Theme injection via page.addInitScript (seeds localStorage before useTheme() reads it)
- Theme class assertion guard (html.scheme-light/scheme-dark) prevents silent wrong-theme scans
- Known RED: RepairPanel confirm dialog <span onClick> fails under BOTH themes

[[2026-05-18T00:04:19+02:00]]
## Builder Notes
- Implementation: reduced JSX inline styles from 14 -> 4 and added required `// inline-justified:` comments on all remaining runtime-driven style attributes.
- Accessibility remediation: removed unnecessary wrapper span around RepairPanel confirm control; RepairPanel and other static inline styles moved to CSS classes.
- Files changed:
  - serve/cockpit/web/src/KanbanBoard.tsx
  - serve/cockpit/web/src/KanbanBoard.css
  - serve/cockpit/web/src/components/ErrorBoundary.tsx
  - serve/cockpit/web/src/components/ErrorBoundary.css
  - serve/cockpit/web/src/components/HistorySubtab.tsx
  - serve/cockpit/web/src/components/DRStatusIndicator.tsx
  - serve/cockpit/web/src/components/HealthBadge.tsx
  - serve/cockpit/web/src/components/RepairPanel.tsx
  - serve/cockpit/web/src/components/RepairPanel.css
- Commit: 1aa5cf16 (`fix: reduce cockpit inline styles and remediate repair panel a11y (#1629, builder)`)

### Verification Evidence
- RED gate (pre-change): quality-runner showed inline-style budget tests failing (14 styles, missing comments).
- GREEN checks (post-change):
  - `quality-runner` retry (scoped on `serve/cockpit/tests/test_visual_redesign.py`) => 2 passed, 1 failed.
  - Passing tests:
    - TestCockpitVisualRedesignInlineStyleBudget::test_inline_style_count_at_most_four
    - TestCockpitVisualRedesignInlineStyleBudget::test_each_inline_style_has_justification_comment
  - Remaining failure:
    - TestCockpitVisualRedesignSuiteGates::test_playwright_e2e_all_passes
    - Error: `subprocess.TimeoutExpired: Command ['npm', 'run', 'test:e2e:all'] timed out after 400 seconds`
- Lint: clean (ruff/eslint/stylelint clean in quality-runner output).
- Additional direct evidence: running `cd serve/cockpit/web && npm run test:e2e:all` showed many unrelated red Playwright specs, so AC-1 cannot be closed within task 1629 scope.

### Escalation
- Gate is structurally unreachable in current branch state: AC-1 requires full Playwright suite green, but full suite currently has multiple unrelated failures and exceeds the 400s subprocess budget used by consolidation test.
- Added prerequisite dependency: #1637 (`Unblock full Playwright e2e:all gate for cockpit consolidation`).

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Resolve failing specs in full Playwright suite and make `npm run test:e2e:all` finish green within gate budget, then rerun `serve/cockpit/tests/test_visual_redesign.py` | serve/cockpit/web/e2e/*.spec.ts, serve/cockpit/web/src/**, serve/cockpit/tests/test_visual_redesign.py | `test_playwright_e2e_all_passes` timeout at 400s; direct Playwright run showed multiple unrelated red specs |
| 2 | reviewer | Re-validate AC-1/AC-3 after #1637 lands, ensuring consolidation test file passes all 4 tests with no timeouts | serve/cockpit/tests/test_visual_redesign.py, serve/cockpit/web/e2e/accessibility-dual-theme.spec.ts | quality-runner retry: 2 passed, 1 failed (timeout) |

[[2026-05-18T03:19:01+02:00]]
## Builder Notes
- Implementation: removed two redundant inline `style={{ cursor: 'pointer' }}` attributes now covered by `SessionRows.css`, reducing total `style={...}` occurrences from 6 to 4 and eliminating missing inline-justified comment violations.
- Files changed:
  - serve/cockpit/web/src/components/ActivityTab.tsx
  - serve/cockpit/web/src/components/HistorySubtab.tsx
- Tests: 4 passed (`serve/cockpit/tests/test_visual_redesign.py`), 0 failed.
- Coverage: not reported for this scoped consolidation gate run (no data collected for module coverage in quality-runner output).
- Lint: clean (`ruff=0`, `eslint=0`).
- Evidence summary: quality-runner (scoped, task 1629) now reports all consolidation tests passing, including AC-1/AC-2/AC-3 checks in `test_visual_redesign.py`.
- Commit: 9843892d (`fix: finalize inline style budget for visual redesign consolidation (#1629, builder)`).
- Approach: surgical GREEN fix only; no test changes; no unrelated frontend refactors.
