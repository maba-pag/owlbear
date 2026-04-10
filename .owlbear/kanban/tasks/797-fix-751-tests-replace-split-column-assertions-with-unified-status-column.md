---
id: 797
title: 'Fix #751 tests: replace split-column assertions with unified status column'
status: backlog
priority: needed
created: '2026-04-10T16:05:19.844611+00:00'
updated: '2026-04-10T16:05:19.844611+00:00'
tags:
- phase-1
- scope:knowledge
- schema
- type:test
parent: 751
depends_on:
- 757
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
The #751 builder commit `be9610a3` added `approval_state` + `extraction_status` columns to `source_pages` DDL and wrote tests asserting their existence. This deviates from the architect-approved #754 AC which specifies a unified `status` column with `PageStatus` StrEnum (DISCOVERED, APPROVED, REJECTED, INGESTED, STALE).

After #757 removes the split columns from the DDL (per refined AC), these two #751 tests will fail:

**Tests to fix in `tests/test_authenticated_content_pipeline_751.py`:**
1. `test_source_pages_has_approval_state_column` (L444) — replace with `test_source_pages_has_status_column` asserting `"status" in cols`
2. `test_source_pages_has_extraction_status_column` (L453) — delete (unified status replaces this; extraction state tracked via PageStatus.INGESTED/STALE)

**AC:**
- [ ] `test_source_pages_has_approval_state_column` replaced with `test_source_pages_has_status_column` that asserts `"status" in cols`
- [ ] `test_source_pages_has_extraction_status_column` removed
- [ ] All remaining tests in `test_authenticated_content_pipeline_751.py` still pass
- [ ] ruff clean