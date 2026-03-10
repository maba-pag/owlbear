---
id: 715
title: 'Tests: hook consumer typed payload annotations'
status: backlog
priority: important
created: 2026-03-09T23:01:10.1806346+01:00
updated: 2026-03-09T23:01:16.1136934+01:00
tags:
    - phase-7
    - hooks
    - typing
    - test
    - type:test
depends_on:
    - 483
class: standard
---

RED phase tests for consumer annotation follow-up to #483.\n\n## Acceptance Criteria\n1. Test module: tests/test_hook_consumer_types.py\n2. Tests verify each of 11 hook consumers accepts its specific TypedDict param type:\n   - CommandSafetyGuard.__call__ -> PreToolUseData\n   - URLSafetyGuard.__call__ -> PreToolUseData\n   - AutoLintHook.__call__ -> PostToolUseData\n   - NotificationHook.__call__ -> dict (mixed events)\n   - ObservabilityHook._make_handler closure -> dict (mixed events)\n   - ContextInjectionHook.__call__ -> SessionStartData\n   - SubagentVerificationHook.__call__ -> SubagentCompleteData\n   - TestVerificationHook.__call__ -> SessionEndData\n   - RetrospectiveHook.__call__ -> TaskCompleteData\n   - ProgressReporter.on_tool_complete -> PostToolUseData\n   - ScreenshotOnErrorHook.handle -> OnErrorData\n3. Tests verify zero isinstance(data, dict) early-return guards remain in consumer __call__ methods\n4. All tests FAIL before implementation (RED phase)\n\n## Architecture Notes\n- Research found 10 consumers; this list adds URLSafetyGuard (11th) in tools/browser/safety.py\n- NotificationHook and ObservabilityHook register on multiple events - they use dict[str, Any] not a specific TypedDict\n- See docs/research/typed-hook-payloads-research.md
