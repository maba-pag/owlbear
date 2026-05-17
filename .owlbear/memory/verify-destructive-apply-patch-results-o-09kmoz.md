---
id: 1d52a313-61f4-4263-a7e8-ab062386dba1
title: Verify patch deletions and rewrites via status
categories:
- pitfall
- tool-usage
confidence: 0.84
state: deleted
scope_agents:
- builder
- doc-writer
- test-writer
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:33:59.975108Z'
updated_at: '2026-05-17T02:58:16.797244Z'
approved_at: null
---

After destructive or absence-sensitive `apply_patch` operations such as file deletes, delete/re-add rewrites, or mass removals, verify disk/index state with `git status`, `ls`, or `rg` before trusting a follow-up gate. Routine patch edits do not need a reread; use this when deletion or absence is the proof.
