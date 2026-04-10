---
id: 568
title: Tighten genai-prices version specifier
status: archived
priority: someday
created: 2026-03-04T07:39:10.6285864+01:00
updated: 2026-03-22T19:17:44.9983407+01:00
started: 2026-03-07T04:53:03.4906214+01:00
completed: 2026-03-22T19:17:44.9983407+01:00
tags:
    - audit
    - config
    - deps
blocked: true
block_reason: 'Already implemented in commit 53c7d42; current pyproject.toml and uv.lock satisfy #568. Historical tracker only.'
class: standard
---

F-01: genai-prices >=0.0.1 accepts every version ever published. Pre-1.0, breaking change in 0.1->0.2 silently enters. See docs/config-dependency-audit.md.

## AC

- [ ] genai-prices version specifier tightened (e.g. >=0.0.1,<1.0)
- [ ] uv lock resolves successfully

[[2026-03-21]] Sat 14:30
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| genai-prices version specifier tightened (e.g. >=0.0.1,<1.0) | Already satisfied and exceeded in current source: pyproject.toml declares `genai-prices>=0.0.54,<0.1.0`, which is narrower than the audit's example bound. | Do not dispatch implementation; treat #568 as stale. |
| uv lock resolves successfully | Already satisfied: uv.lock records `specifier = >=0.0.54,<0.1.0` for genai-prices, `uv lock --check` succeeds, and commit `53c7d42` updated both pyproject.toml and uv.lock for #568. | Do not dispatch implementation; block historical tracker. |

### Architecture Notes
- Verified the originating audit still describes F-01 as the loose `>=0.0.1` risk in docs/config-dependency-audit.md.
- Verified current repository state already mitigates that risk in pyproject.toml with `genai-prices>=0.0.54,<0.1.0`.
- Verified the current branch history contains `53c7d42 chore: tighten genai-prices version specifier (#568, builder)`.
- Verified uv.lock still carries the bounded genai-prices specifier and `uv lock --check` resolves successfully.
- Verified live code uses the dependency in src/owlbear/memory/usage_cost.py, so the bound belongs in the package dependency surface, not a code follow-up.
- Current working tree has a pyproject.toml edit, but `git diff -- pyproject.toml` shows only an unrelated Ruff per-file-ignore addition; the genai-prices line remains satisfied.
- TDD check: no dedicated RED predecessor is discoverable for the historical dependency-pin change, but creating one now would duplicate already-committed work rather than improve the backlog.

### Changes Made
- Claimed #568 as `architect-568`.
- Re-validated F-01 against docs/config-dependency-audit.md, pyproject.toml, uv.lock, git history, and current lock health.
- Appended this architecture review.
- Moved #568 out of backlog to blocked ideation as a historical tracker only.

### Dependencies
- Added/Removed/Verified: verified commit `53c7d42` as the existing implementation evidence; no new test or builder follow-up is required for the task as written.
