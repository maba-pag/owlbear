---
id: 179
title: Implement analysis module with pattern detectors
status: ideation
priority: needed
created: 2026-03-29T19:51:21.7412918+02:00
updated: 2026-03-29T19:51:21.7412918+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 21
class: standard
---

Create packages/orchestrator/src/owlbear_orchestrator/analysis/ with:
- models.py: AnalysisProposal frozen Pydantic model (target_agent, category, pattern, rationale, evidence, suggested_action)
- detectors.py: four pattern detectors (high_error_rate, slow_agent, repeated_failure, stale_dispatch)
- analyze.py: analyze(audit_dir: Path, window: timedelta or None) entrypoint consuming audit log JSONL
- formatters.py: JSON and markdown output formatters

AC:
- [ ] AnalysisProposal Pydantic model with 6 fields
- [ ] analyze() reads DispatchEvent + CompletionEvent from audit JSONL files
- [ ] High error rate detector: >= 40% failure, >= 3 dispatches per agent
- [ ] Slow agent detector: avg duration > 2x global avg, >= 3 dispatches
- [ ] Repeated failure detector: >= 2 failures on same task_id
- [ ] Stale dispatch detector: dispatch with no completion > 1h
- [ ] JSON output (default): serialized list of proposals
- [ ] Markdown output (flag): formatted report with tables
- [ ] No side effects, no file writes, no autonomous mutation
- [ ] Unit tests with synthetic JSONL fixtures
- [ ] Depends on #21 audit log Pydantic models

See docs/research/self-improvement-analysis-pipeline.md
