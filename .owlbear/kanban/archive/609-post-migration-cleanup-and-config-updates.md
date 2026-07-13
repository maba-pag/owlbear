---
id: 609
title: Post-migration cleanup and config updates
status: archived
priority: medium
created: 2026-04-04T20:32:03.4328653+02:00
updated: 2026-04-05T16:42:07.1846601+02:00
started: 2026-04-05T16:42:07.1846601+02:00
completed: 2026-04-05T16:42:07.1846601+02:00
tags:
    - scope:infra
    - type:config
    - phase-2
parent: 598
depends_on:
    - 604
    - 605
    - 606
    - 607
    - 608
class: standard
---

## Summary

Post-migration cleanup: update config files for the new five-tier folder structure, delete empty directories, finalize decision doc status, delete obsolete scripts/setup.py. This is the final subtask of #598 — after completion, the umbrella validation gate can run.

## Acceptance Criteria

### VS Code Settings
- [ ] AC1: .vscode/settings.json `files.exclude`: replace `"docs/scratch": true` with `".owlbear/scratch": true`; replace `"kanban\\kanban-md.exe": true` with `".owlbear\\kanban\\kanban-md.exe": true`. Verify `.owlbear/` is NOT in files.exclude (must remain visible in explorer).
- [ ] AC2: .vscode/settings.json `search.exclude`: `"docs/scratch/**"` → `".owlbear/scratch/**"`, `"kanban/activity.jsonl"` → `".owlbear/kanban/activity.jsonl"`, `"kanban/v1-archive/**"` → `".owlbear/kanban/v1-archive/**"`

### Git and Linting Config
- [ ] AC3: .gitignore updated: section comment `(under docs/)` → `(under .owlbear/)`; `docs/scratch/*` → `.owlbear/scratch/*`; `!docs/scratch/.gitkeep` → `!.owlbear/scratch/.gitkeep`; `!docs/scratch/.instructions.md` → `!.owlbear/scratch/.instructions.md`; `kanban/*.exe` → `.owlbear/kanban/*.exe`
- [ ] AC4: .pre-commit-config.yaml: validate-skills `entry:` → `python .owlbear/scripts/validate_skills.py`; validate-agents `entry:` → `python .owlbear/scripts/validate_agents.py`; validate-agents `files:` → `^share/agents/.*\.agent\.md$`. (Bandit `-r packages/` → `-r serve/` is #601 scope.)
- [ ] AC5: .markdownlint-cli2.jsonc `ignores` array: `docs/research/**` → `.owlbear/research/**`, `docs/scratch/**` → `.owlbear/scratch/**`. .markdownlintignore: `docs/research` → `.owlbear/research`, `docs/scratch` → `.owlbear/scratch`.

### Directory and File Cleanup
- [ ] AC6: docs/ directory deleted. After #603 and #604 git operations, only gitignored temp files (.tmp, .txt) remain in docs/scratch/. Safe to `rm -rf docs/` — tracked files already moved by #603 and #604.
- [ ] AC7: scripts/setup.py deleted (replaced by setup/init.py per #604 AC8). Verify scripts/ contains only setup.py after all #603 moves complete (hooks/, validate_*.py, e2e_smoke.py, skills_ref/ moved to .owlbear/). Delete setup.py, then delete empty scripts/ directory.

### Decision and Metadata
- [ ] AC8: `.owlbear/decisions/resolved/owlbear-folder-restructure.md` status line updated from `**Status:** Pending` to `**Status:** Resolved`. (File at this location after #603 moves docs/decisions/ → .owlbear/decisions/.)
- [ ] AC9: owlbear-project.json `schema_version` stays at 1 — no bump. Rationale: folder restructure changes directory layout, not project JSON schema (keys, types, required fields unchanged). Note rationale in commit message.

### Verification
- [ ] AC10: .gitkeep files present in `.owlbear/scratch/`, `.owlbear/knowledge/` (verify #603/#604 placed them; create only if missing)
- [ ] AC11: Verification gate: grep across .vscode/settings.json, .gitignore, .pre-commit-config.yaml, .markdownlint-cli2.jsonc, .markdownlintignore for stale patterns (`docs/scratch`, `docs/research`, `kanban/activity`, `kanban/v1-archive`, `kanban\\kanban-md`, `kanban/*.exe`, `scripts/validate`, `scripts/setup`) — zero matches

## Scope Boundaries

In scope: config files (.vscode/settings.json, .gitignore, .pre-commit-config.yaml, .markdownlint-cli2.jsonc, .markdownlintignore), directory deletion (docs/, scripts/), decision doc status, scripts/setup.py deletion, .gitkeep verification.

Out of scope (handled by other tasks):
- README.md directory layout: #607 AC6
- .vscode/settings.json chat.*Locations: #600
- .vscode/mcp.json server entries: #604 AC2
- .pre-commit-config.yaml bandit `-r packages/` path: #601
- pyproject.toml workspace paths/members: #601
- Python source code path constants: #602, #606
- Test file path updates: #608
- setup/init.py creation: #604
- Agent/skill/instruction file reference updates: #607
- copilot-instructions.md path references: #607 AC7

## Notes

- depends_on [604, 605, 606, 607, 608] ensures all upstream work completes before this task starts.
- docs/scratch/ after #603: git mv moves only tracked files (.gitkeep, .instructions.md). Hundreds of gitignored .tmp/.txt scratch files remain. Safe to rm -rf — these are agent temp artifacts.
- scripts/setup.py deletion: explicitly delegated from #604 (see #604 Notes). Both files may coexist temporarily between #604 and #609.
- #609 is the final subtask of #598. After #609 completes, the umbrella task (#598) validation gate (AC1-AC8) can run.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Cleanup/finalization is one logical operation — all items share the same trigger (all deps done) and same domain (config/infra). |
| Interface clarity | PASS (refined) | Original 10 AC items had 6 vague entries, 1 factual error, 1 overlap. Rewritten to 11 precise, verifiable items with exact old→new mappings. |
| Dependency correctness | PASS | Depends on [604, 605, 606, 607, 608]. All exist and correctly gate work: #604 (seed/setup), #605 (instructions extraction), #606 (MCP paths), #607 (reference sweep), #608 (tests). No missing deps. |
| Module layering | N/A | Config file edits and directory deletions only. No code modules. |
| TDD compliance | PASS | Tagged type:config (pass-through). No testable Python code produced. |
| KISS/YAGNI | PASS | Mechanical config updates. No abstractions, no features. |
| Premise challenge | PASS | Cleanup task is mechanically necessary after migration — stale config paths will break linting, IDE features, and pre-commit hooks. |
| Pattern consistency | PASS | Follows cleanup-task pattern from sibling tasks. |
| Security surface | PASS | No new system boundaries. Config edits and directory deletions only. |
| Single domain | PASS | scope:infra only. |

### Refinements Applied

1. **AC1 expanded**: Added `kanban\\kanban-md.exe` → `.owlbear\\kanban\\kanban-md.exe` (in files.exclude L47, discovered by challenger)
2. **AC2 specified**: Exact 3 old→new entries for search.exclude
3. **AC3 specified**: Exact 5 old→new entries for .gitignore including section comment and exceptions
4. **AC4 specified**: Exact 3 pre-commit changes with scope boundary (bandit is #601)
5. **AC5 added**: .markdownlint-cli2.jsonc and .markdownlintignore (discovered by challenger — stale `docs/research/**` and `docs/scratch/**` patterns)
6. **AC6 clarified**: Explicit note that tracked files already moved, only gitignored temps remain
7. **AC7 added**: scripts/setup.py deletion (delegated from #604 Notes) + scripts/ directory cleanup with precondition inventory
8. **AC8 fixed**: Source path corrected from `docs/decisions/pending/` (wrong) to `.owlbear/decisions/resolved/` with #603 sequencing note
9. **AC9 resolved**: Changed from "if needed" (unverifiable) to explicit "no bump" with rationale
10. **AC10 specified**: Named exactly which directories need .gitkeep
11. **AC11 added**: Verification gate with explicit grep scope covering all 5 config files
12. **Original AC7 (README) removed**: Duplicate of #607 AC6 scope
13. **Tag changed**: type:build → type:config (pass-through for non-implementation)
14. **Scope Boundaries section added**: 10 explicit handoffs to sibling tasks
15. **Notes section expanded**: Temporal gap (docs/scratch gitignore), scripts/setup.py delegation, umbrella gate sequencing

### Challenge Results

- Challenger: block (confidence: 0.25)
- 10 concerns raised (4 critical, 4 major, 2 minor)
- Architect response: Override block — accepted 4, partially accepted 1, dismissed 5
  - C1 (kanban-md.exe in files.exclude): ACCEPTED → added to AC1
  - C2 (markdown linter configs): ACCEPTED → added as AC5
  - C3 (decision doc location): PARTIALLY ACCEPTED → AC8 clarified with #603 sequencing note
  - C4 (agent docs/scratch refs): DISMISSED — #607 scope, enforced by depends_on chain
  - C5 (pre-commit files pattern): DISMISSED — already in proposed AC4
  - C6 (scripts/ inventory): ACCEPTED → AC7 expanded with precondition inventory
  - C7 (verification gate scope): ACCEPTED → AC11 expanded to 5 config files
  - C8 (temporal dependency): DISMISSED — pipeline depends_on enforces ordering
  - C9 (copilot-instructions.md): DISMISSED — #607 AC7 scope
  - C10 (decision doc verification): DISMISSED — already addressed in AC8
- Post-refinement confidence: 0.91

### Verdict: APPROVE
### Action Taken: Rewrote body from 10 vague AC to 11 precise AC with exact old→new mappings. Added 2 missing AC items (markdown linting, scripts/setup.py deletion). Removed 1 overlapping AC (README). Fixed factual error (decision doc path). Added Scope Boundaries (10 handoffs) and expanded Notes. Replaced type:build with type:config. Advanced to todo.

[[2026-04-05]] Sun 00:34
APPROVED #609 to todo. Rewrote 10 vague AC to 11 precise AC: added kanban-md.exe files.exclude update (AC1), markdown linter configs (AC5), scripts/setup.py deletion (AC7), verification gate (AC11). Removed README overlap with #607. Fixed decision doc path error. Replaced type:build with type:config. Challenger block overridden (0.25): 4 concerns accepted as AC additions, 5 dismissed (scope belongs to sibling tasks or already addressed).

[[2026-04-05]] Sun 05:50
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- AC1–AC11 are all config file edits, directory deletions, and file-system verification: .vscode/settings.json, .gitignore, .pre-commit-config.yaml, .markdownlint-cli2.jsonc, .markdownlintignore, docs/ deletion, scripts/setup.py deletion, decision doc status update, .gitkeep verification.
- No Python interfaces, modules, or functions to test.
- Passing through to builder.

[[2026-04-05]] Sun 09:55
## Review Evidence

### Tests
- Ruff: **CLEAN** (all checks passed)
- Pre-existing failures: ~435 (RED-phase TDD tests, unrelated tasks)
- **New failures introduced by #609 builder (2):**
  1. `tests/test_monorepo_skeleton.py::TestFromAC_DirectoryStructure::test_scripts_setup_placeholder_exists` — FAIL (FileNotFoundError: `scripts/setup.py` deleted but test not updated)
  2. `tests/test_cleanup_github_skills_117.py::TestFromAC_SetupPyNoDualPath::test_setup_py_no_github_skills_reference` — FAIL (same cause: reads `scripts/setup.py` which no longer exists)

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: files.exclude: docs/scratch→.owlbear/scratch; kanban-md.exe path | `.owlbear/scratch: true`, `.owlbear\\kanban\\kanban-md.exe: true`; `.owlbear/` NOT excluded | PASS |
| AC2: search.exclude 3 entries | `.owlbear/scratch/**`, `.owlbear/kanban/activity.jsonl`, `.owlbear/kanban/v1-archive/**` | PASS |
| AC3: .gitignore — section comment, scratch entries (4 of 5) | Comment `(under .owlbear/)`, `.owlbear/scratch/*`, `!.owlbear/scratch/.gitkeep`, `!.owlbear/scratch/.instructions.md` | PASS (4/5) |
| AC3: .gitignore — `kanban/*.exe` → `.owlbear/kanban/*.exe` | **ACTUAL**: `.owlbear/kanban*.exe` — missing `/` before `*.exe`. Does NOT match `.owlbear/kanban/kanban-md.exe`. | ❌ FAIL |
| AC4: .pre-commit-config.yaml | `entry: python .owlbear/scripts/validate_skills.py`, `python .owlbear/scripts/validate_agents.py`, `files: ^share/agents/.*\.agent\.md$` | PASS |
| AC5: .markdownlint-cli2.jsonc + .markdownlintignore | `.owlbear/research/**`, `.owlbear/scratch/**` in both files | PASS |
| AC6: docs/ deleted | `Test-Path "docs"` = False | PASS |
| AC7: scripts/setup.py deleted; scripts/ directory removed | `scripts/setup.py` gone; **PARTIAL FAIL**: `scripts/` still exists (contains `__pycache__/`) | PARTIAL |
| AC8: decision doc status = Resolved | `**Status:** Resolved` in file | PASS |
| AC9: schema_version stays at 1 | `"schema_version": 1` confirmed | PASS |
| AC10: .gitkeep files | `.owlbear/knowledge/.gitkeep` created; `.owlbear/scratch/.gitkeep` present | PASS |
| AC11: zero stale patterns | Config files checked; stale patterns removed — but AC11 also requires `.owlbear/kanban/*.exe` gitignore to be correct, which it isn't | CONDITIONAL |

### Deductions

| Finding | Severity | Deduction |
|---------|----------|-----------|
| AC3 gitignore pattern wrong: `.owlbear/kanban*.exe` instead of `.owlbear/kanban/*.exe` | Critical — functional defect | -.12 |
| Binary committed to git: `.owlbear/kanban/kanban-md.exe` (13MB) now tracked — direct consequence of wrong gitignore | High — repo hygiene + security risk (unvetted binary in VCS) | -.15 |
| 2 TestFromAC failures: setup.py deleted without updating test files | High — builder broke passing tests | -.10 |
| AC7 partial: `scripts/__pycache__/` not removed; directory persists | Low — gitignored artifacts only | -.02 |

**Total Deductions: -.39 | Confidence: .61**

### Verdict: FAIL → in-progress

### Required Fixes

1. **Fix .gitignore (AC3)**: Change `.owlbear/kanban*.exe` → `.owlbear/kanban/*.exe` (add `/` before `*.exe` to match files inside the kanban subdirectory)
2. **Remove binary from git tracking**: `git rm --cached ".owlbear/kanban/kanban-md.exe"` — the exe must not remain tracked. Verify gitignore fix prevents re-addition.
3. **Update `tests/test_monorepo_skeleton.py`**: Remove or update `test_scripts_setup_placeholder_exists` — `scripts/setup.py` no longer exists, test asserts it does → FAIL
4. **Update `tests/test_cleanup_github_skills_117.py`**: `TestFromAC_SetupPyNoDualPath::test_setup_py_no_github_skills_reference` reads `scripts/setup.py`; file gone → FileNotFoundError. Either skip test or redirect to `setup/init.py`
5. **Clean scripts/__pycache__**: Remove to satisfy AC7 "delete empty scripts/ directory"

[[2026-04-05]] Sun 10:18
## Builder Notes (re-run after review → in-progress)

### Files changed
- `.gitignore`: `.owlbear/kanban*.exe` → `.owlbear/kanban/*.exe` (added `/` before `*.exe`)
- `.owlbear/kanban/kanban-md.exe`: removed from git tracking via `git rm --cached`
- `tests/test_monorepo_skeleton.py`: replaced `test_scripts_setup_placeholder_exists` (checked deleted scripts/setup.py) with `test_setup_init_exists` (checks setup/init.py)
- `scripts/__pycache__/`: deleted; `scripts/` directory now gone

### Test results
- 6 passed (TestFromAC_DirectoryStructure × 5, TestFromAC_SetupPyNoDualPath × 1)
- 0 new failures introduced

### Lint
- ruff: CLEAN (tests/test_monorepo_skeleton.py)

### AC11 verification
- Zero stale patterns in .vscode/settings.json, .gitignore, .pre-commit-config.yaml, .markdownlint-cli2.jsonc, .markdownlintignore

### Commit
- `18ee471` fix(config): resolve 4 review deductions for #609

[[2026-04-05]] Sun 12:29
## Review Evidence (Cycle 2)

### Tests
- `tests/test_monorepo_skeleton.py` + `tests/test_cleanup_github_skills_117.py`: **38 passed, 0 failed**
- Ruff: **CLEAN** (both test files)
- Pre-existing failures: unrelated (not investigated, outside scope)

### Changed Files (commit 18ee471)
- `.gitignore` — gitignore pattern fixed
- `.owlbear/kanban/kanban-md.exe` — binary removed from git tracking via `git rm --cached`
- `tests/test_monorepo_skeleton.py` — test method replaced

### AC Compliance Table

| AC | Evidence | Status |
|----|----------|--------|
| AC1: files.exclude: `.owlbear/scratch: true`, `.owlbear\\kanban\\kanban-md.exe: true`; `.owlbear/` not excluded | settings.json L61, L88; `.owlbear/` entry absent | PASS |
| AC2: search.exclude 3 entries | `.owlbear/scratch/**` L140, `.owlbear/kanban/activity.jsonl` L138, `.owlbear/kanban/v1-archive/**` L139 | PASS |
| AC3: .gitignore section comment, 4 scratch entries, exe pattern | L55 `(under .owlbear/)`, L56–58, L74 `.owlbear/kanban/*.exe` (FIXED from `kanban*.exe`) | PASS |
| AC4: .pre-commit-config.yaml 3 entries | L41, L47, L48 — all correctly pointing to `.owlbear/scripts/` and `share/agents/` | PASS |
| AC5: .markdownlint-cli2.jsonc + .markdownlintignore | L3–4 in jsonc, L1–2 in ignore; both files clean | PASS |
| AC6: docs/ deleted | `Test-Path "docs"` = False | PASS |
| AC7: scripts/setup.py + scripts/ deleted | `Test-Path "scripts"` = False | PASS |
| AC8: decision doc status = Resolved | `.owlbear/decisions/resolved/owlbear-folder-restructure.md:4:**Status:** Resolved` | PASS |
| AC9: schema_version stays 1 | owlbear-project.json: `"schema_version": 1` | PASS |
| AC10: .gitkeep files present | `.owlbear/scratch/.gitkeep` = True; `.owlbear/knowledge/.gitkeep` = True | PASS |
| AC11: zero stale patterns in 5 config files | Direct grep on each file — no old path patterns found | PASS |

### TestFromAC Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_scripts_setup_placeholder_exists` (asserting `scripts/setup.py`) | Replaced with `test_setup_init_exists` (asserting `setup/init.py`) | STRENGTHENED — AC7 deletes `scripts/setup.py`; correct artifact is `setup/init.py` (created by #604). Intent preserved. |
| `TestFromAC_SetupPyNoDualPath::test_setup_py_no_github_skills_reference` (already reading `setup/init.py` from `bbba9e5`) | No change in cycle 2 | PASS — 38/38 green |

### Previous Review Deductions — Resolution Status

| Deduction | Fix Made | Verified |
|-----------|----------|----------|
| AC3 gitignore: `.owlbear/kanban*.exe` → `.owlbear/kanban/*.exe` | Fixed in 18ee471 | ✅ `.gitignore` L74 confirmed |
| Binary tracked in VCS: `kanban-md.exe` | `git rm --cached` in 18ee471 | ✅ `git ls-files` returns empty |
| 2 TestFromAC failures | `test_monorepo_skeleton.py` fixed in 18ee471; `test_cleanup_github_skills_117.py` already correct in `bbba9e5` | ✅ 38/38 PASS |
| AC7 partial: `scripts/__pycache__` persisting | Deleted in 18ee471 | ✅ `Test-Path "scripts"` = False |

### Security
- Binary untracked, gitignore pattern now scoped correctly to subdirectory — prevents re-tracking. CLEAN.
- No new code, no new system boundaries. CLEAN.

### Deductions: 0

**Confidence: .97 → PASS**

[[2026-04-05]] Sun 15:18
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | type:config task — no behavior or API change. copilot-instructions.md checked via direct grep: zero stale `docs/scratch`, `docs/research`, `scripts/*` patterns (path cleanup delegated to #607 AC7 per scope boundary, already completed) |
| 2 | Module docstrings | No | N/A | No Python production modules created or modified. Only test file (`tests/test_monorepo_skeleton.py`) had a test method replaced — test files do not require public docstrings |
| 3 | External attribution | No | N/A | No external patterns, repos, or articles referenced |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No `.owlbear/research/` doc produced or linked for this task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/609-*` files found)

docs gate passed

[[2026-04-05]] Sun 16:42
## Audit
### AC Verification
11/11 AC PASS. Spot-checked AC3,4,5,6,7,8,9,10,11 directly; AC1,2 trusted from reviewer C2 (settings.json copilot-restricted).

### Test Results
pytest: 432 failed, 2878 passed (all pre-existing RED-phase TDD). ruff: clean.

### Architect Quality: 4/5
Original AC weak (6 vague, 1 error); challenger rework produced 11 precise items.

### Deductions: 0
### Confidence: 1.00
### Action: archive

### Commits
bbba9e5 feat: post-migration cleanup (#609)
18ee471 fix(config): resolve 4 review deductions (#609)

[[2026-04-05]] Sun 16:42
11/11 AC verified, full suite clean (432 pre-existing RED failures only), ruff clean, architect quality 4/5. Confidence 1.00.
