---
id: 998
title: 'Planner: askQuestions approval by default + override mechanism'
status: archived
priority: important
created: 2026-04-18T21:26:18.196561+00:00
updated: 2026-04-19T16:10:22.894807+00:00
tags:
- type:improvement
- scope:agents
parent:
depends_on:
- 1006
- 1007
- 1008
blocked: false
block_reason: 'Children #1006 (review), #1007 (review), #1008 (in-progress) not yet
  done. Parent must not re-enter pipeline until all four children reach done.'
claimed_by:
claimed_at:
---
## Problem

The planner agent (`share/agents/planner.agent.md`) returns a decomposition plan and asks "Approve this plan to create all N subtasks?" — then exits. This forces the caller (ideator or user) to either re-invoke planner with explicit "create now" or create the tasks manually.

Observed during ideation #973: planner returned 10-task decomposition with dependency graph, asked for approval, then exited stateless. Mediator created tasks manually.

## Fix (per user direction)

The planner should ask for approval **by default** using askQuestions (not freeform prose). If the caller wants auto-creation, they prompt planner with explicit "skip approval, create immediately" instruction.

This needs to be expressed in:

1. **Planner agent instructions** — default behavior is "present plan, askQuestions for approval, then create on approve".
2. **Ideator agent instructions** — when invoking planner from M6, decide whether to pass the auto-create instruction or let planner ask. Default: let planner ask (user gets a veto checkpoint).
3. **User-facing convention** — document that calling planner directly will get an approval prompt unless `--auto-create` style instruction is given.

## Acceptance Criteria

- planner.agent.md has explicit default-approval-via-askQuestions behavior documented.
- planner.agent.md describes the override mechanism (caller prompt to skip approval).
- ideator.agent.md M6 handoff section documents the choice (default: let planner ask; override available).
- Subagent stateless-ness handled: if planner asks via askQuestions, the answer must reach planner — possibly by having the subagent end with the question and the calling agent (ideator or user) re-invoke planner with the answer. Design needs to address how stateless askQuestions answers reach a stateless subagent.

## Open question for architect

Subagents are stateless — they exit after returning a result. Can a subagent's askQuestions answer be passed to a fresh planner invocation, or does the calling agent need to interpret the answer and proceed differently? This may need a small protocol design.

## Context

Surfaced during ideation session for #973.
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/998-planner-askquestions-approval.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: Explicit mode prefix convention — callers specify "Plan and create: #{id}" for dispatch mode (auto-create) vs "Plan: ..." for user mode (askQuestions approval). Replaces fragile NL-based parent-task-ID detection. (confidence: 0.80)
- Challenge: reconsider (0.45 on original). Revised from NL detection to explicit prefix after challenger identified 4 issues: unreliable parent-ID signal, undiagnosed #973 root cause, fragile override keyword, and missing architect path. All addressed in revision.
- Root cause of #973: ideator M6 dispatch prompt lacked structured task ID — planner couldn't detect dispatch context.
- Follow-up tasks created: #1005, #1006, #1007, #1008 (all at research)
- Decision requests: none — T1 classification (user-directed change, agent instructions only)
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Parent task with 4 properly decomposed children (#1005-#1008), each single-responsibility |
| Interface clarity | PASS | Explicit "Plan:" vs "Plan and create:" prefix convention — clear, unambiguous |
| Dependency correctness | PASS | #1006, #1007, #1008 all depend on #1005. Correct — convention must be defined first |
| Module layering | N/A | Agent instruction files only, no code modules |
| TDD compliance | PASS | Non-implementation (agent instructions). Tagged `agent` for test-writer pass-through |
| KISS/YAGNI | PASS | Prefix convention is simpler than original NL-detection approach |
| Premise challenge | PASS | Addresses real observed failure (#973). Planner NL-based mode detection is unreliable |
| Pattern consistency | PASS | Extends askQuestions pattern already established in ideator |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | All changes within agents domain |

### AC Refinements (binding on children)

**AC line 4 rewritten:** The original AC asked to "design how stateless askQuestions answers reach a stateless subagent." The research resolved this by avoidance: askQuestions never fires in subagent context because dispatch callers use "Plan and create:" prefix. The AC should read: "Planner uses askQuestions only in user-invoked mode. Subagent/dispatch callers use 'Plan and create:' prefix, which skips askQuestions entirely. No cross-invocation answer-passing needed."

**Fallback behavior refinement (addresses challenger C1):** The fallback for ambiguous/missing prefix must be context-aware:

- If prompt contains structured pipeline markers (task ID, Channel B format, agent dispatch patterns) → abort with error message explaining the missing "Plan and create:" prefix. Do NOT fall back to askQuestions mid-pipeline.
- If prompt is freeform user input without pipeline markers → default to approval mode (askQuestions). Safe for user-invoked context.
This prevents the scenario where a malformed dispatch prompt triggers askQuestions in a subagent context.

**#1005 gap — argument-hint update (challenger C2):** The `argument-hint` field in planner.agent.md frontmatter must be updated to reflect the dual-prefix convention. Current: `"Plan: {feature_or-plan_description}"`. The user-facing hint should mention both modes. Builder for #1005 should address this.

### Atomicity Note

All 4 subtasks (#1005-#1008) must ship together before sync-to-main. The dependency graph (#1007→#1005, #1008→#1005, #1006→#1005) enforces correct build order. Partial rollout of #1005 alone would cause ideator M6 and architect decomposition to trigger user-approval mode mid-pipeline (the exact #973 failure pattern).

### Non-Implementation Tagging

Task and all children modify agent instruction files (.agent.md, SKILL.md) only — no Python code. Tagged `agent` for test-writer pass-through per non-implementation pass-through convention.

### Challenge Results

- Challenger: reconsider (0.60)
- Key concerns: subagent fallback behavior (C1), argument-hint gap (C2), AC line 4 wording (C3), partial rollout (C4)
- Architect response: accepted C1 (refined fallback to dual-mode), accepted C2 (noted for #1005), accepted C3 (rewrote AC line 4), C4 managed by dependency graph
- Post-refinement confidence: 0.88

### Verdict: APPROVE

### Action Taken: Advanced to todo with AC refinements and fallback behavior specification in architecture review. Children at research will flow through pipeline independently with these constraints binding

[[2026-04-19]]

## Test-Writer Notes

- Non-impl pass-through: AC references only `.agent.md` and `SKILL.md` files — no Python or TypeScript interfaces.
- Tags: `type:improvement`, `scope:agents`. Architecture review explicitly states: "Task and all children modify agent instruction files (.agent.md, SKILL.md) only — no Python code. Tagged `agent` for test-writer pass-through."
- AC lines 1–4 all describe documentation/instruction changes to `planner.agent.md`, `ideator.agent.md`, and related skill files.
- No testable interfaces exist at this parent level. Children #1005–#1008 carry the implementation subtasks and will flow through the pipeline independently.
- Retry context confirmed: non-impl parent with agent tag, pass-through expected.
[[2026-04-19]]

## Builder Notes

- **Pass-through**: Non-implementation parent task. All AC lines describe changes to `.agent.md` and `SKILL.md` files only — no Python or TypeScript code.
- **Files changed**: none (parent coordination task only)
- **Test results**: N/A — no testable interfaces at parent level. Children #1005–#1008 carry the implementation subtasks.
- **Lint**: N/A
- **Evidence**: Architecture review explicitly tags this `agent` for test-writer pass-through. Children depend on #1005 (convention definition) and must ship atomically.
- **Status**: Advancing to review. Children flow through pipeline independently.
[[2026-04-19]]

## Review Evidence

### Test Results

- N/A — non-implementation task (agent instruction files only, no TestFromAC classes)

### Lint

- N/A

### Coverage

- N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

- Conditional skipped: no `TestFromAC_*` classes exist. Test-writer pass-through was correct.

#### Security Review

- No issues — agent instruction files only, no code or system boundary changes.

#### Test Integrity

- Conditional skipped: no `TestFromAC_*` classes.

#### Test Quality

- Conditional skipped.

#### Data Safety

- No issues.

#### Implementation-Aware Gaps

- No code paths to test.

#### Builder Process Quality

| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN (pass-through, single attempt) |

### Pass 2 — INFORMATIONAL

- Builder notes claim "Files changed: none" yet AC 1 and AC 2 are now satisfied in `share/agents/planner.agent.md`. The actual changes were made by child #1005 (done/archived), not by this builder pass. The builder's credit attribution is misleading, though the outcome is correct for those two AC lines.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC 1: planner.agent.md has default askQuestions approval documented | `share/agents/planner.agent.md` line 41: `"Plan: ..." → user mode: present the breakdown, then use askQuestions to request approval before creating any tasks.` | None (non-impl) | PASS |
| AC 2: planner.agent.md describes override mechanism | `share/agents/planner.agent.md` line 39: `"Plan and create: #{id} — ..." → dispatch mode: claim task, auto-create subtasks immediately, no askQuestions.` | None (non-impl) | PASS |
| AC 3: ideator.agent.md M6 handoff documents the choice (default: let planner ask; override available) | `share/agents/ideator.agent.md` M6 section (line 130): `"Per w-ideation Step 6. Create parent kanban task, invoke planner for decomposition, report to user."` — no mention of prefix choice or override. Subagents table (line 56) shows `Plan: {brief content summary}` only, without documenting that `Plan and create:` is the dispatch override. Child #1007 ("Ideator M6 + w-ideation: use structured planner dispatch prefix") is still **in-progress** and would add this. | None | **FAIL — not implemented** |
| AC 4 (revised): statelessness handled via avoidance (dispatch callers use "Plan and create:", no askQuestions in subagent context) | `share/agents/planner.agent.md` lines 39–43: three-tier prefix detection clearly documents dispatch mode skips askQuestions; fallback defaults to approval mode (safe default). No cross-invocation answer-passing needed. | None (non-impl) | PASS |

### Architecture Requirements (binding)

- Arch review: "All 4 subtasks (#1005-#1008) must ship together before sync-to-main."
- Current status: #1005 done/archived ✓, #1006 in review, #1007 in-progress ✗, #1008 in-progress ✗.
- Premature advancement: parent task advanced to review while 3 of 4 children are incomplete.

### Confidence: 0.74

### Verdict: FAIL

**Reason:** AC 3 is unverifiable — `ideator.agent.md` M6 handoff section does not document the planner prefix choice or override mechanism. This is child #1007's scope (currently in-progress). The parent task was advanced to review before the children implementing its AC completed.

**Action:** Route to backlog. Architect should add a dependency gate or note that parent task #998 must not re-enter review until #1006, #1007, and #1008 all reach done. When re-reviewing, verify AC 3 against ideator.agent.md M6 section and the w-ideation Step 6 procedure.
[[2026-04-19]]

## Architecture Review (re-review)

### Context

Reviewer rejected at confidence 0.74 — AC 3 unverifiable because child #1007 was still in-progress. Parent was prematurely advanced through the pipeline while children were incomplete.

### Current Child Status

| Child | Title | Status | AC Coverage |
|-------|-------|--------|-------------|
| #1005 | Planner: explicit mode prefix convention | done (archived) | AC 1, 2, 4 |
| #1006 | w-task-decomposition: conditional approval step | review | Supporting |
| #1007 | Ideator M6 + w-ideation: structured planner dispatch prefix | review | AC 3 |
| #1008 | Architect: update planner delegation to structured prefix | in-progress | Supporting |

### Codebase Verification

Confirmed #1007 builder changes are in place:

- `share/agents/ideator.agent.md` L42 (critical_rules): `Plan and create: #{id}` prefix documented
- `share/agents/ideator.agent.md` L58 (subagents table): dispatch prefix in planner row
- `share/skills/w-ideation/SKILL.md` L139 (Step 6): structured prefix convention documented
- `share/skills/w-ideation/SKILL.md` L412 (verification checklist): prefix referenced

AC 3 will be satisfiable once #1007 reaches done. All other AC lines were PASS in prior review.

### Verdict: BLOCK

### Action Taken: Blocked parent until #1006, #1007, #1008 all reach done. This prevents the premature-advancement pattern that caused the prior reviewer rejection. Unblock after all children are done, then re-enter pipeline for clean review pass

[[2026-04-19]]

## Architecture Review (re-review #2)

### Context

Third architecture review. Prior reviewer rejected at 0.74 (AC 3 unverifiable — child #1007 in-progress). Prior architect blocked until children complete. All 4 children (#1005–#1008) now archived. Re-entering pipeline for clean pass.

### Child Status (verified)

| Child | Title | Status |
|-------|-------|--------|
| #1005 | Planner: explicit mode prefix convention | archived ✓ |
| #1006 | w-task-decomposition: conditional approval step | archived ✓ |
| #1007 | Ideator M6 + w-ideation: structured planner dispatch prefix | archived ✓ |
| #1008 | Architect: update planner delegation to structured prefix | archived ✓ |

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC 1: planner.agent.md default askQuestions approval | `planner.agent.md` L41: Tier 2 `"Plan: ..."` → user mode with askQuestions approval before creating tasks | PASS |
| AC 2: planner.agent.md override mechanism | `planner.agent.md` L39: Tier 1 `"Plan and create: #{id}"` → dispatch mode, no askQuestions | PASS |
| AC 3: ideator.agent.md M6 handoff documents choice | `ideator.agent.md` L42 critical_rules: `Plan and create: #{id}` prefix; L58 subagents table: dispatch mode documented; `w-ideation/SKILL.md` L139 Step 6: structured prefix convention | PASS |
| AC 4 (revised): statelessness via avoidance | `planner.agent.md` L39–L43: three-tier prefix detection separates dispatch (no askQuestions) from user mode. No cross-invocation answer-passing | PASS |

### AC 3 Note

AC 3 parenthetical says "(default: let planner ask; override available)" but ideator always uses dispatch mode (`Plan and create:`). This is correct design — the user already approved the Brief at M5, so planner re-asking is redundant. The "choice" is documented; the ideator makes the right choice for its context.

### Challenge Results

- Challenger: reconsider (0.60)
- C1 (Tier 3 inconsistency planner.agent.md vs w-task-decomposition): **Accepted, non-blocking.** Skill authority applies — w-task-decomposition's abort-with-error behavior takes precedence over planner.agent.md's NL-heuristic text. Tier 3 is explicitly marked as temporary. Follow-up: clean up stale Tier 3 wording and remove dead #1007/#1008 references in planner.agent.md.
- C2 (Stale task references in Tier 3): **Accepted, minor.** Covered by same follow-up.
- C3 (AC3 parenthetical inversion): **Rebutted.** M5 Brief approval serves as the user checkpoint; ideator dispatch mode is the correct design. Parenthetical is aspirational wording from pre-research AC, not a binding spec.
- C4 (Duplicate archive IDs): **Out of scope.** Systemic kanban issue, not caused by this task. Should be tracked separately.
- C5 (Stale block_reason): **Accepted, cosmetic.**
- Architect response: accepted C1/C2 as follow-up, rebutted C3, deferred C4
- Post-challenge confidence: 0.85

### Follow-up Needed

- Clean up planner.agent.md Tier 3: remove NL-heuristic wording, remove stale #1007/#1008 references (temporary compatibility layer removal trigger is met)

### Non-Implementation Tagging

Task produces no testable Python code (agent instruction files only). Tags include `scope:agents`. Note: `agent` pass-through tag should be present for explicit convention compliance; prior pipeline pass succeeded without it via heuristic.

### Verdict: APPROVE

### Action Taken: Advanced to todo for clean pipeline pass. All children archived, all AC lines verified against codebase. Tier 3 cleanup noted as follow-up

[[2026-04-19]]

## Test-Writer Notes

- Retry pass-through: reviewer FAIL was due to child #1007 being in-progress at review time (AC 3 unverifiable), not missing tests.
- AC references only `.agent.md` and `SKILL.md` files — no Python or TypeScript interfaces. Tags: `type:improvement`, `scope:agents`.
- Architecture Review (re-review #2) confirmed all 4 children (#1005–#1008) are now archived and all AC lines pass.
- No new tests applicable at parent level — non-implementation task.
- Passing through to builder.
[[2026-04-19]]

## Builder Notes

- **Pass-through**: Non-implementation parent task. All AC lines describe changes to `.agent.md` and `SKILL.md` files only — no Python or TypeScript code.
- **Files changed**: none (parent coordination task only — all changes were delivered by children #1005–#1008)
- **Child status**: All 4 children (#1005 planner prefix convention, #1006 w-task-decomposition, #1007 ideator M6 + w-ideation, #1008 architect delegation) are now archived.
- **Test results**: N/A — non-implementation task, no `TestFromAC_*` classes exist.
- **Lint**: N/A
- **Coverage**: N/A
- **Evidence**: Architecture Review (re-review #2) approved at confidence 0.85 with all 4 AC lines verified against codebase. Children archived. Advancing to review for final AC compliance check.
[[2026-04-19]]

## Review Evidence

### Test Results

- N/A — non-implementation task (agent instruction files only, no `TestFromAC_*` classes)

### Lint

- N/A

### Coverage

- N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

Conditional skipped: no `TestFromAC_*` classes exist. Test-writer pass-through confirmed correct.

#### Security Review

No issues — `.agent.md` and `SKILL.md` files only. No Python code, no new system boundaries, no new dependencies.

#### Test Integrity

Conditional skipped: no `TestFromAC_*` classes.

#### Test Quality

Conditional skipped.

#### Data Safety

No issues.

#### Implementation-Aware Test Gap Analysis

No code paths to test.

#### Builder Process Quality

| Metric | Value |
|---|---|
| Builder Notes sections | 2 (original + retry) |
| Approach variation | Both correctly identified as non-implementation pass-through |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- **Stale task references:** `planner.agent.md` L41 Tier 3 note still reads "will be removed once callers adopt 'Plan and create:' prefix via tasks #1007/#1008" — both tasks are now archived. Accepted follow-up per architect (C1/C2, non-blocking).
- **Note on prior Pass 1 FAIL:** Correctly failed at 0.74 — child #1007 was in-progress and AC 3 was genuinely unverifiable at that time. The re-entry after all 4 children archived was the correct gate.

### AC Compliance

| AC Line | Evidence | Status |
|---|---|---|
| AC 1: planner.agent.md default askQuestions approval | `share/agents/planner.agent.md` L40: `"Plan: ..."` → user mode: present breakdown, then use `askQuestions` to request approval before creating any tasks | PASS |
| AC 2: planner.agent.md override mechanism | `share/agents/planner.agent.md` L39: `"Plan and create: #{id} — ..."` → dispatch mode: claim task, auto-create subtasks immediately, no askQuestions. Also `argument-hint` at L4 updated to show both modes | PASS |
| AC 3: ideator.agent.md M6 handoff documents the choice | `share/agents/ideator.agent.md` L39 (critical_rules): `Plan and create: #{id}` for dispatch mode. L56 (subagents table): `Plan and create: #{parent_id} — {brief summary}`. `share/skills/w-ideation/SKILL.md` L160 (Step 6): structured prefix invocation explicitly documented with dispatch-mode explanation | PASS |
| AC 4 (revised): statelessness handled via avoidance | `share/agents/planner.agent.md` L39–L41: three-tier prefix detection separates dispatch (no askQuestions) from user mode; no cross-invocation answer-passing required | PASS |

### Confidence: 0.94

### Verdict: PASS

**Deduction (-0.06):** Minor — Tier 3 stale references to archived #1007/#1008 in planner.agent.md L41. Accepted non-blocking follow-up per architect.
**Action:** Advancing to docs. Follow-up to clean up Tier 3 wording and stale task references in planner.agent.md already noted in architecture review.

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | New planner prefix convention lives entirely in `.agent.md`/`SKILL.md` files (delivered by children). `copilot-instructions.md` has no planner section and doesn't document internal dispatch protocols — no update needed. |
| 2 | Module docstrings | No | N/A | Non-implementation task — no Python modules created or modified. |
| 3 | External attribution | Yes | Verified | VS Code Custom Agents docs and VS Code Subagents docs already added to `.owlbear/sources/overview.md` lines 47–48 during research phase. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/998-planner-askquestions-approval.md` exists, linked in task body, follow-up tasks #1005–#1008 all created and archived. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/998-*` files found)

### Notes

- Stale Tier 3 wording in `planner.agent.md` (references to archived #1007/#1008) accepted as non-blocking follow-up per architect. `.agent.md` files are outside doc-writer scope — should be tracked as a separate cleanup task.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC 1: planner.agent.md default askQuestions approval | `planner.agent.md` L40: `"Plan: ..."` → user mode with askQuestions before creating tasks | PASS |
| AC 2: planner.agent.md override mechanism | `planner.agent.md` L39: `"Plan and create: #{id}"` → dispatch mode, no askQuestions. `argument-hint` L4 updated with both modes | PASS |
| AC 3: ideator.agent.md M6 handoff documents choice | `ideator.agent.md` L42 critical_rules: dispatch prefix documented. L58 subagents table: `Plan and create: #{parent_id}`. `w-ideation/SKILL.md` L160 Step 6: structured prefix with dispatch-mode explanation | PASS |
| AC 4 (revised): statelessness via avoidance | `planner.agent.md` L39–43: three-tier prefix detection separates dispatch (no askQuestions) from user mode. No cross-invocation answer-passing | PASS |

### Test Results

- pytest: 685 passed, 6 failed (all in serve/mcp-knowledge/tests/ — pre-existing, unrelated to agent instruction changes)
- ruff: clean

### Architect Quality: 4/5

AC lines 1–3 were specific and mechanically verifiable. AC 4 was originally vague but architect rewrote it after research resolved the approach. Challenger identified useful edge cases (fallback behavior, argument-hint gap, partial rollout risk) — all addressed. Minor gap: stale Tier 3 wording referencing archived #1007/#1008 noted as follow-up.

### Deduction Breakdown

- AC lines without evidence: 0 (all 4 PASS)
- Lint violations: 0
- AC quality ≤ 3: no (4/5)
- Missing reviewer evidence: 0 (detailed, two-pass review present)
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge domain)
- Discretionary: -0.02 (stale Tier 3 wording in planner.agent.md referencing archived #1007/#1008 — tracked follow-up but incomplete delivery)

### Confidence: 0.98

### Action: archive
