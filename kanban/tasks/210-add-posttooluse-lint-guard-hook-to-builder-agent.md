---
id: 210
title: Add postToolUse lint guard hook to builder agent (Phase 2)
status: ideation
priority: nice-to-have
created: 2026-03-30T08:52:17.140436+02:00
updated: 2026-03-30T08:52:17.140436+02:00
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

See docs/research/agent-scoped-hooks-pipeline-enforcement.md §4 (Candidate 1) and §6 for full guidance.

Phase 2 of VS Code agent-scoped hooks adoption: add a `postToolUse` lint guard to `builder.agent.md` that fires after file edits with a reminder to run ruff. Monitor for context window inflation after deployment.

Depends on: #209 (Phase 1 must be deployed and settings opt-in confirmed)

## Acceptance Criteria

- [ ] Add `postToolUse` hook to `agents/builder.agent.md` frontmatter, gated on `tool == 'edit/editFiles' || tool == 'edit/createFile'`, injecting a prompt to run `uv run ruff check` on modified files.
- [ ] `chat.useCustomAgentHooks` setting must already be enabled (prerequisite from #209).
- [ ] The hook YAML must not introduce duplicate keys or conflict with any existing `stop` hook from Phase 1.
- [ ] Verify agent file parses with valid YAML frontmatter.
