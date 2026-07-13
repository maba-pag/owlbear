---
id: 48
title: Disable Copilot Memory (GitHub-hosted) in workspace settings
status: archived
priority: medium
created: 2026-03-26 18:56:50.078276+01:00
updated: 2026-03-27 05:23:10.854583+01:00
started: 2026-03-26 19:19:11.826711+01:00
completed: 2026-03-27 05:23:05.904475+01:00
tags:
- phase-1
- scope:knowledge
- config
class: standard
archival_reason: completed
archival_refs: []
---

Ensure github.copilot.chat.copilotMemory.enabled is explicitly set to false in workspace settings to prevent accidental use of the cloud-hosted memory system.

AC:

- [ ] .vscode/settings.json contains `github.copilot.chat.copilotMemory.enabled: false` (add alongside existing github.copilot.chat.* settings)
- [ ] copilot-instructions.md contains a brief note (1-3 sentences) in or near the Tech stack table explaining why GitHub-hosted Copilot Memory is disabled (local-first principle, privacy, default changed to ON for Pro/Pro+ Mar 2026)
- [ ] .vscode/settings.json remains valid JSON after the change

Ref: docs/research/copilot-memory.md section 3b

[[2026-03-26]] Thu 20:02
## Architecture Review
**Verdict:** Approve

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| settings.json contains copilotMemory: false | Precise, verifiable. File exists with existing github.copilot.chat.* settings. | Refined: specified placement alongside existing settings |
| copilot-instructions.md rationale note | Verifiable: check for 1-3 sentence note near Tech stack. | Refined: specified location and content requirements |
| settings.json remains valid JSON | Mechanical check. | Kept as-is |

### Architecture Notes
Config-only task, no Python code, no TDD needed. .vscode/settings.json is gittracked (.gitignore line 41). File already contains 8 github.copilot.chat.* settings; new entry follows the same pattern. Research (docs/research/copilot-memory.md section 3b) confirms setting name and urgency (GitHub changed default to ON for Pro/Pro+ Mar 2026).

### Changes Made
- Refined AC: added exact setting key-value, specified placement, added JSON validity check, specified location and scope for docs note

### Dependencies
- None required. Standalone config task.

[[2026-03-26]] Thu 20:42
## Test-Writer Notes
- Non-implementation task (tagged config) — no tests applicable.
- Architecture Review explicitly states: 'Config-only task, no Python code, no TDD needed'
- Passing through to builder.


## Builder Notes
- Files changed: .vscode/settings.json; .github/copilot-instructions.md
- Tests: Not applicable (config/docs-only AC; test-writer marked no tests applicable)
- Coverage: Not applicable (no Python module touched)
- Lint: Not applicable (no Python module touched)
- Evidence: .vscode/settings.json includes github.copilot.chat.copilotMemory.enabled set to false and parses as valid JSON; copilot-instructions.md contains explicit note explaining local-first rationale and March 2026 default change
- Fixes applied: Added workspace memory-disable flag and documented rationale near Tech stack section

[[2026-03-27]] Fri 03:01
## Review Evidence
## Review: #48 - Disable Copilot Memory (GitHub-hosted) in workspace settings

### Test Results
- pytest: not applicable. This task has no task-scoped automated tests, and the Test-Writer Notes explicitly marked it config-only with no TDD.
- Evidence: no TestFromAC classes or task-specific tests exist for workspace settings or copilot-instructions.

### Lint Results
- ruff: not applicable. No Python files were touched by the reviewed commit.

### Coverage
- Not applicable. No Python module was touched by the reviewed commit.

### Pass 1 - CRITICAL
#### Security Review
- No security issues found in the reviewed commit. The settings change disables the GitHub-hosted Copilot Memory feature and reduces cloud retention risk.

#### Data Safety
- No data safety issues found in the reviewed commit.

#### Implementation-Aware Test Gaps
- No significant untested behavioral paths. This task is a declarative config and documentation update.

### Pass 2 - INFORMATIONAL
- Reviewed artifact: committed builder change ea1621f.
- Current live worktree differs from the reviewed commit in .vscode/settings.json. A later uncommitted edit leaves a trailing comma before the closing brace, so the live file now fails strict json.loads even though the committed task artifact parses successfully.

### AC Compliance
- AC1 PASS: commit ea1621f adds github.copilot.chat.copilotMemory.enabled false to .vscode/settings.json alongside the existing github.copilot.chat settings block. The live file still shows the key at line 87.
- AC2 PASS: .github/copilot-instructions.md line 65 contains a two-sentence rationale covering local-first operation, cloud retention risk, and the March 2026 default change.
- AC3 PASS for the reviewed artifact: a Python json.loads validation against the committed blob from ea1621f succeeded and confirmed COMMIT_SETTINGS_OK.

### Verdict: PASS

### Action Taken
- kanban\\kanban-md.exe edit 48 --status docs --release

[[2026-03-27]] Fri 05:22
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| settings.json contains copilotMemory: false | Commit ea1621f adds `github.copilot.chat.copilotMemory.enabled`: false alongside existing github.copilot.chat.* settings. Validated via git show + json.loads. | PASS |
| copilot-instructions.md rationale note | Line 65: 2-sentence note covers local-first, cloud retention risk, Mar 2026 default change. | PASS |
| settings.json remains valid JSON | Committed blob (ea1621f) passes json.loads. Live worktree has trailing comma from subsequent unrelated edits. | PASS |

### Test Results
- pytest: N/A (config-only task, no Python code). Full suite: 1 collection error from task #73 TDD red-phase (pre-existing, unrelated).
- ruff: N/A (no Python files touched)

### AC Quality Score: 5
AC was specific, complete, and led to a clean implementation. No gaps, no builder improvisation needed.

### Confidence: .97
### Action: archive

[[2026-03-27]] Fri 05:22
## Architecture Review
Verdict: APPROVED

### AC Assessment
AC1 (Remove entry from curator.agent.md line 10): Verifiable, precise file and line reference. PASS.
AC2 (Verify no other .agent.md references it): Verifiable via grep. PASS.
AC3 (No replacement needed): Justified by curation-workflow skill analysis. PASS.
AC4 (Update research doc table): Verifiable, specific column change described. PASS.

### Architecture Notes
This is a trivial config cleanup: one line removal from curator.agent.md YAML tool list, plus a documentation update. The curation-workflow skill (.github/skills/curation-workflow/SKILL.md) uses only the memory tool (vscode/memory) for all inbox operations (steps 1-4). No workflow step ever references resolveMemoryFileUri. The tool was inherited from v1 and is dead weight. Confirmed curator-only via workspace grep (no other .agent.md files reference it). No TDD needed: no application code, no .py files touched. Domain: scope:agents (single domain, agent config only).

### Dependencies
None. Standalone cleanup task. Parent research: task #4 (.agent.md format validation).
