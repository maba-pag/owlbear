---
id: 213
title: 'Fix #210 and #211 AC to use command-execution hook model'
status: archived
priority: medium
created: 2026-03-30 14:07:05.452852+02:00
updated: 2026-03-30 20:25:33.834705+02:00
started: 2026-03-30 20:24:40.261733+02:00
completed: 2026-03-30 20:24:40.261733+02:00
tags:
- docs
- hooks
- scope:agents
class: standard
archival_reason: completed
archival_refs: []
---

## Context
Tasks #210 and #211 reference the outdated prompt-injection hook model. Their AC says 'injecting a prompt' but the VS Code hooks API (3/25/2026) uses command-execution with JSON I/O.
See docs/research/stop-commit-guard-defect-remediation.md section 6 for impact analysis.

## Acceptance Criteria
- [ ] Update #210 AC: PostToolUse hook should use type: command + script, not prompt injection
- [ ] Update #210 AC: tool filtering done in script via stdin tool_name, not YAML gating
- [ ] Update #211 AC: PreToolUse hook should use type: command + script with permissionDecision
- [ ] Both tasks use command: key (not windows: or bash:)

[[2026-03-30]] Mon 14:13
## Research
Doc: docs/research/hook-ac-command-execution-model.md

### Changes applied
- #210 AC: replaced prompt-injection wording with command-execution model (PostToolUse, script reads tool_name from stdin, returns systemMessage or exit code 2)
- #211 AC: replaced prompt-injection wording with command-execution model (PreToolUse, script reads tool_name from stdin, returns permissionDecision deny)
- Both: corrected tool names from edit/editFiles to create_file, replace_string_in_file, multi_replace_string_in_file
- Both: require command: key (not windows: alone)
- Both: added reference to correction rationale doc

### Sources
VS Code Hooks docs (3/25/2026), OwlBear #209 remediation, OwlBear #86 parent research

[[2026-03-30]] Mon 15:14
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update #210 AC: PostToolUse use command + script | Verified: #210 now has type: command, command: key, scripts/hooks/lint-changed.ps1 | Pass |
| Update #210 AC: tool filtering via stdin | Verified: #210 script reads tool_name from stdin JSON, filters for create_file/replace_string_in_file/multi_replace_string_in_file | Pass |
| Update #211 AC: PreToolUse use command + script with permissionDecision | Verified: #211 now has type: command, command: key, scripts/hooks/deny-writes.ps1, returns permissionDecision deny | Pass |
| Both tasks use command: key | Verified: both #210 and #211 specify command: key, not windows: or bash: | Pass |

### Architecture Notes
This is a kanban-metadata-only correction task (no application code). The researcher has already applied all four AC items to #210 and #211. Corrected AC in both tasks matches the prescribed corrections in docs/research/hook-ac-command-execution-model.md. Both target tasks now reference the correction rationale doc.

No TDD task needed: deliverable is kanban task edits, not source code.

No premise challenge concern: the AC defects were real (prompt-injection vs command-execution model mismatch) and correction was necessary before #210/#211 can proceed through the pipeline.

### Changes Made
- None needed. Researcher already applied all corrections.

### Dependencies
- Verified: no depends_on declared (correct, this is a standalone correction task)
- Downstream: #210 and #211 are now unblocked for architect review with corrected AC

[[2026-03-30]] Mon 15:14
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update #210 AC: PostToolUse use command + script | Verified: #210 now has type: command, command: key, scripts/hooks/lint-changed.ps1 | Pass |
| Update #210 AC: tool filtering via stdin | Verified: #210 script reads tool_name from stdin JSON, filters for create_file/replace_string_in_file/multi_replace_string_in_file | Pass |
| Update #211 AC: PreToolUse use command + script with permissionDecision | Verified: #211 now has type: command, command: key, scripts/hooks/deny-writes.ps1, returns permissionDecision deny | Pass |
| Both tasks use command: key | Verified: both #210 and #211 specify command: key, not windows: or bash: | Pass |

### Architecture Notes
This is a kanban-metadata-only correction task (no application code). The researcher has already applied all four AC items to #210 and #211. Corrected AC in both tasks matches the prescribed corrections in docs/research/hook-ac-command-execution-model.md. Both target tasks now reference the correction rationale doc.

No TDD task needed: deliverable is kanban task edits, not source code.

No premise challenge concern: the AC defects were real (prompt-injection vs command-execution model mismatch) and correction was necessary before #210/#211 can proceed through the pipeline.

### Changes Made
- None needed. Researcher already applied all corrections.

### Dependencies
- Verified: no depends_on declared (correct, this is a standalone correction task)
- Downstream: #210 and #211 are now unblocked for architect review with corrected AC

-t

[[2026-03-30]] Mon 15:14
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Update #210 AC: PostToolUse command + script | Verified in #210 | Pass |
| Update #210 AC: tool filtering via stdin | Verified in #210 | Pass |
| Update #211 AC: PreToolUse command + script + permissionDecision | Verified in #211 | Pass |
| Both tasks use command: key | Verified in both #210 and #211 | Pass |

### Architecture Notes
Kanban-metadata-only correction task (no application code). Researcher already applied all four AC items to #210 and #211. Corrected AC matches docs/research/hook-ac-command-execution-model.md. No TDD task needed (no source code). No premise concern (defects were real).

### Changes Made
- None needed. Researcher already applied all corrections.

### Dependencies
- Verified: no depends_on declared (correct, standalone correction)
- Downstream: #210 and #211 now unblocked for architect review with corrected AC

-t

[[2026-03-30]] Mon 15:14
## Architecture Review
**Verdict:** Approve

Kanban-metadata-only correction task. Researcher already applied all four AC items. Verified #210 and #211 AC matches docs/research/hook-ac-command-execution-model.md. No TDD needed (no source code). No premise concern.

All AC lines pass: both tasks use command: key, type: command, stdin JSON tool_name filtering, correct VS Code tool names.

Downstream: #210 and #211 now unblocked for architect review with corrected AC.

-t

[[2026-03-30]] Mon 15:15
## Architecture Review
**Verdict:** Approve

Kanban-metadata-only correction task. Researcher already applied all four AC items. Verified #210 and #211 AC matches docs/research/hook-ac-command-execution-model.md. No TDD needed (no source code). No premise concern.

All AC lines pass: both tasks use command: key, type: command, stdin JSON tool_name filtering, correct VS Code tool names.

Downstream: #210 and #211 now unblocked for architect review with corrected AC.

[[2026-03-30]] Mon 17:41
## Test-Writer Notes
- Non-implementation task (tagged docs) â€” no tests applicable.
- Deliverable is kanban task edits only (kanban-metadata-only correction per Architecture Review).
- Passing through to builder.

[[2026-03-30]] Mon 18:31
## Review Evidence
Reviewer: reviewer | Task: #213 | Date: 2026-03-30 | Type: docs

AC1 PASS - #210 has type:command + command: key + lint-changed.ps1
AC2 PASS - #210 reads tool_name from stdin, filters create_file etc
AC3 PASS - #211 has type:command + command: key + deny-writes.ps1 + permissionDecision deny
AC4 PASS - both #210 and #211 use command: key (not windows: or bash:)

Research doc docs/research/hook-ac-command-execution-model.md confirmed in git diff.
Security: no surface (markdown/kanban only). Confidence: .96

[[2026-03-30]] Mon 19:35
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Kanban-metadata-only correction; no behavior/API change to OwlBear |
| 2 | Docstrings | No | N/A | No Python modules created or modified |
| 3 | docs/sources/overview.md | Yes | Pass | Row already present under Hook AC Command-Execution Model Correction (Task #213) |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc | Yes | Pass | docs/research/hook-ac-command-execution-model.md exists and is linked in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None found

[[2026-03-30]] Mon 20:24
## Audit
### AC Verification
AC1 PASS - #210 AC now specifies type: command, command: key for scripts/hooks/lint-changed.ps1
AC2 PASS - #210 AC says script reads tool_name from stdin JSON, filters for create_file/replace_string_in_file/multi_replace_string_in_file
AC3 PASS - #211 AC now specifies type: command, command: key for scripts/hooks/deny-writes.ps1, returns permissionDecision deny
AC4 PASS - Both #210 and #211 use command: key (not windows: or bash:)

### Test Results
- pytest: 1349 passed, 118 failed (all pre-existing RED-phase), 5 collection errors (pre-existing). No regressions from #213 (kanban-metadata-only task).
- ruff: N/A (no source code changes)

### Architect Quality
AC quality score: 4/5. All four AC lines were specific and verifiable. Minor gap: no explicit line for research doc creation, but context section covered it.

### Deduction breakdown
No deductions. All AC lines verified with evidence. No lint issues (no source). AC quality 4. Reviewer evidence present and detailed (.96). No in-scope test failures.

### Confidence: 1.00
### Action: archive

[[2026-03-30]] Mon 20:25
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2b5321c | docs | research doc + kanban tasks 210,211,213 | #213 |
