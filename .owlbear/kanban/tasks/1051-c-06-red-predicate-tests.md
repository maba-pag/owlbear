---
id: 1051
title: 'C-06: RED — predicate tests'
status: in-progress
priority: important
created: 2026-04-21T10:42:50.287239+00:00
updated: 2026-04-21T17:20:00.090056+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §8.8
Module: `serve/kanban/tests/test_predicates.py`

## Acceptance Criteria

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup, returns true iff matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed (list[Section] instead of regex)
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes

**Situation:** `predicates.py` implementation already exists — builder ran ahead of test-writer in this batch. All tests pass (21/21), ruff clean.

**Test file:** `serve/kanban/tests/test_predicates.py`
**Classes:**
- `TestFromAC_RequiredSections` (12 tests) — AC-C39, AC-C41
- `TestFromAC_RequireListInSection` (9 tests) — AC-C40, AC-C41

**Categories:**
- Happy path: 4 (exact match, bullet list, ordered list, case-insensitive)
- Edge: 5 (empty required list, preamble heading=None, empty content, whitespace stripping)
- Error/boundary: 12 (one-missing, not-present, code-fence, no-space-##, multi-section)

**AC Coverage:**
| AC | Tests |
|----|-------|
| C39 case-insensitive, whitespace-stripped heading | 9 |
| C40 list detection (bullet/ordered), same lookup | 9 |
| C41 semantic equivalence to Brief B D64 | 2 |

**Fail verification:** N/A — implementation already existed when task was claimed. Tests pass against the extant implementation. Passing through to builder.