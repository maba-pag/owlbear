---
id: 105
title: Tests for usage tracking system
status: todo
priority: high
created: 2026-02-27T03:21:12.8067194+01:00
updated: 2026-02-27T03:40:06.7150429+01:00
started: 2026-02-27T03:32:47.3980287+01:00
tags:
    - observability
    - test
    - phase-3
class: standard
---

Write test files first (TDD) — these define the contracts for all usage tracking modules. No dependencies — tests are written before any implementation.

## Acceptance Criteria

- [ ] `tests/test_usage_record.py`: UsageRecord construction with all fields, `TypeAdapter[UsageRecord]` JSON serialization roundtrip, optional fields (estimated_cost_usd, premium_requests) default to None, total_tokens computed property equals input_tokens + output_tokens
- [ ] `tests/test_usage_tracker.py`: UsageTracker(path).append(record) writes one JSONL line, load() returns list[UsageRecord], query(timedelta) filters records by timestamp window, summary(timedelta) returns UsageSummary with correct totals, empty/missing file returns empty list
- [ ] `tests/test_usage_cost.py`: calc_estimated_cost() with known model (gpt-4o/openai) returns positive float, unknown model/provider returns None, function never raises (logs warning on error)
- [ ] `tests/test_copilot_multipliers.py`: get_premium_requests('gpt-4o') returns 1.0, unknown model defaults to 1.0, known reasoning model returns multiplier > 1.0
- [ ] `tests/test_usage_integration.py`: OwlBearAgent.turn() calls tracker.append() when UsageTracker provided, skips gracefully when tracker is None, tracker error does not propagate to caller (error-isolated)
- [ ] `tests/test_usage_cli.py`: `bearclaw usage` command registered on app, mock JSONL data produces correct tabular output, time-window flags filter correctly, empty log prints informative message (not error/traceback)
- [ ] All tests use mock data (MockRunUsage, mock JSONL files via tmp_path), no live API calls
- [ ] Each test file imports from the target module path (e.g., `from owlbear.memory.usage import UsageRecord`) — these imports will fail until implementation tasks are done (red phase)

See docs/token-usage-tracking-research.md for data model and API contracts.
