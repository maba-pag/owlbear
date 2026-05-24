---
id: 1792
title: Add decision metadata and reduce agent prominence
status: research
priority: important
created: 2026-05-24T01:57:03.845485+02:00
updated: 2026-05-24T03:14:27.959215+02:00
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
blocked: false
block_reason:
claimed_at:
archival_reason:
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
