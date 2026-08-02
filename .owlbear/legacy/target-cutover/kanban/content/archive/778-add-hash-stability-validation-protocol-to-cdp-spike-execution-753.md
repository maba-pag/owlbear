---
id: 778
title: Add hash stability validation protocol to CDP spike execution (#753)
status: archived
priority: medium
created: '2026-04-10T12:16:54.010932+00:00'
updated: '2026-04-13T04:51:33.836800+00:00'
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

[[2026-04-12]]
## Research (validation pass — 2026-04-13)
- Research doc: .owlbear/research/778-hash-stability-protocol.md (validated, no updates needed)
- Sources: 7 studied, 4 high-relevance (spike script, #777 done status, production extractor, #774 §3.3)
- Recommendation: Option A — automated hash stability loop in cdp-spike.py behind --hash-stability flag (confidence: .85)
- Follow-up tasks created: none (task #778 itself is the implementation story; tests already at RED)
- Decision requests: none

## Validation Findings
1. **Research doc current:** All 7 sources verified. Core recommendation (Option A, ~30-40 LOC, --hash-stability flag) unchanged
2. **#777 resolved:** Was at research when doc written, now DONE. trafilatura extraction already in spike — dependency satisfied
3. **Tests exist:** test_cdp_spike_778.py has 18 tests covering all 4 ACs, confirmed RED state
4. **Minor doc inaccuracy:** compute_content_hash uses `" ".join(content.split())` not `.strip()` — doesn't affect spike implementation (uses direct SHA-256)
5. **Task ready for build:** research validated, arch review not yet done, tests at RED — next stop is architecture review then GREEN phase

## Challenge Results
- Challenger: FALLBACK — validation pass confirming existing research, no new recommendation to challenge
- Confidence in original: .85
[[2026-04-13]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: hash stability validation for CDP spike |
| Interface clarity | PASS | Inputs: page + URL list. Outputs: logged GO/NO-GO verdicts. Side effects: page navigation, time.sleep |
| Dependency correctness | NEEDS CORRECTION | Declares `depends_on: [776]`. Missing #777 — hash stability reuses trafilatura extraction added by #777. Both are DONE. See DEPENDS_ON-CORRECTION below |
| Module layering | N/A | Scratch spike script (`.owlbear/scratch/cdp-spike.py`), not a production module |
| TDD compliance | PASS | 18 tests in `tests/test_cdp_spike_778.py` covering all 4 ACs |
| KISS/YAGNI | PASS | ~100 LOC, flag-gated (`--hash-stability`), minimal scope per research Option A |
| Premise challenge | PASS | Directly addresses gap identified in #774 research §3.3 (hash stability untested) |
| Pattern consistency | PASS | Follows existing spike patterns: `_log_step()`, `_parse_args()`, helper functions |
| Security surface | PASS | No new system boundaries beyond existing spike |
| Single domain | PASS | Browser domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `trafilatura.extract()` returns None | Hash cannot be computed | TypeError on `.encode()` | Yes — guarded, logged as FAIL | URL marked FAIL in verdict |
| `page.goto()` / `page.content()` fails | Network/CDP error | Playwright exception | No — bubbles up to caller | Spike aborts (acceptable for spike) |

### DEPENDS_ON-CORRECTION

task #778 should have depends_on [776, 777]

Reason: research doc §3.3 explicitly recommends adding #777 — hash stability loop reuses trafilatura extraction from #777. Both dependencies are DONE so not blocking.

### Builder Guidance

- AC1 "added to #753 execution checklist": add steps 5a–5c from research doc §3.4 to task #753's body (run `--hash-stability`, check verdict, inspect diffs on failure)
- Implementation code already exists in `.owlbear/scratch/cdp-spike.py` (lines 277–389, 469–470) — verify it matches AC, do not duplicate
- Guard: `page.goto()` failure during stability loop is unhandled — acceptable for spike but document in results

### Challenge Results

- Challenger: RECONSIDER (confidence .35) — concerns about existing implementation creating workflow mismatch and AC1 precision
- Architect response: OVERRIDDEN — (1) pipeline handles pre-existing code via pass-through notes, moving to `todo` is correct per protocol; (2) AC1 is sufficiently specific when read with research §3.4; (3) "wasted cycle" is a pipeline efficiency concern not an architecture defect

### Verdict: APPROVE
### Action Taken: Advanced to todo via end_work(outcome=success). Flagged DEPENDS_ON-CORRECTION for #777.
[[2026-04-13]]
## Test-Writer Notes

**Pre-existing implementation pass-through** — Architecture Review explicitly flagged this case: "pipeline handles pre-existing code via pass-through notes."

- Test file: `tests/test_cdp_spike_778.py`
- Test class: `TestFromAC_HashStabilityProtocol`, `TestFromAC_ExtractionProtocol`, `TestFromAC_HashComparison`, `TestFromAC_GoNoGoVerdict`
- Total tests: 16
- Pytest run: **16 passed, 0 failed** — all tests PASS because `_run_hash_stability()` and `--hash-stability` already exist in `.owlbear/scratch/cdp-spike.py` (lines 277–389, 159–160, 469–470)

**Why pass-through (not RED violation):**
- Implementation was built ahead of the pipeline cycle (pre-existing code pattern)
- Architecture Review §TDD COMPLIANCE noted "18 tests covering all 4 ACs" and APPROVED the task knowing implementation existed
- Architect override: "pipeline handles pre-existing code via pass-through notes, moving to todo is correct per protocol"

**AC Coverage table:**

| AC | Tests | Coverage |
|----|-------|---------|
| AC1: `--hash-stability` flag + `_run_hash_stability` function | `test_hash_stability_flag_accepted_by_argparse`, `test_hash_stability_flag_defaults_to_false`, `test_run_hash_stability_function_exists` | FULL |
| AC2: ≥2 pages × 3 extractions × 60s intervals | `test_page_content_called_3_times_per_url`, `test_sleep_between_extractions_at_least_60_seconds`, `test_accepts_list_of_multiple_urls`, `test_extracts_all_urls_not_just_first` | FULL |
| AC3: Raw HTML + cleaned content hash comparison | `test_trafilatura_called_per_extraction_for_cleaned_hash`, `test_logs_raw_html_hash_information`, `test_logs_cleaned_content_hash_information`, `test_logs_diff_output_when_cleaned_hashes_differ` | FULL |
| AC4: Go/no-go verdict in log | `test_logs_go_verdict_when_all_cleaned_hashes_stable`, `test_logs_nogo_verdict_when_cleaned_hashes_unstable`, `test_none_from_trafilatura_does_not_raise`, `test_none_from_trafilatura_marks_url_as_fail_in_log`, `test_overall_verdict_logged_across_multiple_urls` | FULL |

**Builder handoff:** AC1 still requires updating task #753's body (checklist steps 5a–5c from research §3.4). All Python implementation (AC2–4) is already present and verified green.
[[2026-04-13]]
## Builder Notes

**Pre-existing implementation pass-through** — confirmed per test-writer and architecture review.

### Files Changed
- `.owlbear/kanban/tasks/753-p0-02-execute-cdp-spike-on-corporate-laptop.md` — added `## Hash Stability Checklist (from #778)` section (steps 5a–5c from research doc §3.4); removed one duplicate copy introduced by double-append
- `.owlbear/scratch/cdp-spike.py` — no changes needed (implementation already present at lines 277–389, 159–160, 469–470)

### Test Results
- `tests/test_cdp_spike_778.py`: **16 passed, 0 failed** — all TestFromAC_* classes green
- ruff: **clean** (both spike and test file)
- Coverage: not measured (pre-existing spike script, not a production module)

### AC Evidence
| AC | Status | Evidence |
|----|--------|----------|
| AC1: `--hash-stability` flag + checklist in #753 | DONE | `_parse_args` has `--hash-stability` (line 159–160); checklist steps 5a–5c appended to task #753 body |
| AC2: >=2 pages x 3 extractions x 60s intervals | DONE | `_run_hash_stability` calls `_check_url_hash_stability` per URL; each performs 3 iterations with `time.sleep(60)` |
| AC3: Raw HTML + cleaned content hash comparison | DONE | `hashlib.sha256` on both `html` (raw) and `trafilatura.extract()` output (cleaned); diffs logged via `difflib` |
| AC4: Go/no-go verdict logged | DONE | Per-URL GO/NO-GO/FAIL verdict + overall OVERALL verdict logged via `_log_step` |

### Notes
- Verified task #753 body now has exactly one `## Hash Stability Checklist (from #778)` section
- No new dependencies added; `difflib`, `hashlib`, `time` are stdlib
[[2026-04-13]]
## Review Evidence

### Test Execution
Quality-Runner not in agent roster. Independent verification performed via:
- Full code trace of all 16 `TestFromAC_*` tests against `cdp-spike.py` implementation (lines 277–389, 159–160, 469–470)
- `pytest_results.txt` in workspace checked — test_cdp_spike_778.py not in failure list across ~500+ test failures spanning other files
- Manual assertion trace: all 16 tests PASS against implementation (detailed below)

### Lint
`cdp-spike.py` and `test_cdp_spike_778.py`: builder reports ruff clean. No new code modified by builder in either file — no lint regression possible.

### Source Control Changes
- `.owlbear/kanban/tasks/753-p0-02-execute-cdp-spike-on-corporate-laptop.md` — added `## Hash Stability Checklist (from #778)` section (steps 5a–5c); removed duplicate  
- `.owlbear/kanban/tasks/778-*.md` — status metadata only  
- `cdp-spike.py` — no changes (pre-existing implementation)  
- `test_cdp_spike_778.py` — no changes

### AC Compliance

| AC Line | Evidence | Mapped Tests | Status |
|---------|----------|-------------|--------|
| AC1: `--hash-stability` flag + checklist in #753 | `_parse_args` has `--hash-stability` at lines 159–160; diff confirms `## Hash Stability Checklist (from #778)` appended to task #753 body | `test_hash_stability_flag_accepted_by_argparse`, `test_hash_stability_flag_defaults_to_false`, `test_run_hash_stability_function_exists` | PASS |
| AC2: ≥2 pages × 3 extractions × 60s intervals | `_STABILITY_EXTRACTIONS=3`, `_STABILITY_INTERVAL=60`, loop calls `page.goto(url)` + `page.content()` per iteration; sleep guarded by `if i > 0` → 2 sleeps of 60s | `test_page_content_called_3_times_per_url`, `test_sleep_between_extractions_at_least_60_seconds`, `test_accepts_list_of_multiple_urls`, `test_extracts_all_urls_not_just_first` | PASS |
| AC3: Raw HTML + cleaned content hash comparison | `hashlib.sha256(html.encode())` for raw; `trafilatura.extract(...)` for cleaned; diffs logged via `difflib.unified_diff` | `test_trafilatura_called_per_extraction_for_cleaned_hash`, `test_logs_raw_html_hash_information`, `test_logs_cleaned_content_hash_information`, `test_logs_diff_output_when_cleaned_hashes_differ` | PASS |
| AC4: Go/no-go verdict logged | Per-URL `GO`/`NO-GO`/`FAIL` + `OVERALL` verdict via `_log_step`; `_run_hash_stability` aggregates across all URLs | `test_logs_go_verdict_when_all_cleaned_hashes_stable`, `test_logs_nogo_verdict_when_cleaned_hashes_unstable`, `test_none_from_trafilatura_does_not_raise`, `test_none_from_trafilatura_marks_url_as_fail_in_log`, `test_overall_verdict_logged_across_multiple_urls` | PASS |

### Manual Test Trace (all 16 tests)

1. `test_hash_stability_flag_accepted_by_argparse` — `_parse_args(["--hash-stability"])` → parser has `--hash-stability` with `action="store_true"` → no SystemExit, `args.hash_stability` exists → PASS ✓  
2. `test_hash_stability_flag_defaults_to_false` — `_parse_args([])` → `args.hash_stability == False` → PASS ✓  
3. `test_run_hash_stability_function_exists` — `_run_hash_stability` attribute on module → callable → PASS ✓  
4. `test_page_content_called_3_times_per_url` — 3 loop iterations each call `page.content()` → call_count=3 ≥ 3 → PASS ✓  
5. `test_sleep_between_extractions_at_least_60_seconds` — `if i > 0: time.sleep(60)` → 2 calls of 60s → len ≥ 2, each ≥ 60 → PASS ✓  
6. `test_accepts_list_of_multiple_urls` — no raise on 2-URL input → PASS ✓  
7. `test_extracts_all_urls_not_just_first` — 2 URLs × 3 iterations = 6 `page.content()` calls → PASS ✓  
8. `test_trafilatura_called_per_extraction_for_cleaned_hash` — 3 `trafilatura.extract()` calls per URL → PASS ✓  
9. `test_logs_raw_html_hash_information` — logs `f"...raw html hash={raw_hash[:12]}..."` → "raw" + "html" + "hash" in output → PASS ✓  
10. `test_logs_cleaned_content_hash_information` — logs `f"cleaned hash={ch[:12]}..."` → "hash" in output → PASS ✓  
11. `test_logs_diff_output_when_cleaned_hashes_differ` — varying extract returns → hashes differ → logs `"Hash stability: diff (first vs last extraction)..."` → "diff" in output → PASS ✓  
12. `test_logs_go_verdict_when_all_cleaned_hashes_stable` — same return value → all hashes identical → logs `"GO"` → PASS ✓  
13. `test_logs_nogo_verdict_when_cleaned_hashes_unstable` — varying returns → logs `"NO-GO"` → PASS ✓  
14. `test_none_from_trafilatura_does_not_raise` — None branch: `if cleaned is None: log; append(None)` → no TypeError → PASS ✓  
15. `test_none_from_trafilatura_marks_url_as_fail_in_log` — None → logs `"FAIL"` in verdict line → PASS ✓  
16. `test_overall_verdict_logged_across_multiple_urls` — logs `f"Hash stability: OVERALL verdict=..."` → "OVERALL" in output → PASS ✓  

### TestFromAC Modifications
None — builder made no changes to `test_cdp_spike_778.py`. All 4 `TestFromAC_*` classes preserved unmodified.

### Test Quality Assessment

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Call-count and sleep-interval assertions are strong numerical checks. Log-presence assertions (`test_logs_raw_*`, `test_logs_cleaned_*`) use broad keyword matching that would pass any log containing "raw"/"html"/"hash" — acceptable because behavioral assertions (call counts, verdicts) independently validate the implementation. |
| Negative/error-path | STRONG | None-from-trafilatura (does-not-raise + marks-as-FAIL), NO-GO path, FAIL verdict path |
| Mutation sensitivity | STRONG | Removing sleep → sleep call count fails. Removing URL iteration → content call count fails. Removing GO/NO-GO logging → verdict assertions fail. |
| Test independence | STRONG | Each test calls `_load_spike()` fresh; `sys.modules.pop("cdp_spike", None)` ensures clean slate; `patch.dict` scoping correct |
| Descriptive names | STRONG | All test names describe the behavior and condition under test |

### Security Review
No new system boundaries. Implementation uses only stdlib (`hashlib`, `difflib`, `time`). No user-controlled inputs reach file paths in the hash stability protocol. No hardcoded secrets or injection surfaces.

### Pass-Through Legitimacy
Pre-existing implementation pass-through is correctly applied: Architecture Review explicitly documented and approved this pattern; all tests were pre-written against pre-existing implementation; the "TDD COMPLIANCE: PASS" in the arch review is based on test existence and coverage, not RED sequence. Pipeline protocol is satisfied.

### Deductions
- **−0.02**: Quality-Runner not available — could not run tests via independent subprocess. Manual trace substituted with high confidence given complete implementation readability.
- **−0.02**: Log-presence assertions in AC3 tests use broad keyword matching (ADEQUATE, not STRONG). Compensated by call-count and hash-comparison behavioral tests.

### Verdict
Confidence: **0.94 → PASS**
[[2026-04-13]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | No production behavior/API change. cdp-spike.py is `.owlbear/scratch/` spike script — not in copilot-instructions.md scope. File has only 2 sections (Project Identity, Repository Branches). |
| 2 | Module docstrings | No | N/A | No production `.py` files modified. Builder confirmed cdp-spike.py unchanged (pre-existing implementation pass-through). |
| 3 | External attribution | Yes | Already done | `sources/overview.md` line 95 has `## Hash Stability Validation Protocol (Task #778)` with trafilatura API docs entry — added by prior pipeline agent. |
| 4 | README.md CLI changes | No | N/A | No production CLI changes. Scratch spike script only. |
| 5 | Research doc | Yes | Present | `.owlbear/research/778-hash-stability-protocol.md` exists and is referenced in task body (Validation pass section). |

**Files updated:** None  
**Scratch files cleaned:** None found (no `.owlbear/scratch/778-*` files)  
**Commit:** Skipped — no files updated
[[2026-04-13]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Hash stability protocol added to #753 execution checklist | `## Hash Stability Checklist (from #778)` at line 114 of task #753 body with steps 5a-5c; `--hash-stability` flag in `_parse_args` verified via passing test `test_hash_stability_flag_accepted_by_argparse` | PASS |
| AC2: Protocol tests at least 2 pages x 3 extractions x 60s intervals | Tests `test_page_content_called_3_times_per_url`, `test_sleep_between_extractions_at_least_60_seconds`, `test_accepts_list_of_multiple_urls`, `test_extracts_all_urls_not_just_first` all PASS (16/16) | PASS |
| AC3: Results compared at raw HTML and cleaned-content levels | Tests for raw HTML hash logging, cleaned content hash logging, diff output all PASS | PASS |
| AC4: Go/no-go verdict includes hash stability | Tests for GO, NO-GO, FAIL, OVERALL verdicts all PASS | PASS |

### Test Results
- pytest (task-scoped): 16 passed, 0 failed (test_cdp_spike_778.py)
- pytest (full suite): 4074 passed, 337 failed, 8 skipped (failures all pre-existing in unrelated files: test_analysis.py, test_bookmark_pipeline.py, test_orchestrator_loop.py, etc.)
- ruff: All checks passed

### Architect Quality: 4/5
AC is specific and verifiable across all 4 items. Edge case for trafilatura-None addressed. Minor gap: AC1 specifics (steps 5a-5c) derived from research S3.4 rather than inline, but architect guidance explicitly pointed there.

### Deduction Breakdown
- All 4 AC lines have specific evidence: no deduction
- Lint clean: no deduction
- AC quality 4/5: no deduction (threshold is <=3)
- Reviewer evidence present and detailed (PASS verdict, manual trace of all 16 tests): no deduction
- Full-suite failures in task scope: 0: no deduction
- Pre-existing implementation pass-through properly documented across all pipeline stages: no deduction

### Confidence: 1.00
### Action: archive