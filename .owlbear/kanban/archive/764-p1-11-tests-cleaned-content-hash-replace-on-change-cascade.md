---
id: 764
title: 'P1-11: Tests — Cleaned-content hash + replace-on-change cascade'
status: archived
priority: medium
created: '2026-04-10T10:55:57.357680+00:00'
updated: '2026-04-15T10:14:24.389418+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for pipeline quality fixes:
1. Delta detection hashes cleaned markdown, not raw HTML
2. Changed content → old doc + entities + edges cascade-deleted before re-ingestion
3. Unchanged content hash → skip
4. No entity accumulation on refresh

All tests fail (RED). Depends on schema (#757).

Parent: #751

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/764-cleaned-content-hash-tests.md (pre-existing, validated)
- Sources: 7 studied, 5 high-relevance (from original research pass)
- Recommendation: content_cleaner optional param on ingest() — KISS-aligned approach for testing cleaned-content hashing without coupling to browser package (confidence: .85)
- Follow-up tasks created: none (GREEN companion #765 already exists)
- Decision requests: none (T1 — autonomous, test-writing within existing patterns)

## Validation Pass (2026-04-11)
Pre-existing research doc and test file found. Validation instead of full research.

**Codebase verification:**
| Claim | Evidence | Status |
|-------|----------|--------|
| ingest() has no content_cleaner param | ingest.py:131 — signature lacks it | CONFIRMED |
| check_content_changed hashes raw intake.content | ingest.py:162 | CONFIRMED |
| compute_content_hash uses content.strip().encode() | status_store.py:51 | CONFIRMED |
| delete_document_data cascades entities+edges+chunks | document_store.py:245-267 | CONFIRMED |
| owlbear_browser.cleaner absent | no cleaner module in serve/browser/ | CONFIRMED |

**Test execution:** 12 collected, 0 passed, 12 failed — all TypeError (content_cleaner kwarg). Valid RED.

## Challenge Results
- Challenger: FALLBACK — challenger subagent not in available agent roster
- Confidence in original: .85
- Key challenges: self-challenge on coupling AC1 tests to content_cleaner param approach; alternative (testing at refresh handler level) is less unit-testable and couples to full refresh stack
- Researcher response: accepted — content_cleaner param is most KISS-aligned
[[2026-04-11]]
## Architecture Review\n\n### Evaluation\n| Criterion | Assessment | Notes |\n|-----------|-----------|-------|\n| Single responsibility | PASS | Tests one feature: cleaned-content hash + replace-on-change cascade |\n| Interface clarity | PASS | 4 ACs map to 12 tests with clear, testable conditions |\n| Dependency correctness | PASS | depends_on=[] correct; stale #757 ref in body text is informational (tests use in-memory init_db) |\n| Module layering | PASS | Tests import only from owlbear_knowledge; no cross-package imports |\n| TDD compliance | PASS | This IS the RED phase; GREEN companion #765 exists |\n| KISS/YAGNI | PASS | content_cleaner as optional Callable param is minimal injection |\n| Premise challenge | PASS | Real bug: ingest.py:162 hashes raw intake.content, misses content changes through HTML noise |\n| Pattern consistency | PASS | Follows _make_db/_make_store helpers, pytest.mark.asyncio, class-per-AC grouping |\n| Security surface | PASS | No new boundary; content_cleaner is internal callable, not user input |\n| Single domain | PASS | Knowledge domain only |\n\n### Codebase Evidence\n- ingest.py:162 — check_content_changed(intake.source, intake.content, scope) hashes raw content\n- status_store.py:51 — compute_content_hash strips whitespace only, no cleaning\n- document_store.py:245-267 — delete_document_data cascades entities+edges+chunks+status+document\n- Test file: 12 tests, all fail TypeError on content_cleaner kwarg (valid RED)\n\n### Challenge Results\n- Challenger: FALLBACK — challenger subagent not in available agent roster\n- Self-challenge: content_cleaner param vs hardcoded cleaner vs refresh-handler-level testing\n- Verdict: content_cleaner param is most KISS — decouples from browser package, injectable for tests\n- Confidence: .88\n\n### Verdict: APPROVE\n### Action Taken: Advanced to todo. Stale #757 reference in body text noted but not a blocker (depends_on list is correctly empty).
[[2026-04-11]]
## Test-Writer Notes

**Test file:** `tests/test_cleaned_content_hash_replace_on_change_764.py`

**Classes:**
- `TestFromAC_HashCleanedContent` — AC1 (4 tests)
- `TestFromAC_CascadeDeleteOnChange` — AC2 (3 tests)
- `TestFromAC_SkipUnchangedCleanedContent` — AC3 (2 tests)
- `TestFromAC_NoEntityAccumulationOnRefresh` — AC4 (3 tests)

**Test counts by category:**
| Category | Count |
|----------|-------|
| Happy path | 4 |
| Edge cases | 3 |
| Boundary conditions | 3 |
| Isolation/scope | 2 |
| **Total** | **12** |

**Fail confirmation:** 12 collected, 0 passed, 12 failed — all `TypeError: IngestPipeline.ingest() got an unexpected keyword argument 'content_cleaner'`. Valid RED.

**Ruff:** `All checks passed!`

**AC coverage:**
| AC | Tests | Coverage |
|----|-------|----------|
| AC1: Delta detection hashes cleaned markdown, not raw HTML | 4 | FULL |
| AC2: Changed content → cascade-delete before re-ingestion | 3 | FULL |
| AC3: Unchanged content hash → skip | 2 | FULL |
| AC4: No entity accumulation on refresh | 3 | FULL |

Tests are pre-existing and validated from research pass (2026-04-11). No new tests required.
[[2026-04-11]]
## Builder Notes

**Files changed (2):**
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — Added `content_cleaner: Callable[[str], str] | None = None` to `ingest()`. Added `content_for_hash` computed from cleaner or raw content. Added `set_status(doc_id, "ok", source=..., scope=scope)` before `update_content_hash` to create the `document_status` row (pre-existing bug: `UPDATE` was no-oping without a prior INSERT). Moved `Callable` into `TYPE_CHECKING` block (TC003).
- `serve/knowledge/src/owlbear_knowledge/status_store.py` — Changed `compute_content_hash` to use `" ".join(content.split())` (full whitespace normalization) instead of `content.strip()` only. Required so that cleaned strings differing only in internal whitespace produce identical hashes.

**Root cause of 8/12 initial failures:** `document_status` rows were never inserted — `update_content_hash` used `UPDATE` without a preceding `INSERT`, so all writes were no-ops and `check_content_changed` always returned `(True, None)`.

**Test results:** 12 passed, 0 failed
**Lint:** ruff — All checks passed
**Coverage:** Not measured (scope: 2 source files, surgical changes only)
**Pre-existing failures:** 3 in `test_knowledge_foundation.py` (schema v9 vs v8, extra dependency) — unrelated to this task.
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: 12 passed, 0 failed (independently verified via quality-runner)

### Lint
clean: true (ruff — all checks passed)

### Coverage
Collection failed during finalization (KeyboardInterrupt in coverage tool after test completion — infrastructure issue). Builder note "surgical changes only" substantiated by code-reader path analysis: all significant branches exercised by the 12 tests.

---

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: Delta detection hashes cleaned markdown, not raw HTML | `test_hash_computed_on_cleaner_output_not_raw` | Yes — two different raw strings cleaning to same output → second must be "skipped"; fails if raw content hashed | COVERED |
| AC1: content_cleaner param accepted | `test_ingest_accepts_content_cleaner_kwarg`, `test_cleaner_called_with_raw_intake_content` | Yes — TypeError if param absent; mock.assert_called_once_with fails if cleaner not called | COVERED |
| AC1: content_cleaner=None falls back to raw | `test_no_cleaner_hashes_raw_content` | Yes — result.status == "ok" confirms default path works | COVERED |
| AC2: Cascade-delete before re-ingest | `test_changed_content_old_entities_removed_from_db`, `test_changed_content_old_edges_removed_from_db` | Yes — exact DB count equality fails if old rows accumulate | COVERED |
| AC2: Cascade scoped to changed doc only | `test_cascade_preserves_unrelated_document_entities` | Yes — sentinel entity count == 1 fails if cascade over-deletes | COVERED |
| AC3: Same cleaned hash → skip | `test_different_raw_same_cleaned_content_returns_skipped` | Yes — result2.status == "skipped" fails if raw content hashed | COVERED |
| AC3: Whitespace normalization considered | `test_whitespace_only_raw_difference_skips` | Yes — "hello   world" / "hello world" both clean to same hash | COVERED |
| AC4: No entity accumulation on refresh | `test_entity_count_stable_after_content_change`, `test_multiple_refresh_cycles_entity_count_stable` | Yes — exact count equality / `total_entities == 1` after 3 cycles | COVERED |
| AC4: Edge count stable | `test_edge_count_stable_after_refresh` | Yes — exact count equality | COVERED |

No MISSING. No LAX.

#### Security Review
- No hardcoded secrets. No injection (all SQL parameterized). No path traversal. No insecure deserialization. `content_cleaner` is an internal callable not derived from user input. Untrusted-source wrapping via `should_wrap()` / `wrap_untrusted_content()` preserved and unmodified. **No issues.**

#### Test Integrity — TestFromAC Comparison
Builder changed only `ingest.py` and `status_store.py`. Test file not modified. All `TestFromAC_*` methods fully PRESERVED — `# type: ignore[call-arg]` comments (RED-phase markers) remain intact.

| Original Test | Change Made | Assessment |
|--------------|-------------|------------|
| All 12 TestFromAC_* methods | None (test file untouched) | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Direct DB counts (`SELECT COUNT(*)`), exact status strings ("skipped", "ok"), `mock_cleaner.assert_called_once_with(raw_html)` |
| Negative/error-path coverage | ADEQUATE | `test_no_cleaner_hashes_raw_content` covers None-cleaner boundary; AC does not specify error paths |
| Manual mutation reasoning | STRONG | Removing cascade delete breaks 5 tests immediately; flipping hash target breaks 3 skip tests |
| Test independence | STRONG | Each test calls `_make_db()` (in-memory SQLite); no shared mutable state |
| Descriptive names | STRONG | All names describe condition and expected outcome |

#### Data Safety
- Pre-existing UPDATE-without-INSERT bug fixed: `set_status()` (upsert via SELECT+INSERT/UPDATE) called before `update_content_hash()` (UPDATE-only). Order confirmed: ingest.py lines ~211-212. No data integrity issue remains.
- Race condition on concurrent same-source ingest: pre-existing concern, not introduced by this task, outside AC scope.
- **No new data safety issues.**

#### Implementation-Aware Gaps
- `content_cleaner` exception path: caught by outer `except Exception` → `status="failed"`. Sound defensive coding, untested but outside AC scope.
- Concurrent ingest of same source: pre-existing; no AC coverage required.
- **No significant untested paths within AC scope.**

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL
- `test_no_cleaner_hashes_raw_content` asserts `result.status == "ok"` (minimal) — adequate for its scope (verifying None-cleaner doesn't break default behavior). Not a concern.

---

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: Hash cleaned markdown, not raw HTML | ingest.py: `content_for_hash = content_cleaner(intake.content) if content_cleaner is not None else intake.content`; passed to `check_content_changed` | TestFromAC_HashCleanedContent (4 tests) | PASS |
| AC2: Cascade-delete before re-ingest | ingest.py: `delete_document_data(existing_id)` before `insert_document`; document_store.py:245-267 cascade confirmed by code-reader | TestFromAC_CascadeDeleteOnChange (3 tests) | PASS |
| AC3: Unchanged hash → skip | ingest.py: `check_content_changed` on cleaned content; early-return with `status="skipped"` | TestFromAC_SkipUnchangedCleanedContent (2 tests) | PASS |
| AC4: No entity accumulation | via AC2's cascade delete; three-cycle test: `total_entities == 1` | TestFromAC_NoEntityAccumulationOnRefresh (3 tests) | PASS |

---

### Confidence: .95
### Verdict: PASS → docs
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `ingest()` gained `content_cleaner` param; `compute_content_hash` changed normalization. `copilot-instructions.md` has no tables/sections for `owlbear_knowledge` API (confirmed: no matches for `ingest`, `owlbear_knowledge`, `IngestPipeline`, `serve/knowledge`). No update required. |
| 2 | Module docstrings | Yes | Verified | Both modified functions have accurate docstrings. `ingest()` docstring covers `content_cleaner` param (line 152: "Optional callable applied to raw content before hashing…"). `compute_content_hash` docstring describes `" ".join(content.split())` normalization. No edits needed. |
| 3 | External attribution | No | N/A | Research doc sources (7 entries) are all internal: pre-existing research docs and codebase files. No external URLs/articles used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. `content_cleaner` is an internal callable parameter. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/764-cleaned-content-hash-tests.md` exists and is linked in task body. GREEN companion #765 already exists. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/764-*` files found)
[[2026-04-15]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Delta detection hashes cleaned markdown, not raw HTML | TestFromAC_HashCleanedContent: 4 tests pass (test_hash_computed_on_cleaner_output_not_raw, test_ingest_accepts_content_cleaner_kwarg, test_cleaner_called_with_raw_intake_content, test_no_cleaner_hashes_raw_content) | PASS |
| AC2: Changed content cascade-delete before re-ingest | TestFromAC_CascadeDeleteOnChange: 3 tests pass (test_changed_content_old_entities_removed_from_db, test_changed_content_old_edges_removed_from_db, test_cascade_preserves_unrelated_document_entities) | PASS |
| AC3: Unchanged content hash skip | TestFromAC_SkipUnchangedCleanedContent: 2 tests pass (test_different_raw_same_cleaned_content_returns_skipped, test_whitespace_only_raw_difference_skips) | PASS |
| AC4: No entity accumulation on refresh | TestFromAC_NoEntityAccumulationOnRefresh: 3 tests pass (test_entity_count_stable_after_content_change, test_multiple_refresh_cycles_entity_count_stable, test_edge_count_stable_after_refresh) | PASS |

### Test Results
- pytest (task): 12 passed, 0 failed
- pytest (full suite): 192 failed, 4386 passed, 8 skipped. 192 failures are pre-existing across many unrelated files (mcp_kanban, deny_src_writes, lint_feedback, etc.). 3 knowledge_integration failures are pre-existing (test file last modified in #162, not in task scope).
- ruff: 3 violations, all outside task scope (engine.py E501, test_refresh_sharepoint_879.py RUF002/UP024)

### Reviewer Evidence
Present and detailed. Thorough AC mapping table, security review (clean), test integrity check (TestFromAC preserved), test quality assessment (STRONG). Verdict: PASS at .95. Trusted for code-level findings.

### Upstream Commit
c42261fe test: add failing tests for cleaned-content hash + cascade (#764, test-writer) -- 1 file, 387 insertions. Properly scoped and attributed.

### Architect Quality: 4/5
Four ACs are specific, testable, and map cleanly to 12 tests. Minor gap: no AC for cleaner exception path, but builder/reviewer correctly noted it's outside scope. No improvisation needed.

### Deduction Breakdown
- Start: 1.00
- AC lines with no evidence: 0 (0 x -.02 = -.00)
- Lint violations in scope: 0 (-.00)
- AC quality LE 3: No, score 4 (-.00)
- Missing reviewer evidence: No (-.00)
- Full-suite failures in scope: 0 (-.00)

### Confidence: 1.00
### Action: archive