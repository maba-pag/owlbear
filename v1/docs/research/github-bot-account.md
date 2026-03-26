# GitHub Bot Account for OwlBear-Published Projects

> **Owning task:** #139 — GitHub bot account for OwlBear-published projects
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

Task #139 proposes a dedicated "owlbear-bot" GitHub account so that repos/PRs created by OwlBear are published under a separate identity from the user's personal and business accounts. OwlBear already has `GitHubToolset` (PAT-based, httpx) and `GitLocalToolset` (subprocess `git`), both using the user's configured identity.

**Core question:** Does a solo-developer, laptop-resident AI tool need a separate GitHub account for its published work, or is the existing PAT + git config approach sufficient?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| GitHub ToS §B.3 — Machine accounts | docs.github.com/en/site-policy/github-terms/github-terms-of-service#3-account-requirements | .95 | Machine user rules: 1 free machine account per person, human must accept ToS |
| GitHub — Managing deploy keys | docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys | .90 | Comparison: SSH agent, PATs, deploy keys, GitHub Apps, machine users |
| GitHub — Types of accounts | docs.github.com/en/get-started/learning-about-github/types-of-github-accounts | .80 | Personal, org, enterprise accounts; machine users are user accounts |
| GitHub — About GitHub Apps | docs.github.com/en/apps/creating-github-apps/about-creating-github-apps | .70 | GitHub Apps as first-class automation identity (server-to-server tokens) |
| Aider git integration | github.com/Aider-AI/aider (repo.py, commands.py) | .85 | Uses user's git config, prefixes commit messages with "aider:" |
| OwlBear GitHubToolset | src/owlbear/tools/github_api.py | 1.0 | Current PAT-based httpx implementation with 4 API tools |
| OwlBear GitLocalToolset | src/owlbear/tools/git_local.py | 1.0 | subprocess git, uses local git config user.name/email |
| OwlBear config | src/owlbear/config.py | 1.0 | `github_token`, `github_owner`, `github_repo` in OwlBearSettings |

## 3. Analysis

### 3.1 GitHub Identity Options for Automation

| Criterion | Personal PAT (.90) | Machine user account (.40) | GitHub App (.50) |
|-----------|--------------------|-----------------------------|-------------------|
| Setup complexity | None (already done) | Create new GH account, new email, new PAT | Register app, generate keys, manage install tokens |
| Accounts to manage | 1 (existing) | 2–3 (personal + business + bot) | 1 + app registration |
| Cost | Free (PAT on existing account) | Requires paid seat if >1 free account | Free for personal use |
| ToS compliance | Full | §B.3 allows 1 free machine account, but user already has 2 accounts | Full |
| Commit attribution | User's identity | Bot identity | `app[bot]` identity |
| KISS score | **High** | Low | Medium |
| Maintenance | Rotate 1 PAT | Rotate 2 PATs, manage 2 accounts | Manage JWT + installation tokens (1h expiry) |

### 3.2 How AI Coding Tools Handle Identity

| Tool | Identity model | Separate account? | Commit attribution |
|------|---------------|--------------------|--------------------|
| **Copilot** | User's own account | No | User's git config (suggestion engine, doesn't commit autonomously) |
| **Aider** | User's own git config | No | Commit message prefix "aider:", `Co-authored-by` optional |
| **Cursor** | User's IDE git setup | No | Defers entirely to IDE |
| **SWE-agent** | User's configuration | No | User's git config |
| **Devin** | GitHub App integration | Yes (as GH App, not user account) | `devin-ai-integration[bot]` — only because Devin is a SaaS product |

**Key insight:** Only Devin uses a separate identity, and it's a **SaaS product** serving many users — it *must* separate identities. Every laptop-resident / single-user tool uses the developer's own identity.

### 3.3 Commit Attribution Without a Separate Account

Git supports attribution metadata natively. For distinguishing AI-authored commits:

| Approach | Effort | Traceability | Example |
|----------|--------|--------------|---------|
| Commit message prefix | ~5 LOC | `git log --grep` | `owlbear: implement feature X` |
| `Co-authored-by` trailer | ~5 LOC | `git log --grep` | `Co-authored-by: OwlBear <owlbear@noreply>` |
| Custom git trailer | ~5 LOC | `git log --format` | `AI-assisted-by: OwlBear` |
| Separate branch convention | 0 LOC | Branch name filter | `owlbear/feature-x` |

All of these achieve traceability without a separate GitHub account. Aider's approach (commit message prefix) is the simplest and most widely adopted.

### 3.4 Risk Assessment

| Risk | Impact | Likelihood | If bot account | If PAT only |
|------|--------|------------|----------------|-------------|
| Confused commit attribution | Low | Medium | Mitigated | Mitigated via trailers |
| Account management overhead | Medium | Certain | **Yes — ongoing** | No |
| ToS complications (3 accounts) | Medium | Low | Possible (§B.3 limits) | None |
| PAT rotation burden | Low | Certain | **Doubled** | Single PAT |
| Blocked by missing feature | None | None | N/A | N/A |

## 4. Recommendation (.90 confidence) — Close Task #139

**Close** this task. A separate bot account is unnecessary for a solo-developer, laptop-resident tool.

**Rationale:**

1. **YAGNI** — No user has requested it, no feature requires it. OwlBear runs on *your* laptop, commits to *your* repos, under *your* authority. A separate identity solves a problem that doesn't exist for single-user tools.
2. **KISS** — Managing 3 GitHub accounts (personal + business Copilot + owlbear-bot) adds complexity. Every AI coding tool designed for individual use (Copilot, Aider, Cursor, SWE-agent) uses the user's own identity.
3. **ToS caution** — §B.3 allows "no more than one free machine account in addition to your free Personal Account." The user already has 2 accounts; a third may require a paid seat.
4. **Commit traceability** — Easily solved with commit message prefixes or `Co-authored-by` trailers (≤5 LOC change to `git_commit`), which is exactly what Aider does.

**If this need ever resurfaces** (e.g., OwlBear becomes multi-user or publishes to public repos on behalf of others), a **GitHub App** is the correct approach, not a machine user account. GitHub Apps are first-class automation citizens with scoped permissions and decoupled identity.

## 5. Follow-up Tasks

One small, actionable improvement that replaces the original task:

1. **Add OwlBear commit attribution to `git_commit`** — Append `Co-authored-by: OwlBear <owlbear@noreply>` trailer to commits made by the agent. ~5 LOC in `GitLocalToolset.git_commit`. This gives full traceability without a separate account. Priority: `nice-to-have`, tags: `github, tooling`.
