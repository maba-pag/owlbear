---
id: 1792
title: Add decision metadata and reduce agent prominence
status: archived
priority: important
created: 2026-05-24T01:57:03.845485+02:00
updated: 2026-05-24T10:50:02.525694+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - decisions
  - discussion
parent: 1773
depends_on: []
ac:
  - Decision board prioritizes decision content over agent attribution.
  - Decision detail includes a clear Metadata section with relevant available
    fields.
  - Agent/source information remains available but not over-prominent.
  - No implementation begins until the user approves this task.
  - Agent attribution is moved out of the primary Decision list/detail line and
    into metadata.
  - Decision detail metadata is added using available decision fields.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback on Decisions:
1. The agent that created the decision does not feel important enough to show on the decision board or in the first line of decision detail.
2. Agent information may be better placed in a Metadata section, similar to Kanban task details.
3. Decision detail currently lacks a comparable Metadata section populated with available decision info.

## Current Interpretation
Information hierarchy issue. Decision surfaces may be over-emphasizing author/agent while under-providing structured metadata in a predictable location.

## Value
Decision review should focus first on the decision, options, context, and action. Metadata should be available without crowding the primary decision flow.

## Discussion Questions
- Which fields belong in Decision metadata: task id, agent, request type, created age/date, source file/id?
- Should agent disappear entirely from list cards, or move to a less prominent line/chip?
- Should decision detail metadata mirror task detail metadata patterns?

[[2026-05-24T03:14:27+02:00]]
## Decision
User selected `Move agent to metadata`. Decision list/detail primary rows should prioritize decision content and essential workflow context; agent/source attribution belongs in a Decision Metadata section instead of the most prominent line.

[[2026-05-24T05:41:57+02:00]]
## Implementation Proof
- Moved decision agent attribution out of the Decisions list primary metadata row; cards now foreground request type, task, age, title, context/options, and resolver path.
- Moved resolver header attribution out of the first line and added a Decision Metadata section with task, request type, created timestamp/age, agent, and source ID.
- Focused tests passed: `npm test -- --run src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/DecisionsPage_1645.test.tsx src/__tests__/ResolveModal.test.tsx src/__tests__/ResolveModalSnapshot_1647.test.tsx src/__tests__/DecisionContract.test.tsx` -> 58 passed, 3 skipped.
- Lint passed: `npx eslint src/pages/DecisionsPage.tsx src/components/ResolveModal.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/DecisionsPage_1645.test.tsx src/__tests__/ResolveModal.test.tsx src/__tests__/DecisionContract.test.tsx`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1792-decision-metadata-1024.png` at the 1024 support floor, showing the resolver header without agent and the Decision Metadata section with agent/source attribution.

[[2026-05-24T05:42:02+02:00]]
Completed Decision Metadata hierarchy: list/header primary rows no longer emphasize agent attribution, resolver metadata contains task/type/created/agent/source ID, focused tests/lint/build passed, and 1024 screenshot proof captured.
