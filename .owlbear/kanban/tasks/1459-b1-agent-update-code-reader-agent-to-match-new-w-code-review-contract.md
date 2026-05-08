---
id: 1459
title: 'B1-agent: Update code-reader agent to match new w-code-review contract'
status: backlog
priority: needed
created: 2026-05-08T19:47:13.556859+00:00
updated: 2026-05-08T19:47:45.946847+00:00
tags:
- pipeline
- ws-reviewer
- scope:agents
parent: 1403
depends_on:
- 1458
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Update `share/agents/code-reader.agent.md` to align with the new w-code-review consumer contract. The 8-section output (test_writer-audit, security_review, test_integrity, test_quality, data_safety, test_gaps, necessity_check, informational) is replaced by the 3-item checklist model. Update persona, critical_rules, output_format, and examples.