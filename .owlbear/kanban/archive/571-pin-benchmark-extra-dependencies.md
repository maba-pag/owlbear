---
id: 571
title: Pin benchmark extra dependencies
status: archived
priority: someday
created: 2026-03-04T07:39:13.3539198+01:00
updated: 2026-03-22T19:17:46.4382127+01:00
started: 2026-03-07T04:53:04.0189212+01:00
completed: 2026-03-22T19:17:46.4382127+01:00
tags:
    - audit
    - config
    - deps
blocked: true
block_reason: Already implemented in commit c4abb33; current pyproject.toml and uv.lock satisfy F-15. Historical tracker only.
class: standard
---

F-15: benchmark = ['beir', 'ranx'] has no version specifiers. Unpinned deps can break CI. See docs/config-dependency-audit.md.

## AC

- [ ] beir has minimum version specifier (e.g. beir>=2.0.0)
- [ ] ranx has minimum version specifier (e.g. ranx>=0.3)
- [ ] uv lock resolves successfully

[[2026-03-21]] Sat 06:58
## Architecture Review
**Verdict:** BLOCK

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| beir has minimum version specifier | Satisfied in current source: pyproject.toml already declares `benchmark = [beir>=2.0.0, psutil>=5.9, ranx>=0.3]`. | Do not dispatch implementation from #571. |
| ranx has minimum version specifier | Satisfied in current source: pyproject.toml already declares `ranx>=0.3`, and uv.lock still records the benchmark extra specifier `>=0.3` plus a resolved `ranx` package entry. | Keep as historical evidence only. |
| uv lock resolves successfully | Satisfied in current workspace: `uv lock --check` succeeds, and commit `c4abb33` already updated uv.lock when the task originally landed. | Treat the lock AC as already implemented, not pending backlog work. |

### Architecture Notes
- Verified docs/config-dependency-audit.md still describes F-15 as the original finding and recommends `beir>=2.0.0` plus `ranx>=0.3`.
- Verified pyproject.toml line 45 already contains `benchmark = [beir>=2.0.0, psutil>=5.9, ranx>=0.3]`.
- Verified uv.lock still contains the benchmark extra specifier for `ranx` at line 3171 and resolved package entries for `beir` 2.2.0 and `ranx` 0.3.21.
- Verified git history: commit `c4abb33` is `chore: pin benchmark extra dependencies (#571, builder)` and includes changes to both pyproject.toml and uv.lock.
- Verified current lock health with `uv lock --check`, which resolved successfully without modifying the workspace.
- Because the exact task scope is already implemented in the current tree, moving #571 to `todo` would duplicate shipped config work and send the builder after a stale backlog item.

### Changes Made
- Claimed #571 as `architect-gpt54-571`.
- Re-validated the audit finding against docs/config-dependency-audit.md, pyproject.toml, uv.lock, and git history.
- Appended this architecture review.
- Moved #571 out of backlog to blocked ideation as a historical tracker only.

### Dependencies
- Added/Removed/Verified: verified commit `c4abb33` as the existing implementation evidence; no additional TDD or builder follow-up belongs to this task as written.
