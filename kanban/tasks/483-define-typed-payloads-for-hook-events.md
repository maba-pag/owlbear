---
id: 483
title: Define typed payloads for hook events
status: in-progress
priority: important
created: 2026-03-04T07:38:00.5039018+01:00
updated: 2026-03-10T03:59:36.5348719+01:00
started: 2026-03-06T23:05:05.2610742+01:00
tags:
    - audit
    - refactor
    - hooks
depends_on:
    - 714
claimed_by: test-writer
claimed_at: 2026-03-10T03:59:36.5348719+01:00
class: standard
---

ARC-08/F-18/INT-05: Define typed payloads for hook events.
See docs/research/typed-hook-payloads-research.md for full analysis.

## Acceptance Criteria
1. 9 TypedDict classes defined in src/owlbear/core/hooks.py:
   - PreToolUseData: tool_name (str), args (dict[str, object])
   - PostToolUseData: tool_name (str); NotRequired: result (object), event_type (str), approval_required (bool), approval_decision (str), grant_ttl (int), grant_max_uses (int)
   - OnMessageData: prompt (str)
   - OnErrorData: error (Exception), prompt (str)
   - SessionStartData: session_id (str); NotRequired: workspace_root (str), context (dict[str, str])
   - SessionEndData: session_id (str); NotRequired: messages (list), test_results (list[TestResult])
   - SubagentCompleteData: NotRequired: task_id (str), created_files (list[str]), test_files (list[str]), result (object), verification (dict)
   - TaskCompleteData: task_id (str), outcome (str)
   - DaemonStartupData: channel (str), config_dir (str)
2. Handler alias updated from Callable[[object], object] to Callable[[dict[str, Any]], None]
3. All 9 TypedDicts exported from core/__init__.py (__all__ updated)
4. No QUESTION_PENDING TypedDict (YAGNI - event not yet emitted)
5. Zero runtime behavior changes - only type annotations added
6. All tests in test_hook_payloads.py pass; ruff check clean
7. Follow existing TypedDict precedent: TestResult in core/test_hook.py

## Architecture Notes
- PostToolUseData resolves INT-05 via NotRequired fields (PEP 655)
- Handler type fix resolves F-18 (return type None, param dict[str, Any])
- Emit sites unchanged - existing dict literals already satisfy TypedDicts structurally
- QUESTION_PENDING skipped - not emitted anywhere
- Consumer annotation is a separate follow-up task

## Patterns to Follow
- TestResult(TypedDict) in core/test_hook.py is the precedent
- Python 3.12+ NotRequired available natively
- TypedDicts go in core/hooks.py alongside HookEvent enum

[[2026-03-09]] Mon 23:03

## Architecture Review
VERDICT: APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| typed payloads | Vague - no TypedDict names or field specs | Rewritten: 9 named TypedDicts with exact fields |
| Handler type narrowed | Vague - target type unspecified | Rewritten: Callable[[dict[str, Any]], None] |
| INT-05 divergence | Implicit in description | Explicit: PostToolUseData NotRequired fields |

### Architecture Notes
- All TypedDicts in core/hooks.py alongside HookEvent (single module, single domain)
- Follows TestResult(TypedDict) precedent in core/test_hook.py
- Module layering: core/ is correct layer for type definitions consumed by core/ and tools/
- PostToolUseData resolves INT-05 via NotRequired (PEP 655) - zero breaking changes
- Handler Callable[[dict[str, Any]], None] fixes F-18 (return type was object, all handlers return None)
- YAGNI: QUESTION_PENDING TypedDict skipped (event not emitted), @overload deferred to #717
- Consumer annotation scoped out to separate task #716 (different domain: 11 files across core/ and tools/)
- Research missed URLSafetyGuard in tools/browser/safety.py - corrected in #715/#716 AC (11 consumers, not 10)

### Changes Made
- Created #714: TDD RED test task (todo, needed)
- Refined #483 AC: 7 verifiable criteria with exact TypedDict specs
- Added depends_on #714 (TDD compliance)
- Created #715: Consumer annotation tests (backlog)
- Created #716: Consumer annotation impl (backlog, depends_on #483 + #715)
- Created #717: @overload on emit (backlog, nice-to-have, depends_on #483)

### Dependencies
- Added: #714 (test task) - preceding RED phase
- Verified: no circular deps in graph #714 -> #483 -> #715 -> #716, #483 -> #717

[[2026-03-09]] Mon 23:03

## Architecture Review
VERDICT: APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| typed payloads | Vague - no TypedDict names or field specs | Rewritten: 9 named TypedDicts with exact fields |
| Handler type narrowed | Vague - target type unspecified | Rewritten: Callable[[dict[str, Any]], None] |
| INT-05 divergence | Implicit in description | Explicit: PostToolUseData NotRequired fields |

### Architecture Notes
- All TypedDicts in core/hooks.py alongside HookEvent (single module, single domain)
- Follows TestResult(TypedDict) precedent in core/test_hook.py
- Module layering: core/ is correct layer for type definitions consumed by core/ and tools/
- PostToolUseData resolves INT-05 via NotRequired (PEP 655) - zero breaking changes
- Handler Callable[[dict[str, Any]], None] fixes F-18 (return type was object, all handlers return None)
- YAGNI: QUESTION_PENDING TypedDict skipped (event not emitted), @overload deferred to #717
- Consumer annotation scoped out to separate task #716 (different domain: 11 files across core/ and tools/)
- Research missed URLSafetyGuard in tools/browser/safety.py - corrected in #715/#716 AC (11 consumers, not 10)

### Changes Made
- Created #714: TDD RED test task (todo, needed)
- Refined #483 AC: 7 verifiable criteria with exact TypedDict specs
- Added depends_on #714 (TDD compliance)
- Created #715: Consumer annotation tests (backlog)
- Created #716: Consumer annotation impl (backlog, depends_on #483 + #715)
- Created #717: @overload on emit (backlog, nice-to-have, depends_on #483)

### Dependencies
- Added: #714 (test task) - preceding RED phase
- Verified: no circular deps in graph #714 -> #483 -> #715 -> #716, #483 -> #717

[[2026-03-10]] Tue 03:59
## Test-Writer Notes
- RED phase already completed via #714 (archived)
- Test file: tests/test_hook_payloads.py
- Classes: TestFromAC_TypedDictImports, TestFromAC_PayloadFieldShapes, TestFromAC_PostToolUseDataShapes, TestFromAC_HandlerType, TestFromAC_CoreInitExports
- Total: 25 tests, all PASS (impl already exists from #714 pipeline)
- No new test file needed - #714 fully covers all #483 AC lines

[[2026-03-10]] Tue 03:59
## Test-Writer Notes
- RED phase already completed via #714 (archived)
- Test file: tests/test_hook_payloads.py
- Classes: TestFromAC_TypedDictImports, TestFromAC_PayloadFieldShapes, TestFromAC_PostToolUseDataShapes, TestFromAC_HandlerType, TestFromAC_CoreInitExports
- Total: 25 tests, all PASS (impl already exists from #714 pipeline)
- No new test file needed - #714 fully covers all #483 AC lines
