---
id: 942
title: Codify prompt-vs-skill-vs-agent rules for user-facing command surfaces
status: archived
priority: nice-to-have
created: 2026-03-22T19:01:34.2542942+01:00
updated: 2026-03-24T10:59:03.267034+01:00
started: 2026-03-24T10:58:58.2020699+01:00
completed: 2026-03-24T10:58:58.2020699+01:00
tags:
    - agent
    - scope:copilot
    - docs
    - type:docs
parent: 930
class: standard
---

## Context

Task #930 recommends a simple rule for user-facing command surfaces: use .prompt.md for repeatable slash commands, SKILL.md for reusable on-demand knowledge, and .agent.md for long-lived role-based execution. OwlBear currently uses all three surfaces but does not document when to choose which.

See docs/research/prompt-vs-skill-vs-agent-rules.md.

## Acceptance Criteria

- [ ] Add a Command Surface Selection section to .github/copilot-instructions.md containing a when-to-use decision table that distinguishes .prompt.md, SKILL.md, and .agent.md by use case (based on section 3.2 of the research doc).
- [ ] Include one concrete OwlBear example per surface using existing repo files (e.g. orchestrate.prompt.md, research-workflow/SKILL.md, reviewer.agent.md).
- [ ] State the default rule: user-facing one-shot commands use .prompt.md unless they need auto-loading or co-located resources.
- [ ] Do not add, rename, or delete any command files in this task -- scope is limited to the copilot-instructions doc.

[[2026-03-24]] Tue 02:54

## Architecture Review

**Verdict:** APPROVED (with merge)

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| One concrete example per surface | Verifiable, research identifies the three examples (orchestrate.prompt.md, research-workflow/SKILL.md, reviewer.agent.md) | Kept as-is |

| Default rule: .prompt.md for one-shots | Verifiable, presence check | Kept as-is |

| Scope guard: no file add/rename/delete | Verifiable, diff check | Kept as-is |

### Architecture Notes

- Docs-only task (type:docs) touching a single file (.github/copilot-instructions.md). No code, no tests needed.

- Research doc (docs/research/prompt-vs-skill-vs-agent-rules.md) provides the decision table content (section 3.2) and examples (section 3.3) -- writer can copy directly.

- Merged redundant follow-up #974 (identical AC, at ideation) into this task to avoid duplicate work.

- Pattern consistency: copilot-instructions.md already has tables for tech stack, directory structure, priorities, and tags. A new table fits the established style.

### Changes Made

- Deleted #974 (redundant duplicate at ideation with identical scope).

### Dependencies

- Parent #930 (research) -- complete, no blockers.

- No other dependencies required.

[[2026-03-24]] Tue 03:18

## Test-Writer Notes

- Non-implementation task (type:docs) — scope limited to .github/copilot-instructions.md doc edit only.

- Architect notes: No code, no tests needed. Passing through to builder.

[[2026-03-24]] Tue 05:09

## Builder Notes

- Files changed: .github/copilot-instructions.md
- Tests: N/A (docs-only task; test-writer notes explicitly state no tests needed)
- Lint: N/A (markdown-only scope)
- Evidence: Added a new `Command Surface Selection` section with a decision table for `.prompt.md`, `SKILL.md`, and `.agent.md`; included concrete OwlBear examples (`.github/prompts/orchestrate.prompt.md`, `.github/skills/research-workflow/SKILL.md`, `.github/agents/reviewer.agent.md`); and added the default-rule sentence for user-facing one-shot commands.
- Fixes applied: Added command-surface guidance section only; no command files were added, renamed, or deleted.
- Commit: d3b8bed

[[2026-03-24]] Tue 09:44

## Review Evidence

## Review: #942 - Codify prompt-vs-skill-vs-agent rules for user-facing command surfaces

### Test Results

- pytest: 15 passed, 0 failed (`uv run pytest tests/test_context_hook.py -q --tb=short`)
- warnings: 2 optional-dependency warnings from `tests/conftest.py` about missing `qdrant_client`; unrelated to this docs-only change

### Lint Results

- ruff: All checks passed (`uv run ruff check src/owlbear/core/context_hook.py tests/test_context_hook.py`)

### Coverage

- N/A — docs-only task; no src/ module changed

### Test-Writer Coverage

- No task-specific `TestFromAC_*` classes were created for #942; the test-writer correctly marked this docs-only task as having no applicable tests.

### TestFromAC Comparison

- N/A — no task-specific `TestFromAC_*` classes were added or modified for this task.

### Test Quality

- N/A for direct AC enforcement because the acceptance criteria are documentation content, not runtime behavior.
- Runtime sanity check still passed: `tests/test_context_hook.py` confirms `.github/copilot-instructions.md` remains readable by the instruction-loading path.

### Security / Data Safety

- No executable code, dependency, or runtime-behavior changes in the reviewed commit.
- `git show --stat --name-only d3b8bed` lists only `.github/copilot-instructions.md`.

### Current-State Check

- The reviewed section in the working tree matches builder commit `d3b8bed` exactly at lines 33-41, despite unrelated uncommitted noise elsewhere in the repo and later parts of the same file.

### AC Compliance

| AC Line | Evidence | Status |
| --- | --- | --- |
| Add `Command Surface Selection` section with a when-to-use table distinguishing `.prompt.md`, `SKILL.md`, and `.agent.md` by use case | `.github/copilot-instructions.md` lines 33-39 contain the new section and three-surface decision table; source recommendation is `docs/research/prompt-vs-skill-vs-agent-rules.md` lines 36-44 | PASS |
| Include one concrete OwlBear example per surface using existing repo files | `.github/copilot-instructions.md` lines 37-39 list `.github/prompts/orchestrate.prompt.md`, `.github/skills/research-workflow/SKILL.md`, and `.github/agents/reviewer.agent.md`; file existence verified in the workspace; research examples align with `docs/research/prompt-vs-skill-vs-agent-rules.md` lines 50-52 | PASS |
| State the default rule: user-facing one-shot commands use `.prompt.md` unless they need auto-loading or co-located resources | `.github/copilot-instructions.md` line 41 states the default rule verbatim; it matches `docs/research/prompt-vs-skill-vs-agent-rules.md` line 44 | PASS |
| Do not add, rename, or delete any command files in this task | Builder commit `d3b8bed` shows only one touched file: `.github/copilot-instructions.md`; no prompt, skill, or agent files were added, renamed, or deleted | PASS |

### Verdict

- PASS
- Confidence: .96
- Reason: The change is scoped correctly, matches the research recommendation, preserves the required examples and default rule, and the current reviewed section still matches the builder commit.

[[2026-03-24]] Tue 10:58

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Add Command Surface Selection section with when-to-use decision table | `.github/copilot-instructions.md` lines 34-41: section heading + 3-row table distinguishing `.prompt.md`, `SKILL.md`, `.agent.md` by use case; aligns with research doc section 3.2 | PASS |
| One concrete OwlBear example per surface using existing repo files | Table column 3 lists `orchestrate.prompt.md`, `research-workflow/SKILL.md`, `reviewer.agent.md`; all three verified on disk via Test-Path | PASS |
| State default rule: user-facing one-shot commands use `.prompt.md` unless they need auto-loading or co-located resources | Line 41 states the default rule verbatim | PASS |
| Do not add, rename, or delete any command files | Commit d3b8bed touches only `.github/copilot-instructions.md` (`git show --stat --name-only d3b8bed`) | PASS |

### Test Results

- pytest: 4215 passed, 46 failed (all pre-existing RED-phase stubs and signature drift — `test_notification_hook`, `test_intent_routing`, `test_integration_e2e`, `test_bootstrap_structure`, etc.), 20 skipped, 6 deselected. No failures related to #942.
- ruff: N/A (markdown-only change)

### Architect Quality

- AC specificity: 4/5 — clear, verifiable criteria for a docs-only task; matched research doc recommendations precisely
- Edge cases: N/A (docs-only, no runtime behavior)
- Design direction: architect correctly identified this as a single-file docs task, merged duplicate #974
- AC quality score: 4

### Upstream Commit Verification

- Builder commit d3b8bed verified in git log; correct message format `docs: add command surface selection guidance (#942, builder)`; scoped to single file.
- Uncommitted changes in working tree are cosmetic table-alignment reformatting unrelated to #942.

### Confidence: .97

### Action: archive
