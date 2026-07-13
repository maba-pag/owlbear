---
id: 670
title: Create .cspell.json for project vocabulary
status: archived
priority: medium
created: 2026-04-06T22:22:52.1798651+02:00
updated: 2026-04-07T12:13:55.3882245+02:00
started: 2026-04-07T12:13:55.3882245+02:00
completed: 2026-04-07T12:13:55.3882245+02:00
tags:
    - scope:ci
    - type:config
parent: 672
class: standard
---

## Objective\nCreate a .cspell.json config with project-specific vocabulary so the cspell linter in MegaLinter produces meaningful results instead of noise.\n\n## Context\nMegaLinter config enables SPELL_CSPELL for .md, .py, .ps1 files. Without a custom dictionary, every project term (OwlBear, kanban, MCP, ruff, pyproject, frontmatter, etc.) will be flagged as a spelling error. The first run would be unusable.\n\n## Acceptance Criteria\n- [ ] .cspell.json created at repo root\n- [ ] Custom words list covers project vocabulary (OwlBear, kanban, MCP, ruff, pyproject, uv, frontmatter, megalinter, etc.)\n- [ ] Language set to en\n- [ ] Ignore patterns for generated/vendored paths (.venv, v1, __pycache__, .egg-info, uv.lock)\n- [ ] Validated: `npx cspell lint --config .cspell.json` runs without excessive false positives on a sample file\n\n## Files Affected\n- .cspell.json (new file)

[[2026-04-07]] Tue 10:56
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| .cspell.json created at repo root | Clear, testable | None |
| Custom words list covers project vocabulary (OwlBear, kanban, MCP, ruff, pyproject, uv, frontmatter, megalinter, etc.) | Acceptable — "etc." is pragmatic for a vocabulary list | Builder: scan codebase for project-specific terms; aim for 15+ entries |
| Language set to en | Clear | None |
| Ignore patterns for .venv, v1, __pycache__, .egg-info, uv.lock | Incomplete — missing paths from .mega-linter.yml FILTER_REGEX_EXCLUDE | **REFINED:** Also add .owlbear/kanban/v1-archive/ and .owlbear/scratch/ for parity |
| Validated: npx cspell lint runs without excessive false positives | Invalid — project has no Node.js/npm tooling; cspell runs inside MegaLinter Docker | **REFINED:** Replace with: ".cspell.json follows cspell schema (version 0.2, words array, ignorePaths array). No npx required — MegaLinter handles cspell execution." |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One config file (.cspell.json), one concern |
| Interface clarity | PASS | AC clear after refinements above |
| Dependency correctness | PASS | No dependencies; independent of sibling CI tasks |
| Module layering | PASS | N/A for config file |
| TDD compliance | PASS | Tagged type:config — non-impl pass-through |
| KISS/YAGNI | PASS | Minimal scope, addresses verified need |
| Premise challenge | PASS | SPELL_CSPELL already enabled in .mega-linter.yml line 22; line 77 comment confirms ".cspell.json for custom words" needed |
| Pattern consistency | PASS | Standard cspell configuration approach |
| Security surface | PASS | No security concerns with spell-check dictionary |
| Single domain | PASS | scope:ci only |

### Priority Promotion
Parent epic #672 arch review recommended promoting #670 from nice-to-have to needed. Confirmed: SPELL_CSPELL is active now, first MegaLinter run will flag every project term without this dictionary. Builder or orchestrator should promote priority.

### Codebase Evidence
- .mega-linter.yml line 22: SPELL_CSPELL enabled
- .mega-linter.yml line 77: comment "will need .cspell.json for custom words"
- .mega-linter.yml line 78: SPELL_CSPELL_FILTER_REGEX_INCLUDE restricts to .md, .py, .ps1
- .mega-linter.yml lines 34-41: FILTER_REGEX_EXCLUDE includes .owlbear/kanban/v1-archive/, .owlbear/scratch/, .venv/, v1/, __pycache__/, .egg-info/, uv.lock
- No existing .cspell.json or cspell config anywhere in repo

### Challenge Results
- Challenger: reconsider (confidence 0.75)
- Findings: (1) AC5 npx validation unrealistic without Node.js tooling, (2) AC4 missing two ignore paths
- Architect response: accepted both findings, documented refined AC above. Core task design is sound; refinements are minor corrections.

### Builder Guidance
- Follow refined AC (see AC Assessment table above)
- Use cspell schema version "0.2"
- Scan the full codebase for project-specific terms beyond the examples in AC2
- ignorePaths should cover: .venv, v1, __pycache__, .egg-info, uv.lock, .owlbear/kanban/v1-archive, .owlbear/scratch
- No npx validation needed — verify .cspell.json is valid JSON with correct schema structure

### Verdict: APPROVE
### Action Taken: Advanced to todo with AC refinements documented for builder. Priority promotion to needed recommended.

[[2026-04-07]] Tue 11:25
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- Task creates a .cspell.json config file (JSON, no Python interfaces).
- AC references only a JSON config file — no `implement`, `function`, `class`, `src/`, or `.py` keywords found.
- Passing through to builder.

[[2026-04-07]] Tue 11:31
## Builder Notes

### Files Changed
- `.cspell.json` (new file, repo root)

### Implementation
- Created `.cspell.json` with cspell schema `version: "0.2"`, `language: "en"`
- **74 custom words** covering project vocabulary: owlbear, kanban, mcp, fastmcp, ruff, pyproject, uv, frontmatter, megalinter, cspell, pydantic, orchestrator, ideator, planner, subagent(s), asyncio, asynccontextmanager, typeddict, basemodel, dataclass, docstring, tdd, conftest, noqa, xdist, yaml-related (yamllint, pyyaml, strictyaml), pathlib, importlib, serializable, deduplicate, dispatchable, and others
- **8 ignore paths**: `.venv/**`, `v1/**`, `__pycache__/**`, `**/*.egg-info/**`, `uv.lock`, `.owlbear/kanban/v1-archive/**`, `.owlbear/scratch/**`, `node_modules/**`
- ignorePaths parity with `.mega-linter.yml` FILTER_REGEX_EXCLUDE (lines 34-41) as directed by arch review

### AC Verification
- [x] `.cspell.json` created at repo root — confirmed
- [x] Custom words list ≥ 15 entries — 74 words total
- [x] Language set to `en` — confirmed
- [x] Ignore patterns cover all required paths (`.venv`, `v1`, `__pycache__`, `.egg-info`, `uv.lock`, `.owlbear/kanban/v1-archive`, `.owlbear/scratch`) — confirmed
- [x] Valid JSON with correct cspell schema structure — `ConvertFrom-Json` parsed successfully; version=0.2, language=en, wordCount=74, ignoreCount=8

### Test Results
- Non-implementation task (type:config) — no pytest tests applicable
- No ruff lint targets (JSON file only)

### Notes
- No npx validation needed per arch refinement — cspell runs inside MegaLinter Docker
- Vocabulary scanned from README.md, pyproject.toml, system instructions, pipeline-protocol skill, and conftest

[[2026-04-07]] Tue 11:54
## Review Evidence

### Test Results
- pytest: N/A — type:config task, no Python implementation, no tests applicable
- ruff: N/A — JSON file only, no Python sources to lint

### Coverage: N/A

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
- SKIP — No TestFromAC_* classes exist (type:config pass-through confirmed by test-writer notes)

#### Security Review
- No issues — read-only JSON vocabulary list; no secrets, no injection surface, no deserialization, no dependencies added

#### Test Integrity
- SKIP — No TestFromAC_* classes

#### Test Quality
- SKIP — No Python implementation; type:config task

#### Data Safety
- No issues — static config file, no runtime data handling

#### Implementation-Aware Gaps
- N/A — pure config, no code paths

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- None

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| .cspell.json at repo root | file_search confirms .cspell.json at c:\...\owlbear\.cspell.json | N/A | PASS |
| Custom words ≥ 15, project vocab | 74 words in words array: owlbear, kanban, mcp, ruff, pyproject, uv, frontmatter, megalinter, fastmcp, pydantic, etc. | N/A | PASS |
| Language set to en | .cspell.json line 3: "language": "en" | N/A | PASS |
| ignorePaths cover .venv, v1, __pycache__, .egg-info, uv.lock, .owlbear/kanban/v1-archive, .owlbear/scratch (refined AC) | ignorePaths array: .venv/**, v1/**, __pycache__/**, **/*.egg-info/**, uv.lock, .owlbear/kanban/v1-archive/**, .owlbear/scratch/** — all 7 required paths present (+ bonus node_modules/**) | N/A | PASS |
| cspell schema: version 0.2, words array, ignorePaths array | .cspell.json line 2: "version": "0.2"; words array lines 4–79; ignorePaths array lines 80–89 | N/A | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-07]] Tue 11:58
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Pure CI spell-check config file; no OwlBear system behavior or API changed. copilot-instructions.md main-branch contents reflect the current sync-to-main include list — .cspell.json is intentionally not in that list yet; bootstrap to main is handled by sibling task #671 |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | Standard cspell JSON schema v0.2; widely documented tool config, no novel external patterns used |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No .owlbear/research/ doc produced; task had no research phase |

### Files Updated
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/670-* files found)

[[2026-04-07]] Tue 12:13
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| .cspell.json created at repo root | File confirmed at .cspell.json (90 lines, valid JSON) | PASS |
| Custom words list covers project vocabulary (15+ entries) | 74 words: owlbear, kanban, mcp, ruff, pyproject, uv, frontmatter, megalinter, fastmcp, pydantic, etc. | PASS |
| Language set to en | .cspell.json line 2: "language": "en" | PASS |
| Ignore patterns for .venv, v1, __pycache__, .egg-info, uv.lock, .owlbear/kanban/v1-archive, .owlbear/scratch | ignorePaths array: all 7 required paths present plus bonus node_modules/** (8 total) | PASS |
| Follows cspell schema (version 0.2, words array, ignorePaths array) | version: "0.2", words array (74 entries), ignorePaths array (8 entries), valid JSON | PASS |

### Test Results
- pytest: 3968 passed, 436 failed (all pre-existing, none related to .cspell.json), 19 skipped
- ruff: 5 pre-existing warnings (PLR0915, RUF059, SIM117), none related to this task
- No Python code in this task (type:config, JSON file only)

### Reviewer Evidence
Present and detailed. PASS verdict at .97 confidence. Full AC compliance table with file-level evidence. Trusted.

### Architect Quality: 4/5
AC was mostly specific. Architect caught npx validation was unrealistic (no Node.js tooling) and refined to schema validation. Also expanded ignore paths for parity with .mega-linter.yml. Minor gap: original AC5 required npx which was infeasible. Corrected during arch review.

### Deduction Breakdown
- Start: 1.00
- AC lines (5/5 with evidence): no deduction
- Lint violations: 0 (no Python targets)
- AC quality 4/5: no deduction (threshold is 3 or below)
- Reviewer evidence present and detailed: no deduction
- Full-suite failures in task scope: 0 (436 failures all pre-existing)
- Note: builder left .cspell.json uncommitted (untracked). Committed as leftover per Step 4.

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0eb6023 | feat(ci) | .cspell.json | #670 |
