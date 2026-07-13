---
id: 695
title: Full ToolError unification across all MCP servers (gated on evidence)
status: archived
priority: medium
created: 2026-04-08T21:24:23.792112+02:00
updated: 2026-04-10T04:28:16.5225155+02:00
started: 2026-04-10T04:28:16.5225155+02:00
completed: 2026-04-10T04:28:16.5225155+02:00
tags:
    - scope:mcp
    - ' type:refactor'
    - ' source:research'
blocked: true
block_reason: Gate condition (AC1) infeasible — .owlbear/error-journal.jsonl does not exist on disk. Zero empirical evidence of agent failures after 3 research passes and 4 architecture reviews. Unblock only when error journal accumulates runtime data showing agents mishandling isError:false responses.
class: standard
---

## Context

Research #680 identified that 9 MCP tools return `"error: ..."` strings (`isError: false`) instead of raising `ToolError` (`isError: true`). The MCP spec (2025-11-25 §6) recommends `isError: true` for all tool execution errors including input validation and business logic errors.

The Phase 1 task fixes the 3 bugs. This Phase 2 task would convert ALL remaining error-string tools to ToolError for full consistency. However, this has significant blast radius:

- ~10 tools need changes across 3 servers (knowledge, memory, project)
- ~40 test assertions need restructuring
- 1 runtime consumer (approve.py) needs updating
- Core library functions (scope_transfer.py) keep string errors; MCP wrappers would translate
- Return type annotations change on ~7 tools (remove `| str` unions)

**GATE:** Only proceed if evidence shows agents struggle with the dual pattern in practice. Track agent error-handling failures and assess whether unification provides measurable benefit.

See: `.owlbear/research/mcp-tool-error-signaling-680.md`

## Acceptance Criteria

- [ ] AC1: Evidence collected that dual pattern causes agent failures (gate condition)
- [ ] AC2: All str-return tools converted from `"error: ..."` to `raise ToolError(...)`
- [ ] AC3: Return type annotations cleaned up (remove `| str` unions where applicable)
- [ ] AC4: approve.py updated to remove dead `startswith("error:")` checks
- [ ] AC5: All tests updated (~40 assertions)
- [ ] AC6: SKILL.md docs updated (h-mcp-knowledge, h-mcp-memory, h-mcp-project)
- [ ] AC7: No agent breakage verified

[[2026-04-08]] Wed 22:30
## Research
- Research doc: .owlbear/research/toolerror-unification-gate-695.md
- Sources: 9 studied, 5 high-relevance (1.0)
- Recommendation: Gate NOT met — do not proceed with full unification (confidence: .90)
- Follow-up tasks created: none (gate negative, no actionable follow-ups)
- Decision requests: none

### Gate Assessment Summary
Searched all available evidence sources: error journal (doesn't exist on disk), memory store (zero entries), kanban board (zero failure reports across 695+ tasks), agent source files (no dual-pattern handling code), runtime consumers (approve.py handles both patterns correctly). The dual pattern has been validated by 3 prior research tasks (#496, #540, #680), follows a sound return-type-driven design rationale, and is MCP-spec-valid (SHOULD, not MUST). Zero empirical evidence of agent failures exists, and the system lacks telemetry infrastructure to detect such failures. Reassess only after error journal reaches production and accumulates runtime data.

[[2026-04-08]] Wed 22:44
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Task is coherent — unify one error pattern |
| Interface clarity | N/A | Gate condition not met; AC2-AC7 never evaluated |
| Dependency correctness | PASS | No deps listed, none needed for a gated task |
| Module layering | N/A | No implementation to evaluate |
| TDD compliance | N/A | Gate not met |
| KISS/YAGNI | **FAIL** | YAGNI — zero empirical evidence of need. 3 prior research tasks validated the dual pattern. |
| Premise challenge | **FAIL** | The premise (agents struggle with dual pattern) is unsubstantiated. The system lacks telemetry to even detect such failures. |
| Pattern consistency | N/A | No implementation to evaluate |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp only |

### Challenge Results
- Challenger: SKIP (REJECT verdict — protocol exemption)

### Verdict: REJECT
### Reason
AC1 (gate condition) is explicitly not met per the task's own research (`.owlbear/research/toolerror-unification-gate-695.md`). The research found:
- Zero agent failure reports across 695+ kanban tasks
- Zero memory store entries referencing error pattern confusion
- Zero agent source files checking for `"error:"` prefix
- Error journal infrastructure not deployed (no telemetry possible)
- 3 prior research tasks (#496, #540, #680) validated the dual pattern as intentional, spec-valid (SHOULD not MUST), and sound (Return-Type-Driven design)
- Runtime consumer (approve.py) correctly handles both patterns

The task cannot proceed without evidence that doesn't exist and can't be gathered without error journal deployment. Reassess only after error journal (#522) reaches production and accumulates runtime data.

### Action Taken
Rejected to `research`. No follow-up tasks — the gate is infrastructure-dependent (error journal deployment), which is tracked separately.

[[2026-04-08]] Wed 23:15
[[2026-04-08]] Wed 23:15
## Research (validation pass)
- Research doc: .owlbear/research/toolerror-unification-gate-695.md (validated, current)
- Validation findings: all prior conclusions hold
- Gate condition: still NOT met (confidence: .92)
- Follow-up tasks created: none
- Decision requests: none

### Validation Summary
Re-checked all evidence sources after architecture review REJECT:
1. `.owlbear/error-journal.jsonl` still does not exist on disk — zero runtime telemetry
2. Task #522 (ErrorLogger adapter wiring) is archived/complete, but the orchestrator has not run to generate journal data
3. Kanban board: zero tasks mentioning dual/error pattern failures (re-searched full board)
4. Memory store: zero entries about pattern confusion
5. Agent source files: zero `startswith("error:")` checks

Prior research doc remains fully accurate. Gate cannot be assessed until the orchestrator runs in production and accumulates error journal data. Recommend archiving this task with a "reassess when telemetry exists" note rather than keeping it in a research↔reject loop.

[[2026-04-08]] Wed 23:44
## Architecture Review (2nd pass)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coherent scope |
| Interface clarity | N/A | Gate not met |
| Dependency correctness | PASS | No deps |
| Module layering | N/A | No implementation |
| TDD compliance | N/A | Gate not met |
| KISS/YAGNI | **FAIL** | YAGNI — zero evidence after 2 research passes, 3 prior validations (#496, #540, #680) |
| Premise challenge | **FAIL** | Gate condition (AC1) infeasible without telemetry infrastructure that does not exist |
| Pattern consistency | N/A | No implementation |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp only |

### Challenge Results
- Challenger: SKIP (REJECT verdict — protocol exemption)

### Verdict: REJECT
### Reason
Same conclusion as 1st review — AC1 gate condition is not met and **cannot be met** with current infrastructure. Two research passes (confidence .90, .92) confirm zero empirical evidence across all available sources. Rejecting a second time.

### Loop-Breaking Directive
This task has completed a full reject→research→backlog cycle with no change in gate status. The researcher's own recommendation is to archive. **On receiving this task in research status, the researcher SHOULD archive it** with a "reassess when error journal telemetry is deployed and accumulating data" note rather than re-researching. Re-research will produce identical results and waste a pipeline cycle.

### Action Taken
Rejected to `research` with archival recommendation. No follow-ups — gate is infrastructure-dependent (error journal deployment), tracked separately.

[[2026-04-09]] Thu 01:08
[[2026-04-09]] Wed 01:08
## Research (3rd pass — archival per Loop-Breaking Directive)
- Research doc: .owlbear/research/toolerror-unification-gate-695.md (validated, current)
- Gate condition: still NOT met (confidence: .92)
- Follow-up tasks created: none
- Decision requests: none

### Validation Summary
3rd-pass spot-check confirms zero change from prior two passes:
- `.owlbear/error-journal.jsonl` still does not exist (Test-Path: False)
- No new kanban tasks referencing dual-pattern failures
- Gate infrastructure (error journal telemetry) remains undeployed

### Archival Rationale
This task has completed 2 full research→reject→research cycles with identical results. The architecture review's Loop-Breaking Directive (2026-04-08 23:44) explicitly recommends archival. Re-research produces identical output each cycle. Archiving now.

**Reassess trigger:** Error journal (#522) deployed to production AND accumulating runtime data showing agents mishandling `isError: false` tool responses.

[[2026-04-09]] Thu 01:38
## Architecture Review (3rd pass — loop-breaking BLOCK)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coherent scope |
| Interface clarity | N/A | Gate not met |
| Dependency correctness | PASS | No deps |
| Module layering | N/A | No implementation |
| TDD compliance | N/A | Gate not met |
| KISS/YAGNI | **FAIL** | YAGNI — zero evidence after 3 research passes, 3 prior validations (#496, #540, #680) |
| Premise challenge | **FAIL** | Gate condition (AC1) is infeasible without telemetry infrastructure that does not exist |
| Pattern consistency | N/A | No implementation |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp only |

### Challenge Results
- Challenger: SKIP (BLOCK verdict — protocol exemption)

### Loop History
- Research pass 1: gate NOT met (confidence .90)
- Architecture review 1: REJECT
- Research pass 2 (validation): gate NOT met (confidence .92)
- Architecture review 2: REJECT + Loop-Breaking Directive
- Research pass 3: followed directive, recommended archival, but pipeline advanced to backlog
- Architecture review 3 (this pass): BLOCK to break the cycle

### Verdict: BLOCK
### Reason
This task has completed 2 full reject→research→backlog cycles with identical results. All 3 research passes (confidence .90–.92) confirm zero empirical evidence across every available source — error journal doesn't exist on disk, zero memory store entries, zero kanban failure reports across 695+ tasks, zero agent source files with dual-pattern handling. The gate condition (AC1) is **infrastructure-blocked**: `.owlbear/error-journal.jsonl` does not exist, error journal telemetry (#522) is not deployed.

Blocking rather than rejecting a 3rd time because:
1. Re-research will produce identical results (proven by 3 passes)
2. The researcher already attempted archival per the Loop-Breaking Directive but the pipeline advanced to backlog
3. The task is genuinely blocked on external infrastructure, not on unclear requirements

### Unblock Condition
Error journal (#522) deployed to production AND accumulating runtime data showing agents mishandling `isError: false` tool responses. Only then can AC1 be assessed.

### Action Taken
Blocked with explicit unblock condition. Breaks the reject→research→backlog loop that has wasted 5 pipeline cycles.

[[2026-04-10]] Fri 02:27
## Architecture Review (4th pass — re-block)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Coherent scope |
| Interface clarity | N/A | Gate not met |
| Dependency correctness | PASS | No deps |
| Module layering | N/A | No implementation |
| TDD compliance | N/A | Gate not met |
| KISS/YAGNI | **FAIL** | YAGNI — zero evidence after 3 research passes, 3 prior validations (#496, #540, #680) |
| Premise challenge | **FAIL** | Gate condition (AC1) infeasible — telemetry infrastructure exists (#522 archived) but has not generated data |
| Pattern consistency | N/A | No implementation |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:mcp only |

### Challenge Results
- Challenger: SKIP (BLOCK verdict — protocol exemption)

### Infrastructure Check
- #522 (ErrorLogger adapter wiring): archived/complete
- `.owlbear/error-journal.jsonl`: does NOT exist on disk (Test-Path: False)
- Orchestrator has not run in production to generate journal data
- All prior evidence sources unchanged: zero memory entries, zero kanban failure reports, zero agent source files with dual-pattern handling

### Loop History
| Pass | Agent | Verdict | Confidence |
|------|-------|---------|------------|
| Research 1 | researcher | gate NOT met | .90 |
| Arch Review 1 | architect | REJECT | — |
| Research 2 | researcher | gate NOT met | .92 |
| Arch Review 2 | architect | REJECT + Loop-Breaking Directive | — |
| Research 3 | researcher | archival recommended | .92 |
| Arch Review 3 | architect | BLOCK | — |
| Arch Review 4 (this) | architect | RE-BLOCK | — |

7 pipeline cycles, identical conclusion each time. This task was unblocked and returned to backlog after the 3rd-pass BLOCK without any change in gate status.

### Verdict: BLOCK
### Reason
Re-blocking. Nothing has changed since the 3rd-pass BLOCK: error journal still doesn't exist on disk, zero empirical evidence across all sources. The task was unblocked without meeting its unblock condition.

### Unblock Condition (unchanged)
ALL of: (1) `.owlbear/error-journal.jsonl` exists on disk, (2) contains runtime data, (3) data shows agents mishandling `isError: false` tool responses. Only then can AC1 be assessed.

### Action Taken
Blocked with explicit unblock condition. Do NOT unblock or return to backlog until all 3 unblock criteria are met.
