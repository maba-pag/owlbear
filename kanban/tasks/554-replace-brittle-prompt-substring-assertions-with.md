---
id: 554
title: Replace brittle prompt substring assertions with semantic checks
status: backlog
priority: nice-to-have
created: 2026-03-04T07:38:56.8370984+01:00
updated: 2026-03-07T01:09:50.0290943+01:00
started: 2026-03-07T01:05:38.6153764+01:00
tags:
    - audit
    - test
class: standard
---

M1: Tests assert exact substrings in agent system prompts. Any prompt rewording breaks them. Better: test for tool names in tool list, or use regex for semantic intent. See docs/test-quality-audit.md.

Research complete -- see docs/research/brittle-prompt-assertions.md. Findings: 30+ prompt assertions across 8 test files; only 2 files need changes (test_kanban_pipeline.py, test_source_evaluator.py). Follow-up: 2 implementation tasks.

## AC

- [x] Research doc at docs/research/brittle-prompt-assertions.md
- [x] Audited 30+ prompt assertions across 8 test files
- [x] Identified 2 files needing changes (test_kanban_pipeline.py, test_source_evaluator.py)
- [x] Follow-up implementation tasks created
