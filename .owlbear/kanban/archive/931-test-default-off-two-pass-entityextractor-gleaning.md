---
id: 931
title: Test default-off two-pass EntityExtractor gleaning flow
status: archived
priority: nice-to-have
created: 2026-03-21T23:58:38.5118938+01:00
updated: 2026-03-21T23:58:38.5118938+01:00
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

AC: add focused failing tests in tests/test_knowledge_extractor.py that prove EntityExtractor defaults to the current single-pass behavior, only runs a second pass when the gleaning constructor option is enabled, and returns the Pass 1 output unchanged when Pass 2 raises. Paired GREEN task: #917. Affected files: tests/test_knowledge_extractor.py, src/owlbear/memory/knowledge/extractor.py.
