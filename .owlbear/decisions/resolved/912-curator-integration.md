---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "D: Manual dispatch only — with coverage-gap mining workflow"
notes: "Approach C confirmed. Invocation: manual prompt (user-invocable, like agent-audit). Not task-scoped — operates on the test suite as a whole. Scans for archived task-tests, measures module coverage without them, mines gaps, deletes rest."
# >> Agent metadata
task_id: 912
agent: orchestrator
created: 2026-04-17
urgency: blocking
decision_type: approach-selection
impact_tier: 2
---

# Decision: How should the test-curator be invoked post-archive?

## Context

The test-curator agent processes task-scoped test files post-archive — promoting contract-level assertions to durable module-level files and removing transient scaffolding. It must **never gate** the next task dispatch. The agent exists but has no dispatch trigger in `w-orchestration`.

The question: **what mechanism invokes the test-curator after a task is archived?**

## Options

### A: Archive-triggered dispatch — (rec:) recommended

The orchestrator dispatches the test-curator immediately when `end_work` archives a task. Fire-and-forget — non-blocking.

- Effort: ~0.5 day — add one dispatch call to the orchestrator's archive path in `w-orchestration`
- Trade-off: simplest integration; immediate curation with minimal infrastructure
- Risk: if the next task reaches test-writer before test-curator finishes, both touch `tests/` — but different files (`test_{module}.py` vs `test_{module}_{task_id}.py`), so no conflict
- Confidence: .85

### B: Parallel dispatch with next wave

The orchestrator dispatches the test-curator alongside non-test-touching agents (researcher/architect) in the first wave after archiving a task.

- Effort: ~1 day — wave assembly logic needs a post-archive slot
- Trade-off: uses existing wave machinery; curation runs in parallel with next task's early phases
- Risk: same as A — different file targets, no conflict. Slightly more complex assembly logic
- Confidence: .70

### C: Periodic sweep (every N archives) — (bp:) best practice

A dedicated curator cycle runs after N archives accumulate (e.g., every 5 tasks). The orchestrator checks the archive count and dispatches the test-curator in its own orchestration pass, similar to the memory-curator's periodic dispatch.

- Effort: ~1 day — counter + threshold check in `w-orchestration`
- Trade-off: batches curation work, reducing dispatch overhead; follows memory-curator's established pattern
- Risk: task-scoped test files linger up to N tasks before cleanup; module-level files lag behind
- Confidence: .65

### D: Defer / do nothing

The test-curator agent definition exists but is never automatically invoked. Manual dispatch only via `/test-curator`.

- Effort: 0
- Trade-off: no automatic test lifecycle management; task-scoped files accumulate indefinitely
- Risk: test debt grows silently; the entire two-tier model exists on paper but doesn't execute
- Confidence: .20

## Recommendation

.85 — **A: Archive-triggered dispatch.** Lowest complexity, immediate feedback. The memory-curator uses periodic dispatch because memory curation is batch-oriented. Test curation is task-specific — one archived task produces exactly one set of files to process. Archive-triggered matches the work unit naturally.

## Impact of Deferral

Without a dispatch trigger, the test-curator is dead code. Task-scoped test files accumulate in `tests/`, the two-tier model doesn't function, and the nuclear reset + skill updates from #912 deliver no value. Auto-resolves in 5 days (T2).
