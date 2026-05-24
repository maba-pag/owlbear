---
id: 1727
title: Polish markdown code block contrast
status: archived
priority: important
created: 2026-05-23T03:17:00+0200
updated: 2026-05-24T10:50:01.632783+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - markdown
  - ideas
  - readability
parent:
depends_on: []
ac:
  - Reproduce markdown code blocks reading as loose indented text in the Ideas
    preview.
  - Improve shared MarkdownPreview code block contrast without breaking inline
    code or sanitization.
  - Apply the improvement through the shared component rather than per-surface
    one-offs.
  - Validate with focused tests and desktop screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback Context
The post-fix Cockpit sweep shows the Ideas preview rendering code-block sample text with little visual container contrast. Lists and paragraphs are fixed, but code blocks still do not read like intentional markdown blocks.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/postfix-sweep-ideas-20260523.png`.
- The existing user-authored Ideas note includes code block sample text; it appears mostly as unframed monospaced indentation.

## Evaluation Notes
- Classification: current markdown readability polish issue.
- Product value: task bodies, decision requests, memory entries, and ideas all rely on markdown previews; code blocks should be immediately recognizable.
- Keep the fix in `MarkdownPreview` so preview surfaces stay consistent.

## Evidence
- Shared `MarkdownPreview` now gives fenced code blocks a visible surface, border, radius, padding, and shadow while keeping nested `pre code` transparent.
- Inline code keeps a compact bordered treatment independent of fenced blocks.
- Focused Vitest passed: `MarkdownPreview.test.tsx`, `IdeasPage_1663.test.tsx`, `DetailTab.gfm-plugins.test.tsx`, and `ResolveModal.plugins.test.tsx`, 4 files, 24 tests.
- ESLint passed for `MarkdownPreview.tsx` and `MarkdownPreview.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/1727-ideas-code-block-after-fix.png`.
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1727-ideas-code-block-after-fix-metrics.json` reports two `pre` blocks with a 1px solid border, surface background, padding, and transparent nested code background.
