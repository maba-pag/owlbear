---
id: 897
title: 'Update agent.md command: fields to uv run python'
status: research
priority: needed
created: 2026-04-16T22:54:12.431883+00:00
updated: 2026-04-16T22:54:12.431883+00:00
tags:
- phase-2
- scope:agent
- config
- platform
parent: 890
depends_on:
- 894
- 895
- 896
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] All 19+ agent.md files in share/agents/ updated
- [ ] Every `command:` field changed from `powershell -NoProfile -NonInteractive -File .owlbear/hooks/{name}.ps1` to `uv run python .owlbear/hooks/{name}.py`
- [ ] Hook type mappings preserved (PreToolUse, PostToolUse, SessionStart unchanged)
- [ ] Agent-to-hook mappings preserved exactly (see research findings for full mapping table)
- [ ] No .ps1 references remain in any agent.md file
- [ ] grep -r "powershell" share/agents/ returns no results
- [ ] grep -r ".ps1" share/agents/ returns no results

## Agent-Hook Mapping (reference)
architect: PreToolUse deny-code-writes | auditor: PreToolUse deny-writes | builder: SessionStart session-context, PostToolUse lint-changed | challenger: PreToolUse deny-writes | code-reader: PreToolUse deny-writes | doc-writer: SessionStart session-context, PreToolUse deny-code-writes | fix-attempt: PostToolUse lint-changed | ideation-architect: PreToolUse allow-stances-only | ideation-critic: PreToolUse deny-writes | ideation-data: PreToolUse allow-stances-only | ideation-enduser: PreToolUse allow-stances-only | ideation-security: PreToolUse allow-stances-only | quality-runner: PreToolUse deny-writes | researcher: PreToolUse deny-code-writes | reviewer: PreToolUse deny-writes | test-writer: SessionStart session-context, PreToolUse deny-src-writes

## Files
- `share/agents/*.agent.md` (19+ files, edit)