---
id: 715
title: 'Tests: hook consumer typed payload annotations'
status: archived
priority: important
created: 2026-03-09T23:01:10.1806346+01:00
updated: 2026-03-10T22:01:22.3993302+01:00
started: 2026-03-10T21:20:38.2737955+01:00
completed: 2026-03-10T22:01:22.3993302+01:00
tags:
    - phase-7
    - hooks
    - typing
    - test
    - type:test
depends_on:
    - 483
claimed_by: builder
claimed_at: 2026-03-10T22:00:59.3801415+01:00
class: standard
---

RED phase tests for consumer annotation follow-up to #483.\n\n## Acceptance Criteria\n1. Test module: tests/test_hook_consumer_types.py\n2. Tests verify each of 11 hook consumers accepts its specific TypedDict param type:\n   - CommandSafetyGuard.__call__ -> PreToolUseData\n   - URLSafetyGuard.__call__ -> PreToolUseData\n   - AutoLintHook.__call__ -> PostToolUseData\n   - NotificationHook.__call__ -> dict (mixed events)\n   - ObservabilityHook._make_handler closure -> dict (mixed events)\n   - ContextInjectionHook.__call__ -> SessionStartData\n   - SubagentVerificationHook.__call__ -> SubagentCompleteData\n   - TestVerificationHook.__call__ -> SessionEndData\n   - RetrospectiveHook.__call__ -> TaskCompleteData\n   - ProgressReporter.on_tool_complete -> PostToolUseData\n   - ScreenshotOnErrorHook.handle -> OnErrorData\n3. Tests verify zero isinstance(data, dict) early-return guards remain in consumer __call__ methods\n4. All tests FAIL before implementation (RED phase)\n\n## Architecture Notes\n- Research found 10 consumers; this list adds URLSafetyGuard (11th) in tools/browser/safety.py\n- NotificationHook and ObservabilityHook register on multiple events - they use dict[str, Any] not a specific TypedDict\n- See docs/research/typed-hook-payloads.md

[[2026-03-10]] Tue 18:36
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| AC1: Test module tests/test_hook_consumer_types.py | Clear, specific filename. File does not exist yet. | Keep |
| AC2: 11 consumers  specific TypedDict param type | Verified all 11 consumers in codebase. Type mappings match hook event registrations (e.g. CommandSafetyGuard registers PRE_TOOL_USE -> PreToolUseData). NotificationHook/ObservabilityHook correctly use dict[str, Any] for multi-event. | Keep |
| AC3: Zero isinstance(data, dict) early-return guards in __call__ | Scoped to __call__ methods (7 consumers have early-return guards). ProgressReporter.on_tool_complete and ScreenshotOnErrorHook.handle are non-__call__  excluded correctly. Verifiable via AST/source inspection. | Keep |
| AC4: All tests FAIL before implementation (RED) | Standard TDD-RED meta-criterion. All consumers currently have data: object, so type-hint tests will fail. isinstance guards currently exist, so AC3 tests will fail. | Keep |

### Architecture Notes
- TDD pair verified: #715 (RED) -> #716 (GREEN). #716 depends_on [483, 715].
- Dependency #483 (TypedDict definitions) is archived  all 9 TypedDicts in core/hooks.py.
- Existing test pattern: tests/test_hook_payloads.py uses get_type_hints() per-class  test-writer should follow same approach.
- ObservabilityHook._make_handler returns a closure  test-writer may use inspect.signature() on the returned callable since get_type_hints() can be unreliable on closures.
- Module layering: test file only, no src/ changes required.

### Dependencies
- Verified: #483 (TypedDict definitions)  archived
- Verified: #716 (GREEN impl) depends_on #715  correct TDD ordering

[[2026-03-10]] Tue 19:11
## Test-Writer Notes
- Test file: tests/test_hook_consumer_types.py
- Classes: TestFromAC_ConsumerParamAnnotations, TestFromAC_NoIsinstanceGuards
- Tests per category: happy 11, edge 0, error 0, boundary 8
- Total: 19 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| AC2: CommandSafetyGuard.__call__ -> PreToolUseData | test_command_safety_guard_accepts_pre_tool_use_data | happy |
| AC2: URLSafetyGuard.__call__ -> PreToolUseData | test_url_safety_guard_accepts_pre_tool_use_data | happy |
| AC2: AutoLintHook.__call__ -> PostToolUseData | test_auto_lint_hook_accepts_post_tool_use_data | happy |
| AC2: NotificationHook.__call__ -> dict | test_notification_hook_accepts_dict | happy |
| AC2: ObservabilityHook._make_handler -> dict | test_observability_hook_handler_accepts_dict | happy |
| AC2: ContextInjectionHook.__call__ -> SessionStartData | test_context_injection_hook_accepts_session_start_data | happy |
| AC2: SubagentVerificationHook.__call__ -> SubagentCompleteData | test_subagent_verification_hook_accepts_subagent_complete_data | happy |
| AC2: TestVerificationHook.__call__ -> SessionEndData | test_test_verification_hook_accepts_session_end_data | happy |
| AC2: RetrospectiveHook.__call__ -> TaskCompleteData | test_retrospective_hook_accepts_task_complete_data | happy |
| AC2: ProgressReporter.on_tool_complete -> PostToolUseData | test_progress_reporter_on_tool_complete_accepts_post_tool_use_data | happy |
| AC2: ScreenshotOnErrorHook.handle -> OnErrorData | test_screenshot_on_error_hook_handle_accepts_on_error_data | happy |
| AC3: No isinstance guards in 8 __call__ methods | test_*_no_isinstance_guard (8 tests) | boundary |

[[2026-03-10]] Tue 20:09
## Builder Notes
- Files changed (src): command_guard.py, browser/safety.py, lint_hook.py, notification_hook.py, observability.py, context_hook.py, subagent_hook.py, test_hook.py, retrospective_hook.py, progress.py, screenshot_hook.py
- Files changed (tests): test_command_guard.py, test_lint_hook.py, test_context_hook.py, test_subagent_hook.py, test_test_hook.py, test_retrospective_hook.py, test_browser_safety.py (removed 8 obsolete non-dict-payload tests)
- Tests: 411 passed (19 new AC tests + 392 existing), coverage >= 97% on all touched modules
- Lint: ruff clean
- Evidence: All 11 consumer annotations changed from `object` to specific TypedDict/`dict[str, Any]`; all 8 isinstance(data, dict) guards removed from __call__ methods
- Circular import (hooks.py <-> test_hook.py) handled via module-level `import owlbear.core.hooks as _hooks_mod` with qualified annotation `_hooks_mod.SessionEndData`
- 8 obsolete `test_non_dict_data_ignored` tests removed (tested the isinstance guard behavior that AC3 removes)

[[2026-03-10]] Tue 22:00
## Audit
Confidence: .97 -- all 4 AC items PASS. 19/19 tests pass, ruff clean.
