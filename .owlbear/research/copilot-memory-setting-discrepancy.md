# copilotMemory.enabled Setting Discrepancy

> **Owning task:** #118 — Fix copilotMemory.enabled discrepancy in workspace settings
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #48 (archived) set `github.copilot.chat.copilotMemory.enabled` to `false` in `.vscode/settings.json` (commit ea1621f). The `copilot-instructions.md` (line 65) states this setting is "explicitly disabled." However, the current workspace setting shows `true`. What caused the regression and what is the correct fix?

## 2. Sources Studied

| # | Source | Path / Ref | Relevance |
|---|--------|-----------|-----------|
| S1 | Git history — settings.json | `git log -- .vscode/settings.json` | 1.0 |
| S2 | Commit ea1621f (task #48) | `git show ea1621f` | 1.0 |
| S3 | Commit 53cf529 (task #7 monorepo skeleton) | `git show 53cf529` | 1.0 |
| S4 | Task #48 audit evidence | kanban/tasks/048-*.md | .95 |
| S5 | copilot-instructions.md line 65 | .github/copilot-instructions.md | 1.0 |
| S6 | docs/research/copilot-memory-boundaries.md §3d | docs/research/copilot-memory-boundaries.md | .90 |

## 3. Analysis

### 3a. Root Cause

N/A — trivial change, rationale: regression from a subsequent commit.

| Step | Commit | Value | What happened |
|------|--------|-------|---------------|
| 1 | ea1621f (#48, builder) | `false` | Correctly set to false per task AC |
| 2 | 53cf529 (#7, builder) | `true` | Monorepo skeleton rewrote settings.json, flipped value back to `true` |
| 3 | a2bdc11 (refactor) | `true` | Carried `true` forward unchanged |
| 4 | Current worktree | `true` | Still incorrect |

The monorepo skeleton commit (53cf529) restructured the entire settings file and inadvertently reverted the setting. The task #48 reviewer noted "live worktree differs from reviewed commit" but the discrepancy was attributed to "subsequent unrelated edits" and not flagged as a regression.

### 3b. Scope of Fix

- **One line change:** `.vscode/settings.json` line 97: change `true` to `false`
- **No documentation change needed:** `copilot-instructions.md` line 65 already correctly states the setting is disabled — the docs are right, the setting is wrong
- **No test needed:** Config-only change, same classification as original task #48

### 3c. Prevention

The root cause (whole-file rewrite clobbering a targeted setting) is a common git workflow issue. The monorepo skeleton task touched 50+ settings and didn't diff against the prior commit's targeted changes. This is a process gap, not a tooling bug.

## 4. Recommendation (.95 confidence)

Change `.vscode/settings.json` line 97 from `"github.copilot.chat.copilotMemory.enabled": true` to `false`. One-line fix, no other files affected.

## 5. Follow-up Tasks

Task #118 is itself the fix task — no additional follow-up tasks needed. The builder should:
1. Change the setting value from `true` to `false` on line 97 of `.vscode/settings.json`
2. Verify valid JSON after the change
3. Commit as `fix: restore copilotMemory.enabled to false (#118, builder)`
