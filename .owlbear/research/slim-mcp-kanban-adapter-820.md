# Slim mcp-kanban Adapter

> **Owning task:** #820 — Slim mcp-kanban adapter
> **Date:** 2026-04-15 **Status:** Complete

## 1. Context and Question

Task #820 is the GREEN implementation step (Phase 2, step 4) that slims the mcp-kanban package down to a thin adapter over the extracted `owlbear_kanban` engine. The question: **what implementation work is needed for #820?**

**Key finding: #818 already completed all slimming work.** The builder for #818 ("Extract engine to serve/kanban/ + workspace config") performed both the extraction AND the adapter slimming in a single pass. Every #820 AC line is already satisfied. #820 is a verification-only task.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/mcp-kanban/src/owlbear_mcp_kanban/` directory listing | Codebase | 1.0 — confirms only 4 files remain |
| S2 | `serve/mcp-kanban/pyproject.toml` | Codebase | 1.0 — confirms `owlbear-kanban` dependency |
| S3 | `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` L15-18 | Codebase | 1.0 — confirms `owlbear_kanban` imports |
| S4 | `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Codebase | 0.9 — confirms `KanbanTask` retained |
| S5 | Task #818 body (builder + review notes) | Kanban | 0.9 — documents extraction + slimming work |
| S6 | Task #819 body (test-writer + review) | Kanban | 0.9 — 19 regression tests, all GREEN |
| S7 | `.owlbear/research/mcp-adapter-slimming-tests-819.md` | Research doc | 0.8 — prior research confirming #818 did slimming |
| S8 | `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md` | Brief | 0.8 — Phase 2 decomposition context |
| S9 | `tests/test_mcp_adapter_slimming_819.py` | Codebase | 0.9 — test file structure and assertions |

## 3. Analysis

### 3.1 AC Compliance — Current State

| AC Line | Current State | Evidence |
|---------|---------------|----------|
| pyproject.toml adds `owlbear-kanban` dep | ✅ Already done | S2: `dependencies = ["mcp[cli]>=1.26", "owlbear-kanban"]` |
| server.py imports from `owlbear_kanban` | ✅ Already done | S3: L15 `from owlbear_kanban import KanbanEngine`, L16-17 dispatch + models |
| Engine modules removed from source tree | ✅ Already done | S1: only `server.py`, `models.py`, `__init__.py`, `__main__.py` remain |
| models.py retains KanbanTask | ✅ Already done | S4: full Pydantic model with 12 fields + `_coerce_claimed` validator |
| `__main__.py` retained | ✅ Already done | S1: present with `mcp.run()` entry point |
| #819 tests pass GREEN | ✅ Per review | S6: 19/19 passed at confidence .97 |
| All 8 MCP tool tests pass (O4) | ✅ Per builder | S5: 362 passed in engine + MCP suite |

### 3.2 Why #820 Is a No-Op

The task decomposition (Brief Phase 2) assumed extraction (#818) and slimming (#820) would be separate steps. In practice, extraction required slimming: moving engine files out of mcp-kanban necessitated updating imports and adding the `owlbear-kanban` dependency. The #818 builder did both atomically.

This is the same pattern identified in #819's research (S7): "#818 already completed both extraction AND slimming."

### 3.3 Dependency Status Risk

| Concern | Detail | Impact on #820 |
|---------|--------|----------------|
| #818 stuck in-progress | Review FAILed (.65) — `engine_models.py` not deleted | **None** — file was subsequently deleted (S1 confirms absent). #818 needs re-review but the work is complete. |
| #819 at done | 19 tests pass GREEN, reviewed at .97 | #820 can rely on these tests as verification |

### 3.4 Builder Guidance

Since all AC lines are met, the #820 GREEN builder should:

1. Run `uv run pytest tests/test_mcp_adapter_slimming_819.py -q --tb=short` — verify 19 pass
2. Run `uv run pytest tests/ -k "kanban" -q --tb=short` — verify O4 (all MCP tool tests)
3. Confirm no engine files in `serve/mcp-kanban/src/owlbear_mcp_kanban/` (only 4 files)
4. Submit a verification-only builder note — no code changes needed

## 4. Recommendation

**Verification-only pass** (confidence: 0.92)

No implementation work is needed. The #820 builder runs tests and confirms AC compliance. This is identical to how #819 handled the same situation (builder submitted a verification-only note).

Challenge: FALLBACK — challenger subagent not available in researcher mode.

### Tier Classification

**T1 — Autonomous.** No new capability, architecture change, or security impact. The task is a verification of already-completed work.

## 5. Follow-up Tasks

None needed. The work is complete; verification is self-contained within #820.

**Note:** #818's stuck `in-progress` status is a separate concern — it should be re-reviewed (the `engine_models.py` fix was the only blocking issue, now resolved). This is outside #820's scope.
