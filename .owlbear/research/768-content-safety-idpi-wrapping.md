# Content Safety: IDPI + Wrapping for AUTHENTICATED_WEB

> **Owning task:** #768 — P1-15: Tests — Content safety: IDPI + wrapping for AUTHENTICATED_WEB
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

Task #768 specifies RED-phase tests for three content safety requirements:
1. AUTHENTICATED_WEB content automatically wrapped as untrusted
2. Content safety predicate defaults to wrapped for unknown source types (inverted default)
3. IDPI scanning called before content enters graph

**Core question:** What test work remains, given that AC1 and AC2 may already be covered by sibling tasks in the #751 tree?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| `content_safety.py` | `serve/knowledge/src/owlbear_knowledge/content_safety.py` | .95 — `should_wrap()` predicate + `wrap_untrusted_content()` already implemented |
| `ingest.py` | `serve/knowledge/src/owlbear_knowledge/ingest.py:182-195` | .95 — wrapping integration already uses `should_wrap()` |
| `test_content_safety_inversion_775.py` | `tests/test_content_safety_inversion_775.py` | .90 — 10 tests covering predicate inversion |
| `test_authenticated_content_pipeline_751.py` | `tests/test_authenticated_content_pipeline_751.py` | .90 — 7 tests covering authenticated_web wrapping |
| `test_authenticated_content_pipeline_775.py` | `tests/test_authenticated_content_pipeline_775.py` | .85 — 4 tests covering predicate inversion in ingest |
| IDPI research (#724) | `.owlbear/research/idpi-content-scanning.md` | .90 — ContentInjectionGuard design, pattern-matching approach |
| OWASP LLM01:2025 | `https://genai.owasp.org/llmrisk/llm01-prompt-injection/` | .85 — Strategy #3 string-checking, #6 segregate content |

## 3. Analysis

### 3a. AC1+AC2 Overlap Assessment

| AC | Requirement | Existing Coverage | Files | Status |
|----|-------------|-------------------|-------|--------|
| AC1 | AUTHENTICATED_WEB wrapped | 7 tests: wrapping, URL attribute, all-chunks, regression | `test_authenticated_content_pipeline_751.py` | **REDUNDANT** |
| AC2 | Predicate inverted (wrap unknown) | 14 tests: deny-list, trusted exempt, None, empty, bool type | `test_content_safety_inversion_775.py`, `test_authenticated_content_pipeline_775.py` | **REDUNDANT** |
| AC3 | IDPI scanning before graph entry | 0 tests | None | **NOT IMPLEMENTED** |

**Implementation state:** `content_safety.py` has `_TRUSTED_SOURCE_TYPES = frozenset({"file", "file_glob", "text"})` with `should_wrap()` returning True for all non-exempt types. `ingest.py` calls `should_wrap()` and wraps accordingly. This is the inverted predicate AC2 describes.

### 3b. IDPI Gap Analysis

`ContentInjectionGuard` was designed in research #724 but never implemented. No `content_guard.py` exists in `serve/browser/` or `serve/knowledge/`. The research targeted browser extraction paths — task #768 targets graph entry (ingest pipeline), a complementary integration point.

| Criterion | Browser path (#724) | Knowledge graph entry (#768 AC3) |
|-----------|---------------------|----------------------------------|
| Integration point | `browser_read_text`, `extract_content` | `IngestPipeline.ingest()` |
| When scanned | After extraction, before return | After chunking, before entity extraction |
| Purpose | Warn/block at extraction time | Prevent poisoned entities in graph |
| Module location | `owlbear_browser/content_guard.py` | `owlbear_knowledge/content_guard.py` |

### 3c. IDPI Integration Design Options

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| A. In `content_safety.py` | Extend existing module | Single file for all safety | Module grows beyond SRP |
| B. New `content_guard.py` in knowledge | Separate module | Clean SRP, mirrors #724 design | New file |
| C. Shared package | New `serve/content-safety/` | Reusable across browser + knowledge | Over-engineering for 1 class |

**Recommendation: Option B** (.85 confidence). Mirrors the #724 design pattern. `content_safety.py` handles wrapping; `content_guard.py` handles scanning. The scan call goes in `ingest.py` alongside the existing `should_wrap()` check.

## 4. Recommendation (.85 confidence)

**Rescope #768 to AC3 only.** AC1 and AC2 are fully covered — writing duplicate tests wastes effort and creates maintenance burden. The RED-phase test file should focus exclusively on IDPI scanning at graph entry:

1. `ContentInjectionGuard` importable from `owlbear_knowledge.content_guard`
2. `CheckResult` dataclass with `threat`, `blocked`, `reason`, `pattern` fields
3. `scan(text) -> CheckResult` detects known injection phrases
4. `IngestPipeline.ingest()` calls `guard.scan()` before entity extraction
5. Strict mode: ingest returns `status="blocked"` (or similar)
6. Warn mode: logs warning, proceeds with wrapping + extraction

Challenge: FALLBACK — challenger subagent not available

## 5. Follow-up Tasks

See kanban tasks created below. AC1+AC2 coverage acknowledged as complete — no duplicate tasks.
