---
id: 567
title: 'Curator: write curation-report.json to data/memory/'
status: ideation
priority: important
created: 2026-04-03T10:25:09.2481537+02:00
updated: 2026-04-03T10:25:09.2481537+02:00
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
