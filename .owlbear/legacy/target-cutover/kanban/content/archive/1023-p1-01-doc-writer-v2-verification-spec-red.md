---
id: 1023
title: 'P1-01: doc-writer v2 verification spec (RED)'
status: archived
priority: medium
created: 2026-04-19 23:52:14.064115+00:00
updated: 2026-04-20 02:23:15.344750+00:00
tags:
- phase-1
- docs-currency
- docs-agent
parent: 1016
depends_on:
- 1020
- 1021
- 1022
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1016

## Acceptance Criteria

- [ ] Verification spec document created defining exactly 6 behavioral test cases per Brief Outcome 4:
  1. **No-op:** task changes only test files; expected: doc-writer writes `## Docs Gate` with all checks N/A, advances to done
  2. **Prose update:** task changes a CLI command; expected: doc-writer updates README.md (or relevant in-scope doc), commits
  3. **Diagram maintenance:** task touches file matching existing diagram's `describes` glob; expected: doc-writer updates diagram + footer (date + commit hash)
  4. **Explicit diagram creation:** task body requests new diagram; expected: doc-writer creates .excalidraw + index entry + footer
  5. **Deletion proposal:** task removes feature with orphaned doc; expected: doc-writer creates child kanban task + scribe-DR, advances without deleting
  6. **Ambiguous (misclassification):** task touches agent-executable file (OUT of scope); expected: doc-writer correctly identifies as OUT, no edit, no false-positive
- [ ] Each test case specifies: setup (task state, files changed), trigger, expected outcome, pass/fail criteria
- [ ] Verification log template created at `tests/fixtures/doc_writer_v2_verification.md`
- [ ] Pass criteria stated: 6/6 expected outcomes met

## Files

- Creates: verification spec + log template
- Reference: Brief Outcome 4, `share/agents/doc-writer.agent.md`, `share/skills/w-doc-update/SKILL.md`

## Notes

These are agent-behavioral verification cases, not pytest unit tests. The spec defines what "correct" looks like before the agent is rewritten. TDD RED phase for agent design.
[[2026-04-20]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One task: create behavioral verification spec. Spec + template are tightly coupled deliverables. |
| Interface clarity | PASS (after refinement) | See binding refinements below — path, format, and trigger definition tightened. |
| Dependency correctness | PASS | All 3 dependencies (#1020, #1021, #1022) archived/complete. Phase 0 tooling is in place. |
| Module layering | N/A | No code modules; markdown deliverables only. |
| TDD compliance | PASS | This IS the RED phase — defines expected behavior before #1024 GREEN implementation. |
| KISS/YAGNI | PASS | Minimal scope: 6 cases per Brief Outcome 4, one file, one template. |
| Premise challenge | PASS | Brief Outcome 4 explicitly requires this spec before agent rewrite. |
| Pattern consistency | PASS | No existing verification spec pattern in repo; this establishes the pattern. |
| Security surface | N/A | No system boundaries, no I/O, no user input. |
| Single domain | PASS | Documentation domain only. |

### Challenge Results

- Challenger: **reconsider** (confidence 0.55)
- Key concerns: Brief-vs-AC path disagreement (C1), diagram cases reference non-existent infrastructure (C2), no deliverable format specification (C4)
- Architect response: **accepted C1 and C4**, partially accepted C2. All addressed via binding refinements below. C3 (location) overruled — planner's decision stands per Brief's "planner-decided path" language. C5 (tag) accepted as best practice.

### Binding Refinements for Builder

**R1 — Single file, authoritative path.** The verification spec and log template are a **single document** at `tests/fixtures/doc_writer_v2_verification.md`. This resolves the AC ambiguity between "spec document" and "log template" — they are one file. The Brief's `serve/tools/tests/` suggestion is superseded per the Brief's own "or similar planner-decided path" clause.

**R2 — Mandatory document structure.** Each of the 6 cases MUST use this structure:

```
## Case N: {Case Name}
### Setup
{Task state, files changed, board state, any pre-existing artifacts}
### Trigger
{Exact pipeline event that invokes doc-writer}
### Expected Outcome
{Observable result — what doc-writer does or doesn't do}
### Pass/Fail Criteria
{Binary condition: how to judge pass vs fail}
```

The log template section at the bottom uses a table: `| Case | Mode | Expected | Observed | Pass/Fail | Notes |`

**R3 — Trigger definition.** "Trigger" for all cases = standard pipeline dispatch: task reaches `docs` status and doc-writer is invoked via `start_work`. This is the only trigger mechanism. State it once at the top of the spec.

**R4 — Diagram cases (3 & 4) are forward-looking.** Cases 3 and 4 define expected behavior for diagram infrastructure that is a Phase 2 deliverable. The setup sections for these cases MUST:
- Explicitly reference Brief §4.6 (`describes` schema: list of file path globs only)
- State that setup assumes diagram infrastructure exists (`.excalidraw` files in `share/diagrams/` with `describes` metadata in doc-index)
- Define concrete hypothetical setup state (e.g., "an existing `share/diagrams/pipeline.excalidraw` with `describes: ['share/agents/*.agent.md']` and footer `Last verified: 2026-04-01 (abc1234)`")

**R5 — Pass-through tag required.** This task produces no testable Python code. Tag `type:docs` must be added before the test-writer processes it. (Architect lacks `edit_task` tool — orchestrator or user must add the tag.)

### Verdict: APPROVE
### Action Taken: Advanced to `todo` with binding refinements R1–R5 appended to task body. Builder must follow the mandatory document structure (R2) and forward-looking diagram case conventions (R4). Tag `type:docs` must be added manually.
[[2026-04-20]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `tests/fixtures/doc_writer_v2_verification.md` (markdown deliverable) — no testable Python interfaces.
- Scanned AC for implementation keywords (`implement`, `function`, `class`, `module`, `src/`, `.py`, `import`, `API`): none found.
- Architect R5 confirmed: "This task produces no testable Python code."
- Heuristic pass-through per w-tdd-red Step 2a (AC references only `.md` files).
- ⚠️ Tag `type:docs` was not present — architect flagged this as missing. Recommend orchestrator adds it before next retry to enable automatic Step 1 pass-through.
[[2026-04-20]]
## Builder Notes

### Files Changed
- `tests/fixtures/doc_writer_v2_verification.md` — created (new file)

### Test Results
N/A — this task produces no Python code. Deliverable is a markdown specification.

### Lint Status
N/A — markdown file.

### Evidence Summary
- Created verification spec at `tests/fixtures/doc_writer_v2_verification.md`.
- Exactly 6 behavioral test cases per Brief Outcome 4 and AC.
- Each case uses the mandatory R2 structure: Setup → Trigger → Expected Outcome → Pass/Fail Criteria.
- Trigger stated once at the top (R3): standard pipeline dispatch via `start_work` when task is in `docs` status.
- Cases 3 and 4 (diagram cases) explicitly flag as forward-looking per R4, reference Brief §4.6 `describes` schema, and define concrete hypothetical setup state.
- Log template at the bottom uses the required table format: `| Case | Mode | Task ID | Expected Outcome | Observed Outcome | Pass/Fail | Notes |`.
- R1 honored: single file, authoritative path at `tests/fixtures/doc_writer_v2_verification.md`.

### Fixes Applied
None — greenfield creation.
[[2026-04-20]]
## Review Evidence

### Test Results
N/A — docs-only deliverable. No Python code, no pytest, no lint.

### Coverage
N/A

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| 6 behavioral cases (No-op, Prose, Diagram Maintenance, Diagram Creation, Deletion, Ambiguous) | Cases 1–6 in `tests/fixtures/doc_writer_v2_verification.md`, one-to-one match with Brief Outcome 4 named modes | PASS |
| Each case: setup + trigger + expected outcome + pass/fail | All 6 cases follow R2 mandatory structure (## Case N → ### Setup → ### Trigger → ### Expected Outcome → ### Pass/Fail Criteria) | PASS |
| Log template at `tests/fixtures/doc_writer_v2_verification.md` | Single file at R1 path; log table columns superset of Brief Outcome 4 required columns (added Task ID) | PASS |
| Pass criteria: 6/6 stated | "Pass criteria: 6/6 expected outcomes met." present at top of document | PASS |

### Binding Refinements

| Refinement | Status |
|-----------|--------|
| R1 — single file at `tests/fixtures/doc_writer_v2_verification.md` | PASS |
| R2 — mandatory 4-section structure per case | PASS |
| R3 — trigger stated once at top ("## Trigger (all cases)") | PASS |
| R4 — Cases 3 & 4 forward-looking with Brief §4.6 reference and concrete hypothetical setup | PASS |
| R5 — tag `type:docs` missing | Not builder-executable; architect-flagged; N/A |

### Spec Accuracy Against Brief
- Case 6 "OUT of scope per Brief §3": verified — Brief §3 lists `share/skills/*/SKILL.md (30)` as OUT. ✓
- Case 5 deletion workflow: matches Brief §4.1 verbatim (child task blocked, scribe DR, current task advances). ✓
- Case 4 diagram trigger: matches Brief §4.1(a) explicit request condition. ✓
- Log template columns match Brief Outcome 4 required fields. ✓

### Deductions
None. Markdown spec only; no security surface, no test integrity concerns, no builder loop.

### Verdict
**PASS — confidence .97 → docs**
[[2026-04-20]]
## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → `.github/copilot-instructions.md` | No | N/A | Task creates a markdown test fixture only; no code, no API, no config change |
| 2 | Module docstrings | No | N/A | No Python modules created or modified; builder and reviewer both confirm N/A |
| 3 | External attribution | No | N/A | Spec content derived from the brief and AC — no external repos or articles |
| 4 | CLI changes → `README.md` | No | N/A | No CLI commands added or modified |
| 5 | Research doc linkage | No | N/A | No `.owlbear/research/*.md` produced; brief reference is internal only |

### Files Updated
None.

### Scratch Files
No `.owlbear/scratch/1023-*` files found.

### Verdict
No docs impact. All 5 checklist items N/A. Deliverable `tests/fixtures/doc_writer_v2_verification.md` is a test fixture / behavioral spec, not a documentation artifact governed by items 1–5. Advancing to done.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 6 behavioral cases per Brief Outcome 4 | Cases 1–6 in `tests/fixtures/doc_writer_v2_verification.md`: No-op, Prose Update, Diagram Maintenance, Explicit Diagram Creation, Deletion Proposal, Ambiguous — one-to-one match | PASS |
| Each case: setup + trigger + expected outcome + pass/fail | All 6 cases follow R2 mandatory 4-section structure | PASS |
| Log template at `tests/fixtures/doc_writer_v2_verification.md` | Table at document bottom with columns: Case, Mode, Task ID, Expected Outcome, Observed Outcome, Pass/Fail, Notes | PASS |
| Pass criteria: 6/6 stated | "Pass criteria: 6/6 expected outcomes met." at top of document | PASS |

### Binding Refinements
| Refinement | Status |
|-----------|--------|
| R1 — single file at authoritative path | PASS |
| R2 — mandatory 4-section structure | PASS |
| R3 — trigger stated once at top | PASS |
| R4 — Cases 3 & 4 forward-looking with Brief §4.6 ref | PASS |
| R5 — type:docs tag | Not builder-executable; N/A |

### Test Results
- pytest: 797 passed, 6 failed (all in `serve/mcp-knowledge/` — unrelated to task scope), 4 skipped
- ruff: clean

### Architect Quality: 4/5
AC was specific and verifiable. Challenger cycle produced binding refinements R1–R5 that tightened deliverable format and addressed path ambiguity. Minor: R5 (tag) required out-of-band action, but architect correctly flagged this limitation.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 verified) → no deduction
- Lint violations: none → no deduction
- AC quality ≤ 3: no (4/5) → no deduction
- Missing reviewer evidence: no (detailed, .97 PASS) → no deduction
- Full-suite failures in task scope: none → no deduction

### Confidence: 1.00
### Action: archive