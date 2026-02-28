---
id: 263
title: 'Research: Bootstrap/assembly layer — nanobot wiring patterns for PydanticAI'
status: archived
priority: critical
created: 2026-02-28T13:31:55.7126658+01:00
updated: 2026-02-28T23:54:29.5275515+01:00
started: 2026-02-28T13:57:46.3199827+01:00
completed: 2026-02-28T23:54:29.5275515+01:00
tags:
    - research
    - agent
    - phase-8
class: standard
---

## Context
The full project audit (2026-02-28) revealed the 'assembly gap': 50 modules, 1608 tests passing, but no bootstrap layer wires them into a running system. The user directed: 'use nanobot as the base, as far as this is feasible, and go from there.''

## Research Questions
1. How does nanobot wire its AgentLoop, MessageBus, ChannelManager, and tools together at startup?
2. Which nanobot patterns translate to PydanticAI (we use Agent.run(), FunctionToolset, RunContext)?
3. What is the minimal bootstrap() function that wires all OwlBear modules?
4. How should the MessageBus pattern replace our current ChannelPlugin.receive()/send()?
5. Can we adopt nanobot's memory consolidation (LLM-based MEMORY.md + HISTORY.md) pattern?
6. How should we handle Copilot token refresh in a long-running daemon?

## Nanobot Components to Evaluate
- AgentLoop (loop.py ~22K, manages tool iteration, session, context)
- MessageBus (async queue decoupling channels from agent)
- ChannelManager (multi-channel init + routing)
- ContextBuilder (bootstrap files, skills, memory injection)
- SubagentManager (subagent spawning + cancellation)
- SessionManager (JSONL + LLM consolidation)
- ToolRegistry + Tool ABC (our equivalent: PydanticAI FunctionToolset)

## Key Constraint
Nanobot uses LiteLLM + raw OpenAI messages. OwlBear uses PydanticAI which manages the agent loop. Direct adoption of AgentLoop is NOT feasible. Pattern extraction + adaptation is required.

## Acceptance Criteria
- [ ] Comparison table: nanobot component vs OwlBear equivalent vs adaptation needed
- [ ] Bootstrap function design (what gets wired, in what order)
- [ ] MessageBus adoption: yes/no decision with rationale
- [ ] Memory consolidation: yes/no decision with rationale
- [ ] Follow-up implementation tasks created on kanban
- [ ] daemon-bootstrap-research.md findings integrated

See docs/daemon-bootstrap-research.md and docs/agent-patterns-research.md for prior art.
