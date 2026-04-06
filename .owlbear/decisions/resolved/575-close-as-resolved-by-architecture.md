---
response: approved
decision: "A: Close task #575 as resolved-by-architecture"
notes: ""
task_id: 575
agent: researcher
created: 2026-04-06
urgency: blocking
decision_type: scope-decision
impact_tier: 2
---

# Decision: Close Task #575 as Resolved-by-Architecture?

## Context

Task #575 ("Update pipeline agent files with MCP tool references alongside CLI") has completed three research passes (confidence .78→.85→.85) plus a formal architecture review, all reaching the same conclusion: **the task premise is obsolete and all acceptance criteria are either invalid, already satisfied, or violate DRY principle.**

The task is stuck in an ideation→research→architect-reject loop. The researcher is requesting explicit closure decision because the architectural findings are complete and decisive.

## Evidence

### AC Assessment (Architecture Review)

| AC Line | Status | Evidence |
|---------|--------|----------|
| "All 11 pipeline agent files updated" | INVALID | Only 9 pipeline agents exist (architect, auditor, builder, curator, doc-writer, planner, researcher, reviewer, test-writer). Files kanban-planner.agent.md and writer.agent.md do not exist. scribe.agent.md has no kanban protocol section. |
| "MCP tool alternatives alongside CLI examples" | OBSOLETE | v2 agents have zero CLI commands in body. Premise was based on v1 agent structure. |
| "Compound tools documented as preferred pattern" | ALREADY DONE | h-mcp-kanban SKILL.md § Agent Lifecycle Pattern documents this as single source of truth. |
| "No existing CLI refs removed" | N/A | No CLI references exist in v2 agent bodies to preserve. |
| "Must pass #572 agent file checks" | INVALID | #572 originally tested agent body assertions; these were removed during v2 architectural reorganization. |

### DRY Violation Analysis

All 9 existing pipeline agents already implement the correct pattern:

```
## Kanban Protocol
[Pointer to h-mcp-kanban skill § Agent Lifecycle Pattern]
```

Adding redundant lifecycle documentation to 9 agent files would:
- Break DRY principle (lifecycle spec in 10 places instead of 1)
- Introduce maintenance debt (changes to pattern require 10 edits)
- Violate v2 architecture (factored through skill pointers, not inline)

### Research Completeness

- **Research pass 1** (2026-04-05): Confidence .78, recommended close-as-resolved-by-architecture
- **Challenge cycle** (2026-04-05): Challenger raised 5 concerns; researcher accepted all; conviction stands
- **Research pass 2** (2026-04-06): Confidence .85 (up from .78), validation pass confirms all findings hold
- **Architecture review** (2026-04-06): **REJECT verdict — every AC line is factually incorrect, obsolete, or already satisfied**

## Options

### A: Close as resolved-by-architecture — (rec:) recommended
- **Effort:** 5 minutes (update task body with resolution note, mark done)
- **Trade-off:** None. All legitimate requirements are already satisfied by existing v2 architecture.
- **Risk:** None. Decision is based on three complete research passes + architecture review consensus.

### B: Rewrite AC to identify a legitimate remaining gap
- **Effort:** 8+ hours of research to identify gap (if one exists)
- **Trade-off:** Researcher has already conducted two validation passes; no gap identified. Additional research unlikely to surface new requirements.
- **Risk:** Medium. Extends task indefinitely; researcher confidence already at .85 (threshold for GO/NO-GO).

### C: Leave in ideation indefinitely
- **Effort:** None (do nothing)
- **Trade-off:** Task blocks phase-2 pipeline planning; children tasks (#625, #596) are held at ideation or todo pending parent closure.
- **Risk:** High. Task sits blocked without clear exit criteria. Violates commitment to resolution when evidence is complete.

## Recommendation

**Confidence: 0.85** — **Option A: Close as resolved-by-architecture.**

**Rationale:**

1. **Evidence is decisive.** Three research passes (confidence drift .78→.85) confirm the same conclusion. Challenger review accepted all concerns. Architecture review reached REJECT verdict with detailed line-by-line AC assessment.
2. **Every AC line is factually incorrect or already satisfied.** Not a matter of interpretation — agent files can be counted, h-mcp-kanban SKILL.md exists and documents lifecycle pattern, v1 CLI commands do not exist in v2 agent bodies.
3. **Closing unblocks downstream.** Child tasks (#625 at ideation, #596 at todo) can proceed without waiting for a task that will never pass as written.
4. **DRY principle demands it.** The existing v2 architecture (9 agents with pointer-based factoring, single h-mcp-kanban skill as source of truth) IS the correct solution. Duplicating lifecycle into 9 agent files unwould break that principle.

## Impact of Deferral

- **Task remains blocked:** Phase-2 pipeline planning cannot finalize agent inventory while #575 status is unresolved.
- **Children stall:** #625 (restore #574 MCP callouts) and #596 (planner skill language fix) remain ideation/todo pending closure signal.
- **Researcher time:** Additional investigation cycles are unlikely to surface new gaps given two complete validation passes and architecture review consensus.

**Auto-resolve:** If no user response within 5 days, will auto-resolve to Option A (close as resolved-by-architecture) per impact_tier: 2 timeout rules.
