# GitHub API Integration — Git Operations as Agent Tools

> **Owning task:** #131 — GitHub API integration — git operations as agent tools
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear agents need git operations as tools: create branches, commit, push, open PRs, read issues. The project already has Copilot OAuth authentication (`src/owlbear/auth/copilot.py`). Key questions: what libraries to use, can the existing Copilot token work for GitHub API, and how to structure the toolsets.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PyGitHub | github.com/PyGithub/PyGithub | .70 | Typed GitHub REST API client, 7.7k stars, LGPL-3.0, 393 contributors |
| ghapi (AnswerDotAI) | github.com/AnswerDotAI/ghapi | .75 | Auto-generated from OpenAPI spec, 35kB, Apache-2.0, always up-to-date |
| GitPython | pypi.org/project/GitPython | .60 | Local git ops, maintenance mode, warns against daemon use (resource leaks) |
| Aider repo.py | github.com/Aider-AI/aider/blob/main/aider/repo.py | .90 | GitPython for local ops, auto-commit pattern, diff generation, attribution |
| Aider commands.py | github.com/Aider-AI/aider/blob/main/aider/commands.py | .85 | /commit, /undo, /diff, /git passthrough commands |
| GitHub OAuth scopes | docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps | .95 | `repo` scope required for private repos, `read:user` insufficient |
| GitHub App permissions | docs.github.com/en/rest/overview/permissions-required-for-github-apps | .80 | Contents, Pull requests, Issues permission sets |
| OwlBear copilot.py | src/owlbear/auth/copilot.py | 1.0 | Current OAuth flow requests `scope: read:user` only |

## 3. Analysis

### 3.1 Authentication: Can Copilot OAuth Token Access GitHub API?

**No.** Critical finding with high confidence (.95):

The Copilot OAuth flow in `copilot.py` requests `scope=read:user`. This token is then exchanged for a Copilot-specific session token via `/copilot_internal/v2/token`. The resulting Copilot token:

- Is scoped to `api.individual.githubcopilot.com` (LLM completions only)
- Has no `repo`, `pull_request`, or `issues` permissions
- Cannot authenticate against `api.github.com`

**Options for GitHub API auth:**

| Option | Complexity | Scope control | UX |
|--------|-----------|---------------|-----|
| Fine-grained PAT (env var) | Low | Per-repo, fine-grained | User creates token manually |
| Classic PAT (env var) | Low | Coarse (`repo` scope) | User creates token manually |
| Expand OAuth device flow | Medium | Request `repo` scope | Reuse device flow, but different client ID needed |
| GitHub CLI (`gh auth token`) | Low | Reuse existing auth | User must have `gh` installed |

**Recommendation (.85):** Fine-grained PAT stored as `OWLBEAR_GITHUB_TOKEN` in config. Simplest, most explicit, aligns with KISS. The existing AC already specifies this approach.

### 3.2 Python Libraries for GitHub API

| Criterion | PyGitHub (.65) | ghapi (.70) | httpx direct (.85) |
|-----------|---------------|-------------|---------------------|
| Dependency count | 3 (requests, urllib3, etc.) | 2 (fastcore, packaging) | 0 (already in stack) |
| API coverage | Full REST API | Full REST API (auto-gen) | Manual per-endpoint |
| Type hints | Good (typed stubs) | Partial | Full control |
| License | LGPL-3.0 | Apache-2.0 | N/A |
| Maintenance | Active (393 contributors) | Active (AnswerDotAI) | N/A |
| KISS score | Medium | Medium | High |
| Disc footprint | ~2MB | ~500KB | 0 |

**Recommendation (.85):** httpx direct. OwlBear already depends on httpx. For the 3–5 GitHub API endpoints we need (create PR, list PRs, list issues), writing thin async functions over `httpx.AsyncClient` is simpler than adding a full SDK. This matches YAGNI — we need ~5 endpoints, not all 800+. If API coverage needs grow later, ghapi is the upgrade path.

### 3.3 Local Git Operations

| Criterion | GitPython (.50) | subprocess git (.90) | asyncio.create_subprocess (.85) |
|-----------|-----------------|----------------------|----------------------------------|
| Dependency | New (gitpython + gitdb + smmap) | 0 | 0 |
| Daemon-safe | **No** — docs explicitly warn against daemons (resource leaks via `__del__`) | Yes | Yes |
| API ergonomics | Pythonic objects | String output parsing | String output parsing |
| Testing | Mock complex objects | Mock subprocess | Mock subprocess |
| Aider pattern | Uses GitPython | N/A | N/A |

**Recommendation (.90):** subprocess via `asyncio.create_subprocess_exec`. GitPython explicitly warns against use in long-running processes (daemons), which is exactly what OwlBear is. Subprocess is zero-dependency, daemon-safe, and OwlBear already has the `TerminalToolset` pattern for subprocess execution. Git CLI output is well-structured and parseable.

### 3.4 How Other AI Agents Handle Git

| Agent | Local git | GitHub API | Commit strategy | Approval gates |
|-------|-----------|-----------|-----------------|----------------|
| **Aider** | GitPython (commit, diff, undo) | None — no PR/issue support | Auto-commit per edit, LLM-generated messages | None (user can undo) |
| **SWE-agent** | subprocess git | GitHub API for issue/PR reading | Explicit commit at end | Explicit submission step |
| **Devin** | Proprietary | PR creation, branch management | Auto-branch + auto-PR | Human review before merge |
| **Cursor** | IDE git integration | None | Defers to IDE | IDE prompts |

Key patterns adopted from Aider (highest relevance):

- LLM-generated commit messages from diffs
- Auto-add changed files before commit
- Undo support (reset to pre-commit state)
- Passthrough `/git` command for arbitrary git operations

### 3.5 Toolset Architecture

| Option | Description | KISS score |
|--------|-------------|------------|
| Single `GitToolset` | All 10+ tools in one class | Low — mixes concerns |
| Split: `GitLocalToolset` + `GitHubToolset` | Local in one, remote API in another | **High** — clean separation |
| Use `TerminalToolset` directly | No new toolset, agents run `git` via `run_command` | Medium — no type safety, no approval gates |

**Recommendation (.85):** Two separate toolsets:

- **`GitLocalToolset(FunctionToolset)`** — `git_status`, `git_diff`, `git_add`, `git_commit`, `git_branch`, `git_log`, `git_push`
- **`GitHubToolset(FunctionToolset)`** — `create_pr`, `list_prs`, `list_issues`, `get_issue`

Rationale: different auth (local needs no token; GitHub needs PAT), different failure modes, different approval needs. An agent that only needs to read issues shouldn't get commit tools.

### 3.6 Minimal Viable Toolset

**Local git tools (subprocess):**

| Tool | Approval | Description |
|------|----------|-------------|
| `git_status` | No | `git status --porcelain` |
| `git_diff` | No | `git diff [--staged] [path]` |
| `git_add` | No | `git add <paths>` |
| `git_commit` | **Yes** | `git commit -m <message>` |
| `git_branch` | No | `git branch <name>` / `git checkout -b <name>` |
| `git_log` | No | `git log --oneline -n <count>` |
| `git_push` | **Yes** | `git push [--set-upstream origin <branch>]` |

**GitHub API tools (httpx):**

| Tool | Approval | Endpoint |
|------|----------|----------|
| `create_pr` | **Yes** | `POST /repos/{owner}/{repo}/pulls` |
| `list_prs` | No | `GET /repos/{owner}/{repo}/pulls` |
| `list_issues` | No | `GET /repos/{owner}/{repo}/issues` |
| `get_issue` | No | `GET /repos/{owner}/{repo}/issues/{number}` |

## 4. Recommendation (.85 confidence)

1. **Auth:** Add `OWLBEAR_GITHUB_TOKEN: SecretStr | None` to `OwlBearSettings`. Fine-grained PAT, not Copilot token.
2. **Local git:** subprocess via `asyncio.create_subprocess_exec`, NOT GitPython (daemon-unsafe).
3. **GitHub API:** httpx direct against `api.github.com`, NOT a full SDK (YAGNI).
4. **Architecture:** Two toolsets — `GitLocalToolset` + `GitHubToolset`, following existing `FunctionToolset` pattern.
5. **Safety:** `git_commit`, `git_push`, and `create_pr` require approval via `HookEvent.PRE_TOOL_USE` + `CommandGuard` (extend blocked patterns) or `ask_user`.
6. **Config:** Owner/repo auto-detected from `git remote get-url origin` (parsed), with `OWLBEAR_GITHUB_OWNER` / `OWLBEAR_GITHUB_REPO` overrides.

Risk: subprocess git parsing is fragile if git locale changes output format.
Mitigation: use `--porcelain` / `--format` flags for machine-readable output (~10 LOC per tool).

## 5. Follow-up Tasks

1. **Add `OWLBEAR_GITHUB_TOKEN` to config** — Add `github_token: SecretStr | None` and `github_owner`/`github_repo` optional fields to `OwlBearSettings`.
2. **Implement `GitLocalToolset`** — `FunctionToolset` with 7 tools (status, diff, add, commit, branch, log, push) using subprocess. Commit/push require approval gate.
3. **Implement `GitHubToolset`** — `FunctionToolset` with 4 tools (create_pr, list_prs, list_issues, get_issue) using httpx + PAT auth.
4. **Extend `CommandGuard`** — Add `git_commit`, `git_push`, `create_pr` to approval-required tool list.
5. **Wire toolsets into CLI** — Add `GitLocalToolset` and optionally `GitHubToolset` (when token present) to `_chat_async` in `bearclaw/cli.py`.
6. **Tests** — Mock subprocess for git commands, mock httpx for API calls, test approval gates.
