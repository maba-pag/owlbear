# MCP Tool References Alongside CLI in Agents and Skills

> **Owning task:** #483 — Phase A: Add MCP tool references alongside CLI in all agents and skills
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Task #483 adds MCP tool alternatives alongside existing CLI references in ~22
agent, skill, and instruction files. Both paths must work simultaneously with
CLI preserved as fallback. This research validates feasibility, maps CLI-to-MCP
equivalences, identifies scope corrections, and recommends a decomposition approach.

**Dependency status:** 5/6 deps archived. #477 (move/pick JSON + board_context
removal) is blocked — test mock data conflict between #489 and #495. Fix is
mechanical (update mock data) but requires test-writer re-dispatch. #483 cannot
begin implementation until #477 completes.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | mcp-kanban SKILL.md | Codebase | .95 — documents all 8 MCP tools with parameters |
| 2 | mcp-kanban server.py | Codebase | .95 — actual tool implementations |
| 3 | kanban-md SKILL.md | Codebase | .90 — CLI pitfalls and full command reference |
| 4 | 10 agent .agent.md files | Codebase | .90 — current CLI patterns and tools sections |
| 5 | 12 skill SKILL.md files | Codebase | .85 — current cheatsheet sections |
| 6 | agent-common.instructions.md | Codebase | .85 — Channel B protocol, CLI references |
| 7 | expand-mcp-kanban-tools.md | Research | .80 — earlier MCP tool surface analysis |

## 3. Analysis

### 3a. CLI-to-MCP Mapping

| CLI Pattern | MCP Equivalent | Notes |
|------------|----------------|-------|
| `show {id}` | `show_task(task_id)` | 1:1 |
| `edit {id} --claim X` | `edit_task(task_id, claim="X")` | 1:1 |
| `edit {id} -a "text" -t` | `edit_task(task_id, append_body="text", timestamp=true)` | `-a`=`append_body` |
| `edit {id} --status S --release` | `edit_task(task_id, status="S", release=true)` | 1:1 |
| `edit {id} --block "reason"` | `edit_task(task_id, block="reason")` | 1:1 |
| `edit {id} --unblock` | `edit_task(task_id, unblock=true)` | 1:1 |
| `create "T" --priority P --status S` | `create_task(title="T", priority="P", status="S")` | 1:1 |
| `move {id} S` | `move_task(task_id, status="S")` | 1:1 |
| `list --json [filters]` | `list_tasks([filters])` | 1:1 |
| `pick --status S --claim X` | `pick_task(status="S", claim="X")` | 1:1 |
| claim + show (2 calls) | `start_work(task_id, claim?)` | Compound: 1 call |
| note + advance + release (3 calls) | `end_work(task_id, note, outcome)` | Compound: 1 call |
| `archive {id}` | `end_work(task_id, note, outcome="success")` | Only when at last status |
| `delete {id} --yes` | No MCP equivalent | Intentional: destructive |
| `board --compact` | No MCP equivalent | Use `list_tasks` |
| `agent-name` | Embedded in `start_work` | Auto-generated |
| `handoff` | `end_work(outcome="block", block_reason=...)` | Partial — complex handoffs need multiple edit_task calls |

### 3b. Compound Tool Workflow Pattern

Current agent CLI workflow (every pipeline agent):
1. `show {id}` (read task)
2. `edit {id} --claim <agent>` (claim)
3. [work]
4. `edit {id} -a "## Section\n..." -t --claim <agent>` (Channel B)
5. `edit {id} --status {next} --release` (advance + release)

Simplified MCP workflow:
1. `start_work(task_id, claim="<agent>")` (claim + read, 1 call)
2. [work]
3. `edit_task(task_id, append_body="## Section\n...", timestamp=true, claim="<agent>")` (Channel B)
4. `end_work(task_id, note="...", outcome="success")` (note + advance + release, 1 call)

Reduction: 4-5 CLI calls reduced to 3 MCP calls per task lifecycle.

### 3c. Pitfall Carryover

The kanban-md `--claim` + `--release` same-call pitfall (kanban-md SKILL.md)
applies to `edit_task` too since MCP wraps CLI. Agents must issue
`edit_task(claim=...) ; edit_task(release=true)` as separate calls.
However, `start_work` and `end_work` handle this internally — another
reason to prefer compound tools.

### 3d. Error Handling Differences

MCP and CLI paths differ in error surfaces:
- `show_task`, `move_task`, `pick_task` raise `ToolError` (client sees `isError: true`)
- `list_tasks`, `create_task`, `edit_task`, `start_work`, `end_work` return `error: {msg}` strings
- CLI always returns stdout/stderr + exit code

Both paths produce identical data outcomes, but MCP avoids PowerShell
escaping pitfalls (`->` arrows, `--token` patterns, pipe characters in tables)
that are documented in agent-common.instructions.md.

### 3e. Scope Corrections

| AC Claim | Actual | Delta |
|----------|--------|-------|
| "10 skill cheatsheets" | 9 have `## kanban-md Commands`, 2-3 more have inline CLI refs | +2-3 files |
| "agent-common Channel B section" | ~16 kanban-md refs across 6+ sections | Broader scope |
| Scope mentions research-docs.instructions.md | Not in AC items | Missing from AC |
| "Each agent's tools: section" | All 10 already have `'owlbear-kanban/*'` | Already done |

### 3f. AC Item 5 — Already Satisfied

All 10 pipeline agents already include `'owlbear-kanban/*'` in their YAML
`tools:` section (verified via grep). This AC item requires no implementation
work. The other AC items cover the body-text guidance that teaches agents
*when and how* to use MCP tools.

## 4. Recommendation (.80 confidence)

Proceed as planned. The task is feasible and the implementation approach is
clear. Key recommendations:

1. **Block on #477.** Do not begin implementation until #477 is unblocked and
   archived. The test mock fix is mechanical but must complete first.
2. **Recommend decomposition.** ~22-25 files with similar but file-category-
   specific changes. Suggest 4-5 subtasks: (a) mcp-kanban SKILL.md expansion,
   (b) agent-common + research-docs instructions, (c) agent files, (d) skill
   cheatsheets, (e) dispatch-planning/orchestration skills.
3. **Compound tools as primary pattern.** Document `start_work` / `end_work`
   as the recommended workflow, with individual MCP tools for mid-workflow ops.
4. **AC corrections.** Architect should: add research-docs to AC, note AC item 5
   is pre-satisfied, expand agent-common scope beyond Channel B section.

Challenge: reconsider — confidence in original: .65.
Challenger raised valid concerns about #477 block status (accepted),
scope miscounting (accepted), AC item 5 interpretation (rebutted — YAML
glob is what AC says; body-text guidance is other AC items). T1
classification maintained: adding documentation for existing capabilities
is not a new capability.

## 5. Follow-up Tasks

No new follow-up tasks created. Task #483 already has well-scoped AC.
Recommend marking `Needs decomposition: ~25 files across agents, skills,
and instructions — recommend 4-5 subtasks by file category` in the task
body so the kanban-planner handles the split after architect review.

The architect should refine AC during backlog review to address the
scope corrections identified in section 3e.
