---
id: 1631
title: 'Architect calibration: planner AC accuracy for PDS decomposition'
status: done
priority: nice-to-have
created: 2026-05-16T07:50:38.652054+00:00
updated: 2026-05-16T12:23:05.365198+00:00
tags:
  - process
  - quality
parent:
depends_on: []
ac:
  - 'Audit table appended to task body covers the tasks decomposed from #1590 (39
    children), each row containing: task ID, title, AC accuracy verdict (correct /
    inaccurate / not-verifiable), and one-line evidence citation. Verified by artifact
    inspection of the completed table.'
  - Root-cause section classifies the error pattern as isolated (≤2 tasks with 
    inaccurate ACs) or systemic (≥3 tasks), with per-task evidence citations 
    supporting the classification. Verified by artifact inspection.
  - 'If classified systemic: process-guard proposal section specifies concrete step
    description, trigger condition (task type or codebase signal), expected failure
    class prevented, and integration point in w-task-decomposition skill. If classified
    isolated: explicit skip statement satisfies this AC. Verified by artifact inspection.'
  - Follow-up kanban tasks created for each distinct corrective action 
    identified, each referencing this audit (#1631) in its body. Verified by 
    field-presence check on the board.
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Review planner AC accuracy across the PDS decomposition batch (parent #1590) and identify systemic patterns that led to factually incorrect acceptance criteria.

## Context

During audit of #1605 (P1-07: Extend computeSignal with unknown state), two ACs were factually wrong:
- **AC-1** said "return an object with state 'unknown'" — but `computeSignal` returns a string, not an object.
- **AC-2** listed state names "green/yellow/red/gray/stale" — but actual engine states are `dr-pending/blocked/claimed/deps-unmet/ready`.

These ACs were written during planner decomposition of parent #1590. The architect correctly identified #1605 as superseded by #1599, but the original ACs would have misled an implementer had they reached a builder first.

This suggests the planner did not read the actual source code (`computeSignal` return type, engine status enum) before writing ACs — violating the "research before implementation" heuristic.

## Scope

1. Audit all tasks created in the #1590 decomposition batch for AC accuracy against actual codebase state at time of planning.
2. Identify whether the pattern is isolated to #1605 or systemic across the batch.
3. If systemic, propose a planner process guard (e.g., mandatory source-read step before AC authoring for refactor/extension tasks).
4. Create follow-up tasks for any corrective actions identified.

[[2026-05-16T10:10:33+02:00]]
## Architecture Review
### Verdict: APPROVE (REFINE + approve)

**Proof bundle:** skip
**Test-writer:** SKIP
**Challenge:** SKIPPED (proof bundle = skip)

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC-1: per-task audit table | P1 FAIL (no agent), P3 FAIL (no verification method), B3 OK ("all" with enumerable set) | Rewritten: added artifact-inspection verification method, specified 39-child scope |
| AC-2: root-cause classification | P1 FAIL, P3 FAIL | Rewritten: added threshold (≤2 isolated, ≥3 systemic), per-task evidence requirement, artifact-inspection method |
| AC-3: process guard proposal | P3 FAIL ("expected effectiveness" vague) | Rewritten: specified 4-part structure (step, trigger, failure class, integration point), added conditional skip path |
| AC-4: follow-up tasks | P1 FAIL, P3 implicit | Rewritten: added reference requirement (#1631), field-presence check method |

### Architecture Notes
- Task is well-scoped: single responsibility (audit one decomposition batch).
- Verified task framing against codebase: `computeSignal` returns `CardSignal` string union (`dr-pending | blocked | claimed | deps-unmet | ready | unknown`), confirming #1605 ACs were factually incorrect (said "object" and "green/yellow/red/gray/stale").
- Tagged `quality` for pipeline pass-through (no testable code output).
- Proof bundle `skip` — deliverable is audit report + follow-up tasks, not code.

### Dependency Analysis
- No dependencies. Standalone process task.
- References #1590 (parent of batch under audit) and #1605 (known-bad exemplar) — both read-only references, not blocking dependencies.

[[2026-05-16T10:23:01+02:00]]
## Test-Writer Notes
- Non-implementation task (tagged `quality`) — no tests applicable.
- Proof bundle: skip.
- Passing through to builder.

2026-05-16T08:36:59+00:00
## Builder Notes
### AC Audit Table (#1590 decomposition batch, 39 tasks)

| Task | Title | AC Accuracy Verdict | One-line evidence citation |
|---|---|---|---|
| #1591 | P0-01: Tests — PDS global-styles import + CSP font relaxation | correct | AC literals (`--p-color-canvas`, `--p-spacing-static-md`, `--p-font-porsche-next`) align with found symbols in repo scan; CSP tokenization check is precise. |
| #1592 | P0-03: Tests — Tailwind v4 Vite plugin + Stylelint config | correct | AC references concrete build/lint behavior (`@tailwindcss/vite`, `@theme`, `light-dark()`), no contradiction with current toolchain/files. |
| #1593 | P0-05: Tests — board horizontal scroll | correct | AC expresses measurable UI geometry assertions (`scrollWidth > clientWidth`, shared `offsetTop`) without contradicting existing APIs. |
| #1594 | P0-02: PDS global-styles import + CSP font relaxation | inaccurate | AC-1 cites `--p-spacing-md` and `--p-font-family`; repo scan found `--p-spacing-static-md` and `--p-font-porsche-next`, with both cited AC literals absent. |
| #1595 | P0-04: Install @tailwindcss/vite + configure Stylelint for Tailwind v4 | correct | AC pins concrete package/config expectations (`tailwindcss ^4`, `@tailwindcss/vite ^4`, no PostCSS) and matches known frontend direction. |
| #1596 | P0-06: Board horizontal scroll fix | correct | ACs are implementation outcomes (horizontal overflow + min-width + no regression) and do not assert false current contracts. |
| #1597 | P1-01: Token provenance map | correct | AC requires classification/coverage evidence rather than asserting incorrect literals; scope aligns with listed frontend files. |
| #1598 | P1-04: Tests — formatting utilities | correct | AC names existing formatter seam and guardrail import-ban scope; archived implementation/review evidence confirms contract was valid. |
| #1599 | P1-06: Tests — computeSignal unknown state | correct | AC uses correct `computeSignal(...)->'unknown'` string expectation and append-only test constraint; aligns with `CardSignal` union. |
| #1600 | P1-02: Tests — atomic token migration | correct | ACs are grep/file/theme assertions for migration completion; no factual mismatch with known file model. |
| #1601 | P1-08: Tests — shell layout | correct | ACs are verifiable Playwright/layout outcomes and do not encode contradictory symbol names/types. |
| #1602 | P1-10: Tests — sidecar structure | inaccurate | AC-1 requires `--p-spacing-md`; literal not found in repo scans, indicating wrong token name in AC wording. |
| #1603 | P1-03: Atomic token migration — delete tokens.css + migrate references | correct | AC specifies concrete grep/delete/update checks tied to real files and token migration objective; no false interface claim detected. |
| #1604 | P1-05: Formatting utilities | correct | AC maps to concrete module behavior (`utils/format.ts`, canonical/display partition) and was validated by completed downstream evidence. |
| #1605 | P1-07: Extend computeSignal with unknown state | inaccurate | AC-1 says object return; `computeSignal` returns `CardSignal` string union. AC-2 lists `green/yellow/red/gray/stale`; actual states are `dr-pending/blocked/claimed/deps-unmet/ready(/unknown)`. |
| #1606 | P1-09: Shell layout — sticky header + responsive sidebar | correct | AC mirrors #1601 test intent with measurable layout behavior; no contradictory literal/type assumptions. |
| #1607 | P1-11: Sidecar structure — padding, sections, typography | inaccurate | AC-1 repeats `--p-spacing-md` literal; token scan indicates this literal is absent in current PDS token usage baseline. |
| #1608 | P2-01: Component complexity inventory | correct | AC is classification/dependency-inventory deliverable; does not assert a false code-level contract. |
| #1609 | P2-02: Tests — simple component swaps | correct | ACs are audit-style assertions over element usage categories from inventory; no direct factual mismatch found. |
| #1610 | P2-04: Tests — card visual treatment | correct | ACs define test-observable card affordances and tokenized color requirement, with no contradicted symbol/interface claim. |
| #1611 | P2-06: Tests — sidecar information architecture | correct | AC is ordering/typography intent and remains internally consistent with existing sidecar redesign scope. |
| #1612 | P2-08: Tests — filter panel PDS controls | correct | AC states component/layout target outcomes without conflicting with known code contracts. |
| #1613 | P2-10: Tests — complex integrations (modals → PModal) | correct | ACs specify modal behavior expectations (focus trap/Escape/backdrop) as target behavior; no false existing-type assertion. |
| #1614 | P2-03: Simple component swaps | correct | AC defines post-migration element constraints with inventory carve-outs; no factual mismatch with baseline APIs. |
| #1615 | P2-05: Card visual treatment | correct | ACs are UI acceptance outcomes (metadata visibility + tokenized colors), no incorrect literal contract observed. |
| #1616 | P2-07: Sidecar information architecture | correct | ACs are IA/typography outcome statements; no contradictory code-level assumptions detected. |
| #1617 | P2-09: Filter panel PDS controls | correct | AC aligns with #1612 test intent and contains no contradicted enum/type/token literals. |
| #1618 | P2-11: Complex integrations — modals → PModal | correct | AC is behavior-preservation for modal migration and does not assert false existing signatures or enums. |
| #1619 | P3-01: Tests — success feedback (PToast) | correct | ACs are latency/feedback/error-visibility outcomes and contain no incorrect literal contracts. |
| #1620 | P3-03: Tests — dark mode audit | correct | AC sets measurable contrast and hardcoded-color prohibitions; no contradiction with known architecture constraints. |
| #1621 | P3-05: Tests — focus-visible rings | correct | ACs define focus-visibility/tokenized-style checks; no factual mismatch with current code contracts. |
| #1622 | P3-07: Tests — motion/transitions | correct | ACs are animation-token and `transition: all` prohibition checks; no false symbol/type assumptions. |
| #1623 | P3-09: Tests — accessibility sweep | correct | ACs are standard a11y measurable outcomes (axe/tab/contrast) with no contradictory literal assertions. |
| #1624 | P3-02: Success feedback — PToast notifications | correct | AC mirrors #1619 behavior goals; no incorrect interface/type assumptions. |
| #1625 | P3-04: Dark mode audit — border contrast + token compliance | correct | AC aligns with #1620 test intent and contains no contradicted enum/token literal claim. |
| #1626 | P3-06: Focus-visible rings — PDS focus styling | correct | AC is behavior/style-token outcome statement; no false existing interface assumption found. |
| #1627 | P3-08: Motion/transitions — PDS duration + easing tokens | correct | AC is implementation outcome check and does not conflict with known contracts. |
| #1628 | P3-10: Accessibility sweep | correct | AC aligns with #1623 test intent and uses measurable accessibility criteria, no false literal contract. |
| #1629 | Consolidation test: cockpit visual redesign | correct | ACs are suite-level pass/style-budget/theme/a11y outcomes and do not encode incorrect code-level signatures/enums. |

### Root-Cause Classification
- **Classification: systemic (4 inaccurate tasks >= threshold of 3).**
- Inaccurate set with citations: `#1594`, `#1602`, `#1605`, `#1607`.
- Shared failure mode: ACs used inferred/legacy literals instead of literals verified from source (token names and signal contract/state vocabulary).

### Process-Guard Proposal (systemic path)
- **Step description:** Add mandatory **Source Validation** step before AC authoring in decomposition: identify target files, read source, extract canonical symbols/literals (function signatures, unions/enums, token names, component names), then draft ACs from that extracted list.
- **Trigger condition:** Required for refactor/extension tasks or any task whose AC references existing code symbols; explicitly skippable for greenfield tasks with no existing code references.
- **Failure class prevented:** Wrong return-type assumptions, invented enum/state names, stale token literal usage (the exact class seen in #1594/#1602/#1605/#1607).
- **Integration point:** `share/skills/w-task-decomposition/SKILL.md` between current planning and AC-writing steps, with an example demonstrating pass/fail behavior.

### Follow-up Tasks Created
- `#1632` Planner guard: mandatory source-read + symbol validation before AC authoring (references audit #1631 in body).
- `#1633` AC lint checklist: canonical enum/token literals for cockpit/frontend tasks (references audit #1631 in body).

### Evidence summary
- Batch membership source: parent task #1590 decomposition list (39 tasks).
- AC payload source: `show_task(section="ac")` for each task #1591–#1629.
- Literal verification source: repository scans over `serve/cockpit/web/src` and `serve/cockpit/web/e2e` confirming token/signal literals (`--p-spacing-static-md` present, `--p-spacing-md` absent; `CardSignal` string union present; color-state literals absent from computeSignal contract).

[[2026-05-16T10:37:04+02:00]]
## Builder Notes
Completed audit deliverable for #1631 (proof bundle `skip`) with full 39-task table covering #1590 decomposition batch.

- AC-1: Satisfied — appended per-task table with verdicts (`correct`/`inaccurate`) and one-line evidence citations for all 39 tasks.
- AC-2: Satisfied — classified pattern as **systemic** (4 inaccurate tasks: #1594, #1602, #1605, #1607), with per-task evidence in the table.
- AC-3: Satisfied — added concrete process-guard proposal with required 4 fields: step, trigger, prevented failure class, and integration point (`w-task-decomposition`).
- AC-4: Satisfied — created corrective follow-up tasks:
  - #1632 Planner guard: mandatory source-read + symbol validation before AC authoring
  - #1633 AC lint checklist: canonical enum/token literals for cockpit/frontend tasks
  Both bodies reference audit #1631.

Verification method used: artifact inspection (`show_task(section="ac")` across #1591-#1629, parent decomposition list from #1590) plus repository literal checks for disputed symbols/tokens/states.

No code files changed (process-quality task).

[[2026-05-16T11:03:19+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1631 -> docs | AC mapped to deliverable and evidence sufficient.
- AC evidence map:

| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | Board inspection found 39 child tasks with `parent: 1590` across `.owlbear/kanban/**`; the audit table in `.owlbear/kanban/tasks/1631-architect-calibration-planner-ac-accuracy-for-pds-decomposition.md:95-133` contains 39 rows covering `#1591-#1629`, each with task ID, title, verdict, and one-line citation. | PASS |
| AC-2 | Root-cause section exists at `.owlbear/kanban/tasks/1631-architect-calibration-planner-ac-accuracy-for-pds-decomposition.md:136-138` and classifies the pattern as systemic (4 inaccurate tasks). The cited inaccuracies are supported by task/source evidence: `.owlbear/kanban/tasks/1594-p0-02-pds-global-styles-import-csp-font-relaxation.md:16` and `.owlbear/kanban/tasks/1602-p1-10-tests-sidecar-structure.md:18` and `.owlbear/kanban/tasks/1607-p1-11-sidecar-structure-padding-sections-typography.md:16` use `--p-spacing-md`, while `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:4-6` and `serve/cockpit/web/e2e/pds-foundation-1591.spec.ts:111-145` prove the canonical literals are `--p-spacing-static-md` and `--p-font-porsche-next`; `.owlbear/kanban/archive/1605-p1-07-extend-computesignal-with-unknown-state.md:14-17` claims object return and `green/yellow/red/gray/stale`, while `serve/cockpit/web/src/utils/computeSignal.ts:1-27` shows `computeSignal()` returns `CardSignal` string values `dr-pending | blocked | claimed | deps-unmet | ready | unknown`. | PASS |
| AC-3 | The systemic-path process guard is fully specified in `.owlbear/kanban/tasks/1631-architect-calibration-planner-ac-accuracy-for-pds-decomposition.md:141-144`, including step description, trigger condition, prevented failure class, and integration point (`share/skills/w-task-decomposition/SKILL.md`). | PASS |
| AC-4 | Follow-up tasks are listed in `.owlbear/kanban/tasks/1631-architect-calibration-planner-ac-accuracy-for-pds-decomposition.md:146-148`; both follow-up bodies explicitly reference this audit at `.owlbear/kanban/tasks/1632-planner-guard-mandatory-source-read-symbol-validation-before-ac-authoring.md:51` and `.owlbear/kanban/tasks/1633-ac-lint-checklist-canonical-enum-token-literals-for-cockpit-frontend-tasks.md:52`. | PASS |
- Blocking findings: none.
- Safety/security check: no executable, auth, storage, or external-integration change under review; no safety finding in scope.

## Observations
- Builder notes omitted explicit lint status for this `skip` bundle. Reviewer dispatched `quality-runner`; it confirmed `.markdownlint-cli2.jsonc:3-7` excludes `.owlbear/kanban/tasks/**`, so there is no runnable markdownlint surface for `#1631`, `#1632`, or `#1633`. Non-blocking.
- `code-reader` and `challenger` were not required because the authoritative proof bundle is `skip`.

[[2026-05-16T14:23:05+02:00]]
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| README Verification | N/A | No `serve/**`, `share/**`, or `setup/**` files changed by this task. Deliverables were kanban board content only (audit table in task body + follow-up tasks #1632/#1633). |
| External Attribution | N/A | No external sources influenced the audit work. |
| Research Doc | N/A | No research artifact was created for this task. |
| Deletion Detection | N/A | No files deleted. |

### Files Updated
None — no-impact fast path applied.

### Scratch Cleanup
No `.owlbear/scratch/1631-*` files found.
