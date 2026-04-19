---
id: 939
title: 'P3-03: Docs — engine surface + future-surface contract + hello-world walkthrough'
status: research
priority: important
created: 2026-04-17T19:59:26.751674+00:00
updated: 2026-04-17T19:59:26.751674+00:00
tags:
- cockpit
- docs
- phase-3
- type:docs
parent: 920
depends_on:
- 937
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Document the cockpit's engine surface (allowlist), extensibility contract, and a hello-world second-surface walkthrough (O4a, O7).

## Acceptance Criteria

- [ ] Documentation at `serve/cockpit/README.md`
- [ ] Lists all engine methods used by the cockpit adapter (the allowlist) and explains why others are excluded (D12)
- [ ] Documents the shell-to-surface contract: route registration, component structure, optional nav-rail entry, adapter usage pattern
- [ ] Hello-world walkthrough: step-by-step to add a second surface (route + component + nav icon) with no shell layout changes required
- [ ] Documents Work Sessions model: derived states, activity.jsonl event mapping, filter vocabulary
- [ ] Documents `actor: "cockpit"` audit trail convention

## Files

- `serve/cockpit/README.md`