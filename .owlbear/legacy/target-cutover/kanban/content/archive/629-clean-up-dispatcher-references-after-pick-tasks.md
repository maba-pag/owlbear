---
id: 629
title: Clean up dispatcher references after pick_tasks migration
status: archived
priority: medium
created: 2026-04-05T10:42:19.8702275+02:00
updated: 2026-04-05T23:29:47.7272256+02:00
started: 2026-04-05T23:29:47.7272256+02:00
completed: 2026-04-05T23:29:47.7272256+02:00
tags:
    - scope:agents
    - phase-2
    - type:docs
parent: 619
depends_on:
    - 622
claimed_by: forge-ivory
claimed_at: 2026-04-05T23:29:38.1061324+02:00
class: standard
---

## Acceptance Criteria (architect-revised)

1. `share/instructions/agent-common.instructions.md`: remove dispatcher row from Per-Agent Section Mapping table
2. `share/skills/r-pipeline-protocol/SKILL.md` ~L97: replace "the dispatcher will dispatch the planner" with "the orchestrator will route the task to the planner"
3. `share/skills/r-pipeline-protocol/SKILL.md` ~L186: replace "blocked for triage by dispatcher" with "blocked for triage by orchestrator"
4. `share/agents/README.md`: remove `dispatcher` from T1 Orchestrator tier row; update agent count from "14" to "15"
5. `share/skills/h-agent-structure/SKILL.md` ~L38: remove `dispatcher` from T1 Orchestrator tier row
6. `share/agents/dispatcher.agent.md`: **verify** #623 applied deprecation header — do NOT edit (owned by #623)
7. `share/skills/w-task-decomposition/SKILL.md` L19: replace "dispatcher-dispatched" with "orchestrator-dispatched"

## Context

After #622 wires pick_tasks into the orchestrator, these cross-cutting references to the dispatcher agent become stale. See .owlbear/research/wire-pick-tasks-orchestrator.md.

[[2026-04-05]] Sun 14:17


## Research Note from #623
- GAP: `share/skills/w-task-decomposition/SKILL.md` L19 references "dispatcher-dispatched" — add to cleanup scope

[[2026-04-05]] Sun 16:46
## Research
- Research doc: .owlbear/research/cleanup-dispatcher-refs.md
- Sources: 9 studied, 7 high-relevance (all codebase-internal)
- Recommendation: Proceed as-is with 2 AC refinements (confidence: .92)
- Follow-up tasks created: none (refinements apply to #629 itself)
- Decision requests: none - T1 autonomous docs cleanup

### AC Refinements for Architect
1. Narrow AC item 6 (dispatcher.agent.md): change to verification-only - #623 handles deprecation
2. Add AC item 7: w-task-decomposition/SKILL.md L19 - replace dispatcher-dispatched with orchestrator-dispatched
3. Minor: README.md agent count is 14 but 16 files exist on disk - update while editing

## Challenge Results
- Challenge: SKIP - T1 docs cleanup within approved #619 migration plan
- Tier: T1 (autonomous), no new capability or architecture change
- Confidence: .92

[[2026-04-05]] Sun 16:47
Research complete. Doc at .owlbear/research/cleanup-dispatcher-refs.md. All 6 AC items verified against codebase; 1 overlap with #623 (narrow to verification), 1 gap found (w-task-decomposition L19). No follow-up tasks needed.

[[2026-04-05]] Sun 17:58
## Architecture Review

### AC Refinements (binding for downstream agents)

| Original AC | Issue | Revised AC |
|-------------|-------|------------|
| Item 6: "dispatcher.agent.md: add deprecated header OR delete" | Overlaps #623 which owns deprecation (in-progress) | Narrowed to verification: confirm #623 applied deprecation header. Do NOT edit. |
| (missing) | w-task-decomposition/SKILL.md L19 "dispatcher-dispatched" not in any task scope | Added as item 7: replace "dispatcher-dispatched" with "orchestrator-dispatched" |
| Item 4: README agent count | Says 14, disk has 16 files (15 active after dispatcher deprecated) | Update count to 15 while editing the T1 tier row |

### Codebase Verification

- Searched `share/**/*.md` for "dispatcher": 14 matches total
- 7 in-scope for #629 (AC items 1-5, 7 confirmed; item 6 verification only)
- 4 in `w-dispatch-planning/SKILL.md`: ARCHIVED file, acceptable as-is
- 3 in `dispatcher.agent.md`: owned by #623 (in-progress)
- Agent count on disk: 16 `.agent.md` files; 15 active after #623 deprecates dispatcher

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update stale dispatcher references across docs |
| Interface clarity | PASS (refined) | All 7 AC items specify exact file, line, and replacement text |
| Dependency correctness | PASS | Depends on #622 (review). #623 overlap resolved by narrowing item 6 to verification |
| Module layering | N/A | Docs-only changes, no code |
| TDD compliance | PASS | Non-impl task; tagged type:docs (pass-through) |
| KISS/YAGNI | PASS | Mechanical text substitution, minimal scope |
| Premise challenge | PASS | Stale references confirmed in codebase; cleanup necessary |
| Pattern consistency | PASS | Follows migration cleanup pattern from parent #619 |
| Security surface | PASS | No new system boundaries; docs-only |
| Single domain | PASS | All files in share/ docs domain (scope:agents) |

### Challenge Results
- Challenger: FALLBACK (not in available subagent list)
- Mitigant: T1 docs cleanup within approved #619 migration plan; no architecture decisions
- Architect confidence: .92

### Verdict: APPROVE (via REFINE)
### Action: AC refined (item 6 narrowed, item 7 added, agent count clarified); advancing backlog to todo

[[2026-04-05]] Sun 17:58
Architecture review complete. AC refined: item 6 narrowed to verification (overlap with #623), item 7 added (w-task-decomposition L19), agent count correction. All 10 criteria PASS. Confidence .92.

[[2026-04-05]] Sun 20:29
## Test-Writer Notes\n- Non-implementation task (tagged type:docs) — no tests applicable.\n- All 7 AC items are `.md` file text substitutions in share/ (instructions, skills, agents). No testable Python interfaces exist.\n- Passing through to builder.

[[2026-04-05]] Sun 20:53
## Builder Notes\n- Non-implementation task — all changes are `.md` text substitutions in `share/`.\n- AC item 6 (dispatcher.agent.md): verified deprecation header present from #623 — no edit made.\n- AC item 1: removed `dispatcher` row from Per-Agent Section Mapping table in `agent-common.instructions.md`.\n- AC item 2: replaced \"the dispatcher will dispatch the planner\" → \"the orchestrator will route the task to the planner\" in `r-pipeline-protocol/SKILL.md`.\n- AC item 3: replaced \"blocked for triage by dispatcher\" → \"blocked for triage by orchestrator\" in `r-pipeline-protocol/SKILL.md`.\n- AC item 4: removed `dispatcher` from T1 tier row; updated agent count 14 → 15 in `share/agents/README.md`.\n- AC item 5: removed `dispatcher` from T1 tier row in `h-agent-structure/SKILL.md`.\n- AC item 7: replaced \"dispatcher-dispatched\" → \"orchestrator-dispatched\" in `w-task-decomposition/SKILL.md`.\n- 5 files changed, 0 tests (type:docs pass-through), no ruff applicable.

[[2026-04-05]] Sun 21:57
## Review Evidence

**Type:** type:docs pass-through — no tests applicable, no ruff applicable.

### AC Compliance Table

| AC # | File | Evidence | Status |
|------|------|----------|--------|
| 1 | `agent-common.instructions.md` | Per-Agent Section Mapping table has 9 rows (researcher→curator); no dispatcher row present | ✅ PASS |
| 2 | `r-pipeline-protocol/SKILL.md` ~L97 | Text reads: "the orchestrator will route the task to the planner" — confirmed | ✅ PASS |
| 3 | `r-pipeline-protocol/SKILL.md` ~L186 | Text reads: "Stale tasks — blocked for triage by orchestrator" — confirmed | ✅ PASS |
| 4 | `share/agents/README.md` | Header: "15 agent definitions"; T1 tier row: "orchestrator" only — no dispatcher | ✅ PASS |
| 5 | `h-agent-structure/SKILL.md` | T1 tier row: "orchestrator" only — no dispatcher | ✅ PASS |
| 6 | `dispatcher.agent.md` (verify only) | Deprecation header present: "> **Deprecated.** Replaced by pick_tasks MCP tool (#621). See #619 migration plan." — no edit made | ✅ PASS |
| 7 | `w-task-decomposition/SKILL.md` L19 | Text reads: "When **orchestrator-dispatched** (parent task ID provided)" — no dispatcher reference | ✅ PASS |

### Residual Reference Sweep

Grepped "dispatcher" in all 5 changed files: **0 matches** in each. No stale references leaked.

### Security

Docs-only changes. No code paths, no system boundaries, no security surface. N/A.

### Deductions

None. All AC items independently verified against file content.

**Confidence: .97 → PASS**

[[2026-04-05]] Sun 22:02
## Docs Gate

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API — copilot-instructions.md | No | ✅ N/A | Grepped `.github/copilot-instructions.md` for "dispatcher": 0 matches. No tables/sections reference dispatcher. |
| 2 | Module Docstrings | No | ✅ N/A | All 5 changed files are `.md` in `share/`. No Python modules created or modified. |
| 3 | External Attribution | No | ✅ N/A | Research note states all 7 sources are codebase-internal. No external patterns used. |
| 4 | CLI Changes | No | ✅ N/A | No CLI commands added or modified. |
| 5 | Research Doc | Yes | ✅ PASS | `.owlbear/research/cleanup-dispatcher-refs.md` exists. Linked in task body. |

**Files updated:** None — existing share/ docs were the subject of the task; copilot-instructions.md requires no change.

**Scratch files cleaned:** None found for `629-*`.

**Verdict:** All checklist items evaluated with evidence. No documentation files require updating. Docs gate passed.

[[2026-04-05]] Sun 23:29
## Audit
### AC Verification
| AC | Evidence | Status |
|----|----------|--------|
| 1 | grep dispatcher agent-common.instructions.md = 0 matches; diff: row removed | PASS |
| 2 | grep dispatcher r-pipeline-protocol/SKILL.md = 0; diff L97: orchestrator will route | PASS |
| 3 | diff L186: blocked for triage by orchestrator | PASS |
| 4 | diff: T1 row = orchestrator only; count 14->15 | PASS |
| 5 | grep dispatcher h-agent-structure/SKILL.md = 0; diff: T1 row = orchestrator | PASS |
| 6 | grep Deprecated dispatcher.agent.md L13: deprecation header from 623 | PASS |
| 7 | grep dispatcher w-task-decomposition/SKILL.md = 0; diff L19: orchestrator-dispatched | PASS |

### Test Results
- pytest: 2952 passed, 406 failed, 8 skipped -- 0 failures in task scope
- ruff: All checks passed

### Architect Quality: 5/5

### Deduction Breakdown
- AC lines without evidence: 0
- Lint violations: 0
- AC quality: 5/5 (no deduction)
- Reviewer section: present, detailed, .97 PASS
- Full-suite failures in scope: 0
- Note: builder left deliverables uncommitted; committed during audit

### Confidence: 1.00
### Action: archive
