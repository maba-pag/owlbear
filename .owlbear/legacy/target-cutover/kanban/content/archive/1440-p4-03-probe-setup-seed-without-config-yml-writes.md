---
id: 1440
title: 'P4-03: Probe setup seed without config.yml writes'
status: archived
priority: medium
created: 2026-05-08T19:31:51.041322+00:00
updated: 2026-05-09T00:25:41.696230+00:00
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
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: No source-code changes (td:0 probe task). Evidence gathered via scratch workspace runs only.
- Probe command context: ran `uv run ../../../setup/init.py` from target scratch directories under `.owlbear/scratch/1440-probe-*`.
- Empty-target probe results:
  - Created `.owlbear/kanban/tasks` and `.owlbear/kanban/archive`.
  - `.owlbear/kanban/config.yml` present (`empty_has_config=yes`).
  - `.owlbear/decisions/pending` absent (`empty_has_decisions_pending=no`).
  - `.owlbear/decisions/resolved` absent (`empty_has_decisions_resolved=no`).
  - Delta vs expected post-#1441 state documented: current behavior still writes config and does not create decisions dirs.
- Preservation probe results:
  - Pre-seeded sentinels in tasks/archive/decisions files remained unchanged after init:
    - `task-pre.md=SENTINEL_TASK_1440`
    - `archive-pre.md=SENTINEL_ARCHIVE_1440`
    - `dr-pre.md=SENTINEL_DR_PRE_1440`
    - `drr-pre.md=SENTINEL_DRR_PRE_1440`
- Seed tree + codepath inspection:
  - `seed/.owlbear/kanban/config.yml` exists (`seed_has_config=yes`).
  - `seed/.owlbear/decisions/` does not exist (`seed_has_decisions_dir=no`).
  - `setup/init.py` shows generic seed copy path through `_write_seed_file` (definition around line 192; invocation around line 370).
  - No `config.yml`-specific or `decisions`-specific dispatch path found in `setup/init.py`.
- Tests: Not run (AC explicitly restricts evidence to probe notes/artifact inspection).
- Lint: Not run (non-implementation td:0 probe; no code changes).
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner not dispatched. All corrected AC lines are td:0 in .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:54-57, the task made no code changes, and the deliverable is artifact inspection rather than executable proof.
- pytest/vitest: not expected for this task. This matches the builder note in .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:102.
- lint: not expected for this task. This matches the builder note in .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:103.

### Artifact Verification
- Empty-target probe: .owlbear/scratch/1440-probe-empty/.owlbear/kanban contains archive/, config.yml, and tasks/; .owlbear/scratch/1440-probe-empty/.owlbear contains hooks/, kanban/, knowledge/, and scripts/ with no decisions/ directory. .owlbear/scratch/1440-probe-empty/.owlbear/kanban/config.yml:1 confirms config.yml is written. This matches the builder note at .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:87-89.
- Preservation probe: sentinel contents are intact after setup in .owlbear/scratch/1440-probe-preserve/.owlbear/kanban/tasks/task-pre.md:1, .owlbear/scratch/1440-probe-preserve/.owlbear/kanban/archive/archive-pre.md:1, .owlbear/scratch/1440-probe-preserve/.owlbear/decisions/pending/dr-pre.md:1, and .owlbear/scratch/1440-probe-preserve/.owlbear/decisions/resolved/drr-pre.md:1. This matches the builder note at .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:93-96.
- Seed/init inspection: seed/.owlbear/kanban/config.yml exists; file search for seed/.owlbear/decisions/** returns no files. setup/init.py defines _write_seed_file at line 192, applies generic .yml handling at line 194, and invokes _write_seed_file from the seed walk at line 370. grep for "decisions" in setup/init.py returned no matches. This matches the builder note at .owlbear/kanban/tasks/1440-p4-03-probe-setup-seed-without-config-yml-writes.md:98-100.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: empty-target probe records created kanban dirs, config.yml write, and decisions-dir absence | .owlbear/scratch/1440-probe-empty/.owlbear/kanban/config.yml:1 plus directory listings of .owlbear/scratch/1440-probe-empty/.owlbear and .owlbear/scratch/1440-probe-empty/.owlbear/kanban | PASS |
| AC2: preservation probe retains pre-existing task/archive/decision file contents | Sentinel files unchanged at the four preserve paths above, each verified at line 1 | PASS |
| AC3: seed tree and init.py inspection documents config.yml presence, generic copy path, and absence of seed decisions dir | seed/.owlbear/kanban/config.yml exists; no seed/.owlbear/decisions/** files; setup/init.py:192, :194, :370; grep "decisions" => no matches | PASS |
| AC4: proof limited to probe notes/artifact inspection, no pytest/vitest/full-suite execution | Builder note explicitly records tests not run and lint not run at task file lines 102-103; no task-specific 1440 pytest/vitest scratch logs were observed | PASS |

### Pass 1 Checks
- Test-writer audit: SKIP. td:0 task; no TestFromAC_* classes.
- Security review: PASS. No source-code or dependency changes were introduced.
- Test integrity/test quality/test gaps: SKIP. No test artifact deliverable for this td:0 probe task.
- Data safety: PASS. No persistent behavior change or mutable-state change was introduced.
- Necessity check: SKIP. No new dependency/integration/tooling added.
- Builder process quality: CLEAN. No prior ## Review Evidence sections found in the task file.

### Deductions
- -0.03 confidence: the preservation probe can be verified only from final artifact state plus the recorded builder note; the pre-seeding chronology is not directly replayable from the remaining files alone.
- -0.02 confidence: no builder commit hash was present and this session had no git-status/diff tool available, so dirty-tree contamination could not be checked directly.

### Verdict
PASS
Confidence: 0.95
Action: Advance to docs.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | td:0 probe task — no behavior, API, CLI, config, or package structure changes |
| 2 | Module docstrings | No | N/A | No `.py` files created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase document produced |
| 5 | Diagram maintenance (describes match) | No | N/A | No changed files to match against diagram describes entries |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.owlbear/scratch/1440-probe-empty/` | OUT (scratch) | Deleted |
| `.owlbear/scratch/1440-probe-preserve/` | OUT (scratch) | Deleted |
| `setup/init.py` | OUT (inspected only, not changed) | N/A |
| `seed/.owlbear/kanban/config.yml` | OUT (inspected only, not changed) | N/A |

No docs impact — all checklist items N/A. Pure td:0 probe task; deliverable is probe notes in task body only.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1440-probe-empty/` (deleted)
- `.owlbear/scratch/1440-probe-preserve/` (deleted)
[[2026-05-09]]
## Audit

### AC Verification (corrected AC from architect review)

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: empty-target probe records kanban dirs, config.yml write, decisions-dir absence | Builder notes document: tasks/archive created, config.yml present, decisions dirs absent. Reviewer verified via artifact listing at scratch probe paths. Probe directories cleaned. | PASS |
| AC2: preservation probe retains pre-existing files | Builder notes document 4 sentinel files retained. Reviewer verified at 4 file paths (task-pre.md, archive-pre.md, dr-pre.md, drr-pre.md). | PASS |
| AC3: seed tree and init.py inspection | Auditor confirmed seed/.owlbear/kanban/config.yml exists (41-line YAML). Reviewer confirmed _write_seed_file at init.py:192,:194,:370 and no "decisions" grep matches. | PASS |
| AC4: no pytest/vitest execution as proof | No test artifacts found. Builder explicitly noted tests/lint not run. | PASS |

### Test Results
- pytest (full suite): 459 pre-existing failures across kanban/cockpit/MCP packages. Zero failures attributable to this task (no code changes made).
- ruff: 12 pre-existing violations in knowledge/tools packages. None in task scope.
- Cross-task regression: None detected. All failures are baseline.

### Architect Quality: 4/5
Original AC had factual errors (AC1 and AC3 assumed post-#1441 state as current), but architect caught and corrected them. Corrected AC was specific, well-scoped for td:0 probe.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 4 PASS)
- Lint violations in scope: 0
- AC quality deduction: 0 (score 4, threshold is 3 or below)
- Missing reviewer evidence: 0 (present and detailed)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: Archive