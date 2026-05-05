# Memory Review Prompt Design

> **Owning task:** #1314 — P1-13: Review prompt — Create memory-review.prompt.md
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1314 creates a user-facing prompt file (`share/prompts/memory-review.prompt.md`) that guides the user through a review session of MCP memory entries. The prompt invokes MCP tools directly — no dedicated agent required. The user approves, requests changes, or rejects entries one by one, then commits all mutations at session end.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/mcp-memory/src/owlbear_mcp_memory/server.py` — tool signatures | 1.0 |
| S2 | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` — implementation + hints | 1.0 |
| S3 | `share/prompts/memory-audit.prompt.md` — similar review pattern | 0.9 |
| S4 | `share/agents/memory-curator.agent.md` — tools list for reference | 0.8 |
| S5 | `.owlbear/research/consumer-updates-p1-curator-memory.md` — tool naming | 0.9 |

## 3. Analysis

### 3.1 Tool API Summary (Review-Relevant)

| Tool | Key Params | Returns | Role in Workflow |
|------|-----------|---------|-----------------|
| `list_memories` | `states[]`, `categories[]`, `scope_agents[]` | metadata list (no content) | Step 1: inventory |
| `read_memory` | `entry_id` | full entry (with content) | Step 2: inspect |
| `approve_memory` | `entry_id` | updated entry + hint | Decision: promote |
| `curate_memory` | `entry_id`, optional fields | updated entry + hint | Decision: revise |
| `delete_memory` | `entry_id` | deleted entry + hint | Decision: reject |

### 3.2 Prompt Frontmatter

VS Code `.prompt.md` supports `tools:` array. No existing prompt uses it yet; this will be the first. Format: `tools: [ob-memory/list_memories, ...]`.

### 3.3 Workflow Pattern (from memory-audit.prompt.md analogy)

The existing `memory-audit.prompt.md` uses a per-finding loop with `askQuestions`. The review prompt follows the same pattern but operates on MCP entries:

1. **List** — `list_memories(states: ["pending", "curated"])` — show count + summary table
2. **Read** — `read_memory(entry_id)` — present full content
3. **Decide** — user chooses: approve / request changes / reject / skip
4. **Batch commit** — at session end, instruct user to `git add .owlbear/memory/ && git commit`

### 3.4 Batch Commit Semantics

Memory engine writes files immediately on each mutation. "Batch commit" in the AC means a single `git commit` at session end (all reviewed entries in one commit). The prompt body instructs this — no tool needed.

## 4. Recommendation (confidence: 0.94)

Implement as a self-contained prompt with:
- `tools:` frontmatter listing the 5 review tools
- No `agent:` field (runs in default mode with declared tools)
- Body follows list→read→decide loop pattern from memory-audit
- Batch commit instruction at the end

Challenge: SKIPPED — trivial file creation following established patterns, no competing approaches.

**Classification: T1 (Autonomous).** No design decisions or alternative approaches to evaluate.

## 5. Follow-up Tasks

None needed — the task itself (#1314) moves to backlog for implementation. The AC is fully specified and implementation is mechanical.
