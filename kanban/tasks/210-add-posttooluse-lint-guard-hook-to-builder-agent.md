---
id: 210
title: Add postToolUse lint guard hook to builder agent (Phase 2)
status: backlog
priority: nice-to-have
created: 2026-03-30T08:52:17.140436+02:00
updated: 2026-04-01T20:38:06.5803024+02:00
tags:
    - phase-1
    - scope:agents
    - hooks
    - type:build
class: standard
---

## Context

See docs/research/agent-scoped-hooks-pipeline-enforcement.md §4 (Candidate 1) and §6 for full guidance.
See docs/research/hook-ac-command-execution-model.md for the AC correction rationale (#213).

Phase 2 of VS Code agent-scoped hooks adoption: add a `PostToolUse` lint guard to `builder.agent.md` that fires after file edits and runs ruff automatically. Monitor for context window inflation after deployment.

Depends on: #209 (Phase 1 must be deployed and settings opt-in confirmed)

## Acceptance Criteria

- [ ] Add `PostToolUse` hook to `agents/builder.agent.md` frontmatter: `type: command`, `command:` key pointing to `scripts/hooks/lint-changed.ps1`
- [ ] Script reads `tool_name` from stdin JSON; runs ruff only for file-edit tools (`create_file`, `replace_string_in_file`, `multi_replace_string_in_file`)
- [ ] On lint errors: returns `systemMessage` with ruff output (or blocks via exit code 2)
- [ ] On non-edit tools or clean lint: returns empty JSON `{}`
- [ ] `chat.useCustomAgentHooks` setting must already be enabled (prerequisite from #209)
- [ ] Hook YAML must not introduce duplicate keys or conflict with existing Stop hook from Phase 1
- [ ] Verify agent file parses with valid YAML frontmatter
