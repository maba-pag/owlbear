---
id: 143
title: 'Test: Extract CancelSignal and sandbox_path'
status: archived
priority: medium
created: 2026-03-29 16:12:59.664115+02:00
updated: 2026-04-03 02:11:58.713259+02:00
started: 2026-04-03 02:10:43.045352+02:00
completed: 2026-04-03 02:10:43.045352+02:00
tags:
- phase-1
- ' scope:knowledge'
- ' test'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests (TDD RED) for CancelSignal and sandbox_path extraction into packages/knowledge/.

## Acceptance Criteria
- [ ] Test file: tests/test_knowledge_cancel_sandbox.py
- [ ] CancelSignal tests (import from owlbear_knowledge.cancellation):
  - CancelSignal is @runtime_checkable Protocol with is_set() -> bool
  - Any object with is_set() -> bool satisfies CancelSignal (isinstance check)
  - LinkedCancelSignal(*sources).is_set() returns False when no source is set
  - LinkedCancelSignal(*sources).is_set() returns True when any source is set
  - LinkedCancelSignal composes 3+ CancelSignal sources correctly
- [ ] sandbox_path tests (import from owlbear_knowledge._paths):
  - Valid relative path resolves under root
  - Null byte in path raises PermissionError
  - `..` traversal outside root raises PermissionError
  - Absolute path inside root resolves correctly
  - Absolute path outside root raises PermissionError
- [ ] All tests import from owlbear_knowledge (not v1 paths)
- [ ] All tests fail at RED phase (modules not yet implemented)
- [ ] ruff check passes on test file

## Architecture Notes
- Follow TestFromAC_* naming convention (see test_knowledge_foundation.py)
- CancelSignal: sync Protocol, use plain mock objects (no AsyncMock needed)
- sandbox_path: use tmp_path fixture for root, pure path operations
- No in-memory SQLite needed (these modules have no DB dependency)

## Context
TDD RED phase for #135. See docs/research/extract-cancel-sandbox-consolidation-evaluator.md S3.5.
Consolidation + evaluator tests removed per scope refinement (overlap with #138). See docs/research/task-143-tdd-red-scope-validation.md S3.2.

[[2026-03-29]] Sun 20:59
## Architecture Review\n**Verdict:** REFINE\n\n### AC Assessment\nCancelSignal + sandbox_path AC: verified against v1 source, kept and tightened.\nConsolidation + evaluator AC: removed (overlap with #138, incompatible constructors).\nAdded: isinstance duck-type check, 3+ source composition test.\n\n### Architecture Notes\nv1 cancellation.py (29 LOC, sync Protocol) and paths.py (36 LOC, pure function) verified. No existing v2 tests. Scope conflict resolved: consolidation+evaluator used LLM-injectable constructors (TextCompletionFn, EvaluateFn) that conflict with #138 stub constructors (graph_store=None, model=None). Removed to avoid test collision. When #135 implements, it must update #138 tests. Test patterns: TestFromAC_CancelSignal, TestFromAC_SandboxPath. No DB or AsyncMock needed.\n\n### Changes Made\nRenamed task to CancelSignal+sandbox_path scope. Rewrote body removing consolidation+evaluator AC. Updated test filename to tests/test_knowledge_cancel_sandbox.py. Added isinstance and 3+ source tests.\n\n### Dependencies\nVerified: #135 depends_on #143 (TDD ordering). No overlap with #138 after refinement. Cross-task: #135 AC needs update for #138 test constructor migration.

[[2026-03-29]] Sun 21:21
## Test-Writer Notes
- Test file: tests/test_knowledge_cancel_sandbox.py
- Classes: TestFromAC_CancelSignal, TestFromAC_LinkedCancelSignal, TestFromAC_SandboxPath
- Tests per category: happy 14, edge 8, error 5, boundary 0
- Total: 27 tests, all FAIL (ModuleNotFoundError - modules not yet implemented)
- ruff: clean
- AC coverage:
  - CancelSignal is @runtime_checkable Protocol: test_cancel_signal_importable, test_cancel_signal_is_runtime_checkable_protocol (happy)
  - Any object with is_set() satisfies CancelSignal: test_object_with_is_set_satisfies_cancel_signal, test_object_without_is_set_does_not_satisfy_cancel_signal (happy/error)
  - LinkedCancelSignal no source is_set() False: test_no_sources_is_never_set (happy)
  - LinkedCancelSignal any source set returns True: test_single_set_source_returns_true, test_two_sources_one_set_returns_true, test_two_sources_second_set_returns_true (happy)
  - LinkedCancelSignal 3+ sources: test_three_sources_none_set_returns_false, test_three_sources_middle_set_returns_true (edge)
  - Valid relative path resolves under root: test_valid_relative_path_resolves_under_root, test_relative_path_single_component (happy)
  - Null byte raises PermissionError: test_null_byte_in_path_raises_permission_error, test_null_byte_embedded_raises_permission_error (error)
  - dotdot traversal raises PermissionError: test_dotdot_traversal_outside_root_raises_permission_error, test_dotdot_deep_traversal_raises_permission_error (error)
  - Absolute path inside root resolves: test_absolute_path_inside_root_resolves_correctly (happy)
  - Absolute path outside root raises PermissionError: test_absolute_path_outside_root_raises_permission_error (error)

[[2026-03-29]] Sun 22:25
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/cancellation.py, packages/knowledge/src/owlbear_knowledge/_paths.py
- Tests: 27 passed, 100% coverage on both modules
- Lint: ruff clean
- Evidence: 27 passed in 0.24s, All checks passed

[[2026-03-30]] Mon 08:30
## Review Evidence
See docs/scratch/143-reviewer.md for full evidence.

[[2026-04-03]] Fri 01:35
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Internal utility modules; no behavior/API/convention change described there |
| 2 | Docstrings | Yes | Pass | cancellation.py: CancelSignal+LinkedCancelSignal fully documented; _paths.py: sandbox_path() has full Args/Returns/Raises docstring |
| 3 | docs/sources/overview.md | Yes | Pass | v1 cancellation.py + paths.py attributed (lines 579-580); .NET CancellationToken prior art (line 699) already recorded |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research docs linked | Yes | Pass | Both research docs exist and referenced in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None (docs/scratch/143-* - no files found)

[[2026-04-03]] Fri 02:10
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Test file: tests/test_knowledge_cancel_sandbox.py | File exists, 28 tests | PASS |
| CancelSignal is @runtime_checkable Protocol | test_cancel_signal_is_runtime_checkable_protocol L41 | PASS |
| Any object with is_set() satisfies CancelSignal | test_object_with_is_set_satisfies_cancel_signal L51 | PASS |
| LinkedCancelSignal no source is_set() False | test_no_sources_is_never_set L97 | PASS |
| LinkedCancelSignal any source set returns True | test_single_set_source_returns_true L108, L123, L138 | PASS |
| LinkedCancelSignal composes 3+ sources | test_three_sources_none_set_returns_false L152, test_three_sources_middle_set_returns_true L162 | PASS |
| Valid relative path resolves under root | test_valid_relative_path_resolves_under_root L233 | PASS |
| Null byte raises PermissionError | test_null_byte_in_path_raises_permission_error L247 | PASS |
| dotdot traversal raises PermissionError | test_dotdot_traversal_outside_root_raises_permission_error L264 | PASS |
| Absolute path inside root resolves | test_absolute_path_inside_root_resolves_correctly L277 | PASS |
| Absolute path outside root raises PermissionError | test_absolute_path_outside_root_raises_permission_error L284 | PASS |
| All tests import from owlbear_knowledge | Verified all imports use owlbear_knowledge namespace | PASS |
| ruff check passes | All checks passed on all 3 files | PASS |

### Test Results
- pytest (scoped): 28 passed in 0.51s
- pytest (full suite): 3131 passed, 247 failed (all pre-existing RED tests from other tasks, none in #143 scope)
- ruff: clean

### AC Quality Score: 5/5
AC was specific, complete, and mapped directly to verifiable test cases. Architect refined scope well (removed #138 overlap). All AC items were directly testable.

### Deduction breakdown
- -.02 reviewer evidence file (docs/scratch/143-reviewer.md) referenced but missing

### Confidence: .98
### Action: archive

[[2026-04-03]] Fri 02:11
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 065c8e6 | chore | kanban/tasks/143-*.md | #143 |
