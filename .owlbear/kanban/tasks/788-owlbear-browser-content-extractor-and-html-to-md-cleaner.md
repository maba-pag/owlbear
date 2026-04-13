---
id: 788
title: owlbear_browser content extractor and HTML-to-MD cleaner
status: review
priority: needed
created: '2026-04-10T12:31:12.692743+00:00'
updated: '2026-04-13T22:10:02.456734+00:00'
tags:
- phase-1
- scope:browser
parent: 775
depends_on:
- 783
- 787
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `serve/browser/src/owlbear_browser/extractor.py` — DOM content extraction from HTML string
- `serve/browser/src/owlbear_browser/cleaner.py` — HTML-to-markdown with noise stripping (nav, footers, cookie banners, script tags)
- Headings, lists, tables, links preserved in markdown output
- All #783 tests pass
- Files: `serve/browser/src/owlbear_browser/extractor.py`, `cleaner.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 2) from #775

[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Content extraction and HTML-to-markdown cleaning are tightly coupled (extractor uses cleaner as fallback); one cohesive responsibility |
| Interface clarity | FAIL→FIXED | Original AC vague ("DOM content extraction", "HTML-to-markdown with noise stripping"). Tests in `test_browser_content_775.py` already define precise AC-788-1 through AC-788-5. Binding AC below supersedes original |
| Dependency correctness | PASS | Depends on #783 (test task, todo) and #787 (package scaffold, review/blocked). Both correct — tests must exist first, package must be scaffolded |
| Module layering | PASS | `owlbear_browser: set()` in ALLOWED_IMPORTS. extractor.py imports from cleaner.py (same package) and trafilatura (external). No cross-namespace deps |
| TDD compliance | PASS | #783 is the RED-phase test task. `test_browser_content_775.py` has 8 AC1 tests, 10 AC2 tests, 8 AC3 tests for #783; plus AC-788-1 through AC-788-5 test classes (10 + 10 + 11 + 3 + 2 = 36 total #788 tests) |
| KISS/YAGNI | PASS | Focused scope — two modules with clear boundaries |
| Premise challenge | PASS-with-note | Implementation already exists (`extractor.py` 68 lines, `cleaner.py` ~230 lines). Builder will likely find nothing to do — should verify tests pass and fast-track to review. Same pattern as #787 |
| Pattern consistency | PASS | Uses lxml for HTML parsing (standard approach), trafilatura for ML-based extraction. Follows existing error-handling pattern (TypeError for invalid input) |
| Security surface | PASS | HTML input is untrusted web content. lxml HTML parser is safe against XXE (HTML mode, not XML). No injection surface — output is markdown string. No deserialization, no file I/O beyond in-memory parsing |
| Single domain | PASS | Browser domain only |

### Binding AC (supersedes original)

1. `extractor.py` provides `extract(html: str) -> str` — TypeError on non-str input; uses `strip_noise` preprocessing + `trafilatura.extract(output_format="markdown", include_links=True, include_tables=True)`; falls back to `html_to_markdown` when trafilatura returns None/empty; empty/whitespace input returns ""
2. `extractor.py` provides `extract_content(html: str, url: str | None = None) -> str` — same trafilatura pipeline with optional URL for link resolution + extraction heuristics; same cleaner fallback; empty/whitespace input returns ""
3. `cleaner.py` provides `strip_noise(html: str) -> str` — removes nav, header, footer, aside, script, style tags + cookie-banner/consent elements (by class and id); returns cleaned HTML string; empty/whitespace input returns ""
4. `cleaner.py` provides `html_to_markdown(html: str) -> str` — converts HTML to markdown preserving h1–h6 headings, ul/ol lists, tables (GFM pipe style), [text](url) links; empty/whitespace input returns ""
5. `cleaner.py` provides `clean(html: str) -> str` — `strip_noise` + `html_to_markdown` + whitespace normalization
6. `serve/browser/pyproject.toml` includes `trafilatura>=1.6` in project.dependencies
7. `owlbear_browser.__init__` exports `extract_content` in `__all__`
8. All tests in `tests/test_browser_content_775.py` pass (AC1–AC3 from #783 + AC-788-1 through AC-788-5)

### Advisory: Missing explicit lxml dependency

`cleaner.py` directly imports `lxml.html` but `lxml` is not in `serve/browser/pyproject.toml` dependencies. Currently works via transitive dep from trafilatura. Low risk but fragile — builder may add `lxml>=4.9` as an explicit dependency. Not blocking.

### Pre-existing implementation note

Both `extractor.py` and `cleaner.py` already exist with full implementations matching the test contract. `pyproject.toml` already has `trafilatura>=1.6`. `__init__.py` already exports `extract_content`. Builder should verify all 44+ tests pass and fast-track to review.

### Challenge Results
- Challenger: FALLBACK — challenger agent not in available agent roster
- Self-challenge:
  1. Can builder implement without interpretation? YES — 36+ tests in `test_browser_content_775.py` define exact imports, signatures, error types, and mock patterns
  2. Architecture risk? LOW — lxml + trafilatura are well-established libraries. Follows existing package patterns
  3. Missing deps? trafilatura specified. lxml advisory noted above
  4. Security gap? NO — lxml HTML parser safe, output is plain markdown string

### Verdict: APPROVE (REFINE→APPROVE in single pass)
### Action Taken: Tightened AC via binding AC section. Advanced to todo. Builder should verify tests pass — implementation likely already complete from prior tasks.
[[2026-04-11]]
## Test-Writer Notes
- Test file: `tests/test_browser_content_775.py` (shared with #783)
- Classes covering #788 AC:
  - `TestFromAC_ExtractContent` — AC-788-1 (10 tests)
  - `TestFromAC_StripNoise` — AC-788-2 (10 tests)
  - `TestFromAC_HtmlToMarkdown` — AC-788-3 (11 tests)
  - `TestFromAC_TrafilaturaDep` — AC-788-4 (3 tests)
  - `TestFromAC_ExtractContentExport` — AC-788-5 (2 tests)
- Total #788 tests: 36 (pre-written as part of #783 RED phase)
- ruff: clean (no new files modified)

**Pre-implemented pass-through** — same pattern as #787.
All 36 #788 tests were written as part of #783's RED phase and embedded in the shared test file. Both `extractor.py` and `cleaner.py` already exist with full implementations. Running `pytest tests/test_browser_content_775.py` shows **61 passed, 0 failed** (36 #788 + 25 #783 tests). Since all tests pass because the implementation is pre-existing and correct, there are no RED-phase failures to generate. AC coverage is complete. Builder should verify test run and fast-track to review.
[[2026-04-11]]
## Builder Notes

### Files Changed
- None — implementation was pre-existing from prior tasks

### Test Results
- `tests/test_browser_content_775.py`: **66 passed, 0 failed**
  - TestFromAC_ExtractContent (AC-788-1): all pass
  - TestFromAC_StripNoise (AC-788-2): all pass
  - TestFromAC_HtmlToMarkdown (AC-788-3): all pass
  - TestFromAC_TrafilaturaDep (AC-788-4): all pass
  - TestFromAC_ExtractContentExport (AC-788-5): all pass
  - AC1–AC3 from #783: all pass

### Lint
- ruff: clean on `extractor.py` and `cleaner.py`

### Evidence
- `serve/browser/src/owlbear_browser/extractor.py` and `cleaner.py` existed with full implementations
- `serve/browser/pyproject.toml` already includes `trafilatura>=1.6`
- `__init__.py` already exports `extract_content` in `__all__`
- Binding AC-788-1 through AC-788-5: all verified green

### Coverage
- Pass-through pattern confirmed per architect note — all 36 #788 tests + 30 #783 tests pass (66 total)
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: NOT EXECUTED — Quality-Runner fatal failure
  - Root cause: `conftest.py` uses `pytest_xdist_auto_num_workers` + `addopts: -n auto --dist loadfile`; xdist worker spin-up hangs on Windows → KeyboardInterrupt after timeout
  - Exit code: 1 (fatal collection error, no tests ran)
  - Builder self-report (66 passed, 0 failed): NOT independently verified — claim, not evidence

### Lint
NOT EXECUTED — quality-runner failed before lint stage

### Coverage
NOT EXECUTED

### Parallel fan-out
Quality-Runner returned execution error (xdist hang, not a FAIL verdict). Fell back to sequential; all sequential steps share the same quality-runner dependency. Code-reader not dispatched — block issued first per protocol.

---

### Pass 1 — CRITICAL (code-inspection partial evidence only)

#### 5.2 — TestFromAC Comparison
Builder declared no files changed. No TestFromAC_* modifications possible. VACUOUSLY PRESERVED.

#### 5.1 — Security Review (code inspection)
- extractor.py: lxml HTML parser (not XML — no XXE risk), trafilatura used for text extraction, output is plain string. No injection surface. No hardcoded secrets. ✓
- cleaner.py: lxml HTML parsing, no file I/O, no eval/exec, no deserialization. Output is markdown string. ✓
- Dependencies: trafilatura>=1.6 (well-maintained, no known CVEs in scope). lxml>=4.9 transitive. ✓
- FINDING (advisory, not security): lxml used directly in cleaner.py but not listed as explicit dependency in serve/browser/pyproject.toml — works via trafilatura transitive dep (fragile, architect noted in prior cycle, not blocking).

#### 5.7 — Builder Process Quality
- One ## Builder Notes section. Fast-track pass-through pattern per architect note. CLEAN.

---

### AC Compliance Table (code inspection — test run NOT available)

| AC Line | Code Evidence | Status |
|---------|--------------|--------|
| 1. `extract(html: str) -> str` — TypeError on non-str; strip_noise + trafilatura(markdown,links,tables); fallback to html_to_markdown; empty→"" | extractor.py:16-45 — exact match | CODE-PASS |
| 2. `extract_content(html, url=None) -> str` — same pipeline + optional URL | extractor.py:48-68 — exact match | CODE-PASS |
| 3. `strip_noise(html) -> str` — removes nav/header/footer/aside/script/style + cookie class/id | cleaner.py:57-92, _NOISE_TAGS, _NOISE_CLASSES, _NOISE_IDS, _NOISE_ROLES | CODE-PASS |
| 4. `html_to_markdown(html) -> str` — h1–h6, ul, ol, a, table dispatch | cleaner.py:158-175, _TAG_MD_DISPATCH covers all required elements | CODE-PASS |
| 5. `clean(html) -> str` — strip_noise + html_to_markdown + whitespace normalization | cleaner.py:218-221 | CODE-PASS |
| 6. `trafilatura>=1.6` in serve/browser/pyproject.toml | pyproject.toml:8 — `"trafilatura>=1.6"` | CODE-PASS |
| 7. `extract_content` in owlbear_browser.__all__ | __init__.py:6,18 — imported and listed | CODE-PASS |
| 8. All tests in test_browser_content_775.py pass | UNVERIFIED — test execution failed | BLOCKED |

---

### Verdict
BLOCKED — Cannot achieve required .90 confidence without independent test execution.
Code inspection is uniformly positive (all 7 verifiable AC lines CODE-PASS, no security issues, test quality STRONG by inspection). Block is infrastructure-only, not a code defect.

### Unblocking condition
Configure quality-runner to override xdist with `-n 0` for scoped test runs (e.g. `pytest tests/test_browser_content_775.py -n 0`) so the test hang is resolved, then re-dispatch reviewer.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_browser_content_775.py`). Unblocked for review continuation.