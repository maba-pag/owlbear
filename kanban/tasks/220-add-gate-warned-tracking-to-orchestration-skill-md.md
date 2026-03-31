---
id: 220
title: Add gate_warned tracking to orchestration SKILL.md
status: todo
priority: needed
created: 2026-03-30T15:17:02.0028127+02:00
updated: 2026-03-31T03:58:47.3875497+02:00
tags:
    - scope:agents
    - quality
    - type:config
depends_on:
    - 219
class: standard
---

## Objective
Document gate_warned cycle tracking in the orchestration skill so the orchestrator surfaces repeated gate failures to the user.

## AC
- [ ] New tracking state: gate_warned dict (task_id to count) alongside stale_retried
- [ ] Orchestrator increments count for each task in gate_warnings each cycle
- [ ] When count >= 2, orchestrator logs structured warning at end of cycle
- [ ] gate_warned IDs cleared when task no longer appears in gate_warnings
- [ ] Step 1 updated to pass gate_warned context to planner (optional, for future use)
- [ ] Step 3 (Loop) output format updated to include gate warnings when count >= 2

## Context
See docs/research/gate-blocked-task-remediation.md S4.
Mirrors stale_retried pattern from orchestration SKILL.md.
Depends on #219 (gate_warnings field must exist before orchestrator can consume it).

[[2026-03-30]] Mon 21:19
[[2026-03-30]] Sun 22:00
## Research
Parent research: docs/research/gate-blocked-task-remediation.md (#216, .85 confidence, 6 sources)

Checklist validated:
1. Theoretical validity: Sound. Extends stale_retried tracking pattern in orchestration SKILL.md. Counter-based escalation is proven (GitHub stale S3, Azure DevOps S6).
2. Environment audit: N/A, SKILL.md documentation change only.
3. Prior art: Covered by #216. Direct precedent: stale_retried in orchestration SKILL.md (context budget section). GitLab CI blocked pipeline (S4), GitHub stale action (S3).
4. Technical feasibility: Confirmed. Skill doc edit, read by LLM. #219 established gate_warnings JSON output as input.
5. Architecture fit: Perfect mirror of stale_retried. Planner emits gate_warnings (from #219), orchestrator tracks counts. No new system boundaries.
6. Implementation approach: Add gate_warned dict to context budget alongside stale_retried. Process gate_warnings from planner JSON after Step 1. Threshold check (count>=2) at end-of-cycle in Step 3.

Implementation notes for builder:
- Context budget: add gate_warned dict alongside stale_retried (dict not set: maps task_id to count)
- After receiving planner JSON in Step 1: extract gate_warnings array, increment gate_warned counts
- Cleanup: clear IDs from gate_warned when they no longer appear in gate_warnings
- Step 3 output format: add gate warning lines when any count >= 2
- Step 1: optionally pass gate_warned context to planner (future use)
- Update 'No retry tracking state' bullet to list gate_warned alongside stale_retried
- Update self-critique checklist with gate_warned verification item

[[2026-03-30]] Mon 22:42
## Test-Writer Notes
- Non-implementation task (tagged type:config, quality) — no tests applicable.
- Passing through to builder.

[[2026-03-31]] Tue 03:58
## Review Evidence

### No Tests / Lint
Documentation-only task (type:config). Test-writer confirmed no tests applicable. No Python files changed — ruff not applicable.

### Builder Commit
`c89c215 docs: add gate_warned tracking to orchestration SKILL.md (#220, builder)`

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| gate_warned dict alongside stale_retried | Context budget updated: lists gate_warned alongside stale_retried and sequential_remaining; new Gate-warned tracking bullet with task_id to count | PASS |
| Increment count each cycle | Step 1 addition: "For each task ID in gate_warnings, increment its count in the gate_warned dict." | PASS |
| Log warning when count >= 2 | Output format example: `Cycle 1 (Gate Warning): #205 stuck at review gate for 2 cycles`; prose: "appear only when any task count >= 2"; self-critique item added | PASS |
| Clear IDs when no longer in gate_warnings | Context budget bullet + Step 1 step 2 + self-critique checklist all reference cleanup | PASS |
| Step 1 passes gate_warned to planner (optional) | "Optionally pass gate_warned context to the planner (future use)" with runSubagent example | PASS |
| Step 3 output format updated | Gate Warning line in output example, one line per warned task, threshold condition stated | PASS |

### Out-of-Scope Change — FAIL

Builder modified wave assembly drop rule (Step 2, Phase 1, item 7) outside the AC:

Before: Any wave with exactly one task where that task is not an auditor, drop.
After:  Any wave with exactly one task where that task is not an auditor or a retry, drop.

Adding `or a retry` changes orchestrator wave-dispatch behavior for retry tasks — solo retry waves now survive the drop rule. This change is not covered by any AC line in #220, not mentioned in builder notes or commit message, and has no justification or prior art cited.

Builder must either: (a) revert this change and create a separate task with proper AC, or (b) add it as a separate explicitly-scoped AC item in a new task.

### Verdict: FAIL — confidence .82 (below .90 threshold)
Out-of-scope behavioral change to drop rule with no AC coverage.
