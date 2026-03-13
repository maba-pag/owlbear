# ClawFeed Research — Feed Curation and Data Ingestion Patterns

> **Owning task:** #591 — Research: kevinho/clawfeed
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear needs patterns for autonomous content ingestion, source management, and
structured summarization. ClawFeed is an AI-powered news digest tool (MIT, 1.6k
stars) that curates multi-source feeds into fixed-length summaries. It runs as an
OpenClaw/Zylos skill or standalone. **Question:** What architectural patterns,
prompt designs, or ingestion idioms can OwlBear adopt?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| kevinho/clawfeed (v0.8.1) | <https://github.com/kevinho/clawfeed> | .85 — direct analysis target |
| OpenClaw skill system | <https://github.com/openclaw/openclaw> | .70 — host framework, already in sources.md |
| ClawHub skill registry | <https://clawhub.ai/> | .50 — skill discovery/distribution model |

## 3. Analysis

### 3.1 Architecture Overview

ClawFeed is a Node.js (ESM) + SQLite (better-sqlite3) server with:

- **Source registry** — typed sources (`twitter_feed`, `rss`, `hackernews`, `reddit`,
  `github_trending`, `website`, `digest_feed`, `custom_api`) with per-type config JSON
- **raw_items pipeline** — decoupled fetch → dedup → store, with `dedup_key = source_id:url`
  and `INSERT OR IGNORE` on a UNIQUE constraint
- **Digest generation** — LLM prompt with curation rules + raw items → fixed-length output
- **Marks (bookmarks)** — URL + optional note, with "deep dive" AI analysis on demand
- **Source Packs** — sharable bundles of source subscriptions
- **Multi-frequency scheduling** — 4h / daily / weekly / monthly digest cadences

### 3.2 Patterns Comparison with OwlBear

| Pattern | ClawFeed | OwlBear (current) | Gap / Opportunity |
|---------|----------|-------------------|-------------------|
| Source types | 9 types (twitter, rss, hn, reddit, etc.) | 3 types (`url_list`, `crawl`, `file_glob`) | OwlBear lacks RSS/feed-native source types |
| Dedup | `source_id:url` UNIQUE constraint | `content_hash` on bookmarks | ClawFeed's approach is simpler and URL-first |
| Digest/summary | LLM prompt with curation rules template | None — raw chunks stored, no summarization | Major gap: OwlBear has no digest generation |
| Curation rules | Configurable markdown templates | None | Useful pattern: externalized prompt templates |
| Scheduling | Multi-frequency (4h/daily/weekly/monthly) | `RefreshOrchestrator` per-source refresh | OwlBear refreshes sources but doesn't schedule digests |
| Bookmarks + deep dive | Mark → AI deep analysis on demand | `BookmarkPipeline` with evaluation + ingest | Similar; OwlBear's is more sophisticated (scoring, auto-ingest) |
| Source packs | Bundle + share source sets | None | Not needed (YAGNI — single-user) |
| Feed output | RSS/JSON Feed per user | None | Not needed (YAGNI — OwlBear is not a SaaS) |

### 3.3 Reusable Patterns

**Pattern 1: Externalized Curation Rules as Markdown Templates (.75)**

ClawFeed stores curation rules and digest prompts as editable `.md` files in
`templates/`. The LLM prompt includes both the raw items and the rules template.
This separates *what to curate* (rules) from *how to generate* (prompt structure).

- **OwlBear fit:** Knowledge query context injection could benefit from configurable
  "relevance rules" templates — project-specific curation of what matters.
- **Complexity:** Low — just a config file path + template loading.

**Pattern 2: Typed Source Registry with Per-Type Config (.70)**

Each ClawFeed source has a `type` enum + `config` JSON blob. The collector
dispatches to type-specific fetchers. OwlBear's `SourceType` enum (`url_list`,
`crawl`, `file_glob`) follows the same pattern but with fewer types.

- **OwlBear fit:** Adding an `rss` source type to `KnowledgeSource` would let agents
  subscribe to RSS feeds and auto-ingest new articles. The existing
  `RefreshOrchestrator` already dispatches by type.
- **Complexity:** Medium — needs an RSS parser dependency (e.g., `feedparser`).

**Pattern 3: Fixed-Length Digest Generation (.65)**

ClawFeed's core insight: "Source count up → selection pool larger → output quality
higher → output length stays fixed." The digest prompt template enforces 8-12
items regardless of input volume.

- **OwlBear fit:** A "knowledge digest" tool could summarize recent ingested content
  into a fixed-length briefing for the developer. Useful for daily standup context.
- **Complexity:** Medium — needs a new agent tool + prompt template.

**Pattern 4: SKILL.md Convention for Agent Skill Discovery (.60)**

ClawFeed ships a `SKILL.md` that OpenClaw auto-detects. This is the same pattern
OwlBear already uses (`.github/skills/*/SKILL.md`). Validates our approach.

- **OwlBear fit:** Already implemented. No action needed.

**Pattern 5: Dedup via URL + Source Compound Key (.55)**

`UNIQUE(source_id, dedup_key)` with `INSERT OR IGNORE` — simple, database-level
dedup. OwlBear's `BookmarkStore` uses `UNIQUE(url, scope)` which is similar.

- **OwlBear fit:** Already implemented in BookmarkStore. No action needed.

## 4. Recommendation (.65 confidence)

ClawFeed is a well-structured feed curation tool, but its primary value
proposition (multi-source news digest for end users) doesn't directly map to
OwlBear's use case (AI dev system for a single developer). The overlap is in
**source management** and **prompt-template-driven summarization**.

**Adopt:**

- Externalized curation/prompt templates pattern (low effort, high flexibility)
- RSS source type concept for `KnowledgeSource` (medium effort, fills a real gap)

**Skip (YAGNI):**

- Source Packs, Feed output, multi-user subscription model — all SaaS features
- Multi-frequency digest scheduling — OwlBear agents work on-demand, not on cron
- Twitter/Reddit/HN fetchers — too specialized, OwlBear uses `web_read` generically

**Risk:** Adding RSS as a source type introduces a new dependency (`feedparser`)
and fetcher code for relatively niche value. The `url_list` source type with
periodic refresh already covers most use cases. Recommend only if the user
actively consumes RSS feeds.

## 5. Follow-up Tasks

Commands below for user review — **do not execute**.

```
kanban\kanban-md.exe create "Add RSS source type to KnowledgeSource" --priority nice-to-have --tags "scope:knowledge,config,phase-research" --body "Add `rss` variant to `SourceType` enum. Implement RSS fetcher in `RefreshOrchestrator` using `feedparser`. Each RSS item becomes a document ingested via `IngestPipeline`.\n\nSee docs/clawfeed-research.md Pattern 2.\n\nAC:\n- [ ] `SourceType.RSS` exists\n- [ ] `RefreshOrchestrator` handles `rss` type\n- [ ] New articles from RSS feed are ingested as documents\n- [ ] Dedup by URL prevents re-ingestion\n- [ ] Tests cover RSS refresh flow"

kanban\kanban-md.exe create "Externalized prompt templates for knowledge context" --priority nice-to-have --tags "scope:knowledge,config,phase-research" --body "Allow project-level prompt template files (e.g. `curation-rules.md`) that configure how knowledge context is injected into agent prompts. Inspired by ClawFeed's `templates/curation-rules.md` pattern.\n\nSee docs/clawfeed-research.md Pattern 1.\n\nAC:\n- [ ] Config field for prompt template path\n- [ ] Template loaded and injected into knowledge context\n- [ ] Default template works without configuration\n- [ ] Tests cover template loading and injection"
```
