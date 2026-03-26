---
id: 819
title: Tests for kanban_list block_filter enum replacement
status: archived
priority: nice-to-have
created: 2026-03-15T08:04:09.9415143+01:00
updated: 2026-03-26T16:13:15.0404+01:00
started: 2026-03-26T16:13:15.0404+01:00
completed: 2026-03-26T16:13:15.0404+01:00
tags:
    - test
    - tools
blocked: true
block_reason: 'Empty body: no acceptance criteria defined. Test-writer cannot proceed without a contract. Needs architect to specify the enum interface, affected files, and testable AC.'
class: standard
---

[[2026-03-23]] Mon 17:54
## Test-Writer Notes
BLOCKED: task body is entirely empty - no acceptance criteria, no context, no files listed. Cannot write tests without a defined contract. Returning to backlog for architect review.

What is needed:
- Define the interface change: is block_filter moving from Literal to a Python Enum? Which enum class? Where is it defined?
- Specify which file(s) to update and which existing tests (if any) to update.
- Define testable acceptance criteria per AC line.

[[2026-03-26]] Thu 16:12
## Architecture Review
**Verdict:** Delete (duplicate)

### Finding
Task #819 is a duplicate of archived task #820 (same title, same scope).
The entire block_filter enum replacement work is already complete:
- #820 (RED tests): archived, TestFromAC_BlockFilterEnum exists in tests/test_kanban_tools.py
- #534 (GREEN impl): archived, kanban_list() uses Literal enum in src/owlbear/tools/kanban.py

No new work is possible or needed. Deleting as redundant.

[[2026-03-26]] Thu 16:12
## Architecture Review
**Verdict:** Delete (duplicate)

### Finding
Task #819 is a duplicate of archived task #820 (same title, same scope).
The entire block_filter enum replacement work is already complete:
- #820 (RED tests): archived, TestFromAC_BlockFilterEnum exists in tests/test_kanban_tools.py
- #534 (GREEN impl): archived, kanban_list() uses Literal enum in src/owlbear/tools/kanban.py

No new work is possible or needed. Deleting as redundant.
