---
id: 1830
title: Review DetailTab information architecture region order
status: done
priority: important
created: 2026-05-24T11:24:06.524711+02:00
updated: 2026-05-24T17:49:32+02:00
tags:
  - scope:cockpit-web
  - ux
  - detail-tab
  - discussion
parent: 1773
depends_on: []
ac:
  - Review DetailTab IA against current Cockpit sidecar workflow.
  - Decide expected section order and direct-child/accordion host contract.
  - Any approved change updates code/tests together.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Found during #1825 full Vitest verification. DetailTab.information-architecture.test.tsx has two residual failures around direct-child data-region ordering. The product decision should resolve whether the current metadata/body/action/history order is intentional before implementation.

## User Decision
Approved direction: set a core-first DetailTab information architecture order.

Implementation should prioritize the task work contract before secondary information: core fields/body first, then acceptance criteria, actions, metadata, and history. Tests should follow that product contract instead of enforcing stale or incidental DOM structure.

## Implementation Outcome
Completed by aligning the DetailTab information architecture contract to the core-first order: task body and fields, acceptance criteria, actions, metadata, then history. Tests now follow the product structure rather than an incidental old DOM order.

Evidence: focused DetailTab IA/payload tests passed as part of the full Cockpit frontend Vitest suite, which passed with 2390 passed, 0 failed, 11 skipped.