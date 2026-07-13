---
id: 1553
title: 'P4-03: PDS component dark-mode compatibility verification'
status: archived
priority: medium
created: 2026-05-13T18:43:53.233186+00:00
updated: 2026-05-14T06:54:56.324628+00:00
tags:
  - phase-4
  - scope:cockpit
  - theme
  - test
  - frontend
parent: 1534
depends_on:
  - 1545
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Verify PDS web components (buttons, tabs, banners) respond to `data-theme` attribute changes on `<html>`; document any components needing additional treatment
- **Out:** PDS component replacement or adoption (out of scope per brief)

## Acceptance Criteria

- AC-1: Researcher determines whether PDS web components (PButton, PText, PBanner, PSpinner, PHeading, PInlineNotification, PInputText, PSelect, PMultiSelect, PMultiSelectOption, PTextarea, p-tabs, p-tabs-item) change visual styling when `document.documentElement.dataset.theme` toggles between `'light'` and `'dark'`. Task body contains a verification finding section documenting the result (positive or negative) and the method used.
- AC-2: If any PDS component does not respond to `data-theme`, the task body lists each affected component and the CSS/JS treatment required to enable dark-mode support. A follow-up implementation task exists at `research` status if bridge work is needed.

Proof bundle: skip

## AC-2: Components needing additional treatment

**Finding: ALL 14 PDS components need the same treatment** — none respond to `data-theme` because PDS v4 uses CSS `color-scheme` property via `.scheme-*` classes, not `data-theme` attributes.

**Root cause:** PDS v4 removed the per-component `theme` prop. Components now inherit `color-scheme` from ancestor elements. Our Cockpit sets `data-theme` on `<html>` but never sets `color-scheme` or `.scheme-*` classes.

**Components affected (all used PDS components):** PButton, PText, PSelect, PInputText, PTextarea, PSpinner, PMultiSelect, PMultiSelectOption, PIcon, PHeading, PInlineNotification, p-tabs, p-tabs-item, PBanner.

**Required treatment (uniform for all):**
1. Import PDS v4 mandatory global styles CSS
2. Bridge `data-theme` ↔ `.scheme-*` class in `theme-bootstrap.js` and `useTheme.ts`

No per-component CSS overrides needed — PDS v4 handles dark mode uniformly via `color-scheme` inheritance once the bridge is in place.

## Research
- Research doc: .owlbear/research/1553-pds-dark-mode-compat.md
- Sources: 7 studied, 5 high-relevance
- Key finding: PDS v4 components do NOT respond to `data-theme` — they use CSS `color-scheme` via `.scheme-*` classes. Our Cockpit never sets these, so PDS components are stuck in light mode.
- Recommendation: Bridge approach — set both `data-theme` and `.scheme-*` class on `<html>` (confidence: 0.85)
- All 14 PDS components will work correctly once bridge is implemented; no per-component CSS needed
- Follow-up: #1555 (bridge implementation) created at research status
- Challenge: skipped (T1 — integration fix, no architecture change)
2026-05-14T06:03:24+00:00
## Architecture Review

**Verdict:** APPROVED (after REFINE)
**Proof bundle:** skip

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1 | REFINED — original said "confirms PDS web components switch styling" which frames a positive result. Research proved the OPPOSITE (they don't switch). Rewrote to "determines whether ... change visual styling" with "(positive or negative)" result path. Enumerated all 13 used PDS components explicitly (B3 compliance). Added observable artifact requirement: "task body contains a verification finding section." | Rewrote in task body |
| AC-2 | REFINED — added "A follow-up implementation task exists at `research` status if bridge work is needed" to make the follow-up (#1555) an inspectable artifact rather than implicit side-effect. P2: task body + follow-up task. P3: artifact inspection. | Tightened in task body |

### Proof-Bundle Validation

- Planner assignment: `behavioral`
- Final bundle: `skip` (de-escalated)
- Rationale: This is a verification/documentation task producing no testable code. The deliverable is documentation in the task body + a follow-up task. No code changes, no tests to write.
- Test-writer: SKIP (pass-through via `test` tag)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Verify PDS component dark-mode compat, document findings — one concern |
| Interface clarity | N/A | No code interfaces; deliverable is task body documentation |
| Dependency correctness | PASS | #1545 (theme bootstrap) archived/completed ✓ |
| Module layering | N/A | No code changes |
| TDD compliance | N/A | Non-implementation task (tagged `test` for pass-through) |
| KISS/YAGNI | PASS | Minimal scope — verify and document |
| Premise challenge | PASS | Verification needed before bridge implementation (#1555) can proceed |
| Pattern consistency | N/A | No code changes |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Codebase Verification

Confirmed PDS component usage via grep of `serve/cockpit/web/src/`:
- **React imports:** PButton (10 components), PText (5), PBanner (1), PSpinner (2), PHeading (1), PInlineNotification (1), PInputText (1), PSelect (2), PMultiSelect (1), PMultiSelectOption (1), PTextarea (2)
- **Custom elements:** p-tabs, p-tabs-item (Shell.tsx)
- **Indirect:** p-icon (rendered by PButton internally, registered in main.tsx)
- **No `.scheme-*` classes or `color-scheme` property** found anywhere except `@media` fallback in `tokens.css:83`
- Research core finding confirmed: PDS v4 components do NOT respond to `data-theme`

### Architecture Notes

- Research finding is architecturally sound. PDS v4 migrated from per-component `theme` prop to CSS `color-scheme` inheritance via `.scheme-*` utility classes.
- The bridge approach (set `.scheme-dark`/`.scheme-light` alongside `data-theme`) is the correct remediation — documented in follow-up #1555.
- No per-component CSS overrides needed; uniform bridge handles all PDS components.

### Dependency Analysis

- #1545 (theme bootstrap): archived/completed ✓
- #1555 (bridge implementation): exists at `research` status, depends on #1553 ✓

### Challenge Results

- Skipped per Step 2.1 (finalized proof bundle = `skip`)

### Non-Implementation Tagging

- Task tagged `test` — sufficient for test-writer pass-through ✓
2026-05-14T06:06:36+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Architect confirmed: "Test-writer: SKIP (pass-through via `test` tag)" and "Proof bundle: skip".
- Deliverable is task body documentation (research findings) + follow-up task #1555, not testable code.
- Passing through to builder.
2026-05-14T06:27:35+00:00
## Builder Notes
- Implementation: no code changes (non-implementation pass-through task).
- Proof bundle: skip (validated in task body and Architecture Review section).
- AC evidence: AC-1 and AC-2 are already satisfied by the documented verification findings in this task body, including the method, affected component list, and required treatment.
- Dependency evidence: follow-up implementation task #1555 exists at research status and depends on #1553.
- Tests: not applicable for this task type (Test-Writer marked non-implementation; no TestFromAC gate required under proof bundle skip).
- Lint/Coverage: not applicable (no source/test changes in this builder pass).
- Approach: verified completion artifacts and routed task forward without introducing unnecessary edits.
2026-05-14T06:38:00+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1553 -> docs | AC mapped to artifact evidence and dependency evidence is sufficient.
- Builder evidence review: Proof bundle `skip` is consistent with this non-implementation verification task. Builder notes, the research artifact, and direct source inspection are internally consistent; no independent test or lint rerun was required.
- AC evidence map:

| AC Line | Code / Artifact Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 | Task body documents the negative result, root cause, affected surface, and remediation path. The research artifact records the source-study method and findings at `.owlbear/research/1553-pds-dark-mode-compat.md:10`, `.owlbear/research/1553-pds-dark-mode-compat.md:24`, `.owlbear/research/1553-pds-dark-mode-compat.md:35`, and `.owlbear/research/1553-pds-dark-mode-compat.md:47`. Direct source inspection confirms the current theme flow only writes `document.documentElement.dataset.theme` in `serve/cockpit/web/public/theme-bootstrap.js:11` and `serve/cockpit/web/src/hooks/useTheme.ts:26`, `:56`, `:68`; local tokens are keyed from `[data-theme="dark"]` and OS fallback in `serve/cockpit/web/src/tokens.css:56` and `:83`; repo search over `serve/cockpit/web/src/**` and `serve/cockpit/web/public/**` found no `.scheme-dark` / `.scheme-light` hooks. | Proof bundle `skip`; artifact review is the required proof for this documentation task, and the builder evidence is sufficient. | PASS |
| AC-2 | Task body lists the affected components and required bridge treatment. Current frontend usage of PDS provider / custom elements is present in `serve/cockpit/web/src/App.tsx:2`, `:10` and `serve/cockpit/web/src/main.tsx:4`, `:7`, `:32`, `:37`, supporting the scope of the finding. Follow-up task `#1555` exists at `research` status and depends on `#1553`, satisfying the remediation-task requirement. | Artifact review sufficient; implementation work is explicitly deferred to follow-up `#1555`. | PASS |
- Safety & security: No new executable behavior, input handling, storage, auth, or external integration surface was introduced by this task.
- Blocking findings: none.

## Observations
- The verification method is split across the task body's `Research` and `Architecture Review` sections instead of being restated directly inside the `## AC-2: Components needing additional treatment` section. That is still adequate for the refined AC, but future artifact-only verification tasks would be easier to audit if result and method were kept adjacent in the same section.
2026-05-14T06:47:25+00:00
## Docs Gate

**Verdict:** PASS — advancing to done.

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| Item 1: README Verification | N/A (fast path) | Non-implementation task; no source files changed. No README target via convention mapping. |
| Item 2: External Attribution | PASS | 6 external sources recorded in `.owlbear/sources/overview.md` under "PDS Dark-Mode Compatibility Research (Task #1553)". Source #7 (local codebase) is internal — no attribution entry needed. |
| Item 3: Research Doc | PASS | `.owlbear/research/1553-pds-dark-mode-compat.md` exists and is explicitly linked in task body `## Research` section. |
| Item 4: Deletion Detection | N/A | No files deleted in this task. |

### Files Updated
None — docs gate is a no-op for this non-implementation task.

### Scratch Cleanup
No `.owlbear/scratch/1553-*` files found.
2026-05-14T06:54:56+00:00
## Audit
### Regression Detection
- quality-runner mode full: Python 4602 passed / 212 failed / 5 errors; Frontend 1590 passed / 156 failed. Lint clean (ruff + eslint).
- Task #1553 is a non-implementation research task with ZERO code changes. All test failures are pre-existing background issues from other in-flight tasks, unrelated to this task's research doc commit (ea08d351).
- regression verdict: PASS (no regressions attributable to this task)

### Research Task Verification
- Research doc exists: .owlbear/research/1553-pds-dark-mode-compat.md
- Follow-up task #1555 created at research status, depends on #1553
- Follow-up references research findings and parent #1534

### Intent Verification
- scope alignment: PASS (cockpit frontend theming domain, consistent with task tags and parent #1534)
- purpose match: PASS (verify PDS dark-mode compat, document findings, create follow-up: all achieved)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
- AC-1 refined to cover both positive and negative outcomes (originally assumed positive)
- AC-2 tightened to require follow-up task as inspectable artifact
- Proof bundle correctly de-escalated from behavioral to skip
- All PDS components enumerated explicitly (B3 compliance)
- Minor gap: original AC needed refinement (architect caught and fixed it)

### Commit Integrity
- upstream commit presence: PASS (ea08d351 covers research doc and sources)
- No other commits expected for pass-through task (architect/test-writer/builder/reviewer/doc-writer all pass-through with task-body-only contributions)
- kanban commit packaging: pending (this archival)

### Deduction Breakdown
- No deductions applied. Task is clean across all criteria.

### Confidence: 1.00
### Action: archive