---
id: 1440
title: 'P4-03: Probe setup seed without config.yml writes'
status: todo
priority: needed
created: 2026-05-08T19:31:51.041322+00:00
updated: 2026-05-08T20:23:37.441601+00:00
tags:
- phase-4
- scope:setup
- type:test
- verification-probe
- deployment-readiness
parent: 1437
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: setup/init.py and seed board bootstrap behavior.
Out of scope: kanban engine internals, MCP tools, Cockpit UI, and docs.

## Acceptance Criteria
1. Test-writer records a scratch-workspace setup probe where setup.init runs against an empty target and the expected artifact state is tasks, archive, decisions/pending, and decisions/resolved directories present with no .owlbear/kanban/config.yml file.
2. Test-writer records a board-preservation probe where a target with pre-existing task, archive, and decision files is passed to setup.init and those files retain their content after setup completes.
3. Test-writer records a seed-tree inspection showing seed/.owlbear/kanban/config.yml absent and setup/init.py lacking a per-file write path for that seed file.
4. Test-writer adds no pytest, vitest, or full-suite execution as functional proof; verification evidence is limited to scratch-workspace probe notes and artifact inspection.
[[2026-05-08]]


## Architecture Review

**Verdict:** APPROVE (after inline AC correction)
**Test-depth:** all td:0 → Test-writer: SKIP

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| 1 | States "decisions/pending and decisions/resolved directories present with no config.yml" as expected artifact state — but seed currently lacks decisions dirs and DOES contain config.yml. Intent is correct (defining desired post-#1441 state) but phrasing implies current-state observation. | Rewrite below: document deltas from expected state |
| 2 | Sound — preservation probe is well-scoped | td:0 annotated |
| 3 | States "showing config.yml absent" — currently FALSE (`seed/.owlbear/kanban/config.yml` exists, 41 lines). States "init.py lacking a per-file write path" — init.py copies it via generic `_write_seed_file`, which is technically not a per-file path but IS the mechanism that writes it. | Rewrite below: document current presence + codepath |
| 4 | Sound — meta-constraint consistent with parent #1437 planning | td:0 annotated |

### Corrected Acceptance Criteria (supersedes original)

1. Builder runs setup.init against an empty scratch-workspace target and records the resulting artifact tree, noting: (a) which `.owlbear/kanban/` directories are created, (b) whether `config.yml` is written, (c) whether `decisions/pending` and `decisions/resolved` directories are created — documenting deltas from the expected post-#1441 state (tasks + archive + decisions dirs present, no config.yml). (td:0)
2. Builder runs setup.init against a target with pre-existing task, archive, and decision files and verifies those files retain their content after setup completes. (td:0)
3. Builder inspects the seed tree and `init.py` source, documenting: (a) current presence of `seed/.owlbear/kanban/config.yml` and the `_write_seed_file` codepath that copies it, (b) absence of `seed/.owlbear/decisions/` — establishing removal and addition targets for #1441. (td:0)
4. No pytest, vitest, or full-suite execution is used as functional proof; verification evidence is limited to scratch-workspace probe notes recorded in the task body. (td:0)

### Architecture Notes

- `setup/init.py` walks `seed_dir.rglob("*")` and copies all non-special files via `_write_seed_file`. Special dispatch exists for `settings.json`, `mcp.json`, `.gitignore`, `_SKIP_IF_EXISTS_REL` files, and hooks — but NOT for `config.yml`.
- Current seed tree: `seed/.owlbear/kanban/{config.yml, tasks/.gitkeep, archive/.gitkeep}`. No decisions directories anywhere under `seed/.owlbear/`.
- `init.py` contains zero references to "decisions" — directory creation must be added by #1441.
- Probe value: creates the reference artifact that #1441 builder uses as a delta checklist.

### Dependency Analysis

- No inbound dependencies (root probe). Correct: #1441 depends on this task.
- No conflicts with sibling probes (#1438, #1442, #1444).

### Challenge

Skipped — all AC lines are td:0 (Step 2.1 gate).

[[2026-05-08]]
Architecture review complete. Corrected AC #1 and #3: original text assumed post-implementation state (config.yml absent, decisions dirs present) but codebase shows config.yml exists in seed (41-line YAML) and no decisions directories exist under seed/.owlbear/. Corrected AC reframes probes as delta documentation against expected post-#1441 state. All AC lines td:0 — test-writer SKIP.