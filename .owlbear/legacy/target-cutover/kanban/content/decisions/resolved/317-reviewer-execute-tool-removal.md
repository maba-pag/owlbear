---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Remove all execute/* tools + read/terminalLastCommand"
notes: ""
# >> Agent metadata (do not edit)
task_id: 317
agent: architect
created: 2026-04-02
urgency: blocking
decision_type: approach-selection
impact_tier: 3
---

# Decision: Reviewer agent execute/* tool removal approach

## Context

Task #317 evaluated whether the reviewer agent can drop `execute/*` tools entirely now that Quality-Runner handles pytest/ruff/coverage and MCP kanban tools provide full parity with terminal `kanban-md.exe` commands.

The researcher completed the analysis at `docs/research/reviewer-execute-tool-removal.md` (.80 confidence). The research found 3 options with meaningful trade-offs around risk tolerance and fallback capability. This is a **security/process change** (T3) — it changes the reviewer's enforcement model from instructional ("you must not run commands") to structural (tools physically removed).

Follow-up implementation tasks already exist: #457 (implementation, depends on #264) and #458 (test, depends on #457). Both are at `ideation` awaiting this decision.

## Options

### A: Remove all execute/* tools + read/terminalLastCommand ← (rec:) recommended

- Removes: 7 execute/* tools + read/terminalLastCommand (8 total)
- Retains: vscode/memory, read/problems, read/readFile, read/viewImage, agent, search, owlbear-kanban/*
- Effort: ~1 day, 2 tasks (#457, #458)
- Trade-off: structural read-only enforcement, but no fallback if Quality-Runner fails
- Risk: medium — if QR is unavailable, reviewer must BLOCK (cannot run tests directly). Mitigated by QR's internal 2-retry loop and pipeline auto-redispatch.
- Confidence: .80

### B: Remove all except execute/runInTerminal — (bp:) best practice for risk-averse

- Removes: 6 execute/* tools + read/terminalLastCommand (7 total)
- Retains everything in A plus execute/runInTerminal as emergency fallback
- Effort: ~1 day, 2 tasks (modify #457 AC)
- Trade-off: keeps manual fallback for pytest/ruff if QR fails, but enforcement is partial (reviewer CAN still run arbitrary commands)
- Risk: low — graceful degradation available
- Confidence: .75

### C: Defer / do nothing

- Effort: 0
- Trade-off: reviewer keeps all 15 tool entries; read-only boundary remains instructional only; `execute/runTests` (explicitly forbidden by skill, known to deadlock) stays listed as a latent risk
- Risk: none immediate, but `execute/runTests` is a known hazard

## Recommendation

.80 confidence — **Option A**. The reviewer's "strictly read-only" persona is a core design principle. Structural enforcement via tool removal is stronger than instructional enforcement. The fallback concern (QR unavailable) is managed by pipeline mechanics: the reviewer reports BLOCKED, the task re-enters the queue, and the planner redispatches when QR is operational. Keeping `execute/runTests` (which deadlocks) in the tool list is an active hazard that Option A eliminates.

## Impact of Deferral

Task #317 is blocked. Follow-up tasks #457 and #458 remain at `ideation`. Neither can proceed until this decision is resolved. No auto-resolve — this is a T3 security/process change. #264 (Quality-Runner wiring) is a prerequisite for #457 regardless, so there is no immediate timeline pressure.
