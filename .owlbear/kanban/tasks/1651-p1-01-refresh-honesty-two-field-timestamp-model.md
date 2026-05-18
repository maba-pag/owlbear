---
id: 1651
title: 'P1-01: Refresh honesty — two-field timestamp model'
status: backlog
priority: critical
created: 2026-05-18T03:11:06.841802+02:00
updated: 2026-05-18T03:18:51.102121+02:00
tags:
  - scope:knowledge
  - knowledge
parent: 1650
depends_on: []
ac:
  - 'AC-1: `KnowledgeSource` model has `last_checked_at: str | None = None` field;
    schema migration (v13→v14) adds `last_checked_at TEXT` column to `knowledge_sources`
    table; `KnowledgeSourceStore` reads and writes the field in `_SELECT_COLS`, `_row_to_model`,
    `create`, and `update` paths'
  - "AC-2: `_update_source_record` given `RefreshResult` with `refreshed > 0` or `partial
    > 0` bumps both `last_checked_at` and `last_refreshed_at` to current UTC time;
    sets `last_error` from `errors + warnings` joined by '; ' if non-empty, clears
    to `None` otherwise"
  - 'AC-3: `_update_source_record` given `RefreshResult` with only `skipped > 0` or
    `failed > 0` (zero refreshed and partial) bumps `last_checked_at` to current UTC
    time and preserves existing `last_refreshed_at`; sets `last_error` from `errors`
    list if `failed > 0`, clears to `None` if only skipped'
  - 'AC-4: `_update_source_record` given `RefreshResult` with all counters zero preserves
    existing `last_checked_at`, `last_refreshed_at`, and `last_error` unchanged'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1650

## Scope

**In-scope:** Add `last_checked_at` field to `KnowledgeSource` model, schema, store; fix `_update_source_record` conditional logic per brief truth table.

**Out-of-scope:** Exposing health fields in MCP response (O1, separate task). Source removal (O4). Direct-ingest retype (O3).

## Context

Current `_update_source_record` unconditionally bumps `last_refreshed_at` to `now` regardless of whether content was actually acquired. The two-field model separates "system checked" (`last_checked_at`) from "content arrived" (`last_refreshed_at`).

`RefreshResult` fields: `source_id`, `refreshed`, `partial`, `skipped`, `failed`, `errors: list[str]`, `warnings: list[str]`.

Current schema version: 13. Migration target: 14.

[[2026-05-18T03:18:20+02:00]]
## Research
- Research doc: .owlbear/research/refresh-honesty-two-field-timestamps.md
- Sources: 7 studied, 6 high-relevance
- Recommendation: proceed with implementation as designed in brief (confidence: 0.92)
- Follow-up tasks created: none (this task IS the implementation task)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — no multi-option recommendation; brief decisions already settled design (D3)
- Confidence in original: 0.92
- Key challenges: column ordering risk in source_store.py (mitigated by appending at position 13)
- Researcher response: N/A — validation research, not option selection

[[2026-05-18T03:18:51+02:00]]
## Research
- Research doc: .owlbear/research/refresh-honesty-two-field-timestamps.md
- Sources: 7 studied (6 high-relevance) — codebase analysis of models.py, source_store.py, schema.py, refresh.py; brief + data stance; RFC 9110 §8.8.2 prior art
- Recommendation: proceed with implementation as designed in brief (confidence: 0.92)
- Follow-up tasks: none — this task IS the implementation task with full AC
- Decision requests: none
- Tier: T1 (bug fix)

## Key Findings
1. Bug confirmed: `_update_source_record` unconditionally bumps `last_refreshed_at` (refresh.py L435–452)
2. Implementation touches 4 files: models.py (add field), schema.py (v13→v14 migration), source_store.py (4 mechanical edits to CRUD), refresh.py (4-branch conditional)
3. Column ordering risk: `last_checked_at` must be appended at position 13 in SELECT to avoid shifting existing row indices
4. Upstream contamination (`_record_ingest_outcome` status aliasing) is a pre-existing bug, explicitly out of scope per brief
5. 13 prior migrations establish clear pattern for v14

## Challenge Results
- Challenger: FALLBACK — no multi-option recommendation; brief decisions already settled design (D3)
- Confidence in original: 0.92
