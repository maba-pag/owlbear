---
id: 1830
title: Review DetailTab information architecture region order
status: research
priority: important
created: 2026-05-24T11:24:06.524711+02:00
updated: 2026-05-24T11:24:06.524711+02:00
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