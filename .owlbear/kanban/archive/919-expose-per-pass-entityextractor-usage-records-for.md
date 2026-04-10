---
id: 919
title: Expose per-pass EntityExtractor usage records for gleaning benchmarks
status: archived
priority: nice-to-have
created: 2026-03-21T15:57:48.7311696+01:00
updated: 2026-03-21T15:57:48.7311696+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - type:build
    - phase-research
parent: 907
depends_on:
    - 906
class: standard
---

See docs/research/entity-extractor-gleaning-prototype.md §5. AC: when a tracker/provider are supplied, record Pass 1 and Pass 2 separately so #908 can compare token and estimated-cost deltas, and cover the behavior in focused tests. Affected files: src/owlbear/memory/knowledge/extractor.py, tests/test_usage_wiring.py, tests/benchmarks/.
