---
id: 210
title: Add postToolUse lint guard hook to builder agent (Phase 2)
status: in-progress
priority: nice-to-have
created: 2026-03-30T08:52:17.140436+02:00
updated: 2026-04-03T00:47:02.5431576+02:00
tags:
    - phase-1
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context

See docs/research/agent-scoped-hooks-pipeline-enforcement.md section 4 (Candidate 1) and section 6 for full guidance.
See docs/research/hook-ac-command-execution-model.md for the AC correction rationale (#213).
See docs/research/posttooluse-lint-guard-feasibility.md for feasibility analysis and empirical update (section 6).

Add a PostToolUse lint guard hook to builder.agent.md that fires after file edits and runs ruff automatically. Uses the command-execution model (type: command) with systemMessage as the user-facing output channel. Model-facing additionalContext is handled by follow-up #547. apply_patch tool_name support is handled by follow-up #546.

## Acceptance Criteria

- [ ] Add PostToolUse hook to agents/builder.agent.md frontmatter: type: command, command: key pointing to scripts/hooks/lint-changed.ps1
- [ ] Create scripts/hooks/lint-changed.ps1 that reads stdin JSON and extracts tool_name
- [ ] Script runs ruff only for file-edit tool_names: create_file, replace_string_in_file, multi_replace_string_in_file
- [ ] On lint errors: returns JSON with systemMessage containing ruff output (non-blocking design; script must never exit with code 2)
- [ ] On non-edit tools or clean lint: returns empty JSON {}
- [ ] All script output must be valid JSON (no plain text, no partial output)
- [ ] chat.useCustomAgentHooks: true already present at .vscode/settings.json (no action needed)
- [ ] No duplicate YAML keys in builder.agent.md frontmatter; file parses as valid YAML

[[2026-04-02]] Thu 23:29
## Architecture Review
**Verdict:** Approve
**DR Verification:** N/A -- not research-driven. Parent research #86 produced phased rollout plan; this is a T1 implementation task.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| PostToolUse hook in frontmatter | Clear, verifiable; type: command + script path | Kept |
| Create lint-changed.ps1 | Deliverable; testable via subprocess | Kept |
| Filter on 3 edit tool_names | Precise list matching VS Code tool names; apply_patch deferred to #546 | Tightened (removed stale exit code 2 option) |
| systemMessage with ruff output | User-facing output; model-facing additionalContext is #547 scope | Tightened (non-blocking constraint explicit) |
| Non-edit/clean returns {} | Verifiable via test | Kept |
| Valid JSON output | Verifiable via test | Added (was implicit) |
| useCustomAgentHooks present | Already at settings.json line 70; no action needed | Simplified (removed stale #209 reference) |
| No duplicate keys, valid YAML | Verifiable via test | Consolidated (was 2 lines) |

### Architecture Notes
- builder.agent.md has no hooks: section (clean addition, no conflict risk)
- scripts/hooks/ directory exists but is empty (first hook script in project)
- Follows VS Code command-execution hook model (3/25/2026 spec)
- Non-blocking design: systemMessage only, no exit code 2 (tests enforce this)
- apply_patch deferred to #546 (tool_input format unknown per docs/research/apply-patch-lint-guard-filter.md)
- additionalContext deferred to #547 (already at todo, depends on #210)
- Security: script reads stdin JSON from VS Code hook context (trusted), runs ruff on file paths (no user-input boundary)
- Note: phase-1 tag is stale (this was Phase 2 of hooks rollout; Phase 1 was invalidated). Tag editing not supported by kanban-md; planner should clean up.

### Changes Made
- Rewrote AC body: removed stale exit code 2 option (AC3), stale #209 prerequisite text (AC5), stale Phase 1 Stop hook reference (AC6)
- Added explicit valid-JSON criterion, consolidated YAML validation lines
- Updated context section with feasibility and empirical research references

### Dependencies
- No blockers (depends_on empty; #375 already cleared #209 dependency)
- #546 (apply_patch filter) depends on #210: correct ordering
- #547 (additionalContext output) depends on #210: correct ordering
- #548 (exit code 2 -File verification) is informational, not blocking

### Challenge Results
- Challenger: block (.35 confidence in original)
- Key challenges: C1 (AC not yet written), C2 (test-AC mismatch if switching to additionalContext), C5 (scope collision with #547), C6 (apply_patch format unknown)
- Architect response:
  - C1 ACCEPTED: AC written to body before approval (standard workflow)
  - C2 ACCEPTED: kept systemMessage design (existing tests remain valid)
  - C3 ACCEPTED: stale #209 reference cleaned up
  - C4 MOOT: not switching to additionalContext
  - C5 ACCEPTED: keeping systemMessage, #547 adds additionalContext later
  - C6 ACCEPTED: apply_patch stays in #546
  - Alternative angle ADOPTED: ship original systemMessage scope, iterate via #546/#547
- Confidence in original (revised): .85
