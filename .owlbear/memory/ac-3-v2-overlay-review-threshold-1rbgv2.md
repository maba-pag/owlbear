---
id: 7768c506-8919-4cf1-ae49-e093bd5e3d89
title: AC-3-v2 overlay review threshold
categories:
- process
- pitfall
- domain-knowledge
confidence: 0.84
state: curated
scope_agents:
- reviewer
- auditor
- architect
source_agent: reviewer
created_at: '2026-05-15T21:58:46.625789Z'
updated_at: '2026-05-15T22:17:00.031674Z'
approved_at: null
---

In cockpit visual-remediation reviews under AC-3-v2, do not fail solely because overlay/dialog screenshots look raw or minimally styled. Treat that as an observation unless you can point to actual layout breakage, document overflow, in-flow parent expansion, or missing required PDS selectors. The refined contract narrowed review from aspirational polish to structural compliance.
