---
id: 1634
title: 'P2-12: Migrate unowned simple swaps (option→PSelectOption, anchor→PLinkPure)'
status: archived
priority: medium
created: 2026-05-17T16:51:40.816862+02:00
updated: 2026-05-17T21:02:38.938504+02:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
ac:
  - 'AC1: TaskFieldsEditor `<PSelect>` renders `PSelectOption` children (no raw `<option>`
    elements) — assert `p-select-option` inside `p-select` plus zero native `OPTION`
    elements (FilterPanel falsifiability pattern from #1617)'
  - 'AC2: DecisionViewport task reference renders as `<PLinkPure href="..." icon="none">`
    using host-href pattern — renders `p-link-pure` custom element in DOM with `data-testid`
    and `onClick` preserved on the outer element; `icon="none"` suppresses default
    arrow'
  - "AC3: DecisionViewport.test.tsx existing assertions updated — clickable-element
    test (line ~155, checks tagName) and keyboard-reachability test (line ~289, hardcodes
    `tagName === 'a'`) both accept `p-link-pure`; `href` attribute check preserved
    on custom element"
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Discovered by #1608 (component complexity inventory): two raw HTML elements have no owning Phase 2 task.

### Scope

1. **TaskFieldsEditor.tsx:233** — `<option>` inside `<PSelect>` → replace with `PSelectOption` (follows #1617 FilterPanel pattern)
2. **DecisionViewport.tsx:52** — `<a>` task reference link → replace with `PLinkPure` (available in PDS React wrappers)

~15 LOC combined. Both are direct element swaps with no layout or state implications.

[[2026-05-17T19:46:47+02:00]]
## Research
- Research doc: .owlbear/research/1634-unowned-simple-swaps.md
- Sources: 6 studied, 5 high-relevance
- Recommendation: proceed with both swaps (confidence: 0.85)

Key findings:
1. PSelectOption swap is trivial — exact FilterPanel pattern
2. PLinkPure available in PDS React v4.1.0, but 2 DecisionViewport test assertions hardcode `<a>` tag check and will break — builder must update to accept `p-link-pure`
3. PLinkPure slotted anchor pattern (`<PLinkPure><a ...>`) is an alternative that preserves test compatibility — builder should evaluate both approaches

[[2026-05-17T19:47:01+02:00]]
## Research
- Research doc: .owlbear/research/1634-unowned-simple-swaps.md
- Sources: 6 studied, 5 high-relevance
- Recommendation: proceed with both swaps (confidence: 0.85)

Key findings:
1. PSelectOption swap — trivial, exact FilterPanel pattern from #1617
2. PLinkPure — available in PDS React v4.1.0; 2 test assertions in DecisionViewport.test.tsx hardcode `<a>` tag check (lines ~157, ~289) and will break
3. Slotted anchor pattern (`<PLinkPure><a ...>`) documented alternative — builder should evaluate
4. No follow-up tasks needed — #1634 is the implementation task

Commit: 27a9a57a

[[2026-05-17T20:09:04+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Two co-discovered PDS migration swaps (~15 LOC total) under same parent/motivation; splitting would cost more pipeline overhead than the implementation |
| Interface clarity | PASS | Inputs/outputs clear: element swaps with preserved props (href, onClick, data-testid) |
| Dependency correctness | PASS | #1608 archived (completed) |
| Module layering | PASS | Frontend-only, same component layer |
| TDD compliance | PASS | Test-writer will write RED tests; existing FilterPanel test pattern provides template |
| KISS/YAGNI | PASS | Minimal scope, host-href pattern (simplest PLinkPure usage), no new abstractions |
| Premise challenge | PASS | Raw HTML in PDS components is a known migration debt; PSelectOption and PLinkPure are direct PDS replacements |
| Pattern consistency | PASS | Follows established FilterPanel pattern (#1617) for PSelectOption; PLinkPure host-href matches PDS React idiom |
| Security surface | PASS | No new system boundaries; href is fragment-only (#task-{id}) |
| Single domain | PASS | Frontend PDS migration only |

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Findings addressed:
  - AC test-impact completeness: ACCEPTED — refined AC3 to name both failing assertions (clickable-element line ~155 AND keyboard-reachability line ~289)
  - PLinkPure icon default: ACCEPTED — AC2 now specifies `icon=\"none\"` to suppress default arrow-right
  - Host-href vs slotted-anchor ambiguity: RESOLVED — AC2 mandates host-href pattern (simpler, KISS-aligned)
  - Atomicity (two file-level swaps): REBUTTED — 15 LOC total under same parent/discovery/motivation; split pipeline overhead exceeds implementation cost
  - Test ownership gap: ACKNOWLEDGED — test-writer will write new RED tests following FilterPanel falsifiability pattern; AC1 explicitly requires zero-native-OPTION guard
- Architect response: revised AC per valid findings; rebutted atomicity challenge

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — only one valid approach after host-href vs slotted-anchor resolved to host-href (simpler, fewer test ownership implications)

### Verdict: APPROVE
### Action Taken: Refined AC (test-impact completeness, icon suppression, host-href decision), assigned proof bundle `smoke`, advanced to todo

[[2026-05-17T20:16:05+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx
- Classes: TestFromAC_PdsSimpleSwaps_1634_PSelectOption, TestFromAC_PdsSimpleSwaps_1634_PLinkPure, TestFromAC_PdsSimpleSwaps_1634_KeyboardReachability
- Tests per category: happy 3, edge 0, error 0, boundary 0
- Total: 3 tests, all FAIL
- ESLint: clean

| AC | Tests | Coverage |
|----|-------|----------|
| AC1: PSelectOption inside PSelect, no native OPTION | 1 | p-select-option present + nativeCount === 0 |
| AC2: PLinkPure host-href, icon="none", data-testid, onClick | 1 | tagName, href, icon attr, callback |
| AC3: Keyboard-reachability accepts p-link-pure + href on host | 1 | tagName + href for 2 items |

Proof bundle: smoke — 1 smoke test per AC line.

[[2026-05-17T20:25:17+02:00]]
## Builder Notes
### Files Changed
- serve/cockpit/web/src/components/TaskFieldsEditor.tsx
- serve/cockpit/web/src/components/DecisionViewport.tsx
- serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx

### Plan (Step 1)
- Replace native `<option>` children in `TaskFieldsEditor` `PSelect` with `PSelectOption`.
- Replace native `<a>` task reference in `DecisionViewport` with `PLinkPure` host-href pattern (`href`, `icon="none"`, existing `data-testid`, existing click handler).
- Update existing `DecisionViewport.test.tsx` clickable-element and keyboard-reachability assertions to accept `p-link-pure` while preserving host `href` checks.
- Risk considered: jsdom host attribute visibility for PDS custom-element props (`href`/`icon`) could differ from native-anchor attribute behavior.

### RED Verification (quality-runner)
- Task-scoped test: `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx`
- Result: 0 passed / 3 failed (all `TestFromAC_*` classes failed as expected)
- Lint: clean

### Module Baseline (quality-runner)
- `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx`
- `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`
- Result: 35 passed / 0 failed
- Lint: clean

### Implementation Applied
- `TaskFieldsEditor.tsx`: imported `PSelectOption` and replaced mapped native `<option>` nodes with `<PSelectOption>`.
- `DecisionViewport.tsx`: imported `PLinkPure`; replaced `<a>` with `<PLinkPure href="#task-{id}" icon="none" ...>` preserving `data-testid` and `onClick` callback behavior.
- `DecisionViewport.tsx`: added host-attribute normalization in `ref` (`href`, `icon`) to keep custom-element host assertions deterministic in jsdom.
- `DecisionViewport.test.tsx`: updated two existing assertions per AC3:
  - clickable-element test now accepts `p-link-pure`
  - keyboard-reachability test now accepts `a` or `p-link-pure` and still asserts host `href`

### GREEN Verification (quality-runner)
- Scoped tests:
  - `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx`
  - `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx`
  - `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx`
- Final result: 38 passed / 0 failed / 0 skipped
- Lint: clean (`eslint` clean on touched files)
- Coverage: not reported by scoped runner for this frontend smoke bundle (N/A)

### Quality-Runner Environment Fallback
- First final verification run failed with environment error (`HTMLElement/document is not defined`).
- Retried once with required hint: `frontend — cd serve/cockpit/web before all commands`.
- Retry succeeded (38 passed).

### Commit
- `feat: migrate simple pds swaps (#1634, builder)`
- Hash: `1ad05673`

### Evidence Summary
- AC1 satisfied: `p-select-option` replaces native `option` in `TaskFieldsEditor`.
- AC2 satisfied: `DecisionViewport` task reference renders as `p-link-pure` host with `href`, `icon="none"`, `data-testid`, and preserved click callback.
- AC3 satisfied: existing durable test assertions updated for `p-link-pure` and host-`href` preservation.

[[2026-05-17T20:35:53+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1634 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: quality-runner packet in Builder Notes reports 38 passed / 0 failed / 0 skipped across the task smoke tests plus DecisionViewport and SaveConfirmed durable suites; lint clean; smoke bundle matches the architect-assigned proof bundle.
- Independent checks: editor diagnostics report no errors in `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`, `serve/cockpit/web/src/components/DecisionViewport.tsx`, `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx`, or `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1: TaskFieldsEditor `<PSelect>` renders `PSelectOption` children with zero native `<option>` elements | `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:234` maps every priority to `PSelectOption`, matching the established FilterPanel pattern | `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx:136` proves `p-select-option` exists and `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx:146` asserts zero native `OPTION` children | PASS |
| AC2: DecisionViewport task reference uses `PLinkPure` host-href pattern with `icon="none"`, `data-testid`, and preserved `onClick` | `serve/cockpit/web/src/components/DecisionViewport.tsx:52-62` renders `PLinkPure` with `href`, `icon="none"`, `data-testid`, host-attribute normalization for `href`/`icon`, and preserved `onItemClick(item.id)` | `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx:158` asserts `p-link-pure`, host `href`, `icon="none"`, and click callback behavior | PASS |
| AC3: existing DecisionViewport assertions accept `p-link-pure` and preserve host `href` checks | `serve/cockpit/web/src/components/DecisionViewport.tsx:52-62` is the migrated surface consumed by the durable tests | `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx:158` updates the clickable-element assertion to accept `p-link-pure`; `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx:292` updates the keyboard-reachability assertion to accept `p-link-pure` while preserving host `href`; `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx:189` provides the exact-task regression guard that the current implementation is `p-link-pure` | PASS |

- Blocking findings: none.

## Observations
- `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx:292` remains intentionally permissive (`a` or `p-link-pure`). That is acceptable here because `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx:189` is the exact regression guard for the migration contract.
- Git dirty-tree overlap could not be independently checked with the available tool surface; review scope used the builder file list plus on-disk inspection of the touched files and proof surface.

[[2026-05-17T20:47:16+02:00]]
## Docs Gate

### Checklist

**Item 1: README Verification** — PASS
- Convention mapping: `serve/cockpit/web/src/**` → `serve/cockpit/README.md`
- Added #1634 bullet after #1628 in the Frontend Surface section: PSelectOption swap in TaskFieldsEditor, PLinkPure host-href swap in DecisionViewport, updated DecisionViewport.test.tsx assertions, test counts (3 task-scoped + 35 durable), and cross-references to #1608 and #1617.
- Layer 1: `#1634` greps to 2 matches in README (lines 273 and 281). ✓
- Layer 2: paragraph is style-consistent with sibling bullets (#1614, #1617), factually grounded in Review Evidence. ✓

**Item 2: External Attribution** — PASS
- 1 external source used in research (PDS v3 link-pure examples). Added "Unowned Simple Swaps Research (Task #1634)" section to `.owlbear/sources/overview.md` (line 313).

**Item 3: Research Doc** — N/A
- `.owlbear/research/1634-unowned-simple-swaps.md` exists and is linked from the task body (two `## Research` entries). No action needed.

**Item 4: Deletion Detection** — N/A
- No source files deleted. Only modifications to `TaskFieldsEditor.tsx`, `DecisionViewport.tsx`, `DecisionViewport.test.tsx` and addition of task-scoped test file.

### Files Updated
- `serve/cockpit/README.md` — added #1634 bullet (lines 273–287)
- `.owlbear/sources/overview.md` — added Task #1634 sources section

### Scratch Cleanup
- No `1634-*` scratch files found; nothing to clean.

### Commit
- `docs: add #1634 pds simple swaps to cockpit readme and sources (#1634, doc-writer)`
- Hash: `1ca5a540`

[[2026-05-17T21:02:38+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4642 passed, 258 failed (all pre-existing background debt outside serve/cockpit/web/ domain), 14 skipped; vitest env error in App.wiring.test.tsx is pre-existing
- Lint: ruff clean, ESLint 0 violations
- regression verdict: PASS (no task-attributable failures)

### Intent Verification
- scope alignment: PASS (builder commit 1ad05673 touched 3 files, all in serve/cockpit/web/src/ frontend PDS migration domain)
- purpose match: PASS (native option replaced with PSelectOption, native anchor replaced with PLinkPure, existing test assertions updated)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
AC lines are specific: named components, patterns (host-href), attributes (icon=\"none\", data-testid, onClick), exact test-line references (~155, ~289). Challenger ran at 0.68 confidence; architect addressed all valid findings (icon suppression, host-href decision, test-impact completeness). Clean implementation path.

### Commit Integrity
- upstream commit presence: PASS (test-writer cb4f354d, builder 1ad05673, doc-writer 1ca5a540 all in HEAD)
- kanban commit packaging: pending (this archive cycle)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
