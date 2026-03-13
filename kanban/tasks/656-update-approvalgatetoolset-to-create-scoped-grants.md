---
id: 656
title: Update ApprovalGateToolset to create scoped grants
status: archived
priority: needed
created: 2026-03-08T01:38:05.1004841+01:00
updated: 2026-03-09T00:14:22.6106164+01:00
started: 2026-03-08T02:23:52.123204+01:00
completed: 2026-03-09T00:14:22.6106164+01:00
tags:
    - safety
    - scope:core
depends_on:
    - 655
class: standard
---

Update gate.py 'approve all' handler to create GrantRecord with policy defaults. See docs/research/approval-scope-limits.md.

## Acceptance Criteria

- [ ] 'approve all {tool}' in gate.py creates GrantRecord with ttl=policy.default_grant_ttl and max_uses=policy.default_max_uses
- [ ] Grant expiry auto-revokes: next is_pre_granted returns False after TTL
- [ ] Grant exhaustion auto-revokes: after max_uses calls, next is_pre_granted returns False
- [ ] POST_TOOL_USE hook event for approved_all includes grant metadata (ttl, max_uses)
- [ ] Tests in test_approval_gate.py:
  - 'approve all' creates grant with policy defaults
  - Grant expires after TTL (mock monotonic)
  - Grant exhausts after max_uses calls
  - Hook event includes grant metadata
- [ ] ruff clean

[[2026-03-08]] Sun 23:51
Wave 2, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 00:14
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| approve all creates GrantRecord with policy defaults | gate.py L138-144: session.grant(ttl=policy.default_grant_ttl, max_uses=policy.default_max_uses) | .97 |
| Grant expiry auto-revokes after TTL | policy.py is_pre_granted TTL check + del; test_grant_expires_after_ttl passes | .97 |
| Grant exhaustion after max_uses | policy.py remaining_uses decrement + del; test_grant_exhausts_after_max_uses passes | .97 |
| POST_TOOL_USE hook includes grant metadata | gate.py L146-155: grant_ttl, grant_max_uses in payload; test_hook_includes_grant_metadata passes | .97 |
| Tests: approve all creates grant with policy defaults | TestApproveAllScopedGrants.test_approve_all_creates_grant_with_policy_defaults passes | .97 |
| Tests: grant expires after TTL | TestApproveAllScopedGrants.test_grant_expires_after_ttl passes | .97 |
| Tests: grant exhausts after max_uses | TestApproveAllScopedGrants.test_grant_exhausts_after_max_uses passes | .97 |
| Tests: hook includes grant metadata | TestApproveAllHookMetadata.test_hook_includes_grant_metadata passes | .97 |
| ruff clean | All checks passed on gate.py, policy.py, test_approval_gate.py, test_approval_policy.py | 1.0 |

### Verdict
72 tests passing (test_approval_gate.py + test_approval_policy.py). All 6 AC items verified. Confidence: .97
