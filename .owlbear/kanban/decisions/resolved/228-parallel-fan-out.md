---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Start with reviewer parallel fan-out, then auditor"
notes: ""
# >> Agent metadata (do not edit)
task_id: 228
agent: researcher
created: 2026-03-30
urgency: blocking
decision_type: approach-selection
---

# Decision: Which agents should get parallel fan-out first?

## Context

Category B proposes splitting agent workloads into parallel subagent calls. VS Code docs explicitly support parallel subagent execution. The orchestrator already proves parallel `runSubagent` works in waves. See `docs/research/subagent-nesting-architecture.md` §3d for benefit ranking. Task #228 is blocked pending this decision.

## Options

### A: Reviewer first, then Auditor — (rec:) recommended

- Effort: ~2 tasks (reviewer split, then auditor split)
- Trade-off: Reviewer has the clearest parallel division (Quality-Runner + Code-Reader are fully independent). Validates pattern before applying to auditor (3-way split is more complex).
- Risk: Low — reviewer is read-only, failures don't corrupt code

### B: Auditor first

- Effort: ~2 tasks
- Trade-off: Auditor runs full suite (most expensive operation), so parallel gain is larger in absolute terms
- Risk: Higher — auditor's 3-way split (Quality-Runner + AC-Verifier + Code-Spotter) is more complex to coordinate

### C: Both simultaneously — (bp:) best practice

- Effort: ~3 tasks
- Trade-off: Fastest overall delivery; both agents benefit sooner
- Risk: More implementation surface; harder to debug if parallel pattern has issues

### D: Defer / do nothing

- Effort: 0
- Trade-off: Reviewer continues spending 40-60% of context on test output
- Risk: No immediate impact; context pollution persists

## Recommendation

.85 confidence — Option A. Reviewer is the safest first target (read-only, clean 2-way split). Validates the parallel pattern before the more complex auditor 3-way split. Depends on Quality-Runner being available (Category E-sub).

## Impact of Deferral

Parallel fan-out implementation tasks are blocked. Reviewer and auditor continue with sequential workflows. If no decision within 5 days, auto-resolve with Option A.
