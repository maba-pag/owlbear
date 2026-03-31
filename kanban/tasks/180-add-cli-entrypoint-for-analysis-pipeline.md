---
id: 180
title: Add CLI entrypoint for analysis pipeline
status: backlog
priority: important
created: 2026-03-29T19:51:28.617595+02:00
updated: 2026-03-31T03:43:52.9639105+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
    - cli
depends_on:
    - 179
class: standard
---

Add python -m owlbear_orchestrator.analyze entrypoint:
- __main__.py in analysis/ package
- Args: --window (hours, default all), --format (json or markdown, default json), --audit-dir (default data/audit/)
- Reads audit JSONL, runs analyze(), prints output to stdout

AC:
- [ ] python -m owlbear_orchestrator.analyze runs analysis
- [ ] --window filters by time window
- [ ] --format json prints JSON array of proposals
- [ ] --format markdown prints formatted report
- [ ] Exit code 0 on success, 1 on error
- [ ] No proposals scenario prints empty array or 'No issues detected'

See docs/research/self-improvement-analysis-pipeline.md S3.5

[[2026-03-31]] Tue 03:43
## Research
Approach: argparse `__main__.py` with `_cli.py` helper (~35 LOC).
- `_cli.py`: `main(argv=None) -> int` with argparse, calls `analyze()` + formatters
- `__main__.py`: 3-line entrypoint per Python docs pattern
- No changes to existing `analyze()` or `cli.py`
- All window: pass large timedelta to avoid changing analyze() default
- Confidence: .85

See docs/research/cli-entrypoint-analysis-pipeline.md for full analysis.
