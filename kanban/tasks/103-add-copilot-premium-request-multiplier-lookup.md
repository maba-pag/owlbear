---
id: 103
title: Add Copilot premium request multiplier lookup
status: todo
priority: medium
created: 2026-02-27T03:20:56.6307896+01:00
updated: 2026-02-27T03:41:26.4101067+01:00
started: 2026-02-27T03:32:46.5189824+01:00
tags:
    - observability
    - auth
    - phase-3
depends_on:
    - 105
class: standard
---

Maintain a small model-to-multiplier dict for GitHub Copilot premium request tracking. Intentionally simple — a dict literal, not a config file or database.

## Acceptance Criteria

- [ ] `COPILOT_MULTIPLIERS: dict[str, float]` constant in `src/owlbear/providers/copilot.py` mapping model names to premium request multipliers
- [ ] Initial entries (sourced from GitHub Copilot public docs, Feb 2026):
  - gpt-4o -> 1.0
  - gpt-4o-mini -> 0.25
  - o1 -> 1.0
  - o1-mini -> 0.33
  - o3-mini -> 1.0
  - claude-3.5-sonnet -> 1.0
  - claude-3.7-sonnet -> 1.0
  (values are approximate — verify against current GitHub docs at implementation time)
- [ ] `get_premium_requests(model: str) -> float` function: looks up model in COPILOT_MULTIPLIERS, returns multiplier if found, defaults to 1.0 for unknown models
- [ ] Function handles model name variations: strips `openai:` or `copilot:` prefix if present before lookup
- [ ] Module-level docstring section explaining the multiplier dict and update cadence (quarterly manual check)

Depends on: #105 (test contracts written first — TDD)
See docs/token-usage-tracking-research.md section 3.4
