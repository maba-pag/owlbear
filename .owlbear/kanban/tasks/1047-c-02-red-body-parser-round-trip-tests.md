---
id: 1047
title: 'C-02: RED — body_parser round-trip tests'
status: todo
priority: needed
created: 2026-04-21T10:42:50.247058+00:00
updated: 2026-04-21T13:03:26.388680+00:00
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
claimed_at: 2026-04-21T13:03:26.388680+00:00
---
## Brief
Brief C (#1043) — paper-c.md §8.2, §8.11
Module: `serve/kanban/tests/test_body_parser.py`

## Acceptance Criteria

- [ ] AC-C5: `parse_body(render_body(sections)) == sections` round-trip identity
- [ ] AC-C6: CRLF in input normalised to LF in `Section.content`
- [ ] AC-C7: `##Heading` (no space) preserved verbatim as content, never promoted to section boundary
- [ ] AC-C8: `## Heading` (with space) creates `Section(heading="Heading", level=2, ...)`
- [ ] AC-C9: Setext headings (`Heading\n===`) create level-1 sections
- [ ] AC-C10: Code-fenced content containing `## Looks-like-heading` does NOT create a section
- [ ] AC-C11: Trailing whitespace within section content preserved
- [ ] AC-C12: Inter-section blank lines preserved on round-trip
- [ ] AC-C53: Setext-heading input round-trips through write as ATX-heading output (same Section model)
- [ ] All tests fail (RED phase — no implementation exists yet)