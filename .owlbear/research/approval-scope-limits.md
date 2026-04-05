# Approval Scope Limits Research

> **Owning task:** #498 — Add scope limits to approve-all session grants
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

SEC-12 identified that "approve all {tool}" grants blanket session-wide approval with no constraints on arguments, usage count, or time. A user approving `git push origin main` via "approve all git_push" also silently approves `git push --force origin main`. How should we scope these grants?

Current code: `ApprovalSession._pre_grants` is a `set[str]` of tool names. `grant()` adds a name; `is_pre_granted()` checks membership. No expiry, no counter, no arg filtering.

## 2. Sources Studied

| # | Source | URL | Relevance | Key Pattern |
|---|--------|-----|-----------|-------------|
| 1 | OAuth 2.0 RFC 6749 S3.3 | <https://www.rfc-editor.org/rfc/rfc6749#section-3.3> | .85 | `scope` param narrows access; `expires_in` limits token lifetime; refresh requires re-auth |
| 2 | GitHub OAuth Scopes | <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps> | .80 | Hierarchical scopes (`repo` > `repo:status`); parent absorbs child; fine-grained narrowing |
| 3 | AWS IAM Condition Keys | <https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html> | .90 | `StringEquals`/`StringLike` for arg matching; `aws:TokenIssueTime` + `DateLessThan` for expiry; `NumericLessThan` for count limits; `aws:CurrentTime` for time-based conditions |

## 3. Analysis

### 3.1 Scope Mechanism Comparison

| Mechanism | OAuth 2.0 | GitHub Scopes | AWS IAM Conditions | Fit for OwlBear |
|-----------|-----------|---------------|-------------------|-----------------|
| **Arg-scoped grants** | `scope` param narrows token access | Hierarchical: `repo:status` < `repo` | `StringLike` conditions on resource ARNs | High — `arg_pattern` already on `ApprovalRule` |
| **Time expiry** | `expires_in` field on tokens | Token expiry at creation | `aws:TokenIssueTime` + `DateLessThan` | High — `time.monotonic()` delta check |
| **Max-uses counter** | Refresh token rotation (single-use) | Not applicable | No direct equivalent (session policies expire) | Medium — simple decrement counter |
| **Automatic revocation** | Refresh token invalidation | Token revocation endpoint | Session policy termination | Low priority — session clear already exists |

### 3.2 Implementation Options

| Option | Description | Complexity | KISS Score |
|--------|-------------|------------|------------|
| **A: GrantRecord dataclass** | Replace `set[str]` with `dict[str, GrantRecord]`; GrantRecord has `max_uses`, `expires_at`, `arg_pattern` | ~60 LOC | .90 |
| **B: Scoped grant + config** | Option A + configurable defaults in `ApprovalPolicy` (`default_grant_ttl`, `default_max_uses`) | ~80 LOC | .85 |
| **C: Full hierarchical scopes** | GitHub-style scope hierarchy with parent/child inference | ~200 LOC | .50 |

### 3.3 Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Expired grants annoy users with repeated prompts | UX friction | Sensible defaults: TTL=300s, max_uses=10 |
| Arg-pattern grants are too restrictive | Legitimate calls blocked | Grant without pattern = current behavior (name-only) |
| Counter-based grants create race conditions | Incorrect count in async | Single-threaded agent loop — no real concurrency risk |
| Breaking change to `ApprovalSession` API | Test regressions | `is_pre_granted()` gains `args` param; existing tests pass with `args={}` default |

## 4. Recommendation (.85 confidence)

**Option B: Scoped grant + config.** It addresses all three SEC-12 recommendations (max-uses, expiry, arg-scoped) with ~80 LOC of changes, aligning with KISS/YAGNI. Option C (hierarchical scopes) is over-engineering for our use case — we have ~10 gated tools, not GitHub's 50+ scopes.

### Proposed Data Model

```
@dataclass
class GrantRecord:
    tool_name: str
    granted_at: float          # time.monotonic()
    remaining_uses: int | None # None = unlimited
    ttl: float | None          # seconds; None = session-lifetime
    arg_pattern: str | None    # regex; None = any args

class ApprovalSession:
    _grants: dict[str, GrantRecord]  # was: set[str]

    def is_pre_granted(self, tool_name: str, args: dict[str, Any] = {}) -> bool:
        grant = self._grants.get(tool_name)
        if grant is None: return False
        if grant.ttl and (monotonic() - grant.granted_at) > grant.ttl: return False
        if grant.remaining_uses is not None and grant.remaining_uses <= 0: return False
        if grant.arg_pattern and not _args_match(grant.arg_pattern, args): return False
        if grant.remaining_uses is not None: grant.remaining_uses -= 1
        return True
```

### Config Additions to `ApprovalPolicy`

```
default_grant_ttl: float = 300.0      # 5 minutes
default_max_uses: int | None = 10     # None = unlimited
```

### Gate Changes

The "approve all {tool}" handler in `gate.py` creates a `GrantRecord` with policy defaults. Future: support "approve all git_push --pattern 'origin main'" syntax for arg-scoped grants.

## 5. Follow-up Tasks

See kanban commands below — do NOT execute, present for user review.

```
kanban\kanban-md.exe create "Implement GrantRecord dataclass in policy.py" --status backlog --priority needed --tags "phase-3,safety,scope:core" --body "Replace ApprovalSession._pre_grants set[str] with dict[str, GrantRecord]. GrantRecord fields: tool_name, granted_at (monotonic), remaining_uses (int|None), ttl (float|None), arg_pattern (str|None). Update is_pre_granted() to check expiry, counter, and arg pattern. Add default_grant_ttl and default_max_uses to ApprovalPolicy. See docs/research/approval-scope-limits.md for design. AC: - [ ] GrantRecord dataclass with 4 constraint fields - [ ] is_pre_granted checks expiry via monotonic clock - [ ] is_pre_granted decrements remaining_uses - [ ] is_pre_granted checks arg_pattern via regex - [ ] ApprovalPolicy has default_grant_ttl (300s) and default_max_uses (10) - [ ] Backward compat: is_pre_granted(tool_name) still works (args defaults to {})"

kanban\kanban-md.exe create "Update ApprovalGateToolset to create scoped grants" --status backlog --priority needed --tags "phase-3,safety,scope:core" --depends-on "<grant-record-task-id>" --body "Update gate.py 'approve all' handler to create GrantRecord with policy defaults (default_grant_ttl, default_max_uses). Wire arg_pattern=None for now (future: parse from user input). See docs/research/approval-scope-limits.md. AC: - [ ] 'approve all {tool}' creates GrantRecord with TTL and max-uses from policy - [ ] Grant expiry auto-revokes (next is_pre_granted returns False) - [ ] Hook event includes grant metadata (ttl, max_uses)"

kanban\kanban-md.exe create "Add tests for scoped approval grants" --status backlog --priority needed --tags "phase-3,safety,test" --depends-on "<grant-record-task-id>" --body "TDD tests for GrantRecord expiry, counter decrement, arg-pattern matching. See docs/research/approval-scope-limits.md. AC: - [ ] Test: grant with max_uses=3 allows 3 calls then denies - [ ] Test: grant with ttl=1.0 expires after 1 second (mock monotonic) - [ ] Test: grant with arg_pattern allows matching args, denies non-matching - [ ] Test: grant with no constraints behaves like current blanket grant - [ ] Test: expired/exhausted grants are cleaned up"
```

