---
id: 661
title: 'Improve test coverage: agent_def.py (91%) + context.py (91%)'
status: archived
priority: important
created: 2026-03-08T01:59:29.9522472+01:00
updated: 2026-03-09T19:32:24.1231668+01:00
started: 2026-03-08T04:12:38.9378599+01:00
completed: 2026-03-09T19:32:24.1231668+01:00
tags:
    - coverage-sprint
    - scope:core
    - test
class: standard
---

## Coverage Gap
agent_def.py: 91% (4 of 46 stmts uncovered)  lines 80-81, 116-117
context.py: 91% (3 of 33 stmts uncovered)  lines 76-78

## Acceptance Criteria
- [ ] Coverage >= 95% for src/owlbear/core/agent_def.py
- [ ] Coverage >= 95% for src/owlbear/memory/context.py
- [ ] Tests cover agent_def uncovered load/parse branches
- [ ] Tests cover context.py uncovered update/retrieval paths
- [ ] All new tests pass, ruff clean

[[2026-03-09]] Mon 19:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 95% agent_def.py | 46 stmts, 0 miss, 100% | PASS |
| Coverage >= 95% context.py | 33 stmts, 0 miss, 100% | PASS |
| Tests cover agent_def L80-81, L116-117 | test_no_closing_delimiter_raises + test_yaml_not_mapping_raises | PASS |
| Tests cover context.py L76-78 | 3 MEMORY.md tests exercise the branch | PASS |
| All new tests pass, ruff clean | 27/27 pass, ruff All checks passed | PASS |

### Test Results
- pytest (scoped): 27 passed
- pytest (full): 1315 passed, 2 failed (pre-existing env: slack_sdk missing, Win PermissionError), 20 skipped
- ruff: All checks passed

### Confidence: .98
### Action: archive

[[2026-03-09]] Mon 19:32
## Audit
### AC Verification
- Coverage agent_def.py: 100% (46 stmts, 0 miss) - PASS
- Coverage context.py: 100% (33 stmts, 0 miss) - PASS
- agent_def L80-81,L116-117: test_no_closing_delimiter_raises + test_yaml_not_mapping_raises - PASS
- context.py L76-78: 3 MEMORY.md tests exercise branch - PASS
- All tests pass, ruff clean: 27/27 pass, ruff clean - PASS

### Test Results
- pytest (scoped): 27 passed
- pytest (full): 1315 passed, 2 failed (pre-existing env), 20 skipped
- ruff: All checks passed

### Confidence: .98
### Action: archive
