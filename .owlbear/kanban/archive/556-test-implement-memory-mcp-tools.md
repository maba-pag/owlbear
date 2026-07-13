---
id: 556
title: 'Test: Implement memory-mcp tools'
status: archived
priority: medium
created: 2026-04-02 16:34:22.295344+02:00
updated: 2026-04-03 01:06:37.026621+02:00
started: 2026-04-03 01:05:38.640059+02:00
completed: 2026-04-03 01:05:38.640059+02:00
tags:
- scope:agents
- phase-2
- test
depends_on:
- 524
class: standard
archival_reason: completed
archival_refs: []
---

Write failing tests for #525 memory-mcp tool implementations. Tests cover all 4 tools: get_knowledge, record_learning, list_entries, mark_for_deletion.

AC:
- [ ] Test get_knowledge returns entries sorted by scope-specificity, approval_state (approved before pending), then confidence DESC
- [ ] Test get_knowledge respects 4-tier scope union (agent+project, agent-only, project-only, general)
- [ ] Test get_knowledge excludes deleted entries
- [ ] Test get_knowledge limit param defaults to 50
- [ ] Test get_knowledge filters by categories and min_confidence when provided
- [ ] Test record_learning rejects confidence < 0.7 with soft error string
- [ ] Test record_learning rejects invalid category with soft error string
- [ ] Test record_learning generates UUID, sets timestamps, source=agent_id, approval_state=pending
- [ ] Test record_learning defaults scope_project to AppContext.project_name when None
- [ ] Test record_learning returns bare UUID string on success
- [ ] Test list_entries filters by agent_id, category, status
- [ ] Test list_entries excludes deleted unless include_deleted=True
- [ ] Test mark_for_deletion sets approval_state=deleted and deleted_at+updated_at
- [ ] Test mark_for_deletion is idempotent (no-op if already deleted)
- [ ] Test mark_for_deletion raises ToolError for nonexistent entry_id
- [ ] Test _apply_tool_exclusions reads MEMORY_TOOLS_EXCLUDE and removes tools
- [ ] Test ToolAnnotations correct for each tool (readOnly, idempotent, destructive hints)
- [ ] All tests use in-memory SQLite (no disk files)

[[2026-04-02]] Thu 18:03
## Test-Writer Notes
- Test file: tests/test_memory_tools_556.py
- Classes: TestFromAC_GetKnowledge, TestFromAC_RecordLearning, TestFromAC_ListEntries, TestFromAC_MarkForDeletion, TestFromAC_ApplyToolExclusions, TestFromAC_ToolAnnotations
- Tests per category: happy 28, edge 9, error 8, boundary 5
- Total: 50 tests, all FAIL (ImportError -- owlbear_mcp_memory.tools not yet created)
- ruff: clean
- AC coverage:
  AC1  -- sort by scope+approval+confidence -- tier1_precedes_tier4, approved_before_pending, higher_confidence_first
  AC2  -- 4-tier scope union -- all_four_tiers_returned, entries_outside_scope_excluded
  AC3  -- excludes deleted -- excludes_deleted_entries
  AC4  -- limit defaults 50 -- limit_defaults_to_50, limit_default_returns_exactly_50, explicit_limit_caps
  AC5  -- category/min_confidence filters -- filter_by_single/multiple_category, filter_by_min_confidence
  AC6  -- confidence less than 0.7 -- rejects_confidence_below_0_7, rejects_zero, confidence_exactly_0_7_accepted
  AC7  -- invalid category -- rejects_invalid_category, accepts_all_five_valid_categories
  AC8  -- UUID+timestamps+source+state -- returned_uuid_matches_stored, sets_created_and_updated_at, sets_source, sets_approval_state
  AC9  -- scope_project default -- defaults_scope_project_from_app_context, explicit_scope_project_overrides
  AC10 -- returns bare UUID -- returns_bare_uuid_string_on_success
  AC11 -- list_entries filters -- filter_by_agent_id, filter_by_category, filter_by_status_approved, combined_filters
  AC12 -- excludes deleted -- excludes_deleted_entries_by_default, includes_deleted_when_flag_set, no_filters_returns_all_non_deleted
  AC13 -- sets deleted state -- sets_approval_state_to_deleted, sets_deleted_at_timestamp, updates_updated_at_timestamp
  AC14 -- idempotent -- is_idempotent_when_already_deleted
  AC15 -- ToolError nonexistent -- raises_tool_error_for_nonexistent_entry_id
  AC16 -- MEMORY_TOOLS_EXCLUDE -- reads_env_var, multiple_tools, no_op_absent/empty, ignores_unknown, whitespace_stripped, mixed_valid_invalid
  AC17 -- ToolAnnotations -- all 4 tools have annotations; correct readOnly/idempotent/destructive hints per tool
  AC18 -- in-memory SQLite -- all tests use _make_conn() with sqlite3.connect(':memory:')
- Import target: owlbear_mcp_memory.tools (does not exist yet -- builder must create it)

[[2026-04-02]] Thu 18:49
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear_mcp_memory/tools.py (new, 256 lines)
- Tests: 53 passed, coverage 99% on tools.py
- Lint: ruff clean
- Evidence: 53 passed in 0.81s; ruff All checks passed
- Fixes applied: matched mcp-kanban pattern for _apply_tool_exclusions; noqa:S608 on closing triple-quote line

[[2026-04-02]] Thu 22:35
## Review Evidence
See docs/scratch/556-reviewer.md for full evidence.

[[2026-04-03]] Fri 00:03
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Test task (tag:test); mcp-memory already documented in tech stack + directory structure tables; no new behavior/API exposed |
| 2 | Docstrings | Yes | Pass | tools.py has module docstring + complete per-function docstrings on all 5 exports; all accurate |
| 3 | docs/sources/overview.md | No | N/A | Only internal pattern reuse (mcp-kanban _apply_tool_exclusions); no external sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Test task, no research phase |

### Files Updated
- None

### Scratch Files Cleaned
- Deleted docs/scratch/556-reviewer.md

[[2026-04-03]] Fri 01:05
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1 sort order | tests tier1_precedes_tier4, approved_before_pending, higher_confidence_first; SQL ORDER BY (tier_case), approval_state, confidence DESC | PASS |
| AC2 4-tier scope | tests all_four_tiers_returned, entries_outside_scope_excluded; CASE expression covers tiers 1-4 | PASS |
| AC3 excludes deleted | test excludes_deleted_entries; WHERE approval_state != 'deleted' | PASS |
| AC4 limit default 50 | tests limit_defaults_to_50, exactly_50, explicit_limit_caps; LIMIT ? with default=50 | PASS |
| AC5 category/confidence | tests single/multiple_category, min_confidence; IN (?) and >= ? clauses | PASS |
| AC6 confidence < 0.7 | tests rejects_below_0_7, rejects_zero, exactly_0_7_accepted; if confidence < _MIN_CONFIDENCE returns error: | PASS |
| AC7 invalid category | tests rejects_invalid, accepts_all_five; _VALID_CATEGORIES frozenset check | PASS |
| AC8 UUID+timestamps | tests uuid_matches_stored, created_at, updated_at, source, approval_state; INSERT with uuid4, _now_utc | PASS |
| AC9 scope_project default | tests defaults_from_app_context, explicit_overrides; if None uses app_ctx.project_name | PASS |
| AC10 bare UUID | test returns_bare_uuid_string_on_success; return entry_id (str uuid) | PASS |
| AC11 list_entries filters | tests agent_id, category, status_approved, combined_filters; AND conditions in WHERE | PASS |
| AC12 deleted exclusion | tests excludes_default, includes_when_flag, no_filters_all_non_deleted; include_deleted param | PASS |
| AC13 deleted state | tests approval_state_to_deleted, deleted_at_timestamp, updates_updated_at; UPDATE SET | PASS |
| AC14 idempotent | test is_idempotent_when_already_deleted; if row[0] == 'deleted' returns no-op | PASS |
| AC15 ToolError | test raises_tool_error_for_nonexistent; row is None check | PASS |
| AC16 tool exclusions | 7 tests covering env var, multiple, absent, empty, unknown, whitespace, mixed | PASS |
| AC17 ToolAnnotations | parametrized + individual hint checks for all 4 tools | PASS |
| AC18 in-memory SQLite | all tests use _make_conn() with :memory: | PASS |

### Test Results
- pytest (scoped): 53 passed in 0.93s
- pytest (full suite): 3111 passed, 237 failed (all failures unrelated to #556)
- ruff: All checks passed

### AC Quality Score: 5/5
AC was specific (18 testable items), complete (edge cases included), and led to a clean implementation with no builder improvisation needed.

### Deduction breakdown
- -.02 reviewer evidence section references deleted scratch file (thin evidence trail)

### Confidence: 0.98
### Action: archive

[[2026-04-03]] Fri 01:06
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| d813d56 | chore | kanban/tasks/556-*.md | #556 |
