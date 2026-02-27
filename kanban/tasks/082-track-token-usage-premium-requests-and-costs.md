---
id: 82
title: Track token usage, premium requests, and costs
status: ideation
priority: medium
created: 2026-02-27T01:33:42.7518913+01:00
updated: 2026-02-27T01:33:42.7518913+01:00
tags:
    - ideation
    - observability
    - agent
class: standard
---

Display token usage stats for LLM interactions. When using GitHub Copilot, also show premium request consumption. Include cost estimates.

## Desired behavior
- Track input/output tokens per model per request
- When using GitHub Copilot: track premium request usage
- Show cost estimates (auto-detect pricing where possible, avoid manual config)
- Time windows: last hour, last 24 hours, last 7 days
- Zero-config ideal: infer costs from model name + provider (e.g. GitHub Copilot premium request pricing is public)

## Open questions
- Where to surface this? CLI command (bearclaw usage)? Dashboard? Both?
- Storage: append to session JSONL or separate usage log?
- PydanticAI exposes token usage in RunResult.usage() — leverage that
- GitHub Copilot premium request costs: can we scrape/hardcode the public pricing table?
