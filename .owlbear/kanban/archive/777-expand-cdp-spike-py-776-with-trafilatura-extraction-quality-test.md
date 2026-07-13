---
id: 777
title: Expand cdp-spike.py (#776) with trafilatura extraction quality test
status: archived
priority: medium
created: '2026-04-10T12:16:53.902954+00:00'
updated: '2026-04-15T11:16:45.092344+00:00'
tags:
- phase-0
- scope:browser
parent: 751
depends_on:
- 776
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Add trafilatura extraction quality testing to the CDP spike script (#776).

After CDP connectivity and basic text extraction succeed, the script should:
1. `pip install trafilatura` (or include in spike deps)
2. For each navigated page, capture raw `page.content()` (full HTML)
3. Run `trafilatura.extract(html, output_format="markdown", include_links=True, url=page_url)`
4. Also run `trafilatura.extract(html, output_format="markdown", include_links=True, url=page_url, favor_precision=True)`
5. Log: text length, paragraph count, presence of boilerplate indicators (nav text, footer text, breadcrumb patterns)
6. Compare standard vs precision mode output
7. Test with 3+ SharePoint pages and 2+ Confluence pages (URLs configurable)

AC:
1. Spike script includes trafilatura extraction after CDP text extraction
2. Both standard and favor_precision modes tested
3. Output logged with quality metrics (text length, paragraph count, boilerplate indicators)
4. At least 5 URLs configured (3 SharePoint, 2 Confluence)

Context: From #774 research — AC 6 was not covered by original spike design.
Research: .owlbear/research/774-edge-cdp-spike.md §3.2

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/777-trafilatura-spike-expansion.md
- Sources: 7 studied, 4 high-relevance (trafilatura docs, #774 research, production extractor/cleaner, spike script)
- Recommendation: Option A — inline trafilatura testing in existing spike script, ~40-60 LOC addition (confidence: .88)
- Follow-up tasks created: none (task #777 itself is the implementation story)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — implementation approach prescribed by task AC, no controversial trade-off
- Confidence in original: .88

## Findings Summary
1. Spike script exists at .owlbear/scratch/cdp-spike.py (~245 LOC), uses only page.inner_text("body") — no trafilatura
2. Production extractor.py already uses trafilatura standard mode (no favor_precision), but only tested with synthetic HTML
3. trafilatura v2.0.0 API confirmed: favor_precision, output_format="markdown", include_links, include_tables, prune_xpath all available
4. Key gap: production doesn't use favor_precision=True — spike should test both modes to inform production configuration
5. Dependency resolved: trafilatura available via workspace member serve/browser; no additional install needed
6. Builder approach: add _extract_trafilatura() helper, modify argparse for --urls (multi-URL), wrap navigation+extraction in URL loop, log quality metrics (text length, paragraph count, boilerplate indicators)
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adds trafilatura quality testing to existing spike — one concern |
| Interface clarity | PASS | AC specifies extraction calls, modes, metrics, URL count. Boilerplate indicators enumerated in research §3.3 (Home, Sign out/in, Copyright, Privacy, Terms of Use, Powered by, breadcrumb separators, Cookie, Footer) |
| Dependency correctness | PASS | `depends_on: [776]` — #776 "P0-01: Implement cdp-spike.py" is done. Spike script exists at `.owlbear/scratch/cdp-spike.py` (~245 LOC) |
| Module layering | N/A | Scratch spike script, no module dependencies to violate |
| TDD compliance | PASS | Existing test file `tests/test_cdp_spike_776.py` establishes testable patterns (importlib-based function tests with mocked playwright). Test-writer can extend for #777 AC |
| KISS/YAGNI | PASS | ~40-60 LOC addition. No speculative features. Directly serves Phase 0 validation gap |
| Premise challenge | PASS | Production `extractor.py` uses trafilatura without `favor_precision` and only has synthetic HTML tests. Real corporate page quality testing is a genuine gap. #774 research §3.2 identified this at .65 confidence |
| Pattern consistency | PASS | Follows existing spike patterns: argparse for config, `_log_step()` for output, helper functions for extraction |
| Security surface | PASS | No new security surface — trafilatura processes HTML already fetched via existing CDP connection. Spike is local-only scratch script |
| Single domain | PASS | Browser/extraction domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `trafilatura.extract()` | Returns None on unparseable HTML | None (returns None) | Yes — spike should log and continue | Informational only |
| `page.content()` | Page not loaded / CDP disconnected | PlaywrightError | Yes — existing cleanup handler in spike | Spike terminates with error log |

### Challenge Results
- Challenger: FALLBACK — agent not in available roster
- Architect response: Proceeded; implementation approach prescribed by AC, no controversial trade-off. Research confidence .88

### Builder Guidance
1. **Boilerplate indicators** (from research §3.3): regex patterns for `Home`, `Sign out/in`, `Copyright`, `Privacy`, `Terms of Use`, `Powered by`, breadcrumb separators (`›`, `»`, `>`), `Cookie`, `Footer`
2. **Include `include_tables=True`** in both trafilatura calls — matches production extractor pattern and captures SharePoint table content
3. **Placeholder URLs**: Use clearly fake company URLs (e.g., `https://contoso.sharepoint.com/sites/...`) that users replace before execution. Do NOT hardcode real corporate URLs
4. **URL config pattern**: Research recommends `--urls` (comma-separated) or `TARGET_URLS` env var, consistent with existing `--url`/`TARGET_URL` pattern

### Codebase Evidence
- Spike script: `.owlbear/scratch/cdp-spike.py` — `_extract_text()` at line 163 is the insertion point for trafilatura comparison
- Production extractor: `serve/browser/src/owlbear_browser/extractor.py` — `extract()` and `extract_content()` use standard mode only
- trafilatura dependency: `serve/browser/pyproject.toml` — `trafilatura>=1.6` already declared
- Existing tests: `tests/test_cdp_spike_776.py` — importlib + mock pattern for spike function testing

### Verdict: APPROVE
### Action Taken: Advanced #777 to todo. AC sufficiently precise with research doc supplement. No splits needed.
[[2026-04-11]]
## Test-Writer Notes

**Test file:** `tests/test_cdp_spike_777.py`

**Classes:**
- `TestFromAC_TrafilaturaExtraction` — 5 tests (AC1)
- `TestFromAC_ExtractionModes` — 6 tests (AC2)
- `TestFromAC_QualityMetrics` — 5 tests (AC3)
- `TestFromAC_URLConfiguration` — 5 tests (AC4)

**Total: 21 tests, all FAIL** (pytest confirmed: 21 failed, 0 passed)

**Ruff:** clean (exit 0)

**AC coverage:**

| AC | Tests | Coverage |
|----|-------|----------|
| AC1: trafilatura extraction after CDP text extraction | `test_extract_trafilatura_function_exists`, `test_extract_trafilatura_calls_page_content_for_raw_html`, `test_extract_trafilatura_passes_html_to_trafilatura`, `test_extract_trafilatura_handles_none_from_trafilatura_without_raising`, `test_extract_trafilatura_produces_log_output_on_success` | Full |
| AC2: both standard and favor_precision modes | `test_trafilatura_called_at_least_twice_per_extraction`, `test_standard_mode_call_does_not_set_favor_precision_true`, `test_favor_precision_true_mode_called`, `test_both_modes_use_output_format_markdown`, `test_both_modes_pass_include_links_true`, `test_both_modes_pass_url_parameter` | Full |
| AC3: quality metrics logged (length, paragraph count, boilerplate) | `test_quality_metrics_log_text_length`, `test_quality_metrics_log_paragraph_count`, `test_quality_metrics_log_boilerplate_indicators`, `test_quality_metrics_handle_none_extraction_gracefully`, `test_quality_metrics_compare_standard_vs_precision_output` | Full |
| AC4: ≥5 URLs (3 SharePoint, 2 Confluence) | `test_script_accepts_multiple_urls_argument`, `test_default_urls_include_at_least_five_entries`, `test_default_urls_include_three_sharepoint_entries`, `test_default_urls_include_two_confluence_entries`, `test_script_help_documents_multi_url_option` | Full |

**Failure root causes (confirming correct RED state):**
1. Tests 1–16: `_extract_trafilatura()` function does not exist in current spike → `assert callable(None)` fails
2. Tests 17–21: No `--urls` argparse flag, no `DEFAULT_URLS` constant, no `TARGET_URLS` mention in `--help`

**Strategy notes:**
- `trafilatura_stub` pytest fixture uses `patch.dict(sys.modules, {"trafilatura": stub})` — keeps stub active during both module load and function calls (handles top-level and inline imports)
- Builder must add `_extract_trafilatura(page, url)` with contract: `page.content()` → HTML → `trafilatura.extract()` x2 (standard + `favor_precision=True`), both with `output_format="markdown"`, `include_links=True`, `url=`
- Builder must add `DEFAULT_URLS` list constant with 3+ SharePoint + 2+ Confluence placeholder URLs, and `--urls` argparse argument
[[2026-04-11]]
## Builder Notes

**Files changed:**
- `.owlbear/scratch/cdp-spike.py` — added `DEFAULT_URLS` constant, `_extract_trafilatura()` helper, `--urls` argparse argument with `TARGET_URLS` env var support, and call from `main()`. (~75 LOC added)

**Test results:**
- `tests/test_cdp_spike_777.py`: **21/21 passed** (all TestFromAC_* classes green)
- `tests/test_cdp_spike_776.py`: **37/37 passed** (no regressions)
- Total: **58 passed, 0 failed**

**Lint:** ruff exit 0 — clean (fixed `RUF100` unused noqa + `N806` uppercase local variable)

**Coverage:** Spike script is in `.owlbear/scratch/` (gitignored), coverage not applicable.

**Evidence summary:**
- `_extract_trafilatura(page, url)` calls `page.content()`, then `trafilatura.extract()` twice: standard mode and `favor_precision=True`, both with `output_format="markdown"`, `include_links=True`, `include_tables=True`, `url=url`
- Logs quality metrics per mode: text length, paragraph count, boilerplate indicators (regex patterns for Home, Sign in/out, Copyright, Privacy, Terms of Use, Powered by, breadcrumbs, Cookie, Footer)
- Logs mode comparison when both extractions succeed
- Handles `None` return gracefully (logs "extraction returned None — no content extracted")
- `DEFAULT_URLS`: 3 SharePoint + 2 Confluence placeholder URLs (contoso.sharepoint.com × 3, contoso.atlassian.net × 2)
- `--urls` argparse argument with `nargs="+"` defaults to `DEFAULT_URLS` (falls back to `TARGET_URLS` env var)
- `--help` documents both `--urls` and `TARGET_URLS`

**Commit:** `.owlbear/scratch/` is gitignored — spike scripts are not tracked (by design)
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: 58 passed, 0 failed (test_cdp_spike_777.py: 21, test_cdp_spike_776.py: 37)

### Lint: clean (ruff exit 0)

### Coverage: N/A — spike script in `.owlbear/scratch/` (gitignored by design)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: trafilatura extraction after CDP text extraction | test_extract_trafilatura_function_exists, test_extract_trafilatura_calls_page_content_for_raw_html, test_extract_trafilatura_passes_html_to_trafilatura | Yes — callable check, page.content.called, trafilatura.extract.called with HTML arg | COVERED |
| AC2: both standard and favor_precision modes | test_trafilatura_called_at_least_twice_per_extraction, test_favor_precision_true_mode_called, test_both_modes_use_output_format_markdown, test_both_modes_pass_include_links_true, test_both_modes_pass_url_parameter | Yes — call count ≥2, favor_precision=True kwarg, output_format, include_links, url kwargs all individually verified | COVERED |
| AC3: quality metrics logged | test_quality_metrics_log_text_length, test_quality_metrics_log_paragraph_count, test_quality_metrics_log_boilerplate_indicators, test_quality_metrics_handle_none_extraction_gracefully, test_quality_metrics_compare_standard_vs_precision_output | Yes — capsys checks for metric keyword presence; NOTE: disjunctive assertions ("500" OR "length") are LAX for value accuracy but adequate for presence verification; AC3 requires *logging* not *accuracy* | COVERED |
| AC4: ≥5 URLs (3 SharePoint, 2 Confluence) | test_default_urls_include_at_least_five_entries, test_default_urls_include_three_sharepoint_entries, test_default_urls_include_two_confluence_entries, test_script_accepts_multiple_urls_argument, test_script_help_documents_multi_url_option | Yes — counts sharepoint/atlassian URLs in DEFAULT_URLS directly; argparse --urls acceptance tested; help text verified | COVERED |

#### Security Review
- No hardcoded secrets — DEFAULT_URLS use "contoso" placeholder domains
- subprocess.Popen called with list[str] — no shell injection
- env vars TARGET_URL/TARGET_URLS used as URL strings only — no eval/exec
- trafilatura processes already-fetched HTML — no unsafely deserialized content
- No credentials or PII in log output
- No issues

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 21 TestFromAC_* tests (test-writer confirmed 21 FAIL on HEAD) | None — all 21 present with original assertions intact | PRESERVED |

All 21 TestFromAC_* tests accounted for. No tests weakened or removed.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | assert callable(fn), page.content.called, call_count >= 2, favor_precision kwarg checked, url kwarg checked, sharepoint/atlassian URL counts verified directly against DEFAULT_URLS constant; quality metric assertions use OR disjuncts but acceptable for logging-presence checks |
| Negative/error-path coverage | ADEQUATE | test_extract_trafilatura_handles_none_from_trafilatura_without_raising, test_quality_metrics_handle_none_extraction_gracefully both exercise None return path |
| Manual mutation reasoning | STRONG | Removing page.content() call → test_extract_trafilatura_calls_page_content fails; removing favor_precision=True → test_favor_precision_true_mode_called fails; removing --urls flag → test_script_accepts_multiple_urls_argument fails; reducing DEFAULT_URLS to 4 → test_default_urls_include_at_least_five_entries fails |
| Test independence | STRONG | Each test reloads spike via importlib with fresh stubs; no shared mutable state |
| Descriptive names | STRONG | All tests describe AC contract and observable behavior |

#### Data Safety
- No LLM output, no shared mutable state, no multi-step atomicity concerns. N/A.

#### Implementation-Aware Gaps
- `_extract_trafilatura()` — all branches covered: html fetched, both trafilatura calls, _log_metrics with valid text, _log_metrics with None, comparison path
- `DEFAULT_URLS` constant verified directly
- `--urls` argparse integration verified via parse_args() call
- `main()` integration (calling _extract_trafilatura after _extract_text) not independently tested but #776 integration tests provide callsite coverage; spike requires live Edge so full integration not feasible
- No significant untested paths

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- test_quality_metrics_log_text_length assertion `"500" in output or "length" in output.lower()` — second disjunct is always true when metric is logged, so value accuracy is not verified. AC3 does not require accuracy, only presence. Informational only.
- test_quality_metrics_log_paragraph_count same pattern — "para" in output always true once metric format is logged. Informational.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: spike includes trafilatura extraction after CDP text extraction | `_extract_trafilatura()` at cdp-spike.py:183; called from `main()` after `_extract_text()` (~line 327); uses `page.content()` for raw HTML | test_extract_trafilatura_function_exists, test_extract_trafilatura_calls_page_content_for_raw_html | PASS |
| AC2: both standard and favor_precision modes tested | Standard call at cdp-spike.py:205-211, favor_precision=True call at cdp-spike.py:212-219; both with output_format="markdown", include_links=True, include_tables=True, url=url | test_favor_precision_true_mode_called, test_both_modes_use_output_format_markdown | PASS |
| AC3: quality metrics logged (text length, paragraph count, boilerplate indicators) | `_log_metrics()` inner function at cdp-spike.py:222-240 logs `length={length} chars, paragraphs={paragraphs}, boilerplate_indicators={count} ({names})`; 9 boilerplate regex patterns | test_quality_metrics_log_text_length, test_quality_metrics_log_boilerplate_indicators | PASS |
| AC4: ≥5 URLs (3 SharePoint, 2 Confluence) | DEFAULT_URLS at cdp-spike.py:34-41: contoso.sharepoint.com ×3, contoso.atlassian.net ×2; `--urls` argparse with nargs="+" and TARGET_URLS env fallback | test_default_urls_include_three_sharepoint_entries, test_default_urls_include_two_confluence_entries | PASS |

### Confidence: .95
### Verdict: PASS
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Only file changed: `.owlbear/scratch/cdp-spike.py` (gitignored spike script, not a published API or documented behavior) |
| 2 | Module docstrings | No | N/A | No Python modules created or modified — spike script in scratch, no module docstrings |
| 3 | External attribution | No | N/A | Trafilatura already attributed in `.owlbear/sources/overview.md` from prior tasks (#774, #775, #759); no new external sources introduced by #777 |
| 4 | CLI changes | No | N/A | No changes to published CLI commands; spike is local scratch only |
| 5 | Research doc | Yes | Verified | `.owlbear/research/777-trafilatura-spike-expansion.md` exists and is linked from task body |

### Files Updated
None — no documentation impact.

### Scratch Files Cleaned
None found — no `.owlbear/scratch/777-*` files existed.
[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: trafilatura extraction after CDP text extraction | `_extract_trafilatura()` at cdp-spike.py:201, called from main() after `_extract_text()`; 5 tests in TestFromAC_TrafilaturaExtraction | PASS |
| AC2: both standard and favor_precision modes tested | Two `trafilatura.extract()` calls at cdp-spike.py:225,232 (standard + favor_precision=True); 6 tests in TestFromAC_ExtractionModes | PASS |
| AC3: quality metrics logged | `_log_metrics()` at cdp-spike.py:240 logs length, paragraph count, boilerplate indicators (9 regex patterns); 5 tests in TestFromAC_QualityMetrics | PASS |
| AC4: at least 5 URLs (3 SharePoint, 2 Confluence) | DEFAULT_URLS at cdp-spike.py:39-44: 3x contoso.sharepoint.com + 2x contoso.atlassian.net; 5 tests in TestFromAC_URLConfiguration | PASS |

### Test Results
- pytest: 4386 passed, 192 failed, 8 skipped (0 failures in task scope: cdp_spike_777 21/21 pass, cdp_spike_776 37/37 pass). All 192 failures are pre-existing in unrelated modules (MCP kanban refactor, analysis model, lint hooks, bookmark pipeline, etc.)
- ruff: 3 violations, 0 in task scope (engine.py E501, test_refresh_sharepoint_879.py RUF002 + UP024)

### Architect Quality: 4/5
AC lines were specific with clear extraction modes, metric dimensions, and URL count requirements. Minor gap: `include_tables=True` came from builder guidance rather than AC text, but guidance section covered it well. No builder improvisation needed beyond guidance.

### Deduction Breakdown
- AC lines with no evidence: 0 (-.00)
- Lint violations in scope: 0 (-.00)
- AC quality score leq 3: No, 4/5 (-.00)
- Missing reviewer evidence: No, detailed section present (-.00)
- Full-suite test failures in scope: 0 (-.00)

### Confidence: 1.00
### Action: archive

### Commit Verification
- tests/test_cdp_spike_777.py: committed at df06e4f4
- .owlbear/research/777-trafilatura-spike-expansion.md: committed at df06e4f4
- .owlbear/scratch/cdp-spike.py: gitignored by design (scratch spike script)
- No uncommitted deliverables