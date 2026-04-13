---
id: 783
title: Tests — owlbear_browser content extractor and HTML-to-MD cleaner
status: done
priority: needed
created: '2026-04-10T12:30:44.046816+00:00'
updated: '2026-04-11T15:54:11.651308+00:00'
tags:
- phase-1
- scope:browser
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify content extraction from HTML string returns structured text
- Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved)
- Tests verify noise removal (nav bars, footers, cookie banners, script tags stripped)
- File: `tests/test_browser_content_775.py`

## Context
- WS-C: Browser Packages
- Scope item 1 (part 2) from #775

[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for browser content extraction/cleaning |
| Interface clarity | PASS | AC describes three test coverage areas mapping to distinct test classes |
| Dependency correctness | PASS | No deps needed; #788 (impl) correctly depends on this task |
| Module layering | PASS | Tests only — no layering concerns |
| TDD compliance | PASS | This IS the RED-phase test task; tagged `type:test` |
| KISS/YAGNI | PASS | Focused scope — three AC lines, one test file |
| Premise challenge | PASS | Tests pre-written at `tests/test_browser_content_775.py` (~698 lines); implementation exists at `serve/browser/src/owlbear_browser/extractor.py` and `cleaner.py` |
| Pattern consistency | PASS | Test file named after parent #775, consistent with other `test_*_775.py` files |
| Security surface | PASS | No new security boundaries |
| Single domain | PASS | Browser domain only |

### Codebase Evidence

- `extractor.py`: `extract(html) -> str`, `extract_content(html, url=None) -> str`
- `cleaner.py`: `strip_noise(html) -> str`, `html_to_markdown(html) -> str`, `clean(html) -> str`
- Test file covers AC1 (`TestFromAC_ContentExtractor`), AC2 (`TestFromAC_HTMLCleaner`), AC3 (`TestFromAC_NoiseRemoval`)
- Test file also covers #788 AC (AC-788-1 through AC-788-5) in shared file — no split needed

### Note: Pre-existing deliverables

Tests and implementation both exist. Executor should verify tests pass and fast-track to review rather than writing new tests.

### Challenge Results

- Challenger: proceed (confidence 0.90)
- Architect response: accepted — gap is pipeline efficiency (pre-done work), outside arch-review scope

### Verdict: APPROVE
### Action Taken: Advanced to todo
[[2026-04-11]]
## Test-Writer Notes

**Pre-existing deliverable — arch-review authorized fast-track.**

- Test file: `tests/test_browser_content_775.py` (698 lines)
- Implementation also pre-exists at `serve/browser/src/owlbear_browser/extractor.py` and `cleaner.py`
- Arch review (#780 notes) explicitly noted both exist and authorized fast-track

### Test inventory

| Class | Category | Count | AC |
|-------|----------|-------|----|
| `TestFromAC_ContentExtractor` | happy/edge/error | 8 | AC1 |
| `TestFromAC_HTMLCleaner` | happy/edge | 9 | AC2 |
| `TestFromAC_NoiseRemoval` | happy/edge | 8 | AC3 |
| `TestFromAC_ExtractContent` | happy/edge/error | 9 | AC-788-1 |
| `TestFromAC_StripNoise` | happy/edge | 9 | AC-788-2 |
| `TestFromAC_HtmlToMarkdown` | happy/edge | 10 | AC-788-3 |
| `TestFromAC_TrafilaturaDep` | boundary | 3 | AC-788-4 |
| `TestFromAC_ExtractContentExport` | happy | 2 | AC-788-5 |
| **Total** | | **58+** | all AC lines |

- **pytest result:** 61 passed, 0 failed
- **ruff:** All checks passed (no linting errors)

### AC coverage

| AC | Tests present | Status |
|----|--------------|--------|
| AC1 — extract() returns structured text | 8 tests | COVERED |
| AC2 — HTML-to-markdown conversion | 9 tests | COVERED |
| AC3 — noise removal | 8 tests | COVERED |

### Note — test phase state

Tests PASS because implementation was written ahead of pipeline processing. This is a known pre-existing condition documented by arch review. Builder should verify (fast-track) and advance directly to review.
[[2026-04-11]]
## Builder Notes

**Fast-track verified — pre-existing deliverable confirmed green.**

### Files changed
- `tests/test_browser_content_775.py` — added `TestBuilderDiscovered` class (5 tests)

### Test results
- **66 passed, 0 failed** (61 original + 5 builder-discovered)
- `extractor.py`: 100% coverage (22/22 stmts, 10/10 branches)
- `cleaner.py`: 100% coverage (109/109 stmts) — up from 89%

### Lint
- ruff: All checks passed

### Builder-discovered tests (RED → GREEN in one pass — code pre-existed, gaps were coverage-only)
| Test | Covered line(s) | Description |
|------|----------------|-------------|
| `test_strip_noise_removes_role_complementary` | 77-80 | ARIA role="complementary" removal in `_remove_cookie_elements` |
| `test_strip_noise_handles_html_comment` | 65 | Non-string tag branch in `_remove_cookie_elements` |
| `test_html_to_markdown_empty_table` | 114 | `return ""` branch in `_table_to_md` for empty table |
| `test_html_to_markdown_handles_comment_node` | 177 | Non-string tag branch in `_elem_to_md` |
| `test_clean_collapses_consecutive_blank_lines` | 215 | Double-blank `continue` in `_normalize_content` |

### AC coverage confirmed
| AC | Status |
|----|--------|
| AC1 — extract() returns structured text | COVERED (8 tests) |
| AC2 — HTML-to-markdown conversion | COVERED (9 tests) |
| AC3 — noise removal | COVERED (8 tests) |
[[2026-04-11]]
## Review Evidence

### Test Results (independent — quality-runner)
- **pytest:** 66 passed, 0 failed — exit code 0
- **ruff:** clean — exit code 0
- **Coverage:** `owlbear_browser.extractor` 100% (22/22 stmts, 10/10 branches), `owlbear_browser.cleaner` 100% (109/109 stmts)

### Changed Files
- `tests/test_browser_content_775.py` — builder added `TestBuilderDiscovered` class (5 tests). No other files changed.

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped TestFromAC_ | Would Fail If AC Violated? | Verdict |
|---------|-------------------|--------------------------|---------|
| AC1: extract() returns structured text from HTML | TestFromAC_ContentExtractor (8 tests): `test_extract_returns_string`, `test_extract_returns_main_content_text`, `test_extract_noise_only_page_omits_nav_and_footer`, `test_extract_non_string_raises_type_error` are the load-bearing tests | Yes — removing content extraction or returning wrong type fails 4+ tests | COVERED |
| AC2: HTML-to-markdown (headings, lists, tables, links preserved) | TestFromAC_HTMLCleaner (9 tests): `test_clean_preserves_h1/h2_as_markdown_heading`, `test_clean_preserves_unordered/ordered_list_items`, `test_clean_preserves_hyperlink_text_and_url`; table assertions supplemented by `TestFromAC_HtmlToMarkdown.test_html_to_markdown_preserves_table_structure` | Yes — assert "# Page Title" in result; assert "|" in result; both fail on broken conversion | COVERED |
| AC3: noise removal (nav, footer, cookie banners, script tags stripped) | TestFromAC_NoiseRemoval (8 tests): explicit negative assertions ("Nav link" not in result, "doTrack" not in result, "We use cookies" not in result); `test_clean_strips_all_noise_types_simultaneously` for combined coverage | Yes — removing noise stripping causes specific text to appear in output | COVERED |
| File: `tests/test_browser_content_775.py` | File exists, all 3 AC classes present | PASS |

#### 5.1 Security Review
No hardcoded secrets, no injection surface, no path traversal, no insecure deserialization. lxml HTML parser is used (safe against XXE in HTML mode). trafilatura output is plain markdown string. No credentials in error messages. CLEAN.

#### 5.2 TestFromAC Modification Check
Builder changed only `tests/test_browser_content_775.py`. Git diff confirms exactly one unified diff: addition of `TestBuilderDiscovered` block starting at line 695. No existing class, method, or assertion was modified.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC_* (8 classes, 58 methods) | None — builder only appended new class | PRESERVED |

#### 5.3 Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Specific string assertions (`"# Page Title" in result`, `"Nav link 1" not in result`), regex checks for bullet/numbered markers, exact empty-string equality on whitespace inputs |
| Negative/error-path coverage | ADEQUATE | TypeError for non-str input; empty/whitespace tests in every class; no-content page tested |
| Manual mutation reasoning | STRONG | Removing `strip_noise()` → nav/footer text appears; removing `html_to_markdown()` heading dispatch → "# Page Title" absent; flipping cookie-banner removal → "We use cookies" reappears |
| Test independence | STRONG | All imports inside test methods; static HTML string inputs; no shared mutable state |
| Descriptive test names | STRONG | All names self-documenting (`test_clean_strips_cookie_consent_by_id`, `test_extract_noise_only_page_omits_nav_and_footer`) |

#### 5.4 Data Safety
No LLM output, race conditions, missing atomicity, or unbounded input. CLEAN.

#### 5.5 Implementation-Aware Test Gap Analysis
**extractor.py (22 stmts, 10 branches — 100%)**
- `extract()`: TypeError path (test_extract_non_string_raises_type_error), empty-string path, trafilatura fallback to html_to_markdown (TestFromAC_ExtractContent::test_extract_content_falls_back_when_trafilatura_returns_none/empty). All branches covered.
- `extract_content()`: url kwarg, url=None, empty, whitespace, trafilatura fallback — all covered.

**cleaner.py (109 stmts — 100%)**
- `_remove_cookie_elements()`: non-string tag branch (HTML comments) → TestBuilderDiscovered::test_strip_noise_handles_html_comment; role="complementary" → test_strip_noise_removes_role_complementary. Both builder-added, both appropriate.
- `_table_to_md()`: empty table `return ""` → test_html_to_markdown_empty_table. Covered.
- `_elem_to_md()`: comment node branch → test_html_to_markdown_handles_comment_node. Covered.
- `_normalize_content()`: consecutive blank-line skip → test_clean_collapses_consecutive_blank_lines. Covered.

**Minor note:** `test_clean_collapses_consecutive_blank_lines` tests private `_normalize_content` directly (docstring says "clean() normalizes..." — minor doc inconsistency). Not a defect; private-function testing for coverage is acceptable at builder discovery phase.

### Pass 2 — INFORMATIONAL
- Table assertion in `TestFromAC_HTMLCleaner.test_clean_preserves_table_cell_content` checks only text content, not pipe structure. This is compensated by `TestFromAC_HtmlToMarkdown.test_html_to_markdown_preserves_table_structure` asserting `"|" in result`. Not a coverage gap.
- Builder Notes list 5 new tests but count reported "66 passed" (61 original + 5 builder) — confirmed accurate by quality-runner.

### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Files changed | 1 |
| RED → GREEN | Pre-existing implementation (fast-track authorized by arch review) |
| TestFromAC modifications | None |

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests verify content extraction from HTML string returns structured text | 8 TestFromAC_ContentExtractor tests — pytest 66/0; `test_extract_returns_main_content_text` catches missing extraction | PASS |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | 9 TestFromAC_HTMLCleaner + 10 TestFromAC_HtmlToMarkdown — all pass; `"# Page Title"` assertion catches broken heading conversion | PASS |
| Tests verify noise removal (nav, footer, cookie banners, script tags stripped) | 8 TestFromAC_NoiseRemoval — `test_clean_strips_all_noise_types_simultaneously` is the combined sentinel | PASS |
| File: `tests/test_browser_content_775.py` | File exists (63KB, 750 lines with builder additions) | PASS |

### Deductions
- Minor doc inconsistency in `test_clean_collapses_consecutive_blank_lines` (docstring says "clean()" but tests `_normalize_content`): −0.01

### Verdict
Confidence: **0.97 → PASS**
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure test task — no public API or behavior added. `copilot-instructions.md` unchanged. |
| 2 | Module docstrings | Yes | Updated | Review flagged minor inconsistency: `test_clean_collapses_consecutive_blank_lines` had docstring `clean() normalizes...` but tests `_normalize_content` directly. Fixed to `_normalize_content() reduces consecutive blank lines to a single blank line.` |
| 3 | External attribution | No | N/A | `trafilatura` and `lxml` already attributed in `.owlbear/sources/overview.md` (tasks #751, #774, #775). No new libraries introduced. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research phase for this task. Arch review notes in task body; no `.owlbear/research/783-*.md` produced or expected. |

### Files Updated
- `tests/test_browser_content_775.py` — fixed docstring on `test_clean_collapses_consecutive_blank_lines`

### Scratch Files Cleaned
- None (no `.owlbear/scratch/783-*` files found)

### Commit Notes
- `8e58094c` — `docs: fix owlbear_knowledge.schema module docstring (doc-writer)` — pre-staged schema.py fix swept into initial commit; amend corrected the message.
- `fa39b232` — `docs: fix inaccurate test docstring in test_browser_content_775.py (#783, doc-writer)` — staged file included the builder's `TestBuilderDiscovered` class (5 tests, unstaged from builder's working tree) plus the docstring fix. All content was review-verified (0.97 confidence, 66/0 tests pass). No application logic touched.
[[2026-04-11]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests verify content extraction from HTML string returns structured text | `TestFromAC_ContentExtractor` (8 tests) — all pass, `test_extract_returns_main_content_text` asserts extracted text present | PASS |
| Tests verify HTML-to-markdown conversion (headings, lists, tables, links preserved) | `TestFromAC_HTMLCleaner` (9 tests) — `test_clean_preserves_h1_as_markdown_heading` asserts `"# Page Title" in result`; table/list/link assertions present | PASS |
| Tests verify noise removal (nav, footer, cookie banners, script tags stripped) | `TestFromAC_NoiseRemoval` (8 tests) — negative assertions (`"Home | About | Contact" not in result`, `"doTrack" not in result`, `"We use cookies" not in result`) | PASS |
| File: `tests/test_browser_content_775.py` | File exists (32KB, 9 test classes, 66 tests total incl. 5 builder-discovered) | PASS |

### Test Results
- pytest (task scope): 66 passed, 0 failed
- pytest (full suite): 3450 passed, 303 failed, 6 collection errors — all failures in 36 unrelated test files (kanban, knowledge, planner, etc.), pre-existing
- ruff: All checks passed

### Architect Quality: 4/5
AC was specific and testable — three distinct criteria each mapping to a dedicated test class. Builder improvisation was coverage-only (5 tests for private-function branches), not AC gap-filling.

### Deduction Breakdown
- AC lines with no evidence: 0 (−0.00)
- Lint violations: 0 (−0.00)
- AC quality ≤ 3: no (−0.00)
- Missing reviewer evidence: no — detailed, 0.97 PASS (−0.00)
- Full-suite failures in task scope: 0 (−0.00)
- Process note: builder deliverables swept into doc-writer commit fa39b232 rather than committed separately — minor irregularity, no deduction (content is correct and committed)

### Confidence: 0.98
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 73ed9072 | test | tests/test_browser_content_775.py | #788 (shared file) |
| fa39b232 | docs | tests/test_browser_content_775.py | #783 |