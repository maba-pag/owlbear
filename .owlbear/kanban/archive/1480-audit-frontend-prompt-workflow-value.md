---
id: 1480
title: Audit frontend prompt workflow value
status: archived
priority: important
created: 2026-05-11T01:27:03.160056+00:00
updated: 2026-05-11T01:40:11.706678+00:00
tags:
- frontend
- prompts
- skills
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-11T01:29:57.654851+00:00
archival_reason:
archival_refs: []
---

## Context
Frontend prompt files exist (`design-context`, `frontend-audit`, `frontend-normalize`, `frontend-polish`), but the user reports they have never used them and does not know whether they have value.

Audit whether this prompt workflow should be kept, rewritten for Cockpit, moved, or deleted. Do not assume imported prompt assets are useful just because they exist.

## Acceptance Criteria
- Inventory each frontend prompt's purpose, references, and likely invocation path.
- Check whether `docs/design-context.md` is still the right target path or whether OwlBear should use an existing docs/research/decision location.
- Recommend keep/rewrite/delete for each prompt with pro/con/risk/confidence.
- If kept, define how prompts should load `h-frontend-design` and `h-frontend-conventions` and what concrete user workflow they serve.


## Audit Findings
- The four frontend prompts were live shared prompt surfaces, not inert notes.
- `design-context`, `frontend-normalize`, and `frontend-polish` were Impeccable-inspired pilot prompts that the user has never used.
- `design-context` targeted `docs/design-context.md`, but this repo does not use a root `docs/` tree and the prompt did not match current OwlBear file-placement habits.
- `frontend-normalize` and `frontend-polish` were edit-capable prompts that could bypass kanban/task/test discipline unless heavily rewritten.
- `frontend-audit` was the least risky and highest-value prompt because it is read-only.

## Decision
User selected: keep only the audit prompt and delete the rest.

## Outcome
- Deleted `share/prompts/design-context.prompt.md`.
- Deleted `share/prompts/frontend-normalize.prompt.md`.
- Deleted `share/prompts/frontend-polish.prompt.md`.
- Rewrote `share/prompts/frontend-audit.prompt.md` as a read-only Cockpit/PDS-aware audit prompt.
- Updated `share/README.md` and `share/WIRING.md` to reflect 11 prompts and the surviving frontend-audit wiring.
- Regenerated `.owlbear/doc-index.md`.

## Verification
- `share/prompts/*.prompt.md` now reports 11 prompt files.
- No stale deleted-prompt references remain in `share/**` or `.owlbear/doc-index.md`.
- VS Code diagnostics are clean for edited docs/prompt files.
- `git diff --check` passed for the edited prompt/docs/doc-index files.
