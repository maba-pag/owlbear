---
id: 662
title: 'Improve test coverage: auth/copilot.py (94%) + browser/config.py (94%)'
status: archived
priority: important
created: 2026-03-08T01:59:38.2714116+01:00
updated: 2026-03-09T19:34:42.7461914+01:00
started: 2026-03-08T04:24:35.3011413+01:00
completed: 2026-03-09T19:34:42.7461914+01:00
tags:
    - coverage-sprint
    - auth
    - browser
    - test
class: standard
---

## Coverage Gap
auth/copilot.py: 94% (6 of 95 stmts uncovered)  lines 133-134, 205-208
browser/config.py: 94% (4 of 64 stmts uncovered)  lines 73, 76-78

## Acceptance Criteria
- [ ] Coverage >= 97% for src/owlbear/auth/copilot.py
- [ ] Coverage >= 97% for src/owlbear/tools/browser/config.py
- [ ] Tests cover copilot.py uncovered error/edge paths
- [ ] Tests cover browser config.py uncovered validation paths
- [ ] All new tests pass, ruff clean

[[2026-03-09]] Mon 19:34
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Coverage >= 97% copilot.py | 100% (95/95 stmts, 0 miss) | PASS |
| Coverage >= 97% browser/config.py | 100% (64/64 stmts, 0 miss) | PASS |
| Tests cover copilot.py uncovered error/edge paths | TestPollForAccessTokenUnexpectedError (L133-134) + TestSaveTokenUnixBranch (L205-208) | PASS |
| Tests cover browser config.py uncovered validation paths | TestCDPEndpointNonePassthrough (L73) + TestCDPEndpointUrlparseFailure (L76-78) | PASS |
| All new tests pass, ruff clean | 1315 passed; ruff 3 pre-existing errors, 0 in #662 files | PASS |

### Test Results
- pytest: 1315 passed, 20 skipped, 2 pre-existing failures (slack_sdk missing, Windows PermissionError on tmpdir)
- ruff: 3 pre-existing errors (E501 screenshot.py, I001 test_bootstrap_structure.py) - none in #662 scope

### Confidence: .97
### Action: archive
