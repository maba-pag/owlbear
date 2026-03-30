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

See docs/research/agent-scoped-hooks-pipeline-enforcement.md §4 (Candidate 5) and §6 for full guidance. Defense-in-depth: adds a `preToolUse` hook to the reviewer agent as a secondary guard against accidental edits, complementing the existing `tools:` restriction in the frontmatter.

Depends on: #209 (Phase 1 must be deployed and settings opt-in confirmed)

## Acceptance Criteria

- [ ] Add `preToolUse` hook to `agents/reviewer.agent.md` frontmatter, gated on `tool == 'edit/editFiles' || tool == 'edit/createFile'`, injecting a stop-and-return reminder that the reviewer is read-only.
- [ ] `chat.useCustomAgentHooks` setting must already be enabled (prerequisite from #209).
- [ ] The hook must not conflict with existing `tools:` restrictions in `reviewer.agent.md`.
- [ ] Verify agent file parses with valid YAML frontmatter.
