---
id: 542
title: Add TypedDict return types for outputSchema specificity on mcp-project
status: todo
priority: important
created: 2026-04-02T06:16:23.9009603+02:00
updated: 2026-04-02T07:55:45.7340378+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 543
class: standard
---

## Objective

Replace generic dict return types with TypedDict on mcp-project tools so FastMCP auto-generates field-level outputSchema (matching mcp-kanban pattern).

## Context

Annotations complete (done by #502). Auto-generated outputSchema exists but is generic. Tools return dicts with known fixed fields but outputSchema only says 'object with any properties'. See docs/research/mcp-project-typeddict-outputschema.md.

## Acceptance Criteria

- [ ] `ProjectInfoResult(TypedDict)` defined at module scope (after imports, before tool functions) in `server.py` with fields: name(str), type(str), project_path(str), owlbear_path(str), created_at(str)
- [ ] `ProjectListItem(TypedDict)` defined at module scope (after imports, before tool functions) in `server.py` with fields: name(str), path(str)
- [ ] `project_info` return annotation is `ProjectInfoResult` (no `| str` union)
- [ ] `project_info` error path: `raise ToolError(msg)` when config is absent (replaces `return "error: ..."`, follows mcp-kanban show_task pattern)
- [ ] `project_list` return annotation is `list[ProjectListItem]`
- [ ] `project_readme` and `project_structure` unchanged (return str)
- [ ] TypedDicts NOT under `if TYPE_CHECKING:` -- FastMCP resolves via `inspect.signature(eval_str=True)` at registration time
- [ ] `__all__` in `server.py` includes `ProjectInfoResult` and `ProjectListItem`
- [ ] Existing error-path tests updated: `packages/mcp-project/tests/test_server.py` (test_returns_string_when_project_file_is_none, test_error_string_is_non_empty_and_descriptive) and `tests/test_error_prefix_506.py` (test_project_info_no_config_returns_error_prefix, test_project_info_no_config_exact_error_string) changed from string-return assertions to ToolError expectations
- [ ] Schema-pinning: `fn_metadata.output_schema` for project_info has top-level `properties` with all 5 field names, each `type: string`
- [ ] Schema-pinning: `fn_metadata.output_schema` for project_list items schema contains `name` and `path` properties (inside FastMCP `result` wrapper)

## Design Notes

- FastMCP auto-generates precise outputSchema from TypedDict (confirmed in research)
- Only 2 tools need TypedDict (project_info, project_list); other 2 return str
- TypedDict for pre-validated/constructed data (mcp-project); BaseModel for external process output (mcp-kanban) -- intentional convention difference
- `project_readme` retains `return "error: ..."` -- returns `str` type regardless, no schema conflict
- Removing `| str` union from project_info is essential -- union defeats schema precision (research sec. 3c)

## Files

- Target: `packages/mcp-project/src/owlbear_mcp_project/server.py`
- Test update: `packages/mcp-project/tests/test_server.py` (2 methods in TestFromAC_ProjectInfoTool)
- Test update: `tests/test_error_prefix_506.py` (2 methods for project_info error path)

[[2026-04-02]] Thu 07:55
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- T1 classification (type annotation refinement), no new capabilities or architecture changes

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ProjectInfoResult TypedDict | Clear: 5 named fields, module scope placement | Kept |
| ProjectListItem TypedDict | Clear: 2 named fields, module scope placement | Kept |
| project_info return is ProjectInfoResult (no union) | ADDED: research sec 3c says union defeats precision | Refined |
| project_info ToolError on missing config | ADDED: essential for removing str union | Added from research |
| project_list return list[ProjectListItem] | Clear and verifiable | Kept |
| project_readme/structure unchanged | Scope boundary, explicit | Kept |
| TypedDicts not under TYPE_CHECKING | Critical constraint from research | Kept |
| __all__ updated | ADDED per challenger: new module-scope symbols | Added |
| Existing tests updated | ADDED per challenger: 4 tests across 2 files assert string-return error path | Added |
| Schema-pinning project_info | Clarified: top-level properties (direct TypedDict return) | Refined |
| Schema-pinning project_list | Clarified: items inside result wrapper (list return) | Refined |

### Architecture Notes
Single-domain task (mcp-project only). TypedDict is the correct choice for pre-validated data -- lighter than BaseModel, no double-validation. Convention: TypedDict for constructed data (mcp-project), BaseModel for external process output (mcp-kanban).

ToolError migration for project_info is necessary to eliminate the str union that defeats outputSchema precision. project_readme retains string error return since it already returns str type.

Key constraint: `from __future__ import annotations` makes all annotations lazy. TypedDicts must be at module scope and defined before first use so FastMCP can resolve them via `inspect.signature(eval_str=True)`.

### Changes Made
- Refined AC: added 4 new lines (ToolError, no-union, __all__, existing test updates)
- Clarified schema-pinning AC with nesting expectations
- Created test task #543 (TDD RED phase)
- Added depends_on: #542 depends on #543

### Dependencies
- Added: #543 (test task, TDD RED phase)
- Verified: #502 (annotations) completed
- No other dependencies needed

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: (1) existing tests assert string-return error path, (2) return type union removal not explicit, (3) schema nesting expectations vague, (4) __all__ not addressed, (5) TypedDict placement in server.py vs models.py
- Architect response: ACCEPTED challenges 1-4 and refined AC accordingly. REBUTTED challenge 5 (TypedDicts are 2-5 field lightweight annotations closer to function signatures than full models; models.py serves a different purpose of validating external JSON). Post-refinement confidence: .88
