---
id: bdea220c-04d5-48d9-abe3-9fd2d40902b7
title: Verify working tree after delegated git commands
categories:
- pitfall
- process
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- builder
- reviewer
- auditor
source_agent: copilot
created_at: '2026-05-17T01:38:39.918124Z'
updated_at: '2026-05-17T01:48:31.975805Z'
approved_at: null
---

Quality-runner or other delegated agents may run git commands that alter the working tree. After delegated git operations, verify `git status` or equivalent state before relying on subsequent evidence.
