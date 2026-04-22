---
id: 1056
title: 'C-11: GREEN — body_parser structured-body rewrite'
status: review
priority: needed
created: 2026-04-21T10:43:21.208221+00:00
updated: 2026-04-22T06:24:48.992920+00:00
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