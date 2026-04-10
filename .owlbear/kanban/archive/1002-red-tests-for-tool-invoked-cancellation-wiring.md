---
id: 1002
title: RED tests for tool-invoked cancellation wiring
status: archived
priority: nice-to-have
created: 2026-03-25T04:41:44.0812204+01:00
updated: 2026-03-25T06:12:34.16749+01:00
tags:
    - scope:core
    - type:test
depends_on:
    - 1001
    - 870
class: standard
---

**Source:** #877 research (docs/research/tool-invoked-cancellation.md)

**AC:**
1. CancelSlot unit tests: is_set returns False when unlinked, True when linked source is set.
2. KnowledgeToolset._ingest_document passes cancel to pipeline.ingest/ingest_text.
3. KnowledgeSourceToolset._refresh_source passes cancel to orchestrator.refresh.
4. BookmarkToolset._bookmark_source passes cancel to pipeline.process.
5. Integration: BootstrapResult exposes cancel slot; run_daemon wires it to shutdown_event.
6. All tests fail before implementation (RED phase).
