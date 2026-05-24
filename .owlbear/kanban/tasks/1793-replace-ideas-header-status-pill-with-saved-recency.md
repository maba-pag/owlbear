---
id: 1793
title: Replace Ideas header status pill with saved recency
status: done
priority: important
created: 2026-05-24T01:57:03.868117+02:00
updated: 2026-05-24T03:42:59.363899+02:00
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

