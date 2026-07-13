---
id: 550
title: 'Test: Bookmark pipeline orchestrator'
status: archived
priority: medium
created: 2026-04-02 16:05:37.065781+02:00
updated: 2026-04-04 07:10:01.344187+02:00
started: 2026-04-04 07:09:35.801256+02:00
completed: 2026-04-04 07:09:35.801256+02:00
tags:
- phase-1
- scope:knowledge
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
TDD RED phase: write failing tests for the BookmarkPipeline orchestrator module.

## Acceptance Criteria
- [ ] Test file: tests/test_bookmark_pipeline.py
- [ ] TestFromAC_ classes covering all AC lines from the implementation task
- [ ] Test BookmarkResult model: frozen, all fields (url, bookmark, evaluation, ingested, skipped_reason) with correct types and defaults
- [ ] Test BookmarkPipeline constructor: accepts bookmark_store, evaluator, ingest_pipeline (optional), web_read_fn (optional), ingest_threshold (default 0.7)
- [ ] Test process() dedup: returns early with skipped_reason when BookmarkStore.get_by_url returns existing bookmark
- [ ] Test process() extraction failure: broad exception from web_read_fn returns BookmarkResult with skipped_reason
- [ ] Test process() evaluation: calls SourceEvaluator.evaluate with content and project_context
- [ ] Test process() conditional ingest: triggers when ingest_pipeline is not None AND content truthy AND relevance_score >= threshold AND worth_ingesting; skips otherwise
- [ ] Test process() bookmark creation: creates Bookmark with title from evaluation.summary[:120], tags, relevance_score, reason, scope, document_id
- [ ] Test process() cancel signal: checked between stages, returns partial results
- [ ] Test process() no web_read_fn: graceful handling when web_read_fn is None
- [ ] All tests FAIL (RED phase)
- [ ] ruff check passes

## Context
Test task for bookmark pipeline extraction. Split from #140.

[[2026-04-02]] Thu 17:32
## Research
Duplicate of #552 (identical AC, same title). #552 is already at todo (architect-approved on 2026-04-02). Architect review on #552 explicitly flagged #550 as a duplicate to clean up. Recommend archiving #550 as superseded.
