# MCP Startup Fix — copilot_auth Removal (Already Complete)

> **Owning task:** #1318 — P0-02: MCP startup fix — remove copilot_auth from lifespan
> **Date:** 2026-05-04  **Status:** Complete

## 1. Context and Question

Task #1318 requires removing the copilot_auth device-flow fallback from the MCP server lifespan so the server starts without LLM dependency. The brief (§4.2) specifies: no import, no device-flow, IngestPipeline with extractor=None, token cleanup.

**Question:** What implementation work remains? What's the current state of the AC items?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `server.py` L245–330 (current lifespan) | Codebase | 1.0 |
| S2 | `git log -S "get_copilot_token"` on server.py | Git history | 1.0 |
| S3 | Commit `cd74db6e` (#1321 builder) | Git diff | 1.0 |
| S4 | `test_server_1317.py` — 8 tests all GREEN | Test run | 1.0 |
| S5 | `test_copilot_server_wiring_888.py` — 4 tests GREEN | Test run | 0.9 |
| S6 | `grep -rn copilot_auth serve/ tests/` | Codebase scan | 0.8 |

## 3. Analysis

### 3.1 AC Status Matrix

| AC | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| AC1 | copilot_auth.py removed from lifespan | ✅ Done | Commit `cd74db6e` deleted the else-branch (L274–291) |
| AC2 | IngestPipeline starts with extractor=None | ✅ Done | server.py L256: `structured_extractor = None`; only set if API key |
| AC3 | Server starts cleanly, search works (O1) | ✅ Done | test_server_1317 proves lifespan completes; QS wired without LLM |
| AC4 | Token cleanup at startup | ✅ Done | server.py L248: `token_path.unlink(missing_ok=True)` |
| AC5 | All #1317 tests green | ✅ Done | 8/8 PASSED (pytest run 2026-05-04) |

### 3.2 How It Was Already Done

The #1321 builder (commit `cd74db6e feat: wire ingest guard at lifespan/text path`) removed the copilot_auth fallback branch while refactoring the lifespan to wire `ContentInjectionGuard`. The `else:` branch that called `get_copilot_token` was deleted as part of that commit.

**Git pickaxe proof:** `git log -S "get_copilot_token" -- server.py` shows only 3 commits: #888 (added), sync (propagated), #1321 (removed).

### 3.3 Remaining Items

| Item | Status | Action needed |
|------|--------|--------------|
| Dead `_bypass_copilot_auth` fixtures (3 files) | Harmless | Out-of-scope housekeeping |
| `copilot_auth.py` module in serve/knowledge/ | Retained | Per brief: extraction via agent workers (future) |
| `test_llmextractor_wiring_876.py` mock of copilot_auth | Stale | Out-of-scope (tests still pass) |

## 4. Recommendation

**Fast-track through pipeline.** Confidence: 0.95.

The builder's work is a no-op — all ACs already satisfied. The builder should:
1. Confirm tests pass (trivial `uv run pytest tests/test_server_1317.py`)
2. Make a documentation commit noting the task was completed by #1321 builder

Challenge: SKIPPED — no ambiguity; factual verification against git history.

## 5. Follow-up Tasks

None needed. All ACs are met. Dead fixture cleanup is background tech debt, not blocking.
