---
id: 1540
title: 'P3-05: test — theme toggle UI: status bar button'
status: archived
priority: medium
created: 2026-05-13T18:41:58.336718+00:00
updated: 2026-05-13T22:09:32.085375+00:00
tags:
  - phase-3
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
- **In:** Tests for toggle button rendering, click behavior calling useTheme toggle, visual state indication per theme
- **Out:** Toggle implementation, useTheme hook (tested in P2-01), status-bar placement (Shell integration concern)

## Acceptance Criteria

- AC-1: Vitest verifies `<ThemeToggle />` renders an accessible button element (`role="button"`)
- AC-2: Vitest verifies clicking the toggle button invokes `useTheme().toggle` (mock hook via `vi.mock`, assert mock called once)
- AC-3: Vitest verifies button accessible name or content differs for each theme state (light, dark, auto) when `useTheme` mock returns the respective value

## Builder Guidance

- `@testing-library/user-event` is NOT currently in `package.json` — either add it as a devDependency or use `fireEvent.click` from existing `@testing-library/react`
- Mock pattern: `vi.mock('../hooks/useTheme')` matching existing hook-mocking convention (see `ActivityTab.sse-refetch.test.tsx`)
- Wrap renders in `<PorscheDesignSystemProvider>` per existing test convention
- Expected file: `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx`

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1540-theme-toggle-ui-test-approach.md
- Sources: 6 studied, 4 high-relevance (≥0.85)
- Recommendation: Mock useTheme via vi.mock, test 3 ACs with click + RTL (confidence: 0.92)
- Follow-up tasks created: none needed — task well-scoped, impl task #1548 already exists
- Decision requests: none
2026-05-13T19:48:13+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only ThemeToggle button rendering and behavior |
| Interface clarity | PASS | AC specifies exact assertions: role query, mock call count, content difference per state |
| Dependency correctness | PASS | No deps needed — RED test task runs independently; #1548 depends on this |
| Module layering | PASS | Test in `__tests__/`, mocks hook module, follows existing pattern |
| TDD compliance | PASS | IS the RED phase test task in TDD pair with #1548 |
| KISS/YAGNI | PASS | 3 focused ACs, no abstractions |
| Premise challenge | PASS | Required for TDD pair with #1548 (impl) |
| Pattern consistency | PASS | vi.mock hook, PDS provider wrap, role queries — all match existing tests |
| Security surface | PASS | UI test only, no system boundary |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger: reconsider (0.58)
- Findings: (1) AC-1 "status bar area (right side)" untestable in jsdom, (2) userEvent not in package.json, (3) auto state contract gap across tasks, (4) requirements drift concern
- Architect response: ACCEPTED findings 1-2, REFINED ACs accordingly. REBUTTED finding 3 (mock isolation is standard; consolidation test #1554 covers integration). REBUTTED finding 4 (mock assertion IS the unit-test equivalent of "invokes toggle").

### AC Refinements Applied
- AC-1: Removed untestable "status bar area (right side)" → now specifies accessible button role query
- AC-2: Added explicit "vi.mock, assert mock called once" for independent verifiability
- AC-3: Added parameterization requirement (all 3 states) and mock return specification
- Added Builder Guidance section noting userEvent dependency gap and existing patterns to follow

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: pass-through (tagged `test`)

### Design Diverge
- Trigger: skipped — single clear approach (vi.mock + RTL), no competing designs

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined AC wording for independent verifiability, added builder guidance on userEvent dependency, advanced to todo
2026-05-13T20:05:59+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no Python tests applicable.
- Task AC describes frontend Vitest tests for `&lt;ThemeToggle /&gt;`; these are the builder's deliverable.
- Passing through to builder.
2026-05-13T20:25:54+00:00
## Builder Notes
- Task type: non-implementation test delivery (`test` tag). Implemented AC as RED-phase Vitest coverage only; no production source changes.
- Files changed:
  - serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx
- AC mapping:
  - AC-1: added test verifying `<ThemeToggle />` renders an accessible button (`getByRole('button')`).
  - AC-2: added hook-mock interaction test (`vi.mock('../hooks/useTheme')`) asserting click triggers `useTheme().toggle` exactly once.
  - AC-3: added state-parameterized verification that button accessible name/content descriptor differs across `light`, `dark`, and `auto` mocked theme states.
- Quality evidence (quality-runner, scoped):
  - Tests: RED confirmed (`vitest` exit 1) with expected unresolved import `../components/ThemeToggle` (implementation out of scope for this task).
  - Lint: clean for changed test file (`eslint` exit 0).
  - Coverage: not produced because suite load fails at expected RED unresolved import.
  - Module-level durable test file: no dedicated ThemeToggle durable suite exists yet — skipped.
- Commit:
  - 42f25760
  - `test: add RED tests for theme toggle UI (#1540, builder)`
- Evidence summary:
  - This task is explicitly test-only and out-of-scope for implementation. RED tests now encode the ThemeToggle contract for follow-up implementation task #1548.
2026-05-13T21:07:48+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1540 -> docs | AC mapped to code and evidence sufficient.
- Blocking findings: none.
- Builder evidence reviewed first and found internally consistent for a RED-phase test-only task: scoped `vitest` RED at missing `../components/ThemeToggle`, scoped `eslint` clean, commit `42f25760` is present in `.git/logs/refs/heads/dev:2757`, and direct file inspection matches the reported single-file change. Coverage absence is non-blocking here because no production code changed and the suite intentionally stops at the missing component import boundary.
- Challenger cross-check: proceed (0.84). No blocking findings surfaced.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:23` wraps render in `PorscheDesignSystemProvider`; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:47` asserts `screen.getByRole('button')` | `TestFromAC_ThemeToggle_1540` / `AC-1: renders an accessible button element` | PASS |
| AC-2 | `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:7` mocks `useTheme`; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:16` injects the toggle spy; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:53` clicks the button; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:55` asserts one call | `TestFromAC_ThemeToggle_1540` / `AC-2: clicking toggle button invokes useTheme().toggle exactly once` | PASS |
| AC-3 | `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:16` parameterizes mocked `theme`; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:31`-`36` capture `aria-label|textContent`; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:59` evaluates `light`, `dark`, and `auto`; `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:61` requires three distinct descriptors | `TestFromAC_ThemeToggle_1540` / `AC-3: button accessible name or content differs across light, dark, and auto theme states` | PASS |
- Proof sufficiency: AC-1 and AC-2 are directly falsifiable. AC-3 is softer than an exact semantic-label assertion, but it matches the current task wording, which requires distinct accessible name or content per state rather than exact state text.
- Safety/security: no blocking concerns. This is a test-only frontend change, adds no dependency, and follows existing cockpit test patterns.

## Observations
- `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:4` imports a component file that does not exist yet, which matches the builder's expected RED boundary. No `serve/cockpit/web/src/components/ThemeToggle.*` file was present during review.
- `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:7` uses the same `vi.mock` hook strategy already used in `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx:27`, `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx:67`, `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx:77`, `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:21`, `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:69`, and `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:75`.
- Mocking a not-yet-existing hook module is an established repo pattern; see `serve/cockpit/web/src/App.wiring.test.tsx:11`-`13`.
- Minor non-blocking softness: `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx:16`-`19` includes `isDark: theme === 'dark'`, but this suite never asserts on `isDark`, so it does not narrow the approved task contract.
2026-05-13T21:47:02+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A — no update needed | `serve/cockpit/README.md` mapped via convention. Grep: 0 ThemeToggle references. RED-phase test for non-existent component; no documented interface, command, or flag changed. Layer 1: confirmed absent. Layer 2: README covers stack, backend API, and launch commands — no contradictions introduced. |
| 2 | External attribution | Yes | N/A — already present | `sources/overview.md` already contains "## Theme Toggle UI Test Research (Task #1540)" with all 3 external sources (OneUptime blog, next-themes/issues/21, SO/72561602). No action required. |
| 3 | Research doc | Yes | N/A — linked | `.owlbear/research/1540-theme-toggle-ui-test-approach.md` exists and is linked from task body ("Research doc: .owlbear/research/1540-theme-toggle-ui-test-approach.md"). |
| 4 | Deletion detection | No | N/A | Builder added one file only (`ThemeToggle.test.tsx`). No deletions. |

### Verification Layers
- Layer 1 — grep structural: `ThemeToggle` absent from `serve/cockpit/README.md` (0 matches); `sources/overview.md` confirms task #1540 section present.
- Layer 2 — editorial: README documents launch, stack table, backend API surface, and engine allowlist — nothing that would drift from adding a RED-phase Vitest test file. Coherent and unaffected.

### Scratch Cleanup
- No `.owlbear/scratch/1540-*` files found. Nothing to delete.
2026-05-13T22:09:32+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: vitest 7 failed (all expected RED-phase: #1535, #1541, #1542, #1540) | 92 passed (99 files); pytest 208 failures (pre-existing, zero Python files in task commit); eslint clean for task file\n- regression verdict: PASS — no cross-task regressions caused by this task\n\n### Intent Verification\n- scope alignment: PASS (single file `serve/cockpit/web/src/__tests__/ThemeToggle.test.tsx` in cockpit frontend test domain)\n- purpose match: PASS (RED-phase tests encoding ThemeToggle contract for implementation task #1548)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 5/5\nAC lines specific, directly testable, parameterized. Challenger surfaced real issues (untestable status bar assertion, userEvent dep gap); architect accepted and refined ACs. Builder guidance added. Clean implementation path.\n\n### Commit Integrity\n- upstream commit presence: PASS (`42f25760` — `test: add RED tests for theme toggle UI (#1540, builder)`, 1 file changed, 63 insertions)\n- kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive