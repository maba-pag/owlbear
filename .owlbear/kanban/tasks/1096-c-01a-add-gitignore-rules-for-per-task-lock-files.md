---
id: 1096
title: 'C-01a: Add gitignore rules for per-task lock files'
status: in-progress
priority: nice-to-have
created: 2026-04-21T19:26:03.707441+00:00
updated: 2026-04-21T20:38:26.027655+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- type:config
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — split from #1046 AC-C4b architect review.

## Context
Per-task lock files (`tasks/.<id>.lock`) are created by `write_task_if_unchanged` at `serve/kanban/src/owlbear_kanban/storage.py:299`. Only `.owlbear/kanban/.next_id.lock` is gitignored (`.gitignore:108`, `seed/.gitignore:68`). Per-task lock files have no ignore rule.

## Acceptance Criteria

- [ ] `.gitignore` and `seed/.gitignore` include a pattern matching `tasks/.<id>.lock` and `archive/.<id>.lock` files within `.owlbear/kanban/`
- [ ] Existing lock files (if any) removed from git tracking via `git rm --cached`
- [ ] No `.lock` files appear in `git status` after creating tasks via the engine
[[2026-04-21]]
## Architecture Review

### Refined Acceptance Criteria (supersedes original AC)

The original AC-3 ("No `.lock` files appear in `git status` after creating tasks via the engine") is vacuous: `create_task` only acquires `.next_id.lock` (already ignored). Per-task locks are created by `write_task_if_unchanged` which has no engine call site yet (only tests, which use tmp dirs). Additionally, the original AC-1 pattern wording is too loose, risking collision with `.gitkeep` files.

**Builder: use these AC instead of the original:**

- [ ] `.gitignore` adds two lines under the existing "Lock files" comment (line 108): `.owlbear/kanban/tasks/.*.lock` and `.owlbear/kanban/archive/.*.lock`
- [ ] `seed/.gitignore` adds the same two lines under its "Lock files" comment (line 68)
- [ ] Existing per-task lock files (if any) removed from git tracking via `git rm --cached`
- [ ] The new patterns do not match `.gitkeep` or other non-lock hidden files (verify: `.owlbear/kanban/tasks/.gitkeep` remains tracked)

Archive pattern rationale: no current code creates archive lock files, but Brief C paper-c.md and parent #1055 AC-C4b explicitly specify `archive/.<id>.lock` scope. This is design-intentional per the brief, not speculative.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: gitignore rules for lock files |
| Interface clarity | PASS | Exact patterns and file locations specified in refined AC |
| Dependency correctness | PASS | No deps; standalone config edit |
| Module layering | PASS | Config files only, no code changes |
| TDD compliance | PASS | Tagged `type:config`, pass-through applies |
| KISS/YAGNI | PASS | Minimal scope; archive pattern justified by Brief C spec |
| Premise challenge | PASS | Gap confirmed: storage.py:320 creates `.<id>.lock`, no ignore rule exists |
| Pattern consistency | PASS | Follows existing `.next_id.lock` ignore at .gitignore:108 |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Config only |

### Challenge Results
- Challenger: reconsider (confidence: 0.64)
- Findings: (1) AC-3 vacuous since create_task only uses .next_id.lock, (2) archive pattern speculative vs current code, (3) pattern safety risk with .gitkeep files
- Architect response: ACCEPTED points 1 and 3 — refined AC replaces vacuous AC-3 with pattern-safety check. REBUTTED point 2 — archive pattern is Brief C spec, not speculation. Parent #1055 AC-C4b explicitly lists `archive/.<id>.lock`.

### Verdict: APPROVE (with AC refinement)
### Action: Refined AC in note above. Advanced to todo.
[[2026-04-21]]
## Test-Writer Notes
- Non-implementation task (tagged `type:config`) — no tests applicable.
- AC covers only `.gitignore` and `seed/.gitignore` edits plus a `git rm --cached` step. No Python interfaces, no modules, no testable code paths.
- Passing through to builder.