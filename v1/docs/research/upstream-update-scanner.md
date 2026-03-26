# Upstream Update Scanner — Monitor Inspiration Repos

> **Owning task:** #140 — Upstream update scanner — monitor inspiration repos for relevant changes
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear tracks ~20 inspiration repos in `docs/sources.md` (PydanticAI, kanban-md, Aider, LightRAG, etc.). Task #140 proposes building a daemon job that periodically polls these repos for new releases, uses LLM to judge relevance, and auto-creates kanban tasks.

**Key question:** Does the value of automated monitoring justify custom code, or are GitHub's built-in Watch features sufficient for a solo developer?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| GitHub Releases API | <https://docs.github.com/en/rest/releases/releases> | .95 | `GET /repos/{owner}/{repo}/releases/latest` — no auth needed for public repos, returns tag_name, body, published_at |
| GitHub Tags API | <https://docs.github.com/en/rest/repos/repos#list-repository-tags> | .85 | `GET /repos/{owner}/{repo}/tags` — list tags with commit SHA, no auth for public repos |
| GitHub Notifications docs | <https://docs.github.com/en/account-and-profile/managing-subscriptions-and-notifications-on-github/setting-up-notifications/about-notifications> | .90 | Watch repos with "Releases only" filter — email + inbox notifications, zero code |
| GitHub Atom feeds | <https://github.com/{owner}/{repo}/releases.atom> | .80 | RSS/Atom feed per repo for releases — standard feed reader compatible |
| OwlBear GitHubToolset | src/owlbear/tools/github_api.py | 1.0 | Existing httpx-based GitHub API client — 4 tools (create_pr, list_prs, list_issues, get_issue), no releases endpoint yet |
| OwlBear sources.md | docs/sources.md | 1.0 | ~20 unique GitHub repos tracked across 10 research tasks |

## 3. Analysis

### 3.1 What Would a Custom Scanner Require?

| Component | Effort | Dependencies |
|-----------|--------|-------------|
| Parse sources.md → extract repo URLs | ~30 LOC | Regex or markdown parser |
| Poll GitHub Releases API per repo | ~50 LOC | httpx (already in stack) |
| State storage (last-seen release per repo) | ~40 LOC | JSON file or SQLite |
| LLM relevance filter (changelog → relevance score) | ~60 LOC | Copilot LLM access, prompt engineering |
| Auto-create kanban tasks for relevant updates | ~30 LOC | kanban-md CLI |
| Cron/scheduler integration | ~20 LOC | Depends on #147 (someday, phase-12) |
| **Total** | **~230 LOC** | **#147 (cron scheduler, not built)** |

### 3.2 GitHub API Rate Limits for Polling

| Auth level | Rate limit | Repos per hour | Sufficient? |
|------------|-----------|----------------|-------------|
| Unauthenticated | 60 req/hr | 60 (all public) | Yes — 20 repos = 20 req, polled once daily = trivial |
| PAT (already have) | 5,000 req/hr | 5,000 | Vastly oversized |

All inspiration repos are public — no auth needed for reads.

### 3.3 Build vs. Use GitHub Watch

| Criterion | GitHub Watch (.90) | Custom Scanner (.35) | GitHub Watch + RSS (.80) |
|-----------|--------------------|---------------------|--------------------------|
| Setup effort | 10 min (click Watch > Releases on ~20 repos) | ~230 LOC + tests + cron dep | 10 min (add feeds to reader) |
| Maintenance burden | Zero | Ongoing (API changes, prompt tuning) | Zero |
| Notification channel | Email + GitHub inbox | Slack/CLI (via daemon) | Feed reader |
| Relevance filtering | Manual scan (~5 min/week) | LLM-automated | Manual |
| Kanban task creation | Manual (`kanban-md create`) | Automated | Manual |
| Dependencies | None | #147 cron scheduler (someday) | Feed reader app |
| KISS alignment | High | Low | High |
| YAGNI alignment | High | Low | High |

### 3.4 Quantifying the Time Savings

- **Repos monitored:** ~20
- **Avg releases per repo:** ~1-2/month (most are mature projects)
- **Expected new releases per week:** ~3-5 across all repos
- **Manual triage time:** ~1-2 min per release (read title + first paragraph of changelog)
- **Total manual effort:** ~5-10 min/week
- **Automated scanner saves:** ~5-10 min/week minus maintenance overhead

**Break-even analysis:** At ~230 LOC + tests (~460 LOC total), plus prompt engineering, plus ongoing maintenance — the scanner needs to run for **months** before it saves more time than it cost to build. And it can't run until #147 (cron scheduler) is built.

### 3.5 GitHub Watch: Step-by-Step Setup (Recommended)

1. Visit each repo in sources.md
2. Click **Watch** → **Custom** → check **Releases** only
3. GitHub sends notifications to inbox + email for every new release
4. Optionally: use `https://github.com/{owner}/{repo}/releases.atom` feeds in a reader

This takes ~10 minutes and provides ~90% of the value with zero code.

## 4. Recommendation (.90 confidence) — CLOSE

**Close task #140.** The cost-benefit analysis strongly favors GitHub's built-in Watch feature:

- Custom scanner violates **YAGNI** — we're building for a hypothetical future need
- Custom scanner violates **KISS** — 230+ LOC replacing 10 minutes of GitHub UI clicks
- Blocked on **#147** (cron scheduler, `someday` priority, phase-12) — can't run without it
- Saves ~5-10 min/week at the cost of significant engineering effort and maintenance
- A solo developer can manually triage ~5 release notifications per week trivially

**If revisited later** (after #147 exists and repo count grows to 50+), a minimal `list_releases` endpoint added to `GitHubToolset` would be the right first step — not a full scanner.

## 5. Follow-up Tasks

1. **Set up GitHub Watch for inspiration repos** — Manual, non-code task. Watch ~20 repos from sources.md with "Releases only" filter. (Not a kanban task — just do it.)

2. **Close #140** — Mark as closed with rationale link to this doc.

No implementation tasks recommended. The research conclusion is "don't build this."
