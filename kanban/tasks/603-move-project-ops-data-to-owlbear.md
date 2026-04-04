---
id: 603
title: Move project ops data to .owlbear/
status: todo
priority: needed
created: 2026-04-04T20:30:51.9919622+02:00
updated: 2026-04-04T22:26:22.4400211+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - type:config
parent: 598
depends_on:
    - 599
class: standard
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
