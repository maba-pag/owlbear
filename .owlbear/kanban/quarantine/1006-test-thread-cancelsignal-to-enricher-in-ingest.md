---
id: 1006
title: 'Test: Thread CancelSignal to enricher in _ingest_from_intake'
status: archived
priority: nice-to-have
created: 2026-03-26 05:11:10.707583+01:00
updated: 2026-03-26 06:01:26.099284+01:00
tags:
- scope:core
- type:test
class: standard
archival_reason: completed
archival_refs: []
---

RED-phase tests for #1005. Verify _ingest_from_intake threads cancel to enricher.
AC:

1. Test that _ingest_from_intake passes cancel kwarg to schedule_graph_enrichment (mock enricher, assert cancel=cancel in call args).
2. Test that _ingest_from_intake passes cancel kwarg to schedule_inter_doc_enrichment (same pattern).
3. Test that when cancel is None (default), enricher schedule calls receive cancel=None.
4. All tests FAIL on current HEAD (RED contract).
