# Curator Workflow Design for memory-mcp

> **Owning task:** #528 — Design curator workflow for memory-mcp
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

How should the curator agent and curation-workflow skill be updated to work with memory-mcp? The current curator reads lesson files from `/memories/repo/inbox/`, triages them via the built-in memory tool, and produces a curation report. The memory-mcp design (§3I, S1) specifies MCP tools (`list_entries`, `mark_for_deletion`, `record_learning`) as the new interface. This research fleshes out the concrete workflow changes, approval mechanism, and migration path. **Contingent on DR #387 approval** (S2, currently pending).

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | memory-mcp design doc | `docs/research/memory-mcp-server-design.md` §3E-3I | .95 |
| S2 | DR #387 (pending) | `docs/decisions/pending/387-memory-mcp-architecture.md` | 1.0 |
| S3 | DR #428 (resolved) | `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` | .90 |
| S4 | Current curator agent | `agents/curator.agent.md` | .95 |
| S5 | Current curation-workflow | `skills/curation-workflow/SKILL.md` | .95 |
| S6 | Mem0 memory ops | `github.com/mem0ai/mem0` — Memory class (add/get/delete/history) | .75 |
| S7 | LangMem conceptual guide | `langchain-ai.github.io/langmem/concepts/conceptual_guide` | .70 |
| S8 | agent-common instructions | `instructions/agent-common.instructions.md` L248 (inbox pattern) | .90 |
| S9 | #499 schema definitions | `docs/research/deer-flow-memory-patterns-schema-definitions.md` | .85 |

## 3. Analysis

### 3A. Current vs Proposed Workflow

| Step | Current (file-based) | Proposed (MCP-based) |
|------|---------------------|---------------------|
| Gather | `memory view /memories/repo/inbox/` + read each file | `list_entries(status="pending")` via MCP |
| Dedup | Manual text comparison across files | Semantic comparison across entry `content` fields |
| Delete noise | `memory delete /memories/repo/inbox/{file}` | `mark_for_deletion(entry_id)` — soft-delete, reversible |
| Promote | Write to `/memories/repo/` or propose instruction edits | Write recommendation to report; user calls `set_approval_state` |
| Cross-pollinate | Not supported | `record_learning` with broader scope |
| Report | Channel B task body | Channel B task body (unchanged) |

### 3B. Approval Mechanism

| Approach | KISS | User Control | MCP Consistency | Testability |
|----------|------|-------------|-----------------|-------------|
| A: CLI reads SQLite directly | High | High | **Low — bypasses MCP** | Medium |
| B: Report + standalone CLI (original) | Medium | High | **Low — bypasses MCP** | Medium |
| C: `set_approval_state` MCP tool + CLI wrapper | Medium | High | **High — all access via MCP** | High |
| D: `promote_entry` in curator toolset | High | **None — violates DR** | High | High |

**Recommendation (.78): Option C.** Add a `set_approval_state` MCP tool to memory-mcp that transitions entries between `pending`/`approved`/`deleted`. Restrict it to user-facing agents only (exclude from pipeline agent toolsets). Wrap in a CLI script (`scripts/approve_memory.py`) that calls the MCP tool via the server, maintaining a single data-access path. DR #428 constrains permanent deletion (user-only), not approval state transitions (S3).

### 3C. Cross-Pollination Design

Curator calls `record_learning` with broader scope to generalize agent-specific insights. Cross-pollinated entries enter the `pending` queue (by design — user oversight). The `source` field identifies lineage: format `curator:cross-pollinate:{original_id}`. This prevents accidental dup deletion and maintains traceability.

**Intentional re-approval:** Cross-pollinated entries ARE reviewed again. The user sees them as "curator-recommended generalizations" in the next curation cycle. This is the correct behavior — broadening scope is a judgment call that benefits from human validation.

### 3D. Tool Permissions

| Tool | Curator access? | Other pipeline agents? | User agents? |
|------|----------------|----------------------|-------------|
| `list_entries` | Yes (read pending entries) | No | Yes |
| `mark_for_deletion` | Yes (soft-delete noise) | No | Yes |
| `record_learning` | Yes (cross-pollinate) | Yes (write learnings) | Yes |
| `get_knowledge` | No (not needed) | Yes (auto-load) | Yes |
| `set_approval_state` | **No** (user-only) | **No** | **Yes** |

Curator keeps `vscode/memory` for `/memories/` and `/memories/session/` access. `owlbear-memory/*` tools added alongside (S4 tool list). `set_approval_state` excluded from curator toolset — approval is a privileged user operation.

### 3E. Curation-Workflow Skill Changes

**Step 1 — Gather:** Replace `memory view /memories/repo/inbox/` with `list_entries(status="pending")`. During migration (§3F), also check the file-based inbox for stragglers.

**Step 2 — Dedup:** Unchanged (semantic comparison). If pattern 3 (content dedup) is approved via DR #387 Option B, the MCP server handles dedup at write time, reducing curator's dedup burden.

**Step 3 — Assess signal:** Unchanged (HIGH/MEDIUM/LOW/NOISE/CONFLICT rating).

**Step 4 — Act:**

| Rating | Current action | New action |
|--------|---------------|-----------|
| HIGH | Write to /memories/repo/ or propose instruction edits | Write recommendation with entry IDs to report. Propose instruction edits (unchanged). |
| MEDIUM | Keep in inbox | No action (entry stays `pending` for next cycle) |
| LOW/NOISE | `memory delete` | `mark_for_deletion(entry_id)` |
| CONFLICT | Decision request | Decision request (unchanged) |
| CROSS-POLLINATE (new) | N/A | `record_learning` with broader scope, source=`curator:cross-pollinate:{id}` |

**Step 5 — Report:** Include entry IDs with recommendations. Format: `| Entry ID (short) | Content preview | Recommendation | Reason |`

### 3F. Migration Period

During dual-write (design doc §3L phase 2), curator must:
1. Read BOTH `/memories/repo/inbox/` AND `list_entries(status="pending")`
2. Process all entries through the same dedup/signal pipeline
3. For inbox files: use `memory delete` (old path). For MCP entries: use `mark_for_deletion` (new path)
4. After phase 4 cut-over: remove inbox-reading step entirely

### 3G. Soft-Delete Reversibility

`mark_for_deletion` sets `approval_state=deleted` and `deleted_at`. To reverse a false positive, user calls `set_approval_state(entry_id, "pending")` to restore visibility. Entries are never permanently deleted by agents — only users via CLI.

## 4. Recommendation (.78 confidence)

MCP-tool-based curator workflow replacing file-based inbox. Key design choices: (1) `set_approval_state` MCP tool restricted to user agents for all DB state transitions, maintaining single data-access path through MCP; (2) cross-pollination via `record_learning` with source lineage, entries re-enter pending queue intentionally; (3) dual-write migration period with parallel processing. Follows existing MCP patterns and preserves user oversight per DR #428.

Challenge: block — confidence in original: .45. Challenger raised valid concerns about DR #387 dependency (rebutted: research proceeds ahead of DR, design is contingent), CLI-bypasses-MCP (accepted: revised to MCP tool), cross-pollination duplication (accepted: addressed with source lineage and intentional re-approval). Revised confidence from .85 to .78.

## 5. Follow-up Tasks

All contingent on DR #387 approval. No separate DR needed — curator workflow is a component within the already-gated memory-mcp architecture.

```
kanban\kanban-md.exe create "Add set_approval_state MCP tool to memory-mcp" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Add a 5th MCP tool to memory-mcp for approval state transitions. Per docs/research/curator-workflow-memory-mcp.md. Depends on #525.\n\nAC:\n- [ ] set_approval_state(entry_id, new_state) validates state transitions (pending->approved, pending->deleted, deleted->pending)\n- [ ] Tool has correct ToolAnnotations (not readOnly, not idempotent)\n- [ ] Tool excluded from pipeline agent toolsets — user-facing agents only\n- [ ] Reversibility: deleted entries can be restored to pending" --depends-on 525
kanban\kanban-md.exe create "Update curator agent and skill for memory-mcp" --priority important --status ideation --tags "scope:agents,phase-2" --body "Update curator.agent.md and curation-workflow/SKILL.md for memory-mcp integration. Per docs/research/curator-workflow-memory-mcp.md. Depends on #525.\n\nAC:\n- [ ] Curator agent tools include owlbear-memory list_entries, mark_for_deletion, record_learning\n- [ ] Curator agent retains vscode/memory for /memories/ access\n- [ ] Curation-workflow Step 1 updated: list_entries(status=pending) replaces memory view\n- [ ] Curation-workflow Step 4 updated: mark_for_deletion replaces memory delete\n- [ ] New cross-pollination step: record_learning with source=curator:cross-pollinate:{id}\n- [ ] Report format includes entry IDs with short preview and recommendation" --depends-on 525
kanban\kanban-md.exe create "Build approve_memory CLI wrapper for set_approval_state" --priority important --status ideation --tags "scope:agents,phase-2" --body "CLI script wrapping set_approval_state MCP tool for user batch approval. Per docs/research/curator-workflow-memory-mcp.md.\n\nAC:\n- [ ] scripts/approve_memory.py lists pending entries with content preview\n- [ ] Interactive mode: user selects entries to approve/reject\n- [ ] Batch mode: approve by ID list\n- [ ] Calls set_approval_state MCP tool (not direct SQLite)\n- [ ] Shows curator recommendations from curation report if available" --depends-on 525
```
