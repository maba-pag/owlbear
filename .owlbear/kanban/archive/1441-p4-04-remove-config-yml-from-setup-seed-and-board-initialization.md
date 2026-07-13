---
id: 1441
title: 'P4-04: Remove config.yml from setup seed and board initialization'
status: archived
priority: medium
created: 2026-05-08T19:31:53.767342+00:00
updated: 2026-05-10T21:07:27.061721+00:00
tags:
- phase-4
- scope:setup
- type:refactor
- seed
- deployment-readiness
parent: 1437
depends_on:
- 1440
- 1439
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: setup seed files and setup/init.py board-directory creation.
Out of scope: engine constants, MCP transport, Cockpit UI, and docs.

## Acceptance Criteria
1. Builder removes seed/.owlbear/kanban/config.yml from the seed tree and leaves no replacement topology template under seed.
2. setup.init creates missing board directories for tasks, archive, decisions/pending, and decisions/resolved without writing .owlbear/kanban/config.yml.
3. Given a target with existing task, archive, decision, and activity files, setup.init preserves those files' content and does not rewrite task frontmatter.
4. setup.init remains compatible with the fixed-topology engine from #1439 when the target board has no config.yml.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1440 and does not use pytest or vitest as the functional proof.
[[2026-05-10]]


## Refined Acceptance Criteria
_Replaces original AC above. Refinements: added AC-2 for obsolete test cleanup, specified explicit board-directory paths under `.owlbear/kanban/`, clarified probe methodology._

1. Builder removes `seed/.owlbear/kanban/config.yml` from the seed tree and leaves no replacement topology template under `seed/`. (td:0)
2. Builder removes the `TestFromAC_SeedTemplateGroupedFormat` class and the unused `_SEED_CONFIG` constant from `tests/test_config_grouped.py` (made obsolete by AC-1; remaining AC9 migration tests are unaffected). (td:0)
3. `setup.init()` creates four board directories under `.owlbear/kanban/` — `tasks`, `archive`, `decisions/pending`, `decisions/resolved` — using `Path.mkdir(parents=True, exist_ok=True)` after the seed-tree walk, without writing `config.yml`. (td:1)
4. Given a target with existing task, archive, and decision files under `.owlbear/kanban/`, `setup.init()` preserves those files' content unchanged. (td:0)
5. `setup.init()` works correctly with the fixed-topology engine from #1439 when the target board has no `config.yml`. (td:0)
6. Builder re-runs the empty-target and preservation probe scenarios from #1440 methodology as manual verification of AC-1, AC-3–5. (td:0)

## Architecture Notes
- **Board-directory path**: all four directories are under `.owlbear/kanban/` (the board root), aligned with engine topology (`topology.py` → `tasks_dir`, `archive_dir`, `decisions_dir`), MCP server (`server.py:333`), and Cockpit backend (`deps.py:55`). The workspace's `.owlbear/decisions/` at top-level is a legacy location predating the engine's decisions support — that migration is out of scope (covered by #1455 docs update).
- **Seed .gitkeep files**: `seed/.owlbear/kanban/tasks/.gitkeep` and `seed/.owlbear/kanban/archive/.gitkeep` remain and continue providing implicit directory creation for those two directories. The explicit `mkdir` calls in AC-3 provide redundancy for tasks/archive and are the sole creation mechanism for decisions/pending and decisions/resolved.
- **Engine compatibility**: `storage._resolve_board_config()` already returns `config=None` when `config.yml` is missing. `PRODUCT_TOPOLOGY` from #1439 provides all constants. No config.yml read path is exercised at runtime for fixed-topology boards.
[[2026-05-10]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Setup seed + init.py board-directory creation — one domain |
| Interface clarity | PASS (after refine) | Refined AC specifies exact paths, exact classes to remove, exact mkdir calls |
| Dependency correctness | PASS | #1439 (fixed-topology engine) and #1440 (probe) both archived/done |
| Module layering | PASS | Changes confined to setup/init.py and seed files; no upward imports |
| TDD compliance | PASS | AC-3 (td:1) gets test-writer coverage; remaining AC lines are td:0 |
| KISS/YAGNI | PASS | Minimal scope, no abstractions, uses stdlib Path.mkdir |
| Premise challenge | PASS | Removing seed config.yml is a necessary consequence of #1439 fixed topology |
| Pattern consistency | PASS | Extends init.py's existing seed-walk pattern with post-walk mkdir calls |
| Security surface | PASS | No new system boundaries; directory creation uses standard Path.mkdir |
| Single domain | PASS | setup domain only |

### AC Assessment
| Original AC | Refined AC | Action |
|-------------|-----------|--------|
| AC-1: remove seed config.yml | AC-1: unchanged (td:0) | Retained |
| — | AC-2: remove TestFromAC_SeedTemplateGroupedFormat + _SEED_CONFIG (td:0) | Added — obsolete tests will fail after AC-1 |
| AC-2: create board directories | AC-3: explicit paths under .owlbear/kanban/ (td:1) | Tightened — specified exact paths and mechanism |
| AC-3: preserve existing files | AC-4: scoped to .owlbear/kanban/ (td:0) | Tightened — inherent from mkdir(exist_ok=True) |
| AC-4: engine compatibility | AC-5: unchanged (td:0) | Retained |
| AC-5: probe verification | AC-6: methodology not artifacts (td:0) | Fixed — probe artifacts are transient |

### Challenge Results
- Challenger: block (confidence 0.44)
- Critical findings: (1) stale task body — resolved by persisting refined AC; (2) decision-path collision .owlbear/decisions/ vs .owlbear/kanban/decisions/ — pre-existing discrepancy, engine/MCP/Cockpit consistently use kanban_dir/decisions, out of scope for this task
- Moderate findings: (3) proof masking from .gitkeep — decisions dirs have no .gitkeep so they discriminate; (4) probe artifacts gone — AC rewritten to reference methodology
- Architect response: override block — decision-path discrepancy is pre-existing, not introduced by this task; all three runtime consumers (engine, MCP, Cockpit) agree on kanban_dir/decisions

### Test Depth
- Max depth: 1 (AC-3 only)
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC (added test cleanup AC-2, specified exact board-directory paths, fixed probe reference), persisted to task body, advanced to todo.
[[2026-05-10]]
## Test-Writer Notes

**Test file:** `tests/test_setup_init_1441.py`

**Class:** `TestFromAC_BoardDirectoryCreation`

| Category | Tests |
|----------|-------|
| Happy path | 3 (decisions/pending created, decisions/resolved created, all four dirs exist) |
| Edge | 1 (idempotent second run) |
| Boundary | 1 (nested dirs require parents=True) |
| Error/contract | 1 (config.yml must not be written) |
| **Total** | **6 — all FAIL** |

**AC coverage:**

| AC line | Tests covering it |
|---------|------------------|
| AC-3: tasks dir created | `test_all_four_board_dirs_exist_after_init` |
| AC-3: archive dir created | `test_all_four_board_dirs_exist_after_init` |
| AC-3: decisions/pending created | `test_decisions_pending_dir_created_on_fresh_target`, `test_all_four_board_dirs_exist_after_init`, `test_board_dirs_created_idempotently`, `test_decisions_dirs_created_with_parents` |
| AC-3: decisions/resolved created | `test_decisions_resolved_dir_created_on_fresh_target`, `test_all_four_board_dirs_exist_after_init`, `test_board_dirs_created_idempotently`, `test_decisions_dirs_created_with_parents` |
| AC-3: mkdir(parents=True, exist_ok=True) | `test_decisions_dirs_created_with_parents` (parents), `test_board_dirs_created_idempotently` (exist_ok) |
| AC-3: without writing config.yml | `test_config_yml_not_written_to_board_dir` |

**Fail confirmation:** pytest shows 6 failed, 0 passed. Ruff exit 0.

**AC-1, AC-2, AC-4, AC-5, AC-6:** td:0 — no tests written (builder verification only).
[[2026-05-10]]
## Builder Notes
- Implementation: removed `seed/.owlbear/kanban/config.yml`; added explicit post-seed board directory creation in `setup/init.py` for `tasks`, `archive`, `decisions/pending`, and `decisions/resolved` via `Path.mkdir(parents=True, exist_ok=True)`; removed obsolete `TestFromAC_SeedTemplateGroupedFormat` class and `_SEED_CONFIG` constant from `tests/test_config_grouped.py`.
- Tests (quality-runner): `tests/test_setup_init_1441.py` + `tests/test_config_grouped.py` => 19 passed, 0 failed, 0 skipped.
- Lint (quality-runner): clean (`ruff check` + `ruff format --check` on `setup/init.py`, `tests/test_setup_init_1441.py`, `tests/test_config_grouped.py`).
- Coverage: quality-runner reported task-scoped run pass; `setup.init` coverage metric is not directly meaningful in this suite because `init()` is exercised via subprocess import pattern.
- Manual probe verification (AC-6 methodology, non-pytest/vitest):
  - Empty-target probe: PASS — after `init()`, `.owlbear/kanban/{tasks,archive,decisions/pending,decisions/resolved}` exist; `.owlbear/kanban/config.yml` absent.
  - Preservation probe: PASS — pre-existing task/archive/decision files retained byte-identical content after `init()`.
  - Engine compatibility probe (no config.yml): PASS — `KanbanEngine(kanban_dir_without_config)` initializes and `list_tasks()` executes without exception.
- Commit: `4afea41c` (`refactor: remove seeded kanban config and create board dirs (#1441, builder)`).
[[2026-05-10]]
## Review Evidence
### Test Results
- Independent quality-runner scoped rerun: `tests/test_setup_init_1441.py` + `tests/test_config_grouped.py` => 19 passed, 0 failed, 0 skipped.
- Independent lint rerun in the same scoped pass: clean for `setup/init.py`, `tests/test_setup_init_1441.py`, and `tests/test_config_grouped.py`.
- Coverage output was informational only: quality-runner reported 23% overall on broad `serve.kanban.*` modules, which does not meaningfully measure `setup/init.py` for this td:1 task. This is consistent with the builder note that `setup.init()` coverage is not directly meaningful in this suite.
- Builder evidence is internally consistent with the independent rerun and with direct file inspection.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC-1 | Task AC at lines 44-49. `file_search("seed/.owlbear/kanban/**")` returned only `seed/.owlbear/kanban/archive/.gitkeep` and `seed/.owlbear/kanban/tasks/.gitkeep`; `file_search("seed/**/config.yml")` returned no matches. Builder manual empty-target probe is recorded at task lines 129-130. | PASS |
| AC-2 | Task line 45. `grep_search("TestFromAC_SeedTemplateGroupedFormat|_SEED_CONFIG", includePattern="tests/test_config_grouped.py")` returned no matches; builder note at task line 125 reports removing both. | PASS |
| AC-3 | Task line 46. `setup/init.py:372-379` creates `.owlbear/kanban/{tasks,archive,decisions/pending,decisions/resolved}` via `Path.mkdir(parents=True, exist_ok=True)` after the seed walk. `tests/test_setup_init_1441.py:66`, `:85`, `:115`, `:134`, `:159-163`, and `:191-195` assert exact directory existence, no `config.yml`, idempotent re-run behavior, and nested directory creation requiring `parents=True`. Independent quality-runner rerun is green. | PASS |
| AC-4 | Task line 47. Post-seed code path in `setup/init.py:372-379` performs directory-only `mkdir(..., exist_ok=True)` calls, which do not rewrite existing task/archive/decision files. Builder preservation probe is recorded PASS at task lines 129-131. | PASS |
| AC-5 | Task line 48. `serve/kanban/src/owlbear_kanban/storage.py:137-138` returns `(board_dir, None)` when `config.yml` is absent. `serve/kanban/src/owlbear_kanban/config_loader.py:38-39`, `:54`, and `:57-58` show config loading is optional and default topology paths come from `PRODUCT_TOPOLOGY`. Builder engine-compatibility probe is recorded PASS at task line 132. | PASS |
| AC-6 | Task line 49. Builder notes at task lines 129-132 record the required empty-target, preservation, and engine-compatibility manual probes, satisfying the non-pytest/vitest verification requirement. | PASS |

### Test Audit
| Test / Proof Surface | Would Fail If AC Violated? | Assessment |
|---|---|---|
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_decisions_pending_dir_created_on_fresh_target` | Yes | Exact `.is_dir()` assertion on the pending directory at line 66. |
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_decisions_resolved_dir_created_on_fresh_target` | Yes | Exact `.is_dir()` assertion on the resolved directory at line 85. |
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_all_four_board_dirs_exist_after_init` | Yes | Exact `missing == []` style proof at line 115 across all four required directories. |
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_config_yml_not_written_to_board_dir` | Yes | Exact absence assertion for `.owlbear/kanban/config.yml` at line 134. |
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_board_dirs_created_idempotently` | Yes | Second `init()` call plus exact directory assertions at lines 159-163 would fail if `exist_ok=True` behavior regressed. |
| `tests/test_setup_init_1441.py::TestFromAC_BoardDirectoryCreation::test_decisions_dirs_created_with_parents` | Yes | Nested directory assertions at lines 191-195 would fail if `parents=True` were omitted. |

### Observations
- `tests/test_config_grouped.py:7` still contains a stale module docstring reference to the removed seed-template AC10. This is commentary drift only; no live test or assertion still depends on the deleted seed config file.
- `setup/setup-guide.md:58` still states that `.owlbear/kanban/config.yml` is always written. Docs are explicitly out of scope for #1441 and this appears to be covered by follow-up doc work, so it is non-blocking here.

### Deductions
- `-0.03` No terminal tool was available in this session, so I could not run `git diff --name-only 4afea41c~1 4afea41c` or `git status --porcelain` for dirty-tree contamination. Commit `4afea41c` existence was still confirmed through `.git/logs/**`.
- `-0.02` TestFromAC immutability was reconstructed from current file state plus builder notes rather than a direct commit diff.

### Verdict
- PASS
- Confidence: 0.93

### Action
- Advance task to `docs`.
[[2026-05-10]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `setup/setup-guide.md:58` had stale `config.yml` row ("Always written"). Removed row; added two rows for `decisions/pending/` and `decisions/resolved/` matching the new `mkdir` behavior in `setup/init.py`. |
| 2 | Module docstrings | Yes | Updated | `setup/init.py::init()` docstring described only the seed walk. Added sentence: "Also creates the four kanban board directories under `.owlbear/kanban/` (`tasks`, `archive`, `decisions/pending`, `decisions/resolved`)." |
| 3 | External attribution | No | N/A | No external patterns referenced in task body or builder notes. |
| 4 | Research doc | No | N/A | No research phase document produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `project-overview.excalidraw` has `"describes": ["setup/**"]` — matches `setup/init.py`. Footer updated from `2026-05-09 (2c78ed43)` → `2026-05-10 (bef6d7e8)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | Yes | N/A (handled inline) | `seed/.owlbear/kanban/config.yml` was deleted. Sole IN-scope doc referencing it was `setup/setup-guide.md` — updated in Item 1. No orphaned IN-scope docs remain. `serve/kanban/README.md` migration docs reference `config.yml` in the context of migrating legacy boards — still accurate. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `seed/.owlbear/kanban/config.yml` | OUT (seed data, deleted) | Deletion handled via Item 1 prose update |
| `setup/init.py` | IN (docstrings) | Updated `init()` docstring |
| `setup/setup-guide.md` | IN | Updated (removed stale row, added 2 new rows) |
| `tests/test_setup_init_1441.py` | OUT (test file) | N/A |
| `tests/test_config_grouped.py` | OUT (test file) | N/A |
| `share/diagrams/project-overview.excalidraw` | IN (diagram, describes match) | Footer updated |

### Files Updated

- `setup/setup-guide.md` — removed stale `config.yml` row; added `decisions/pending/` and `decisions/resolved/` rows
- `setup/init.py` — updated `init()` docstring to document board-dir creation
- `share/diagrams/project-overview.excalidraw` — footer updated to `2026-05-10 (bef6d7e8)`

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1441-*` files found)

### Informational

- `share/instructions/owlbear-system.instructions.md:26` references `config.yml` in the tech stack table — OUT of scope (agent-executable). Drift is minor; no follow-up task warranted.
[[2026-05-10]]
## Audit
### Regression Detection
- quality-runner mode full: Python 71 passed / 0 failed; Frontend 1224 passed / 17 failed / 9 skipped; ruff clean
- 17 frontend failures are all in `ResponsiveLayout_1391.test.tsx` (task #1391 — Shell.css responsive layout, Card.tsx priority colors) — pre-existing, completely unrelated to #1441 setup/seed domain
- ESLint `react-hooks/exhaustive-deps` rule definition issue on `usePolling.ts` — pre-existing config issue
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: `seed/.owlbear/kanban/config.yml` deleted, `setup/init.py`, `tests/test_config_grouped.py`, `tests/test_setup_init_1441.py`, `setup/setup-guide.md`, `share/diagrams/project-overview.excalidraw` — all within setup/seed domain)
- purpose match: PASS (removing config.yml from seed tree, adding board-directory creation in init.py, cleaning obsolete tests — matches stated task purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
Refined AC was excellent: specific class/constant names for removal (AC-2), exact directory paths and mechanism (AC-3), clear scope boundaries, proper td annotations. Architecture notes about board-directory paths and engine compatibility were accurate and helpful.

### Commit Integrity
- upstream commit presence: PASS
  - test-writer `4c992df2`: `tests/test_setup_init_1441.py` only
  - builder `4afea41c`: `seed/.owlbear/kanban/config.yml`, `setup/init.py`, `tests/test_config_grouped.py`
  - doc-writer `902e9c55`: `setup/init.py`, `setup/setup-guide.md`, `share/diagrams/project-overview.excalidraw`
  - all commits properly scoped to their agent's domain
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
No deductions. All pillars pass cleanly. Pre-existing frontend failures are outside task scope and do not constitute regressions.

### Confidence: 1.00
### Action: archive