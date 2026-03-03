---
id: 403
title: 'Tests: SourceEvaluator with mocked PydanticAI agent'
status: archived
priority: important
created: 2026-03-01T20:18:10.0476153+01:00
updated: 2026-03-03T13:42:47.7018533+01:00
started: 2026-03-01T20:23:49.170812+01:00
completed: 2026-03-03T13:42:47.7018533+01:00
tags:
    - phase-13
    - test
    - knowledge-graph
class: standard
---

From #304 source-discovery-bookmarking-research.md. TDD with mocked PydanticAI agent. Test prompt construction, score thresholds, graceful failure when no project context. AC: Evaluator prompt includes content excerpt + project context; score thresholds respected; missing project gracefully handled (neutral score). Depends on #304.
