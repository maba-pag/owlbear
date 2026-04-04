---
id: 598
title: Five-tier folder restructure (share/serve/store/seed/.owlbear)
status: in-progress
priority: needed
created: 2026-04-04T20:30:01.0914716+02:00
updated: 2026-04-04T22:54:43.8129085+02:00
tags:
    - scope:infra
    - type:restructure
    - type:config
    - phase-2
depends_on:
    - 609
class: standard
---

## Summary

Restructure the owlbear repo into a five-tier model: share/ serve/ store/ seed/ + .owlbear/

Decision doc: docs/decisions/pending/owlbear-folder-restructure.md

## Context

OwlBear currently uses .github/ for agents/skills/instructions/prompts which creates namespace confusion when shared to target projects. A previous attempt moved to root-level folders (agents/, skills/) but that was reversed because it cluttered the project root.

The five-tier model separates concerns cleanly:
- share/ = VS Code customizations (linked by targets)
- serve/ = Python runtime services (used by targets via MCP)
- store/ = global persistent state (cross-project)
- seed/ = project templates (copied into targets)
- .owlbear/ = project operational data (per-project)

## Acceptance Criteria (Final Gate)

- [ ] AC1: Decision doc in .owlbear/decisions/resolved/ with status Resolved
- [ ] AC2: All 11 subtasks (#599 through #609) completed and verified
- [ ] AC3: uv run pytest passes (full suite, no failures)
- [ ] AC4: uv run ruff check passes (no lint errors)
- [ ] AC5: VS Code discovers agents/skills/instructions from share/ (manual verification)
- [ ] AC6: All 4 owlbear MCP servers (kanban, knowledge, memory, project) start and respond to list_tools (uv run python -m {module})
- [ ] AC7: setup/init.py bootstraps a test target project with correct .owlbear/ structure
- [ ] AC8: No references to old paths in live (non-historical) files

## Subtasks

#599 Research: kanban-md path verify (blocker)
#600 Move .github/ customizations to share/
#601 Rename packages/ to serve/
#602 Rename data/ to store/
#603 Move project ops data to .owlbear/
#604 Create seed/ templates and setup/init.py
#605 Extract system instructions from copilot-instructions.md
#606 Update MCP server path resolution
#607 Update live references to new folder paths
#608 Update tests for new folder structure
#609 Post-migration cleanup and config updates

## Risks

- kanban-md binary may assume kanban/ directory name
- setup.py shallow merge bug in chat.*Locations (pre-existing)
- Large diff touching hundreds of files
- Historical docs not updated (intentional: they document history)

## Architecture Review

[[2026-04-04]]

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Umbrella task coordinating 11 well-decomposed subtasks. Each subtask has single domain. |
| Interface clarity | PASS | All 8 AC items are mechanically verifiable (pytest, ruff, grep, MCP startup). AC6 refined to specify 4 servers. |
| Dependency correctness | PASS (fixed) | Circular dependency removed: subtasks #599-#602 now use parent: 598 instead of depends_on: [598]. All subtasks have parent: 598. DAG is acyclic. |
| Module layering | N/A | Restructure task — no new code modules. Subtask #606 handles MCP path resolution. |
| TDD compliance | PASS | Subtask #608 dedicated to test updates. Umbrella tagged type:config (pass-through). |
| KISS/YAGNI | PASS | Five-tier model addresses real namespace confusion. Previous root-level attempt was reversed, validating this approach. |
| Premise challenge | PASS | .github/ namespace conflict with target projects is real. No simpler fix — explicit chat.*Locations settings needed anyway. |
| Pattern consistency | PASS | MCP servers use env-var + default Path pattern. Migration follows git mv + config update pattern. |
| Security surface | PASS | No new system boundaries. File moves only. |
| Single domain | PASS | scope:infra, type:restructure. Each subtask scoped to its domain. |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| kanban-md from .owlbear/kanban/ | Binary assumes cwd=kanban/ | FileNotFoundError | Yes — #599 research blocker | Board ops fail |
| VS Code discovery from share/ | .github/ auto-discovery lost | None (silent) | Yes — AC5, #600 AC6-AC7 | Agents not visible |
| MCP server path resolution | Hardcoded defaults stale | FileNotFoundError | Yes — #606 | MCP tools unavailable |
| setup.py → setup/init.py | Old setup.py referenced | ImportError | Yes — #604 replaces, #607 refs | Setup fails |

### Dependency Graph (fixed)

```
#598 (umbrella, depends_on: [609])
├── #599 (research, no deps — leaf starter)
├── #600 (move .github/ → share/, no deps — leaf starter)
├── #601 (rename packages/ → serve/, no deps — leaf starter)
├── #602 (rename data/ → store/, no deps — leaf starter)
├── #603 (move ops → .owlbear/, depends: [599])
├── #604 (seed/ + setup/init.py, depends: [600, 603])
├── #605 (extract instructions, depends: [600])
├── #606 (MCP paths, depends: [601, 602, 603])
├── #607 (live references, depends: [600, 601, 602, 603])
├── #608 (tests, depends: [600, 601, 602, 603, 604])
└── #609 (cleanup, depends: [604, 605, 606, 607, 608])
```

### Refinements Applied

1. Circular dependency fixed: #599-#602 changed from depends_on: [598] to parent: 598
2. AC6 corrected: "5 MCP servers" → "4 owlbear MCP servers (kanban, knowledge, memory, project)"
3. Pass-through tag added: type:config for non-implementation umbrella

### Challenge Results

- Challenger: reconsider (confidence: 0.62)
- Concerns: (1) #117/#166 conflict, (2) kanban-md research unverified, (3) AC1 circular
- Architect response: Override with rebuttal
  - #117/#166 superseded by this new approach (share/ not root-level)
  - #599 research correctly sequenced as subtask before #603
  - AC "Final Gate" heading — AC1 is post-migration verification, not pre-condition

### Superseded Tasks

#117 and #166 (delete .github/skills/ and agents/) are superseded by this migration.

### Verdict: APPROVE
### Action Taken: Fixed circular dep, refined AC6, added type:config tag, advanced to todo.

[[2026-04-04]] Sat 21:54
APPROVED #598 -> todo | Five-tier restructure umbrella. Fixed circular dependency (subtasks now use parent: 598 instead of depends_on: [598]). Refined AC6 (4 MCP servers, not 5). Added type:config pass-through tag. Challenger overridden — concerns already addressed by task graph.

[[2026-04-04]] Sat 22:54
Non-implementation umbrella task (tagged type:config, type:restructure) — no tests applicable. All testable behavior is delegated to subtasks #599–#609, particularly #608 (dedicated test-update subtask). Passing through to builder.
