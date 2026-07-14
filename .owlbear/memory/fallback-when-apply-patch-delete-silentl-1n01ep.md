---
approved_at: null
categories: [tool-usage, pitfall]
confidence: 0.83
contested_by_task: null
created_at: '2026-05-26T04:42:22.559799Z'
didnt_use_count: 0
id: b99d722c-25e0-4891-a924-07fd71b7c4df
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Fallback when apply_patch delete silently doesn't remove files
unremarkable_count: 0
updated_at: '2026-07-14T22:46:36.630533+00:00'
---

In owlbear-dev, apply_patch Delete File may report success while files still exist unchanged; verify with ls/git status and use direct rm fallback when repeated delete patches fail.
