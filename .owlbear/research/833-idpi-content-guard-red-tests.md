# RED Tests — IDPI ContentInjectionGuard at Graph Entry

> **Owning task:** #833 — RED tests — IDPI ContentInjectionGuard at graph entry
> **Date:** 2026-04-12 **Status:** Complete

## 1. Context and Question

Task #833 is the RED-phase TDD task for ContentInjectionGuard scanning at the knowledge graph entry point. The design was established in research #724 (browser path) and #768 (graph entry rescope). This research validates the test design against codebase state and confirms the ACs are testable.

**Core question:** Does the existing codebase state support writing RED tests for all 7 ACs, and are there any design gaps in the test specification?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| #724 IDPI research | `.owlbear/research/idpi-content-scanning.md` | .90 — CheckResult design, pattern matching approach |
| #768 content safety research | `.owlbear/research/768-content-safety-idpi-wrapping.md` | .90 — graph entry integration point, Option B recommendation |
| `ingest.py` | `serve/knowledge/src/owlbear_knowledge/ingest.py` | .95 — current pipeline, wrapping at L200-210 |
| `content_safety.py` | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | .90 — existing should_wrap/wrap pattern |
| `IngestResult` model | `ingest.py:28-37` | .95 — status Literal lacks "blocked" |
| PinchTab `idpi/content.go` | github.com/pinchtab (via #724) | .85 — CheckResult struct, strict/warn modes |
| Test conventions | `test_content_safety_inversion_775.py`, `test_content_safety_735.py` | .90 — TestFromAC_ class structure, in-function imports |

## 3. Analysis

### 3a. AC-by-AC Test Feasibility

| AC | Requirement | Testable at RED? | Design Note |
|----|-------------|------------------|-------------|
| AC1 | `ContentInjectionGuard` importable from `owlbear_knowledge.content_guard` | Yes | Import test — will fail, no module exists |
| AC2 | `CheckResult` dataclass with 4 fields | Yes | Field presence + type checks on dataclass |
| AC3 | `scan(text)` detects injection phrases (case-insensitive) | Yes | Call scan with known phrases, assert threat=True |
| AC4 | `IngestPipeline.ingest()` calls `guard.scan()` on chunk text | Yes | Mock-based integration test, verify scan called |
| AC5 | Strict mode: ingest returns blocked status | Yes | **Requires new `"blocked"` literal in IngestResult.status** |
| AC6 | Warn mode: logs warning, proceeds | Yes | Mock logger, assert warning logged, status="ok" |
| AC7 | Clean content passes without false positives | Yes | Scan benign text, assert threat=False |

### 3b. IngestResult.status Gap

Current `IngestResult.status` is `Literal["ok", "failed", "skipped", "cancelled"]`. AC5 requires distinguishing "injection blocked" from "processing failed." Two options:

| Option | Change | Pros | Cons |
|--------|--------|------|------|
| A. Add `"blocked"` literal | `Literal[..., "blocked"]` | Semantic clarity, distinct from errors | Minor model change |
| B. Reuse `"failed"` | No model change | Zero changes to IngestResult | Conflates injection with crash |

**Recommendation: Option A** (.90 confidence). Tests should assert `status="blocked"`. The GREEN-phase implementation (#834) adds the literal. This is defense-in-depth — callers need to distinguish intentional blocking from unexpected failures for alerting and metrics.

### 3c. Integration Test Design

The scan integration point is in `ingest()` at L200-210, between chunking and entity extraction. The current wrapping flow:

```
chunks = chunker.chunk(content)
_should_wrap = should_wrap(source_type)
extract_coros = [extractor.extract(wrap(c.text) if _should_wrap else c.text) for c in chunks]
```

The guard scan should slot in **before** the extract comprehension, scanning each `c.text` for untrusted sources. Tests should verify:
- `guard.scan()` called for each chunk when source is untrusted
- `guard.scan()` NOT called for trusted sources (file, text, file_glob)
- Strict mode short-circuits before extraction

### 3d. Test Structure Convention

Per codebase convention (`test_content_safety_inversion_775.py`, `test_content_safety_735.py`):
- Class names: `TestFromAC_{DescriptiveName}`
- In-function imports (lazy import inside each test method)
- Descriptive docstrings per method
- Mocks for pipeline dependencies (AsyncMock for extractor, MagicMock for store/chunker)
- File name: `tests/test_content_guard_833.py`

## 4. Recommendation (.90 confidence)

All 7 ACs are testable at RED phase. The test file should contain ~15-20 tests across 4 test classes:

1. **TestFromAC_ContentGuardImport** — AC1: module + class importability
2. **TestFromAC_CheckResultFields** — AC2: dataclass fields and types
3. **TestFromAC_ScanDetection** — AC3, AC7: injection detection + clean content
4. **TestFromAC_IngestGuardIntegration** — AC4, AC5, AC6: pipeline integration, strict/warn modes

Key design decision: RED tests should assert `IngestResult(status="blocked")` for AC5, requiring the GREEN phase to add the literal.

Challenge: FALLBACK — challenger subagent not available

## 5. Follow-up Tasks

No additional follow-up tasks needed. #833 (RED) and #834 (GREEN) already exist as a TDD pair under parent #751.
