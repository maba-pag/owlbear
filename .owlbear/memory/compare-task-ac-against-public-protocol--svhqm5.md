---
id: 7d0eee72-f84e-49f6-a8e1-60dd4c662249
title: Compare task AC against public protocol before PASS
categories:
- process
- pitfall
confidence: 0.86
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-26T20:37:44.478965Z'
updated_at: '2026-05-26T23:03:00.293575Z'
approved_at: null
---

In review, compare frontmatter AC and task tests against the public protocol/contract docs. If green tests encode behavior that contradicts the protocol, route to backlog for AC/contract refinement instead of treating it as a builder-only defect.
