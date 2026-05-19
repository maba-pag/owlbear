---
id: 1005
title: Thread CancelSignal to enricher in _ingest_from_intake
status: archived
priority: nice-to-have
created: 2026-03-26 03:12:35.820301+01:00
updated: 2026-03-26 05:12:46.975872+01:00
tags:
- scope:core
- type:build
depends_on:
- 1006
class: standard
archival_reason: completed
archival_refs: []
---

Source: #999 research (docs/research/ingestpipeline-cancel-threading-to-enricher.md).

AC:

1. _ingest_from_intake passes cancel=cancel to enricher.schedule_graph_enrichment (ingest.py:287).
2. _ingest_from_intake passes cancel=cancel to enricher.schedule_inter_doc_enrichment (ingest.py:288).
3. When cancel is set, enricher schedule calls create no background tasks.
4. Callers that omit cancel continue to work unchanged.
5. Integration test: ingest with cancel set verifies enricher receives the signal.

[[2026-03-26]] Thu 05:12

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. cancel to schedule_graph_enrichment | Correct call site at ingest.py:287; enricher already accepts cancel kwarg | Line ref corrected from 288 to 287 |
| 2. cancel to schedule_inter_doc_enrichment | Correct call site at ingest.py:288; enricher already accepts cancel kwarg | Line ref corrected from 289 to 288 |
| 3. cancel set skips background tasks | Enricher already checks cancel.is_set() early-return; verifiable | OK |
| 4. Callers that omit cancel work unchanged | cancel defaults to None; no positional signature change | OK |
| 5. Integration test | Covered by RED test task #1006 and AC-5 | OK |

### Architecture Notes

- Trivial two-kwarg threading. cancel already flows into _ingest_from_intake (ingest.py:252) and is used at_run_extract (line 269). This extends the same pattern to the enricher calls.
- Both schedule_graph_enrichment and schedule_inter_doc_enrichment (enrichment.py:72, 99) accept cancel: CancelSignal or None = None keyword-only. No signature changes needed.
- Module layering: change is within ingest.py calling enrichment.py (same layer, knowledge subpackage). No layer violations.
- Pattern consistency: follows cancel=cancel threading already established in _run_extract call.

### Changes Made

- Corrected AC line references from 288/289 to 287/288 (verified against HEAD)
- Added depends_on: #1006 (test task)
- Created #1006 (Test: Thread CancelSignal to enricher in _ingest_from_intake) at todo

### Dependencies

- Added: #1006 (RED test task, preceding TDD requirement)
- Verified: #999 (research) complete, doc exists
- Verified: #997 (enricher-side cancel support) archived
