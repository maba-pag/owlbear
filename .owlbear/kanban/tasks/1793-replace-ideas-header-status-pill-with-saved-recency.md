---
id: 1793
title: Replace Ideas header status pill with saved recency
status: done
priority: important
created: 2026-05-24T01:57:03.868117+02:00
updated: 2026-05-24T04:34:04.727259+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - ideas
  - discussion
  - scope:cockpit-api
parent: 1773
depends_on: []
ac:
  - Ideas header avoids redundant `Saved` state when the editor toolbar already 
    communicates save state.
  - If shown, last-saved recency uses a clear relative format such as `Saved 3m 
    ago`.
  - Dirty/conflict states remain prominent enough for safe editing.
  - No implementation begins until the user approves this task.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback on Ideas: the status bubble in the title line (`Saved`) is practically redundant with the edit/preview/save controls in the markdown section. If the header space should not be empty, it could show last saved datetime in a relative `3m ago` format.

## Current Interpretation
Information design issue. The header summary slot is currently used for state that is already visible and actionable below, while recency would be more informative for a notebook surface.

## Value
Ideas is a writing/capture surface. Last saved recency gives users confidence that their notes are current without duplicating disabled/enabled button state.

## Discussion Questions
- Should the header summary be omitted entirely when saved, or show relative last saved time?
- Does the backend currently provide enough data for last saved time, or would this require API support?
- Should dirty/conflict states still appear in the header because they are urgent?

[[2026-05-24T03:25:38+02:00]]

## Discussion Decision
- Remove the clean `Saved` header pill; keep dirty and conflict states prominent.
- Do not show `Saved 3m ago` from client-only state.
- Fact check: `.owlbear/ideas.md` is plain markdown today with no YAML frontmatter, and `GET /api/ideas` currently returns only `{content}`. A real recency display would require a new API-backed metadata contract rather than exposing existing data.
- Candidate follow-up design: extend Ideas persistence/API with explicit metadata, possibly YAML frontmatter if we want the markdown file to own its own saved metadata, but this is not currently implemented.

[[2026-05-24T03:42:50+02:00]]

## Implementation Proof
Implemented in Cockpit web as part of the approved small polish package. The Ideas header no longer renders a clean `Saved` summary pill. Dirty and conflict states remain in the header; proof shows clean summary count `0` and dirty summary text `Unsaved changes`.

Proof screenshots: `.owlbear/scratch/1716-wide-cockpit/1793-ideas-clean-header-after.png`, `.owlbear/scratch/1716-wide-cockpit/1793-ideas-dirty-header-after.png`

[[2026-05-24T04:22:03+02:00]]

## Reopen Note
User review found the dirty-state header pill is still redundant: `Unsaved changes` remains on the same line as the Ideas headline and duplicates the editor toolbar state. User also does not see a `last saved` entry anywhere. Fix direction: remove the Ideas header status pill entirely and add an honest last-saved display backed by real persistence/API data.

[[2026-05-24T04:33:35+02:00]]
## Completion Note
- Removed Ideas workspace-header status pills entirely, including the dirty `Unsaved changes` pill on the title line.
- Extended `GET /api/ideas` with `updated_at` from the ideas markdown file mtime and exposed `X-Ideas-Updated-At` on successful PUT while preserving the 204/no-body write contract.
- Added a visible Notebook `Last saved` row in the Ideas state panel; dirty state remains in the editor toolbar and state panel, not the headline.
- Verification: `uv run pytest tests/test_cockpit_ideas_1660.py`; `npm test -- --run src/__tests__/IdeasPage.test.tsx src/__tests__/ThemeToggle.test.tsx src/__tests__/HealthBadge.test.tsx src/__tests__/BoardVisualDesign.test.tsx src/__tests__/Shell.test.tsx`; focused ESLint; `npm run build`.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1793-ideas-dirty-last-saved-updated.png` shows header text `Ideas`, no workspace-header summary, dirty toolbar state, and `Last saved 1m ago` in the Notebook panel.

