# Skill Cheatsheet MCP Alternatives — Scope and Approach

> **Owning task:** #576 — P2-05: Update skill cheatsheets with MCP tool alternatives alongside CLI
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #576 adds MCP tool alternatives alongside CLI references in 14 skill SKILL.md files.
Dependencies #573 (mcp-kanban SKILL.md expansion) and #572 (validation tests) are both
complete. The question is: what is the precise scope, what pattern should inline MCP
alternatives follow, and are there any skills that need special handling?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | mcp-kanban SKILL.md | Codebase | .95 — canonical MCP tool reference with full parameter tables |
| 2 | 14 skill SKILL.md files | Codebase | .95 — current CLI patterns and cheatsheet sections |
| 3 | test_mcp_tool_references_483.py | Codebase | .90 — validation test targets and assertions |
| 4 | docs/research/mcp-tool-references-alongside-cli.md | Research | .85 — CLI-to-MCP mapping from parent task #483 |
| 5 | agent-common.instructions.md | Codebase | .80 — existing MCP equivalents note pattern |

## 3. Analysis

### 3a. Current State by Category

**Category A — 8 cheatsheet skills (have `## kanban-md Commands` table + 3 MCP rows):**

| Skill | CLI refs | MCP refs | Inline CLI needing MCP alt |
|-------|----------|----------|---------------------------|
| arch-review | 13 | 3 | ~10 |
| code-review | 10 | 3 | ~7 |
| curation-workflow | 3 | 3 | ~0 |
| docs-gate | 10 | 3 | ~7 |
| task-decomposition | 9 | 3 | ~6 |
| task-verification | 11 | 3 | ~8 |
| tdd-red | 15 | 3 | ~12 |
| tdd-workflow | 10 | 3 | ~7 |

**Category B — 4 inline-ref skills (no cheatsheet, CLI scattered in body):**

| Skill | CLI refs | MCP refs | Notes |
|-------|----------|----------|-------|
| dispatch-planning | 2 | 1 | Prescriptive PS scripts, MCP note exists |
| decision-requests | 2 | 1 | Blocking/unblocking workflow |
| research-workflow | 1 | 1 | Minimal — Step 0 ref + Step 6 advance |
| kanban-md | 4 | 1 | Canonical CLI reference — already cross-refs MCP |

**Category C — 2 excluded skills (not in #572 test validation):**

| Skill | CLI refs | MCP refs | Notes |
|-------|----------|----------|-------|
| orchestration | 1 | 0 | Describes other agents' behavior, not command recipes |
| pytest-and-linting | 0 | 0 | Only a test marker description of `kanban-md` binary |

### 3b. Pattern for Inline MCP Alternatives

The established pattern in agent-common and existing skills uses a `> **MCP equivalent:**`
blockquote immediately after the CLI command. This is consistent across 6+ files already.

**Pattern A — After code block:**
```powershell
kanban\kanban-md.exe edit {id} --status review --release
```
> **MCP equivalent:** `end_work(task_id="{id}", note="...", outcome="success")`

**Pattern B — Inline note (for scattered single-line refs):**
Read task via `show {id}` (MCP: `show-task`).

**Pattern C — Table column (for cheatsheet tables):**
Already implemented — 3 rows at bottom of cheatsheet tables.

### 3c. Scope Assessment

| Item | Count | Effort |
|------|-------|--------|
| Cheatsheet table MCP rows | Already done (8 skills) | None |
| Inline CLI→MCP notes (Cat A) | ~57 inline refs across 8 skills | Medium — mechanical but high volume |
| Inline CLI→MCP notes (Cat B) | ~9 refs across 4 skills | Low |
| Passthrough mentions (Cat C) | 1-2 refs across 2 skills | Minimal |
| **Total inline insertions** | **~68** | **Medium-high volume, low complexity** |

### 3d. Not Every CLI Ref Needs an MCP Note

Some CLI refs are:
- Inside cheatsheet tables (already have MCP rows) — skip
- Generic `kanban-md` name mentions (not command invocations) — skip
- `kanban-md create` in follow-up task sections — add `create_task` note
- `kanban-md edit` in PowerShell code blocks — add MCP equivalent note after block
- `kanban-md show` read-only calls — add `show-task` note
- `kanban-md list` in PS scripts — add `list_tasks` note

The builder should add MCP notes only after **actionable CLI command invocations**,
not after every string mention of `kanban-md`.

## 4. Recommendation (.85 confidence)

Proceed as a single implementation task. The work is mechanical (add `> **MCP equivalent:**`
notes after inline CLI commands) with a clear, repeatable pattern.

**Approach:**
1. For Category A (8 cheatsheet skills): add MCP equivalent blockquotes after inline CLI
   commands in procedural steps. The cheatsheet table MCP rows are already done.
2. For Category B (4 inline-ref skills): add MCP equivalent notes inline. No cheatsheet
   table needed — these skills are structured differently.
3. For Category C (2 excluded skills): add minimal MCP cross-references where applicable.
   `pytest-and-linting` has no actionable kanban-md refs; `orchestration` mentions what
   other agents do — a brief note suffices.
4. Use the 3a CLI-to-MCP mapping from the parent research doc as the translation table.

**Risk:** High volume of small edits (~68 insertions) increases the chance of missing
refs or inconsistent formatting. The #572 validation test only checks for *presence*
of MCP tool names in cheatsheet sections and bodies, not coverage of every inline ref.
Manual spot-checks after implementation are recommended.

Challenge: FALLBACK — skipped for T1 docs-only task with established pattern.

## 5. Follow-up Tasks

No follow-up tasks needed. #576 already has well-scoped AC. The task is ready
for architect review at `backlog` status.
