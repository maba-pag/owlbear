---
id: 1608
title: 'P2-01: Component complexity inventory'
status: archived
priority: important
created: 2026-05-16T03:36:20.585323+00:00
updated: 2026-05-17T19:36:08.980251+02:00
tags:
  - frontend
  - pds
  - phase-2
  - research
parent: 1590
depends_on:
  - 1603
ac:
  - 'Document classifies every raw interactive/display element as: simple swap, complex
    integration, or intentional native (with rationale for each intentional-native
    decision)'
  - Dependency graph produced showing which component migrations can proceed in 
    parallel
  - 'Inventory accounts for: buttons, headings, selects, lists, web-component elements,
    modals, and form controls'
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1590.

Research artifact: classify remaining raw HTML elements by migration complexity. Prerequisite for component migration tasks. Must preserve intentional native controls where tests assert specific DOM contracts (e.g., sidecar collapse button, theme toggle).

Scope: Inventory/analysis only.
Out of scope: Code changes, component replacement.

[[2026-05-17T16:51:46+02:00]]
## Planning

Single-task shortcut — one follow-up created from inventory findings.

| ID | Title | Status | Depends | Parent |
|----|-------|--------|---------|--------|
| #1634 | P2-12: Migrate unowned simple swaps (option→PSelectOption, anchor→PLinkPure) | research | #1608 | #1590 |

Scope: two simple element swaps (~15 LOC) discovered by inventory with no existing owning task.

[[2026-05-17T16:52:48+02:00]]
## Research
- Research doc: .owlbear/research/1608-component-complexity-inventory.md
- Sources: 6 studied, 5 high-relevance
- Recommendation: Inventory complete; 7 intentional-native buttons (all marked data-pds-exception), 0 remaining headings/modals/selects, 8 ul/li lists (no PDS list component), 9 raw p-* web-component tags assigned to #1616, 3 radio inputs + fieldset/legend assigned to #1618, 2 unowned simple swaps → follow-up #1634 created (confidence: 0.82)
- Challenge: proceed — revised down to 0.82 after challenger identified 4 gaps (missing legend, misclassified options, incorrect anchor routing, uneven native rationale); all accepted and incorporated
- Follow-up: #1634 (P2-12: unowned simple swaps)

[[2026-05-17T17:15:14+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Inventory/classification only — no code changes |
| Interface clarity | PASS | AC defines 3 verifiable outputs: classification document, dependency graph, element-type coverage |
| Dependency correctness | PASS | #1603 archived (completed); dependency satisfied |
| Module layering | N/A | Research artifact — no code changes |
| TDD compliance | PASS | proof_bundle=skip; no tests needed for documentation output |
| KISS/YAGNI | PASS | Minimal scope — inventory and analysis only, no implementation |
| Premise challenge | PASS | Inventory is prerequisite for parallel migration tasks; research doc demonstrates value |
| Pattern consistency | PASS | Follows research artifact pattern with structured sections, source table, and dependency graph |
| Security surface | N/A | No system boundaries — documentation only |
| Single domain | PASS | Frontend component classification only |

### Design Diverge
Skipped — single approach (systematic element scan + classification). No competing alternatives.

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: skip
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Non-impl tagging
Added `research` pass-through tag for test-writer pipeline compliance.

### Verdict: APPROVE
### Action Taken: Tagged `research` for pipeline pass-through. Advanced to todo.

[[2026-05-17T17:30:34+02:00]]
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Non-implementation task (tagged `research`) — inventory/classification artifact only, no testable Python interfaces.
- Passing through to builder.

[[2026-05-17T17:54:26+02:00]]
## Builder Notes
- Type: Non-implementation pass-through (`proof_bundle=skip`, `research` tagged)
- Files changed: None
- Implementation: No code changes required; scope is inventory/classification artifact only
- AC evidence summary:
  - AC1 satisfied by `.owlbear/research/1608-component-complexity-inventory.md` sections 3.1–3.8 with explicit classifications (simple swap / complex integration / intentional native) and rationale for intentional-native decisions.
  - AC2 satisfied by section 5 dependency graph showing parallel migration streams.
  - AC3 satisfied by documented coverage for buttons, headings, selects, lists, web-component elements, modals, and form controls.
- Test results: Not run (pass-through exception; proof bundle `skip`)
- Lint status: Not applicable (no code changes)
- Fixes applied: None

[[2026-05-17T18:22:33+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1, AC3 | The inventory claims there are no remaining raw modal/dialog surfaces, but the current frontend still contains raw `div[role="dialog"]` implementations. The artifact therefore does not classify every remaining raw interactive/display element and does not fully account for modals. | `.owlbear/research/1608-component-complexity-inventory.md:75`; `serve/cockpit/web/src/components/CleanupPanel.tsx:92`; `serve/cockpit/web/src/components/RepairPanel.tsx:72`; `serve/cockpit/web/src/components/DRStatusIndicator.tsx:92`; `serve/cockpit/web/src/components/HealthBadge.tsx:91` | in-progress |

- AC map:

| AC Line | Status | Evidence |
|---|---|---|
| AC1: Document classifies every raw interactive/display element as simple swap, complex integration, or intentional native (with rationale for each intentional-native decision) | FAIL | `.owlbear/research/1608-component-complexity-inventory.md:75` says no raw dialog patterns remain, but raw `div[role="dialog"]` still exist in `serve/cockpit/web/src/components/CleanupPanel.tsx:92`, `serve/cockpit/web/src/components/RepairPanel.tsx:72`, `serve/cockpit/web/src/components/DRStatusIndicator.tsx:92`, and `serve/cockpit/web/src/components/HealthBadge.tsx:91`. |
| AC2: Dependency graph produced showing which component migrations can proceed in parallel | PASS | `.owlbear/research/1608-component-complexity-inventory.md:105-118` provides the Phase 2 dependency graph and parallelism statement. |
| AC3: Inventory accounts for buttons, headings, selects, lists, web-component elements, modals, and form controls | FAIL | Buttons/headings/selects/lists/web-components/form-controls are covered in sections 3.1-3.5 and 3.7-3.8, but section 3.6 incorrectly states no raw dialogs remain while raw dialog surfaces are present at the source lines above. |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Update the inventory to classify the remaining raw `div[role="dialog"]` surfaces and correct the modal coverage claim, including any count or ownership changes implied by `CleanupPanel`, `RepairPanel`, `DRStatusIndicator`, and `HealthBadge`. | `.owlbear/research/1608-component-complexity-inventory.md` | AC1/AC3 mismatch from `.owlbear/research/1608-component-complexity-inventory.md:75` vs `serve/cockpit/web/src/components/CleanupPanel.tsx:92`, `serve/cockpit/web/src/components/RepairPanel.tsx:72`, `serve/cockpit/web/src/components/DRStatusIndicator.tsx:92`, `serve/cockpit/web/src/components/HealthBadge.tsx:91` |

## Observations
- AC2 is satisfied: the dependency graph exists and shows the Phase 2 migration streams in parallel at `.owlbear/research/1608-component-complexity-inventory.md:105-118`.
- Builder evidence was otherwise structured, but the modal coverage summary relied on the incorrect claim in section 3.6.

[[2026-05-17T18:52:17+02:00]]
## Builder Notes
- Implementation: Updated modal/dialog inventory in `.owlbear/research/1608-component-complexity-inventory.md` to classify all remaining dialog surfaces.
- Files changed: `.owlbear/research/1608-component-complexity-inventory.md`
- AC evidence summary:
  - AC1: Corrected section 3.6 to classify every modal/dialog surface: 3 PModal surfaces (already migrated), 2 unowned raw confirm dialogs (complex integration), 2 status-bar popovers (intentional native with rationale).
  - AC2: Dependency graph section unchanged and still present in section 5.
  - AC3: Modal coverage now explicitly accounts for raw `div[role="dialog"]` surfaces in CleanupPanel, RepairPanel, DRStatusIndicator, and HealthBadge.
- Ownership updates:
  - Recorded #1634 as created follow-up for simple swaps (option/anchor).
  - Added explicit note that one additional follow-up task is needed for CleanupPanel + RepairPanel confirm overlay migration.
- Test results: Not run (`proof_bundle=skip`, non-implementation/documentation artifact correction).
- Lint status: Not applicable (no source/test code changes).
- Fixes applied: Replaced incorrect "no raw dialogs remain" claim and aligned recommendation/follow-up sections with actual dialog inventory.
- Commit: `b087ef41` (`docs: fix modal/dialog inventory classification (#1608, builder)`).

[[2026-05-17T19:11:53+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1608 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence sufficiency: Sufficient for `proof_bundle=skip`; builder changed only `.owlbear/research/1608-component-complexity-inventory.md`, and direct source scans of `serve/cockpit/web/src/components/**/*.tsx` and `serve/cockpit/web/src/*.tsx` matched the artifact's in-scope inventory without further omissions.

| AC Line | Status | Evidence |
|---|---|---|
| AC1: Document classifies every raw interactive/display element as simple swap, complex integration, or intentional native (with rationale for each intentional-native decision) | PASS | Inventory sections at `.owlbear/research/1608-component-complexity-inventory.md:25`, `:43`, `:51`, `:63`, `:75`, `:87`, and `:97` align with current source surfaces found at `serve/cockpit/web/src/Shell.tsx:266`, `:303`, `:314`, `:342`, `:343`, `:408`, `:440`, `:441`, `:506`; `serve/cockpit/web/src/KanbanBoard.tsx:278`; `serve/cockpit/web/src/components/ThemeToggle.tsx:23`; `serve/cockpit/web/src/components/CleanupPanel.tsx:92`, `:148`, `:179`; `serve/cockpit/web/src/components/RepairPanel.tsx:72`, `:92`, `:132`; `serve/cockpit/web/src/components/DRStatusIndicator.tsx:76`, `:92`, `:112`; `serve/cockpit/web/src/components/HealthBadge.tsx:75`, `:91`, `:111`; `serve/cockpit/web/src/components/DecisionViewport.tsx:49`, `:52`; `serve/cockpit/web/src/components/ArchivalModal.tsx:351`, `:361`, `:377`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:233`; `serve/cockpit/web/src/components/ResolveModal.tsx:241`, `:242`, `:244`, `:245`, `:257`, `:258`, `:270`, `:271`; `serve/cockpit/web/src/components/DetailTab.tsx:196`; and `serve/cockpit/web/src/components/Card.tsx:143`. |
| AC2: Dependency graph produced showing which component migrations can proceed in parallel | PASS | Dependency graph present at `.owlbear/research/1608-component-complexity-inventory.md:117`, with follow-up routing documented at `:132`. |
| AC3: Inventory accounts for buttons, headings, selects, lists, web-component elements, modals, and form controls | PASS | Sections 3.1-3.8 at `.owlbear/research/1608-component-complexity-inventory.md:25-97` cover each required category, and the source-only scan matched that category set exactly. |

## Observations
- Section 6 documents one further unowned follow-up for CleanupPanel/RepairPanel confirm-overlay migration at `.owlbear/research/1608-component-complexity-inventory.md:135`, but kanban task searches for `CleanupPanel`, `RepairPanel`, `dialog`, and `modal` returned only #1608. This is not AC-blocking for the inventory artifact, but board follow-through is still needed before archival.

[[2026-05-17T19:19:51+02:00]]
## Docs Gate

**Verdict:** PASS — no docs impact; advance to done.

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | Only changed file is `.owlbear/research/1608-component-complexity-inventory.md` — a research artifact; maps to no `serve/{pkg}/README.md` target per convention mapping. |
| 2. External Attribution | Already present | `sources/overview.md` already contains a task #1608 section (PDS v4 React wrapper exports + PDS v4 component overview) added prior to this gate pass. Verified at line ~4857. |
| 3. Research Doc | Linked ✓ | Task body contains explicit link: "Research doc: .owlbear/research/1608-component-complexity-inventory.md". File exists and is complete. |
| 4. Deletion Detection | N/A | No files deleted. Only `.owlbear/research/1608-component-complexity-inventory.md` was modified (builder corrected modal/dialog classification). |

### Layer 1 (grep)
- Grep confirmed `## Component Complexity Inventory (Task #1608)` is present in `sources/overview.md` exactly once (at the existing pre-task entry; transient duplicate removed).
- Research doc verified to exist and contain task-id reference.

### Layer 2 (editorial)
- Research doc sections 3.1–3.8 are internally coherent, each section closes with a classification verdict.
- Section 3.6 (Modals) corrected by builder: all seven dialog surfaces classified; two confirm-overlay `div[role="dialog"]` correctly marked as unowned complex integrations.
- Section 6 follow-up list is consistent with task body: #1634 created for simple swaps; one additional follow-up noted for CleanupPanel/RepairPanel confirm overlays.
- No contradictions between artifact and review evidence.

### Files Modified
None.

### Scratch Cleanup
No `.owlbear/scratch/1608-*` files found.

[[2026-05-17T19:36:08+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4642 passed, 19 failed (all pre-existing background debt outside task domain), 14 skipped, lint clean
- Task domain: `.owlbear/research/` → skip (docs/config only) per domain mapping; zero failures attributable to #1608
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (only `.owlbear/research/1608-component-complexity-inventory.md` changed — correct research domain)
- purpose match: PASS (inventory classifies raw HTML elements per AC; modal gap corrected in builder cycle 2)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines were specific and verifiable. Reviewer caught a real modal omission from AC1/AC3, proving the criteria were usefully precise. Minor gap: no AC line requiring explicit follow-up task creation for discovered items (pipeline protocol covers this generically).

### Commit Integrity
- upstream commit presence: PASS (`ffbd729c` researcher, `b087ef41` builder — both properly attributed with #1608)
- kanban commit packaging: pending (this audit cycle)

### Research Task Verification
- Research doc exists: `.owlbear/research/1608-component-complexity-inventory.md` ✓
- Follow-up #1634 created at `research` status, references #1608 ✓
- Additional follow-up #1635 created during audit for CleanupPanel/RepairPanel confirm-overlay migration (documented in research doc section 6 but missing from board)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
