---
id: 541
title: Add TypedDict return types for outputSchema specificity on mcp-knowledge
status: archived
priority: medium
created: 2026-04-02 06:16:15.547930+02:00
updated: 2026-04-03 04:34:33.230259+02:00
started: 2026-04-03 04:33:01.763170+02:00
completed: 2026-04-03 04:33:01.763170+02:00
tags:
- scope:mcp
- type:build
- phase-2
depends_on:
- 544
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Replace generic dict return types with TypedDict on mcp-knowledge tools so FastMCP auto-generates field-level outputSchema (matching mcp-kanban pattern).

## Context

Annotations complete (done by #501). Auto-generated outputSchema exists but is generic. Tools return dicts with known fixed fields but outputSchema only says 'array of objects'. See docs/research/knowledge-project-outputschema-annotations.md (v2).

## Acceptance Criteria

- [ ] AC1: Define SearchResult TypedDict with title(str), score(float), snippet(str) at module scope in server.py
- [ ] AC2: Define SourceInfo TypedDict with name(str), source_type(str), scope(str) at module scope in server.py
- [ ] AC3: Define EntityInfo TypedDict with name(str), entity_type(str), description(str) at module scope in server.py
- [ ] AC4: Define StatsResult TypedDict with documents(int), entities(int), edges(int) at module scope in server.py
- [ ] AC5: search_knowledge return type changed to list[SearchResult] | str -- fn_metadata.output_schema includes SearchResult field defs
- [ ] AC6: list_sources return type changed to list[SourceInfo] -- fn_metadata.output_schema includes SourceInfo field defs
- [ ] AC7: list_entities return type changed to list[EntityInfo] | str -- fn_metadata.output_schema includes EntityInfo field defs
- [ ] AC8: get_stats return type changed to StatsResult -- fn_metadata.output_schema has top-level properties (unwrapped)
- [ ] AC9: ingest_document return type unchanged (str) -- no change needed
- [ ] AC10: ingest_document ToolAnnotations updated to include destructiveHint=False
- [ ] AC11: All TypedDicts defined at module scope (NOT under if TYPE_CHECKING) -- required for from __future__ import annotations resolution
- [ ] AC12: All outputSchemas verified at runtime via fn_metadata.output_schema (test task #544)

## Design Notes

- TypedDicts MUST be at module scope in server.py. `from __future__ import annotations` makes annotations lazy; FastMCP resolves them via inspect.signature(func, eval_str=True) at registration time. If TypedDict is not in module __globals__, NameError at startup.
- list[TypedDict] and list[TypedDict] | str return types produce WRAPPED schemas ({result: anyOf[...]}) with field definitions in $defs. This is expected FastMCP behavior (GenericAlias path in func_metadata._try_create_model_and_schema). The $defs contain full field-level info which is strictly better than current "array of objects".
- Direct TypedDict return (get_stats) produces UNWRAPPED schema with top-level properties. This is the cleanest case (Case 2 path in func_metadata).
- TypedDict annotations add Pydantic output validation. Since tools already construct dicts from typed source attributes (r.title, r.score, etc.), validation catches implementation bugs only. This is intentional and desirable.
- Pattern: FastMCP auto-generates precise outputSchema from TypedDict (confirmed in #477 research). No manual fn_metadata.output_schema hack needed.
- Do NOT add TypedDicts to __all__ -- they are internal to the server module.

## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A -- T1 autonomous (type refinement, no new capabilities)

### AC Assessment

- AC1-4 TypedDict definitions: Precise -- names, fields, types specified. Kept.
- AC5 search_knowledge: list[SearchResult] or str -- wrapped schema with $defs. Refined from original.
- AC6 list_sources: list[SourceInfo] -- wrapped schema with $defs. Refined from original.
- AC7 list_entities: list[EntityInfo] or str -- wrapped schema with $defs. Refined from original.
- AC8 get_stats: StatsResult -- unwrapped top-level properties. Tightened from "verify or add".
- AC9 ingest_document: No change (str). Kept.
- AC10 destructiveHint: Single-line annotation change, same file. Kept.
- AC11 Module scope constraint: New -- prevents NameError under from __future__ import annotations. Added per challenger C4.
- AC12 Runtime verification: Delegated to test task #544. Kept.

### Architecture Notes

Single module change (server.py). TypedDicts at module scope follow SDK design (Case 2 in func_metadata for direct returns, GenericAlias wrapping for list returns). Wrapping for list-returning tools is expected -- $defs field info is strictly better than current generic "array of objects". Pydantic output validation tightening is intentional. No cross-package imports. No __all__ changes needed.

Challenger raised valid point about union wrapping (C1). Addressed: wrapping behavior documented in design notes, $defs still provide field-level info. Manual fn_metadata.output_schema override (mcp-kanban pattern) would avoid wrapping but adds maintenance burden for marginal schema quality difference.

### Changes Made

- Refined AC: 7 lines expanded to 12 precise, testable lines
- Added design notes: wrapping behavior, module-scope requirement, validation intent
- Created test task #544 (TDD RED) with matching AC
- Added dependency: #541 depends_on #544

### Dependencies

- Added: #541 depends on #544 (test task, TDD RED)
- Verified: #501 (annotations) archived, no open blockers

### Challenge Results

- Challenger: reconsider (confidence 0.62)
- Key challenges: C1 (union wrapping for list returns), C4 (module-scope under from __future__), C5 (Pydantic validation tightening)
- Architect response: C1 accepted and documented in design notes ($defs still better than generic), C4 accepted and encoded as AC11, C5 rebutted (validation is intentional benefit). Verdict stands.
- Confidence in original after challenge: .82

[[2026-04-02]] Thu 22:46
## Test-Writer Notes\n- Test file: tests/test_mcp_knowledge_typeddict_541.py\n- Classes: TestFromAC_TypedDictFieldAnnotations, TestFromAC_FunctionReturnAnnotations\n- Tests per category: happy 17, edge 1, error 0, boundary 3\n- Total: 21 tests, 20 FAIL + 1 PASS (AC9 guard) \u2713\n- ruff: clean\n- Notes: AC12 delegated to #544 (archived). tests/test_outputschema_541.py covers schema shapes. This file adds TypedDict Python type contract tests.\n- AC coverage:\n  AC1 SearchResult: test_search_result_is_typeddict, test_search_result_title_is_str, test_search_result_score_is_float, test_search_result_snippet_is_str, test_search_result_has_exactly_three_fields\n  AC2 SourceInfo: test_source_info_is_typeddict, test_source_info_name_is_str, test_source_info_source_type_is_str, test_source_info_scope_is_str\n  AC3 EntityInfo: test_entity_info_is_typeddict, test_entity_info_name_is_str, test_entity_info_entity_type_is_str, test_entity_info_description_is_str\n  AC4 StatsResult: test_stats_result_is_typeddict, test_stats_result_documents_is_int, test_stats_result_entities_is_int, test_stats_result_edges_is_int\n  AC5 search_knowledge annotation: test_search_knowledge_return_annotation_references_search_result\n  AC6 list_sources annotation: test_list_sources_return_annotation_references_source_info\n  AC7 list_entities annotation: test_list_entities_return_annotation_references_entity_info\n  AC8 get_stats annotation: test_get_stats_return_annotation_references_stats_result\n  AC9 ingest_document guard: test_ingest_document_return_annotation_is_str_unchanged (PASS in RED)\n  AC11: all TypedDict existence tests verify module-scope accessibility\n  AC12: delegated to packages/mcp-knowledge/tests/test_outputschema_541.py (#544)

[[2026-04-03]] Fri 00:19
## Builder Notes\n- Files changed: packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py\n- Tests: 22 passed, coverage 41% on server.py (annotation-only tests; tool bodies require full lifespan context)\n- Lint: ruff clean\n- Evidence: 20 FAIL -> 22 pass after adding TypedDicts and updating annotations\n- Fixes applied: Added TypedDict import; defined SearchResult/SourceInfo/EntityInfo/StatsResult at module scope; updated search_knowledge/list_sources/list_entities/get_stats return annotations; added destructiveHint=False to ingest_document ToolAnnotations

[[2026-04-03]] Fri 01:44
## Review Evidence
See docs/scratch/541-reviewer.md for full evidence.

[[2026-04-03]] Fri 01:44
## Review Evidence
See docs/scratch/541-reviewer.md for full evidence.

[[2026-04-03]] Fri 01:44
## Review Evidence
See docs/scratch/541-reviewer.md for full evidence.

[[2026-04-03]] Fri 02:17
## Test-Writer Notes (retry)\n- Retry reason: reviewer cited (1) AC10 MISSING and (2) list_sources/get_stats return str on error paths instead of raising ToolError\n- Added: 3 new tests (TestFromAC_ToolAnnotations x1, TestFromAC_ErrorPathConventions x2)\n- Preserved: 22 existing tests (all PASS)\n- AC10 test (test_ingest_document_destructive_hint_is_false): PASS -- builder already implemented destructiveHint=False\n- Error-path tests: FAIL -- DID NOT RAISE ToolError (functions still return str literals)\n- ruff: clean

[[2026-04-03]] Fri 03:18
## Builder Notes (retry)\n- Files changed: packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py\n- Change: added ToolError import; changed list_sources/get_stats None-store paths from return str to raise ToolError(msg)\n- Tests: 25 passed (23 existing + 2 new error-path tests now GREEN)\n- Coverage: 47% on server.py (annotation-only tests; tool bodies require full lifespan context)\n- Lint: ruff clean\n- Evidence: 2 FAIL -> 25 pass after fix

-t

[[2026-04-03]] Fri 04:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | MCP Return types bullet changed from dict to TypedDict; ToolError/error-prefix bullets updated to reference TypedDict |
| 2 | Docstrings | Yes | Pass | All 4 TypedDicts (SearchResult, SourceInfo, EntityInfo, StatsResult) and 5 tool functions have accurate docstrings in server.py |
| 3 | docs/sources/overview.md | No | N/A | Patterns already documented under Task #492 section (FastMCP TypedDict outputSchema, MCP SDK) |
| 4 | README.md | No | N/A | No CLI changes -- internal type annotation change only |
| 5 | Research doc | Yes | Pass | docs/research/knowledge-project-outputschema-annotations.md exists and referenced in task body |

### Files Updated
- .github/copilot-instructions.md

### Scratch Files Cleaned
- 541-architect-fix.tmp, 541-architect.tmp, 541-audit.tmp, 541-contract-err.txt, 541-contract.txt, 541-cov.txt, 541-final.txt, 541-out.txt, 541-reviewer.md, 541-reviewer.tmp, 541-t-err.txt, 541-t-out.txt (12 files deleted)

[[2026-04-03]] Fri 04:32
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1 SearchResult TypedDict | server.py L36-40: TypedDict with title(str), score(float), snippet(str) | PASS |
| AC2 SourceInfo TypedDict | server.py L43-48: TypedDict with name(str), source_type(str), scope(str) | PASS |
| AC3 EntityInfo TypedDict | server.py L51-56: TypedDict with name(str), entity_type(str), description(str) | PASS |
| AC4 StatsResult TypedDict | server.py L59-64: TypedDict with documents(int), entities(int), edges(int) | PASS |
| AC5 search_knowledge return | server.py L155: list[SearchResult] | str | PASS |
| AC6 list_sources return | server.py L163: list[SourceInfo] | PASS |
| AC7 list_entities return | server.py L197: list[EntityInfo] | str | PASS |
| AC8 get_stats return | server.py L225: StatsResult | PASS |
| AC9 ingest_document unchanged | server.py L182: str return type unchanged | PASS |
| AC10 destructiveHint | server.py L178: destructiveHint=False in ToolAnnotations | PASS |
| AC11 module scope | All TypedDicts at lines 36-64, outside TYPE_CHECKING block | PASS |
| AC12 runtime schema | Delegated to #544 (archived, verified) | PASS |

### Test Results
- pytest: 25/25 pass (test_mcp_knowledge_typeddict_541.py), full suite 260 fail / 2679 pass (0 failures in task scope)
- ruff: clean

### Deduction breakdown
- No deductions applied. All AC items verified with code evidence, lint clean, tests pass, AC quality adequate.

### AC Quality: 4/5
AC was specific and testable. Minor gap: error-path convention (ToolError vs str) not covered by original AC, caught by reviewer retry.

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 04:34
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2724915 | chore | kanban/tasks/541-*, activity.jsonl | #541 |
