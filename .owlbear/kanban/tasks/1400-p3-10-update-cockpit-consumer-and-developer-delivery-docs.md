---
id: 1400
title: 'P3-10: Update Cockpit consumer and developer delivery docs'
status: backlog
priority: needed
created: 2026-05-06T01:09:50.523051+00:00
updated: 2026-05-06T01:12:35.221720+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:docs
- type:docs
- docs
- delivery
- frontend
- packaging
parent: 1363
depends_on:
- 1399
- 1385
- 1389
- 1390
- 1396
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Update Cockpit consumer, developer, and package docs so delivery behavior and frontend stack guidance match the final remediated product.

## Problem Evidence
- README-consumer does not mention Cockpit or the prebuilt dist launch path.
- Developer README guidance assumes a source build from serve/cockpit/web without clearly separating consumer behavior.
- serve/cockpit README is backend-centric and points to instruction text for frontend stack details.
- Stack and version descriptions have drifted from package.json.

## Acceptance Criteria
- Consumer docs explain launching Cockpit from prebuilt dist without Node and without serve/cockpit/web in the consumer tree.
- Developer docs explain the source-build workflow, Node/npm requirement, and Cockpit frontend quality commands.
- serve/cockpit README accurately describes backend and frontend surfaces, decision lifecycle behavior after #1385, decision UX after #1389, product boundary after #1390, and delivery packaging after #1399.
- Stack and version documentation is aligned with package.json rather than stale instruction text.
- Documentation distinguishes consumer launch, developer source build, release packaging, and product-boundary responsibilities clearly enough for future maintainers.
- Verification confirms docs match the final responsive/accessibility state from #1396 and do not describe cache/SSE invalidation work from #1346 as part of this bundle.

## Scope
- In scope: README-consumer.md, README.md, serve/cockpit README content, and related committed documentation that describes Cockpit delivery, stack, launch, and product boundary.
- Out of scope: changing CI or packaging behavior from #1399, implementing Cockpit UI behavior, editing instruction files as the source of stack truth, and cache/SSE invalidation from #1346.

## Notes
This is intentionally a docs task without a separate RED task because the acceptance criteria are documentation accuracy and verification rather than new executable behavior.
