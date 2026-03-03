---
id: 399
title: SourceEvaluator — LLM-based relevance scoring
status: archived
priority: needed
created: 2026-03-01T20:17:32.6884985+01:00
updated: 2026-03-03T13:42:40.1672051+01:00
started: 2026-03-01T20:23:42.9159718+01:00
completed: 2026-03-03T13:42:40.1672051+01:00
tags:
    - phase-13
    - knowledge-graph
    - agent
class: standard
---

From #304 source-discovery-bookmarking-research.md. PydanticAI agent with EvaluationResult structured output (relevance_score 0-1, tags, summary, worth_ingesting). Prompt takes content excerpt (first 2000 chars) + project context (name, description, goals). Scores relevance to current project. AC: Evaluator returns structured EvaluationResult; project-aware scoring; graceful fallback when no active project (score=0.5). Depends on #304.
