---
id: 211
title: Add preToolUse read-only guard hook to reviewer agent (Phase 2, defense-in-depth)
status: ideation
priority: nice-to-have
created: 2026-03-30T08:52:23.636729+02:00
updated: 2026-03-30T08:52:23.636729+02:00
tags:
    - phase-1
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 209
class: standard
---

## Context

See docs/research/agent-scoped-hooks-pipeline-enforcement.md §4 (Candidate 5) and §6 for full guidance.
See docs/research/hook-ac-command-execution-model.md for the AC correction rationale (#213).

Defense-in-depth: adds a `PreToolUse` hook to the reviewer agent as a secondary guard against accidental edits, complementing the existing `tools:` restriction in the frontmatter.

Depends on: #209 (Phase 1 must be deployed and settings opt-in confirmed)

## Acceptance Criteria

- [ ] Add `PreToolUse` hook to `agents/reviewer.agent.md` frontmatter: `type: command`, `command:` key pointing to `scripts/hooks/deny-writes.ps1`
- [ ] Script reads `tool_name` from stdin JSON; filters for write tools (`create_file`, `replace_string_in_file`, `multi_replace_string_in_file`)
- [ ] On write tool match: returns `hookSpecificOutput` with `permissionDecision: "deny"` and `permissionDecisionReason` explaining reviewer is read-only
- [ ] On non-write tools: returns empty JSON `{}`
- [ ] `chat.useCustomAgentHooks` setting must already be enabled (prerequisite from #209)
- [ ] Hook must not conflict with existing `tools:` restrictions in `reviewer.agent.md`
- [ ] Verify agent file parses with valid YAML frontmatter
