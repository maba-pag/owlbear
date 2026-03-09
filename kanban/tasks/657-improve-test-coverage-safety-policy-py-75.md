---
id: 657
title: 'Improve test coverage: safety/policy.py (75%)'
status: archived
priority: needed
created: 2026-03-08T01:58:54.8259855+01:00
updated: 2026-03-09T00:18:47.8435541+01:00
started: 2026-03-08T02:43:00.0565532+01:00
completed: 2026-03-09T00:18:47.8435541+01:00
tags:
    - coverage-sprint
    - safety
    - test
class: standard
---

## Coverage Gap
Current: 75% (17 of 69 statements uncovered)
Missing lines: 69-70, 85-86, 130-131, 135-136, 140-145, 149-151, 173-174, 186

## Acceptance Criteria
- [ ] Coverage >= 95% for src/owlbear/safety/policy.py
- [ ] Tests cover: ApprovalPolicy.requires_approval with wildcard rules, arg_pattern matching, and no-match fallback
- [ ] Tests cover: ApprovalSession.is_pre_granted TTL expiry, remaining uses exhaustion, arg-pattern mismatch
- [ ] Tests cover: ApprovalSession.grant with policy defaults applied
- [ ] All new tests pass, ruff clean

[[2026-03-08]] Sun 23:51
Wave 2, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 00:18
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| Coverage >= 95% for policy.py | 100% (69/69 stmts) via --cov | .97 |
| requires_approval: wildcard, arg_pattern, no-match | TestRequiresApprovalWildcard (2), TestRequiresApprovalArgPattern (5), TestRequiresApprovalEmptyPolicy (2) | .97 |
| is_pre_granted: TTL, uses, arg-pattern | TestTTLExpiry (4), TestMaxUses (4), TestArgPattern::test_non_matching_args_denied | .97 |
| grant with policy defaults | TestBlanketGrant::test_grant_with_policy_defaults + test_grant_explicit_overrides | .97 |
| All tests pass, ruff clean | 50 passed; ruff All checks passed | .97 |

### Full Suite
3 pre-existing failures (slack_sdk missing, bootstrap.create_copilot_client removed) — unrelated to #657.
1269 passed, 20 skipped, 3 failed (pre-existing).
