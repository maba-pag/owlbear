---
id: 567
title: 'Curator: write curation-report.json to data/memory/'
status: backlog
priority: important
created: 2026-04-03T10:25:09.2481537+02:00
updated: 2026-04-04T23:12:10.180384+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 530
class: standard
---

When curator completes a curation cycle, write a structured JSON report to data/memory/curation-report.json containing entry IDs with recommendations. Per docs/research/approve-memory-cli-wrapper.md 3C.

AC:
- [ ] Curator writes data/memory/curation-report.json after Step 5 (report)
- [ ] Format: array of {entry_id, content_preview, recommendation, reason}
- [ ] File is overwritten each cycle (latest report only)
- [ ] approve_memory CLI reads this file for recommendation display

## Research
Validation pass on existing research: docs/research/approve-memory-cli-wrapper.md section 3C.

Key findings:
- Consumer exists: approve.py _load_curation_report() reads data/memory/curation-report.json
- Supports two formats: top-level JSON array (preferred) and legacy dict
- Curator skill w-mem-curation Step 5 writes report to task body but NOT to JSON file
- data/memory/ directory exists as the standard memory data location
- Implementation: curator skill needs Step 5 addition to write JSON file after curation

Classification: T1 autonomous (add JSON output to existing curation workflow)
Confidence: .90
Follow-up tasks: none needed (this task IS the implementation)

[[2026-04-04]] Sat 23:12
Research complete (.90). T1 autonomous. Consumer exists in approve.py, curator skill needs JSON output step. See docs/research/approve-memory-cli-wrapper.md 3C.
