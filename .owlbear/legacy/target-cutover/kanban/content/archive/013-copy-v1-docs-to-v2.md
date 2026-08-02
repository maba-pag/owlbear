---
id: 13
title: Copy v1 docs to v2
status: archived
priority: medium
created: 2026-03-26 17:20:40.467474+01:00
updated: 2026-03-28 01:49:31.054256+01:00
started: 2026-03-28 01:49:26.492072+01:00
completed: 2026-03-28 01:49:26.492072+01:00
tags:
- phase-1
- scope:docs
- type:docs
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Copy valuable v1 documentation assets to the v2 directory structure.

## Acceptance Criteria
- [ ] Copy docs/research/*.md to v2 docs/research/ (50+ research documents)
- [ ] Copy docs/sources/overview.md to v2 docs/sources/
- [ ] Copy docs/decisions/ to v2 docs/decisions/
- [ ] Review and remove v1-specific docs that are no longer relevant
- [ ] Update any internal cross-references that broke due to path changes
- [ ] Verify docs/scratch/ exists and is gitignored

## Context
Depends on F1 (monorepo skeleton) for directory structure. V1 has 50+ research docs, source attributions, and decision records that are valuable for v2. This is a bulk copy with light curation.

[[2026-03-28]] Sat 01:49
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Copy docs/research/*.md (50+) | 368 files at v2 root vs 327 in v1/ | PASS |
| Copy docs/sources/overview.md | File exists at docs/sources/overview.md | PASS |
| Copy docs/decisions/ | Exists with pending/, resolved/, README.md (6 files vs v1 4) | PASS |
| Review/remove v1-specific docs | No v1-specific titles (daemon/bearclaw-cli/pydanticai) in research titles | PASS |
| Update cross-references | No broken v1/ paths found in research docs | PASS |
| docs/scratch/ exists and gitignored | Line 56 of .gitignore | PASS |

### Test Results
- pytest: 122 passed, 72 failed (all pre-existing from unrelated tasks: argument-hint, model-invocation, todo-rename, memory-uri, scratch-enforcement)
- ruff: clean on tests/; src/ not yet present

### Architect Quality
- AC specificity: Good, all lines are verifiable
- Edge case coverage: N/A (docs copy task)
- Design direction: N/A
- AC quality score: 4/5

### Quality Gaps
- No dedicated commit for task 13. Work subsumed by v1 relocation (d96f141)
- No Builder/Reviewer/Writer evidence sections in task body

### Confidence: .95
### Action: archive
