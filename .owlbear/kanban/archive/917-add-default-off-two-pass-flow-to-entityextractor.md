---
id: 917
title: Add default-off two-pass flow to EntityExtractor
status: archived
priority: nice-to-have
created: 2026-03-21T15:57:47.4958911+01:00
updated: 2026-03-21T15:57:47.4958911+01:00
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

See docs/research/entity-extractor-gleaning-prototype.md §5. AC: add a constructor-level default-off gleaning option, keep the current single-pass path as the default, and return Pass 1 output when Pass 2 fails. Affected files: src/owlbear/memory/knowledge/extractor.py, tests/test_knowledge_extractor.py.
