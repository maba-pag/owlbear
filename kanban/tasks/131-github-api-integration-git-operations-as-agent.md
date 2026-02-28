---
id: 131
title: GitHub API integration — git operations as agent tools
status: archived
priority: important
created: 2026-02-27T14:56:36.8403762+01:00
updated: 2026-02-27T20:47:47.1851956+01:00
started: 2026-02-27T20:30:20.1642678+01:00
completed: 2026-02-27T20:47:47.1851956+01:00
tags:
    - phase-8
    - tools
    - github
class: standard
---

Agents need to commit, push, create branches, and open PRs. Git CLI for local ops, GitHub API for remote.

## AC
- [ ] New file: src/owlbear/tools/github.py
- [ ] GitToolset(FunctionToolset) with tools: git_status, git_diff, git_add, git_commit, git_push, git_branch
- [ ] GitHub API tools: create_pr, list_prs (via httpx, not a heavy SDK)
- [ ] Auth: fine-grained PAT stored in config (OWLBEAR_GITHUB_TOKEN)
- [ ] git_commit requires human approval gate (CommandGuard or ask_user)
- [ ] git_push requires human approval gate
- [ ] Tests: mock subprocess for git commands, mock httpx for API calls
- [ ] ruff clean
