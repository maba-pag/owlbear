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

M1: Tests assert exact substrings in agent system prompts. Any prompt rewording breaks them. Better: test for tool names in tool list, or use regex for semantic intent. AC: prompt tests resilient to rewording. See docs/test-quality-audit.md.

Research complete -- see docs/brittle-prompt-assertions-research.md. Findings: 30+ prompt assertions across 8 test files; only 2 files need changes (test_kanban_pipeline.py, test_source_evaluator.py). Follow-up: 2 implementation tasks.
