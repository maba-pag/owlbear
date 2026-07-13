---
id: 741
title: Delete v1/ directory and v1-archive kanban tasks
status: archived
priority: medium
created: '2026-04-10T04:29:46.8972445+02:00'
updated: '2026-04-10T07:34:39.278162+00:00'
tags:
- cleanup
- v1-analysis
parent: null
depends_on:
- 735
- 736
- 737
- 738
- 739
- 740
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
class: standard
---

## Objective

Delete the v1/ directory and .owlbear/kanban/v1-archive/ after all v1-derived tasks are completed or triaged. The v1 feature inventory at .owlbear/research/v1-feature-inventory.md preserves all feature knowledge.

## Context

v1 was the PydanticAI-based standalone daemon architecture. v2 is the VS Code Copilot Chat + MCP architecture. A full feature analysis was performed (2026-04-10) cataloging 164 features across 18 domains. The report is at .owlbear/research/v1-feature-inventory.md. Two ideation briefs were created for larger ideas (.owlbear/briefs/draft-browser-knowledge-extraction/ and .owlbear/briefs/draft-voice-interaction-rethink/).

## What to delete

- v1/ — entire directory (v1 source code, tests, docs, .owlbear/, .venv/, etc.)
- .owlbear/kanban/v1-archive/ — 999 archived v1 kanban tasks

## What to keep

- .owlbear/research/v1-feature-inventory.md — the comprehensive feature catalog
- .owlbear/briefs/draft-browser-knowledge-extraction/ — ideation brief
- .owlbear/briefs/draft-voice-interaction-rethink/ — ideation brief
- Tasks #735-740 — v1-derived work items

## Acceptance Criteria

- [ ] v1/ directory deleted
- [ ] .owlbear/kanban/v1-archive/ deleted
- [ ] .owlbear/research/v1-feature-inventory.md still exists and is accessible
- [ ] Git commit with clear message about v1 removal
- [ ] No references to v1/ paths remain in active configuration files

[[2026-04-10]]

## Architecture Review

### Scope Refinement

**CRITICAL:** Do NOT delete `.owlbear/kanban/v1-archive/`. The kanban engine actively uses this directory — `_ARCHIVE_DIR_NAME = "v1-archive"` in `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py:37`. It contains 1016 archived tasks, 317 of which are v2-era (ID ≥ 700). Deleting it would destroy v2 archive history and break `list_tasks(archived=True)`. A separate task #744 handles renaming `v1-archive` → `archive`.

**Original AC2 overridden:** "`.owlbear/kanban/v1-archive/` deleted" → replaced by refined AC below.

### Refined Acceptance Criteria

- [ ] `v1/` directory deleted (`rm -rf v1/`)
- [ ] `.owlbear/research/v1-feature-inventory.md` still exists and accessible
- [ ] v1/ references removed from active config files:
  - `pyproject.toml`: lines 27 (`norecursedirs = ["v1"]`) and 39 (`exclude = ["v1/"]`)
  - `.gitignore`: lines 79-85 (v1 build artifacts section)
  - `.mega-linter.yml`: line 31 (`v1/` in FILTER_REGEX_EXCLUDE), lines 47-50 (ruff v1/ exclude)
  - `.vscode/settings.json`: lines 83 (`v1/.venv`), 138-139 (`v1/.venv`, `v1/**`)
  - `.cspell.json`: line 82 (`v1/**`)
  - `.github/copilot-instructions.md`: line 11 (remove `v1/` from dev branch contents)
- [ ] Do NOT touch `.owlbear/kanban/v1-archive/` — leave for #744
- [ ] Do NOT touch `.owlbear/sources/overview.md` v1 references — those are historical source tracking
- [ ] Git commit with message: `chore: delete v1/ directory and clean v1/ config references #741`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Refined to v1/ directory deletion + config cleanup only |
| Interface clarity | PASS | Inputs/outputs clear: delete directory, edit config files |
| Dependency correctness | PASS | All 6 deps (#735-740) confirmed done |
| Module layering | N/A | No module changes |
| TDD compliance | N/A | type:config — no testable Python code |
| KISS/YAGNI | PASS | Minimal scope after refinement |
| Premise challenge | PASS | v1/ directory is dead code; deletion is warranted |
| Pattern consistency | PASS | Mirrors #740 cleanup pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cleanup/config domain only |

### Challenge Results

- Challenger: FALLBACK — no challenger agent available in current tool set
- Architect response: N/A — straightforward deletion task with no design decisions

### Non-impl tagging

Task requires `type:config` pass-through tag — no testable Python code produced.

### Verdict: APPROVE (refined scope)

### Action Taken: Refined AC to exclude v1-archive deletion (moved to #744). Narrowed to v1/ directory + config reference cleanup. Advanced to todo

[[2026-04-10]]

## Test-Writer Notes

- Non-implementation task (tagged type:config) — no tests applicable.
- AC covers: `rm -rf v1/`, config file edits (pyproject.toml, .gitignore, .mega-linter.yml, .vscode/settings.json, .cspell.json, .github/copilot-instructions.md), and a git commit. No testable Python interfaces produced.
- Passing through to builder.
[[2026-04-10]]

## Builder Notes

### Files Changed

- `v1/` — entire directory deleted (source, tests, docs, .venv, .owlbear/, etc.)
- `pyproject.toml` — removed `norecursedirs = ["v1"]` and `exclude = ["v1/"]`
- `.gitignore` — removed v1 build artifacts section (v1/.venv/, v1/.pytest_cache/, etc.)
- `.mega-linter.yml` — removed `v1/` from FILTER_REGEX_EXCLUDE regex, removed `- v1` from ADDITIONAL_EXCLUDED_DIRECTORIES, removed `PYTHON_RUFF_ARGUMENTS: "--extend-exclude v1/"` and its obsolete comment
- `.vscode/settings.json` — removed `"v1/.venv": true` from files.exclude, removed `"v1/.venv": true` and `"v1/**": true` from search.exclude
- `.cspell.json` — removed `"v1/**"` from ignorePaths
- `.github/copilot-instructions.md` — removed `v1/` from dev branch contents table

### Verification

- `Test-Path v1/` → False (directory gone)
- `grep v1/ pyproject.toml` → no matches
- `grep v1/ .mega-linter.yml` → no matches
- `.owlbear/research/v1-feature-inventory.md` — confirmed untouched
- `.owlbear/kanban/v1-archive/` — confirmed untouched (left for #744)

### Commit

`62dbbb3` — `chore: delete v1/ directory and clean v1/ config references #741`

### AC Evidence

- [x] `v1/` directory deleted
- [x] `.owlbear/research/v1-feature-inventory.md` still exists
- [x] v1/ references removed from all 6 config files
- [x] `.owlbear/kanban/v1-archive/` untouched
- [x] `.owlbear/sources/overview.md` untouched
- [x] Git commit with required message

### Type: config (no Python tests — pass-through)

[[2026-04-10]]

## Review Evidence

### Type

`type:config` — no tests, lint, or coverage to run. Direct filesystem + file inspection review.

### Changed Files (Reconstructed from builder notes)

- `v1/` — deleted
- `pyproject.toml` — v1 entries removed
- `.gitignore` — v1 section removed
- `.mega-linter.yml` — partial v1 cleanup
- `.vscode/settings.json` — v1/.venv and v1/** removed
- `.cspell.json` — `"v1/**"` removed
- `.github/copilot-instructions.md` — v1/ table row removed

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| `v1/` directory deleted | `file_search("v1/**")` → no results | PASS |
| `.owlbear/research/v1-feature-inventory.md` still exists | `file_search` → 1 result confirmed | PASS |
| `.owlbear/kanban/v1-archive/` untouched | `list_dir(.owlbear/kanban/)` → `v1-archive/` present | PASS |
| `pyproject.toml` — v1 references removed | `grep "v1" pyproject.toml` → no matches | PASS |
| `.gitignore` — v1 section removed | No v1 matches found (search-excluded; builder verification accepted) | PASS |
| `.mega-linter.yml` lines 31, 47-50 cleaned | grep confirms no v1 in ruff config or FILTER_REGEX_EXCLUDE | PASS |
| `.mega-linter.yml` line 77 — TRIVY_ARGUMENTS | `grep` found `--skip-dirs v1` at line 77 | **VIOLATION** |
| `.vscode/settings.json` — v1/.venv, v1/** removed | grep finds only `.owlbear/kanban/v1-archive/**` (appropriate) | PASS |
| `.cspell.json` — `"v1/**"` removed | grep finds only `.owlbear/kanban/v1-archive/**` (appropriate) | PASS |
| `.github/copilot-instructions.md` — v1/ removed | grep → no v1 references remain | PASS |
| Git commit with required message | Builder reports `62dbbb3` | ACCEPTED |

### Violation Detail

**File:** `.mega-linter.yml` line 77
**Content:** `REPOSITORY_TRIVY_ARGUMENTS: "--scanners vuln,misconfig --skip-dirs .venv --skip-dirs v1"`
**AC violated:** "No references to v1/ paths remain in active configuration files"
**Impact:** Functionally harmless (Trivy skips a non-existent dir), but the AC is unambiguous.
**Fix:** Change line 77 to: `REPOSITORY_TRIVY_ARGUMENTS: "--scanners vuln,misconfig --skip-dirs .venv"`

### Security

No concerns. Config-only changes, no new code surfaces, no credentials.

### Deductions

- -0.14 — one AC miss: `--skip-dirs v1` not removed from TRIVY_ARGUMENTS in `.mega-linter.yml:77`

### Verdict

Confidence: **.76** → FAIL (threshold .90)

### Action

Move to in-progress. Single-line fix in `.mega-linter.yml` line 77, then re-commit and re-submit.
[[2026-04-10]]

## Builder Notes (Follow-up)

### Fix Applied

- `.mega-linter.yml` line 77: removed `--skip-dirs v1` from `REPOSITORY_TRIVY_ARGUMENTS`
  - Before: `"--scanners vuln,misconfig --skip-dirs .venv --skip-dirs v1"`
  - After: `"--scanners vuln,misconfig --skip-dirs .venv"`

### Verification

- `grep TRIVY .mega-linter.yml` → `"--scanners vuln,misconfig --skip-dirs .venv"` — no v1 reference
- All original AC items from prior builder pass remain verified

### Commit

`90dcab8` — `chore: remove --skip-dirs v1 from Trivy arguments #741`

### AC Evidence (full)

- [x] `v1/` directory deleted
- [x] `.owlbear/research/v1-feature-inventory.md` still exists
- [x] v1/ references removed from all config files (including TRIVY_ARGUMENTS)
- [x] `.owlbear/kanban/v1-archive/` untouched
- [x] Git commits with required messages

### Type: config (no Python tests — pass-through)

[[2026-04-10]]

## Review Evidence

### Type

`type:config` — no tests, lint, or coverage to run. Direct filesystem + file inspection review.
Review cycle: 2 (follow-up after cycle-1 FAIL on `.mega-linter.yml:77`).

### Changed Files Verified

- `v1/` — deleted (confirmed: `file_search("v1/**")` → 0 results)
- `pyproject.toml` — `norecursedirs` and ruff `exclude` entries removed (grep → no matches)
- `.gitignore` — v1 section removed (grep → no matches)
- `.mega-linter.yml` — FILTER_REGEX_EXCLUDE, ADDITIONAL_EXCLUDED_DIRECTORIES, RUFF_ARGUMENTS and TRIVY_ARGUMENTS all clean
- `.vscode/settings.json` — only `.owlbear/kanban/v1-archive/**` remains (legitimate v2 kanban ref)
- `.cspell.json` — only `.owlbear/kanban/v1-archive/**` remains
- `.github/copilot-instructions.md` — no v1 references

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| `v1/` directory deleted | `file_search("v1/**")` → 0 results | PASS |
| `.owlbear/research/v1-feature-inventory.md` exists | `file_search` → 1 result | PASS |
| `.owlbear/kanban/v1-archive/` untouched | `list_dir(.owlbear/kanban/)` → `v1-archive/` present | PASS |
| `pyproject.toml` v1 entries removed | `norecursedirs` → no match; `exclude` → no match | PASS |
| `.mega-linter.yml` FILTER_REGEX_EXCLUDE clean | Line 31: no standalone `v1` path | PASS |
| `.mega-linter.yml` ADDITIONAL_EXCLUDED_DIRECTORIES clean | `v1` entry absent | PASS |
| `.mega-linter.yml:77` TRIVY `--skip-dirs v1` removed | Line 77: `"--scanners vuln,misconfig --skip-dirs .venv"` | PASS (cycle-1 fix confirmed) |
| `.vscode/settings.json` v1 entries removed | `v1/` references gone; only kanban `v1-archive` ref remains | PASS |
| `.cspell.json` `v1/**` removed | Only `.owlbear/kanban/v1-archive/**` remains | PASS |
| `.github/copilot-instructions.md` v1/ removed | grep → no matches | PASS |
| Git commit with required message | `62dbbb3` + `90dcab8` (TRIVY fix) | ACCEPTED |

### Security

No concerns. Config-only changes. No new code surfaces, no credentials, no injection paths.

### Deductions

0 — cycle-1 violation resolved. No new issues found.

### Verdict

Confidence: .97 → PASS
[[2026-04-10]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | Verified | `.github/copilot-instructions.md` dev branch table updated by builder — v1/ removed; current file confirmed accurate (no v1/ entry) |
| 2 | Module docstrings | No | N/A | `type:config` task — no Python modules created or modified |
| 3 | External attribution | No | N/A | Cleanup/deletion task — no external patterns used |
| 4 | CLI changes | No | N/A | No CLI modifications |
| 5 | Research doc | Yes | Verified | `.owlbear/research/v1-feature-inventory.md` confirmed present; linked in task body; follow-up task #744 created for v1-archive rename |

### Files Updated

None — builder already updated `.github/copilot-instructions.md` as part of the task. Doc-writer verified it is accurate.

### Scratch Files Cleaned

None — no `.owlbear/scratch/741-*` files found.

### Commit

No doc-writer commit needed. Builder commits `62dbbb3` and `90dcab8` cover all changes.
[[2026-04-10]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `v1/` directory deleted | `file_search("v1/**")` → 0 results | PASS |
| `.owlbear/research/v1-feature-inventory.md` exists | file_search → 1 result confirmed | PASS |
| v1/ references removed from config files | grep pyproject.toml, .mega-linter.yml, .github/copilot-instructions.md → no v1 matches | PASS |
| `.owlbear/kanban/v1-archive/` untouched | list_dir → `v1-archive/` present | PASS |
| Git commits with required messages | `62dbbb3` + `90dcab8` confirmed via git log | PASS |

### Test Results

- pytest: 3111 passed, 280 failed, 2 errors, 18 skipped — all failures pre-existing, none mention v1 or relate to config files changed. Task is type:config with no Python code changes.
- ruff: All checks passed (0 violations)

### Architect Quality: 4/5

Original AC included deleting v1-archive which would have broken kanban engine — architect caught this and refined scope (excellent). Refined AC was specific with exact files and lines. One gap: missed TRIVY_ARGUMENTS line 77 in .mega-linter.yml (caught by reviewer cycle 1). Minor gap filled by pipeline.

### Deduction Breakdown

- No AC lines without evidence: 0
- No lint violations: 0
- AC quality 4/5 (above threshold): 0
- Reviewer evidence present and detailed (cycle 2 PASS .97): 0
- No task-scope test failures: 0

### Confidence: .98

### Action: archive
