---
id: 759
title: 'P1-06: Impl — HTML→markdown cleaner'
status: todo
priority: needed
created: '2026-04-10T10:55:57.210371+00:00'
updated: '2026-04-12T22:40:12.500641+00:00'
tags:
- phase-1
- scope:browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. `serve/browser/src/owlbear_browser/cleaner.py`:
- HTML→markdown with boilerplate stripping
- SharePoint-specific normalization
- Idempotent output for stable hashing

All P1-05 (#756) tests pass.

Parent: #751

[[2026-04-12]]
## Research
- Research doc: .owlbear/research/759-html-markdown-cleaner.md
- Sources: 9 studied, 5 high-relevance
- Validation pass: existing research confirmed current. Implementation complete and diverged from recommendation (lxml direct vs trafilatura prune_xpath — more KISS-aligned).
- Implementation verified: cleaner.py (236 LOC) — strip_noise(), html_to_markdown(), clean(), _normalize_content(). 12 noise classes, 5 noise IDs, 1 noise role. Zero-width char stripping, \r removal, whitespace normalization.
- Tests: 118/118 pass (test_cleaner_756.py + test_browser_content_775.py)
- Follow-up tasks #828 (tests) and #829 (impl) both done.
- Recommendation: lxml-based approach (confidence: .85)
- Follow-up tasks created: none — all covered by #828/#829 (done)
- Decision requests: none
[[2026-04-12]]
## Architecture Review

### Context
GREEN phase task for `serve/browser/src/owlbear_browser/cleaner.py`. Implementation already complete (236 LOC, committed during #756). Research doc validated approach: lxml-based direct approach diverged from trafilatura recommendation, assessed as more KISS-aligned (confidence .85). Parent #751 is the authenticated content pipeline epic.

### AC Refinement (binding for test-writer/builder)
Original AC bullets are descriptive. Binding AC for pipeline:
- AC1: All `TestFromAC_*` tests in `test_cleaner_756.py` pass (header/sidebar stripping, SharePoint boilerplate, normalization, idempotency)
- AC2: All `TestFromAC_*` tests in `test_browser_content_775.py` that exercise cleaner.py pass (StripNoise, HtmlToMarkdown, SharePointPatterns, ContentNormalization, DeterministicOutput classes)
- AC3: All `TestFromAC_*` tests in `test_sharepoint_normalization_829.py` pass (SharePoint class/ID patterns, zero-width char stripping, idempotent output)
- AC4: `lxml` must be listed as an explicit dependency in `serve/browser/pyproject.toml` (`lxml>=4.9`) — cleaner.py imports it directly but it is currently only a transitive dep of trafilatura

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module, one purpose: HTML noise stripping + markdown conversion |
| Interface clarity | PASS | 3-function public API: `strip_noise()`, `html_to_markdown()`, `clean()`. AC refined above. |
| Dependency correctness | FLAG | `depends_on` is `[]`, should be `[756]` (RED phase precedes GREEN). #756 at `review`, effectively satisfied. See correction below. |
| Module layering | PASS | `cleaner.py` within `serve/browser/src/owlbear_browser/`, consumed by `extractor.py` in same package. No upward imports. |
| TDD compliance | PASS | #756 is the preceding RED-phase task. Tests exist (40+ in test_cleaner_756.py, 60+ in test_browser_content_775.py, 30+ in test_sharepoint_normalization_829.py). |
| KISS/YAGNI | PASS | lxml-based approach is 236 LOC vs trafilatura wrapping. Minimal. |
| Premise challenge | PASS | No existing HTML→markdown cleaner in the codebase. Needed by browser pipeline. |
| Pattern consistency | PASS | Frozensets for config, lxml for parsing, empty-input guards, recursive element dispatch. |
| Security surface | PASS | In-memory HTML processing only. No user input at boundary, no external I/O, no file writes. lxml is battle-tested against malicious HTML. |
| Single domain | PASS | `scope:browser` only. |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `strip_noise("")` | Empty/whitespace input | None | Yes — returns `""` | None |
| `lxml_html.document_fromstring()` | Malformed HTML | lxml recovers | Yes — lxml tolerant parser | None |
| `_elem_to_md()` | Non-string tag (comments) | None | Yes — returns `el.tail or ""` | None |

### Challenge Results
- Challenger: RECONSIDER (confidence .78)
- Primary concern: `lxml` is imported directly in cleaner.py but not listed in `serve/browser/pyproject.toml` — only arrives as trafilatura transitive dep. If trafilatura dropped lxml, cleaner breaks at import.
- Secondary: empty `depends_on` should be `[756]`
- Architect response: ACCEPTED — both concerns valid. lxml dependency added as binding AC4. depends_on correction flagged below.

DEPENDS_ON-CORRECTION: task #759 should have depends_on [756]

### Informational Notes
- Tasks #828 and #829 referenced in body as "both done" but are no longer on the board (deleted/archived). No action needed.
- Research recommended trafilatura; implementation used lxml directly. Research notes this divergence as "more KISS-aligned" — confirmed by code review.
- No uv.lock in workspace; transitive dependency risk is real without explicit declaration.

### Verdict: APPROVE
### Action Taken: Advanced #759 to todo. Binding AC refined in review note. DEPENDS_ON-CORRECTION flagged for orchestrator. lxml explicit dep required as AC4.