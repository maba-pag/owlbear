---
id: 1721
title: Reduce decision board text repetition
status: archived
priority: medium
created: 2026-05-23T01:44:00+02:00
updated: 2026-05-24T10:50:01.550881+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - decisions
  - information-architecture
parent:
depends_on: []
ac:
  - Audit the live Decisions route and resolver for repeated text surfaces.
  - Avoid rendering the same unstructured decision paragraph as title, context,
    request, and full request preview.
  - Preserve the resolver workflow and response controls.
  - Validate with desktop screenshot evidence and focused checks.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
The decision board is all but done, but the current page repeats the same text multiple times on the main page and again in the detail page. There is no useful difference or structure; the general route idea is good, but the duplicated text makes it strange.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI issue, confirmed in 2560px screenshots.
- Product value: Decisions should help a user quickly understand what needs a human response and choose a response; repeated unstructured paragraphs make the route feel like copied data rather than a decision workflow.
- Impact: hurts Cockpit now because `/decisions` is the primary human resolution surface.
- Screenshot target: Decisions route list and resolver modal at desktop width.

## Acceptance Criteria
- The Decisions list shows each request once, with useful metadata and action affordance rather than duplicate Context/Request blocks when the source body is unstructured.
- The resolver modal separates heading, brief, response choices, notes, and optional full request without repeating the same paragraph in multiple visible sections.
- Structured request bodies with explicit Context/Options/Recommendation/Impact continue to expose those sections.

## Implementation Notes
- Confirmed the live issue against real pending DR data: the plain paragraph in `1558-decision.md` was rendered as the title, Context, Request, and Full request preview.
- Backend pending-decision title extraction now keeps markdown heading titles, but derives compact titles from plain decision paragraphs instead of returning the entire first line.
- Frontend decision briefs now distinguish structured markdown from unstructured paragraphs. Structured requests still show Context/Options/Recommendation/Impact; unstructured requests show one concise Summary and parsed inline Options when present.
- The Decisions route card was polished into a compact decision brief with PDS metadata tags, summary/options sections, and an inline resolver affordance instead of a repeated side panel.
- The resolver modal now shows the same single brief plus response controls, with the full markdown request kept behind disclosure.
- Added markdown list CSS for the resolver full request so numbered and bulleted markdown lists render with visible markers.

## Evidence
- Before screenshots: `.owlbear/scratch/1716-wide-cockpit/decisions-current-1721.png`, `.owlbear/scratch/1716-wide-cockpit/decisions-modal-current-1721.png`.
- After screenshots: `.owlbear/scratch/1716-wide-cockpit/decisions-after-1721.png`, `.owlbear/scratch/1716-wide-cockpit/decisions-modal-after-1721.png`.
- Real browser proof at 2560x1440: heading is `Choose ownership model for knowledge source lifecycle`; visible card sections are Summary and Options; modal summary/options match and Full request remains collapsed.
- Focused frontend checks: `npx vitest run src/__tests__/DecisionsPage_1645.test.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/ResolveModalSnapshot_1647.test.tsx --reporter=verbose` passed, 43 tests.
- Focused backend checks: `uv run pytest tests/test_cockpit_decisions_api.py -k "pending_plain_paragraph_title or pending_returns_count_and_required_fields_including_body or pending_body_and_preview_preserve_full_markdown"` passed, 3 tests.
- Lint/build checks passed for touched frontend files; `npm run build` passed with the existing Vite chunk-size warning only.