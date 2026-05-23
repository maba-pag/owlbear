---
id: 1779
title: Define Cockpit desktop viewport support floor
status: done
priority: important
created: 2026-05-24T00:49:02.653772+02:00
updated: 2026-05-24T00:51:53+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - product-decision
  - discussion
parent: 1773
depends_on:
  - 1773
ac:
  - Cockpit visual sweeps use viewport widths that match the product's real
    desktop usage model.
  - Findings below the support floor are classified as stress evidence rather
    than current product harm unless they indicate catastrophic breakage.
  - 'Existing #1773 candidate findings are reclassified against the agreed viewport
    floor before implementation decisions.'
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
During #1773 discussion, the user clarified Cockpit is a desktop-only app. Expected practical worst case is about 1024px viewport width, regular viewing is 1200-1400px, and most use is 2000px+.

## Value Question
A UI quality sweep should judge the product in the environment it is meant to serve. Treating 320/390/768 mobile/tablet screenshots as equal product evidence can create low-value work and distract from desktop polish.

## Current Interpretation
This is a product criteria decision, not a code issue. It should reframe #1774, #1775, #1776, and #1778 before any implementation.

## Evidence
- User clarification during #1773 discussion.
- Current #1773 sweep included 320, 390, 768, and 1440 widths; future sweeps likely need 1024, 1200/1440, and 2000+ widths instead.

## Decision
Cockpit product-quality findings start at 1024px viewport width. 1200px, 1440px, and 2000px+ are primary desktop proof widths. Findings below 1024px are stress notes unless they show catastrophic blankness, global overflow, or impossible recovery.

## Reclassification
#1774, #1775, #1776, and #1778 were closed as stress notes rather than current product harm. #1773 must rerun evidence at 1024px+ before presenting the next implementation candidate.