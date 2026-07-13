---
id: 1807
title: Frame decision resolver metadata as section
status: archived
priority: medium
created: 2026-05-24T07:23:36.019757+02:00
updated: 2026-05-24T10:50:02.721894+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - decisions
  - resolver
  - metadata
  - discussion
parent: 1773
depends_on: []
ac:
  - Decision resolver metadata appears in its own visually framed section with a
    clear heading.
  - The metadata section remains readable at the 1024px support floor and wide
    desktop modal widths.
  - Resolver response controls and footer actions remain usable after the
    metadata framing change.
  - Screenshot proof captures the resolver with the metadata section visible.
  - If the framed metadata does not improve the layout problem, return for
    another decision before further implementation.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback while reviewing Memory/detail spacing: Kanban task detail metadata is presented as a separate bordered section, but Decision resolver metadata is present without the same section framing or headline.

## Requested Direction
Pack the Decision resolver metadata into its own bordered section with a heading, then inspect how it looks. If that does not improve the layout/problem, return and ask again before further changes.

## Current Interpretation
The resolver may benefit from the same information-architecture treatment used by task detail: metadata as a distinct section rather than loose grid content.

## Boundary
User approved this specific experiment. Do not expand beyond metadata framing without coming back for approval.

[[2026-05-24T07:28:44+02:00]]
Checked the requested metadata-section experiment. No source change was needed because the current resolver already renders metadata in its own bordered `resolve-decision-metadata` section with the visible heading `Decision Metadata`. Existing #1804 resolver screenshots show the framed metadata section at 1024/2000. Per user direction, returning for another decision rather than changing unrelated layout.
