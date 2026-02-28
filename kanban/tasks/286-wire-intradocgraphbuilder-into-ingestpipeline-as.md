---
id: 286
title: Wire IntraDocGraphBuilder into IngestPipeline as post-ingestion hook
status: todo
priority: important
created: 2026-02-28T22:58:05.958293+01:00
updated: 2026-02-28T23:12:24.5037987+01:00
started: 2026-02-28T23:12:24.5037987+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 284
    - 285
class: standard
---

After IngestPipeline completes, queue IntraDocGraphBuilder for the document.
AC:
- [ ] IngestPipeline triggers graph builder after successful ingestion
- [ ] Runs as asyncio.create_task (non-blocking)
- [ ] document_status updated to graph_enriched on completion
- [ ] Skips if document already enriched (idempotent)
- [ ] Test integration with mocked builder
Depends on #284, #285
See docs/intra-document-graph-research.md
