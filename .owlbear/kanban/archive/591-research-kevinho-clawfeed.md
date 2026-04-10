---
id: 591
title: 'Research: kevinho/clawfeed'
status: archived
priority: important
created: 2026-03-05T23:51:21.2505416+01:00
updated: 2026-03-07T18:08:12.0488404+01:00
started: 2026-03-06T21:26:14.428145+01:00
completed: 2026-03-07T18:08:12.0488404+01:00
tags:
    - research
    - phase-research
    - scope:agent
parent: 581
class: standard
---

**Source:** https://github.com/kevinho/clawfeed
Analyze for agent autonomy, feed processing, and data ingestion patterns.

**Research:** See docs/research/clawfeed.md

**Findings:**
- ClawFeed is a Node.js + SQLite AI news digest (MIT, 1.6k stars)
- Typed source registry (9 types) with per-type config JSON dispatched to fetchers
- Externalized curation rules as markdown prompt templates
- raw_items dedup pipeline via UNIQUE(source_id, dedup_key) + INSERT OR IGNORE
- Fixed-length digest generation (input grows, output stays constant)
- SKILL.md convention for OpenClaw agent skill discovery (validates our approach)
- Bookmark deep-dive = Mark + AI analysis on demand (similar to our BookmarkPipeline)

**Adopted patterns:**
1. Externalized prompt templates for curation rules (low effort)
2. RSS source type concept for KnowledgeSource (medium effort)

**Skipped (YAGNI):** Source Packs, Feed output, multi-user subscriptions, multi-frequency scheduling, platform-specific fetchers

**Follow-up tasks:** 2 kanban create commands in docs/research/clawfeed.md section 5
