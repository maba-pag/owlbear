---
id: 561
title: 'Add static test: reviewer tools list excludes write tools'
status: archived
priority: medium
created: 2026-04-02 23:11:12.717571+02:00
updated: 2026-04-04 07:10:05.372240+02:00
started: 2026-04-04 07:09:39.593761+02:00
completed: 2026-04-04 07:09:39.593761+02:00
tags:
- scope:agents
- test
- type:test
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/pretooluse-read-only-guard-feasibility.md s3.2 and s4.
Challenger alternative A1: static validation catches tools-list misconfiguration at commit time.

## Acceptance Criteria
- [ ] Add test in tests/ that parses reviewer.agent.md YAML frontmatter
- [ ] Assert tools list does not contain create_file, replace_string_in_file, multi_replace_string_in_file, or create_directory
- [ ] Test runs in existing test suite (uv run pytest)

[[2026-04-03]] Fri 00:59
## Architecture Review
**Verdict:** BLOCK (duplicate of archived #533)
**DR Verification:** N/A

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Parse reviewer.agent.md frontmatter | Already implemented in tests/test_reviewer_write_tools_533.py | Duplicate |
| Assert no write tools | Already implemented with edit/* prefix matching (9 tests) | Duplicate |
| Test runs in suite | tests/test_reviewer_write_tools_533.py already passing | Duplicate |

### Architecture Notes
Task #533 (archived, auditor confidence .98) already delivered this exact deliverable at tests/test_reviewer_write_tools_533.py with 9 passing tests. The existing test uses edit/* prefix matching which is superior to the snake_case names in this task's AC (create_file etc. never appear in .agent.md frontmatter, making the AC vacuously true).

This task was spawned from the same kanban-md create command in docs/research/pretooluse-read-only-guard-feasibility.md that produced #533. It is a duplicate creation artifact.

### Challenge Results
- Challenger: block
- Confidence in original: .10
- Key challenges: C1 (critical) exact duplicate of archived #533 with existing test file; C2 (critical) AC uses snake_case tool names that never appear in frontmatter, making test vacuously true
- Architect response: accepted all challenges, verified #533 exists and test file passes
