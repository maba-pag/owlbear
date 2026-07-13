---
id: 506
title: 'Standardize error: prefix across mcp-knowledge and mcp-project'
status: archived
priority: medium
created: 2026-03-31 23:40:53.221387+02:00
updated: 2026-04-01 05:31:05.125234+02:00
started: 2026-04-01 05:31:00.490944+02:00
completed: 2026-04-01 05:31:00.490944+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] mcp-knowledge ingest_document: change 'Ingestion failed: {exc}' to 'error: ingestion failed: {exc}'
- [ ] mcp-knowledge list_entities: prefix 'Invalid entity_type' with 'error: '
- [ ] mcp-knowledge search_knowledge: prefix 'Knowledge service not available.' with 'error: '
- [ ] mcp-project project_info: prefix 'No owlbear-project.json' with 'error: '
- [ ] mcp-project project_readme: prefix 'No README.md' with 'error: '
- [ ] Add __all__ to mcp-knowledge server.py
- [ ] Update existing tests to match new error prefixes

## Context
See docs/research/mcp-server-error-return-standardization.md

## Research
Validated against codebase (2026-03-31). All AC items confirmed.

**Error strings (5 sites):** knowledge/server.py L92,L125,L131; project/server.py L80,L106.
**__all__ gap:** knowledge/server.py has no __all__; kanban + project both do.
**Tests to update (4 files):** knowledge/tests/test_search_knowledge.py, test_search_v2.py, test_ingest_graph_tools.py; project/tests/test_server.py.
**Reference:** mcp-kanban uses `error:` prefix consistently (10 occurrences).
**Tier:** T1 (consistency refactor). No T3 triggers.
Research doc: docs/research/mcp-server-error-return-standardization.md

[[2026-04-01]] Wed 02:43
## Test-Writer Notes
- Test file: tests/test_error_prefix_506.py
- Classes: TestFromAC_ErrorPrefixKnowledge, TestFromAC_ErrorPrefixProject, TestFromAC_KnowledgeServerAll
- Tests per category: happy 0, edge 5, error 10, boundary 0
- Total: 15 tests, all FAIL
- ruff: clean
- AC coverage:
  - AC1 ingest_document error prefix: test_ingest_document_exception_returns_error_prefix, test_ingest_document_error_starts_with_error_ingestion_failed, test_ingest_document_error_has_no_capital_ingestion
  - AC2 list_entities error prefix: test_list_entities_invalid_type_returns_error_prefix
  - AC3 search_knowledge error prefix: test_search_knowledge_no_service_returns_error_prefix, test_search_knowledge_no_service_exact_error_string
  - AC4 project_info error prefix: test_project_info_no_config_returns_error_prefix, test_project_info_no_config_exact_error_string
  - AC5 project_readme error prefix: test_project_readme_no_readme_returns_error_prefix, test_project_readme_no_readme_exact_error_string
  - AC6 dunder all: test_server_has_dunder_all, test_server_all_is_sequence, test_server_all_is_non_empty, test_server_all_includes_mcp_instance, test_server_all_includes_public_tools
  - AC7 update existing tests: builder task (no new tests written)

[[2026-04-01]] Wed 02:43
## Test-Writer Notes
- Test file: tests/test_error_prefix_506.py
- Classes: TestFromAC_ErrorPrefixKnowledge, TestFromAC_ErrorPrefixProject, TestFromAC_KnowledgeServerAll
- Tests per category: happy 0, edge 5, error 10, boundary 0
- Total: 15 tests, all FAIL
- ruff: clean
- AC coverage:
  - AC1 ingest_document error prefix: 3 tests
  - AC2 list_entities error prefix: 1 test
  - AC3 search_knowledge error prefix: 2 tests
  - AC4 project_info error prefix: 2 tests
  - AC5 project_readme error prefix: 2 tests
  - AC6 dunder all: 5 tests
  - AC7 update existing tests: builder task (no new tests written, see Tests to update in research notes)

[[2026-04-01]] Wed 04:40
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | T1 consistency refactor; error strings internal, no API change |
| 2 | Docstrings | Yes | Pass | All public fns documented in mcp-knowledge/server.py and mcp-project/server.py |
| 3 | docs/sources/overview.md | No | N/A | No external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Pass | docs/research/mcp-server-error-return-standardization.md exists and linked |

### Files Updated
- None

### Scratch Files Cleaned
- None
