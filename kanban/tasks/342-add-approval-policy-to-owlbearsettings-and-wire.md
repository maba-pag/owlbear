---
id: 342
title: Add approval_policy to OwlBearSettings and wire ApprovalGateToolset into bootstrap
status: archived
priority: needed
created: 2026-03-01T11:19:03.244521+01:00
updated: 2026-03-01T17:10:11.2204695+01:00
started: 2026-03-01T11:21:47.1075673+01:00
completed: 2026-03-01T17:10:11.2204695+01:00
tags:
    - phase-12
    - agent
    - safety
    - config
depends_on:
    - 341
class: standard
---

## Acceptance Criteria
- [ ] Add approval_policy field to OwlBearSettings: list of ApprovalRule dicts, default rules for git_push, create_pr, deploy
- [ ] Add approval_timeout to OwlBearSettings: float = 120.0
- [ ] build_toolsets() wraps destructive toolsets (GitLocalToolset, TerminalToolset, GitHubToolset) in ApprovalGateToolset
- [ ] Wrapping order: inner toolset -> HookedToolset -> ApprovalGateToolset
- [ ] Non-destructive toolsets (FileToolset, AskUserToolset, BrowserToolset) skip approval wrapping
- [ ] One shared ApprovalSession per bootstrap call (session scope = daemon turn)
- [ ] Integration test: bootstrap creates approval-wrapped toolsets when policy is non-empty
- [ ] When approval_policy is empty: no ApprovalGateToolset wrapping (transparent)

See docs/research/approval-gates.md S3.5, S4
