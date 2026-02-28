---
id: 212
title: Add temporal decay settings to OwlBearSettings
status: archived
priority: nice-to-have
created: 2026-02-28T01:10:58.388759+01:00
updated: 2026-02-28T23:53:58.3711638+01:00
started: 2026-02-28T01:11:46.2111661+01:00
completed: 2026-02-28T23:53:58.3711638+01:00
tags:
    - phase-9
    - memory
    - config
class: standard
---

Add temporal decay configuration fields to OwlBearSettings.

File: src/owlbear/config.py

AC:
- [ ] temporal_decay_rate: float = 0.001 (29-day half-life)
- [ ] temporal_recency_weight: float = 0.1 (similarity dominates, recency is tiebreaker)
- [ ] Fields under a '--- Temporal memory ---' comment section
- [ ] Env var overrides: OWLBEAR_TEMPORAL_DECAY_RATE, OWLBEAR_TEMPORAL_RECENCY_WEIGHT
- [ ] No validation beyond float type (pydantic handles it)

Depends on: #224 (test task), #207
See docs/temporal-memory-research.md
