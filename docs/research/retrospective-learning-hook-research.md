# Retrospective Learning Hook — Research

> **Owning task:** #621 — Retrospective learning hook on task completion
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear's daemon completes tasks via the poll-dispatch-reconcile loop but captures
no structured learnings afterward. The `ErrorJournal` logs errors but doesn't extract
patterns, successful strategies, or reusable insights. Should OwlBear adopt a
retrospective learning hook on task completion, and how should it integrate with the
existing hook system and knowledge graph?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Conductor retrospective agent | [GitHub](https://github.com/Ibrahim-3d/conductor-orchestrator-superpowers) | .85 | Post-track retrospective → `patterns.md` + `errors.json` |
| Reflexion (Shinn et al., 2023) | [arXiv:2303.11366](https://arxiv.org/abs/2303.11366) | .80 | Verbal self-reflection stored in episodic memory buffer |
| OwlBear hook system | `src/owlbear/core/hooks.py` | .95 | `HookEvent.TASK_COMPLETE` exists; never emitted in production |
| OwlBear knowledge ingest | `src/owlbear/memory/knowledge/ingest.py` | .90 | `IngestPipeline.ingest_text()` accepts raw text + metadata |
| OwlBear ErrorJournal | `src/owlbear/memory/error_journal.py` | .75 | Append-only JSONL; no pattern extraction |
| Conductor orchestrator SKILL | conductor-orchestrator `SKILL.md` | .85 | Knowledge Manager pre-loads patterns; Retrospective Agent post-extracts |

## 3. Analysis

### 3.1 Pattern Comparison

| Criterion | Conductor (flat files) | Reflexion (episodic buffer) | Proposed: OwlBear (KG ingest) |
|-----------|----------------------|---------------------------|-------------------------------|
| Storage | `patterns.md` + `errors.json` | In-context memory buffer | Knowledge graph + vector store |
| Retrieval | Keyword match in text | Injected into next trial prompt | Semantic search via `KnowledgeQueryService` |
| Persistence | Per-project files | Per-session (lost across sessions) | Permanent, cross-project scoped |
| Structure | Free-form markdown + JSON array | Free-form verbal reflection | Structured `RetroFindings` Pydantic model |
| Trigger | Post-track completion (orchestrator calls) | After each trial attempt | `TASK_COMPLETE` hook event |
| Cost | 1 LLM call per track | 1 LLM call per trial | 1 LLM call per non-trivial task |
| KISS score | High (simple files) | High (text buffer) | Medium (needs LLM + ingest pipeline) |

### 3.2 Architecture Fit

Existing infrastructure covers every piece:

| Component | Exists? | Notes |
|-----------|---------|-------|
| `HookEvent.TASK_COMPLETE` | Yes | Defined in `HookEvent` enum, never emitted |
| `HookRegistry.emit()` | Yes | Async, error-isolated per handler |
| `IngestPipeline.ingest_text()` | Yes | Accepts raw text + metadata, full pipeline |
| `KnowledgeQueryService.query_for_context()` | Yes | Per-turn injection into agent prompt |
| Production emit site | **No** | `reconcile_tasks()` in `daemon.py` must emit |
| `RetroFindings` model | **No** | New Pydantic model needed |
| Retrospective LLM call | **No** | PydanticAI structured output agent needed |

### 3.3 Triviality Filter

Not every task warrants a retrospective. Conductor skips tracks that completed on
first pass with no fix cycles. Proposed criteria for OwlBear:

| Signal | Source | Skip if |
|--------|--------|---------|
| Rejection count | kanban activity log | 0 rejections (never sent back) |
| Fix cycles | task frontmatter / kanban moves | No review→todo or review→backlog moves |
| Error journal entries | `ErrorJournal.query(tool_name=task_id)` | No errors logged |
| Task priority | kanban frontmatter | `someday` or `nice-to-have` |

A task is "non-trivial" if it had ≥1 rejection/fix cycle OR priority ≥ `needed`.

### 3.4 Token Cost Analysis

| Component | Est. tokens | When |
|-----------|-------------|------|
| Retrospective prompt (task context) | ~1,500 | Per non-trivial task |
| LLM analysis response | ~500 | Per non-trivial task |
| Knowledge ingest (chunking + embedding) | ~200 | Per retrospective |
| **Total per task** | **~2,200** | Only non-trivial |

Conservative estimate: 20% of tasks are non-trivial → ~5 retrospectives per 25-task batch.

## 4. Recommendation (.85 confidence)

**Implement a `RetrospectiveHook` that:**

1. Listens on `HookEvent.TASK_COMPLETE`
2. Checks triviality filter (rejection count, priority)
3. If non-trivial: calls a PydanticAI agent with structured `RetroFindings` output
4. Ingests findings as text via `IngestPipeline.ingest_text()` with metadata
   `{"source_type": "retrospective", "task_id": "...", "scope": "project"}`

**Data flow:**

```
reconcile_tasks() ─emit──► TASK_COMPLETE{task_id, outcome}
                                │
                    RetrospectiveHook.handle()
                                │
                    triviality check (skip if trivial)
                                │
                    PydanticAI Agent → RetroFindings
                                │
                    IngestPipeline.ingest_text(findings_text, metadata)
                                │
                    Knowledge graph ← searchable via KnowledgeQueryService
```

**Risk:** LLM call in hook handler blocks the reconcile tick. Mitigation: fire-and-forget
via `asyncio.create_task()` so the hook returns immediately.

**Why not flat files (Conductor pattern)?** OwlBear already has a knowledge graph with
semantic search. Ingesting into KG makes findings automatically retrievable via
`query_for_context()` on future tasks — no custom search code needed. KISS-aligned
because it reuses existing infrastructure.

## 5. Refined AC

- [ ] `reconcile_tasks()` emits `HookEvent.TASK_COMPLETE` with `{task_id, outcome}` payload
- [ ] `RetrospectiveHook` class with `register(hooks)` / `handle(data)` pattern
- [ ] Triviality filter: skip tasks with 0 rejections AND priority < `needed`
- [ ] PydanticAI agent produces structured `RetroFindings` (what_worked, what_failed, error_patterns, reusable_patterns)
- [ ] Findings ingested via `IngestPipeline.ingest_text()` with `source_type: retrospective`
- [ ] Hook registered in `build_hooks()` when knowledge system is available
- [ ] Fire-and-forget async: hook does not block reconcile loop
- [ ] Tests: mock hook emission → verify ingest called with correct metadata

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Emit TASK_COMPLETE from reconcile_tasks" --priority needed --status backlog --tags "scope:core,phase-12" --body "reconcile_tasks() in daemon.py must emit HookEvent.TASK_COMPLETE with payload {task_id: str, outcome: 'success' | 'failure'} after popping completed tasks from state.running. Currently TASK_COMPLETE is defined in HookEvent but never emitted in production code.\n\nAC:\n- [ ] emit called after successful task completion (outcome=success)\n- [ ] emit called after failed task completion (outcome=failure)\n- [ ] hooks instance threaded through to reconcile_tasks\n- [ ] Test: mock registry, verify emit called with correct payload"

kanban\kanban-md.exe create "Implement RetrospectiveHook with triviality filter" --priority important --status backlog --tags "scope:agent,scope:knowledge,phase-12" --depends-on 621 --body "RetrospectiveHook listens on TASK_COMPLETE. Triviality filter skips tasks with 0 rejections AND priority < needed. Non-trivial tasks trigger PydanticAI agent with RetroFindings structured output. Findings ingested via IngestPipeline.ingest_text() with source_type=retrospective. Fire-and-forget via asyncio.create_task().\n\nAC:\n- [ ] RetrospectiveHook class with register/handle pattern\n- [ ] Triviality filter based on rejection count + priority\n- [ ] RetroFindings Pydantic model (what_worked, what_failed, error_patterns, reusable_patterns)\n- [ ] PydanticAI agent with structured output\n- [ ] ingest_text called with metadata {source_type: retrospective, task_id}\n- [ ] Fire-and-forget async (does not block reconcile)\n- [ ] Registered in build_hooks() when knowledge system available\n- [ ] >= 90% coverage"

kanban\kanban-md.exe create "Test retrospective hook end-to-end" --priority important --status backlog --tags "scope:test,scope:knowledge,phase-12" --depends-on 621 --body "Integration test: emit TASK_COMPLETE with non-trivial payload → verify RetrospectiveHook calls PydanticAI agent → verify ingest_text called with correct metadata. Also test triviality filter skips trivial tasks.\n\nAC:\n- [ ] Test non-trivial task triggers retrospective\n- [ ] Test trivial task skips retrospective\n- [ ] Test fire-and-forget does not block\n- [ ] Test ingest metadata contains source_type=retrospective"
```
