---
id: 1060
title: 'C-15: GREEN — predicates section-based rewrite'
status: todo
priority: important
created: 2026-04-21T10:43:41.533670+00:00
updated: 2026-04-21T10:43:41.533670+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1051
- 1056
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §6, §8.8
Module: `serve/kanban/src/owlbear_kanban/predicates.py`

Rewrite predicates to traverse `list[Section]` from body_parser (#1056) instead of regex on raw markdown.

## Acceptance Criteria

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped
- [ ] AC-C40: `require_list_in_section` — same case-insensitive heading lookup, returns true iff matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 semantically; implementation substrate changed (list[Section] not regex)
- [ ] All RED tests from C-06 (#1051) pass