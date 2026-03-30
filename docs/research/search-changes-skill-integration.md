# Add search/changes to Reviewer and Auditor Skill Workflows

> **Owning task:** #102 — Add search/changes usage to reviewer and auditor skill workflows
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #95 (docs/research/vs-code-new-tools-evaluation.md) identified that `search/changes` (`get_changed_files`) is available to 9/11 agents via the `search` tool set but no skill workflow references it. This task validates the approach for adding explicit steps to the code-review and task-verification skills.

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | VS Code Copilot Cheat Sheet [S1] | .95 | `#search/changes` — "List of source control changes", part of `#search` tool set |
| S2 | VS Code Agent Tools docs [S2] | .90 | Tool sets, `search` set includes `search/changes`; tool set example JSON confirms grouping |
| S3 | OwlBear code-review SKILL.md [S3] | 1.0 | Current reviewer workflow: no diff-check step; starts with tests, then lint, then code reading |
| S4 | OwlBear task-verification SKILL.md [S4] | 1.0 | Current auditor workflow: Step 2 verifies AC via file reads + tests; no commit scope check |
| S5 | OwlBear agent-common.instructions.md [S5] | .85 | Commit discipline: `git status --short` and `git diff --cached` referenced for committers |
| S6 | OwlBear vs-code-new-tools-evaluation.md [S6] | .90 | Prior research confirming search/changes value for reviewer and auditor |

## 3. Analysis

### 3.1 Tool Capabilities

`get_changed_files` accepts:
- `repositoryPath` (optional) — defaults to active git repo
- `sourceControlState` — filter: `staged`, `unstaged`, `merge-conflicts`

Returns file-level diffs. This replaces `git status`/`git diff` terminal commands with structured output the agent can reason about directly.

### 3.2 Reviewer Integration (code-review SKILL.md)

| Approach | Placement | Rationale |
|----------|-----------|-----------|
| New Step 2 (before tests) | Between claim and test run | Reviewer sees changed files first, scopes test run and code reading to those files |
| Merge into Step 5 (code reading) | Inside existing step | Delays scope awareness; reviewer reads code blind |

**Recommendation (.85 confidence):** New Step 2. Seeing the changed file list early lets the reviewer scope all subsequent steps (tests, lint, code reading) to relevant files. This is how human code reviewers work — read the diff summary first, then deep-dive.

### 3.3 Auditor Integration (task-verification SKILL.md)

| Approach | Placement | Rationale |
|----------|-----------|-----------|
| Add to Step 2 | Alongside existing AC verification | Scope check is part of verifying the builder's work |
| New Step 2.1 | Between AC check and scoring | Isolates concern but adds step bloat |

**Recommendation (.80 confidence):** Integrate into existing Step 2. The auditor already verifies "file exists" and "code matches AC" here. Adding "changed files match task scope" is a natural extension, not a new step.

### 3.4 Tool Name Reference

AC requires "steps reference the tool by name." The runtime name visible to agents is `get_changed_files` (what appears in tool calls). The `#search/changes` name is the user-facing `#`-mention shorthand [S1]. Skills should reference `get_changed_files` since agents invoke tools by runtime name.

## 4. Recommendation (.85 confidence)

Proceed with the task as specified. Both skills need minimal, targeted additions:

1. **code-review SKILL.md:** Insert new Step 2 ("Check source control changes") between current Steps 1 and 2. Use `get_changed_files` with `sourceControlState: ['staged', 'unstaged']` to list builder's changes. Record the changed file list for scoping later steps.

2. **task-verification SKILL.md:** Add a bullet to Step 2 using `get_changed_files` to verify changed files align with task AC scope. Flag unexpected file changes (files outside the task's domain).

Risk: Low — both agents already have the `search` tool set. No `.agent.md` changes needed. Changes are additive text in skill workflow docs.

KISS check: No new abstractions, no new tools, no config changes. Just workflow documentation.

## 5. Follow-up Tasks

No additional tasks needed. Task #102 itself is the implementation task. The AC is concrete and directly actionable by the builder.
