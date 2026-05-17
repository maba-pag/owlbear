---
id: ab8beaa7-1127-4710-b330-674a46fda814
title: Use rg files-without-match, not -L
categories:
- pitfall
- tool-usage
confidence: 0.8
state: deleted
scope_agents:
- builder
- reviewer
- test-writer
- doc-writer
source_agent: copilot
created_at: '2026-05-17T01:35:07.908931Z'
updated_at: '2026-05-17T03:29:07.394642Z'
approved_at: null
---

In ripgrep, `-L` means follow symlinks, not files-without-match. When checking which files lack a required string, use `rg --files-without-match PATTERN paths...` instead of `rg -L`.
