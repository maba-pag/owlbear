# Reviewer execute/* Tool Removal Evaluation

> **Owning task:** #317 — Evaluate execute/* tool removal from reviewer agent
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

The reviewer agent lists 7 `execute/*` tools despite being a "strictly read-only" agent. Task #264 wires Quality-Runner to handle pytest/ruff/coverage, and the reviewer already has `owlbear-kanban/*` MCP tools. Can the reviewer drop all `execute/*` tools to enforce the read-only boundary structurally, not just instructionally?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | VS Code Subagents Guide | https://code.visualstudio.com/docs/copilot/agents/subagents | .95 — subagent tool independence from parent |
| S2 | VS Code Custom Agents docs | https://code.visualstudio.com/docs/copilot/customization/custom-agents | .90 — assign mode, agents array override, security via least privilege |
| S3 | OwlBear code-review skill | skills/code-review/SKILL.md | .95 — full terminal usage inventory |
| S4 | OwlBear mcp-kanban skill | skills/mcp-kanban/SKILL.md | .95 — MCP coverage of kanban operations |
| S5 | OwlBear quality-runner-wiring.md | docs/research/quality-runner-wiring.md | .90 — tool retention analysis |
| S6 | OwlBear reviewer.agent.md | agents/reviewer.agent.md | .95 — current tool inventory |
| S7 | OwlBear reviewer-parallel-fan-out.md | docs/research/reviewer-parallel-fan-out.md | .85 — coordinator pattern compatibility |

## 3. Analysis

### 3a. Current Reviewer Terminal Usage Inventory

| Category | Steps | Terminal Commands | Replacement |
|----------|-------|-------------------|-------------|
| pytest | 3 | `uv run pytest ...` | Quality-Runner (S5) |
| ruff | 4 | `uv run ruff check ...` | Quality-Runner (S5) |
| coverage | 5 | `uv run pytest --cov ...` | Quality-Runner (S5) |
| kanban show | 1 | `kanban-md.exe show {id}` | MCP `show_task` (S4) |
| kanban claim | 1 | `kanban-md.exe edit --claim` | MCP `edit_task` claim param (S4) |
| kanban append | 8 | `kanban-md.exe edit -a "..." -t` | MCP `edit_task` append_body+timestamp (S4) |
| kanban advance | 9 | `kanban-md.exe edit --status docs --release` | MCP `edit_task` status + separate release call (S4) |
| kanban reject | 9 | `kanban-md.exe edit --status todo --release` | MCP `edit_task` status + separate release call (S4) |
| handoff | edge | `kanban-md.exe handoff ...` | MCP `edit_task` (block+append) + `edit_task` (release) (S4) |

**Result:** Every terminal operation has a non-terminal replacement. No git commands (unlike builder/auditor).

### 3b. Execute/* Tools: Usage vs. Availability

| Tool | In Reviewer | Referenced in Skill? | Verdict |
|------|-------------|---------------------|---------|
| `execute/runInTerminal` | Yes | Steps 3-5, kanban cmds | Replaceable (QR + MCP) |
| `execute/getTerminalOutput` | Yes | No | Unnecessary |
| `execute/awaitTerminal` | Yes | No | Unnecessary |
| `execute/killTerminal` | Yes | No | Unnecessary |
| `execute/createAndRunTask` | Yes | No | Unnecessary |
| `execute/runTests` | Yes | **Explicitly forbidden** ("deadlocks") | Should never have been listed |
| `execute/testFailure` | Yes | No | Quality-Runner handles this |

**Notable:** `execute/runTests` is explicitly forbidden by the code-review skill (S3, Step 3: "never `runTests` — it deadlocks with parallel agents"). Having it in the tool list is a latent risk.

### 3c. Subagent Tool Independence

VS Code docs (S1, S2) confirm: subagent tools are independent of parent tools. The reviewer does not need `execute/*` to invoke Quality-Runner; Quality-Runner has its own `execute/*` tools via assign mode. The `agent` tool in the parent is sufficient for invocation.

### 3d. MCP Kanban Parity Check

| kanban-md CLI Command | MCP Equivalent | Parity | Notes |
|-----------------------|----------------|--------|-------|
| `show {id}` | `show_task(task_id)` | Full | |
| `edit --claim X` | `edit_task(task_id, claim=X)` | Full | |
| `edit -a "..." -t` | `edit_task(task_id, append_body, timestamp)` | Full | |
| `edit --status X` | `edit_task(task_id, status=X)` or `move_task` | Full | |
| `edit --release` | `edit_task(task_id, release=True)` | Full | Must be separate call (S4 pitfall) |
| `edit --block "..."` | `edit_task(task_id, block="...")` | Full | |
| `handoff` | Decompose: block+append+release | Functional | No single-call equivalent |

**Result:** Full parity. The agent-common `handoff` template needs a MCP-equivalent documented in the code-review skill.

### 3e. Orphaned read/ Tool

`read/terminalLastCommand` is under `read/` (not `execute/`) but becomes useless without terminal commands — parent cannot see subagent terminals. Should be removed alongside `execute/*` even though it's technically out of scope.

### 3f. Post-Removal Tool List

| # | Tool | Purpose |
|---|------|---------|
| 1 | `vscode/memory` | Agent memory |
| 2 | `read/problems` | Compile/lint errors |
| 3 | `read/readFile` | File reading |
| 4 | `read/viewImage` | Image viewing |
| 5 | `agent` | Subagent invocation (Quality-Runner) |
| 6 | `search` | Codebase search |
| 7 | `owlbear-kanban/*` | MCP kanban (7 tools) |

7 tool entries (13 endpoints with MCP expansion). Down from 15 entries. All read-only or MCP.

### 3g. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Quality-Runner unavailable (crash/timeout) | High — no fallback to direct pytest/ruff | QR has 2-retry internal loop; reviewer reports BLOCKED if QR fails entirely |
| MCP kanban server down | Medium — can't read/write tasks | Fail-fast: reviewer detects error prefix, reports BLOCKED |
| Undiscovered terminal usage in reviewer workflow | Low — full inventory shows no gaps | This research is the validation |
| Parallel fan-out (#265) compatibility | None — coordinator only needs `agent`, `read`, `search`, `owlbear-kanban/*` (S7) | Fan-out design already compatible |

### 3h. Options Comparison

| Criterion | A: Remove all execute/* | B: Keep runInTerminal as fallback | C: Status quo |
|-----------|------------------------|-----------------------------------|---------------|
| Read-only enforcement | Structural (tool-level) | Instructional only | Instructional only |
| Fallback if QR fails | None (BLOCKED) | Direct terminal pytest/ruff | Direct terminal |
| KISS alignment | High — 7 tools vs 15 | Medium — 8 tools | Low — 15 tools |
| Least privilege (S2) | Best | Partial | Poor |
| Risk | Medium (QR dependency) | Low | None |
| Skill updates needed | code-review skill (MCP kanban cmds) | Minimal | None |

## 4. Recommendation (.80 confidence)

**Option A: Remove all 7 `execute/*` tools + `read/terminalLastCommand`.**

Rationale: The reviewer's "strictly read-only" persona is currently enforced by instructions alone. Removing execute/* tools makes this structural — the agent physically cannot run terminal commands. This aligns with VS Code's least-privilege recommendation (S2) and KISS (fewer tools = less room for error).

The fallback concern is valid but manageable: Quality-Runner has internal retries and timeout handling. If QR is completely unavailable, the reviewer should BLOCK rather than attempt manual debugging — that's the correct pipeline behavior (the task re-enters the queue when QR is fixed).

**Prerequisite:** Quality-Runner must be validated through at least 3-5 successful reviewer cycles before removing fallback capability. This means #317's follow-up tasks should depend on #264 completion AND a validation period.

**Scope note:** Also remove `read/terminalLastCommand` (orphaned) but leave all other `read/` tools.

## 5. Follow-up Tasks

Two tasks needed:

1. **Implementation task** — Remove execute/* tools from reviewer, update code-review skill
2. **Test task** — Verify tool removal and MCP kanban usage in skill

Both at `ideation` for architect gate.
