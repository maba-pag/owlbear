---
id: 100
title: Create UsageRecord model and UsageTracker service
status: archived
priority: high
created: 2026-02-27T03:20:33.6510502+01:00
updated: 2026-02-27T13:21:34.7180432+01:00
started: 2026-02-27T03:32:45.2663588+01:00
completed: 2026-02-27T13:21:34.7180432+01:00
tags:
    - observability
    - agent
    - phase-3
depends_on:
    - 105
class: standard
---

Pydantic model for usage records + JSONL-based tracker service. Foundation for all usage tracking.

## Acceptance Criteria

- [ ] `UsageRecord` Pydantic BaseModel in `src/owlbear/memory/usage.py` with fields:
  - timestamp: datetime (UTC, default=now)
  - session_id: str
  - model_name: str
  - provider: str (e.g. 'copilot', 'openai')
  - input_tokens: int
  - output_tokens: int
  - cache_read_tokens: int (default=0)
  - cache_write_tokens: int (default=0)
  - total_tokens: computed property (input_tokens + output_tokens)
  - requests: int
  - tool_calls: int (default=0)
  - estimated_cost_usd: float | None (default=None — populated by #102)
  - premium_requests: float | None (default=None — populated by #103)
- [ ] `TypeAdapter[UsageRecord]` for JSON serialization/deserialization (same pattern as SessionStore's `_message_adapter`)
- [ ] `UsageSummary` Pydantic BaseModel with: total_input_tokens, total_output_tokens, total_tokens, total_requests, total_cost_usd (float | None), total_premium_requests (float | None), record_count: int, models: list[str] (unique model names seen)
- [ ] `UsageTracker` class with constructor `UsageTracker(path: Path)`
- [ ] `append(record: UsageRecord) -> None` — serialize record as JSON line, append to file (mkdir parents as needed)
- [ ] `load() -> list[UsageRecord]` — read all records from JSONL file, empty list if file missing
- [ ] `query(window: timedelta) -> list[UsageRecord]` — return records where timestamp >= (now - window)
- [ ] `summary(window: timedelta | None = None) -> UsageSummary` — aggregate records in window (None = all)
- [ ] Add `usage_path: Path` field to `OwlBearSettings` in `src/owlbear/config.py` with default `config_dir / usage.jsonl`
- [ ] Follow SessionStore pattern: TypeAdapter serialization, append-only JSONL, Path-based constructor

Depends on: #105 (test contracts written first — TDD)
See docs/token-usage-tracking-research.md sections 3.1, 3.3
