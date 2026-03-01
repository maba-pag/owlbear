---
id: 338
title: Test ApprovalPolicy model — tool matching, arg patterns, wildcard, empty policy
status: archived
priority: needed
created: 2026-03-01T11:18:20.9001867+01:00
updated: 2026-03-01T17:10:07.9421384+01:00
started: 2026-03-01T11:21:09.7700847+01:00
completed: 2026-03-01T17:10:07.9421384+01:00
tags:
    - phase-12
    - agent
    - safety
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test ApprovalPolicy with rules list: each rule has tool_name (str) and optional arg_pattern (regex)
- [ ] Test requires_approval('git_push', {}) returns True when 'git_push' in rules
- [ ] Test requires_approval('read_file', {}) returns False when not in rules
- [ ] Test arg_pattern matching: rule {tool: 'run_command', arg_pattern: 'git push'} matches run_command with command='git push origin main'
- [ ] Test wildcard rule: {tool: '*'} matches all tool names
- [ ] Test empty policy: requires_approval always returns False
- [ ] Test ApprovalPolicy is a Pydantic BaseModel with JSON serialization

See docs/approval-gates-research.md S3.4, S3.5
