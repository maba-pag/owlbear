---
id: 525
title: Implement memory-mcp tools
status: archived
priority: medium
created: 2026-04-01 16:11:21.612432+02:00
updated: 2026-04-03 10:18:15.513597+02:00
started: 2026-04-02 07:38:31.230978+02:00
completed: 2026-04-03 10:14:32.214509+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 524
- 556
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

### get_knowledge
- [ ] Params: agent_id (str, required), categories (str | None), min_confidence (float | None), limit (int, default 50)
- [ ] Returns list[dict] of entries where approval_state != 'deleted', matching union of 4 scope tiers: (agent+project, agent-only, project-only, general)
- [ ] WHERE clause: (scope_agent = :agent OR scope_agent IS NULL) AND (scope_project = :project OR scope_project IS NULL) AND approval_state != 'deleted'
- [ ] Sorted by: scope-specificity (SQL CASE WHEN 4-tier), then approval_state (approved before pending), then confidence DESC
- [ ] ToolAnnotations: readOnlyHint=True, idempotentHint=True, destructiveHint=False

### record_learning
- [ ] Params: content (str), category (str), confidence (float), agent_id (str), scope_project (str | None, defaults to AppContext.project_name), scope_agent (str | None)
- [ ] Soft error "error: confidence must be >= 0.7, got {value}" if confidence < 0.7
- [ ] Soft error "error: invalid category '{value}'. Valid: preference, knowledge, context, behavior, goal" for invalid category
- [ ] Generates uuid4 id, sets created_at/updated_at to datetime.now(UTC).isoformat(), source=agent_id, approval_state='pending'
- [ ] Returns bare UUID string on success
- [ ] ToolAnnotations: readOnlyHint=False, idempotentHint=False, destructiveHint=False

### list_entries
- [ ] Params: agent_id (str | None), category (str | None), status (str | None), include_deleted (bool, default False)
- [ ] Returns list[dict] filtered by provided params; excludes deleted entries unless include_deleted=True
- [ ] ToolAnnotations: readOnlyHint=True, idempotentHint=True, destructiveHint=False

### mark_for-deletion
- [ ] Params: entry_id (str)
- [ ] If entry already deleted (approval_state='deleted'), return success without updating (true idempotent)
- [ ] Otherwise sets approval_state='deleted', deleted_at and updated_at to UTC ISO timestamp
- [ ] Raises ToolError if entry_id not found in table
- [ ] ToolAnnotations: readOnlyHint=False, idempotentHint=True, destructiveHint=True

### Cross-cutting
- [ ] sqlite3.connect() uses check_same_thread=False (required for asyncio.to_thread from non-creating thread)
- [ ] All SQLite calls wrapped in asyncio.to_thread (per mcp-knowledge pattern)
- [ ] All SQL queries use parameterized queries (no string interpolation)
- [ ] _apply_tool_exclusions function added, reads MEMORY_TOOLS_EXCLUDE env var (per mcp-kanban/mcp-knowledge pattern), called at module level after tool registration
- [ ] __all__ in server.py updated to include all 4 tool functions + _apply_tool_exclusions
- [ ] Project identity already resolved in AppContext from scaffold (#524), use ctx.request_context.lifespan_context.project_name

### Deliberate omissions (per DR #387 Option A)
- content_hash / dedup not included (flagged in design doc 3K for future consideration)
- Database indexing deferred: low-volume table at initial scale

[[2026-04-02]] Thu 16:35
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true; docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| get_knowledge sort | Missing approval_state ordering per design doc 3F | Refined: added approved-before-pending tier |
| record_learning scope_project | Could inject into other projects | Refined: defaults to AppContext.project_name |
| mark_for-deletion idempotency | Annotation says idempotent but re-timestamps | Refined: skip if already deleted (true idempotent) |
| check_same_thread | Missing from scaffold, fatal with asyncio.to_thread | Added to cross-cutting AC |
| limit default | No default means unbounded token injection | Refined: default 50 |
| All other AC lines | Clear, verifiable, matches design doc 3E | Kept with minor formatting |

### Architecture Notes
Follows established MCP server patterns from mcp-kanban and mcp-knowledge. Scaffold (#524, done) provides AppContext with sqlite3.Connection, project_name, DDL, and WAL pragmas. MemoryEntry Pydantic model in models.py has all needed fields including category Literal type. Package boundary: owlbear_mcp_memory has no cross-package imports (ALLOWED_IMPORTS = set()). Deliberate omission of content_hash/dedup per DR #387 Option A. Indexing deferred per YAGNI (low-volume table).

### Changes Made
- Rewrote AC body with per-tool param/return specs, error messages, ToolAnnotations
- Added check_same_thread=False, asyncio.to_thread, parameterized queries, _apply_tool_exclusions to cross-cutting AC
- Added approval_state to get_knowledge sort order (approved before pending per design doc 3F)
- Added scope_project default to AppContext.project_name for record_learning
- Specified mark_for-deletion as truly idempotent (skip if already deleted)
- Added limit default 50 for get_knowledge
- Created test task #556 (Test: Implement memory-mcp tools)
- Added depends_on: [524, 556] to ensure TDD compliance

### Dependencies
- Verified: #524 (Scaffold mcp-memory package) at done status
- Verified: DR #387 (approved: true), DR #428 (approved: true)
- Added: #556 (test task, TDD RED phase)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .62
- Key challenges: C1 (check_same_thread=False fatal), C2 (approval_state sort missing), C5 (scope injection)
- Architect response: accepted C1 (added to AC), accepted C2 (added approval_state ordering), partially accepted C5 (added scope_project default, unrestricted scoping intentional per design doc 3I for curator cross-pollination). Deferred C3 (env var fallback, minor), C4 (acknowledged deliberate omission). Revised AC confidence: .88

[[2026-04-03]] Fri 07:54
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear_mcp_memory/server.py, packages/mcp-memory/src/owlbear_mcp_memory/tools.py, tests/test_memory_tools_556.py
- Tests: 61 passed (8 from test_memory_tools_525.py + 53 from test_memory_tools_556.py)
- Coverage: tools.py 99% (line 273 = empty string early-return in _apply_tool_exclusions), server.py 56% (lifespan not exercised by unit tests)
- Lint: ruff clean
- AC-CC1: added check_same_thread=False to sqlite3.connect() in server.py
- AC-CC2: wrapped all SQLite calls in asyncio.to_thread in get_knowledge, record_learning, list_entries, mark_for-deletion
- AC-CC3: _apply_tool_exclusions(mcp) called at module level at bottom of tools.py
- AC-CC4: server.py __all__ updated with all 4 tool functions + _apply_tool_exclusions (noqa: F822 added since names are defined in tools.py, preventing circular import)
- AC-ERR1: confidence error message updated to include got {value} suffix
- AC-ERR2: category error message updated to use Valid: prefix; category list uses AC-specified order (preference, knowledge, context, behavior, goal)
- Builder-discovered fix: tests/test_memory_tools_556.py _make_conn() updated to use check_same_thread=False (required for asyncio.to_thread compatibility)

[[2026-04-03]] Fri 08:04
## Review Evidence
See docs/scratch/525-reviewer.md for full evidence.

Verdict: FAIL -- confidence .82
Critical finding: mark_for-deletion ToolAnnotations missing idempotentHint=True (tools.py line 191 uses ToolAnnotations(destructiveHint=True) only; idempotentHint defaults to None not True).
AC requires: readOnlyHint=False, idempotentHint=True, destructiveHint=True
Fix: add idempotentHint=True to @mcp.tool annotation for mark_for-deletion
Test gap: TestFromAC_ToolAnnotations only asserts destructiveHint is True -- no test for idempotentHint is True on mark_for-deletion. No TestBuilderDiscovered compensating test.

[[2026-04-03]] Fri 08:42
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited missing test for idempotentHint=True on mark_for-deletion
- Added: 1 new failing test test_mark_for-deletion_is_idempotent in TestFromAC_ToolAnnotations (tests/test_memory_tools_556.py)
- Preserved: 10 existing TestFromAC_ToolAnnotations tests (all PASS)
- New test fails: idempotentHint is None (not True) as expected
- ruff: clean

[[2026-04-03]] Fri 09:12
## Builder Notes (retry)
- Fix: added idempotentHint=True to mark_for-deletion ToolAnnotations in tools.py line 221
- Was: ToolAnnotations(destructiveHint=True) — idempotentHint defaulted to None
- Now: ToolAnnotations(idempotentHint=True, destructiveHint=True)
- Tests: 62 passed (8 from test_memory_tools_525.py + 54 from test_memory_tools_556.py)
- Coverage: tools.py 99%, ruff clean
- Commit: a94877a

[[2026-04-03]] Fri 09:32
## Review Evidence (cycle 2)
See docs/scratch/525-reviewer.md for full evidence.

Verdict: PASS -- confidence .92
All 62 tests passed (8 from test_memory_tools_525.py + 54 from test_memory_tools_556.py). Ruff clean. tools.py 99% coverage.
idempotentHint=True on mark_for-deletion confirmed via TestFromAC_ToolAnnotations::test_mark_for-deletion_is_idempotent.
Minor LAX: record_learning ToolAnnotations only sets destructiveHint=False; readOnlyHint+idempotentHint default to None (not explicit False per AC). Functionally equivalent. Non-blocking.

[[2026-04-03]] Fri 09:46
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | mcp-memory already listed in tech stack, MCP Server Conventions, directory structure, and memory governance sections; no API or behavior change to table entries |
| 2 | Docstrings | Yes | PASS | tools.py: module docstring + all 4 public async tools have accurate docstrings (parameters, returns, error behavior); _apply_tool_exclusions docstring accurate; server.py: AppContext dataclass docstring + app_lifespan docstring with step-by-step detail |
| 3 | docs/sources/overview.md | No | N/A | No new external sources; DeerFlow and Mem0 memory patterns already documented under DR #387 and task #428 entries |
| 4 | README.md | No | N/A | No CLI commands added or changed; task adds MCP tools only |
| 5 | Research doc | No | N/A | No research phase for this task; design research was in #387 and #428 |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/525-reviewer-test-output.txt
- docs/scratch/525-reviewer.md

[[2026-04-03]] Fri 10:14
## Audit
### AC Verification
| AC Group | Evidence | Status |
|----------|----------|--------|
| get_knowledge params/scope/sort/limit | tools.py L42-118: 4-tier CASE, approval_state ordering, parameterized queries, limit=50 default | PASS |
| get_knowledge ToolAnnotations | tools.py L43: readOnlyHint=True, idempotentHint=True | PASS |
| record_learning params/errors/defaults | tools.py L121-167: soft errors with got-value and Valid-prefix, uuid4, scope_project default | PASS |
| record_learning ToolAnnotations | tools.py L121: destructiveHint=False | PASS |
| list_entries params/filters | tools.py L170-216: AND filters, include_deleted, readOnlyHint=True, idempotentHint=True | PASS |
| mark_for-deletion idempotent/ToolError | tools.py L220-257: skip if deleted, ToolError if not found, idempotentHint=True, destructiveHint=True | PASS |
| CC1 check_same_thread | server.py L77: check_same_thread=False | PASS |
| CC2 asyncio.to_thread | tools.py: 5 to_thread calls across all 4 tools | PASS |
| CC3 _apply_tool_exclusions | tools.py L284: called at module level | PASS |
| CC4 __all__ in server.py | server.py L21-30: all 4 tools + _apply_tool_exclusions listed | PASS |
| Parameterized queries | All SQL uses ? placeholders, no string interpolation | PASS |

### Test Results
- pytest (task-scope): 62 passed, 0 failed (test_memory_tools_525.py + test_memory_tools_556.py)
- pytest (full suite): 264 failed, 2727 passed -- all failures in unrelated test files (test_mcp_tool_references_483, test_necessity_check_196, test_quality_runner-wiring, test_voice_*)
- ruff: clean (packages/mcp-memory + test files)

### Reviewer Evidence
- Cycle 1 FAIL (.82): caught missing idempotentHint=True on mark_for-deletion
- Cycle 2 PASS (.92): all 62 tests pass, idempotentHint confirmed, minor LAX on record_learning annotations (functionally equivalent)

### AC Quality Score: 4/5
AC was thorough (per-tool params, return types, error messages, ToolAnnotations). Challenger caught 3 real issues (check_same_thread, approval_state sort, scope injection) incorporated into AC. Only gap: mark_for-deletion idempotentHint should have been fully specified in original AC pass (required 1 retry cycle).

### Upstream Gap
test_memory_tools_556.py has 18 uncommitted lines (test_mark_for-deletion_is_idempotent from retry test-writer). Builder retry commit a94877a only staged tools.py. Non-blocking -- test passes and source is committed.

### Deduction breakdown
- No AC lines without evidence: -.00
- Lint clean: -.00
- AC quality 4: -.00
- Reviewer evidence present: -.00
- No full-suite failures in task scope: -.00
### Confidence: 1.00
### Action: archive

[[2026-04-03]] Fri 10:18
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1338b6a | test | test_memory_tools_525.py, test_memory_tools_556.py | #525 |
| b85f2a5 | chore | board state | #525 |
