# Memory Full Lifecycle Integration Test Design

> **Owning task:** #1315 — P1-14: Integration test — Full lifecycle (save → curate → approve → recall + git commits)
> **Date:** 2026-05-06 **Status:** Complete

## 1. Context and Question

Task #1315 requires a single integration test that exercises the full mcp-memory lifecycle end-to-end: save → list → read → curate (with scope) → approve → recall, with git commit verification at each phase boundary. Dependencies #1311 (git module GREEN) and #1308 (recall_memory GREEN) are both complete — the implementation exists.

Key design questions:
1. What's the minimal test structure that covers all 6 AC lines?
2. How to verify git commit semantics (no commit on save, batch after curate, batch after approve)?
3. How to verify recall scope filtering (returns for scoped agent, excludes non-scoped)?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 |
| S2 | engine.py | `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | 1.0 |
| S3 | git.py | `serve/mcp-memory/src/owlbear_mcp_memory/git.py` | 1.0 |
| S4 | models.py | `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | .95 |
| S5 | test_memory_git_integration_1310.py | `tests/test_memory_git_integration_1310.py` | .90 |
| S6 | test_recall_memory_1308.py | `tests/test_recall_memory_1308.py` | .90 |

## 3. Analysis

### 3A. Test Architecture — Single Linear Test vs Multi-Test Class

| Approach | Pros | Cons |
|----------|------|------|
| Single `test_full_lifecycle` function | Shows complete flow; state verified step-by-step; mirrors real usage | Long test function (~80 lines); one assertion failure hides later ones |
| Class with ordered steps via setup | Isolated assertions per AC | Complex fixture sharing; state coupling between tests |
| **Single function with explicit phases** | Clear step markers; each AC verified inline; self-documenting | Slightly longer, but readable and maintainable |

**Choice:** Single async test function with explicit phase comments. This mirrors how the system is actually used (sequential operations on the same data) and ensures state is verified at each transition.

### 3B. Interaction Layer — Direct Tool Handlers

The test calls the actual async tool handlers (`save_memory`, `list_memories`, `read_memory`, `curate_memory`, `approve_memory`, `recall_memory`) from `tools.py` using a `MagicMock` context wired to a real `MemoryEngine` on a git-initialised `tmp_path`. This matches existing test patterns (S5, S6).

`commit_batch` from `git.py` is called explicitly between phases — it's not auto-triggered by tool handlers.

### 3C. Git Verification Strategy

| Phase | Expected git state |
|-------|-------------------|
| After save_memory | commit count = 1 (initial only); file exists on disk uncommitted |
| After curate + commit_batch("curation") | commit count = 2; curated file staged and committed |
| After approve + commit_batch("review") | commit count = 3; approved file staged and committed |

### 3D. Scope Filtering Verification

- Create entry with `scope_agents=["builder"]`
- `recall_memory(agent="builder")` → returns entry body
- `recall_memory(agent="reviewer")` → returns empty string

### 3E. State Transition Verification

| Step | Expected state |
|------|---------------|
| After save_memory | pending |
| After curate_memory (with scope_agents) | curated |
| After approve_memory | approved |

### 3F. Test Infrastructure Requirements

- `pytest.mark.asyncio` — tool handlers are async
- `tmp_path` + git init — same pattern as test_memory_git_integration_1310.py
- `MagicMock` context with `engine` on `lifespan_context`
- `subprocess` for git verification (commit count, status)

## 4. Recommendation (.92 confidence)

Write a single test file `tests/test_memory_lifecycle_1315.py` with one integration test class containing one primary test (`test_full_lifecycle`) that:

1. Initialises a git repo with `MemoryEngine` on `tmp_path/memory`
2. Calls `save_memory` → asserts state=pending, no new git commit
3. Calls `list_memories` → asserts entry present with pending state
4. Calls `read_memory` → asserts full entry returned
5. Calls `curate_memory` with `scope_agents=["builder"]` → asserts state=curated
6. Calls `commit_batch(session_type="curation")` → asserts exactly 1 new commit
7. Calls `approve_memory` → asserts state=approved with `approved_at` set
8. Calls `commit_batch(session_type="review")` → asserts exactly 1 more commit
9. Calls `recall_memory(agent="builder")` → asserts entry body present
10. Calls `recall_memory(agent="reviewer")` → asserts empty (scope exclusion)

Plus a second test (`test_recall_excludes_non_scoped`) if needed for AC4 isolation, but the single test covers it inline.

Challenge: FALLBACK — no challenger invoked (trivial test design, no architectural trade-offs to challenge).

## 5. Follow-up Tasks

Task #1315 itself is the implementation task. No additional follow-up tasks needed — the research informs RED/GREEN phases for #1315.
