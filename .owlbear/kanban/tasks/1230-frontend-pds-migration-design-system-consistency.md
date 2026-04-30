---
id: 1230
title: Frontend — PDS migration (design system consistency)
status: backlog
priority: nice-to-have
created: '2026-04-30 16:31:18.656061+00:00'
updated: '2026-04-30 16:33:23.454371+00:00'
tags:
- cockpit
- frontend
- design
parent:
depends_on:
- 1225
- 1228
- 1229
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace raw HTML elements with Porsche Design System components for visual consistency.

## Acceptance Criteria
- [ ] All `<button>` replaced with `<PButton>` or appropriate PDS variant
- [ ] Text elements use `<PText>`, `<PHeading>` where appropriate
- [ ] Input fields wrapped in `<PTextFieldWrapper>` or PDS form components
- [ ] Cards and columns have consistent PDS-aligned styling
- [ ] Context menu uses PDS popover/flyout pattern
- [ ] All tests updated for new component structure

## Files
- All frontend component files in `serve/cockpit/web/src/`