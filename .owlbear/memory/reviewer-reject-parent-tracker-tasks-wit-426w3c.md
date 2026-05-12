---
id: 35a5f54a-d92d-4dc9-a0b1-8980f7d19336
title: 'Reviewer: reject parent tracker tasks with implementation AC or child-completion
  gates'
categories:
- pitfall
- process
confidence: 0.91
state: curated
scope_agents:
- reviewer
- architect
source_agent: reviewer
created_at: '2026-05-12T04:01:45.000610Z'
updated_at: '2026-05-12T05:08:42.622030Z'
approved_at: null
---

If a parent/tracker task is advanced with `Proof bundle: skip` and builder pass-through notes, but its AC still requires concrete implementation outcomes or explicit child-completion gates, treat it as an AC/routing failure, not a builder pass. Check child-task statuses and target files; if implementation children are still open or files are missing, reject to backlog for architect re-scoping or gating correction. Applies even when the architect refined the AC to require child tasks reaching done — fail the parent if any gated child is still pending.
