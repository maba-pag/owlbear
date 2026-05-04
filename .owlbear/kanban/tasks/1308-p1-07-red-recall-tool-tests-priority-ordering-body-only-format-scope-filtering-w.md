---
id: 1308
title: 'P1-07: RED — Recall tool tests (priority ordering, body-only format, scope
  filtering, wildcard block)'
status: in-progress
priority: needed
created: 2026-05-04T01:32:18.553275+00:00
updated: 2026-05-04T15:47:57.849038+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1305
blocked: false
block_reason:
claimed_at: 2026-05-04T15:47:57.849038+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Tests assert recall returns entries where agent name is in scope_agents (td:2)
- [ ] Tests assert recall includes entries where scope_agents=["*"] (universal) (td:2)
- [ ] Tests assert recall excludes entries where scope_agents=[] (unscoped) (td:2)
- [ ] Tests assert recall with agent="*" is code-blocked (rejected with error) (td:1)
- [ ] Tests assert return format is body-only: title as ## heading, content below, no metadata (td:2)
- [ ] Tests assert ordering: approved entries first, then curated entries fill remaining slots (td:2)
- [ ] Tests assert limit parameter works (default 20) (td:1)
- [ ] All tests fail (RED state) (td:0)

## Scope

- In: recall_memory query behavior, result format, filtering, ordering
- Out: other 6 tools (already in #1306/#1307), git integration, consumer wiring
[[2026-05-04]]
## Research

Research gate passed — trivial-scope RED task with prescriptive AC and established patterns.

### Findings
1. `recall_memory` does not exist yet in `owlbear_mcp_memory.tools` — ImportError guarantees RED
2. Expected signature (from #1309 AC): `recall_memory(ctx, *, agent: str, categories: list | None = None, limit: int | None = None) -> str`
3. Return format: concatenated "## {title}\n{content}" strings, not metadata dicts
4. Ordering: approved (state_rank 0) before curated (state_rank 1)
5. Scope filtering: include entries where agent in scope_agents OR scope_agents=["*"]; exclude scope_agents=[]
6. Wildcard block: agent="*" raises ToolError
7. Test pattern: follow test_state_machine_1304.py (mock engine, mock ctx, _make_entry factory)

### Implementation approach for test-writer
- File: tests/test_recall_memory_1308.py
- Import recall_memory from owlbear_mcp_memory.tools (causes ImportError = RED guarantee)
- 7 test classes mapping 1:1 to ACs
- Use same _make_ctx/_make_entry helpers as test_state_machine_1304.py
- All tests async (pytest-asyncio)

No research doc needed — no design decisions or trade-offs involved. AC is fully prescriptive.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for one tool (recall_memory) only |
| Interface clarity | PASS | Each AC line specifies exact testable behavior |
| Dependency correctness | PASS | #1305 archived/done |
| Module layering | PASS | Tests import from owlbear_mcp_memory.tools — correct direction |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope — tests only |
| Premise challenge | PASS | recall_memory is distinct from query_memory (body-only str vs dict metadata) |
| Pattern consistency | PASS | Follows test_state_machine_1304.py pattern |
| Security surface | PASS | No new system boundaries; wildcard block is AC |
| Single domain | PASS | mcp-memory only |

### Challenge Results
- Challenger: reconsider (0.68)
- Concerns: categories coverage, module-scope import pattern, brief inheritance, discriminating failure
- Architect response: OVERRIDE — categories is optional filter with same query_memory mechanics (no separate AC needed); import strategy is test-writer implementation choice not AC defect; AC derived from brief by researcher; discriminating failure inherent to RED phase (tests exercise assertions in GREEN)

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Annotated AC with test depths, approved to todo
[[2026-05-04]]
Architecture review complete. All 10 criteria PASS. Challenger override justified — concerns are implementation-level observations not AC defects. Test depths annotated (max td:2). Approved to todo for test-writer.
[[2026-05-04]]
## Test-Writer Notes

**File:** `tests/test_recall_memory_1308.py`

**Test classes and counts:**

| Class | AC | Tests | Category |
|---|---|---|---|
| `TestFromAC_ScopeAgentMatch` | AC1 | 3 | happy + edge |
| `TestFromAC_UniversalScope` | AC2 | 3 | happy + boundary |
| `TestFromAC_UnscopedExclusion` | AC3 | 3 | happy + edge + boundary |
| `TestFromAC_WildcardAgentBlock` | AC4 | 1 | error |
| `TestFromAC_BodyOnlyFormat` | AC5 | 5 | happy + boundary |
| `TestFromAC_PriorityOrdering` | AC6 | 4 | happy + boundary + edge |
| `TestFromAC_LimitParameter` | AC7 | 2 | happy + boundary |

**Total: 21 tests — all FAIL (RED state confirmed)**

**Failure mechanism:** `recall_memory` does not exist in `owlbear_mcp_memory.tools`. A deferred-import proxy `_recall()` ensures each test fails individually with `ImportError` (not a collection error).

**AC coverage:**

| AC | Covered |
|---|---|
| recall returns entries where agent in scope_agents | ✅ 3 tests |
| recall includes scope_agents=["*"] entries | ✅ 3 tests |
| recall excludes scope_agents=[] entries | ✅ 3 tests |
| agent="*" raises ToolError | ✅ 1 test |
| body-only format: ## heading + content, no metadata | ✅ 5 tests |
| approved before curated in output | ✅ 4 tests |
| limit parameter, default 20 | ✅ 2 tests |

**Ruff:** exit 0, no issues.