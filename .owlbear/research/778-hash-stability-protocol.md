# Hash Stability Validation Protocol — CDP Spike Extension

> **Owning task:** #778 — Add hash stability validation protocol to CDP spike execution (#753)
> **Date:** 2026-04-11 **Status:** Complete

## 1. Context and Question

#774 research §3.3 identified that content hash stability was untested in the
CDP spike. The hash function (`compute_content_hash`, SHA-256) is deterministic,
but the **input** to the hash (trafilatura output on live pages) may vary across
extractions due to dynamic HTML elements leaking through trafilatura's heuristics.
This task designs the validation protocol and determines where it belongs.

Research questions: (1) Does automated hash stability testing belong in the spike
script or as manual checklist steps? (2) What is the implementation approach?
(3) Is there a dependency on #777 (trafilatura expansion)?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | #774 research §3.3 — hash stability protocol | .owlbear/research/774-edge-cdp-spike.md | .95 |
| 2 | #777 research — trafilatura spike expansion | .owlbear/research/777-trafilatura-spike-expansion.md | .95 |
| 3 | compute_content_hash() implementation | serve/knowledge/src/owlbear_knowledge/status_store.py | .90 |
| 4 | Production extractor.py + cleaner.py | serve/browser/src/owlbear_browser/ | .90 |
| 5 | Cleaner idempotency tests (#756) | tests/test_cleaner_756.py:211-250 | .85 |
| 6 | #753 execution checklist | Kanban task body — architecture review section | .90 |
| 7 | trafilatura Python API docs | trafilatura.readthedocs.io/en/latest/usage-python.html | .80 |

## 3. Analysis

### 3.1 Instability Risk Layers

| Layer | Deterministic? | Risk source | Mitigation |
|-------|---------------|-------------|------------|
| CDP `page.content()` | No | Timestamps, session avatars, dynamic footers | Expected to vary |
| trafilatura extraction | Yes (same input → same output) | Dynamic HTML leaking through heuristics | `prune_xpath` |
| `compute_content_hash()` | Yes (SHA-256 on `.strip()`) | None | N/A |

The cleaner tests (test_cleaner_756.py) validate idempotency for *static* HTML.
The untested scenario is: does `page.content()` on the *same* live page return
sufficiently similar HTML that trafilatura produces identical cleaned output?

### 3.2 Implementation Approach — Trade-off Matrix

| Aspect | A: Automated in spike | B: Manual checklist only | C: Separate script |
|--------|----------------------|------------------------|--------------------|
| User effort | Low — script runs 3 iterations | High — 3 manual runs + manual diff | Medium |
| Result quality | Exact SHA-256 comparison | Human eyeball comparison | Exact comparison |
| LOC in cdp-spike.py | ~30-40 | 0 | ~60 (new file) |
| KISS score | .85 | .70 | .60 |
| Depends on #777? | Yes — needs trafilatura in spike | No — user runs trafilatura manually | No |
| Go/no-go automation | Automated verdict | User judgment | Automated verdict |

### 3.3 Undeclared Dependency on #777

#778 depends on #776 (spike script exists), declared. But hash stability
validation requires trafilatura extraction output — which #777 adds. Two options:

| Option | Pros | Cons |
|--------|------|------|
| Add `depends_on: [777]` | Clean dependency chain; reuse #777's trafilatura code | Blocks #778 implementation until #777 is done |
| Self-contained trafilatura call | No dependency; can proceed independently | ~10 LOC overlap with #777 |

**Recommendation:** Add `depends_on: [777]`. The hash stability loop reuses
#777's trafilatura extraction — duplicating it violates DRY. Since both are
Phase 0 spike extensions, sequential ordering (#777 → #778) is natural.

### 3.4 Recommended Protocol Implementation (Option A)

After #777's trafilatura extraction is in the spike, add `--hash-stability` flag:

```
for url in target_urls:
    hashes = []
    for i in range(3):
        page.goto(url, wait_until="networkidle")
        raw_html = page.content()
        cleaned = trafilatura.extract(raw_html, ...)
        raw_hash = sha256(raw_html.encode()).hexdigest()
        clean_hash = sha256(cleaned.encode()).hexdigest()
        hashes.append((raw_hash, clean_hash, cleaned))
        if i < 2: time.sleep(60)

    raw_stable = len(set(h[0] for h in hashes)) == 1
    clean_stable = len(set(h[1] for h in hashes)) == 1
    log(url, raw_stable, clean_stable)

    if not clean_stable:
        # Diff cleaned outputs, try prune_xpath
        ...
```

**Checklist additions to #753:** Add steps 5a-5c after step 5:
- 5a. Run with `--hash-stability` flag (adds ~6 min per URL)
- 5b. Check console output: "Hash stability: PASS/FAIL" per URL
- 5c. If FAIL: inspect diff output, check for dynamic element patterns

**Go/no-go matrix addition:**

| CDP | SSO | EDR | DLP | Hash stable | Decision |
|-----|-----|-----|-----|-------------|----------|
| ✓ | ✓ | Clean | Clean | ✓ | **GO** |
| ✓ | ✓ | Clean | Clean | ✗ + prune fixes it | **CONDITIONAL GO** |
| ✓ | ✓ | Clean | Clean | ✗ + prune doesn't fix | **NO-GO** for hash approach |

### 3.5 What Constitutes "Stable"?

- Raw HTML hashes: **expected to differ** — timestamps, CSRF tokens, session data
- Cleaned (trafilatura) hashes: **must match** across all 3 extractions
- If cleaned hashes differ: `difflib.unified_diff` on cleaned text reveals leaking elements
- `prune_xpath` remediation: try known SharePoint XPaths from #759 research §3c

## 4. Recommendation (.85 confidence)

**Option A: Automated hash stability loop in cdp-spike.py** behind
`--hash-stability` flag. Add `depends_on: [777]` since it reuses #777's
trafilatura extraction code. Add 3 checklist items and 1 go/no-go row to #753.

~30-40 LOC addition to the spike. The builder implements the loop, the diff
logic, and `prune_xpath` fallback. The user executes via #753's checklist.

Challenge: FALLBACK — implementation approach is prescribed by task AC and
#774 §3.3; no controversial technical trade-off.

## 5. Follow-up Tasks

None beyond the task itself (#778 moves to backlog for implementation).
The builder adds code to cdp-spike.py and updates #753's checklist.
Dependency update needed: add #777 to #778's `depends_on`.
