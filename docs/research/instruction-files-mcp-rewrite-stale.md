# Instruction Files MCP Rewrite — Stale Scope

> **Owning task:** #583 — P2-B4: Rewrite instruction files to MCP-only
> **Date:** 2026-04-04 **Status:** Complete (no-op)

## 1. Context and Question

Task #583 was created from docs/research/phase-b-mcp-only-kanban-migration.md §3c
(2026-04-03) to structurally rewrite agent-common.instructions.md and
research-docs.instructions.md: remove PS escaping, rewrite Channel B, update tool
discipline, replace CLI refs with MCP equivalents.

**Question:** Does any of this scope still exist in the current codebase?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | .github/instructions/ directory listing | Codebase | 1.0 — actual file inventory |
| 2 | All 4 instruction files (full content) | Codebase | 1.0 — verified zero CLI refs |
| 3 | Parent task #484 body (architect review) | Kanban | .95 — stale subtask disposition |
| 4 | phase-b-mcp-only-kanban-migration.md | Research | .90 — original scope source |

## 3. Analysis

### Instruction File Inventory (verified 2026-04-04)

| File | Lines | Content | CLI refs |
|------|-------|---------|----------|
| agents-and-skills.instructions.md | 6 | Stub → h-agent-structure skill | 0 |
| frontend.instructions.md | 6 | Stub → h-frontend-conventions skill | 0 |
| python.instructions.md | 6 | Stub → h-python-conventions skill | 0 |
| research-docs.instructions.md | 6 | Stub → w-research skill | 0 |

### AC Verification

| AC Item | Status | Evidence |
|---------|--------|----------|
| agent-common Channel B uses MCP syntax | N/A | File does not exist |
| PS escaping guidance removed | N/A | File does not exist |
| Tool discipline no longer lists kanban-md | N/A | File does not exist |
| research-docs uses create_task MCP syntax | N/A | File is a 6-line stub, no kanban refs |
| 0 kanban-md matches in instructions/ | PASS | grep verified: 0 matches |

### Root Cause

The workspace was reorganized between research (2026-04-03) and now. The content
that was in agent-common.instructions.md was either moved into skill files or
removed. All instruction files became thin stubs pointing to their respective skills.
The CLI-to-MCP migration work is captured in parent task #484's revised AC.

## 4. Recommendation

**T1 — Autonomous.** No scope remains. Task should be cancelled.

Confidence: .95 — all 5 AC items verified as either N/A (file absent) or already
passing (zero CLI matches). No ambiguity.

Challenge: FALLBACK — no recommendation to challenge (finding is "no work needed").

## 5. Follow-up Tasks

None. All remaining CLI-to-MCP instruction scope is captured in parent #484's
revised AC. The parent's architect review explicitly marked #583 as stale.
