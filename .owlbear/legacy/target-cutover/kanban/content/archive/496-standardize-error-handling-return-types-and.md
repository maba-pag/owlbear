---
id: 496
title: Standardize error handling, return types, and exports across MCP servers
status: archived
priority: medium
created: 2026-03-31 06:52:31.074813+02:00
updated: 2026-04-02 17:30:08.384077+02:00
started: 2026-04-02 17:30:07.973611+02:00
completed: 2026-04-02 17:30:07.973611+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective\n\nEstablish consistent patterns across all three MCP servers (kanban, knowledge, project).\n\n## Acceptance Criteria\n\n### Error handling\n- [ ] All tool errors return strings with `error: ` prefix (kanban already does this)\n- [ ] mcp-knowledge ingest_document: change `Ingestion failed: {exc}` to `error: ingestion failed: {exc}`\n- [ ] mcp-project: add error returns where appropriate (e.g., file read failures)\n\n### Return types\n- [ ] Move toward structured returns (dict/list) for data, `str` for messages/errors\n- [ ] mcp-knowledge: search results, entity lists, source lists return structured data (not formatted bullet strings)\n- [ ] Verify mcp-project already uses structured returns (it does) — no change needed\n\n### Module exports\n- [ ] Add `__all__` to mcp-knowledge server.py listing all public symbols\n\n### Documentation\n- [ ] Add a brief `MCP server conventions` section to copilot-instructions.md or a new instructions/mcp-servers.instructions.md covering: error prefix convention, annotation requirements, return type guideline, lifespan pattern\n\n## Design Notes\n\n- Error prefix `error: ` is a simple string convention that callers can detect with startswith()\n- Structured returns enable outputSchema (already tasked in #492)\n- This is a consistency pass, not a redesign — each change is small

[[2026-04-02]] Thu 12:32
## Test-Writer Notes
- Test file: tests/test_mcp_server_conventions_496.py
- Classes: TestFromAC_ProjectReadmeErrorHandling, TestFromAC_ProjectStructureErrorHandling, TestFromAC_KnowledgeServerExports
- Tests per category: happy 0, edge 2, error 6, boundary 1
- Total: 9 tests, 6 FAIL, 3 pass (regression guards + integrity check)
- ruff: clean
- AC coverage:
  - mcp-project project_readme OSError: test_read_text_oserror_returns_string_not_raises, test_read_text_oserror_returns_error_prefix, test_permission_error_is_caught_and_returns_error_prefix (3 FAIL)
  - mcp-project project_structure OSError: test_build_tree_exception_returns_string_not_raises, test_build_tree_exception_returns_error_prefix (2 FAIL)
  - mcp-knowledge __all__ completeness: test_init_db_exported (1 FAIL)
  - regression guards: test_successful_read_still_returns_content, test_successful_traversal_still_returns_tree (2 PASS - intentional)
  - integrity guard: test_all_symbols_actually_exist_on_module (1 PASS - guards against bad __all__ entries)
- Notes: ingest_document error prefix and structured returns for search/list/entities already implemented; no failing tests were possible for those items. Documentation AC item already present in copilot-instructions.md.

[[2026-04-02]] Thu 15:26
## Builder Notes\n- Files changed: packages/mcp-project/src/owlbear_mcp_project/server.py, packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py\n- Tests: 9 passed (was 6 FAIL, 3 PASS)\n- Lint: ruff clean\n- Evidence: 9 passed in 1.81s; commit 81b5bdd, 2 files changed\n- Changes: (1) project_readme: try/except OSError around read_text(); (2) project_structure: try/except around build_tree(); (3) mcp-knowledge __all__: added init_db

[[2026-04-02]] Thu 16:15
## Review Evidence
See docs/scratch/496-reviewer.md for full evidence.

[[2026-04-02]] Thu 16:33
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | Yes | N/A (pre-satisfied) | MCP Server Conventions section at line 67 covers all 6 conventions: error prefix, ToolError vs string prefix, tool annotations, return types, lifespan pattern, module exports. Pre-existing and accurate — no update needed. |
| 2 | Docstrings | Yes | PASS | mcp-project server.py: all public functions have docstrings; project_readme ('Return README.md content from project root, or a fallback string if absent.') and project_structure ('Return an indented directory tree (max depth 3) of the project root.') are accurate. mcp-knowledge server.py: init_db ('Open the SQLite database at *path*, apply schema, return connection.') and all public tools have docstrings. |
| 3 | sources/overview.md | Yes | PASS | Entry 'MCP Server Error/Return Standardization (Task #496)' already present at lines 13-18 with MCP Spec and Python SDK sources. No new external patterns introduced by the builder's +9-line diff. |
| 4 | README.md | No | N/A | No CLI commands added or modified — server-side convention pass only. |
| 5 | Research doc | Yes | PASS | docs/research/mcp-server-error-return-standardization.md exists, links owning task in header, linked from sources/overview.md. |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/496-reviewer.md: already absent (clean)

[[2026-04-02]] Thu 17:30
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All tool errors return error: prefix | Grep mcp-knowledge server.py: 7 error: prefixed returns (L128,139,154,158,178,185,203) | PASS |
| ingest_document error: prefix | L158: `error: ingestion failed: {exc}` | PASS |
| mcp-project error returns | project_readme L185: try/except OSError; project_structure L200: except Exception | PASS |
| Structured returns (dict/list) for data | search_knowledge returns list[dict] (L130); list_sources returns list[dict] (L141) | PASS |
| mcp-knowledge structured data | Same as above (search, entity lists, source lists) | PASS |
| mcp-project structured returns (verify) | ProjectInfoResult TypedDict, project_list returns list[ProjectListItem] | PASS |
| __all__ in mcp-knowledge | L105-116: __all__ includes init_db and 10 other symbols | PASS |
| MCP conventions docs | Pre-existing in copilot-instructions.md (docs gate confirmed) | PASS |

### Test Results
- pytest: 9/9 task-specific pass; full suite 2896 pass / 274 fail (all failures from task 541 outputschema tests, outside scope)
- ruff: clean (mcp-project, mcp-knowledge, test file)

### Upstream Commits
- f1d6100 test: add failing tests for MCP server conventions (496, test-writer)
- 81b5bdd feat: standardize error handling and exports across MCP servers (496, builder)

### AC Quality: 4/5
AC was specific and checklist-style. Minor note: some items were already implemented pre-task (ingest_document prefix, structured returns), making them verify-only. Harmless but slightly unfocused.

### Deduction breakdown: none (all AC verified, lint clean, tests pass, AC quality 4)
### Confidence: 1.0
### Action: archive
