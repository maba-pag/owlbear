---
id: 551
title: 'Test: Bookmark pipeline orchestrator'
status: archived
priority: medium
created: 2026-04-02 16:05:55.090494+02:00
updated: 2026-04-02 17:27:42.203662+02:00
started: 2026-04-02 17:27:42.203662+02:00
completed: 2026-04-02 17:27:42.203662+02:00
tags:
- phase-1
- scope:knowledge
- type:test
- test
claimed_by: researcher
claimed_at: 2026-04-02 17:27:32.954163+02:00
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

[[2026-04-02]] Thu 17:27
## Research
**Finding: DUPLICATE â€” archive immediately**

#551 is identical to #552 (same title, same AC, same origin '#140 split'). #550 is also an identical duplicate.

- #552 is the canonical task: architect-approved, status 'todo', with Architecture Review section and challenge results
- #551 and #550 are orphan duplicates from the same #140 split that created #552
- The architect's #552 review already flagged: 'Duplicate tasks #550 and #551 (ideation, identical to #552) should also be cleaned up.'

**Board cleanup needed:**
- Archive #550 (duplicate of #552)
- Archive #551 (duplicate of #552)

Additionally, #136 (in-progress, unclaimed) has overlapping BookmarkPipeline scope with #552/#553. The #552 architect review noted this overlap and recommended the planner narrow #136 to RefreshOrchestrator + MCP tools only, or archive #136's BookmarkPipeline scope as superseded.

**No research document needed** â€” this is a dedup finding, not a research question.
**No follow-up tasks needed** â€” #552 is already the canonical task in 'todo'.
