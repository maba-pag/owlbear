---
id: 1006
title: 'w-task-decomposition: add conditional approval step for user-invoked mode'
status: archived
priority: medium
created: 2026-04-18 21:54:33.726798+00:00
updated: 2026-04-19 13:07:51.881344+00:00
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

w-task-decomposition skill has no approval step between plan validation and task creation. When planner runs in user-invoked mode, it needs to present the plan and ask for approval before executing create_task calls.

## Changes Required

1. Add a conditional Step 5b between Step 5a (validate) and Step 6 (create):
   - If user-invoked mode (no "and create" prefix): present the planned tasks, call askQuestions for approval, proceed to Step 6 only on approve.
   - If dispatch mode ("Plan and create" prefix): skip Step 5b, proceed directly to Step 6.
2. Document what happens if user rejects: planner stops and reports the rejection.

## Acceptance Criteria

- w-task-decomposition SKILL.md includes conditional approval step.
- Step references the explicit mode prefix convention from planner.agent.md.
- Approval uses askQuestions (not prose question).
- Rejection ends the workflow cleanly without creating tasks.

## Affected Files

- `share/skills/w-task-decomposition/SKILL.md`

## Context

See `.owlbear/research/998-planner-askquestions-approval.md`. Depends on #1005 for the mode convention.

[[2026-04-19]]

## Research

- Research doc: .owlbear/research/1006-task-decomposition-approval-step.md
- Sources: 5 studied (all codebase), 4 high-relevance
- Recommendation: Four targeted edits to w-task-decomposition/SKILL.md — update Step 0 execution mode to reference prefix convention, add Step 5b conditional approval gate (askQuestions with approve/reject), adjust user-mode behavior from output-only to approve-then-create. (confidence: 0.90)
- Challenge: skipped (trivial — behavior fully specified by #998 architecture review and planner.agent.md)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none — T1 classification (agent instructions, user-directed)
[[2026-04-19]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single file edit: w-task-decomposition/SKILL.md |
| Interface clarity | PASS | AC verifiable by file inspection (see refinements below) |
| Dependency correctness | PASS | #1005 confirmed done — prefix convention in planner.agent.md verified |
| Module layering | N/A | Agent instruction files only |
| TDD compliance | PASS | Non-implementation — requires `agent` tag for pass-through (see below) |
| KISS/YAGNI | PASS | Minimal scope — one conditional step + Step 0 update |
| Premise challenge | PASS | Addresses real gap identified in #998 architecture review |
| Pattern consistency | PASS | askQuestions approval pattern matches w-ideation/SKILL.md M5 |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Agents domain only |

### Binding AC Refinements

**AC addition — three-tier mode detection:** Step 0's "Execution mode" paragraph must reference or mirror the three-tier prefix detection from planner.agent.md (dispatch / user / fallback), NOT collapse no-prefix into user mode unconditionally. The #998 architecture review binding constraint specifies: no-prefix with pipeline markers → abort with error; no-prefix with freeform input → default to approval mode. The SKILL.md must either replicate this or defer detection to planner.agent.md with a cross-reference.

**AC addition — `agent` tag prerequisite:** Task must carry the bare `agent` tag for test-writer pass-through before entering `todo`. Parent #998 arch review explicitly mandates this for all children. (NOTE: No edit_task MCP tool available — user or orchestrator must add the `agent` tag manually.)

**Design choice accepted:** Binary approve/reject (not three-option). Task decomposition is cheap to re-invoke — "adjust" adds complexity without proportionate value here.

### Challenge Results

- Challenger: reconsider (0.55)
- Key concerns: C1 (fallback behavior contradicts #998 binding constraint), C2 (research challenge skipped), C3 (missing agent tag), C4 (binary approve/reject dismisses adjustment)
- Architect response: C1 accepted — added binding refinement requiring three-tier detection; C2 covered by this review; C3 accepted — noted as prerequisite; C4 rebutted — binary is appropriate for decomposition approval
- Post-refinement confidence: 0.85

### Verdict: APPROVE

### Action Taken: Advanced to todo with binding AC refinements (three-tier mode detection, agent tag prerequisite). Builder must follow #998 binding constraints for fallback behavior

[[2026-04-19]]

## Test-Writer Notes

- Non-impl pass-through: SKILL.md only — no testable Python interfaces.
- AC targets `share/skills/w-task-decomposition/SKILL.md` exclusively (Step references, askQuestions call, rejection path, mode detection).
- Scanned all AC lines — zero implementation intent keywords (implement, function, class, src/, .py, endpoint, API).
- Tags `type:improvement`, `scope:agents` consistent with non-impl; arch review confirms "Non-implementation — requires `agent` tag for pass-through".
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

- **File changed:** `share/skills/w-task-decomposition/SKILL.md`
- **Changes applied (2):**
  1. Step 0 execution mode paragraph replaced — now mirrors `planner.agent.md` three-tier prefix convention (dispatch / user / fallback-with-error)
  2. Step 5b added between Step 5a and Step 6 — conditional approval gate: skip in dispatch mode, present breakdown inline + `askQuestions` (Approve/Reject) in user mode; on reject stop without calling `create_task`
- **Non-impl pass-through:** no Python code changes, no test suite run needed
- **Lint:** N/A (Markdown file)
- **AC verification:**
  - ✅ SKILL.md includes conditional approval step
  - ✅ Step 0 references three-tier prefix convention from planner.agent.md
  - ✅ Approval uses `askQuestions` (not prose)
  - ✅ Rejection path: "stop, report cancellation to the user. Do NOT call `create_task`"
  - ✅ Fallback: pipeline markers → abort with error; freeform → default to user mode
- **Commit:** `875942ee` feat(agents): add conditional approval step to w-task-decomposition (#1006, builder)
[[2026-04-19]]

## Review Evidence

### Test Results

N/A — non-implementation task (SKILL.md only). No Python code changed, no test suite applicable.

### Lint Results

N/A — Markdown file, no linter applicable.

### Coverage

N/A

### Changed Files

- `share/skills/w-task-decomposition/SKILL.md` (builder-reported; verified via file read)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md includes conditional approval step | Step 5b present: "Call `askQuestions` with two options: Approve / Reject"; skip clause for dispatch mode | PASS |
| Step references explicit mode prefix convention from planner.agent.md | Step 0: "Determined by the caller's prompt prefix (mirrors `planner.agent.md` three-tier convention)" — all three tiers listed | PASS |
| Approval uses askQuestions (not prose question) | Step 5b explicitly calls `askQuestions` with two discrete options | PASS |
| Rejection ends the workflow cleanly without creating tasks | "On reject: stop, report cancellation to the user. Do NOT call `create_task`." | PASS |

### Binding Arch Refinement — Three-Tier Detection (AR1)

All three tiers verified in Step 0:

1. `Plan and create: #{id} — ...` → dispatch mode, execute directly ✅
2. `Plan: ...` → user mode, present breakdown + `askQuestions` approval ✅
3. No prefix + pipeline markers → abort with error; freeform → default to user mode ✅

### Minor Inconsistency (non-blocking)

SKILL.md tier-3 fallback ("abort with error if pipeline markers present") diverges from `planner.agent.md` tier-3 ("apply NL-based parent-task-ID heuristic; if inconclusive, default to approval mode"). SKILL.md is more conservative (abort vs attempt execution). `planner.agent.md` itself labels tier-3 a "temporary compatibility layer — will be removed via #1007/#1008." The binding arch constraint for this task endorsed the abort-with-error approach. Net: safer behavior, not a blocking defect.

### Deductions

- Tier-3 fallback divergence between SKILL.md and planner.agent.md creates a minor cross-file documentation inconsistency: −0.04

### Verdict

Confidence: **0.91 → PASS**

### Action

Advancing to `docs`.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | SKILL.md change only; copilot-instructions.md covers tech stack/API, not agent workflow steps — no update needed |
| 2 | Module docstrings | No | N/A | No Python files changed |
| 3 | External attribution | No | N/A | All 5 research sources are internal codebase refs — no external URLs, no attribution row needed |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | `.owlbear/research/1006-task-decomposition-approval-step.md` confirmed present; linked in task body under `## Research` |

### Files Updated

None — no documentation changes required.

### Scratch Files

None found matching `1006-*` pattern.

### Review Evidence

Present: `## Review Evidence` section with AC compliance table, tier-3 fallback analysis, confidence 0.91 → PASS.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md includes conditional approval step | Step 5b present: `askQuestions` with Approve/Reject options; skip clause for dispatch mode (line ~94-107) | PASS |
| Step references explicit mode prefix convention from planner.agent.md | Step 0: "mirrors `planner.agent.md` three-tier convention" — dispatch / user / fallback all listed | PASS |
| Approval uses askQuestions (not prose question) | Step 5b: "Call `askQuestions` with two options" — explicit tool call, not prose | PASS |
| Rejection ends workflow cleanly without creating tasks | "On reject: stop, report cancellation to the user. Do NOT call `create_task`." | PASS |

### Binding Refinements

- Three-tier mode detection in Step 0: all three tiers verified ✅
- `agent` tag prerequisite: acknowledged as manual action by architect — not a file deliverable ✅

### Test Results

- pytest: 664 passed, 6 failed (all in `serve/mcp-knowledge/tests/` — pre-existing, unrelated to this SKILL.md-only task)
- ruff: clean

### Architect Quality: 4/5

AC was specific, verifiable, and complete. Minor gap: binding refinements added three-tier detection requirement not in original AC — appropriate scoping by architect. No builder improvisation needed.

### Deduction Breakdown

- AC lines: 4/4 verified with file evidence → no deduction
- Lint: clean → no deduction
- AC quality: 4/5 (>3) → no deduction
- Reviewer evidence: present, detailed, PASS at 0.91 → no deduction
- Full-suite failures: 6 failures all in mcp-knowledge (pre-existing, outside task scope) → no deduction

### Confidence: 1.00

### Action: archive

### Notes

- Reviewer's tier-3 fallback divergence flag (SKILL.md abort-with-error vs planner.agent.md heuristic) is documented, acknowledged, and covered by #1007/#1008 cleanup. Not a defect for this task.
- Builder commit: `875942ee`
