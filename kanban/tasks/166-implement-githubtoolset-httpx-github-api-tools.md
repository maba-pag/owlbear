---
id: 166
title: Implement GitHubToolset — httpx GitHub API tools + config
status: archived
priority: important
created: 2026-02-27T20:47:09.5181486+01:00
updated: 2026-02-28T23:53:19.1506385+01:00
started: 2026-02-27T21:46:29.605143+01:00
completed: 2026-02-28T23:53:19.1506385+01:00
tags:
    - phase-8
    - tools
    - github
    - config
depends_on:
    - 165
class: standard
---

FunctionToolset wrapping 4 GitHub REST API operations via httpx.AsyncClient.

## AC
- [ ] File: src/owlbear/tools/github_api.py
- [ ] GitHubToolset(FunctionToolset) using httpx.AsyncClient against api.github.com
- [ ] Constructor: token: SecretStr, owner: str, repo: str, hooks: HookRegistry | None = None
- [ ] 4 tools registered via add_function():
      - create_pr: POST /repos/{owner}/{repo}/pulls (title, head, base, body). Emits PRE_TOOL_USE hook.
      - list_prs: GET /repos/{owner}/{repo}/pulls (state param, default 'open')
      - list_issues: GET /repos/{owner}/{repo}/issues (state param, default 'open')
      - get_issue: GET /repos/{owner}/{repo}/issues/{number}
- [ ] Auth: Authorization: Bearer {token} header on all requests
- [ ] Add to OwlBearSettings (src/owlbear/config.py):
      - github_token: SecretStr | None = None
      - github_owner: str | None = None
      - github_repo: str | None = None
- [ ] create_pr emits HookEvent.PRE_TOOL_USE before API call
- [ ] Helper: _parse_git_remote(url: str) -> tuple[str, str] to extract owner/repo from git remote URL
- [ ] All tests from #165 pass
- [ ] ruff clean

## Architecture
- httpx is already in the dependency tree (zero new deps)
- YAGNI: only 4 endpoints, not a full SDK. ghapi is the upgrade path if needed later.
- Note: phase-10 MCP research (#137) identified GitHub MCP server as alternative — evaluate overlap when MCP infrastructure is built
- PAT auth (not Copilot OAuth — Copilot token has read:user scope only, cannot access GitHub API)
