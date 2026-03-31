---
id: 428
title: 'deer-flow deep dive: memory system + subagent delegation patterns'
status: ideation
priority: needed
created: 2026-03-30T21:17:52.6808313+02:00
updated: 2026-03-30T21:17:52.6808313+02:00
tags:
    - research
    - ' scope:agents'
    - ' phase-2'
depends_on:
    - 386
class: standard
---

## Context

Focused analysis of deer-flow's memory and subagent systems. These two areas directly feed OwlBear's planned work:
- Memory system findings feed #387 (per-agent institutional knowledge via memory-mcp)
- Subagent system findings feed #228 (subagent nesting architecture)

The deer-flow repo should already be cloned at `docs/scratch/research/deer-flow/` (parent task #386 handles cloning).

## Scope

### Memory System (feeds #387)
Analyze `packages/harness/deerflow/agents/memory/` in depth:
- `updater.py` — LLM-based fact extraction. What prompts does it use? How does it decide what's a "fact"?
- `queue.py` — Debounced update queue. How does per-thread deduplication work?
- `prompt.py` — Prompt templates for memory updates
- Memory JSON schema: `workContext`, `personalContext`, `topOfMind`, `recentMonths`, `earlierContext`, `longTermBackground` + facts with id/content/category/confidence/createdAt/source
- Fact deduplication: whitespace-normalized content comparison
- Injection: top 15 facts + context into `<memory>` tags in system prompt
- Config: `max_facts` (100), `fact_confidence_threshold` (0.7), `max_injection_tokens` (2000), `debounce_seconds` (30)

### Subagent System (feeds #228)
Analyze `packages/harness/deerflow/subagents/` in depth:
- `executor.py` — Background execution engine. Dual thread pool (`_scheduler_pool` 3 workers + `_execution_pool` 3 workers). How does this work?
- `registry.py` — Agent registry. How are subagents registered and discovered?
- `builtins/` — general-purpose and bash agents. What distinguishes them?
- `task()` tool — the tool that delegates to subagents. Parameters: description, prompt, subagent_type, max_turns
- `SubagentLimitMiddleware` — enforces MAX_CONCURRENT_SUBAGENTS (3). How does truncation work?
- SSE events: task_started, task_running, task_completed/failed/timed_out
- 15-minute timeout per subagent

## Acceptance Criteria

- [ ] Read and document deer-flow's memory extraction prompts — what does the LLM see when extracting facts? How are categories assigned?
- [ ] Document the fact lifecycle: creation, confidence scoring, deduplication, injection, expiry/pruning
- [ ] Compare deer-flow's memory model to OwlBear's proposed 4-dimensional scoping (#387) — what ideas are transferable? What's missing?
- [ ] Read and document the subagent executor's dual-thread-pool architecture — why two pools? How does scheduling vs execution separate?
- [ ] Document subagent discovery/registry — how does deer-flow know what subagents exist?
- [ ] Compare deer-flow's subagent delegation to OwlBear's orchestrator dispatch and the proposed nesting patterns (#228)
- [ ] For each system: document what deer-flow does, how it differs from OwlBear, and adoption recommendation with confidence score
- [ ] Create a decision request with top findings for user approval
- [ ] Create follow-up tasks at ideation for approved patterns
