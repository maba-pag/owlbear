# Mutation Tools + Access Control Removal — Implementation Readiness

> **Owning task:** #1307 — P1-06: GREEN — Mutation tools + access control removal
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1307 implements the GREEN phase for 6 mutation MCP tools and removes legacy access control. Dependencies #1305 (state machine) and #1306 (RED tests) are both archived/done. The question: what implementation work remains for the builder?

## 2. Sources Studied

| # | Source | Path | Relevance |
|---|--------|------|-----------|
| S1 | Current server.py | `serve/mcp-memory/src/owlbear_mcp_memory/server.py` | 1.0 |
| S2 | Current tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 |
| S3 | Brief (tool surface) | `.owlbear/briefs/draft-memory-mcp-ux/brief.md` §Tool Surface | 1.0 |
| S4 | #1306 test file | `tests/test_mutation_tools_1306.py` | 1.0 |
| S5 | #1273 test file | `tests/test_mcp_memory_tools_1273.py` (imports from server) | 0.9 |
| S6 | Package README | `serve/mcp-memory/README.md` | 0.8 |

## 3. Analysis

### 3A. Current State vs AC

| AC Item | Status | Evidence |
|---------|--------|----------|
| 6 MCP tools registered (save/list/read/curate/delete/approve) | **NOT DONE** | server.py still registers old 5: store_learning, query_memory, update_entry, delete_entry, approve_entry |
| Correct parameter schemas | DONE | Implementations in tools.py match Brief spec |
| Validation → teaching messages | DONE | `_teaching_validation_message()` handles all cases |
| State transitions delegate to #1305 | DONE | Logic inline in tools.py (auto-promote, auto-downgrade, `_ensure_update_transition`) |
| OWLBEAR_MEMORY_CALLER deleted | **NOT DONE** | Still in server.py:51, AppContext, README.md |
| MEMORY_TOOLS_EXCLUDE deleted | DONE | Not in server.py source |
| Role-check code removed | DONE | No `_require_role` or caller-gating exists |
| list_memories pending-first ordering | DONE | `_state_rank_for_list` sorts pending=0, curated=1, approved=2 |
| All #1306 tests pass | DONE | 47 passed, 0 failed |

### 3B. Required Changes (server.py rewiring)

| Change | File | LOC estimate |
|--------|------|------|
| Replace 5 old `@mcp.tool` wrappers with 6 new ones | server.py | ~60 LOC rewrite |
| Remove `caller` from `AppContext` dataclass | server.py | -1 line |
| Remove `OWLBEAR_MEMORY_CALLER` from `app_lifespan` | server.py | -1 line |
| Remove `_caller_from_ctx` helper | tools.py | -4 lines |
| Update import block in server.py | server.py | ±10 lines |
| Remove OWLBEAR_MEMORY_CALLER from README.md | README.md | -1 line |

### 3C. Regression Risk: test_mcp_memory_tools_1273.py

This test file imports `query_memory` from `server.py` (line 28). After rewiring, `query_memory` won't exist in server module → ImportError at collection time (blocks 20+ sibling tests).

**Fix options:**
- (A) Import from `tools.py` instead (1-line change) — old tool functions remain in tools.py
- (B) Delete the server-level test class (it tests old API surface being removed)

Recommendation: Option A (.85 confidence) — minimal diff, keeps regression coverage on query logic.

### 3D. Dead Code

After rewiring, old functions (`store_learning`, `query_memory`, `update_entry`, `delete_entry`, `approve_entry`) remain in tools.py but are unreachable from server.py. They're still imported by test_mcp_memory_1266.py and test_mcp_memory_tools_1273.py. Removing them is out of scope (would break sibling test files); a follow-up cleanup task can retire them.

### 3E. approve_memory Hint Gap

Brief specifies `approve_memory` should return hint: "Entry approved. Now visible to scoped agents." Current implementation delegates to `approve_entry` which returns `_entry_to_dict()` (no hint). The #1306 test suite does NOT test for this hint. Builder should add it for Brief compliance even though tests don't enforce it.

## 4. Recommendation (.92 confidence)

**Proceed to builder.** The implementation is 80% done — tools.py has all logic passing all #1306 tests. Remaining work is mechanical server.py rewiring (~60 LOC) plus access control removal (~6 lines deleted) plus README update.

Challenge: SKIPPED — info-only readiness assessment, no alternative approaches to evaluate.

**Classification: T1 (Autonomous).** No DR needed.

## 5. Follow-up Tasks

- Builder implements server.py rewiring, env var removal, and README cleanup (this task #1307 itself, advancing to backlog)
- Dead code cleanup of old tool names in tools.py (separate future task, post-#1309)
