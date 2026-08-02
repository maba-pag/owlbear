---
id: 759
title: 'P1-06: Impl — HTML→markdown cleaner'
status: archived
priority: medium
created: '2026-04-10T10:55:57.210371+00:00'
updated: '2026-04-13T04:27:46.632250+00:00'
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
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_html_markdown_cleaner_759.py
- Classes: TestFromAC_LxmlExplicitDependency
- Tests per category: happy 1, edge 0, error 0, boundary 2
- Total: 3 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 — TestFromAC_* in test_cleaner_756.py pass | Existing file, tests pass already | Pre-existing ✓ |
| AC2 — TestFromAC_* in test_browser_content_775.py pass (StripNoise/HtmlToMarkdown/SharePointPatterns/ContentNormalization/DeterministicOutput) | Existing file, tests pass already | Pre-existing ✓ |
| AC3 — TestFromAC_* in test_sharepoint_normalization_829.py pass | Existing file, tests pass already | Pre-existing ✓ |
| AC4 — lxml>=4.9 explicit in serve/browser/pyproject.toml | 3 new failing tests | RED ✗ |

### Why only AC4 has new tests
AC1–AC3 reference test files created during predecessor tasks (#756, #828, #829). All those TestFromAC_* tests exist and pass against the completed implementation. The only uncovered AC line was AC4: lxml is not in serve/browser/pyproject.toml (current deps: playwright>=1.40, trafilatura>=1.6 only). The 3 new tests drive the builder to add `lxml>=4.9` explicitly.

### Failure evidence (pytest -p no:logfire)
```
FAILED test_lxml_present_in_browser_dependencies       — AssertionError: lxml is not listed; current deps: ['playwright>=1.40', 'trafilatura>=1.6']
FAILED test_lxml_version_constraint_includes_gte_4_9   — AssertionError: lxml not found in dependencies
FAILED test_lxml_dep_has_no_strict_upper_pin           — AssertionError: lxml not found in dependencies
3 failed in 3.73s
```
[[2026-04-13]]
## Builder Notes

### Files Changed
- `serve/browser/pyproject.toml` — added `lxml>=4.9` to `project.dependencies`

### Test Results
- `test_html_markdown_cleaner_759.py` — 3/3 passed (RED → GREEN)
- `test_cleaner_756.py` + `test_browser_content_775.py` + `test_sharepoint_normalization_829.py` — 143/143 passed (AC1–AC3 pre-existing, all green)
- Total: 146 passed, 0 failed

### Coverage
Not measured separately — single-line config change with no code logic to cover.

### Lint
ruff: clean (exit 0)

### Evidence Summary
- RED verified: 3 tests failing before change (`lxml` absent from pyproject.toml)
- GREEN verified: 3 tests passing after adding `lxml>=4.9` at correct position
- Constraint satisfies all 3 test assertions: entry present, `>=4.9` present, no `==` pin
- Pre-existing AC1–AC3 tests unaffected

### Fixes Applied
Added `lxml>=4.9` as explicit dependency in `serve/browser/pyproject.toml`. One-line change; no implementation code touched.
[[2026-04-13]]
## Review Evidence

**Tests:** 146 passed, 0 failed (pytest exit 0). Scope: test_html_markdown_cleaner_759.py (3 new), test_cleaner_756.py, test_browser_content_775.py, test_sharepoint_normalization_829.py.

**Lint:** cleaner.py — ruff clean (exit 0). test_html_markdown_cleaner_759.py — ruff had infrastructure-level KeyboardInterrupt (4 attempts), not a code violation; file manually verified clean (67 lines, stdlib-only imports, no unused vars).

**Coverage:** owlbear_browser/cleaner — 100%.

**Changed files:** serve/browser/pyproject.toml only — `lxml>=4.9` added to project.dependencies.

**AC Compliance:**
| AC | Evidence | Status |
|----|----------|--------|
| AC1 — TestFromAC_* in test_cleaner_756.py pass | 146 passed | PASS |
| AC2 — TestFromAC_* in test_browser_content_775.py pass | 146 passed | PASS |
| AC3 — TestFromAC_* in test_sharepoint_normalization_829.py pass | file exists, 146 passed | PASS |
| AC4 — lxml>=4.9 in serve/browser/pyproject.toml | confirmed at line 7, no == pin | PASS |

**Assertion quality:** All 3 new tests catch the broken state (absent dep) and defective states (no version floor, exact pin). Meaningful, not vacuous.

**TestFromAC_* integrity:** Builder changed only pyproject.toml. No test modifications.

**Deductions:** −0.02 (ruff not tool-verified on test file — manual review substituted).

**Confidence: .98 → PASS**
[[2026-04-13]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|---------|
| 1 | copilot-instructions.md | No | N/A | Change was `lxml>=4.9` added to pyproject.toml dep list — no behavior/API/convention change. copilot-instructions.md contains no dependency tables. |
| 2 | Module docstrings | No (already complete) | PASS | `cleaner.py`: module-level docstring names all 3 public functions. `strip_noise()`, `html_to_markdown()`, `clean()`, `_normalize_content()`, and all dispatch helpers carry accurate per-function docstrings. #759 added no new functions. |
| 3 | sources/overview.md | Yes — already present | PASS | "HTML→Markdown Cleaner (Task #759)" section exists with 3 source rows (trafilatura API, trafilatura benchmarks, markdownify). No new sources were used in the builder phase (pyproject.toml edit only). |
| 4 | README.md CLI changes | N/A | N/A | No CLI surface touched. |
| 5 | Research doc | Yes | PASS | `.owlbear/research/759-html-markdown-cleaner.md` exists and is referenced in task body. |
| 6 | Scratch files | None | PASS | No `.owlbear/scratch/759-*` files found. |

**Files updated:** none — all documentation already complete from predecessor tasks (#756, #829).
**Commit:** none required.
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — TestFromAC_* in test_cleaner_756.py pass | 4,076 passed in full suite; test_cleaner_756.py not in 335-failure list | PASS |
| AC2 — TestFromAC_* in test_browser_content_775.py pass | Same full-suite run; file not in failure list | PASS |
| AC3 — TestFromAC_* in test_sharepoint_normalization_829.py pass | Same full-suite run; file exists, not in failure list | PASS |
| AC4 — lxml>=4.9 in serve/browser/pyproject.toml | Verified directly: line 7, `"lxml>=4.9"`, no == pin | PASS |

### Test Results
- pytest: 4,076 passed, 335 failed, 8 skipped. All 335 failures are pre-existing cross-task regressions (AppContext kanban_bin removal: 246, browser tool signature changes: ~60, planner selector: 10, missing lint-changed.ps1: 18). Zero failures in task scope.
- ruff: clean (exit 0)

### Architect Quality: 4/5
AC1-AC3 were "pre-existing tests pass" (unusual but valid since this is a GREEN phase for a RED phase that already has tests). AC4 was the only new requirement and was specific, actionable, and verifiable. Minor gap: AC could have been clearer that AC1-AC3 are regression-guard items, not new test targets.

### Deduction Breakdown
- AC lines: all 4 have specific evidence → -0.00
- Lint: clean → -0.00
- AC quality 4/5 (>3) → -0.00
- Reviewer evidence: present, detailed, PASS at .98 → -0.00
- Full-suite failures in task scope: 0 → -0.00
- Uncommitted builder deliverable (pyproject.toml) → -0.01

### Confidence: .99
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f8b83671 | test | tests/test_html_markdown_cleaner_759.py | #759 |
| 6f0438f3 | feat | serve/browser/pyproject.toml | #759 |