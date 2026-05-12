---
id: 1491
title: 'Cockpit: Extract CockpitProvider from Shell.tsx'
status: backlog
priority: important
created: 2026-05-11T23:14:53.705441+00:00
updated: 2026-05-12T03:00:52.330672+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract all state management from Shell.tsx into a CockpitProvider context.

## Acceptance Criteria
- Shell.tsx becomes ~60 LOC layout-only (CSS grid + component composition)
- CockpitProvider (~150 LOC) owns: board/tasks state, selected task lifecycle, DR state, cross-domain effects
- Children consume via hooks: useBoardState(), useTaskSelection(), useDRState()
- No prop drilling through Shell
- Also fold in F10 (useSSERefetch extraction) and F11 (inline useConnectionHealth)

## Source
Cockpit audit 2026-05-11, Finding F1 (+ F10, F11)
2026-05-12T03:00:37+00:00

## Research
- Research doc: .owlbear/research/1491-cockpit-provider-extraction.md
- Sources: 11 studied, 6 high-relevance
- Recommendation: Single CockpitProvider with 3 consumer hooks (confidence: 0.72)
- Follow-up tasks created: #1504 (implement provider), #1505 (update tests)
- Decision requests: none (T1 — autonomous refactor)

## Challenge Results
- Challenger: reconsider (confidence in original: 0.44)
- Key challenges: render fan-out real but bounded, LOC targets need adjustment (60→75), callback identity churn needs explicit attention, test blast radius significant (8 Shell + 4 hook files)
- Researcher response: revised — accepted LOC adjustment, callback stabilization requirement, test scope documentation. Rebutted HIGH risk (moderate) and "narrow boundaries" claim. Confidence: 0.72
2026-05-12T03:00:52+00:00
Research complete. Single CockpitProvider recommended (confidence: 0.72). Challenger pushed back (0.44) — accepted LOC adjustment (60→75), callback stabilization, test blast radius. Two follow-ups created: #1504 (implement), #1505 (tests). Doc: .owlbear/research/1491-cockpit-provider-extraction.md