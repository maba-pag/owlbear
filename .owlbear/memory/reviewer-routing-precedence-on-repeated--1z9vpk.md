---
id: 1e9d98e7-d2e0-4958-8df4-deec8b73157b
title: Reviewer routing precedence on repeated review failures
categories:
- process
- pitfall
confidence: 0.85
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-13T04:57:49.076845Z'
updated_at: '2026-05-13T05:59:37.792502Z'
approved_at: null
---

In reviewer mode, use the mode-specific routing (pipeline_position + w-code-review) when repeated review cycles conflict with generic r-pipeline-protocol thresholds. Mode-specific skill routing takes precedence: w-code-review supports sending to backlog on a second review-cycle proof failure even when the generic protocol text suggests architect discretion through cycle 2. When in doubt, defer to the active skill's routing over the general pipeline text.
