---
id: 1051
title: 'C-06: RED — predicate tests'
status: todo
priority: important
created: 2026-04-21T10:42:50.287239+00:00
updated: 2026-04-21T13:03:33.769466+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by: strong-stag
claimed_at: 2026-04-21T13:03:33.769466+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.8
Module: `serve/kanban/tests/test_predicates.py`

## Acceptance Criteria

- [ ] AC-C39: `required_sections` matches `Section.heading` case-insensitively, with surrounding whitespace stripped
- [ ] AC-C40: `require_list_in_section` uses same case-insensitive, whitespace-stripped heading lookup, returns true iff matched section's content parses to at least one CommonMark list (`bullet_list` or `ordered_list`)
- [ ] AC-C41: Predicate behaviour matches Brief B D64 semantically; only the implementation substrate changed (list[Section] instead of regex)
- [ ] All tests fail (RED phase — no implementation exists yet)