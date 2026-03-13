---
id: 655
title: Implement GrantRecord and scoped ApprovalSession
status: archived
priority: needed
created: 2026-03-08T01:37:55.7940357+01:00
updated: 2026-03-09T00:14:03.7060536+01:00
started: 2026-03-08T02:02:06.537967+01:00
completed: 2026-03-09T00:14:03.7060536+01:00
tags:
    - safety
    - scope:core
class: standard
---

Replace ApprovalSession._pre_grants set[str] with dict[str, GrantRecord]. See docs/research/approval-scope-limits.md Option B.

## Acceptance Criteria

- [ ] GrantRecord dataclass in safety/policy.py with fields: tool_name (str), granted_at (float, monotonic), remaining_uses (int|None), ttl (float|None), arg_pattern (str|None)
- [ ] ApprovalSession._pre_grants replaced with _grants: dict[str, GrantRecord]
- [ ] is_pre_granted(tool_name, args=None) checks:
  - TTL expiry via time.monotonic() delta
  - remaining_uses > 0 (decrements on use; None = unlimited)
  - arg_pattern regex match against string arg values (None = any args)
  - Removes expired/exhausted grants on check
- [ ] grant(tool_name, ...) accepts optional max_uses, ttl, arg_pattern
- [ ] ApprovalPolicy gains default_grant_ttl: float = 300.0 and default_max_uses: int | None = 10
- [ ] Backward compat: is_pre_granted(tool_name) still works when args omitted
- [ ] Backward compat: grant(tool_name) with no kwargs creates grant with policy defaults
- [ ] Tests in test_approval_policy.py:
  - Grant with max_uses=3 allows 3 calls then denies
  - Grant with ttl=1.0 expires after time passes (mock monotonic)
  - Grant with arg_pattern allows matching args, denies non-matching
  - Grant with no constraints behaves like current blanket grant
  - Expired/exhausted grants cleaned up on next check
  - is_pre_granted backward compat (no args param)
- [ ] ruff clean

[[2026-03-08]] Sun 23:51
Wave 2, agent: auditor

[[2026-03-08]] Sun 23:57
Wave 2, agent: auditor

[[2026-03-09]] Mon 00:13
## Audit
### Report
| AC Line | Evidence | Confidence |
|---------|----------|------------|
| GrantRecord dataclass (5 fields) | policy.py L93-99, dataclass with tool_name/granted_at/remaining_uses/ttl/arg_pattern | .97 |
| _grants: dict[str, GrantRecord] | policy.py L113 | .97 |
| is_pre_granted checks TTL/uses/arg_pattern + cleanup | policy.py L116-153, all 4 checks with auto-removal | .97 |
| grant() accepts max_uses, ttl, arg_pattern | policy.py L155-181, keyword-only params | .97 |
| ApprovalPolicy default_grant_ttl + default_max_uses | policy.py L49-50 (300.0, 10) | .97 |
| Backward compat: is_pre_granted(tool_name) no args | policy.py L118 args=None default | .97 |
| Backward compat: grant(tool_name) no kwargs | policy.py L171-173 policy defaults applied | .97 |
| Test: max_uses=3 allows 3 then denies | TestMaxUses (4 tests passing) | .97 |
| Test: TTL expires (mock monotonic) | TestTTLExpiry (4 tests passing) | .97 |
| Test: arg_pattern match/deny | TestArgPattern (5 tests passing) | .97 |
| Test: blanket grant | TestBlanketGrant (3 tests passing) | .97 |
| Test: expired/exhausted cleanup | TestTTLExpiry + TestMaxUses cleanup tests | .97 |
| Test: backward compat | TestBackwardCompat (4 tests passing) | .97 |
| ruff clean | All checks passed | 1.0 |

### Commit Log
N/A - code already committed

### Push: pending
