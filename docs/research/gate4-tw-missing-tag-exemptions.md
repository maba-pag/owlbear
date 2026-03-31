# Gate 4 TW:MISSING — Tag-Based Exemptions

> **Owning task:** #215 — Add tag-based exemptions to Gate 4 TW:MISSING check
> **Date:** 2026-03-30 **Status:** Complete

## 1. Context and Question

Gate 4 (TW:MISSING) in the dispatch-planning skill flags `in-progress` tasks whose body
lacks `## Test-Writer Notes`. The tdd-red skill's Step 1a defines a non-implementation
pass-through for tags `research`, `docs`, `type:config`, `type:docs`. Both mechanisms
have gaps:

1. **Test tasks flagged as TW:MISSING** — Tasks tagged `test`/`type:test` ARE
   test-writer deliverables. Requiring TW notes on them is circular.
2. **Incomplete pass-through list** — Tags `agent`, `quality` (markdown-only tasks)
   aren't in the non-impl list, causing the test-writer to attempt meta-tests.

**Question:** What tags need exemptions, where do changes go, and are there hidden
interactions?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `skills/dispatch-planning/SKILL.md` Recipe 1 | Internal | TW:MISSING gate logic — no tag check in PowerShell |
| S2 | `skills/tdd-red/SKILL.md` Step 1, 1a | Internal | Non-impl pass-through tag list (4 tags) |
| S3 | `skills/tdd-workflow/SKILL.md` Step 1a | Internal | Builder pass-through keys off TW notes text, not tags |
| S4 | `.github/prompts/agent-audit.prompt.md` L108 | Internal | Duplicates the non-impl tag list |
| S5 | Kanban board — tasks #99, #196, #204, #207, #208 | Internal | Real examples of test/agent/quality tasks in pipeline |
| S6 | GitHub Actions `paths-ignore` pattern | External | Established CI pattern: exempt non-code changes from test gates |
| S7 | GitLab CI `rules:changes` pattern | External | Same pattern: tag/path-based gate exemptions in CI pipelines |

## 3. Analysis

### 3.1 Tag classification for gate exemptions

| Tag | Meaning | Exempt from TW:MISSING? | Add to tdd-red pass-through? | Rationale |
|-----|---------|-------------------------|------------------------------|-----------|
| `test` | Test task | Yes | Yes | TW output — circular to require TW meta-tests |
| `type:test` | Test type | Yes | Yes | Same as `test` |
| `agent` | Agent/skill markdown | No (not test-related) | Yes | No Python code to test |
| `quality` | Process quality | No (not test-related) | Yes | Typically markdown-only changes |
| `scope:agents` | Scope prefix | No | No | Scope tags are too broad — could include Python |

### 3.2 Impact map — all locations needing changes

| File | Section | Change needed |
|------|---------|---------------|
| `skills/dispatch-planning/SKILL.md` | Recipe 1 PowerShell | Add tag exemption to TW:MISSING condition |
| `skills/dispatch-planning/SKILL.md` | Gate 4 description | Document exemption logic |
| `skills/dispatch-planning/SKILL.md` | Agent dispatch table + paragraph | Update non-impl tag list |
| `skills/tdd-red/SKILL.md` | Step 1 item 3 | Expand tag list: add `test`, `type:test`, `agent`, `quality` |
| `.github/prompts/agent-audit.prompt.md` | Non-impl tasks paragraph | Update tag list to match |

**No change needed:** `skills/tdd-workflow/SKILL.md` — builder pass-through (S3) checks
for "Non-implementation task" text in TW notes, not tags. If tdd-red passes through
correctly, tdd-workflow inherits the behavior automatically.

### 3.3 AC gap identified

The current AC (#215) adds `agent`/`quality` to tdd-red but not `test`/`type:test`.
Test tasks also need the tdd-red pass-through — writing meta-tests for a test task
is circular. Recommend the architect adds `test`/`type:test` to AC item 2.

### 3.4 Tag list synchronization risk

The non-impl tag list is duplicated in 4 files (dispatch-planning SKILL, tdd-red SKILL,
agent-audit prompt, copilot-instructions non-impl paragraph). Future tag additions
risk desynchronization. Mitigation: add a cross-reference comment in each file
pointing to dispatch-planning as the authoritative list.

## 4. Recommendation (.90 confidence)

Proceed with the changes. The approach is sound — tag-based exemptions are the
established pattern in CI/CD pipelines (S6, S7). Specific recommendations:

1. **Expand tdd-red pass-through** to 8 tags: `research`, `docs`, `type:config`,
   `type:docs`, `test`, `type:test`, `agent`, `quality`
2. **Add Board Scan exemption** for `test`/`type:test` in Recipe 1 PowerShell
3. **Update all 5 locations** in the impact map above
4. **Add cross-reference notes** to reduce synchronization risk

Risk: Over-exemption if a task is mistagged. Architect tagging responsibility
(already documented in dispatch-planning) is the mitigation.

## 5. Follow-up Tasks

Task #215 covers AC items 1–4. Additional follow-up needed:

```
kanban\kanban-md.exe create "Sync non-impl tag list cross-references across skill files" --priority nice-to-have --status ideation --tags "scope:agents,quality,type:config"
```

This follow-up adds cross-reference comments in each file pointing to the authoritative
tag list location, reducing future synchronization risk.
