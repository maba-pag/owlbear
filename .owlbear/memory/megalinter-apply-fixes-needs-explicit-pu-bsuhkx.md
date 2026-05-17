---
id: 4bd7cdf0-17b4-4933-a4b1-2b066dfb5395
title: MegaLinter APPLY_FIXES needs explicit push path
categories:
- pitfall
- tool-usage
confidence: 0.8
state: deleted
scope_agents:
- builder
- reviewer
source_agent: copilot
created_at: '2026-05-17T01:34:26.426162Z'
updated_at: '2026-05-17T03:09:54.873403Z'
approved_at: null
---

MegaLinter `APPLY_FIXES` can update files without completing the GitHub-side push. Use an upstream-template pattern with checkout token support plus explicit commit or PR steps when relying on automated fixes.
