---
id: 213
title: 'ObservabilityHook: structured JSONL event logging'
status: archived
priority: important
created: 2026-02-28T01:11:08.6949975+01:00
updated: 2026-02-28T23:53:59.2428242+01:00
started: 2026-02-28T01:11:46.7311119+01:00
completed: 2026-02-28T23:53:59.2428242+01:00
tags:
    - phase-11
    - agent
    - config
    - analytics
class: standard
---

Implement ObservabilityHook with JSONL EventStore and aggregation helpers. Subsumes #142.

Files: src/owlbear/core/observability.py (new)

AC:
- [ ] ObservabilityEvent Pydantic model: timestamp, event_type, agent_name, tool_name, session_id, success, error, duration_ms, metadata
- [ ] EventStore class (same pattern as UsageTracker): append(event), load(), query(window), summary(window), tool_stats(window)
- [ ] ObservabilityHook class: registered on all 9 HookEvent types via register(hooks) method
- [ ] PRE_TOOL_USE starts timer (stored in dict by tool_name+context); POST_TOOL_USE computes duration_ms
- [ ] ON_ERROR events capture error type and message
- [ ] SESSION_START/SESSION_END events capture agent_name and session_id
- [ ] EventStore.summary(window) returns: total_tool_calls, error_count, avg_tool_duration_ms, tools_by_frequency: dict[str,int], agents_by_usage: dict[str,int]
- [ ] EventStore.tool_stats(window) returns per-tool: call_count, error_count, avg_duration_ms
- [ ] JSONL file path configurable (default: config_dir / 'events.jsonl')
- [ ] Zero new dependencies (stdlib logging + Pydantic only)
- [ ] Pattern follows NotificationHook.register() pattern for hook registration

Depends on: #229 (test task)
See docs/agent-observability-research.md, docs/agent-analytics-research.md
