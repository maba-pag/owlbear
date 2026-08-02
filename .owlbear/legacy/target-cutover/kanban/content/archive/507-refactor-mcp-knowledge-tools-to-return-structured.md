---
id: 507
title: Refactor mcp-knowledge tools to return structured data
status: archived
priority: medium
created: 2026-03-31 23:40:59.957574+02:00
updated: 2026-04-01 06:08:14.056062+02:00
started: 2026-04-01 06:08:13.559038+02:00
completed: 2026-04-01 06:08:13.559038+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] `search_knowledge` return type: `list[dict[str, Any]] | str`
  - Success: return `[{title: str, score: float, snippet: str}, ...]`
  - Empty results: return `[]`
  - Service unavailable: return error string (unchanged format; error prefix is #506 scope)
- [ ] `list_sources` return type: `list[dict[str, str]]`
  - Success: return `[{name: str, source_type: str, scope: str}, ...]`
  - Empty results: return `[]`
- [ ] `list_entities` return type: `list[dict[str, Any]] | str`
  - Success: return `[{name: str, entity_type: str, description: str}, ...]` (paginated slice per existing offset/limit params; drop the text header line)
  - Empty results: return `[]`
  - Invalid entity_type: return error string (unchanged format)
- [ ] `get_stats` return type: `dict[str, int]`
  - Return `{documents: int, entities: int, edges: int}`
- [ ] Update tests in: `test_search_v2.py` (bullet list assertions to dict assertions), `test_list_sources.py` (bullet list to dict), `test_ingest_graph_tools.py` (list_entities + get_stats string assertions to structured assertions)
- [ ] Type annotations must be precise (avoid `Any` where concrete types are known) so SDK v1.26 auto-generates correct outputSchema
- [ ] Do NOT touch: `tools.py`, `test_search_knowledge.py` (targets tools.py; cleanup is #223), `ingest_document` (stays `str`)

### Scope boundaries
- Error string formatting (`error:` prefix) is #506 scope; this task changes return shapes only
- `knowledge://stats` resource and `knowledge_stats()` helper intentionally stay as `str` (MCP resources serve human-readable content; only tools return structured data)
- Writer gate: update `skills/knowledge-ops/SKILL.md` return format descriptions to match new types

## Context
See docs/research/mcp-server-error-return-standardization.md
Follows pattern already used by mcp-project (`project_info` returns `dict | str`, `project_list` returns `list[dict]`)

[[2026-04-01]] Wed 00:28
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A (T1 autonomous refactor per research doc; no DR required)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| search_knowledge list[dict] or str | Original missing error/empty handling | Refined: explicit empty=[], error=str |
| list_sources list[dict] | Original missing empty handling | Refined: empty=[] |
| list_entities list[dict] or str | Original missing pagination/error handling | Refined: drop header, explicit error=str |
| get_stats dict[str,int] | Clear and verifiable | Kept |
| Update all existing tests | Too broad, would touch wrong files | Refined: 3 specific test files, explicit exclusions |
| Verify outputSchema | Untestable via current FastMCP introspection | Replaced with annotation precision requirement |

### Architecture Notes
Follows established mcp-project pattern (project_info returns dict or str, project_list returns list[dict]). Single domain (mcp-knowledge server), single concern (return types). YAGNI applied: expose only the 3 keys per tool that consumers need, not full model fields. The knowledge://stats resource and knowledge_stats() helper stay as str (MCP resources serve human-readable content). Error string formatting is #506 scope. tools.py is a legacy module (#223).

### Changes Made
- Rewrote full AC body with precise return types, empty/error behavior, test file targets, and scope boundaries
- Added explicit exclusions: tools.py, test_search_knowledge.py, ingest_document
- Added writer gate note for knowledge-ops/SKILL.md update

### Dependencies
- Verified: no depends_on needed. #506 (error prefix) and #507 (return types) are orthogonal axes on the same functions. Boundary documented in AC.
- Verified: #223 (clean up dead tools.py) is separate concern.

### Challenge Results
- Challenger: reconsider (confidence 0.72)
- Key challenges: (C1) knowledge://stats resource not in AC, (C2) knowledge-ops SKILL.md stale, (C3) ordering with #506, (C4) outputSchema untestable, (C5) list_sources error path
- Architect response: C1 accepted (added exclusion note), C2 accepted (added writer gate note), C3 rebutted (orthogonal axes, boundary documented), C4 accepted (replaced with annotation precision AC), C5 rebutted (source_store always created by lifespan)
- Final confidence after refinement: .88

[[2026-04-01]] Wed 02:44
## Test-Writer Notes
- Test files: packages/mcp-knowledge/tests/test_search_v2.py, test_list_sources.py, test_ingest_graph_tools.py
- Classes: TestFromAC_SearchKnowledgeStructuredReturn, TestFromAC_ListSourcesStructuredReturn, TestFromAC_ListEntitiesStructured, TestFromAC_GetStatsStructured
- Tests per category: happy 22, edge 4, boundary 6, error 2
- Total: 34 tests, all FAIL
- ruff: clean
- AC coverage: all 4 tools covered (search_knowledge, list_sources, list_entities, get_stats)

[[2026-04-01]] Wed 04:22
## Review Evidence
See docs/scratch/507-reviewer.md for full evidence.

[[2026-04-01]] Wed 06:08
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| search_knowledge returns list[dict] or str | server.py L98: returns list of dicts with title/score/snippet keys; error string when qs is None | PASS |
| list_sources returns list[dict[str, str]] | server.py L109: returns list of dicts with name/source_type/scope | PASS |
| list_entities returns list[dict] or str | server.py L139-165: returns list of dicts; error string for invalid entity_type | PASS |
| get_stats returns dict[str, int] | server.py L167: returns dict with documents/entities/edges int keys | PASS |
| Update tests in 3 specific files | test_search_v2 (10 structured tests), test_list_sources (10), test_ingest_graph_tools (14 for entities+stats) = 34 new tests | PASS |
| Type annotations precise, avoid Any where concrete | list_sources uses dict[str,str], get_stats uses dict[str,int]; Any only where mixed value types | PASS |
| Do NOT touch tools.py, test_search_knowledge.py, ingest_document | git diff confirms builder commit touched only server.py + 3 test files | PASS |
| Writer gate: SKILL.md updated | knowledge-ops/SKILL.md has structured return docs for all 4 tools (commit e0a668d) | PASS |

### Test Results
- pytest (task scope): 123 passed, 0 failed
- pytest (full suite): 2479 passed, 236 failed (all failures pre-existing, none in mcp-knowledge scope)
- ruff: clean

### Commit Integrity
- Test-writer: 8359971 test: add failing tests for mcp-knowledge structured returns (#507, test-writer)
- Builder: 183aa37 feat: refactor mcp-knowledge tools to return structured data (#507, builder)
- Writer: e0a668d docs: update knowledge-ops SKILL.md return types for structured data (#507, writer)

### AC Quality Score: 5/5
AC was specific (exact return types per tool), complete (empty/error behaviors, test file targets, explicit exclusions), and led to a clean implementation with no improvisation needed.

### Deduction breakdown
- -.02 reviewer evidence file (docs/scratch/507-reviewer.md) referenced but never committed

### Confidence: .98
### Action: archive
