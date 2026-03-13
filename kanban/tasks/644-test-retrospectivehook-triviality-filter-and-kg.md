---
id: 644
title: 'Test: RetrospectiveHook triviality filter and KG ingest'
status: archived
priority: important
created: 2026-03-07T08:17:51.7083469+01:00
updated: 2026-03-07T18:08:32.1576804+01:00
started: 2026-03-07T16:51:16.3958626+01:00
completed: 2026-03-07T18:08:32.1576804+01:00
tags:
    - scope:agent
    - scope:knowledge
    - scope:test
    - phase-12
depends_on:
    - 621
class: standard
---

Test-first companion for the RetrospectiveHook implementation (#645). Write failing tests that describe the target interface before any production code exists.
See docs/research/retrospective-learning-hook.md for full design.

## AC

- [ ] Test: non-trivial task (>=1 rejection) triggers PydanticAI retrospective agent
- [ ] Test: trivial task (0 rejections AND priority < needed) skips retrospective (agent never called)
- [ ] Test: priority >= needed triggers retrospective even with 0 rejections
- [ ] Test: outcome='failure' skips retrospective (only successful tasks get retrospectives)
- [ ] Test: RetroFindings model has fields: what_worked, what_failed, error_patterns, reusable_patterns (all list[str], frozen BaseModel)
- [ ] Test: ingest_text called with text containing formatted findings and metadata containing source_type='retrospective' and task_id
- [ ] Test: __call__ spawns asyncio.create_task for the retrospective work and returns immediately (fire-and-forget, does not block emit)
- [ ] Test: register(hooks) adds handler on HookEvent.TASK_COMPLETE
- [ ] Test: constructor accepts model (Model), ingest_pipeline (IngestPipeline), and kanban_root (Path) for activity log access
- [ ] All tests fail initially (no production code yet -- import errors are acceptable failures)
- [ ] ruff clean

## Implementation Notes

- Mock IngestPipeline.ingest_text, PydanticAI agent.run, and kanban activity.jsonl (provide fixture file or mock Path)
- Follow existing test patterns in test_hooks.py (asyncio.run), test_subagent_hook.py (payload helpers, MagicMock/AsyncMock)
- RetrospectiveHook follows SubagentVerificationHook class pattern: async __call__(data) + register(hooks)
- Constructor signature: RetrospectiveHook(model, ingest_pipeline, kanban_root) where kanban_root is Path to kanban/ dir containing activity.jsonl
- Rejection count: count 'move' entries in activity.jsonl where task_id matches AND to_status in {todo, backlog, ideation} (backward moves = rejections)
- Priority: parsed from kanban show --json output or activity log
- TASK_COMPLETE payload shape: {'task_id': str, 'outcome': 'success' | 'failure'} -- hook reads task_id to look up history
- For fire-and-forget testing: capture the asyncio.Task returned by create_task, await it in test to verify side effects
- Test file: tests/test_retrospective_hook.py
- Production module (not yet created): src/owlbear/core/retrospective_hook.py
