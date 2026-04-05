# Build Dispatch Planner — Research Findings

> **Owning task:** #20 — Build dispatch planner
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #20 asks for a Python dispatch planner module at `packages/orchestrator/src/owlbear/planner/` that reads the kanban board, selects the next task and agent, formats a prompt, and orchestrates dispatch via ACP. This research validates feasibility, identifies architecture concerns, and recommends implementation approach.

Key questions: (1) Does the Python planner module overlap with the existing LLM-based planner agent? (2) What's the right separation between planner and orchestrator concerns? (3) What's the correct board-reading strategy? (4) Are dependencies satisfied?

## 2. Sources Studied

| # | Source | Relevance | What |
|---|--------|:---------:|------|
| S1 | `dispatch-planning` SKILL.md | .95 | Board scan recipes, 6-gate algorithm, agent dispatch mapping |
| S2 | `orchestration` SKILL.md | .95 | Dispatch loop, wave assembly, rate-limit fallback |
| S3 | `planner.agent.md` | .90 | LLM-based planner producing JSON dispatch plans |
| S4 | `orchestrator.agent.md` | .90 | VS Code agent that dispatches subagents |
| S5 | ACP Python SDK quickstart | .85 | `spawn_agent_process`, `conn.prompt()` patterns |
| S6 | `acp_client.py` (existing) | .95 | AcpClient wrapper with timeouts and error classification |
| S7 | `process_supervisor.py` (existing) | .95 | Subprocess lifecycle management |
| S8 | `mcp-kanban/server.py` (existing) | .90 | Board operations via kanban-md subprocess |
| S9 | `orchestration-agent-frameworks.md` | .80 | Poll-dispatch-reconcile from Symphony; wave patterns |
| S10 | `acp-client-library-decomposition.md` | .85 | #19 subtask coverage — AcpClient + ProcessSupervisor done |

## 3. Analysis

### 3.1 Two Orchestration Modes

OwlBear has two distinct orchestration surfaces:

| Aspect | VS Code Agent Mode (current) | ACP Headless Mode (planned) |
|--------|------------------------------|----------------------------|
| Orchestrator | `orchestrator.agent.md` (LLM) | Python module (programmatic) |
| Planner | `planner.agent.md` (LLM) | Python planner module |
| Dispatch | `runSubagent` (VS Code) | `AcpClient.prompt()` (ACP) |
| Board reading | kanban-md.exe via terminal | kanban-md.exe via subprocess |
| Gate checks | LLM reasoning + PS markers | Python functions |
| Wave assembly | LLM reasoning | Python algorithm |

The Python planner module enables headless orchestration without VS Code. Both modes use the same kanban board and the same algorithm (dispatch-planning skill). [S1-S4]

### 3.2 AC Concern Separation

The original AC mixes planner and orchestrator responsibilities:

| Function | Belongs to | Rationale |
|----------|------------|-----------|
| `read_board()` | Planner | Board state is input to planning |
| `select_task()` | Planner | Priority/gate logic |
| `select_agent()` | Planner | Status-to-agent mapping |
| `format_prompt()` | Orchestrator | Prompt is dispatch-time concern |
| Dispatch loop | Orchestrator | Loop + wave assembly + error handling |

**Recommendation (.85):** Split into two modules: (a) planner module producing a typed dispatch plan, (b) orchestrator module consuming it and managing ACP sessions. This mirrors the LLM mode separation (planner.agent.md produces JSON, orchestrator.agent.md dispatches). [S1, S2, S9]

### 3.3 Board Reading Strategy

| Option | Approach | KISS | Deps |
|--------|----------|------|------|
| A. kanban-md subprocess | Call `kanban-md.exe list --json --unblocked --not-blocked --unclaimed` | High | kanban-md.exe binary |
| B. MCP client to mcp-kanban | Connect to mcp-kanban server, call tools | Medium | mcp-kanban server running |
| C. Parse task files directly | Read `kanban/tasks/*.md` YAML frontmatter | Low | Couples to file format |

**Recommendation (.90):** Option A — kanban-md subprocess. Matches dispatch-planning skill Recipe 1. The `--unblocked --not-blocked --unclaimed` triple handles gates 2, 6 server-side. No MCP server dependency at runtime. [S1, S8]

### 3.4 Dependency Status

| Dep | Task | Status | Blocker? |
|-----|------|--------|----------|
| #14 | Build mcp-kanban server | archived | No |
| #19 | Build ACP client library | ideation | **Partially.** AcpClient + ProcessSupervisor exist in code but task hasn't completed the pipeline. The planner module itself only needs kanban-md.exe, not ACP. The orchestrator loop module needs #19's AcpClient. |

**Finding:** The planner module has no unsatisfied code dependencies — it reads from kanban-md.exe and produces a data structure. The orchestrator loop (a separate concern) depends on AcpClient from #19. [S6, S7, S10]

### 3.5 Implementation Approach

Port dispatch-planning skill algorithm to typed Python:

1. **Data models** (Pydantic): `Task`, `DispatchEntry`, `DispatchPlan`
2. **Board reader**: async subprocess call to kanban-md.exe, parse JSON output
3. **Gate checker**: 6 gates as predicate functions (gates 2+6 handled by CLI flags, gates 1+3+4+5 in Python)
4. **Task selector**: dual-key sort (priority rank, pipeline proximity), 20-task cap
5. **Agent mapper**: `STATUS_AGENT_MAP` dict matching dispatch-planning skill table

Total estimated scope: ~150 LOC for planner module, ~50 LOC for models.

### 3.6 Testing Strategy

- Mock `asyncio.create_subprocess_exec` to return canned kanban-md JSON
- Test gate logic independently (AC:MISSING, TW:MISSING, atomicity)
- Test priority sorting with mixed statuses and priorities
- Test 20-task cap and empty board edge case
- No real kanban-md.exe needed for unit tests

## 4. Recommendation (.85 confidence)

Split task #20 into focused subtasks:

1. **Planner data models + board reader** — Pydantic models for Task/DispatchEntry/DispatchPlan, async board reader wrapping kanban-md.exe subprocess
2. **Gate checker + task selector** — 6-gate predicate functions, priority sorting, agent mapping, 20-task dispatch cap
3. **Orchestrator dispatch loop** — consume dispatch plan, manage ACP sessions via AcpClient, wave assembly, error handling (depends on planner + #19 AcpClient)

This decomposition lets the planner module proceed independently of #19 completion.

Risks:
- kanban-md.exe output format coupling — mitigated by testing against actual `--json` output schema
- #19 AcpClient not yet pipeline-complete — blocks only the orchestrator loop, not the planner itself

## 5. Follow-up Tasks

Tasks created at `ideation` below. The architect will gate them before `todo`.
