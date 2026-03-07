---
id: 645
title: Implement RetrospectiveHook with triviality filter and KG ingest
status: archived
priority: important
created: 2026-03-07T08:18:20.3066451+01:00
updated: 2026-03-07T18:08:32.6879463+01:00
started: 2026-03-07T17:21:27.0403788+01:00
completed: 2026-03-07T18:08:32.6879463+01:00
tags:
    - scope:agent
    - scope:knowledge
    - phase-12
depends_on:
    - 621
    - 644
class: standard
---

RetrospectiveHook listens on TASK_COMPLETE, filters trivial tasks, runs PydanticAI agent for structured retrospective, ingests findings into knowledge graph. Fire-and-forget via asyncio.create_task().
See docs/retrospective-learning-hook-research.md for full design.

## AC

- [ ] RetrospectiveHook class in src/owlbear/core/retrospective_hook.py
- [ ] Constructor: RetrospectiveHook(model: Model, ingest_pipeline: IngestPipeline, kanban_root: Path)
- [ ] async __call__(data: object) -> None -- registered as TASK_COMPLETE handler
- [ ] register(hooks: HookRegistry) -> None -- registers self on HookEvent.TASK_COMPLETE
- [ ] Skip if payload is not a dict or outcome != 'success' (only retrospect successful completions)
- [ ] Triviality filter: skip tasks with 0 rejections AND priority < 'needed' (both conditions must be true to skip)
- [ ] Rejection count: parse kanban_root/activity.jsonl for entries with action='move' and task_id match; count moves where to_status in {todo, backlog, ideation} (backward moves = rejections)
- [ ] Priority: invoke subprocess.run() with kanban-md show {task_id} --json, parse JSON output for priority field; priority ordering: someday < nice-to-have < important < needed < critical
- [ ] Priority check only needed when rejection count is 0 (if rejections >= 1, task is non-trivial regardless of priority)
- [ ] RetroFindings frozen Pydantic BaseModel: what_worked, what_failed, error_patterns, reusable_patterns (all list[str])
- [ ] PydanticAI Agent[None, RetroFindings] with output_type=RetroFindings, stored as self._agent
- [ ] Findings formatted as text and ingested via IngestPipeline.ingest_text(text, metadata={'source_type': 'retrospective', 'task_id': str})
- [ ] __call__ spawns asyncio.create_task() -- fire-and-forget, does not block HookRegistry.emit()
- [ ] Error isolation: exceptions in background task logged via logger.exception and swallowed (never crashes daemon); ADD a test for this since #644 did not cover it
- [ ] Bootstrap wiring: register RetrospectiveHook in bootstrap() AFTER model creation (step 3) and build_toolsets (step 4), NOT inside build_hooks() -- build_hooks() runs before model and IngestPipeline exist; IngestPipeline must be exposed from build_toolsets or _build_knowledge_toolset return; kanban_root = workspace / 'kanban'
- [ ] All tests from #644 pass
- [ ] >= 90% coverage on retrospective_hook.py
- [ ] ruff clean

## Implementation Notes

- Follow SubagentVerificationHook class pattern (async __call__ + register) in src/owlbear/core/subagent_hook.py
- PydanticAI structured output: Agent[None, RetroFindings](model, output_type=RetroFindings, system_prompt=PROMPT)
- Bootstrap ordering constraint: build_hooks() at step 2, model at step 3, IngestPipeline inside build_toolsets at step 4 -- hook must be registered after step 4; build_toolsets already receives hooks and chat_model params, so registration can happen inside build_toolsets where infra is available, OR expose IngestPipeline in build_toolsets return tuple
- Rejection detection: parse JSONL line-by-line; 'detail' field format is '{from_status} -> {to_status}'; extract to_status, check membership in {'todo', 'backlog', 'ideation'}
- subprocess.run for kanban show is synchronous but acceptable inside fire-and-forget create_task (does not block event loop main path)
- Token cost: ~2200 tokens per retrospective (see research doc S3.4)
- LLM model instance: accept from caller (bootstrap threads it through via chat_model)
- Error isolation test (missing from #644): mock _agent.run to raise, verify logger.exception called, verify no exception propagates from __call__
