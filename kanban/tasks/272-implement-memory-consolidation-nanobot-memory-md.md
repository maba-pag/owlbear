---
id: 272
title: Implement memory consolidation - nanobot MEMORY.md pattern
status: archived
priority: important
created: 2026-02-28T14:21:18.2027618+01:00
updated: 2026-02-28T23:54:35.6230799+01:00
started: 2026-02-28T15:06:20.9447603+01:00
completed: 2026-02-28T23:54:35.6230799+01:00
tags:
    - phase-8
    - agent
    - memory
class: standard
---

## Context
Adopt nanobot two-layer memory consolidation: LLM summarizes old turns -> MEMORY.md (always in context) + HISTORY.md (grep-searchable log).
See docs/research/bootstrap-assembly.md S3.5 and nanobot agent/memory.py.
NOT on the bootstrap critical path — this is a follow-up enhancement.

## Acceptance Criteria
- [ ] src/owlbear/memory/consolidation.py with MemoryConsolidator class
- [ ] Constructor: MemoryConsolidator(workspace_root: Path, model: str | Model = 'test', threshold: int = 20)
- [ ] consolidate(session: SessionStore) -> bool: returns True if consolidation was performed
- [ ] Reads unconsolidated messages (all messages after last_consolidated index)
- [ ] Uses PydanticAI Agent.run() with structured output (ConsolidationResult: summary: str, key_facts: list[str])
- [ ] Writes/updates MEMORY.md at workspace_root (summary + key facts, ~500 tokens target)
- [ ] Appends to HISTORY.md at workspace_root (timestamped log of consolidated turns, append-only)
- [ ] Triggered when len(unconsolidated_messages) > threshold
- [ ] Add last_consolidated: int | None field to SessionStore (index into message list, None = never consolidated)
- [ ] SessionStore.save() preserves last_consolidated; SessionStore.load() restores it
- [ ] last_consolidated stored as first-line JSON metadata in JSONL file (or separate .meta file)
- [ ] ContextManager.instructions property: if MEMORY.md exists at workspace_root, append its content to instructions
- [ ] Unit test: mock LLM, verify MEMORY.md written with structured output
- [ ] Unit test: verify HISTORY.md is append-only (multiple consolidations)
- [ ] Unit test: verify threshold gating (no consolidation when below threshold)
- [ ] Unit test: verify last_consolidated pointer updated after consolidation
- [ ] Unit test: verify ContextManager injects MEMORY.md content into instructions
- [ ] ~100 LOC across consolidation.py + session.py + context.py changes

## Architecture Notes
- This task touches 3 files: consolidation.py (new), session.py (add pointer), context.py (inject MEMORY.md)
- All changes are cohesive around one feature (memory consolidation), so keeping as one task is appropriate
- ConsolidationResult should be a Pydantic BaseModel for PydanticAI structured output
- MEMORY.md format: '# Memory\n\n## Summary\n{summary}\n\n## Key Facts\n{bullet list}'
- HISTORY.md format: '## {ISO timestamp}\n{summary}\n---\n' (append per consolidation)
- last_consolidated as separate .meta JSON file is simpler than modifying JSONL format
- The consolidation agent is a lightweight PydanticAI Agent (no tools, just structured output)
- Model parameter allows using a cheap/fast model for consolidation vs main agent model

## TDD
Tests included in AC above. All tests in tests/test_consolidation.py.
