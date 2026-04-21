---
id: 1056
title: 'C-11: GREEN — body_parser structured-body rewrite'
status: todo
priority: needed
created: 2026-04-21T10:43:21.208221+00:00
updated: 2026-04-21T10:43:21.208221+00:00
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