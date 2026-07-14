---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.9
contested_by_task: null
created_at: '2026-05-18T16:48:00.838166Z'
didnt_use_count: 2
id: 422dddb3-59bc-4d28-9567-863367d886e8
outstanding_count: 0
scope_agents: [builder, verifier, collector]
score: 0.9
source_agent: auditor
state: curated
title: Pre-commit validate-skills hook fails on unstaged uv.lock
unremarkable_count: 0
updated_at: '2026-07-14T10:48:05.133685+00:00'
---

The "Validate Agent Skills" pre-commit hook (always_run: true) uses `uv run` which can touch `uv.lock`. When `uv.lock` is unstaged-modified, pre-commit's internal stash mechanism conflicts with the hook's file modifications, causing "Stashed changes conflicted with hook auto-fixes" and commit failure. Fix: stage `uv.lock` alongside your intended files before committing, or ensure `uv.lock` is clean before the commit attempt.
