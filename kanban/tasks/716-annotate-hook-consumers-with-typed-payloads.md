---
id: 716
title: Annotate hook consumers with typed payloads
status: backlog
priority: important
created: 2026-03-09T23:01:27.5822872+01:00
updated: 2026-03-09T23:01:33.8471428+01:00
tags:
    - phase-7
    - hooks
    - typing
    - refactor
depends_on:
    - 483
    - 715
class: standard
---

Remove isinstance(data, dict) boilerplate from 11 hook consumers.\n\n## Acceptance Criteria\n1. Update __call__ (or handler method) signatures in 11 consumers to use specific TypedDict param type:\n   - CommandSafetyGuard.__call__(data: PreToolUseData)\n   - URLSafetyGuard.__call__(data: PreToolUseData)\n   - AutoLintHook.__call__(data: PostToolUseData)\n   - ContextInjectionHook.__call__(data: SessionStartData)\n   - SubagentVerificationHook.__call__(data: SubagentCompleteData)\n   - TestVerificationHook.__call__(data: SessionEndData)\n   - RetrospectiveHook.__call__(data: TaskCompleteData)\n   - ProgressReporter.on_tool_complete(data: PostToolUseData)\n   - ScreenshotOnErrorHook.handle(data: OnErrorData)\n   - NotificationHook: dict[str, Any] (multi-event)\n   - ObservabilityHook: dict[str, Any] (multi-event)\n2. Remove isinstance(data, dict) early-return guards from all 11 consumers (13 occurrences total)\n3. Do NOT touch skills/registry.py isinstance guard (different concern)\n4. All existing hook tests pass; ruff check clean\n5. Zero runtime behavior changes beyond removing unreachable guard branches\n\n## Architecture Notes\n- HookRegistry.emit always passes dict - isinstance guards are dead code\n- NotificationHook._make_handler and ObservabilityHook._make_handler use closures that inject event; keep dict[str, Any] for these\n- See docs/research/typed-hook-payloads-research.md
