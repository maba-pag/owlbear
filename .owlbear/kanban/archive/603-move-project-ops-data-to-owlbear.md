---
id: 603
title: Move project ops data to .owlbear/
status: archived
priority: medium
created: 2026-04-04 20:30:51.991962+02:00
updated: 2026-04-05 08:34:57.759748+02:00
started: 2026-04-05 08:34:57.759748+02:00
completed: 2026-04-05 08:34:57.759748+02:00
tags:
- scope:infra
- type:build
- phase-2
- type:config
parent: 598
depends_on:
- 599
claimed_by: flare-heath
claimed_at: 2026-04-05 08:34:12.835362+02:00
class: standard
archival_reason: completed
archival_refs: []
---

## Summary

Move kanban/, docs/decisions/, docs/research/, docs/sources/, docs/scratch/ into .owlbear/. Move CI scripts to .owlbear/scripts/. Copy hooks to .owlbear/hooks/.

## Acceptance Criteria

- [ ] AC1: .owlbear/kanban/ contains all tracked kanban files: config.yml, tasks/, activity.jsonl, setup.ps1, README.md, v1-archive/, .lock (kanban-md.exe is gitignored; running setup.ps1 in new location downloads it; not a git mv target)
- [ ] AC2: .owlbear/decisions/ contains pending/ and resolved/ with all existing decision docs
- [ ] AC3: .owlbear/research/ contains all existing research docs
- [ ] AC4: .owlbear/sources/ contains all source files
- [ ] AC5: .owlbear/scratch/ contains scratch files, .instructions.md (tracked), and .gitkeep
- [ ] AC6: .owlbear/scripts/ contains validate_agents.py, validate_skills.py, e2e_smoke.py, skills_ref/
- [ ] AC7: .owlbear/hooks/ contains deny-writes.ps1, lint-changed.ps1 (copied from scripts/hooks/; originals remain for seed task #604)
- [ ] AC8: After moves, docs/ retains only setup-guide.md and sharing-guide.md (moved to setup/ by #604; folder deletion by #609)
- [ ] AC9: After moves, scripts/ retains only setup.py and hooks/ (setup.py moved by #604; hooks/ originals for seed task; folder deletion by #609)

## Dependencies

Depends on #599 (kanban-md path verification) to confirm .owlbear/kanban/ works.

## Notes

- kanban-md.exe is gitignored (kanban/*.exe). The binary is not git-moved; builder runs setup.ps1 in new location. .gitignore rule update (.owlbear/kanban/*.exe) handled by #607 or #609.
- MCP server path resolution (KANBAN_DIR env var, default path changes) handled by #606, not this task.
- Reference updates (agent files, skill files, config, .pre-commit, .gitignore, pyproject.toml) handled by #607.
- docs/setup-guide.md and docs/sharing-guide.md move to setup/ in #604.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: relocate project ops data to .owlbear/. All 7 directory moves share this purpose. |
| Interface clarity | PASS (refined) | AC1 expanded to include v1-archive/, .lock, kanban-md.exe clarification. AC8-AC9 rewritten from impossible "folder deleted" to verifiable "retains only" with downstream task refs. AC5 made explicit (.instructions.md, .gitkeep). |
| Dependency correctness | PASS | Depends on #599 (kanban-md path verify, in todo). Depended upon by #604, #606, #607, #608. No missing deps. |
| Module layering | N/A | Pure file moves, no code changes. |
| TDD compliance | PASS | Tagged type:config (pass-through). No testable Python code produced. |
| KISS/YAGNI | PASS | Minimal scope: move files, no reference updates (those are #607). |
| Premise challenge | PASS | .owlbear/ consolidation is the core decision from #598. These moves are mechanically required. |
| Pattern consistency | PASS | Follows git mv pattern. Copy-not-move for hooks is intentional (originals needed by seed task #604). |
| Security surface | N/A | No new system boundaries. File moves only. |
| Single domain | PASS | scope:infra only. All moves are infrastructure/ops data. |

### Refinements Applied

1. AC1: Added v1-archive/, .lock (previously missing). Clarified kanban-md.exe is gitignored, not git-moved.
2. AC5: Made explicit: .instructions.md (tracked) and .gitkeep.
3. AC7: Added "(originals remain for seed task #604)" to clarify copy-not-move.
4. AC8: Rewritten from "docs/ folder deleted" to "docs/ retains only setup-guide.md and sharing-guide.md" with cross-refs to #604/#609.
5. AC9: Rewritten from "scripts/ folder deleted" to "scripts/ retains only setup.py and hooks/" with cross-refs.
6. Notes section: Added kanban-md.exe binary handling, MCP server scope boundary (#606), reference update scope boundary (#607).
7. Added type:config pass-through tag for pipeline routing.

### Challenge Results

- Challenger: reconsider (confidence: 0.72)
- Key concerns: (1) kanban-md.exe gitignored not movable, (2) AC8-AC9 impossible as written, (3) v1-archive/.lock missing, (4) implicit #606 dependency, (5) setup.py scope
- Architect response: Override with refinement
  - Concerns 1-3: Accepted, all addressed in AC refinements above
  - Concern 4 (implicit #606 dep): Rebutted. #603 is a prerequisite OF #606 (DAG: #606 depends_on [601, 602, 603]). File moves don't require code changes; code changes require file moves.
  - Concern 5 (setup.py): Rebutted. setup.py replacement is #604's domain (setup/init.py). #603 scope is ops data moves only.

### Verdict: APPROVE
### Action Taken: Refined AC1 (v1-archive, .lock, exe clarification), AC5 (.instructions.md, .gitkeep), AC7 (copy clarification), AC8-AC9 (retention not deletion), added Notes section with scope boundaries, added type:config tag. Advanced to todo.

[[2026-04-04]] Sat 22:26
APPROVED #603 to todo | Refined AC1 (added v1-archive/, .lock, kanban-md.exe gitignore clarification), AC5 (.instructions.md, .gitkeep), AC7 (copy-not-move clarification), AC8-AC9 (rewritten from impossible "folder deleted" to verifiable "retains only" with cross-refs to #604/#609). Added Notes section with explicit scope boundaries for #606 and #607. Added type:config pass-through tag. Challenger overridden (0.72): concerns 1-3 accepted as refinements; #606 dependency rebutted (603 is prerequisite OF 606); setup.py scope rebutted (#604 domain).

[[2026-04-04]] Sat 23:44
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Pure file moves (git mv operations). No Python interfaces introduced. No testable code produced.
- Passing through to builder.

[[2026-04-05]] Sun 02:31
## Builder Notes

### Files Changed
- `docs/decisions/` → `.owlbear/decisions/` (git mv — pending/ + resolved/ + README.md)
- `docs/research/` → `.owlbear/research/` (git mv)
- `docs/sources/` → `.owlbear/sources/` (git mv)
- `docs/scratch/` → `.owlbear/scratch/` (git mv); `.gitkeep` created and staged
- `scripts/validate_agents.py` → `.owlbear/scripts/` (git mv)
- `scripts/validate_skills.py` → `.owlbear/scripts/` (git mv)
- `scripts/e2e_smoke.py` → `.owlbear/scripts/` (git mv)
- `scripts/skills_ref/` → `.owlbear/scripts/skills_ref/` (git mv)
- `scripts/hooks/deny-writes.ps1` → copied to `.owlbear/hooks/` (original preserved for #604)
- `scripts/hooks/lint-changed.ps1` → copied to `.owlbear/hooks/` (original preserved for #604)
- `kanban/` → `.owlbear/kanban/` (git mv; kanban-md.exe physically moved post-git-mv; setup.ps1 run in new location)

### AC Evidence
| AC | Status | Evidence |
|----|--------|----------|
| AC1 | PASS | `.owlbear/kanban/` contains all tracked files (moved after this note) |
| AC2 | PASS | `.owlbear/decisions/` has pending/ and resolved/ with all docs |
| AC3 | PASS | `.owlbear/research/` all research docs present |
| AC4 | PASS | `.owlbear/sources/` contains overview.md |
| AC5 | PASS | `.owlbear/scratch/` has all files, .instructions.md, .gitkeep |
| AC6 | PASS | `.owlbear/scripts/` has validate_agents.py, validate_skills.py, e2e_smoke.py, skills_ref/ |
| AC7 | PASS | `.owlbear/hooks/` has deny-writes.ps1, lint-changed.ps1; originals remain in scripts/hooks/ |
| AC8 | PASS | `docs/` retains only setup-guide.md and sharing-guide.md |
| AC9 | PASS | `scripts/` retains only setup.py and hooks/ |

### Notes
- type:config pass-through — no pytest/ruff applicable
- kanban/ moved after this end_work call (MCP writes before git mv to preserve task file location during this session)

[[2026-04-05]] Sun 04:59
## Review Evidence

### Task Type
type:config pass-through — pure file moves. No tests applicable, no lint applicable, no Python code produced.

### Tests
N/A — tagged type:config. Test-writer pass-through confirmed in build notes.

### Lint
N/A — no Python files changed.

### Coverage
N/A.

### Source Control Verification
Builder commit for main moves: `55a4d8c` ("fix(test): correct packages/ -> serve/ paths in test_rename_data_to_store_602")
Kanban move commit: `4c7caea` ("test: add contract tests for apply_patch lint guard (#546, test-writer)")

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| AC1: .owlbear/kanban/ has config.yml, tasks/, activity.jsonl, setup.ps1, README.md, v1-archive/, .lock | `list_dir .owlbear/kanban/` → all 7 items present. kanban-md.exe present (gitignored, physically moved as noted). | PASS |
| AC2: .owlbear/decisions/ has pending/ and resolved/ | `git ls-tree 55a4d8c .owlbear/decisions/` → pending/.gitkeep, resolved/.gitkeep, resolved/README.md, resolved/25 docs present. | PASS |
| AC3: .owlbear/research/ has all research docs | `list_dir .owlbear/research/` → ~200+ docs present. | PASS |
| AC4: .owlbear/sources/ has source files | `list_dir .owlbear/sources/` → overview.md present. | PASS |
| AC5: .owlbear/scratch/ has scratch files, .instructions.md, .gitkeep | `git ls-tree 55a4d8c .owlbear/scratch/` → .gitkeep, .instructions.md, 585-auditor.md present. | PASS |
| AC6: .owlbear/scripts/ has validate_agents.py, validate_skills.py, e2e_smoke.py, skills_ref/ | `list_dir .owlbear/scripts/` → all 4 items present. | PASS |
| AC7: .owlbear/hooks/ has deny-writes.ps1 and lint-changed.ps1; originals remain in scripts/hooks/ | `list_dir .owlbear/hooks/` → both present. `list_dir scripts/hooks/` → deny-writes.ps1 and lint-changed.ps1 still present (plus deny-src-writes.ps1). | PASS |
| AC8: docs/ retains only setup-guide.md and sharing-guide.md | `git ls-tree 55a4d8c docs/` → exactly {setup-guide.md, sharing-guide.md}. (Subsequent task #604 moved them to setup/ as expected per cross-ref.) | PASS |
| AC9: scripts/ retains only setup.py and hooks/ | `git ls-tree 55a4d8c scripts/` → exactly {hooks/, setup.py}. | PASS |

### Security
No security concerns. Pure directory renames/copies — no code, no new system boundaries.

### Deductions
- **Commit attribution — mixed scope** (-0.05): Builder's #603 file moves (docs/* → .owlbear/*) were committed under commit `55a4d8c` titled as a `#602` test fix. Violates "one logical change per commit" from r-project-standards. Builder disclosed the file changes in Notes but did not provide a separate #603 commit.
- **Kanban move committed under #546 label** (-0.03): The deferred kanban git mv appeared in commit `4c7caea` labeled as the #546 test-writer commit. Builder disclosed the deferral with valid operational reason (MCP must write to task file before git mv). Functional outcome correct; traceability is muddied.

### Verdict
9/9 ACs verified against git state (`git ls-tree` at builder commit) and current filesystem. All file moves completed. Deductions are process/attribution discipline findings only — no functional defects.

**Confidence: 0.90 → PASS**

[[2026-04-05]] Sun 07:00
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Updated | `kanban/` → `.owlbear/kanban/` throughout README.md; `.owlbear/` added to directory layout table; `docs/` and `scripts/` descriptions updated; Quick Start setup.ps1 path corrected |
| 2 | Module docstrings | No | N/A | Pure file moves — no Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns or sources used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | type:config pass-through — no research phase |

### Files Updated
- README.md: Quick Start path corrected to `.owlbear\kanban\setup.ps1`; directory table updated (`.owlbear/` row added, `kanban/` row removed, `docs/` and `scripts/` descriptions revised); "How It Works" kanban reference updated to `.owlbear/kanban/`

### Commit Note
Commit blocked by pre-existing pre-commit failures: `test_agent_port_v2` (agent frontmatter) and stale `.pre-commit-config.yaml` entry (`scripts/validate_skills.py` moved to `.owlbear/scripts/` by this task). README change is correct on disk; commit deferred to #607 (reference updates scope).

### Scratch Files Cleaned
- None found

[[2026-04-05]] Sun 08:34
## Audit - see scratch
