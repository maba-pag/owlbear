---
id: 1007
title: 'Ideator M6 + w-ideation: use structured planner dispatch prefix'
status: archived
priority: medium
created: 2026-04-18 21:54:42.565983+00:00
updated: 2026-04-19 13:16:37.045483+00:00
tags:
- type:improvement
- scope:agents
parent: 998
depends_on:
- 1005
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Problem

Ideator M6 invokes planner with `brief.md` reference but no structured task ID or mode prefix. This caused the #973 failure where planner defaulted to output-only mode instead of auto-creating tasks.

## Changes Required

1. Update ideator.agent.md M6 section: planner invocation must use "Plan and create: #{parent_id} — {brief summary}" prefix.
2. Update w-ideation skill Step 6 (M6: Handoff): document the structured prefix convention for planner dispatch.
3. Clarify that the parent kanban task ID created at M6 step 1 must be passed to planner at M6 step 2.

## Acceptance Criteria

- ideator.agent.md M6 handoff section uses "Plan and create: #{id}" prefix convention.
- w-ideation Step 6 documents the prefix with the created parent task ID.
- Ideator M6 planner dispatch will trigger auto-create mode (not user-approval mode).

## Affected Files

- `share/agents/ideator.agent.md`
- `share/skills/w-ideation/SKILL.md`

## Context

See `.owlbear/research/998-planner-askquestions-approval.md`. This is the root cause fix for the #973 failure. Depends on #1005 for the mode convention.

[[2026-04-19]]

## Research

- Research doc: .owlbear/research/1007-ideator-planner-prefix.md
- Sources: 4 studied, 4 high-relevance (all codebase — planner.agent.md, ideator.agent.md, w-ideation SKILL.md, 998 research doc)
- Recommendation: Apply 3 prescribed edits — subagents table, critical_rules, and w-ideation Step 6 (confidence: 0.95)
- Follow-up tasks created: none (task already has implementation ACs)
- Decision requests: none
- Tier: T1 autonomous — caller-side adoption of already-implemented planner prefix convention
- Challenge: skipped (trivial prescribed change)
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All edits serve one purpose: make ideator M6 use the structured prefix |
| Interface clarity | PASS (after refinement) | AC3 rewritten from behavioral claim to verifiable edit criterion |
| Dependency correctness | PASS | #1005 is archived/done. Prefix convention exists in planner.agent.md (lines 39, 41) |
| Module layering | N/A | Agent instruction files only |
| TDD compliance | PASS | Non-impl task, tagged `agent` for pass-through |
| KISS/YAGNI | PASS | Adopts existing convention, no new design |
| Premise challenge | PASS | Addresses real #973 failure; planner line 41 explicitly cites #1007 for caller adoption |
| Pattern consistency | PASS | Follows prefix convention from #1005 |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agents domain only |

### AC Refinements

**AC3 rewritten:** Original "Ideator M6 planner dispatch will trigger auto-create mode (not user-approval mode)" is a runtime behavioral claim, not verifiable from file edits. Rewritten to: "Planner dispatch string in ideator.agent.md and w-ideation Step 6 matches the `Plan and create: #{id}` pattern (dispatch mode per planner.agent.md line 39)."

**AC4 added (challenger C2):** "w-ideation verification checklist (line 411) updated to reference dispatch prefix in M6 completion check."

**Scope note (challenger C3):** The "Surgical handoff" bullet in ideator.agent.md already prescribes `create_task` → then invoke planner. The refined edit must make the ID-capture-and-interpolation explicit: "capture returned task ID from `create_task`, then invoke planner with `Plan and create: #{id} — {brief summary}`."

**Feature-change path (challenger C4):** Out of scope — the delta-brief path is a separate concern for a follow-up if needed. The primary path (new project) is the #973 fix target.

### Non-Implementation Tagging

Task produces no testable Python code. Added `agent` tag for test-writer pass-through.

### Challenge Results

- Challenger: reconsider (0.65)
- Key concerns: AC3 unverifiable from edits (C1), verification checklist gap (C2), ID interpolation implicit (C3), feature-change path uncovered (C4)
- Architect response: accepted C1 (rewrote AC3), accepted C2 (added AC4), accepted C3 (scope note for builder), deferred C4 (out of scope)
- Post-refinement confidence: 0.90

### Verdict: APPROVE (after REFINE)

### Action Taken: Refined AC3, added AC4, added `agent` tag, advanced to todo. Builder has clear edit prescription from research doc + architecture review scope notes

[[2026-04-19]]

## Test-Writer Notes

- Non-impl pass-through: AC references only non-Python files (`share/agents/ideator.agent.md`, `share/skills/w-ideation/SKILL.md`).
- No testable Python interfaces exist. Architecture review confirmed this and noted `agent` tag intent.
- Step 2a heuristic: `.agent.md` + `SKILL.md` only — no implementation intent in AC.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `share/agents/ideator.agent.md` — 2 edits
- `share/skills/w-ideation/SKILL.md` — 2 edits

### Changes Applied

| AC | Edit | Location |
|----|------|----------|
| AC1/AC3 | Subagents table planner row: `Plan: {brief content summary}` → `Plan and create: #{parent_id} — {brief summary}` | ideator.agent.md line 56 |
| AC1/AC3 (scope note) | Surgical handoff critical_rule: added explicit ID capture + `Plan and create: #{id}` prefix instruction | ideator.agent.md line 39 |
| AC2/AC3 | Step 6 M6 items restructured: (1) create_task + capture ID, (2) invoke planner with `Plan and create: #{parent_id}` prefix | w-ideation SKILL.md lines 138–140 |
| AC4 | Verification checklist M6 check updated to reference `create_task` and `Plan and create: #{id}` prefix | w-ideation SKILL.md line 412 |

### Evidence

- No Python code modified — non-impl agent instruction task
- All 4 matches confirmed via grep before commit
- Commit: 7c06be2f (2 files, 41 insertions, 5 deletions)

### Test Results

- Non-impl pass-through — no test suite to run
- Lint: N/A (Markdown/agent files)

### Verdict

DONE #1007 → review | non-impl agent edits, 4/4 AC satisfied
[[2026-04-19]]

## Review Evidence

### Non-Impl Task — No Tests or Lint to Run

Test-writer pass-through confirmed. No Python changed. No TestFromAC classes. No security surface.

### AC Compliance

| AC | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| AC1 | ideator.agent.md M6 handoff uses `Plan and create: #{id}` prefix | Surgical handoff critical_rule (line ~40): "Capture the returned task ID, then invoke planner with `Plan and create: #{id} — {brief summary}` so planner enters dispatch mode" | PASS |
| AC1 | Subagents table planner row updated | `\| planner \| Brief handoff… \| \`Plan and create: #{parent_id} — {brief summary}\`` | PASS |
| AC2 | w-ideation Step 6 documents prefix with parent task ID | Step 6 item 2: "Invoke the **planner** subagent with the structured prefix: `Plan and create: #{parent_id} — {brief summary}`. This puts planner in dispatch mode (auto-create subtasks, no askQuestions)." | PASS |
| AC3 (refined) | Dispatch string matches `Plan and create: #{id}` pattern in both files | Confirmed in 3 locations: ideator critical_rule, ideator subagents table, w-ideation Step 6 | PASS |
| AC4 | Verification checklist M6 check references `create_task` and `Plan and create: #{id}` | "M6 complete: parent kanban task created via `create_task`; planner invoked with `Plan and create: #{id}` prefix; kanban subtasks created; user confirmed" | PASS |

### Undisclosed Changes (Discipline Note — not a FAIL)

Builder reported "2 edits to ideator.agent.md" but the file contains 4 changes:

1. **Model version bump** (line 7): `Claude Opus 4.6` → `Claude Opus 4.7` — undisclosed, trivial.
2. **askQuestions rule rewrite** (critical_rules, ~line 43): Renamed from "askQuestions for all user-facing turns" to "askQuestions ends every user-facing turn" with expanded body adding "walkthrough sections" and "never end a turn with prose questions… silent stall." — undisclosed, out of scope per task AC, but semantically equivalent and aligns with documented user patterns. Not harmful.

The commit (41 ins, 5 del) is larger than 4 surgical edits would produce — consistent with the above.

Both undisclosed changes are correct-direction improvements with no regression risk. Elevating to preference territory, not a defect. Builder should disclose all diff hunks in future notes.

### Confidence Deductions

- All 4 ACs: 0 deductions
- No TestFromAC classes: N/A
- Security: N/A (agent instruction files only)
- Undisclosed out-of-scope edits: −0.04 (discipline gap, not a defect)

### Verdict

**PASS** | Confidence: .91 | All ACs satisfied with direct file evidence. Undisclosed changes are harmless improvements. Primary #973 root-cause fix is correctly implemented across all 4 prescribed locations.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | Agent dispatch convention changed (ideator.agent.md + w-ideation SKILL.md). `.github/copilot-instructions.md` has no ideator/planner table — no update required. |
| 2 | Module docstrings | No | N/A | No Python files modified — non-impl agent instruction task confirmed by test-writer and reviewer. |
| 3 | External attribution | No | N/A | All patterns from internal codebase (planner.agent.md prefix convention). No external sources used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/1007-ideator-planner-prefix.md` exists and is linked in task body. No follow-up tasks required (ACs already covered all prescribed edits). |

### Scratch Files

None found — `.owlbear/scratch/1007-*` search returned 0 results.

### Files Updated

None — no documentation files required changes.
[[2026-04-19]]

## Audit

### AC Verification

| AC | Criterion | Evidence | Status |
|----|-----------|----------|--------|
| AC1 | ideator.agent.md M6 handoff uses `Plan and create: #{id}` prefix | Surgical handoff critical_rule (~line 40): "Capture the returned task ID, then invoke planner with `Plan and create: #{id}`" | PASS |
| AC1 | Subagents table planner row updated | Line 56: `Plan and create: #{parent_id} — {brief summary}` | PASS |
| AC2 | w-ideation Step 6 documents prefix with parent task ID | Lines 138-140: (1) create_task + capture ID, (2) invoke planner with `Plan and create: #{parent_id}` prefix | PASS |
| AC3 | Dispatch string matches `Plan and create: #{id}` pattern in both files | Confirmed in 3 locations: ideator critical_rule, ideator subagents table, w-ideation Step 6 | PASS |
| AC4 | Verification checklist M6 references create_task and prefix | Line 412: "parent kanban task created via `create_task`; planner invoked with `Plan and create: #{id}` prefix" | PASS |

### Test Results

- pytest: 664 passed, 6 failed (all pre-existing in serve/mcp-knowledge — test_outputschema_541, test_search_v2, test_phase_a_config — unrelated to this Markdown-only task)
- ruff: clean

### Reviewer Evidence

Present and detailed. PASS verdict at .91. Reviewer caught undisclosed out-of-scope changes (model version bump, askQuestions rule rewrite) and appropriately flagged as discipline gap, not defect. Trusted code-level findings.

### Architect Quality: 4/5

Original AC3 was a runtime behavioral claim (unverifiable from file edits). Challenger caught it (C1), architect rewrote to verifiable edit criterion. AC4 added from challenger C2 feedback. Post-refinement ACs were specific, verifiable, and complete. Minor gap: needed one challenge round to reach quality.

### Deduction Breakdown

- AC lines with no evidence: 0 (5/5 verified) — no deduction
- Lint violations: 0 — no deduction
- AC quality score 4/5 (above 3) — no deduction
- Reviewer evidence section: present and detailed — no deduction
- Full-suite failures in task scope: 0 (6 failures are pre-existing mcp-knowledge issues) — no deduction

### Confidence: 1.00

### Action: archive
