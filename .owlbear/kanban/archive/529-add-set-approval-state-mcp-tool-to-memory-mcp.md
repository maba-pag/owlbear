---
id: 529
title: Add set_approval_state MCP tool to memory-mcp
status: archived
priority: medium
created: 2026-04-01 19:12:57.825057+02:00
updated: 2026-04-03 17:40:33.976986+02:00
started: 2026-04-03 17:39:42.472444+02:00
completed: 2026-04-03 17:39:42.472444+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 525
- 569
class: standard
archival_reason: completed
archival_refs: []
---

Add a 5th MCP tool to memory-mcp for approval state transitions. Per docs/research/set-approval-state-mcp-tool.md and docs/research/curator-workflow-memory-mcp.md sec 3B. Depends on #525.

## Acceptance Criteria

### set_approval_state
- [ ] Params: entry_id (str, required), new-state (Literal["approved", "deleted", "pending"])
- [ ] Shared constant _VALID_TRANSITIONS: frozenset of (from, to) tuples: {("pending","approved"), ("pending","deleted"), ("deleted","pending")}
- [ ] Soft error "error: transition from '{current}' to '{new-state}' is not allowed" for invalid transition (including same-state)
- [ ] Raises ToolError if entry_id not found in table (consistent with mark_for-deletion)
- [ ] When transitioning to 'deleted': set deleted_at to UTC ISO timestamp
- [ ] When transitioning from 'deleted' to 'pending': clear deleted_at to NULL
- [ ] Always set updated_at to UTC ISO timestamp on successful transition
- [ ] Returns str confirmation message on success (e.g., "Entry '{entry_id}' state changed from '{old}' to '{new}'")
- [ ] ToolAnnotations: readOnlyHint=False, idempotentHint=False, destructiveHint=True

### Cross-cutting
- [ ] SQL wrapped in asyncio.to_thread (per existing tools.py pattern)
- [ ] SQL uses parameterized queries (no string interpolation)
- [ ] server.py __all__ updated to include set_approval_state
- [ ] Tool registered via @mcp.tool decorator (automatically excludable via MEMORY_TOOLS_EXCLUDE)

### Deliberate design notes
- approved-to-deleted transition NOT in _VALID_TRANSITIONS: that path uses mark_for-deletion (different audience: curator-accessible vs user-only, different idempotency semantics). See research doc sec 3B
- approved-to-pending NOT supported: approved entries are permanent knowledge per research sec 3A
- openWorldHint omitted: consistent with all 4 existing tools (none set it)

[[2026-04-03]] Fri 10:59
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** docs/decisions/resolved/387-memory-mcp-architecture.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| set_approval_state params | Original: vague "validates transitions". Missing types, error formats | Refined: explicit Literal param, _VALID_TRANSITIONS constant, soft error format |
| ToolAnnotations | Original: "not readOnly, not idempotent" -- no explicit values | Refined: explicit readOnlyHint=False, idempotentHint=False, destructiveHint=True |
| Pipeline exclusion | Original: unverifiable at tool level (config concern) | Refined: tool registered via @mcp.tool, excludable via MEMORY_TOOLS_EXCLUDE. Agent config is separate task |
| Reversibility | Subset of transition rules | Folded into transition AC (deleted to pending clears deleted_at) |
| Timestamp handling | Missing from original AC | Added: deleted_at set/clear, updated_at always |
| Return type | Missing from original AC | Added: str confirmation message |
| Cross-cutting | Missing from original AC | Added: asyncio.to_thread, parameterized queries, __all__, @mcp.tool registration |

### Architecture Notes
Follows mark_for-deletion pattern from tools.py L220-257 (entry lookup, state check, timestamp update, asyncio.to_thread). State machine has 3 valid transitions; approved-to-deleted intentionally routes through mark_for-deletion (different audience: curator vs user, different idempotency: mark_for-deletion is idempotent/no-op on deleted, set_approval_state rejects invalid transitions). MemoryEntry model in models.py already has Literal["pending", "approved", "deleted"]. Using Literal type for new-state param gives FastMCP schema-level enum validation. _VALID_TRANSITIONS as frozenset follows _VALID_CATEGORIES pattern in tools.py L30.

### Changes Made
- Rewrote AC body with per-param specs, error formats, ToolAnnotations, cross-cutting concerns
- Added _VALID_TRANSITIONS constant to AC (challenger suggestion accepted)
- Changed new-state from str to Literal type (challenger suggestion accepted)
- Removed unverifiable "pipeline exclusion" AC line, replaced with verifiable "registered via @mcp.tool" line
- Added deliberate design notes documenting mark_for-deletion coexistence
- Created test task #569 (Test: Add set_approval_state MCP tool)
- Added depends_on: [525, 569] to ensure TDD compliance

### Dependencies
- Verified: #525 (Implement memory-mcp tools) at archived status
- Verified: DR #387 (approved: true)
- Added: #569 (test task, TDD RED phase)

### Challenge Results
- Challenger: reconsider
- Confidence in original: .62
- Key challenges: C1 (mark_for-deletion overlap is state machine backdoor), C2 (missing test task), C3 (unverifiable pipeline exclusion AC)
- Architect response: partially accepted C1 (added deliberate design notes documenting the dual-path, but design is intentional per research sec 3B), accepted C2 (created #569), accepted C3 (rewrote to verifiable AC line). Accepted Literal type and _VALID_TRANSITIONS constant suggestions from blind spots section. Rejected single-tool consolidation (would break curator workflow design). Omitted openWorldHint (consistent with all 4 existing tools). Revised AC confidence: .85

[[2026-04-03]] Fri 15:44
## Test-Writer Notes
- Test file: tests/test_set_approval_state_529.py
- Classes: TestFromAC_LiteralAnnotation
- Tests per category: happy 0, edge 0, error 2, boundary 0
- Total: 2 tests, all FAIL (checked)
- ruff: clean
- AC coverage:
  AC-LIT new-state Literal type: test_new-state_annotation_is_not_bare_str, test_new-state_uses_literal_with-correct_values (error)
- Note: Runtime behavioural AC covered by test_set_approval_state_569.py (22 tests). SQL/tools.__all__ already satisfied by 569 builder.

[[2026-04-03]] Fri 16:06
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear_mcp_memory/tools.py
- Change: Added Literal to typing import; changed new-state: str to new-state: Literal[approved, deleted, pending]; split signature to multi-line (E501 fix)
- Tests: 24 passed (test_set_approval_state_529.py x2, test_set_approval_state_569.py x22)
- Lint: ruff clean
- Commit: 645767e feat: annotate set_approval_state new-state as Literal type (#529, builder)

[[2026-04-03]] Fri 16:30
## Review Evidence

### Test Results
- pytest tests/test_set_approval_state_529.py tests/test_set_approval_state_569.py: 24 passed, 0 failed

### Lint Results
- ruff check packages/mcp-memory/src/ tests/test_set_approval_state_529.py tests/test_set_approval_state_569.py: All checks passed!

### Coverage
- Structural tests (AST-based, no branches to measure): N/A

### Commit Scope
- git show --stat 645767e: 1 file changed (packages/mcp-memory/src/owlbear_mcp_memory/tools.py, 8 lines +/-)
- Surgical: only Literal import added + type annotation narrowed

### Test-Writer Coverage (AC 6.0)
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| new-state: Literal[approved,deleted,pending] | TestFromAC_LiteralAnnotation::test_new-state_annotation_is_not_bare_str | Yes â€” asserts NOT bare str | COVERED |
| new-state: Literal (exact values) | TestFromAC_LiteralAnnotation::test_new-state_uses_literal_with-correct_values | Yes â€” checks exact frozenset {approved,deleted,pending} | COVERED |
| All other AC items (transitions, timestamps, ToolAnnotations, __all__, asyncio.to_thread) | test_set_approval_state_569.py (22 tests) | Pre-satisfied by #569 pipeline | COVERED |

### Security (AC 6.1)
- No hardcoded secrets, no SQL injection (parameterized queries verified at L244, L265)
- Literal annotation IMPROVES security: FastMCP rejects invalid new-state values at schema layer (OWASP A03 benefit)
- No path traversal, no insecure deserialization, no new dependencies

### TestFromAC Integrity (AC 6.2)
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_LiteralAnnotation::test_new-state_annotation_is_not_bare_str | No change | PRESERVED |
| TestFromAC_LiteralAnnotation::test_new-state_uses_literal_with-correct_values | No change | PRESERVED |

### Test Quality (AC 6.3)
- Assertion specificity: STRONG â€” AST inspection of exact annotation node type and values
- Negative / error-path: N/A (structural tests, no runtime paths to test)
- Mutation resistance: STRONG â€” wrong Literal values or missing Literal both caught
- Test independence: STRONG â€” no shared mutable state
- Test names: STRONG â€” descriptive

### Builder Loop Detection (AC 6.7)
- 1 x Builder Notes section, no retries. Clean first-pass implementation.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| new-state: Literal[approved,deleted,pending] | tools.py L233 confirmed; test_new-state_uses_literal_with-correct_values PASS | PASS |
| _VALID_TRANSITIONS frozenset (3 pairs) | tools.py L33, test_valid_transitions_is_frozenset_with-exactly_three_pairs PASS (#569) | PASS |
| Soft error for invalid transitions | test_approved_to_pending_returns_soft_error + 5 others PASS (#569) | PASS |
| ToolError if entry_id not found | test_toolerror-raised_for-nonexistent_entry_id PASS (#569) | PASS |
| deleted_at set on to-deleted / cleared on deleted-to-pending | test_deleted_at_set_on_transition_to_deleted + test_deleted_at_cleared PASS (#569) | PASS |
| updated_at always set on success | test_updated_at_refreshed_on_successful_transition PASS (#569) | PASS |
| Returns str confirmation | test_successful_transition_returns_non_empty_str PASS (#569) | PASS |
| ToolAnnotations readOnlyHint=F, idempotentHint=F, destructiveHint=T | test_set_approval_state_annotations PASS (#569) | PASS |
| asyncio.to_thread + parameterized SQL | test_set_approval_state_uses_asyncio_to_thread PASS (#569) | PASS |
| server.py __all__ includes set_approval_state | test_server-all_includes_set_approval_state PASS (#569) | PASS |
| @mcp.tool decorator (excludable via MEMORY_TOOLS_EXCLUDE) | test_set_approval_state_discoverable_via_tool_manager PASS (#569) | PASS |

### Verdict: PASS
### Confidence: .95

[[2026-04-03]] Fri 16:47
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Task narrowed new-state type annotation only; set_approval_state was already implemented by #569. No behavior or API change. |
| 2 | Docstrings | Yes | PASS | set_approval_state (tools.py L230) has complete docstring: transitions, return str, ToolError for missing entry. |
| 3 | sources/overview.md | No | N/A | Follows internal mark_for-deletion pattern; no external patterns adopted. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research docs linked | Yes | PASS | docs/research/set-approval-state-mcp-tool.md and docs/research/curator-workflow-memory-mcp.md both exist and referenced in task body. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/529-* files found)

[[2026-04-03]] Fri 17:38
## Audit
### AC Verification
All 11 AC lines verified with specific evidence. See reviewer table for details.

### Test Results
- pytest (scoped): 24 passed, 0 failed
- pytest (full): 2847 passed, 237 failed (all unrelated to #529)
- ruff: All checks passed

### AC Quality: 5
### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-03]] Fri 17:39
## Audit
### AC Verification
All 11 AC lines verified with specific evidence. See reviewer table for details.

### Test Results
- pytest (scoped): 24 passed, 0 failed
- pytest (full): 2847 passed, 237 failed (all unrelated to #529)
- ruff: All checks passed

### AC Quality: 5
### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-03]] Fri 17:39
## Audit
### AC Verification
All 11 AC lines verified with specific evidence. See reviewer table for details.

### Test Results
- pytest (scoped): 24 passed, 0 failed
- pytest (full): 2847 passed, 237 failed (all unrelated to #529)
- ruff: All checks passed

### AC Quality: 5
### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-03]] Fri 17:40
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| fb9c09c | chore | kanban/tasks/529-*.md | #529 |
