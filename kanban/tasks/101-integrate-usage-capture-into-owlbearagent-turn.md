---
id: 101
title: Integrate usage capture into OwlBearAgent.turn()
status: archived
priority: high
created: 2026-02-27T03:20:41.1319025+01:00
updated: 2026-02-27T13:21:35.2024863+01:00
started: 2026-02-27T03:32:45.6636219+01:00
completed: 2026-02-27T13:21:35.2024863+01:00
tags:
    - observability
    - agent
    - phase-3
depends_on:
    - 100
    - 102
    - 103
class: standard
---

Capture result.usage() after Agent.run() and pass to UsageTracker. This is the wiring task — connects PydanticAI's usage API to the storage layer.

## Acceptance Criteria

- [ ] `OwlBearAgent.__init__()` accepts optional `tracker: UsageTracker | None = None` parameter
- [ ] After `result = await self.inner.run(...)` in `turn()`, extract `result.usage()` -> `RunUsage`
- [ ] Convert RunUsage to UsageRecord:
  - timestamp: datetime.now(UTC)
  - session_id: derived from session store path stem (e.g. 'abc' from 'abc.jsonl')
  - model_name: from `self.inner.model` or agent config
  - provider: from OwlBearSettings.provider
  - input_tokens, output_tokens, cache_read/write_tokens, requests, tool_calls: from RunUsage fields
  - estimated_cost_usd: call `calc_estimated_cost()` from #102 (import guarded, None if unavailable)
  - premium_requests: call `get_premium_requests()` from #103 if provider == 'copilot' (None otherwise)
- [ ] Call `tracker.append(record)` — wrapped in try/except that logs warning and continues (error-isolated, never fails the turn)
- [ ] When tracker is None, skip all usage capture (zero overhead)
- [ ] Existing unit tests in `tests/test_agent.py` remain green — tracker is optional, defaults to None
- [ ] No new dependencies beyond what #100, #102, #103 provide

Depends on: #100, #102, #103 (model, cost calc, and multipliers must exist)
See docs/token-usage-tracking-research.md section 3.5
