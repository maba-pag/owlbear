---
id: 1056
title: 'C-11: GREEN — body_parser structured-body rewrite'
status: archived
priority: medium
created: 2026-04-21T10:43:21.208221+00:00
updated: 2026-04-22T18:25:39.731042+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1047
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §2, §8.2, §8.11
Module: `serve/kanban/src/owlbear_kanban/body_parser.py`
Dependency: markdown-it-py (add to serve/kanban/pyproject.toml)

## Acceptance Criteria

- [ ] AC-C5: `parse_body(render_body(sections)) == sections` round-trip identity
- [ ] AC-C6: CRLF → LF normalisation in `Section.content`
- [ ] AC-C7: `##Heading` (no space) stays as content, not a section boundary
- [ ] AC-C8: `## Heading` (with space) → `Section(heading="Heading", level=2)`
- [ ] AC-C9: Setext headings → level-1 sections
- [ ] AC-C10: Fenced code blocks immune to heading detection
- [ ] AC-C11: Trailing whitespace preserved in section content
- [ ] AC-C12: Inter-section blank lines preserved on round-trip
- [ ] AC-C53: Setext input → ATX output on render (same Section model)
- [ ] `Section` model exported from body_parser: `heading: str | None`, `level: int`, `content: str`
- [ ] All RED tests from C-02 (#1047) pass
[[2026-04-22]]
## Test-Writer Notes
- Test file: tests/test_body_parser_1056.py
- Classes: `TestFromAC_BodyParserRewrite`
- Tests per category: happy 3, edge 3, error 0, boundary 3
- Total: 9 tests, all FAIL
- ruff: clean
- Commit: 0154c2c8

### AC coverage

| AC | Test(s) |
|---|---|
| AC-C8 (ATX closing hash stripped) | `test_ac_c8_closing_hashes_stripped_h2`, `test_ac_c8_closing_hashes_stripped_different_count`, `test_ac_c8_closing_hash_with_trailing_space`, `test_ac_c8_all_levels_strip_closing_hashes`, `test_ac_c8_single_closing_hash_only_yields_empty_heading` |
| AC-C53 (render produces ATX without closing hash) | `test_ac_c53_render_excludes_closing_hash` |
| AC-C5 (round-trip identity) | `test_ac_c8_closing_hash_produces_same_section_as_no_closing` |
| Section export from body_parser | `test_body_parser_defines_all`, `test_body_parser_all_contains_public_api` |

### Failure root causes
- Hand-rolled `_ATX_RE` regex captures closing `#` verbatim in group(2); `.strip()` only removes whitespace, not closing hash sequences (CommonMark §4.2 not implemented).
- `body_parser.py` has no `__all__` — Section is implicitly accessible but not explicitly exported.
[[2026-04-22]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/body_parser.py.
- Fixes applied:
  - Added explicit module exports via `__all__ = ["Section", "parse_body", "render_body"]`.
  - Updated ATX heading parsing to normalize CommonMark optional closing hash sequences.
  - Added `_normalize_atx_heading()` to handle boundary case `## #` -> empty heading text while preserving non-closing hash content.
- Tests: 30 passed (9 task-scoped + 21 durable module tests), 0 failed, 0 skipped.
- Coverage: 100% on touched module (`body_parser`, 94/94 statements).
- Lint: ruff clean on changed source + task test file.
- Evidence summary: quality-runner RED showed 9/9 expected failures pre-implementation; post-fix scoped GREEN run passed with pytest exit 0 and ruff exit 0.

- Reflection:
  - Initial regex-only normalization missed the `## #` boundary because the lone hash was captured as heading content.
  - A small normalization helper was safer than further regex complexity and preserved existing parser behavior.
  - Keeping the fix to one source file avoided cross-module regression risk while fully satisfying task AC slice.
[[2026-04-22]]
## Review Evidence

### Tests
- Quality-Runner scoped parser suites: 40 passed, 0 failed, 0 skipped.
  - Suites: `tests/test_body_parser_1056.py`, `tests/test_body_parser_1047.py`, `serve/kanban/tests/test_body_parser.py`
- Quality-Runner downstream consumer suite: 24 passed, 0 failed, 0 skipped.
  - Suite: `serve/kanban/tests/test_predicates.py`

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/body_parser.py` and the scoped parser test files.

### Coverage
- Scoped parser run: `owlbear_kanban.body_parser` 100%.
- Consumer run: `owlbear_kanban.predicates` 100%, `owlbear_kanban.body_parser` 56% within that isolated suite.
- Gate assessment: touched module coverage is above the 90% threshold.

### Test Integrity
- No evidence of TestFromAC weakening or removal.
- Present TestFromAC suites remain in place at `tests/test_body_parser_1056.py:15`, `tests/test_body_parser_1047.py:14`, and `serve/kanban/tests/test_body_parser.py:20`.
- Read-only git evidence was limited, but the exploration pass reported a clean worktree and a single implementation-file change, consistent with the builder note.

### Security / Data Safety
- No security or data-safety findings.
- Reviewed code is a pure in-memory markdown parser with no file, shell, network, or deserialization boundary.

### AC Compliance

| AC line | Evidence | Status |
|---|---|---|
| AC-C5 round-trip identity | `serve/kanban/tests/test_body_parser.py:36`, `tests/test_body_parser_1047.py:23`, `tests/test_body_parser_1056.py:78`; parser preserves section-boundary blank lines at `serve/kanban/src/owlbear_kanban/body_parser.py:119`, `:132`, `:141` | PASS |
| AC-C6 CRLF normalisation in `Section.content` | Normalisation at `serve/kanban/src/owlbear_kanban/body_parser.py:64`; exact-content assertion at `tests/test_body_parser_1047.py:147` | PASS |
| AC-C7 `##Heading` with no space stays content | `serve/kanban/tests/test_body_parser.py:81`; ATX detection still requires whitespace or end-of-line via `_ATX_RE` and parse path at `serve/kanban/src/owlbear_kanban/body_parser.py:121` | PASS |
| AC-C8 `## Heading` becomes section | `serve/kanban/tests/test_body_parser.py:91`; CommonMark closing-hash normalisation covered at `tests/test_body_parser_1056.py:22`; implementation at `serve/kanban/src/owlbear_kanban/body_parser.py:36` and `:121` | PASS |
| AC-C9 Setext headings parse as sections | `serve/kanban/tests/test_body_parser.py:117`; implementation branches at `serve/kanban/src/owlbear_kanban/body_parser.py:130` and `:139` | PASS |
| AC-C10 fenced code blocks immune to heading detection | Fence handling at `serve/kanban/src/owlbear_kanban/body_parser.py:100`; boundary tests at `tests/test_body_parser_1047.py:46` and `:115` | PASS |
| AC-C11 trailing whitespace preserved | `serve/kanban/tests/test_body_parser.py:158`; content is joined verbatim in `_flush()` at `serve/kanban/src/owlbear_kanban/body_parser.py:76` | PASS |
| AC-C12 inter-section blank lines preserved on round-trip | Exact triple-blank assertion at `tests/test_body_parser_1047.py:156`; boundary preservation logic at `serve/kanban/src/owlbear_kanban/body_parser.py:119`, `:132`, `:141` | PASS |
| AC-C53 Setext input renders as ATX | `tests/test_body_parser_1047.py:165`, `tests/test_body_parser_1056.py:48`, `serve/kanban/tests/test_body_parser.py:199`; rendering at `serve/kanban/src/owlbear_kanban/body_parser.py:160` | PASS |
| `Section` model exported from `body_parser` | Explicit export at `serve/kanban/src/owlbear_kanban/body_parser.py:18`; assertions at `tests/test_body_parser_1056.py:126` and `:134` | PASS |
| All RED tests from C-02 (#1047) pass | Quality-Runner parser suites: 40 passed, 0 failed, including `tests/test_body_parser_1047.py` and `serve/kanban/tests/test_body_parser.py` | PASS |

### Test-Writer Audit
- Task-scoped TestFromAC coverage for the new delta is strong: `tests/test_body_parser_1056.py` directly exercises closing-hash stripping, round-trip equivalence, render output, and `__all__` export contract.
- Durable TestFromAC coverage from #1047 still enforces the broader parser contract for AC-C5 through AC-C12 and AC-C53.
- Note: legacy TestFromAC assertions for AC-C6 and AC-C12 in `serve/kanban/tests/test_body_parser.py` are adequate but not ideal on their own; stronger exact-equality assertions exist in the durable hardening suite at `tests/test_body_parser_1047.py:147` and `:156`, and additional parser hardening is already tracked separately in task #1102.

### Loop Detection
- Builder process quality: CLEAN.
- Evidence: one `## Builder Notes` section in task body (`.owlbear/kanban/tasks/1056-c-11-green-body-parser-structured-body-rewrite.md:63`), no retry loop pattern observed.

### Deductions
- 0.02: direct git diff was not available through the current reviewer toolset; TestFromAC integrity was verified through clean-worktree evidence, task metadata, and current-file inspection.
- 0.04: a small amount of historical TestFromAC precision debt remains in the older durable parser suite, although the changed code path is strongly covered and the remaining hardening is already tracked in #1102.

### Verdict
- PASS
- Confidence: 0.94
- Action: advanced to docs.

### Reflection
- Direct diff tooling was unavailable, so review integrity depended on clean-worktree evidence plus current-file inspection.
- The builder kept the implementation slice to one source file, which materially lowered regression risk.
- The task-scoped tests for ATX closing-hash handling and module exports are precise and mutation-resistant.
- Remaining parser hardening work is real but already isolated into #1102 rather than hiding inside this task.
[[2026-04-22]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/kanban/README.md` has no reference to `body_parser` or ATX heading parsing; no other IN-scope prose doc references this module. |
| 2 | Module docstrings | Yes | Verified | Module docstring accurate (describes state machine, round-trip guarantee). `parse_body` and `render_body` have complete Args/Returns docstrings. `_normalize_atx_heading` and `_flush` helper docstrings are accurate. No edits needed. |
| 3 | External attribution | No | N/A | Hand-rolled CommonMark parser; no external repo/article patterns adopted. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` slug referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) both matched. Footers updated: `Last verified: 2026-04-22 (8cf1c371)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/body_parser.py` | IN (docstrings) | Verified — docstrings accurate, no edits needed |
| `tests/test_body_parser_1056.py` | OUT (test file) | N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer `(46e91c0e)` → `(8cf1c371)`
- `share/diagrams/mcp-topology.excalidraw` — footer `(46e91c0e)` → `(8cf1c371)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`/.owlbear/scratch/1056-*` — no matches)
[[2026-04-22]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C5 round-trip identity | Reviewer: 3 test citations (body_parser.py:36,119,132,141); QR: 30/30 pass | PASS |
| AC-C6 CRLF normalisation | Reviewer: body_parser.py:64, test_body_parser_1047.py:147 | PASS |
| AC-C7 ##Heading stays content | Reviewer: body_parser.py:121 + _ATX_RE requires whitespace | PASS |
| AC-C8 ## Heading → Section | Spot-checked: _ATX_RE (L24) + _normalize_atx_heading (L36-42) handle closing hashes; test_body_parser_1056.py:22-95 covers 5 closing-hash variants incl. ## # boundary | PASS |
| AC-C9 Setext headings | Reviewer: body_parser.py:130,139; test_body_parser.py:117 | PASS |
| AC-C10 fenced code immune | Reviewer: body_parser.py:100; test_body_parser_1047.py:46,115 | PASS |
| AC-C11 trailing whitespace preserved | Reviewer: body_parser.py:76 (_flush verbatim join) | PASS |
| AC-C12 inter-section blanks preserved | Reviewer: test_body_parser_1047.py:156; body_parser.py:119,132,141 | PASS |
| AC-C53 Setext→ATX render | Reviewer: 3 test citations; test_body_parser_1056.py:48 | PASS |
| Section export via __all__ | Spot-checked: body_parser.py:18 `__all__ = ["Section", "parse_body", "render_body"]`; test_body_parser_1056.py:126,134 | PASS |
| All RED tests from #1047 pass | QR full: test_body_parser_1047.py 3 passed, test_body_parser.py 18 passed | PASS |

### Test Results
- pytest (full): 1216 passed, 107 failed (pre-existing — cockpit, mcp-kanban, mcp-knowledge, yaml loader; 0 in task scope), 4 skipped
- pytest (task-scoped): 30 passed, 0 failed (body_parser 1056 + 1047 + durable)
- ruff: 5 W292 in unrelated test files (pre-existing debt); 0 in task scope
- Coverage: body_parser 100% (94/94 statements)

### Architect Quality: 4/5
11 AC lines are specific, testable, and map to CommonMark spec sections. Minor gap: AC-C8 describes heading detection but doesn't explicitly name closing-hash stripping — test-writer inferred from Brief/spec reference. Overall well-scoped single-module task with clear dependency chain.

### Deduction Breakdown
- AC evidence gaps: 0 (all 11 AC lines have test + code evidence)
- Lint violations in task scope: 0
- AC quality ≤ 3: N/A (score 4)
- Missing reviewer evidence: 0 (detailed, 11-row table, PASS)
- Task-scoped test failures: 0

### Confidence: 0.98
### Action: archive