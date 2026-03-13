---
id: 102
title: Add genai-prices dependency and cost calculation wrapper
status: archived
priority: medium
created: 2026-02-27T03:20:48.9650458+01:00
updated: 2026-02-27T13:21:35.6929381+01:00
started: 2026-02-27T03:32:46.077463+01:00
completed: 2026-02-27T13:21:35.6929381+01:00
tags:
    - observability
    - config
    - phase-3
depends_on:
    - 105
class: standard
---

Add genai-prices as a hard dependency and create a thin cost calculation wrapper. Hard dep rationale: lightweight (~26KB data), already in PydanticAI ecosystem (RequestUsage.extract() uses it), cost estimation is a core feature not optional.

## Acceptance Criteria

- [ ] Add `genai-prices` to `pyproject.toml` `dependencies` list (hard dependency, not optional)
- [ ] Run `uv sync` to verify installation
- [ ] Create `calc_estimated_cost(model: str, provider: str, input_tokens: int, output_tokens: int) -> float | None` in `src/owlbear/providers/pricing.py`
- [ ] Uses `genai_prices.calc_price()` or PydanticAI's `RequestUsage.extract()` internally
- [ ] Returns None when model/provider not found in price DB (graceful fallback)
- [ ] Logs warning via `logging.getLogger(__name__)` on missing price data, never raises exceptions
- [ ] Module-level docstring explaining purpose and fallback behavior
- [ ] Follows project patterns: `from __future__ import annotations`, type hints on all signatures

Depends on: #105 (test contracts written first — TDD)
See docs/research/token-usage-tracking.md section 3.2
