---
id: 422dddb3-59bc-4d28-9567-863367d886e8
title: Pre-commit validate-skills hook fails on unstaged uv.lock
categories:
- pitfall
- tool-usage
confidence: 0.9
state: curated
scope_agents:
- builder
- reviewer
- doc-writer
- auditor
source_agent: auditor
created_at: '2026-05-18T16:48:00.838166Z'
updated_at: '2026-05-18T17:32:18.658890Z'
approved_at: null
---

The "Validate Agent Skills" pre-commit hook (always_run: true) uses `uv run` which can touch `uv.lock`. When `uv.lock` is unstaged-modified, pre-commit's internal stash mechanism conflicts with the hook's file modifications, causing "Stashed changes conflicted with hook auto-fixes" and commit failure. Fix: stage `uv.lock` alongside your intended files before committing, or ensure `uv.lock` is clean before the commit attempt.
