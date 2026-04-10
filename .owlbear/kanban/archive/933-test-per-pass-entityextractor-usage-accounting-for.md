---
id: 933
title: Test per-pass EntityExtractor usage accounting for gleaning benchmarks
status: archived
priority: nice-to-have
created: 2026-03-21T23:58:47.291406+01:00
updated: 2026-03-21T23:58:47.291406+01:00
tags:
    - scope:core
    - knowledge
    - benchmark
    - test
    - type:test
    - phase-research
parent: 907
depends_on:
    - 906
class: standard
---

AC: add focused failing tests in tests/test_usage_wiring.py that prove a gleaning-enabled EntityExtractor records separate UsageRecord entries for Pass 1 and Pass 2 with distinct operation labels when tracker and provider are supplied, and preserves the current no-op behavior when tracker or provider are absent. Paired GREEN task: #919. Affected files: tests/test_usage_wiring.py, src/owlbear/memory/knowledge/extractor.py, src/owlbear/memory/usage.py.
