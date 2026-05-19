---
id: 997
title: Add shutdown drain and CancelSignal to GraphEnricher
status: archived
priority: nice-to-have
created: 2026-03-25T04:36:33.6185662+01:00
updated: 2026-03-25T05:56:09.1736801+01:00
started: 2026-03-25T05:56:09.1736801+01:00
completed: 2026-03-25T05:56:09.1736801+01:00
tags:
    - scope:core
    - type:build
depends_on:
    - 870
class: standard
---

[[2026-03-25]] Wed 04:37
Source: #871 research (docs/research/graphenricher-cancellation-draining.md). Depends on: #870 (done).

AC:

1. Add _shutdown bool flag to GraphEnricher.__init__.
2. schedule_graph_enrichment and schedule_inter_doc_enrichment accept optional cancel: CancelSignal parameter; return early when_shutdown is True or cancel.is_set().
3. Add async shutdown() that sets _shutdown, cancels all tracked tasks, gathers with return_exceptions=True, leaves _background_tasks empty.
4. Add async drain() that sets _shutdown, awaits all tracked tasks without cancelling.
5. Subsequent schedule calls are no-ops after shutdown() or drain().
6. Preserve existing _background_tasks bookkeeping and _bg_semaphore concurrency.
