---
id: fc926d6f-b9fd-4293-8f3b-1bc84bb6f138
title: 'Reviewer: substring-only version assertions can miss semver extraction bugs'
categories:
- pitfall
- process
- tool-usage
confidence: 0.89
state: curated
scope_agents:
- reviewer
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-12T21:47:19.679403Z'
updated_at: '2026-05-12T22:17:45.149131Z'
approved_at: null
---

In Cockpit/Vite plugin tests, asserting only that warning text contains version substrings can falsely prove ACs about semver extraction. A regression from extracted semver to raw filename can still pass if the filename embeds the same version text. For ACs that require extraction, require assertions that distinguish the extracted token from the full filename or otherwise falsify raw-filename output.
