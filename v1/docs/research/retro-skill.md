# Retro Skill for Development Analytics

> **Owning task:** #786 — Create retro skill for development analytics
> **Date:** 2026-03-13 **Status:** Complete

## 1. Context and Question

OwlBear has no development metrics or retrospective capability. The curator triages
lessons learned but doesn't analyze git history, velocity, or quality trends.
Should OwlBear adopt a retro skill, and what metrics/structure should it use?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| garrytan/gstack retro v2.0 | <https://github.com/garrytan/gstack/blob/main/retro/SKILL.md> | .90 | 14-step retro: git metrics, session detection, per-contributor, streak, compare mode |
| IonicaBizau/git-stats v3.5 | <https://github.com/IonicaBizau/git-stats> | .60 | GitHub-like contribution calendars, per-author stats, date filtering |
| OwlBear kanban activity.jsonl | local: kanban/activity.jsonl | .85 | JSONL log of task creates/moves/edits — enriches git-only metrics with task context |
| OwlBear retrospective-learning-hook research | local: docs/research/retrospective-learning-hook.md | .70 | Complementary: code-level hook ingests findings into KG; retro skill is user-facing analytics |

## 3. Analysis

### 3.1 Feature Comparison

| Feature | gstack retro | git-stats | Proposed OwlBear |
|---------|-------------|-----------|-----------------|
| Commits + LOC | Yes | Yes | Yes |
| Test LOC ratio | Yes (numstat filter) | No | Yes |
| Session detection (45min gap) | Yes | No | Yes |
| Per-contributor breakdown | Yes (deep: praise + growth) | Yes (pie chart) | Yes (data only, no coaching) |
| Commit type breakdown | Yes (conventional commits) | No | Yes |
| Hotspot analysis | Yes (top 10 files) | No | Yes |
| Focus score | Yes | No | Omit (YAGNI — single dev) |
| Compare mode | Yes (window vs prior) | Yes (date range) | Omit v1 (YAGNI) |
| Streak tracking | Yes | No | Omit v1 (YAGNI) |
| History persistence | Yes (.context/retros/*.json) | Yes (~/.git-stats) | Omit v1 (markdown output only) |
| Kanban integration | No | No | Yes (activity.jsonl correlation) |
| Dependencies | bash + git | Node.js | PowerShell + git (zero deps) |

### 3.2 OwlBear-Specific Adaptations

**What to keep from gstack:**

- Core git commands: `git log --format --shortstat`, `git log --numstat` for test/prod split
- 45-minute session detection threshold (well-established heuristic)
- Conventional commit type categorization
- Per-contributor commit/LOC/test-ratio breakdown
- Structured markdown output with summary table

**What to drop (KISS/YAGNI):**

- Team coaching narrative (praise/growth) — OwlBear is single-developer focused
- Ship of the week / focus score — premature for a single-dev daemon project
- Compare mode / streak tracking — add later if needed
- JSON history persistence — markdown output is sufficient for v1
- Pacific time hardcoding — use local timezone
- PR size distribution — OwlBear doesn't use PRs

**What to add (OwlBear-specific):**

- Kanban correlation: tasks completed/moved in the window (from activity.jsonl)
- Agent contribution: count commits by agents vs human (from git author)

### 3.3 Technical Feasibility

All data comes from git CLI commands available on every dev machine. No Python
dependencies needed — the skill instructs the agent to run git commands in
PowerShell terminal, parse output, and format markdown. This matches the
"allowed-tools" approach: the skill is a SKILL.md (instructions only), not code.

**Git commands needed (all cross-platform):**

| Command | Data produced |
|---------|--------------|
| `git log --format="%H\|%aN\|%ai\|%s" --shortstat` | Commits, LOC, authors |
| `git log --format="COMMIT:%H\|%aN" --numstat` | Test vs prod LOC split |
| `git log --format="%at\|%aN\|%s"` | Timestamps for session detection |
| `git log --format="" --name-only` | File hotspots |
| `git shortlog -sn --no-merges` | Per-author commit counts |

### 3.4 Architecture Fit

| Concern | Assessment |
|---------|-----------|
| File location | `.github/skills/retro/SKILL.md` — standard skill path |
| Tool restriction | `Bash`/terminal + `Read` only — no file writes needed |
| Agent invocation | Any agent or user can invoke; no special wiring required |
| Kanban integration | Read-only: `Get-Content kanban/activity.jsonl` |
| Existing overlap | None — curator handles lessons, not metrics |

## 4. Recommendation (.80 confidence)

Create a focused v1 retro skill with 6 steps:

1. Gather raw git data (parallel commands)
2. Compute summary metrics table (commits, LOC, test ratio, contributors)
3. Per-contributor breakdown table
4. Session detection and time distribution
5. Commit type breakdown (conventional commits)
6. Kanban correlation (tasks completed in window)

**Risks:**

- PowerShell git output parsing differs from bash — skill must use PS-compatible commands
- Large repos may have slow `--numstat` queries — mitigate with `--since` window

**Why not a Python tool?** AC explicitly says "no new Python dependencies" and "no
changes to .py files." A SKILL.md is pure instructions — the agent runs git commands
and formats output. This is the simplest approach (KISS).

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement retro SKILL.md with git metrics workflow" --priority nice-to-have --status ideation --tags "scope:agent-config,type:docs" --body "## Goal\nCreate .github/skills/retro/SKILL.md with development analytics workflow.\n\n## AC\n- [ ] SKILL.md at .github/skills/retro/SKILL.md with valid YAML frontmatter\n- [ ] Step 1: Gather raw git data (5 parallel git commands)\n- [ ] Step 2: Summary metrics table (commits, LOC, test LOC ratio, contributors, active days, sessions)\n- [ ] Step 3: Per-contributor breakdown (commits, +/-, test ratio, top area)\n- [ ] Step 4: Session detection (45min gap threshold, deep/medium/micro classification)\n- [ ] Step 5: Commit type breakdown (feat/fix/refactor/test/chore/docs percentages)\n- [ ] Step 6: Kanban correlation (tasks completed in window from activity.jsonl)\n- [ ] Output format: structured markdown report\n- [ ] PowerShell-compatible commands (no bash-only syntax)\n- [ ] No new Python dependencies\n- [ ] No changes to .py files\n\nSee docs/research/retro-skill.md for design rationale."
```
