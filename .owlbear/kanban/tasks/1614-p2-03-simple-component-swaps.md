---
id: 1614
title: 'P2-03: Simple component swaps'
status: review
priority: important
created: 2026-05-16T03:37:02.195428+00:00
updated: 2026-05-16T20:31:29.445914+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on: []
ac:
  - Zero raw `<select>` elements in source `.tsx` files outside `__tests__/`
  - ActivityTab.tsx session-row button, DRStatusIndicator.tsx resolve-button, 
    and ErrorBoundary.tsx retry button replaced with `PButton`; existing 
    `data-testid` attributes and `onClick` handlers preserved
  - Shell.tsx `<h1>`, both Shell.tsx `<h2>` elements, DetailTab.tsx `<h3>`, and 
    ErrorBoundary.tsx `<h3>` replaced with `<PHeading>` with matching `tag` prop
  - Raw `<button>` in source `.tsx` files outside `__tests__/` remains only 
    where element has `data-pds-exception` attribute or is the Shell.tsx 
    sidecar-collapse button (aria-expanded pattern)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Replace raw HTML: `<button>` → `PButton`, `<h1>`-`<h6>` → `PHeading`/`PText`, `<select>` → `PSelect`, raw web-components → React wrappers. Preserve intentional native controls where tests assert specific DOM contracts.

Scope: Simple swaps only.
Out of scope: Cards, sidecar IA, modals, filter panel.

[[2026-05-16T17:30:24+02:00]]
## Research
- Research doc: .owlbear/research/1614-simple-component-swaps.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Narrow scope to true simple swaps — 3 buttons → PButton, 5 headings → PHeading. Raw PDS web components (p-sheet, p-tabs, p-tabs-item) belong to sidecar IA (#1616) and are NOT simple swaps due to tabChange→onUpdate event contract change. 5 buttons stay as intentional native (data-pds-exception). Zero raw selects exist (AC-1 already met). (confidence: 0.85)
- Follow-up tasks created: none — sibling tasks already cover deferred scope
- Decision requests: none

## Challenge Results
- Challenger: proceed (revised from block after scope narrowing)
- Confidence in original: 0.85 (revised from 0.90)
- Key challenges: (1) AC-2 names p-button/p-icon but neither exists as raw web-component tags — actual raw PDS tags are p-sheet/p-tabs which belong to sibling tasks; (2) Shell p-tabs uses deprecated tabChange event, not a simple swap; (3) Scope collapse into sidecar IA territory
- Researcher response: accepted — narrowed scope to exclude all Shell web-component tags, deferred to #1616

[[2026-05-16T18:05:56+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: swap 3 buttons + 5 headings to PDS React wrappers |
| Interface clarity | PASS (after refinement) | AC-2 originally named non-existent `<p-button>`/`<p-icon>` tags; rewritten to target actual elements with contract preservation |
| Dependency correctness | PASS | No blocking deps; #1609 (test task) archived as deprecated — test-writer will process at todo |
| Module layering | PASS | Frontend-only, no cross-layer concerns |
| TDD compliance | PASS | Proof bundle behavioral → test-writer writes tests at todo; PdsMigration.test.tsx already partially covers |
| KISS/YAGNI | PASS | Minimal scope after research narrowing (3 buttons + 5 headings) |
| Premise challenge | PASS | PDS migration is user-directed; PButton already imported in 9 files |
| Pattern consistency | PASS | PButton widely adopted; PHeading used in ResolveModal — follows existing patterns |
| Security surface | PASS | UI component swaps only, no new system boundaries |
| Single domain | PASS | Frontend/cockpit only |

### Challenge Results
- Challenger: reconsider (confidence 0.72)
- Key challenges: (1) brittle line-number coordinates in AC; (2) source-vs-DOM verification scope ambiguity; (3) contract preservation gap for ActivityTab session-row; (4) behavioral proof vs inventory-style AC mismatch
- Architect response: accepted challenges 1-3, revised AC to remove line numbers, add explicit source-file scope, and require data-testid/onClick preservation. Challenge 4 (proof model mismatch) rebutted: component-swap AC IS testable behavior — render component, assert PButton present, assert no unaccounted raw buttons.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### AC Refinement Applied
- AC-1: Kept (regression guard, already satisfied but prevents regressions)
- AC-2: Rewritten — was \"PDS web-component elements (<p-button>, <p-icon>) replaced\" (elements don't exist). Now: specific 3 buttons → PButton with contract preservation
- AC-3: Added — 5 headings → PHeading with tag prop
- AC-4: Rewritten — explicit intentional-native criteria (data-pds-exception OR sidecar-collapse aria pattern)

### Design Diverge
- Skipped: single clear approach (1:1 element swap to established PDS React wrappers)

### Verdict: APPROVE (after refinement)
### Action Taken: Refined AC to match research findings, removed phantom elements, added contract preservation requirement. Advanced to todo.

[[2026-05-16T18:52:53+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/PdsSimpleSwaps1614.test.tsx`
- Commit: f6b6314b

### Test classes
| Class | AC | Tests | Category |
|---|---|---|---|
| TestFromAC_SimpleSwaps_ActivityTabSessionRow | AC-2, AC-4 | 5 | happy, error, boundary |
| TestFromAC_SimpleSwaps_DRResolveButton | AC-2, AC-4 | 5 | happy, error |
| TestFromAC_SimpleSwaps_ErrorBoundaryRetry | AC-2, AC-4 | 3 | happy, error |
| TestFromAC_SimpleSwaps_ShellH1 | AC-3 | 4 | happy, error |
| TestFromAC_SimpleSwaps_ShellH2 | AC-3 | 4 | happy, error |
| TestFromAC_SimpleSwaps_DetailTabH3 | AC-3 | 4 | happy, error |
| TestFromAC_SimpleSwaps_ErrorBoundaryH3 | AC-3 | 4 | happy, error |

**Total: 29 tests, all FAIL** (verified via `npx vitest run`, exit 1, 29 failed 0 passed)

### AC coverage
| AC | Tests | Notes |
|---|---|---|
| AC-1 (zero raw `<select>`) | none | Pre-satisfied regression guard — all checks would be green. No RED tests possible. |
| AC-2 (buttons → PButton) | 13 tests across 3 classes | session-row, resolve-button, retry all checked for p-button presence, no native button, data-testid preservation, onClick contract |
| AC-3 (headings → PHeading) | 16 tests across 4 classes | h1/h2/h3 for Shell/DetailTab/ErrorBoundary — p-heading presence, tag attribute, no raw heading, content |
| AC-4 (intentional native policy) | embedded in AC-2 classes (3 tests) | no unexcepted raw buttons in ActivityTab+sessions, DRStatusIndicator popover, ErrorBoundary error state |

### Mocking strategy
- `usePollingFetch` mocked globally; sessions injected via captured `onSuccess` callback in `act()`
- `useSSEEvent` mocked to return closed/null
- `react-markdown`, `remark-gfm`, `rehype-sanitize` mocked for DetailTab rendering
- Shell uses `vi.stubGlobal('fetch', ...)` as additional safety net

[[2026-05-16T19:51:09+02:00]]
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/components/ActivityTab.tsx
  - serve/cockpit/web/src/components/DRStatusIndicator.tsx
  - serve/cockpit/web/src/components/ErrorBoundary.tsx
  - serve/cockpit/web/src/components/DetailTab.tsx
  - serve/cockpit/web/src/Shell.tsx
- Implementation summary:
  - Replaced ActivityTab session-row native button with `PButton` while preserving `data-testid="session-row"` and `onClick` navigation contract.
  - Replaced DRStatusIndicator popover `resolve-button` native button with `PButton` preserving `data-testid` and click handler.
  - Replaced ErrorBoundary fallback heading and retry control with `PHeading` and `PButton`.
  - Replaced Shell status-bar `<h1>` with `PHeading` and ensured sidecar heading renders as `p-heading` with `tag="h2"` in both desktop and mobile paths.
  - Ensured DetailTab Actions heading renders as `p-heading` with `tag="h3"`.
- Test results (quality-runner):
  - RED verification (pre-change): 20 failed, 6 passed, lint clean (partial pre-existing implementation detected; investigated before edits).
  - Scoped GREEN verification: `serve/cockpit/web/src/__tests__/PdsSimpleSwaps1614.test.tsx` -> 29 passed, 0 failed, 0 skipped.
  - Durable regression check: `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx` -> 78 passed, 0 failed, 3 skipped.
- Lint status:
  - ESLint clean for changed files + task test (`clean: true`, no violations).
- Coverage:
  - Frontend run for this task did not provide coverage metrics (`none` from quality-runner); behavioral test and durable regression evidence both green.
- Evidence summary:
  - quality-runner environment fallback applied once per protocol due to initial `document is not defined`; retry with frontend hint succeeded.
  - Final scoped test + lint gate passed with zero failures.
- Commit:
  - b2de7a9abd3da8ad2eb88b1d7f32465a19ad5896
  - feat: swap simple buttons and headings to PDS wrappers (#1614, builder)
