---
id: 549
title: Add hookSpecificOutput.additionalContext to lint-changed.ps1
status: archived
priority: medium
created: 2026-04-02 15:59:05.737478+02:00
updated: 2026-04-02 16:35:25.853836+02:00
started: 2026-04-02 16:35:25.853836+02:00
completed: 2026-04-02 16:35:25.853836+02:00
tags:
- scope:agents
- hooks
- type:build
depends_on:
- 210
class: standard
archival_reason: completed
archival_refs: []
---

## Context
See docs/research/posttooluse-additionalcontext-lint-feedback.md (task #547).
Empirical verification (#532) confirmed additionalContext reaches the builder model in subagent context. This task adds additionalContext output to lint-changed.ps1 alongside the existing systemMessage.

## Acceptance Criteria
- [ ] When ruff finds errors, lint-changed.ps1 returns both systemMessage and hookSpecificOutput.additionalContext containing the ruff output
- [ ] hookSpecificOutput includes hookEventName: PostToolUse
- [ ] Clean path (no errors) still returns empty JSON
- [ ] Never exits with code 2 (non-blocking)
- [ ] Builder model receives lint feedback in conversation context (verify via Chat Debug View)
- [ ] Existing systemMessage behavior preserved

## Implementation Notes
Output JSON structure: { systemMessage: ruff_output, hookSpecificOutput: { hookEventName: PostToolUse, additionalContext: ruff_output } }
Same ruff output for both fields (KISS). No truncation initially (YAGNI).

## Dependencies
Depends on #210 (lint-changed.ps1 must exist first).
