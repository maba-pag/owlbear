---
id: 494
title: Expand command guard blocklist and document limitations
status: archived
priority: important
created: 2026-03-04T07:38:09.2339754+01:00
updated: 2026-03-09T20:13:12.0811086+01:00
started: 2026-03-06T23:23:22.4453535+01:00
completed: 2026-03-09T20:13:12.0811086+01:00
tags:
    - audit
    - security
    - scope:core
class: standard
---

SEC-04: DEFAULT_BLOCKED_COMMANDS regex patterns miss common variations. Expand patterns and document that the blocklist is defense-in-depth only. See docs/security-audit.md SEC-04.

## Acceptance Criteria

- [ ] DEFAULT_BLOCKED_COMMANDS in core/command_guard.py expanded to cover:
  - rm: rm -r -f, rm --recursive --force, rm -rf (current), sudo rm (current)
  - git push: git push -f, git push --force-with-lease, git push --force (current)
  - pip: python -m pip (in addition to current bare pip pattern)
  - del: powershell Remove-Item -Recurse -Force variants
  - Additional: chmod 777, mkfs, dd if=, shutdown, reboot
- [ ] Module docstring in command_guard.py updated with explicit NOTE:
  'This blocklist is defense-in-depth only  it is NOT a security boundary.
  The approval gate on run_command is the primary control. Regex blocklists
  are provably insufficient for shell command safety.'
- [ ] Existing tests in test_command_guard.py still pass
- [ ] New tests added for each new/expanded pattern (at least 1 test per new pattern)
- [ ] ruff clean

[[2026-03-09]] Mon 20:12
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| DEFAULT_BLOCKED_COMMANDS expanded: rm variants | L29-35: rm -r -f, --recursive --force, sudo rm | PASS |
| git push variants | L37-38: --force, -f (covers --force-with-lease) | PASS |
| python -m pip | L41: python\d?\s+-m\s+pip\s+install | PASS |
| Remove-Item variants | L45-46: case-insensitive -Recurse/-Force both orders | PASS |
| chmod 777, mkfs, dd, shutdown, reboot | L48-53: all 5 patterns | PASS |
| Module docstring NOTE | L7-9: exact defense-in-depth text | PASS |
| Existing tests pass | 85/85 passed | PASS |
| New tests per pattern | 5 new test classes, 28+ parametrized cases | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 85/85 passed
- pytest (full suite): pre-existing environment crash (logfire/urllib3 import), unrelated to #494
- ruff: All checks passed

### Confidence: .97
### Action: archive

[[2026-03-09]] Mon 20:12
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| DEFAULT_BLOCKED_COMMANDS expanded: rm variants | L29-35: rm -r -f, --recursive --force, sudo rm | PASS |
| git push variants | L37-38: --force, -f (covers --force-with-lease) | PASS |
| python -m pip | L41: python\d?\s+-m\s+pip\s+install | PASS |
| Remove-Item variants | L45-46: case-insensitive -Recurse/-Force both orders | PASS |
| chmod 777, mkfs, dd, shutdown, reboot | L48-53: all 5 patterns | PASS |
| Module docstring NOTE | L7-9: exact defense-in-depth text | PASS |
| Existing tests pass | 85/85 passed | PASS |
| New tests per pattern | 5 new test classes, 28+ parametrized cases | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 85/85 passed
- pytest (full suite): pre-existing environment crash (logfire/urllib3 import), unrelated to #494
- ruff: All checks passed

### Confidence: .97
### Action: archive
