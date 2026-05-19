---
id: 752
title: Add budget threshold to UsageTracker
status: archived
priority: needed
created: 2026-03-12T10:49:12.867734+01:00
updated: 2026-03-12T10:50:25.2501681+01:00
started: 2026-03-12T10:50:25.2501681+01:00
completed: 2026-03-12T10:50:25.2501681+01:00
tags:
    - phase-4
    - config
    - agent
    - scope:core
class: standard
---

## Acceptance Criteria

- [ ] Add `budget_limit_usd: float | None` field to OwlBearSettings (default: None = unlimited)
- [ ] Add field_validator: budget_limit_usd > 0 when not None
- [ ] OwlBearAgent._record_usage() checks cumulative cost via tracker.summary().total_cost_usd against settings.budget_limit_usd after each append
- [ ] At >= 80% of limit: emit HookEvent.BUDGET_WARNING via ObservabilityHook (add event to enum)
- [ ] At >= 100% of limit: raise BudgetExceededError (new exception in owlbear.errors or core module)
- [ ] poll_tick catches BudgetExceededError and blocks the task with reason string
- [ ] When budget_limit_usd is None, no checks are performed (zero overhead path)
- [ ] Unit tests for: 0% (no warning), 80% (warning emitted), 100% (error raised), None (no check)

## Architecture Notes

- Check goes in OwlBearAgent._record_usage() NOT in UsageTracker (tracker is a store, agent is the consumer)
- summary() method already exists with total_cost_usd aggregation - reuse it
- BudgetExceededError should be a subclass of OwlBearError for consistent error taxonomy
- HookEvent.BUDGET_WARNING is a new event constant

## References

- Paperclip budget model: docs/api/costs.md
- Research: docs/research/paperclip.md
- Existing: src/owlbear/memory/usage.py, src/owlbear/core/agent.py L160-211
