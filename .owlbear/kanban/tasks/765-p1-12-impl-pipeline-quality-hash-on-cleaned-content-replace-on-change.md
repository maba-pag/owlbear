---
id: 765
title: 'P1-12: Impl — Pipeline quality: hash on cleaned content + replace-on-change'
status: todo
priority: needed
created: '2026-04-10T10:55:57.388835+00:00'
updated: '2026-04-15T09:20:44.755911+00:00'
tags:
- phase-1
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Delta detection modified to hash cleaned text. Replace-on-change: cascade-delete old doc + entities + edges before re-ingestion.

All P1-11 tests pass.

Parent: #751

[[2026-04-12]]
## Research
- Research doc: .owlbear/research/765-pipeline-quality-hash-cleaned-content.md
- Sources: 7 studied, 5 high-relevance (.90+)
- Recommendation: `content_cleaner: Callable[[str], str] | None` param on `ingest()` (confidence: .88)
- Follow-up tasks created: none — implementation already delivered
- Decision requests: none

## Validation Pass (2026-04-12)
Existing research doc validated against current codebase. All claims confirmed:
- `content_cleaner` param exists on `ingest()` (ingest.py:144)
- `content_for_hash` computed before both hash operations (lines 177, 183, 250)
- Cascade-delete wired at line 193 via `delete_document_data()`
- All 12 RED-phase tests (#764) pass: 4 hash-cleaned, 3 cascade-delete, 2 skip-unchanged, 3 no-accumulation
- Tier: T1 — Autonomous (backward-compatible optional parameter)

## Challenge Results
- Challenger: FALLBACK — subagent not available
- Confidence in original: .88
- Self-challenge: chunker receives raw content (separate Phase 2 concern), ingest_text() excluded (no delta detection), clean() is sub-ms (no perf risk)
- Researcher response: accepted — no revisions needed
[[2026-04-15]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One param addition to `ingest()` with two hash call-site updates |
| Interface clarity | PASS | `content_cleaner: Callable[[str], str] | None` — clean type, docstring documents semantics, None preserves backward compat |
| Dependency correctness | PASS | RED-phase #764 is `done`; no other deps needed |
| Module layering | PASS | Callable injected from caller; no upward imports; StatusStore untouched |
| TDD compliance | PASS | RED-phase #764 provides 12 tests across 4 AC areas |
| KISS/YAGNI | PASS | ~5 LOC delta in ingest.py; no new modules, no new abstractions |
| Premise challenge | PASS | Cosmetic HTML change triggering re-ingestion is a real observed problem |
| Pattern consistency | PASS | Uses `Callable` under TYPE_CHECKING, consistent with existing codebase patterns |
| Security surface | PASS | No new system boundaries; content_cleaner is internal code, not user input |
| Single domain | PASS | Knowledge domain only |

### AC Clarification (for downstream agents)
The GREEN-phase AC is defined by the RED-phase test file (#764):
- AC1: `ingest()` accepts `content_cleaner` kwarg; hash is computed on cleaned output
- AC2: Changed content → cascade-delete old doc + entities + edges before re-ingestion
- AC3: Unchanged content hash → skip (even when raw HTML differs)
- AC4: No entity accumulation on refresh
All 12 tests in `test_cleaned_content_hash_replace_on_change_764.py` must pass.

### Challenge Results
- Challenger: FALLBACK — subagent not available
- Self-challenge: cleaner layer correct (ingest, not StatusStore), chunker raw-content is Phase 2, exception propagation handled by existing try/except, thread-safe (sync call before async work)
- Confidence: .90
- Architect response: accepted — no revisions

### Verdict: APPROVE
### Action Taken: Advanced #765 to todo. Architecture sound — minimal, backward-compatible `content_cleaner` injection. Implementation already in codebase per validation pass; downstream pipeline verifies.
