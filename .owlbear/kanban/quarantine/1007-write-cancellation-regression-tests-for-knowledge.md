---
id: 1007
title: Write cancellation regression tests for knowledge pipelines
status: archived
priority: nice-to-have
created: 2026-03-26 11:43:08.395742+01:00
updated: 2026-03-26 11:43:18.357417+01:00
tags:
- scope:core
- type:test
depends_on:
- 1006
class: standard
archival_reason: completed
archival_refs: []
---

[[2026-03-26]] Thu 11:43
Source: #872 research (docs/research/cancellation-regression-coverage.md).
Depends on: #1006 (cancel threading to enricher).

AC:

1. Test refresh_all with cancel pre-set returns zero results (G1).
2. Test _ingest_from_intake gather interaction when cancel fires mid-extraction: partial extraction result preserved, CancelledError from_run_extract re-raised through gather, document status consistent (G2, G5).
3. Test LinkedCancelSignal(op_event, shutdown_event) through a pipeline call: setting shutdown_event mid-operation stops processing; verify BookmarkPipeline._ingest_text threads cancel to IngestPipeline.ingest_text (G3, G4).
4. Test cancel mid-ingest followed by enricher.shutdown: enricher._background_tasks is empty, no orphaned tasks remain (G6).
5. All tests in a single file tests/test_cancellation_regression.py, max ~200 lines.
