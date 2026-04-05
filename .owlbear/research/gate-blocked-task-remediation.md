# Gate-Blocked Task Remediation for Dispatch Planning

> **Owning task:** #216 — Add remediation process for gate-blocked tasks in dispatch-planning
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

When the planner's gates (3, 4, or 5) exclude a task from dispatch, the exclusion is
silent — no log, no flag, no follow-up action. Tasks that hit false-positive gate checks
or bypassed the pipeline sit at their current status indefinitely. The manual triage
session (2026-03-30) found 5 such tasks (#181, #191, #196, #151, #153), all stuck due
to Gate 4 (TW:MISSING) false positives.

**Question:** How should the system detect and surface gate-blocked tasks, and what
remediation action (if any) should be taken automatically?

Gate 5 (AC:MISSING) is explicitly excluded from this analysis per task AC — it flags
missing content, not a missing process step.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | OwlBear dispatch-planning SKILL.md | (internal) | Existing gate structure, stale-task guided retry pattern, Board Scan markers |
| S2 | OwlBear orchestration SKILL.md | (internal) | `stale_retried` cross-cycle tracking, planner-orchestrator state passing |
| S3 | GitHub actions/stale action | https://github.com/marketplace/actions/close-stale-issues | Timer-based stale detection: label after N days, close after M more |
| S4 | GitLab CI blocked pipeline | https://docs.gitlab.com/ci/jobs/job_control/ | Pipeline "blocked" status visibility, manual job and retry patterns |
| S5 | Jenkins restart-from-stage | https://www.jenkins.io/doc/book/pipeline/running-pipelines/ | Manual re-entry from any completed stage, preserving prior state |
| S6 | Azure DevOps impediment tracking | https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-issues-impediments | Blocker visibility via queries, aging-based escalation ("blockers active >7 days") |

## 3. Analysis

### 3.1 Approach comparison

| Criterion | A: `gate_warnings` field (proposed) | B: Auto-move back to earlier status | C: Block after N cycles | D: Periodic hygiene agent |
|-----------|-------------------------------------|--------------------------------------|-------------------------|---------------------------|
| Planner stays read-only | Yes | **No** — violates planner's sole-mutation constraint (S1) | No — planner blocks tasks | Yes |
| Orchestrator complexity | Low — add dict tracking (mirrors `stale_retried`, S2) | Low | Medium — needs both tracking AND blocking | High — new agent, new dispatch trigger |
| Feedback loop risk | None | **High** — move back → re-gate → fail → move back (infinite) | Low | Low |
| Visibility for user | High — logged at end of cycle (like actions/stale label, S3) | Low — silent reprocessing | Medium — blocked tasks visible in `--blocked` | Medium — delayed reporting |
| Aligns with existing patterns | Yes — extends JSON output + orchestrator tracking (S1, S2) | No — new mutation class | Partially — uses `--block` but adds planner mutation | No — new agent concept |
| KISS score | High | Low | Medium | Low |
| Implementation effort | ~20 lines in skill docs | ~15 lines + principle violation | ~25 lines + principle violation | ~100 lines new skill |

### 3.2 How established systems handle this

**Timer/cycle-based detection** is the dominant pattern (S3, S6): GitHub's stale action
counts days of inactivity; Azure DevOps queries filter blockers by age. Both surface
the problem to humans rather than auto-resolving.

**Visibility before action** is universal (S3, S4, S6): GitLab shows "blocked" status on
the pipeline UI. GitHub posts a comment before closing. Azure DevOps uses queries to
surface aging blockers. None auto-move work backward — they escalate to humans.

**Manual re-entry** (S5): Jenkins lets users manually restart from a stage. This is the
equivalent of our manual triage session — effective but not automated.

### 3.3 Gate 5 (AC:MISSING) exclusion rationale

Gate 5 detects missing acceptance criteria content — a fundamentally different class
of problem. Gates 3 and 4 check process compliance (was the architect consulted? was
the test-writer run?) where false positives are possible. Gate 5 checks for content
existence, which is binary and has no false-positive risk. It also already has a
natural remediation path: the architect adds AC during backlog review.

### 3.4 Cycle-count tracking mechanism

The planner is stateless between cycles (S2). Rather than adding state to the planner,
the orchestrator should track gate warning counts (like it tracks `stale_retried`) and
pass context to the planner. Two sub-approaches:

| Sub-approach | Description | Simplicity |
|-------------|-------------|------------|
| **A1: Planner always emits, orchestrator counts** | Planner reports all gate failures each cycle. Orchestrator filters at threshold. | Higher — planner stays fully stateless |
| **A2: Orchestrator passes counts, planner filters** | Orchestrator passes `gate_fail_counts`, planner emits only when count >= 2 | Lower — planner needs input parsing |

**Recommendation (A1):** Planner always emits `gate_warnings`. Orchestrator tracks
counts and logs to user when count >= 2. This mirrors `stale_retried` tracking (S2)
and keeps the planner stateless. (.85 confidence)

## 4. Recommendation (.85 confidence)

**Option A (gate_warnings field) with sub-approach A1 (always-emit, orchestrator counts).**

**Rationale:**
- Extends existing patterns (JSON output, orchestrator cycle tracking)
- Planner stays read-only and stateless (core constraint, S1)
- User gets visibility at end of cycle (proven pattern from S3, S4, S6)
- No auto-movement — avoids feedback loops and principle violations
- KISS-aligned: minimal changes to two skill documents

**Option B (auto-move) REJECTED:**
- Violates planner read-only constraint. The planner's sole mutation exception is
  decision resolution (Recipe 0), which is a carefully scoped special case (S1).
- Auto-moving creates feedback loops: a task moved back to `todo` would be re-gated
  next cycle and fail again if the root cause isn't fixed.
- Silent reprocessing hides the problem. All established systems (S3, S4, S5, S6) favor
  visibility and human escalation over automatic backward movement.
- Jenkins restart-from-stage (S5) requires explicit user action, not automation.

**Implementation sketch:**

1. **dispatch-planning SKILL.md** — new section "Gate failure remediation" after gate
   checks. Planner emits `gate_warnings` array in JSON for every task excluded by
   Gate 3 or Gate 4. Format: `{"id": N, "gate": "Gate 3|4", "reason": "..."}`.
2. **orchestration SKILL.md** — new tracking: `gate_warned` dict `{id: count}`.
   Increment on each cycle where the task appears in `gate_warnings`. When count >= 2,
   log a structured warning to the user at end of cycle. Clear the ID when the task
   leaves the gate-failed set (either dispatched normally or moved by another agent).
3. **No changes to Gate 5.** Different problem class (content, not process).
4. **No planner task movement.** Warnings only.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement gate_warnings in dispatch-planning SKILL.md" --priority needed --status ideation --tags "scope:agents,quality,type:config" --body "## Objective\nAdd 'Gate failure remediation' section to dispatch-planning SKILL.md after the gate checks section.\n\n## AC\n- [ ] New section 'Gate failure remediation' added after 'Gate checks' in Step 2\n- [ ] Planner emits gate_warnings array in JSON output for tasks excluded by Gate 3 or Gate 4\n- [ ] Format: {\"gate_warnings\":[{\"id\":N,\"gate\":\"Gate 3\",\"reason\":\"atomicity: and in title\"}]}\n- [ ] gate_warnings is always emitted (empty array if no failures), planner stays stateless\n- [ ] Step 3 JSON output spec updated with gate_warnings field\n- [ ] Gate 5 excluded from gate_warnings\n- [ ] Alternative (auto-move back) documented as rejected with reasoning\n\n## Context\nSee docs/research/gate-blocked-task-remediation.md S4."
```

```
kanban\kanban-md.exe create "Add gate_warned tracking to orchestration SKILL.md" --priority needed --status ideation --tags "scope:agents,quality,type:config" --body "## Objective\nDocument gate_warned cycle tracking in the orchestration skill so the orchestrator surfaces repeated gate failures to the user.\n\n## AC\n- [ ] New tracking state: gate_warned dict {task_id: count} alongside stale_retried\n- [ ] Orchestrator increments count for each task in gate_warnings each cycle\n- [ ] When count >= 2, orchestrator logs structured warning at end of cycle\n- [ ] gate_warned IDs cleared when task no longer appears in gate_warnings\n- [ ] Step 1 updated to pass gate_warned context to planner (optional, for future use)\n- [ ] Step 3 (Loop) output format updated to include gate warnings when count >= 2\n\n## Context\nSee docs/research/gate-blocked-task-remediation.md S4. Mirrors stale_retried pattern from orchestration SKILL.md."
```
