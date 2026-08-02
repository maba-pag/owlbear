---
id: 544
title: 'Test: TypedDict return types for mcp-knowledge outputSchema'
status: archived
priority: medium
created: 2026-04-02 08:08:03.446618+02:00
updated: 2026-04-02 20:30:12.903437+02:00
started: 2026-04-02 20:30:12.487110+02:00
completed: 2026-04-02 20:30:12.487110+02:00
tags:
- scope:mcp
- type:test
- phase-2
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] AC1: search_knowledge fn_metadata.output_schema contains SearchResult  with title(str), score(float), snippet(str)
- [ ] AC2: list_sources fn_metadata.output_schema contains SourceInfo  with name(str), source_type(str), scope(str)
- [ ] AC3: list_entities fn_metadata.output_schema contains EntityInfo  with name(str), entity_type(str), description(str)
- [ ] AC4: get_stats fn_metadata.output_schema has top-level properties documents(int), entities(int), edges(int) -- unwrapped (no result wrapper)
- [ ] AC5: ingest_document fn_metadata.output_schema unchanged (wrapped str)
- [ ] AC6: ingest_document ToolAnnotations includes destructiveHint=False
- [ ] AC7: All TypedDict classes importable from owlbear_mcp_knowledge.server at module scope (not wrapped in TYPE_CHECKING)

## Design Notes

- Tests go in packages/mcp-knowledge/tests/test_outputschema_541.py
- Pattern: access tool objects via mcp._tool_manager, check fn_metadata.output_schema
- See packages/mcp-kanban/tests/test_server.py L1104-L1125 for reference pattern
- list-returning tools produce wrapped {result: ...} schemas with field info in  -- assert  presence
- get_stats produces unwrapped schema (TypedDict Case 2) -- assert top-level properties

[[2026-04-02]] Thu 10:54
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- test task, parent #541 DR is N/A (T1 autonomous)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1 search_knowledge schema | Precise -- named TypedDict, field names+types specified | Keep |
| AC2 list_sources schema | Precise -- named TypedDict, field names+types specified | Keep |
| AC3 list_entities schema | Precise -- named TypedDict, field names+types specified | Keep |
| AC4 get_stats unwrapped | Precise -- top-level properties, unwrapped constraint clear | Keep |
| AC5 ingest_document unchanged | Precise -- negative assertion, verifiable | Keep |
| AC6 destructiveHint | Precise -- single annotation check | Keep |
| AC7 module-scope import | Precise -- covers all TypedDicts. Note: StatsResult not named in AC1-3 but implied by 'All TypedDict classes'. Test-writer should test all 4: SearchResult, SourceInfo, EntityInfo, StatsResult | Keep |

### Architecture Notes
Single test file targeting auto-generated outputSchema from TypedDict return types. Tests will use mcp._tool_manager._tools (not .list_tools()) to access fn_metadata.output_schema -- matches mcp-kanban reference pattern for access mechanism. Schema shapes differ from mcp-kanban (auto-generated vs manual override): list-returning tools produce wrapped schemas with field info in dollar-defs, get_stats produces unwrapped top-level properties. Design notes adequately document this distinction.

Tags correct: type:test + test for pass-through. No deps needed -- impl #541 depends on this (TDD RED ordering).

### Changes Made
- Approved to todo, released claim

### Dependencies
- Verified: #541 (impl) depends on #544 -- correct TDD ordering
- No missing dependencies

### Challenge Results
- Challenger: proceed (confidence 0.82)
- Key challenges: C1 StatsResult not explicitly named in AC7 (cosmetic, mitigated by 'All TypedDict classes'), C2 schema path ambiguity for wrapped schemas (mitigated by design notes and sibling reference)
- Architect response: both accepted as execution-level guidance, not AC defects. Design notes provide sufficient context for test-writer. No AC changes needed.
- Confidence in original after challenge: .85

[[2026-04-02]] Thu 15:30
## Test-Writer Notes
- Non-implementation task (tagged type:test, test) -- no tests applicable.
- Passing through to builder.
- Builder deliverable: packages/mcp-knowledge/tests/test_outputschema_541.py
- AC specifies Python test assertions; builder writes the test file directly.

[[2026-04-02]] Thu 16:20
## Builder Notes
- Files changed: packages/mcp-knowledge/tests/test_outputschema_541.py (created)
- Tests: 21 failed (RED), 1 passed (AC5 guard), ruff clean
- Non-implementation task -- builder wrote test file directly per Test-Writer Notes
- AC1-3: assert dollar-defs in schema and TypedDict name in defs with correct field types
- AC4: assert result schema has inline properties (not anyOf) with documents/entities/edges int fields
- AC5: guard test - asserts result schema type=string, passes in RED and GREEN
- AC6: assert destructiveHint is False on ingest_document annotations
- AC7: assert SearchResult/SourceInfo/EntityInfo/StatsResult importable via hasattr
- Schema structure note: FastMCP wraps all output in result wrapper; tests navigate schema properties result accordingly
- Evidence: 21 failed, 1 passed in 1.33s, ruff clean

[[2026-04-02]] Thu 18:38
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure test task, no behavior/API/convention changes |
| 2 | Docstrings complete | Yes | Pass | test_outputschema_541.py has module docstring, helper docstrings, class docstring, and per-test docstrings -- all accurate |
| 3 | sources/overview.md | No | N/A | Design notes reference internal mcp-kanban pattern, not an external source |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch files found)

[[2026-04-02]] Thu 20:29
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1 search_knowledge SearchResult schema | 4 tests assert $defs.SearchResult with title(str), score(number), snippet(str) -- all fail RED as expected | PASS |
| AC2 list_sources SourceInfo schema | 4 tests assert $defs.SourceInfo with name(str), source_type(str), scope(str) -- all fail RED | PASS |
| AC3 list_entities EntityInfo schema | 4 tests assert $defs.EntityInfo with name(str), entity_type(str), description(str) -- all fail RED | PASS |
| AC4 get_stats unwrapped schema | 4 tests assert inline properties documents/entities/edges(integer) -- all fail RED | PASS |
| AC5 ingest_document unchanged | 1 guard test asserts result schema type=string -- PASSES in RED and GREEN | PASS |
| AC6 destructiveHint=False | 1 test asserts annotations.destructiveHint is False -- fails RED (currently None) | PASS |
| AC7 TypedDicts importable at module scope | 4 tests assert hasattr for SearchResult/SourceInfo/EntityInfo/StatsResult -- all fail RED | PASS |

### Test Results
- pytest (task-scoped): 21 failed, 1 passed -- correct TDD RED outcome (21 fail before impl #541, AC5 guard passes)
- pytest (full suite): 376 failed, 2937 passed -- pre-existing failures from other tasks, no regressions from #544
- ruff: All checks passed

### Architect Quality
- AC specificity: 5/5 -- all 7 AC items named exact TypedDict classes, field names, and types; directly testable
- Edge case coverage: StatsResult coverage implied by AC7 'All TypedDict classes'; architect challenger flagged as cosmetic
- Design direction: Design notes correctly documented FastMCP wrapping, schema navigation paths, and sibling reference pattern; builder followed without deviation

### Quality Gaps
- Builder did not commit deliverable (orphaned, committed by auditor as 77a3aa6)
- No ## Review Evidence section in task body (reviewer passed without appending evidence)

### Deduction breakdown
- -.02 missing reviewer evidence section
### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 77a3aa6 | test | packages/mcp-knowledge/tests/test_outputschema_541.py | #544 |
