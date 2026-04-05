# Phase B: Remove CLI Fallback, MCP-Only Kanban for All Agents

> **Owning task:** #484 — Phase B: Remove CLI fallback, MCP-only kanban for all agents
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #484 is Phase B of a 2-phase MCP migration. Phase A (#483, currently in review)
adds MCP tool references alongside CLI. Phase B removes CLI fallback, making MCP tools
the sole kanban interface for agents. Scope: ~24 files (agents, skills, instructions).
Historical research docs keep their CLI references.

**Key question:** What is the precise scope, what gaps exist in MCP tool coverage,
and how should the work be decomposed?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | mcp-kanban SKILL.md | Codebase | .95 — canonical 8-tool MCP reference |
| 2 | mcp-tool-references-alongside-cli.md | Research | .90 — CLI-to-MCP mapping from #483 |
| 3 | skill-cheatsheet-mcp-alternatives.md | Research | .85 — skill file scope analysis |
| 4 | agent-common-mcp-alternatives-gap.md | Research | .85 — instruction file gap audit |
| 5 | 11 agent files, 13 skill files, 2 instruction files | Codebase | .95 — verified CLI ref counts |

## 3. Analysis

### 3a. Verified CLI Reference Inventory

| Category | Files | CLI refs | Notes |
|----------|-------|----------|-------|
| Agent files | 11 | 44 | AC says "10 files" — actually 11 |
| Skill files | 13 | 93 | AC says "10 files" — actually 13 |
| agent-common.instructions.md | 1 | 7 | Plus PS escaping section to remove |
| research-docs.instructions.md | 1 | 1 | Minor — L14 `kanban-md create` ref |
| copilot-instructions.md | 1 | ~7 | **Not in AC** — but loaded by all agents |
| **Total** | **27** | **~152** | AC undercounts by 3-4 files |

### 3b. MCP Tool Coverage Gaps

| CLI Command | MCP Equivalent | Gap? |
|------------|----------------|------|
| `show`, `edit`, `create`, `move`, `list`, `pick` | 1:1 mapping | None |
| `start_work`, `end_work` | Compound tools | None |
| `delete {id} --yes` | **No equivalent** | architect merge operation |
| `handoff` | `edit_task` + `end_work(outcome="block")` | Multi-call, race window |
| `board --compact` | `list_tasks` | Behavioral difference |
| `archive {id}` | `end_work(outcome="success")` at last status | None |

**`delete` gap:** Used by architect for merge operations (arch-review SKILL.md L23).
Options: (a) add `delete_task` to MCP server, (b) document as terminal-only exception.

**`handoff` gap:** Current CLI uses single atomic call. MCP requires 2 calls:
`edit_task(append_body=...)` then `end_work(outcome="block", block_reason=...)`.
Race window is minimal — only the holding agent calls handoff on its own task.

### 3c. Sections Requiring Structural Rewrite (Not Just Find/Replace)

1. **agent-common.instructions.md § PowerShell escaping** — entire section obsolete
   with MCP (pipe chars, arrow parsing, temp-file pattern). Remove and add brief note
   that MCP tools avoid these pitfalls.
2. **agent-common.instructions.md § Channel B** — rewrite CLI examples to MCP syntax.
3. **agent-common.instructions.md § Handoff/blocked** — rewrite with MCP multi-call
   pattern or retain as terminal-only escape hatch.
4. **agent-common.instructions.md § Tool discipline** — remove `kanban-md` from
   terminal use list (L205).
5. **kanban-md SKILL.md** — either retire (redirect to mcp-kanban) or rewrite
   claiming protocol examples to MCP syntax.
6. **copilot-instructions.md § kanban-md usage** — convert agent-facing CLI commands
   to MCP equivalents while keeping the section as project-level documentation.
7. **Skill cheatsheet tables** — rewrite `## kanban-md Commands` to `## MCP Commands`.

### 3d. copilot-instructions.md Scope Decision

The AC mentions agents/ and skills/ for grep verification. But copilot-instructions.md
is loaded into every agent context. CLI commands at L143, L149, L165, L169 would
undermine the migration if agents still see them. **Recommend including in scope.**
The kanban-md section can remain as project documentation but CLI examples should
become MCP-primary with CLI as human-user alternative.

## 4. Recommendation (.70 confidence)

**T1 classification** — pre-approved user task. Not a new capability; documenting
migration of existing MCP tools that are already registered and functional.

**Recommended decomposition (5 subtasks):**

1. **Agent files** (11 files, 44 refs) — Replace CLI with MCP tool calls in output
   format sections, examples, and verdict examples.
2. **Skill cheatsheet files** (8 files with tables) — Rewrite kanban-md cheatsheet
   tables to MCP-only. Add `> **CLI fallback:**` notes where terminal-only (delete).
3. **Skill inline-ref files** (5 files) — Update dispatch-planning, decision-requests,
   kanban-md, orchestration, research-workflow.
4. **Instruction files** (agent-common + research-docs) — Structural rewrites per §3c.
   Remove PS escaping, rewrite Channel B, update tool discipline.
5. **copilot-instructions.md** — Convert kanban-md section to MCP-primary.

**Risk:** Largest single-diff change in codebase history (~152 refs across 27 files).
Recommend incremental validation between subtasks.

Challenge: reconsider — confidence in original: .55.
Challenger raised valid concerns: AC undercounting (accepted, corrected in §3a),
delete/handoff MCP gaps (accepted, documented in §3b), copilot-instructions.md
exclusion (accepted, included per §3d), dependency timing (accepted — #483 must
complete first). Rebutted T2 reclassification: task is pre-approved by user with
explicit AC, not a new capability decision. Adjusted confidence from .80 to .70.

## 5. Follow-up Tasks

Tasks created at `ideation` with dependency on #484 (parent task). The parent
task itself depends on #483 completing. AC corrections noted for architect review.
