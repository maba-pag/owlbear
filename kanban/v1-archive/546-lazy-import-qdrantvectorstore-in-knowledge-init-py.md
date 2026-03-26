---
id: 546
title: Lazy-import QdrantVectorStore in knowledge __init__.py
status: archived
priority: nice-to-have
created: 2026-03-04T07:38:49.8564762+01:00
updated: 2026-03-22T19:20:08.0403599+01:00
started: 2026-03-07T00:49:53.4894756+01:00
completed: 2026-03-22T19:20:08.0403599+01:00
tags:
    - audit
    - config
    - knowledge
blocked: true
block_reason: 'Stale board regression: repo, tests, and commit history show #546 already implemented; do not redispatch to builder.'
class: standard
---

F-11: knowledge/__init__.py imports QdrantVectorStore at module level. Loads qdrant module even for graph/schema/chunker only usage. Move to lazy import. AC: import owlbear.memory.knowledge doesnt load qdrant. See docs/config-dependency-audit.md.

## Research (trivial)

N/A - trivial lazy import, following existing patterns.

**Findings:**
- Line 33: `from owlbear.memory.knowledge.qdrant import QdrantVectorStore` is eagerly imported
- Zero consumers use the re-export; all 8 call sites import directly from `owlbear.memory.knowledge.qdrant`  
- Existing pattern (bootstrap.py, benchmarks): function-body deferred import with `# noqa: PLC0415`  
- Codebase does NOT use PEP 562 `__getattr__` lazy imports anywhere

**Approach:**
1. Remove the eager import on line 33
2. Remove `QdrantVectorStore` from `__all__`  
3. No `__getattr__` needed - zero callers depend on the re-export
4. Verify: `import owlbear.memory.knowledge` should not load qdrant_client

[[2026-03-21]] Sat 04:13
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Lazy-import `QdrantVectorStore` in `knowledge/__init__.py` | Already satisfied in `src/owlbear/memory/knowledge/__init__.py`: the package now uses `_LAZY_IMPORTS` + `__getattr__` and no longer performs a top-level `QdrantVectorStore` import. | Do not dispatch; task is stale relative to repo state |
| `import owlbear.memory.knowledge` does not load qdrant | Already satisfied by current package shape, archived RED task `#821`, current `tests/test_knowledge_exports.py`, and a direct runtime import check (`uv run python -c ...`) confirming `qdrant_client` and `owlbear.memory.knowledge.qdrant` stay out of `sys.modules`. | Do not dispatch; task is stale relative to repo state |

### Architecture Notes
- The task is single-domain (`knowledge`) and the original audit finding in `docs/config-dependency-audit.md` F-11 was valid, but the repository has already absorbed the fix.
- Current code contradicts the stale research note: `src/owlbear/memory/knowledge/__init__.py` now uses a PEP 562-style `__getattr__` lazy export map, so the claim that the codebase did not use that pattern is no longer true.
- Git history confirms the implementation already landed: commit `f986f54` (`feat: lazy-import QdrantVectorStore in knowledge __init__.py (#546, auditor)`) modified `src/owlbear/memory/knowledge/__init__.py` and `tests/test_knowledge_exports.py`.
- TDD compliance is satisfied in the current repo state via archived preceding test task `#821`, whose executable contract now lives in `tests/test_knowledge_exports.py`.
- Routing this card to `todo` would duplicate completed work and create avoidable churn; the correct action is to park it as stale board metadata.

### Changes Made
- Claimed `#546` as `architect`.
- Appended this architecture review.
- Blocking the task and moving it out of the builder path so completed work is not redispatched.

### Dependencies
- Verified: `#821` is archived and covers the lazy-import contract for this task.
- Verified: no additional prerequisite is missing; implementation and tests already exist in the repo.
- Gap noted: task body/status drifted behind repository and git history.
