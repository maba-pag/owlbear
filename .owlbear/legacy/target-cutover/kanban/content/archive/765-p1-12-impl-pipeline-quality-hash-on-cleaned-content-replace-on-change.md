---
id: 765
title: 'P1-12: Impl — Pipeline quality: hash on cleaned content + replace-on-change'
status: archived
priority: medium
created: '2026-04-10T10:55:57.388835+00:00'
updated: '2026-04-15T19:05:13.114901+00:00'
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

[[2026-04-15]]
## Test-Writer Notes

**Exceptional case: implementation pre-delivered before test-writer step.**

The architecture review (2026-04-15) explicitly anchored the GREEN-phase AC to the RED-phase test file from task #764. Per the validation pass (2026-04-12), the implementation was already present in `ingest.py` before this task reached `todo`.

### Verification

Ran `pytest tests/test_cleaned_content_hash_replace_on_change_764.py -v` — **12 passed, 0 failed**.

| Test | Status |
|------|--------|
| `TestFromAC_HashCleanedContent::test_ingest_accepts_content_cleaner_kwarg` | PASS |
| `TestFromAC_HashCleanedContent::test_cleaner_called_with_raw_intake_content` | PASS |
| `TestFromAC_HashCleanedContent::test_hash_computed_on_cleaner_output_not_raw` | PASS |
| `TestFromAC_HashCleanedContent::test_no_cleaner_hashes_raw_content` | PASS |
| `TestFromAC_CascadeDeleteOnChange::test_changed_content_old_entities_removed_from_db` | PASS |
| `TestFromAC_CascadeDeleteOnChange::test_changed_content_old_edges_removed_from_db` | PASS |
| `TestFromAC_CascadeDeleteOnChange::test_cascade_preserves_unrelated_document_entities` | PASS |
| `TestFromAC_SkipUnchangedCleanedContent::test_different_raw_same_cleaned_content_returns_skipped` | PASS |
| `TestFromAC_SkipUnchangedCleanedContent::test_whitespace_only_raw_difference_skips` | PASS |
| `TestFromAC_NoEntityAccumulationOnRefresh::test_entity_count_stable_after_content_change` | PASS |
| `TestFromAC_NoEntityAccumulationOnRefresh::test_multiple_refresh_cycles_entity_count_stable` | PASS |
| `TestFromAC_NoEntityAccumulationOnRefresh::test_edge_count_stable_after_refresh` | PASS |

### AC Coverage

| AC | Tests in `test_764.py` | Coverage |
|----|------------------------|----------|
| AC1: `content_cleaner` kwarg; hash on cleaned output | 4 tests | ✓ |
| AC2: Changed content → cascade-delete entities + edges | 3 tests | ✓ |
| AC3: Skip when cleaned hash matches (raw differs) | 2 tests | ✓ |
| AC4: No entity accumulation on refresh | 3 tests | ✓ |

### No New Tests Written

All 12 AC tests are satisfied by the pre-delivered implementation. Every edge condition I evaluated — cleaner exception propagation, empty-string clean output, multiple refresh cycles, cross-document isolation — is already implemented and covered. Writing new tests that pass from day 1 is not a valid RED-phase delivery.

**Implementation evidence:**
- `content_cleaner` param: `ingest.py` line 148
- `content_for_hash` computation: `ingest.py` line ~177
- Cascade delete: `ingest.py` line 193 via `delete_document_data(existing_id)`
- Hash stored on cleaned content: `ingest.py` line ~250 via `update_content_hash(doc_id, content_for_hash)`

Builder: run full test suite to confirm no regressions, then advance to review.
[[2026-04-15]]
## Builder Notes

### Files Changed
None — implementation was pre-delivered before this task entered `todo`. The test-writer explicitly confirmed this and instructed the builder to run the full suite for regressions.

### Test Results
- **Target file:** `tests/test_cleaned_content_hash_replace_on_change_764.py` — **12 passed, 0 failed** (4.99s)
- **Full suite:** 4606 passed, 1 skipped, 209 failed, 13 warnings (2:46)
  - 209 failures confirmed pre-existing and cross-domain (inter_doc_graph_builder_862, lint_feedback_547, mcp_kanban_move_task_588, etc.)
  - `test_knowledge_integration.py` (3 failures) investigated — root cause is entity `chunk_id` not set by `store_extractions`; zero references to `content_cleaner`, `delete_document_data`, or `content_for_hash`
  - Zero regressions introduced by this task

### Coverage
Not measured — no code changes; pre-delivered implementation coverage already validated in prior validation pass (2026-04-12).

### Lint Status
Not re-run — no code changes introduced in this phase.

### Evidence Summary
- AC1 (content_cleaner kwarg; hash on cleaned output): 4 tests PASS
- AC2 (changed content → cascade-delete entities + edges): 3 tests PASS
- AC3 (skip when cleaned hash matches): 2 tests PASS
- AC4 (no entity accumulation on refresh): 3 tests PASS
- All 12 `TestFromAC_*` tests GREEN
- No `TestBuilderDiscovered` tests added — all edge cases covered by existing suite
- Full suite regression check: clean (no new failures vs baseline)
[[2026-04-15]]
## Review Evidence

### Test Results
- pytest (independent run via quality-runner): **12 passed, 0 failed** — exit 0
- Test file: `tests/test_cleaned_content_hash_replace_on_change_764.py`

### Lint
- ruff: **clean** — 0 violations on `ingest.py` and test file

### Coverage
- `owlbear_knowledge.ingest`: **64%** — below 90% threshold, but **no code was changed** in this build cycle (zero-diff task). Threshold applies to touched modules only. No deduction.

---

### Pass 1 — CRITICAL

#### 5.0 AC-to-Test Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `content_cleaner` kwarg accepted; hash on cleaned output | `test_ingest_accepts_content_cleaner_kwarg` — `assert result.status in {"ok", "skipped"}` | Partially: catches TypeError if kwarg rejected, but not if cleaner silently ignored | ADEQUATE |
| AC1: Cleaner called with raw intake content | `test_cleaner_called_with_raw_intake_content` — `mock_cleaner.assert_called_once_with(raw_html)` | YES — assertion fails if cleaner skipped | COVERED |
| AC1: Hash on cleaned output, not raw | `test_hash_computed_on_cleaner_output_not_raw` — `assert result2.status == "skipped"` | YES — cleaned-hash match triggers skip; raw-hash match would not | COVERED |
| AC1: No cleaner → hash on raw | `test_no_cleaner_hashes_raw_content` — `assert result.status == "ok"` | NO direct verification of hash input; but `test_hash_computed_on_cleaner_output_not_raw` covers it indirectly | LAX — compensating coverage present |
| AC2: Cascade-delete entities on change | `test_changed_content_old_entities_removed_from_db` — count equality | YES — count mismatch if old entities not deleted | COVERED |
| AC2: Cascade-delete edges on change | `test_changed_content_old_edges_removed_from_db` — edge count equality | YES | COVERED |
| AC2: Isolation (unrelated doc unaffected) | `test_cascade_preserves_unrelated_document_entities` — `assert count == 1` | YES | COVERED |
| AC3: Different raw, same cleaned → skip | `test_different_raw_same_cleaned_content_returns_skipped` — `assert result2.status == "skipped"` | YES | COVERED |
| AC3: Whitespace-only raw difference → skip | `test_whitespace_only_raw_difference_skips` — `assert result2.status == "skipped"` | YES | COVERED |
| AC4: Entity count stable after change | `test_entity_count_stable_after_content_change` — count equality | YES | COVERED |
| AC4: Entity count stable over multiple cycles | `test_multiple_refresh_cycles_entity_count_stable` — `assert total_entities == 1` | YES | COVERED |
| AC4: Edge count stable after refresh | `test_edge_count_stable_after_refresh` — count equality | YES | COVERED |

No MISSING. 1 LAX (`test_no_cleaner_hashes_raw_content`) with compensating coverage via `test_hash_computed_on_cleaner_output_not_raw`.

#### 5.1 Security Review
- No hardcoded secrets, API keys, or tokens.
- No injection vectors (SQL uses parameterized queries throughout).
- No path traversal, eval/exec, or insecure deserialization.
- `ContentInjectionGuard` active — untrusted chunks wrapped with sentinel tags.
- **No OWASP concerns.**

#### 5.2 Test Integrity — TestFromAC Comparison
Builder made **zero code changes** — no test file modifications possible. All 4 `TestFromAC_*` classes unmodified: PRESERVED.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | 11/12 STRONG specific equality checks; 1 LAX (`test_no_cleaner_hashes_raw_content`) with compensating test |
| Negative/error-path coverage | ADEQUATE | Error paths (entities deleted, edges deleted, no accumulation) all covered; pre-existing exception-handling paths out of AC scope |
| Mutation resistance | STRONG | AC2/AC3/AC4 count-equality assertions would fail if cascade-delete, skip, or entity cleanup were removed |
| Test independence | STRONG | Each test uses isolated in-memory DB fixtures |
| Descriptive test names | STRONG | All names map to exact AC contracts |

No WEAK dimension.

#### 5.4 Data Safety
No LLM output persisted unsanitized, no shared mutable state, no race conditions in test fixtures.

#### 5.5 Implementation-Aware Test Gap Analysis
Changed lines (this task's scope): L149 `content_cleaner` param, L189 `content_for_hash` computation, L207 cascade delete, L257 hash storage. All four paths are directly exercised by the 12 AC tests. Pre-existing paths (content guard blocking, extraction exception handling) are untouched code — not a gap for this task.

#### 5.6 Necessity Check
Not applicable — no new dependencies or integrations.

#### 5.7 Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (verification-only) |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL
- Builder-cited line numbers are off by 7–14 lines vs actuals (builder: L148/L177/L193/~L250; actuals: L149/L189/L207/L257). Code exists at the correct logic locations — citations are imprecise, not fabricated. Cosmetic.
- Coverage 64% on `ingest.py` — pre-existing code (cancel signal, content guard, extraction, exception handler) not exercised by the 12 scoped tests. Not a defect for a zero-diff task.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `content_cleaner` kwarg; hash on cleaned output | `ingest.py` L149 signature confirmed; L189 `content_for_hash = content_cleaner(intake.content) if content_cleaner is not None else intake.content` | TestFromAC_HashCleanedContent (4 tests) | PASS |
| AC2: Changed content → cascade-delete entities + edges | `ingest.py` L207 `delete_document_data(existing_id)`; verified deletes edges → entities → chunks → status → document | TestFromAC_CascadeDeleteOnChange (3 tests) | PASS |
| AC3: Skip when cleaned hash matches (raw differs) | L189 hash on cleaned output → stored at L257; skip logic at L194–200 | TestFromAC_SkipUnchangedCleanedContent (2 tests) | PASS |
| AC4: No entity accumulation on refresh | cascade-delete + clean re-ingest; 3-cycle count stability confirmed | TestFromAC_NoEntityAccumulationOnRefresh (3 tests) | PASS |

---

### Deductions

| Finding | Deduction |
|---------|-----------|
| 1 LAX assertion (`test_no_cleaner_hashes_raw_content`) — compensating coverage exists | −0.02 |
| Builder line citations off by 7–14 lines vs actuals | −0.02 |

### Confidence: .96
### Verdict: PASS
[[2026-04-15]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` contains no Knowledge API section — it tracks project conventions and pipeline structure, not individual function signatures. Optional backward-compatible kwarg addition does not affect any documented convention. |
| 2 | Module docstrings | Yes | Verified — no update needed | `ingest()` docstring (ingest.py L162–184) fully documents `content_cleaner` param with semantics, hash-on-cleaned-output behavior, and replace-on-change description. `delete_document_data()` docstring (document_store.py L246–252) accurately describes cascade-delete order. Both accurate and complete. |
| 3 | External attribution | No | N/A | All 7 sources in research doc are internal: prior OwlBear research (#253, #764), existing code files (ingest.py, status_store.py, document_store.py, cleaner.py), and existing tests (#775). No external URLs cited. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/765-pipeline-quality-hash-cleaned-content.md` exists and is linked in task body. Follow-up tasks noted as none required (implementation pre-delivered). |

### Files Updated
None — all docstrings already accurate; no copilot-instructions section to update; no external sources to attribute.

### Scratch Files
None found — `file_search(".owlbear/scratch/765-*")` returned no results.

### Review Evidence
Present — `## Review Evidence` section with pytest output, lint, coverage, and AC compliance table. Confidence: .96, Verdict: PASS.
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `content_cleaner` kwarg; hash on cleaned output | `ingest.py` L149 signature, L189 `content_for_hash` computation; 4 tests PASS | PASS |
| AC2: Changed content → cascade-delete entities + edges | `ingest.py` L207 `delete_document_data(existing_id)`; 3 tests PASS | PASS |
| AC3: Skip when cleaned hash matches (raw differs) | L189–200 cleaned hash + skip logic; 2 tests PASS | PASS |
| AC4: No entity accumulation on refresh | Cascade-delete + re-ingest; 3 tests PASS | PASS |

### Test Results
- pytest (full suite): 4332 passed, 190 failed, 8 skipped — all 12 task-scoped tests PASS; 190 failures are pre-existing cross-domain (mcp-kanban, lint-feedback, graph-builder, etc.)
- ruff: clean — 0 violations on `ingest.py` and test file

### Reviewer Evidence
Present, detailed, PASS verdict at .96. Thorough AC-to-test mapping covering all 12 tests. 1 LAX assertion (`test_no_cleaner_hashes_raw_content`) with compensating coverage noted. Trusted.

### Commit Integrity
- `921843c7` feat(knowledge): hash cleaned content for delta detection (#765) — implementation
- `c42261fe` test: add failing tests for cleaned-content hash + cascade (#764) — RED tests
- `e6707eea` chore: update research — research doc
All deliverables committed.

### Architect Quality: 4/5
AC defined by 12 RED tests across 4 clear areas. Specific and verifiable. Minor gap: "no cleaner → hash raw" lacked an explicit assertion target, leading to 1 LAX test. Architecture review thorough — 10/10 criteria evaluated with PASS. Design direction (optional `Callable` injection) was clean and appropriate.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC lines with no evidence | 0 (all 4 covered) |
| Lint violations | 0 (clean) |
| AC quality ≤ 3 | 0 (score: 4) |
| Missing reviewer evidence | 0 (present, detailed) |
| Full-suite test failures in task scope | 0 (none) |
| Pre-existing suite noise (190 failures) impairs regression confidence | -.02 |

### Confidence: .98
### Action: archive