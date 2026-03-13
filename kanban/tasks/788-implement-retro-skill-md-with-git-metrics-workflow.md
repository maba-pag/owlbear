---
id: 788
title: Implement retro SKILL.md with git metrics workflow
status: in-progress
priority: nice-to-have
created: 2026-03-13T17:14:35.7832472+01:00
updated: 2026-03-13T20:45:50.9615286+01:00
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
