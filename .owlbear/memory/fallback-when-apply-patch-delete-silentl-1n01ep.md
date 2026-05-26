---
id: b99d722c-25e0-4891-a924-07fd71b7c4df
title: Fallback when apply_patch delete silently doesn't remove files
categories:
- tool-usage
- pitfall
confidence: 0.83
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T04:42:22.559799Z'
updated_at: '2026-05-26T05:13:56.971860Z'
approved_at: null
---

In owlbear-dev, apply_patch Delete File may report success while files still exist unchanged; verify with ls/git status and use direct rm fallback when repeated delete patches fail.
