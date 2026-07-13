---
id: 86
title: Evaluate agent-scoped hooks for pipeline enforcement (scoped AC)
status: archived
priority: medium
created: 2026-03-27 13:36:44.439454+01:00
updated: 2026-03-30 09:53:59.291158+02:00
started: 2026-03-30 09:53:58.967401+02:00
completed: 2026-03-30 09:53:58.967401+02:00
tags:
- research
- phase-1
- scope:agents
- hooks
class: standard
archival_reason: completed
archival_refs: []
---

## Context

- See docs/research/agent-md-format.md section 7 and section 9.
- This task supersedes placeholder task #37, which was blocked due to empty body and missing acceptance criteria.
- Goal: determine whether agent-scoped hooks should be enabled for the OwlBear pipeline and define safe rollout guardrails.

## Acceptance Criteria

- [ ] Review VS Code hook capabilities relevant to agents used in OwlBear (`preToolUse`, `postToolUse`, `stop`) and summarize constraints/limits.
- [ ] Evaluate at least three concrete pipeline enforcement candidates (for example: claim enforcement, post-edit lint checks, pre-exit commit guard), including trade-offs and failure modes.
- [ ] Produce a recommendation matrix with options, confidence scores, and a clear recommended path.
- [ ] Document findings in `docs/research/agent-scoped-hooks-pipeline-enforcement.md`.
- [ ] Include explicit rollout guidance: prerequisites, required settings, phased adoption plan, and when not to use hooks.

[[2026-03-27]] Fri 14:30
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Review VS Code hook capabilities (preToolUse, postToolUse, stop) | Clear: specific hook types named, deliverable is constraints summary | None |
| Evaluate at least three pipeline enforcement candidates | Clear: minimum count specified, trade-offs and failure modes required | None |
| Produce recommendation matrix with confidence scores | Clear: specific deliverable format | None |
| Document findings in docs/research/agent-scoped-hooks-pipeline-enforcement.md | Clear: exact file path | None |
| Include rollout guidance with 4 specific components | Clear: prerequisites, settings, phased plan, anti-patterns all enumerable | None |

### Architecture Notes
Well-scoped research task with verifiable AC. Each line is pass/fail checkable.

**Important distinction for researcher:** OwlBear has TWO hook layers. (1) Internal `HookRegistry` in `core/hooks.py` which is explicitly observational and non-blocking per architecture-standards. (2) VS Code agent-scoped hooks (`preToolUse`, `postToolUse`, `stop`) in `.agent.md` frontmatter, which are the subject of this research. These are different mechanisms. The research should clearly separate them and note that any enforcement behavior from VS Code hooks must not conflict with the internal hook contract.

No existing VS Code hook usage in current `.agent.md` files (clean slate). Setting `chat.useCustomAgentHooks: true` is a prerequisite noted in docs/research/agent-md-format.md section 7.

### Changes Made
- No AC changes needed (already well-scoped)
- Approved to todo

### Dependencies
- None listed, none missing
- Supersedes #37 (blocked at ideation, properly recorded)

[[2026-03-30]] Mon 03:07
## Review Evidence
See docs/scratch/86-reviewer.tmp for full evidence.

Verdict: FAIL - missing Follow-up Tasks section and zero follow-up kanban tasks created. All 5 explicit AC lines pass on content quality.

[[2026-03-30]] Mon 05:25
## Test-Writer Notes

[[2026-03-30]] Mon 05:25
- Non-implementation task (tagged research) - no tests applicable. Passing through to builder.

[[2026-03-30]] Mon 09:29
## Context

See docs/research/stop-commit-guard-hooks-phase1.md for full analysis.
See docs/research/agent-scoped-hooks-pipeline-enforcement.md section 6 for rollout guidance.

Phase 1 of VS Code agent-scoped hooks adoption: add a Stop hook to builder and writer agents that blocks session end when uncommitted work exists. Uses the command-execution model (type: command), not prompt injection.

## Acceptance Criteria

- [ ] Create scripts/hooks/stop-commit-guard.ps1 that:
  - Reads stdin JSON for hook context
  - Returns immediately (empty JSON) if stop_hook_active is true (loop prevention)
  - Runs git status --short to detect uncommitted changes
  - If dirty: returns JSON with decision block and reason
  - If clean: returns empty JSON
- [ ] Add hooks section to agents/builder.agent.md YAML frontmatter with a Stop hook entry (type: command, windows: powershell -NoProfile -File scripts/hooks/stop-commit-guard.ps1)
- [ ] Add identical hooks section to agents/writer.agent.md YAML frontmatter
- [ ] Add chat.useCustomAgentHooks: true to .vscode/settings.json if not already present
- [ ] Verify both agent files have valid YAML frontmatter (no parse errors in VS Code Problems panel)
- [ ] Verify the script handles three cases: (a) clean working tree returns empty JSON, (b) dirty working tree returns block decision JSON, (c) stop_hook_active true in stdin returns immediately without blocking

[[2026-03-30]] Mon 09:53
## Audit
### AC Verification (Original 5 Research AC)
| AC Line | Evidence | Status |
|---------|----------|--------|
| Review VS Code hook capabilities (preToolUse, postToolUse, stop) and summarize constraints/limits | Section 3 of research doc: 8 hook types, definition format, constraints table (10 entries) | PASS |
| Evaluate at least three pipeline enforcement candidates with trade-offs and failure modes | Section 4: 5 candidates evaluated (lint guard, claim enforcement, stop commit guard, coverage reminder, read-only guard) -- exceeds minimum of 3 | PASS |
| Produce recommendation matrix with options, confidence scores, and clear recommended path | Section 5: 7-column matrix, Phase 1/Phase 2/Skip recommendations, .80 confidence on recommended path | PASS |
| Document findings in docs/research/agent-scoped-hooks-pipeline-enforcement.md | File exists (350+ lines), committed at 0cf02bb, updated at 884bcb6 | PASS |
| Include rollout guidance: prerequisites, required settings, phased adoption plan, when not to use hooks | Section 6: all 4 components present (Prerequisites, Required Settings, Phased Adoption Plan, When Not to Use Hooks) | PASS |

### Research Task Checks
- Research doc exists: YES
- Follow-up tasks created: YES (#209 todo, #210 ideation, #211 ideation, #212 todo)
- Follow-up tasks link to research doc: YES (#209 body references docs/research/agent-scoped-hooks-pipeline-enforcement.md)
- Section 8 in research doc lists follow-up tasks with AC summaries

### Test Results
- pytest: 1292 passed, 168 failed, 6 errors (all failures pre-existing from other tasks -- voice, mcp-knowledge, validate_agents, etc. No task #86 scope)
- ruff: 3 errors (all pre-existing, unrelated to #86)

### Architect Quality
- AC specificity: 5 clear, verifiable items with exact deliverable format
- Edge case coverage: adequate for research scope
- Design direction: architect noted two-hook-layer distinction, researcher addressed it in Section 1
- AC quality score: 4 (adequate, minor gap: AC did not explicitly require follow-up task creation, which is an instruction-level rule)

### Notes
- Task body contains a second AC block (implementation items for Phase 1 hooks) appended during rework -- these belong to follow-up task #209, not #86
- Research doc was updated from prompt-injection model to command-execution model during rework -- committed as part of #86 audit
- Task #212 (update research doc) may overlap with committed changes

### Deduction breakdown
- No AC lines without evidence: -0
- No lint issues in task scope: -0
- AC quality 4: -0
- Missing second reviewer PASS evidence (initial FAIL, then reworked, no updated reviewer section): -.02

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 884bcb6 | docs | docs/research/agent-scoped-hooks-pipeline-enforcement.md | #86 |
