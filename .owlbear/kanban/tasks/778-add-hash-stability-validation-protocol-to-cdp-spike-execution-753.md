---
id: 778
title: Add hash stability validation protocol to CDP spike execution (#753)
status: todo
priority: needed
created: '2026-04-10T12:16:54.010932+00:00'
updated: '2026-04-13T00:03:52.719416+00:00'
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