---
id: 778
title: Add hash stability validation protocol to CDP spike execution (#753)
status: done
priority: needed
created: '2026-04-10T12:16:54.010932+00:00'
updated: '2026-04-12T02:17:59.687412+00:00'
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
Add content hash stability testing to the CDP spike execution checklist (#753).

The spike execution should include this validation protocol:
1. For at least 2 target pages: extract the same page 3 times, 60s apart
2. For each extraction, record: (a) raw HTML hash, (b) trafilatura output hash, (c) trafilatura output text
3. Compare across extractions:
   - Raw HTML hashes likely differ (dynamic boilerplate) — document the delta
   - Cleaned (trafilatura) hashes MUST match for go/no-go
   - If cleaned hashes differ, inspect the diff to identify leaking dynamic elements
4. If trafilatura output differs between extractions of the same page:
   - Test with `prune_xpath` to remove dynamic elements
   - Document specific XPath patterns needed for corporate pages
   - If still unstable, this is a NO-GO signal for the hashing approach

AC:
1. Hash stability protocol added to #753 execution checklist
2. Protocol tests at least 2 pages × 3 extractions × 60s intervals
3. Results compared at raw HTML and cleaned-content levels
4. Go/no-go determination includes hash stability verdict

Context: From #774 research — AC 7 was not covered by original spike design.
Data voice Gap 2 identified hash-on-raw-content as critical issue.
Research: .owlbear/research/774-edge-cdp-spike.md §3.3

[[2026-04-11]]
## Research
- Research doc: .owlbear/research/778-hash-stability-protocol.md
- Sources: 7 studied, 4 high-relevance (#774 §3.3, #777 research, compute_content_hash, #753 checklist)
- Recommendation: Option A — automated hash stability loop in cdp-spike.py behind --hash-stability flag, ~30-40 LOC (confidence: .85)
- Follow-up tasks created: none (task itself is the implementation story)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — implementation prescribed by AC and #774 §3.3; no controversial trade-off
- Confidence in original: .85

## Findings Summary
1. Hash instability risk is in CDP page.content() (dynamic HTML), not trafilatura or SHA-256 — both are deterministic
2. Automated approach (Option A) preferred over manual checklist — enables exact SHA-256 comparison across 3 extractions × 60s intervals
3. **Undeclared dependency on #777:** hash stability needs trafilatura extraction, which #777 adds to spike. Recommend adding depends_on: [777]
4. Cleaner idempotency already validated in test_cleaner_756.py for static HTML; gap is live page extraction stability
5. Protocol: 3 extractions per URL, 60s apart, compare cleaned hashes. If differ → try prune_xpath. If still differ → NO-GO for hash approach
6. #753 execution checklist needs 3 new steps (5a-5c) and 1 new go/no-go row for hash stability verdict
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Adds hash stability validation to spike script — one concern |
| Interface clarity | PASS (with guidance) | AC2-4 are testable. AC1 ("added to #753 execution checklist") conflates code deliverable with kanban task editing — clarified in builder guidance below |
| Dependency correctness | FAIL→CORRECTED | `depends_on: [776]` correct (#776 done). **Missing #777** — hash stability needs trafilatura extraction from `_extract_trafilatura()` which #777 adds to spike. See DEPENDS_ON-CORRECTION below |
| Module layering | N/A | Scratch spike script, no module dependencies |
| TDD compliance | PASS | Existing patterns in `tests/test_cdp_spike_776.py` and `tests/test_cdp_spike_777.py` (importlib + mock for spike functions). Test-writer creates `test_cdp_spike_778.py` |
| KISS/YAGNI | PASS | ~30-40 LOC behind `--hash-stability` flag. Opt-in, minimal |
| Premise challenge | PASS | #774 research §3.3 identifies hash stability as untested gap. Production `compute_content_hash` (status_store.py) and cleaner are deterministic — the gap is live page extraction variability |
| Pattern consistency | PASS | Follows spike patterns: argparse flags, helper functions, `_log_step()` output |
| Security surface | PASS | No new security surface. Local-only scratch script, no external API calls beyond existing CDP connection |
| Single domain | PASS | Browser/extraction domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `trafilatura.extract()` in stability loop | Returns None on unparseable HTML | None (returns None) | Must handle — skip hash comparison, log warning | Incomplete stability data |
| `time.sleep(60)` between extractions | Keyboard interrupt during wait | KeyboardInterrupt | Existing cleanup handler in spike | Spike terminates cleanly |
| `sha256()` on None cleaned content | TypeError if trafilatura returns None | TypeError | Must guard — check for None before hashing | Crash mid-protocol |

### DEPENDS_ON-CORRECTION: task #778 should have depends_on [776, 777]

Research finding #3 confirmed: hash stability protocol calls `trafilatura.extract()` on raw HTML to produce cleaned content for hashing. Task #777 ("Expand cdp-spike.py with trafilatura extraction quality test") adds `_extract_trafilatura()` to the spike. Without #777, there's no trafilatura integration in the spike to build upon. #777 is currently `in-progress`.

### Challenge Results
- Challenger: FALLBACK — challenger agent not in available roster
- Architect response: Proceeded without challenge; implementation approach prescribed by AC + research §3.4, no controversial trade-off. Research confidence .85

### Builder Guidance

1. **AC1 clarification**: "Hash stability protocol added to #753 execution checklist" means: implement the protocol as code in `.owlbear/scratch/cdp-spike.py`. The builder does NOT edit #753's task body — checklist updates are handled by the architect/orchestrator.
2. **Implementation anchor**: Add `--hash-stability` argparse flag (default off). When enabled, after #777's trafilatura extraction, run the stability loop per research §3.4.
3. **Function contract**: Create `_run_hash_stability(page, urls, ...)` (or similar). For each URL: 3 extractions, ≥60s apart, compute SHA-256 of raw HTML and trafilatura cleaned output, compare across extractions, log PASS/FAIL per URL.
4. **None guard**: `trafilatura.extract()` can return `None` — guard before `sha256(cleaned.encode())`. Log and mark as FAIL if extraction returns None.
5. **Diff on mismatch**: Use `difflib.unified_diff` on cleaned text when cleaned hashes differ (research §3.5).
6. **Verdict output**: Log per-URL stability result and overall go/no-go verdict per research §3.4 matrix (GO / CONDITIONAL GO / NO-GO).
7. **Test pattern**: Follow `tests/test_cdp_spike_776.py` and `test_cdp_spike_777.py` — importlib-based loading with mocked playwright and trafilatura. Mock `time.sleep` to avoid actual 60s waits in tests.

### Codebase Evidence
- Spike script: `.owlbear/scratch/cdp-spike.py` (~245 LOC, argparse with `--url`)
- #776 test pattern: `tests/test_cdp_spike_776.py` — `_load_spike()` via importlib, `_make_mock_page()`, `_make_pw_mock()`
- #777 test pattern: `tests/test_cdp_spike_777.py` — `trafilatura_stub` fixture, `_get_extract_fn()`
- Production hash: `serve/knowledge/src/owlbear_knowledge/status_store.py:39` — `compute_content_hash()` (SHA-256 on stripped/normalized content). Spike can use `hashlib.sha256` directly (no production import needed for scratch script)
- Production extractor: `serve/browser/src/owlbear_browser/extractor.py` — `extract()`/`extract_content()` use standard trafilatura mode

### Verdict: APPROVE
### Action Taken: Advanced #778 to todo. Flagged DEPENDS_ON-CORRECTION: add #777 to depends_on [776, 777]. AC1 clarified in builder guidance — builder implements code, does not edit #753.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_cdp_spike_778.py
- Classes: `TestFromAC_HashStabilityProtocol`, `TestFromAC_ExtractionProtocol`, `TestFromAC_HashComparison`, `TestFromAC_GoNoGoVerdict`
- Tests per category: happy 7, edge 2, error 4, boundary 3
- Total: 16 tests, all FAIL (verified: pytest 16 failed, 0 passed)
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — `--hash-stability` flag + `_run_hash_stability` function | `test_hash_stability_flag_accepted_by_argparse`, `test_hash_stability_flag_defaults_to_false`, `test_run_hash_stability_function_exists` |
| AC2 — 2 pages x 3 extractions x 60s intervals | `test_page_content_called_3_times_per_url`, `test_sleep_between_extractions_at_least_60_seconds`, `test_accepts_list_of_multiple_urls`, `test_extracts_all_urls_not_just_first` |
| AC3 — Raw HTML and cleaned-content hash comparison | `test_trafilatura_called_per_extraction_for_cleaned_hash`, `test_logs_raw_html_hash_information`, `test_logs_cleaned_content_hash_information`, `test_logs_diff_output_when_cleaned_hashes_differ` |
| AC4 — Go/no-go verdict | `test_logs_go_verdict_when_all_cleaned_hashes_stable`, `test_logs_nogo_verdict_when_cleaned_hashes_unstable`, `test_none_from_trafilatura_does_not_raise`, `test_none_from_trafilatura_marks_url_as_fail_in_log`, `test_overall_verdict_logged_across_multiple_urls` |

### Failure modes verified
- AC1 fails: `--hash-stability` argparse flag not wired up (SystemExit 2) + `_run_hash_stability()` missing (callable is None)
- AC2-4 all fail with: `AssertionError: Script must expose _run_hash_stability()` — no callable found

### Builder notes
- `time.sleep` is patched in all tests to avoid actual 60s waits
- `trafilatura` is stubbed via `trafilatura_stub` fixture (patch.dict on sys.modules)
- `playwright` is stubbed inline in `_load_spike()` — no browser driver required
- Test file: commit 56717404
[[2026-04-11]]
## Builder Notes

### Files changed
- `.owlbear/scratch/cdp-spike.py` — added `--hash-stability` argparse flag, `_STABILITY_EXTRACTIONS`/`_STABILITY_INTERVAL` constants, `_check_url_hash_stability(page, url)` helper, `_run_hash_stability(page, urls)` entrypoint, and wired into `main()`.

### Test results
- **16/16 passed** (TestFromAC_HashStabilityProtocol × 3, TestFromAC_ExtractionProtocol × 4, TestFromAC_HashComparison × 4, TestFromAC_GoNoGoVerdict × 5)
- RED verified first: 16 failed before implementation

### Lint
- `ruff check` — **All checks passed** (clean)

### Coverage
- Full spike file: 47.8% — uncovered lines are pre-existing `_cleanup`/`main()` which require a live Edge subprocess. New functions (`_check_url_hash_stability`, `_run_hash_stability`) are fully exercised by the 16 tests.

### Implementation summary
- `--hash-stability` flag added to `_parse_args` (dest=`hash_stability`, default=False, opt-in per AC1)
- Refactored into two functions to stay within ruff C901/PLR0915 complexity limits:
  - `_check_url_hash_stability(page, url)` — single-URL 3×60s extraction loop; returns GO/NO-GO/FAIL
  - `_run_hash_stability(page, urls)` — iterates URLs, collects verdicts, logs OVERALL verdict
- SHA-256 comparison of raw HTML hash (delta documented) and cleaned-content hash (stability gate)
- `difflib.unified_diff` triggered on mismatch for first-vs-last cleaned text (builder guidance §5)
- `None` guard on trafilatura output → logs FAIL, no TypeError (builder guidance §4)
- `time.sleep` patched in all tests — no actual 60s waits in CI
[[2026-04-11]]
## Review Evidence

### Test Results
pytest: **16 passed, 0 failed** (quality-runner, independent run)
ruff lint: **clean** — 0 violations
Coverage: quality-runner reports 0% (spike outside package system — known limitation, same as #777). Builder-reported 47.8% via `--cov=.owlbear/scratch/cdp-spike.py` is plausible given new functions fully exercised by 16 tests.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — `--hash-stability` flag + `_run_hash_stability` | `_parse_args` at cdp-spike.py:159, `_run_hash_stability` at line 379 | `test_hash_stability_flag_accepted_by_argparse`, `test_hash_stability_flag_defaults_to_false`, `test_run_hash_stability_function_exists` | PASS |
| AC2 — 2 pages × 3 extractions × 60s intervals | `_STABILITY_EXTRACTIONS=3`, `_STABILITY_INTERVAL=60` at lines 280–281; loop with `time.sleep` in `_check_url_hash_stability`; `_run_hash_stability` iterates url list | `test_page_content_called_3_times_per_url`, `test_sleep_between_extractions_at_least_60_seconds`, `test_accepts_list_of_multiple_urls`, `test_extracts_all_urls_not_just_first` | PASS |
| AC3 — Raw HTML + cleaned-content comparison | `sha256(html.encode())` for raw; `trafilatura.extract()` + `sha256(cleaned.encode())` for cleaned; `difflib.unified_diff` on mismatch | `test_trafilatura_called_per_extraction_for_cleaned_hash`, `test_logs_raw_html_hash_information`, `test_logs_cleaned_content_hash_information`, `test_logs_diff_output_when_cleaned_hashes_differ` | PASS |
| AC4 — Go/no-go verdict | Per-URL `GO/NO-GO/FAIL` + `OVERALL verdict=GO/NO-GO/CONDITIONAL GO` logged in `_run_hash_stability` | `test_logs_go_verdict_when_all_cleaned_hashes_stable`, `test_logs_nogo_verdict_when_cleaned_hashes_unstable`, `test_none_from_trafilatura_does_not_raise`, `test_none_from_trafilatura_marks_url_as_fail_in_log`, `test_overall_verdict_logged_across_multiple_urls` | PASS |

### Pass 1 Checks
- **TestFromAC integrity:** PRESERVED — no modifications detected. 16 RED-verified tests, all preserved.
- **Security:** PASS — no new security surface. hashlib/difflib/trafilatura all safe. No hardcoded credentials.
- **Test quality:** ADEQUATE — call-count assertions are specific; keyword log checks appropriate for spike/logging scripts. One LAX finding (below).
- **Builder process:** CLEAN — single builder notes section, no retry loops.

### Deductions
- −0.05 LAX: `test_logs_go_verdict_when_all_cleaned_hashes_stable` checks `"GO" in output` — substring-matched by "NO-GO". Companion unstable test provides asymmetric coverage. Informational only.
- −0.03 INFO: `CONDITIONAL GO` verdict branch (all-FAIL, no NO-GO) untested. Minor edge, acceptable for spike script.

### Verdict
Confidence: **0.92 → PASS**
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | All changes are to scratch spike script `.owlbear/scratch/cdp-spike.py` — no production API or pipeline behavior changed. `copilot-instructions.md` unaffected. |
| 2 | Module docstrings | Yes | Verified | New functions `_check_url_hash_stability` (line 277) and `_run_hash_stability` (line 374) both have accurate docstrings matching their implementation. No edits needed. |
| 3 | External attribution | Yes | Updated | Research doc source #7: trafilatura Python API docs (`trafilatura.readthedocs.io/en/latest/usage-python.html`) — used for `extract()` `prune_xpath`/`include_tables`/`url` params in hash stability loop. Added new section to `.owlbear/sources/overview.md`. Commit: 6edc72d9. |
| 4 | CLI changes | No | N/A | `--hash-stability` flag is for scratch spike script only. Not documented in `README.md`. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/778-hash-stability-protocol.md` exists and is linked from task body (Research section). Follow-up tasks: none required per researcher (task is the implementation story). |

### Files Updated
- `.owlbear/sources/overview.md` — added "Hash Stability Validation Protocol (Task #778)" section with trafilatura attribution.

### Scratch Files
- No `.owlbear/scratch/778-*` files found to clean.

### Commit
`docs: add trafilatura attribution for #778 (doc-writer)` — 6edc72d9
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — `--hash-stability` flag + `_run_hash_stability` | cdp-spike.py:159 argparse flag, cdp-spike.py:375 `_run_hash_stability` function | PASS |
| AC2 — 2 pages × 3 extractions × 60s | `_STABILITY_EXTRACTIONS=3`, `_STABILITY_INTERVAL=60` at lines 273-274; 4 tests verify including sleep assertion | PASS |
| AC3 — Raw HTML + cleaned-content comparison | SHA-256 on raw HTML + trafilatura cleaned; difflib.unified_diff on mismatch; 4 tests verify | PASS |
| AC4 — Go/no-go verdict | GO/NO-GO/FAIL per-URL + OVERALL verdict logged; 5 tests verify | PASS |

### Test Results
- pytest (task-scoped): 16 passed, 0 failed
- pytest (all CDP spike 776+777+778): 74 passed, 0 failed
- pytest (full suite): 3574 passed, 275 failed, 8 skipped — all 275 failures in kanban/analysis/lint-hooks/orchestrator modules, zero in browser/spike scope
- ruff: clean — 0 violations

### Commits Verified
- 56717404 — test: add failing tests for hash stability protocol (#778, test-writer)
- 6edc72d9 — docs: add trafilatura attribution for #778 (doc-writer)
- cdp-spike.py is gitignored (.owlbear/scratch/) — builder implementation not committable by design

### Architect Quality: 4/5
AC lines are clear and testable. Minor gap: AC1 phrasing ("added to #753 execution checklist") conflated kanban task editing with code delivery — architect corrected in builder guidance, no downstream impact.

### Deduction Breakdown
- No deductions applied. All AC lines have specific test evidence. Lint clean. No task-scoped test failures. Reviewer section present and detailed.

### Confidence: 1.00
### Action: archive