---
id: 1722
title: Fix markdown preview spacing and lists
status: done
priority: important
created: 2026-05-23T02:07:23+0200
updated: 2026-05-23T02:39:09+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - markdown
  - task-detail
  - decisions
parent:
depends_on: []
ac:
  - Audit markdown preview surfaces for missing numbered list markers and collapsed paragraph spacing.
  - Apply one shared markdown preview style to task detail/body edit preview, decision full request, ideas preview, and memory content where applicable.
  - Preserve GFM rendering and sanitization.
  - Validate with focused tests and desktop screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Markdown preview in notes, task details, and decision details appears broken: numbered lists do not seem to work and empty lines are not visually preserved.

## Framing
This is a user-observed current usability problem, not a theoretical future risk. Markdown is a core Cockpit content format; previews should make task notes, request bodies, and decision details readable without losing list structure or paragraph breaks.

## Evaluation Notes
- Current audit found multiple ReactMarkdown wrappers with no ordered-list or paragraph spacing classes.
- Tailwind/PDS reset removes browser default list markers unless list styles are explicitly restored.
- The fix should be shared and reusable, not a one-off class patch per component.

## Evidence
- Added shared `MarkdownPreview` component and applied it to task detail/body edit preview, decision full request, Ideas preview, and Memory content.
- Focused Vitest: `MarkdownPreview.test.tsx`, `DetailTab.gfm-plugins.test.tsx`, `DetailTab.body-preview-toggle.test.tsx`, `ResolveModal.plugins.test.tsx`, `ResolveModal.test.tsx`, `IdeasPage_1663.test.tsx`, and `MemoryTab_1672.test.tsx` passed: 7 files, 111 tests.
- ESLint passed for the touched markdown preview files.
- `npm run build` passed with the existing Vite chunk-size warning.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/1722-markdown-preview-task-detail.png`.
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1722-markdown-preview-metrics.json` reports ordered list `decimal`, unordered list `disc`, and nonzero paragraph margins.

## Markdown Preview Sample
This section intentionally contains paragraphs, an ordered list, and an unordered list so Cockpit can be screenshotted against a real task detail preview.

The blank line above should create visible paragraph spacing in the preview.

1. Ordered list markers should be visible.
2. Ordered list indentation should line up cleanly with the text.
3. The next paragraph should not collapse into the list.

After the ordered list, this paragraph should have breathing room.

- Bullet list markers should also be visible.
- Bullet list spacing should match the ordered list treatment.
