---
id: 285
title: Test IntraDocGraphBuilder -- cross-chunk inference with mocked agent
status: archived
priority: needed
created: 2026-02-28T22:57:57.3184607+01:00
updated: 2026-03-01T17:07:59.5623181+01:00
started: 2026-02-28T23:12:24.0137928+01:00
completed: 2026-03-01T17:07:59.5623181+01:00
tags:
    - phase-9
    - knowledge-graph
    - agent
    - test
class: standard
---

TDD tests for IntraDocGraphBuilder.
AC:
- [ ] Test with 0, 1, 2, 20 entities (boundary cases)
- [ ] Test entity-type batching triggers above 80 entities
- [ ] Test edges get weight=0.5 and correct metadata tagging
- [ ] Test LLM failure produces empty result (no crash)
- [ ] Mock PydanticAI agent (no real LLM calls)
- [ ] Test scope passthrough
See docs/research/intra-document-graph.md
