---
name: retro
description: "Development analytics retrospective: gather git metrics, session detection, commit classification, and kanban correlation. Use when generating a development retrospective or sprint report."
---

# Retro — Development Analytics

> **Agent status:** User-invocable skill — not dispatched by the orchestrator
> pipeline. Invoked directly by the user in VS Code chat for sprint reports.

Generate a structured development retrospective from git history and kanban data.
Produces a markdown report with commit metrics, contributor breakdown, session
analysis, commit type distribution, and kanban task correlation.

## Inputs

Before starting, determine the time window:

- **Default:** last 7 days (`--since="7 days ago"`)
- **Custom:** user-specified date range (e.g., `--since="2026-03-01" --until="2026-03-13"`)

All git commands below use `$since` and optionally `$until` as the date filter.
Set these in PowerShell before proceeding:

```powershell
$since = "7 days ago"
# $until = "2026-03-13"  # optional, omit for "until now"
$gitDateArgs = @("--since=`"$since`"")
if ($until) { $gitDateArgs += "--until=`"$until`"" }
```

## Step 1 — Gather raw git data

Run these 5 git commands to collect raw data. They can run in parallel (independent):

```powershell
# 1. Commits with LOC stats
git log --format="%H|%aN|%ai|%s" --shortstat @gitDateArgs

# 2. Per-file LOC (numstat) for test vs prod split
git log --format="COMMIT:%H|%aN" --numstat @gitDateArgs

# 3. Timestamps for session detection
git log --format="%at|%aN|%s" @gitDateArgs

# 4. File change frequency (hotspots)
git log --format="" --name-only @gitDateArgs

# 5. Per-author commit counts
git shortlog -sn --no-merges @gitDateArgs
```

Parse each command's output and hold in memory for the next steps.

## Step 2 — Summary metrics table

From Step 1 data, compute and present:

| Metric | How to compute |
|--------|---------------|
| Total commits | Count lines from command 1 (exclude blank/stat lines) |
| Lines added / removed | Sum insertions/deletions from `--shortstat` lines |
| Test LOC ratio | From command 2: files matching `test_*.py` or `*_test.py` or `tests/` path → test LOC; remainder → prod LOC. Ratio = test LOC / total LOC |
| Contributors | Distinct author names from command 1 |
| Active days | Distinct dates (YYYY-MM-DD) from commit timestamps |
| Sessions | Count from Step 4 session detection |

Format as a markdown table:

```markdown
## Summary (last 7 days)

| Metric | Value |
|--------|-------|
| Commits | 42 |
| Lines added | +1,234 |
| Lines removed | -567 |
| Test LOC ratio | 38% |
| Contributors | 3 |
| Active days | 5 |
| Sessions | 12 |
```

## Step 3 — Per-contributor breakdown

From commands 1, 2, and 5, build a per-contributor table:

| Column | Source |
|--------|--------|
| Contributor | Author name from git log |
| Commits | Count per author |
| +/- | Lines added / removed per author |
| Test ratio | Test LOC / total LOC for that author's commits |
| Top area | Most frequently changed directory (from command 2 file paths) |

Format:

```markdown
## Per-contributor

| Contributor | Commits | +/- | Test ratio | Top area |
|------------|---------|-----|------------|----------|
| Alice | 20 | +800/-300 | 42% | src/owlbear/core/ |
| Bob | 15 | +350/-200 | 35% | tests/ |
| builder-agent | 7 | +84/-67 | 50% | src/owlbear/tools/ |
```

## Step 4 — Session detection

Use commit timestamps from command 3 to detect work sessions:

1. Sort commits by timestamp (ascending), grouped by author
2. A **new session** starts when the gap between consecutive commits exceeds **45 minutes** (2700 seconds)
3. Classify each session by duration:

| Classification | Duration |
|---------------|----------|
| Deep | > 2 hours |
| Medium | 30 min – 2 hours |
| Micro | < 30 min |

4. Report session count per classification and total time:

```markdown
## Sessions

| Type | Count | Total time |
|------|-------|------------|
| Deep (>2h) | 3 | 8h 30m |
| Medium (30m–2h) | 5 | 6h 15m |
| Micro (<30m) | 4 | 1h 10m |
| **Total** | **12** | **15h 55m** |
```

## Step 5 — Commit type breakdown

Parse commit messages using conventional commit prefixes. Match the first word
of the subject line (case-insensitive) against these categories:

| Type | Prefix match |
|------|-------------|
| feat | `feat:`, `feat(` |
| fix | `fix:`, `fix(` |
| refactor | `refactor:`, `refactor(` |
| test | `test:`, `test(` |
| chore | `chore:`, `chore(` |
| docs | `docs:`, `docs(` |
| other | Anything not matching above |

Report as percentages:

```markdown
## Commit types

| Type | Count | % |
|------|-------|---|
| feat | 15 | 36% |
| fix | 10 | 24% |
| test | 8 | 19% |
| refactor | 5 | 12% |
| chore | 2 | 5% |
| docs | 1 | 2% |
| other | 1 | 2% |
```

## Step 6 — Kanban correlation

Read the kanban activity log to correlate task completions with the time window:

```powershell
$sinceDate = Get-Date $since
Get-Content kanban/activity.jsonl |
    ConvertFrom-Json |
    Where-Object { $_.action -match "moved|status" -and $_.timestamp -ge $sinceDate }
```

Count:

- Tasks moved to `done` in the window
- Tasks moved to `review` in the window
- Tasks created in the window
- Most active task (most status changes)

```markdown
## Kanban activity

| Metric | Value |
|--------|-------|
| Tasks completed (→ done) | 8 |
| Tasks reviewed (→ review) | 12 |
| Tasks created | 5 |
| Most active task | #480 — SkillRegistry (6 moves) |
```

## Output format

Combine all sections into a single structured markdown report:

```markdown
# Development Retrospective — {date range}

{Step 2: Summary table}

{Step 3: Per-contributor table}

{Step 4: Session analysis}

{Step 5: Commit type breakdown}

{Step 6: Kanban activity}

---
Generated by OwlBear retro skill
```

## Notes

- All commands are PowerShell-compatible (no bash-only syntax like `grep -P` or `sed`)
- For large repos, always use `--since` to bound the query window
- Test file detection uses path heuristics (`test_*.py`, `*_test.py`, `tests/` directory)
- Session gap threshold (45 minutes) is based on established developer productivity research
- The kanban correlation requires `kanban/activity.jsonl` to exist; skip Step 6 if missing
