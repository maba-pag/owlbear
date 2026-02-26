---
id: 38
title: Implement HookRegistry
status: done
priority: high
created: 2026-02-26T15:56:40.5978275+01:00
updated: 2026-02-26T19:50:16.1192307+01:00
started: 2026-02-26T19:41:44.2338163+01:00
completed: 2026-02-26T19:50:16.1192307+01:00
tags:
    - phase-2
    - agent
    - hooks
depends_on:
    - 37
class: standard
---

## Research findings (See docs/pydantic-ai-integration-research.md §3.2)

PydanticAI has HistoryProcessor and OpenTelemetry instrumentation but NO general-purpose hook/event system. This is a genuine gap.

pydantic-deepagents implements two approaches: (1) middleware with 7 lifecycle hooks (before_run, after_run, before_model_request, before_tool_call, after_tool_call, on_tool_error, on_error) and (2) Claude Code-style hooks using subprocess commands with exit codes.

**Decision:** Build a simple HookRegistry as dict[HookEvent, list[Callable]]. Python callables only — no subprocess overhead (we're a Python project). Async-safe. Reference pydantic-deepagents but simpler.

**Prior art:**
- pydantic-deepagents middleware/hooks.py — HookEvent enum, HookInput/HookResult dataclasses
- pluggy (pytest) — too complex for our needs
- blinker (Flask) — signal-based, viable but adds dependency

## AC
Src: src/owlbear/core/hooks.py with HookRegistry class. HookEvent enum. register(event, handler), emit(event, data). Async-safe. Error isolation. Tests cover register, emit, ordering, error isolation.
