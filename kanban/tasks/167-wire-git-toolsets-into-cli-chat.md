---
id: 167
title: Wire git toolsets into CLI chat
status: archived
priority: important
created: 2026-02-27T20:47:20.4456664+01:00
updated: 2026-02-28T23:53:19.7554237+01:00
started: 2026-02-27T21:55:10.4321713+01:00
completed: 2026-02-28T23:53:19.7554237+01:00
tags:
    - phase-8
    - tools
    - github
    - cli
depends_on:
    - 164
    - 166
class: standard
---

Integration task: add GitLocalToolset and GitHubToolset to the CLI chat REPL.

## AC

- [ ] In src/bearclaw/cli.py _chat_async():
      - Add GitLocalToolset(workspace_root, hooks=hooks) to toolsets list (always available)
      - If settings.github_token is set, add GitHubToolset(token, owner, repo, hooks=hooks)
      - Auto-detect owner/repo from git remote get-url origin if github_owner/github_repo not in config
- [ ] Test: mock settings to verify GitHubToolset added only when token present
- [ ] Test: verify GitLocalToolset always included
- [ ] ruff clean

## Architecture

- Follow existing pattern in _chat_async() for conditional toolset addition
- GitLocalToolset always available (local git needs no token)
- GitHubToolset conditional on github_token presence (mirrors Slack conditional pattern)

Depends on: #164 (GitLocalToolset impl), #166 (GitHubToolset impl)
