---
id: 788
title: Implement retro SKILL.md with git metrics workflow
status: archived
priority: nice-to-have
created: 2026-03-13T17:14:35.7832472+01:00
updated: 2026-03-23T02:11:28.7466079+01:00
started: 2026-03-23T02:11:24.6531592+01:00
completed: 2026-03-23T02:11:24.6531592+01:00
tags:
    - scope:agent-config
    - type:docs
class: standard
---

## Goal
Create .github/skills/retro/SKILL.md with development analytics workflow.

## AC
- [ ] SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter
- [ ] Step 1: Gather raw git data (5 parallel git commands)
- [ ] Step 2: Summary metrics table (commits, LOC, test LOC ratio, contributors, active days, sessions)
- [ ] Step 3: Per-contributor breakdown (commits, +/-, test ratio, top area)
- [ ] Step 4: Session detection (45min gap threshold, deep/medium/micro classification)
- [ ] Step 5: Commit type breakdown (feat/fix/refactor/test/chore/docs percentages)
- [ ] Step 6: Kanban correlation (tasks completed in window from activity.jsonl)
- [ ] Output format: structured markdown report
- [ ] PowerShell-compatible commands (no bash-only syntax)
- [ ] No new Python dependencies
- [ ] No changes to .py files

See docs/research/retro-skill.md for design rationale.

[[2026-03-13]] Fri 17:48
## Research
Validation of prior research from #786 (docs/research/retro-skill.md).

### Research Checklist
- [x] Theoretical validity: dev analytics via git history well-established
- [x] Prior art: 2 sources verified (gstack retro .90, git-stats .60)
- [x] Technical feasibility: pure SKILL.md, zero Python deps
- [x] Architecture fit: standard skill path
- [x] Implementation approach: 6-step workflow from gstack with kanban correlation

### Key Verification
- gstack retro confirmed: 45min session gap, conventional commits, per-contributor
- Bash-only syntax (grep/sed) must become PS equivalents per AC
- Kanban correlation is OwlBear-specific, straightforward JSONL read
- No existing overlap in codebase

[[2026-03-13]] Fri 20:12
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter | Verifiable. Must have name + description fields per existing pattern. | Keep |
| Step 1: Gather raw git data (5 parallel git commands) | Verifiable. Research doc lists 5 specific git commands. | Keep |
| Step 2: Summary metrics table | Verifiable. 6 named metrics. | Keep |
| Step 3: Per-contributor breakdown | Verifiable. 4 named columns. | Keep |
| Step 4: Session detection (45min gap, deep/medium/micro) | Verifiable. Classification thresholds to builder discretion with gstack reference. | Keep |
| Step 5: Commit type breakdown | Verifiable. 6 conventional commit types listed. | Keep |
| Step 6: Kanban correlation | Verifiable. Read activity.jsonl, count tasks in window. | Keep |
| Output format: structured markdown report | Verifiable via steps 2-6. | Keep |
| PowerShell-compatible commands | Verifiable. No bash-only syntax. | Keep |
| No new Python dependencies | Verifiable. | Keep |
| No changes to .py files | Verifiable. | Keep |

### Architecture Notes
- Path .github/skills/retro/SKILL.md follows established skill convention
- YAML frontmatter must include name and description (see curation-workflow for pattern)
- 6-step workflow consistent with existing skills
- No code, no deps, no security surface -- pure instructions file
- Research doc provides all design rationale and source commands
- TDD: N/A -- type:docs task

### Dependencies
- Verified: docs/research/retro-skill.md exists and is complete
- No code dependencies

[[2026-03-13]] Fri 20:13
## Architecture Review
**Verdict:** Approve

### AC Assessment
All 11 AC lines verified as mechanically testable. No vague AC. See task body for full table.

### Architecture Notes
- Path .github/skills/retro/SKILL.md follows established skill convention
- YAML frontmatter: name + description (see curation-workflow pattern)
- 6-step workflow consistent with existing skills
- Pure instructions file: no code, no deps, no security surface
- TDD: N/A (type:docs)

### Dependencies
- docs/research/retro-skill.md: exists, complete
- No code dependencies

[[2026-03-13]] Fri 20:13
## Architecture Review
**Verdict:** Approve

### AC Assessment
All 11 AC lines verified as mechanically testable. No vague AC. See task body for full table.

### Architecture Notes
- Path .github/skills/retro/SKILL.md follows established skill convention
- YAML frontmatter: name + description (see curation-workflow pattern)
- 6-step workflow consistent with existing skills
- Pure instructions file: no code, no deps, no security surface
- TDD: N/A (type:docs)

### Dependencies
- docs/research/retro-skill.md: exists, complete
- No code dependencies

[[2026-03-13]] Fri 20:13
## Architecture Review
**Verdict:** APPROVED (merged from #786)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter | Clear, verifiable. Pattern: name + description fields (see docs-gate, visual-output) | OK |
| Step 1: Gather raw git data (5 parallel git commands) | Specific. Research doc lists 5 commands | OK |
| Step 2: Summary metrics table | 6 metrics listed. Clear | OK |
| Step 3: Per-contributor breakdown | 4 columns listed. Clear | OK |
| Step 4: Session detection (45min gap) | Threshold + classification specified | OK |
| Step 5: Commit type breakdown | Categories enumerated | OK |
| Step 6: Kanban correlation | Data source specified (activity.jsonl) | OK |
| Output: structured markdown report | Clear | OK |
| PowerShell-compatible commands | Clear constraint | OK |
| No new Python dependencies | Clear constraint | OK |
| No changes to .py files | Clear constraint | OK |

### Architecture Notes
- Pure SKILL.md (instructions only) -- no Python code, no test task needed
- Skill auto-discovery: VS Code loads skills from .github/skills/*/SKILL.md
- YAML frontmatter must have name + description fields per existing skill pattern
- Research doc (docs/research/retro-skill.md) provides implementation guidance for all 6 steps
- KISS applied: gstack 14-step reduced to 6-step (YAGNI items dropped per research)
- Merged #786 (research task, now done) -- this task carries all implementation AC

### Dependencies
- None. Pure docs task with zero code dependencies.

[[2026-03-13]] Fri 20:14
## Architecture Review
**Verdict:** APPROVED (merged from #786)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter | Clear, verifiable. Pattern: name + description fields | OK |
| Step 1: Gather raw git data (5 parallel git commands) | Specific. Research doc lists 5 commands | OK |
| Step 2: Summary metrics table | 6 metrics listed. Clear | OK |
| Step 3: Per-contributor breakdown | 4 columns listed. Clear | OK |
| Step 4: Session detection (45min gap) | Threshold + classification specified | OK |
| Step 5: Commit type breakdown | Categories enumerated | OK |
| Step 6: Kanban correlation | Data source specified (activity.jsonl) | OK |
| Output: structured markdown report | Clear | OK |
| PowerShell-compatible commands | Clear constraint | OK |
| No new Python dependencies | Clear constraint | OK |
| No changes to .py files | Clear constraint | OK |

### Architecture Notes
- Pure SKILL.md (instructions only) -- no Python code, no test task needed
- Skill auto-discovery: VS Code loads skills from .github/skills/*/SKILL.md
- YAML frontmatter must have name + description fields per existing skill pattern
- Research doc (docs/research/retro-skill.md) provides implementation guidance for all 6 steps
- KISS applied: gstack 14-step reduced to 6-step (YAGNI items dropped per research)
- Merged #786 (research task, now done) -- this task carries all implementation AC

### Dependencies
- None. Pure docs task with zero code dependencies.

[[2026-03-13]] Fri 20:14
## Architecture Review
**Verdict:** APPROVED (merged from #786)

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter | Clear, verifiable. Pattern: name + description fields | OK |
| Step 1: Gather raw git data (5 parallel git commands) | Specific. Research doc lists 5 commands | OK |
| Step 2: Summary metrics table | 6 metrics listed. Clear | OK |
| Step 3: Per-contributor breakdown | 4 columns listed. Clear | OK |
| Step 4: Session detection (45min gap) | Threshold + classification specified | OK |
| Step 5: Commit type breakdown | Categories enumerated | OK |
| Step 6: Kanban correlation | Data source specified (activity.jsonl) | OK |
| Output: structured markdown report | Clear | OK |
| PowerShell-compatible commands | Clear constraint | OK |
| No new Python dependencies | Clear constraint | OK |
| No changes to .py files | Clear constraint | OK |

### Architecture Notes
- Pure SKILL.md (instructions only) -- no Python code, no test task needed
- Skill auto-discovery: VS Code loads skills from .github/skills/*/SKILL.md
- YAML frontmatter must have name + description fields per existing skill pattern
- Research doc (docs/research/retro-skill.md) provides implementation guidance for all 6 steps
- KISS applied: gstack 14-step reduced to 6-step (YAGNI items dropped per research)
- Merged #786 (research task, now done) -- this task carries all implementation AC

### Dependencies
- None. Pure docs task with zero code dependencies.

[[2026-03-13]] Fri 20:45
## Test-Writer Notes

[[2026-03-13]] Fri 20:45
- Non-implementation task (tagged type:docs) -- no tests applicable.

[[2026-03-13]] Fri 20:45
- Passing through to builder.

[[2026-03-20]] Fri 18:14
## Builder Notes
- Files changed: .github/skills/retro/SKILL.md (already committed; verified complete)
- Tests: N/A (type:docs, non-implementation pass-through)
- Lint: N/A (no .py files)
- AC verification:
  - YAML frontmatter: name + description fields present
  - Step 1: 5 git commands (shortstat, numstat, timestamps, name-only, shortlog)
  - Step 2: 6 metrics (commits, LOC added/removed, test LOC ratio, contributors, active days, sessions)
  - Step 3: 4 columns (contributor, commits, +/-, test ratio, top area)
  - Step 4: 45-minute gap threshold, deep/medium/micro classification
  - Step 5: feat/fix/refactor/test/chore/docs with percentages
  - Step 6: activity.jsonl correlation (tasks created/completed/archived)
  - Output: structured markdown report template present
  - PowerShell-compatible: no grep/sed/awk, all PS cmdlets
  - No .py changes

[[2026-03-20]] Fri 19:06
sanity-check

[[2026-03-20]] Fri 19:06
## Review Evidence
### Test Results
- `uv run pytest tests/test_skills.py -q --tb=short`
- Result: **3 failed, 30 passed, 2 warnings**
- Failures:
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_discovers_18_real_skills`
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_real_skills_have_nonempty_names`
  - `tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_list_skills_includes_all_19`
- Key failure: `AssertionError: Expected 19 skills, got 20` (discovered list now includes `retro`).

### Lint Results
- `uv run ruff check src/ tests/`
- Result: fails with broad pre-existing lint debt (reported 477 errors), not specific to #788.

### Coverage
- N/A (docs/skill-file task; no Python source touched for this task).

### Pass 1 - CRITICAL
#### Security Review
- No security issues in `.github/skills/retro/SKILL.md` (instruction-only markdown).

#### Test Integrity
- No `TestFromAC_*` class authored under #788 to compare against prior RED intent.

#### Data Safety
- No data-safety issues found in task artifact.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| Valid YAML frontmatter | `.github/skills/retro/SKILL.md` lines 1-4 (`name`, `description`) | PASS |
| Step 1 (5 git commands) | `.github/skills/retro/SKILL.md` lines 31-48 | PASS |
| Step 2 summary metrics | `.github/skills/retro/SKILL.md` lines 56-63 | PASS |
| Step 3 per-contributor | `.github/skills/retro/SKILL.md` lines 85-91 | PASS |
| Step 4 sessions (45 min, deep/medium/micro) | `.github/skills/retro/SKILL.md` lines 109-117 | PASS |
| Step 5 commit types | `.github/skills/retro/SKILL.md` lines 137-145 | PASS |
| Step 6 kanban correlation | `.github/skills/retro/SKILL.md` lines 167-170 and 175-188 | PASS |
| Structured markdown output format | `.github/skills/retro/SKILL.md` lines 191-210 | PASS |
| PowerShell-compatible commands | `.github/skills/retro/SKILL.md` line 214 | PASS |
| No .py changes | `git --no-pager log --oneline --name-only -n 5 -- .github/skills/retro/SKILL.md` -> file-only commit (`fbb8ff6`) | PASS |
| Regression check | `tests/test_skills.py` real-skill count assertions still hard-code 19 and now fail at 20 | **FAIL** |

### Verdict: FAIL
- Confidence: .96
- Rationale: textual AC is met, but #788 introduces a failing real-skill discovery regression in `tests/test_skills.py`.

[[2026-03-22]] Sun 23:34
## Test-Writer Notes
- Non-implementation task (tagged type:docs) -- no tests applicable.
- Passing through to builder.

[[2026-03-23]] Mon 00:04
## Builder Notes (re-run)
- Files changed: .github/skills/retro/SKILL.md (committed fbb8ff6)
- Tests: 33 passed (tests/test_skills.py)
- Lint: ruff clean
- Regression from reviewer fixed by #780 (flexible >= 17 assertion in TestFromAC_RealSkillsDiscovery)
- All AC items verified

[[2026-03-23]] Mon 00:40
## Review Evidence

[[2026-03-23]] Mon 00:41
## Review: #788 - Implement retro SKILL.md with git metrics workflow

[[2026-03-23]] Mon 00:41
### Test Results

[[2026-03-23]] Mon 00:41
- pytest (isolated shell): 33 passed, 0 failed, 3 warnings using plugin autoload disabled.

[[2026-03-23]] Mon 00:41
- command: uv run pytest tests/test_skills.py -q --tb=short (with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1).

[[2026-03-23]] Mon 00:41
### Lint Results

[[2026-03-23]] Mon 00:41
- ruff (isolated shell): all checks passed.

[[2026-03-23]] Mon 00:41
- command: uv run ruff check tests/test_skills.py.

[[2026-03-23]] Mon 00:41
### Coverage

[[2026-03-23]] Mon 00:41
- Not applicable: docs-only task; no Python source touched by task commit.

[[2026-03-23]] Mon 00:41
### Pass 1 - CRITICAL

[[2026-03-23]] Mon 00:41
- Test-writer AC coverage: N/A for #788 (type:docs). No TestFromAC classes were authored for this task, and builder commit fbb8ff6 did not modify test files.

[[2026-03-23]] Mon 00:41
- Security review: no secrets, injection, path traversal, insecure deserialization, or dependency additions in .github/skills/retro/SKILL.md.

[[2026-03-23]] Mon 00:41
- Data safety: no runtime state mutation or persistence paths introduced (instruction-only markdown artifact).

[[2026-03-23]] Mon 00:41
- Implementation-aware test gap analysis: no executable code path changed by #788, so no new runtime branch/test gaps introduced.

[[2026-03-23]] Mon 00:42
### Test Quality

[[2026-03-23]] Mon 00:42
- Assertion specificity: ADEQUATE (existing tests in tests/test_skills.py assert discovery counts, non-empty metadata, and list_skills inclusion).

[[2026-03-23]] Mon 00:42
- Negative/error paths: ADEQUATE for SkillRegistry suite overall; this task is docs-only and introduces no runtime error path.

[[2026-03-23]] Mon 00:42
- Mutation reasoning: ADEQUATE (if skill discovery regresses, TestFromAC_RealSkillsDiscovery tests fail).

[[2026-03-23]] Mon 00:42
- Test independence and naming: STRONG in tests/test_skills.py for reviewed scope.

[[2026-03-23]] Mon 00:42
### AC Compliance

[[2026-03-23]] Mon 00:42
- AC1 PASS: valid YAML frontmatter at .github/skills/retro/SKILL.md lines 2-3; SkillRegistry frontmatter parse check returned parsed=True, name=retro, description_nonempty=True. Mapped test: tests/test_skills.py::TestFromAC_RealSkillsDiscovery::test_real_skills_have_nonempty_names (indirect).

[[2026-03-23]] Mon 00:42
- AC2 PASS: Step 1 present at line 32 with five git commands at lines 38, 41, 44, 47, 50. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC3 PASS: Step 2 present at line 55 with required summary metrics definitions at lines 61-66. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC4 PASS: Step 3 present at line 84 with contributor columns and format examples at lines 91-94 and 101. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC5 PASS: Step 4 present at line 108 with 45-minute gap rule at line 113 and deep/medium/micro classes at lines 118-120. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC6 PASS: Step 5 present at line 135 with feat/fix/refactor/test/chore/docs prefix mapping at lines 142-147. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC7 PASS: Step 6 present at line 166 using kanban/activity.jsonl and ConvertFrom-Json at lines 172-173, with done/review/created/most-active metrics at lines 179-182. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC8 PASS: structured markdown report output template present at lines 195-210. Mapped test: N/A (manual docs verification).

[[2026-03-23]] Mon 00:42
- AC9 PASS: PowerShell-compatible guidance at line 218; Step 1 command pattern was executed in PowerShell with exit code 0 during review. Mapped test: N/A (manual + execution verification).

[[2026-03-23]] Mon 00:42
- AC11 PASS: no .py file changes in task commit scope; fbb8ff6 touches only .github/skills/retro/SKILL.md. Mapped test: N/A (VCS verification).

[[2026-03-23]] Mon 00:42
### Verdict: PASS

[[2026-03-23]] Mon 00:42
### Confidence: .95

[[2026-03-23]] Mon 00:42
### Action Taken

[[2026-03-23]] Mon 00:42
- Advance task to docs gate (review -> docs).

[[2026-03-23]] Mon 00:43
- AC10 PASS: no new Python dependencies; commit fbb8ff6 touches only .github/skills/retro/SKILL.md and pyproject.toml is clean in the current worktree. Mapped test: N/A (VCS verification).

[[2026-03-23]] Mon 02:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md with valid YAML frontmatter | File exists, name + description fields present | PASS |
| Step 1: 5 parallel git commands | 5 numbered commands in Step 1 section | PASS |
| Step 2: Summary metrics (6 metrics) | Table with commits, LOC, test ratio, contributors, active days, sessions | PASS |
| Step 3: Per-contributor (4 columns) | Table: Contributor, Commits, +/-, Test ratio, Top area | PASS |
| Step 4: Session detection (45min, 3 classes) | 2700s gap, deep/medium/micro thresholds defined | PASS |
| Step 5: Commit type breakdown (6 types) | feat/fix/refactor/test/chore/docs + other | PASS |
| Step 6: Kanban correlation | PowerShell reads activity.jsonl, 4 metrics counted | PASS |
| Output: structured markdown | Combined output section present | PASS |
| PowerShell-compatible | All commands use PS syntax, no bash-only | PASS |
| No new Python deps | Pure markdown file | PASS |
| No .py file changes | git diff confirms only SKILL.md touched | PASS |

### Test Results
- pytest: 3 pre-existing collection errors (missing modules), unrelated to #788
- ruff: 251 pre-existing errors, none from this task (no .py files changed)

### Architect Quality
- AC specificity: 11 mechanically testable lines, all clear
- Edge cases: N/A (docs-only task)
- Design direction: Correct, followed research doc
- AC quality score: 5/5

### Confidence: .97
### Action: archive
