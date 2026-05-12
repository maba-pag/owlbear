---
id: 977cbf76-066d-4fe4-b540-f9c92a64ea59
title: 'Reviewer: tracker skip tasks can pass on archived/completed dependency audit'
categories:
- process
- pitfall
confidence: 0.92
state: curated
scope_agents:
- reviewer
source_agent: reviewer
created_at: '2026-05-12T21:50:37.569695Z'
updated_at: '2026-05-12T22:17:48.581626Z'
approved_at: null
---

For parent/tracker tasks with `Proof bundle: skip` and AC that only requires child completion, live board evidence is the proof surface. If dependency tasks are archived with `archival_reason: completed`, that is sufficient pass evidence; do not rerun quality-runner unless builder evidence is inconsistent.
