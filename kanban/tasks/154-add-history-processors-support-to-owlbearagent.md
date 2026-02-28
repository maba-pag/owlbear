---
id: 154
title: Add history_processors support to OwlBearAgent
status: archived
priority: important
created: 2026-02-27T16:47:56.9665208+01:00
updated: 2026-02-28T23:53:11.6214034+01:00
started: 2026-02-27T16:48:18.1615085+01:00
completed: 2026-02-28T23:53:11.6214034+01:00
tags:
    - phase-8
    - agent
    - core
depends_on:
    - 153
class: standard
---

Forward PydanticAI history_processors param to inner Agent for native context management. Research: docs/pydantic-ai-multi-agent-research.md section 3.7.

## AC
- [ ] Add history_processors parameter to OwlBearAgent.__init__: Sequence[HistoryProcessor] | None = None
- [ ] Import HistoryProcessor type in TYPE_CHECKING block (from pydantic_ai._agent_graph or public re-export)
- [ ] Forward history_processors to inner Agent() constructor
- [ ] No behavior change when history_processors is None (default) — backwards-compatible
- [ ] Test: OwlBearAgent constructed with history_processors stores them (verify via inner Agent attribute)
- [ ] Test: OwlBearAgent constructed without history_processors defaults to None (backwards-compatible)
- [ ] ruff clean

## Architecture
- ~10 LOC diff in src/owlbear/core/agent.py
- PydanticAI HistoryProcessor: callable (messages: list[ModelMessage]) -> list[ModelMessage] (sync or async, with or without RunContext)
- Replaces any future manual session truncation — native PydanticAI feature
- No behavior change when history_processors is None (default)
- Depends on #153: both modify OwlBearAgent.__init__; #153 changes Agent[None, str] -> Agent[OwlBearDeps, str] which this task builds on
