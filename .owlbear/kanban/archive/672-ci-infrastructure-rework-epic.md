---
id: 672
title: CI infrastructure rework (epic)
status: archived
priority: medium
created: 2026-04-06T22:41:55.5351404+02:00
updated: 2026-04-07T16:04:42.1156629+02:00
started: 2026-04-07T16:04:42.1156629+02:00
completed: 2026-04-07T16:04:42.1156629+02:00
tags:
    - scope:ci
    - type:epic
    - type:config
class: standard
---

## Objective\nEpic for CI infrastructure rework: fix all workflow issues, switch sync strategy, bootstrap to main.\n\n## Subtasks\n- #667 Rewrite sync-to-main with incremental commit strategy\n- #668 Fix megalinter for private repo constraints\n- #669 Remove dead Docker ecosystem from dependabot\n- #670 Create .cspell.json for project vocabulary\n- #671 Bootstrap CI workflows to main branch\n\n## Context\nAudit found 11 issues across sync-to-main.yml, megalinter.yml, .mega-linter.yml, dependabot.yml. Key findings: force-push destroys main history, include-list missing .github/, SARIF upload fails on private repo, APPLY_FIXES silently lost, docker ecosystem is dead, dependabot not running (config only on dev).

[[2026-04-07]] Tue 09:15
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Epic groups 5 focused CI subtasks; each subtask has one concern |
| Interface clarity | PASS | N/A for tracking epic; subtasks define concrete file changes |
| Dependency correctness | PASS | #671 depends_on [667,668,669] correct; #670 independent (nice-to-have); epic has no deps |
| Module layering | PASS | CI config only, no code layering |
| TDD compliance | PASS | type:epic is non-impl; subtasks are type:build/fix/config/user-action |
| KISS/YAGNI | PASS | Addresses verified audit findings, nothing speculative |
| Premise challenge | PASS | Audit found 11 real issues in sync-to-main.yml, megalinter.yml, .mega-linter.yml, dependabot.yml |
| Pattern consistency | PASS | GitHub Actions conventions followed (SHA-pinned actions, concurrency guards) |
| Security surface | PASS | Removing SARIF upload and security-events permission reduces attack surface |
| Single domain | PASS | All scope:ci, no domain violations |

### Challenge Results
- Challenger: proceed (confidence 0.82)
- Three findings accepted:
  1. Added type:config pass-through tag to epic (precedent: #598)
  2. Recommends promoting #670 from nice-to-have to needed (SPELL_CSPELL already active in .mega-linter.yml line 21; without .cspell.json every project term is flagged)
  3. Decomposition confirmed sound; #668 two-file change is cohesive (both private-repo compatibility)
- Architect response: accepted all three; tag applied directly, #670 priority noted for its own review

### Coordination Notes
- #670 (.cspell.json) should be promoted to priority:needed during its own architect review; SPELL_CSPELL is already enabled and will produce noise without the dictionary
- #670 and #668 both modify linter configs; complete both before #671 bootstrap
- All subtasks verified: exist, have concrete AC, correct dependencies, proper tags

### Verdict: APPROVE
### Action Taken: Added type:config tag for pipeline pass-through. Advanced epic to todo.

[[2026-04-07]] Tue 09:17
## Test-Writer Notes
- Non-implementation task (tagged type:epic, type:config) — no tests applicable.
- Epic is a tracking container for CI config subtasks (#667–#671); no testable Python interfaces.
- Passing through to builder.

[[2026-04-07]] Tue 11:17
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-04-07]] Tue 11:22
## Review Evidence

### Source Control
No direct file changes on this epic — type:config, type:epic pass-through confirmed.

### Tests / Lint / Coverage
N/A — non-implementation epic. No code to test.

### Subtask Completion Gate

| Subtask | Title | Status | Done? |
|---------|-------|--------|-------|
| #667 | Rewrite sync-to-main | `review` | ✗ |
| #668 | Fix megalinter | `review` | ✗ |
| #669 | Remove dead Docker | `review` | ✗ |
| #670 | Create .cspell.json | `todo` | ✗ |
| #671 | Bootstrap CI workflows | `backlog` | ✗ |

**0 of 5 subtasks have reached `done` status.**

### AC Compliance

This epic has no formal AC section — its completion contract is implicit: all subtasks delivered. None are delivered.

### Deductions
- **-0.55** — Epic advanced to review while 0/5 subtasks are complete. Builder passed through without checking subtask completion state. An epic tracking container cannot be considered done while constituent work is in flight.

### Verdict
Confidence: **0.35** → **FAIL**

The builder's pass-through logic is correct (no code to write on the epic itself), but advancement to `review` is premature. Epic moved to `backlog`. Orchestrator should re-dispatch this epic to review only after all 5 subtasks (#667, #668, #669, #670, #671) reach `done`.

[[2026-04-07]] Tue 11:33
## Architecture Review (2nd pass)

### Context
Epic previously approved, passed through test-writer and builder (non-impl pass-through), then correctly FAILED at review (confidence 0.35): 0/5 subtasks were done. Returned to backlog.

### Current Subtask Status
| Subtask | Title | Status | Done? |
|---------|-------|--------|-------|
| #667 | Rewrite sync-to-main | done | Yes |
| #668 | Fix megalinter | done | Yes |
| #669 | Remove dead Docker | done | Yes |
| #670 | Create .cspell.json | review | No |
| #671 | Bootstrap CI workflows | backlog | No |

3/5 subtasks done. #670 is in review (likely to complete soon). #671 is type:user-action in backlog — its deps (#667, #668, #669) are all done so it can proceed independently.

### AC Refinement
The epic had no formal AC section, causing the original premature advancement. Explicit completion contract:
- All 5 subtasks (#667, #668, #669, #670, #671) must reach `done` status before this epic can pass review.

### Decision
BLOCK — re-dispatching now would repeat the reviewer failure. The epic cannot pass the subtask completion gate with 2 subtasks still in flight. Blocking prevents wasted pipeline cycles.

### Unblock Criteria
Orchestrator should unblock this epic when #670 and #671 both reach `done`.

### Verdict: BLOCK
### Action Taken: Blocked epic pending subtask completion (2/5 remaining). Previous arch review still valid — no structural changes needed.
