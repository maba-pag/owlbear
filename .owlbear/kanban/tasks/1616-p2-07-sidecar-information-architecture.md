---
id: 1616
title: 'P2-07: Sidecar information architecture'
status: review
priority: important
created: 2026-05-16T03:37:02.251956+00:00
updated: 2026-05-16T20:31:22.857482+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on: []
ac:
  - "DetailTab renders data-region sections in DOM order: sidecar-body (Editor) →
    actions (Actions) → sidecar-metadata (Metadata) → history (History); asserted
    via querySelectorAll('[data-region]') sequence within DetailTab's root element"
  - Metadata section (data-region='sidecar-metadata') wrapped in a p-accordion 
    element with compact attribute and heading='Metadata'; accordion closed by 
    default (no open attribute); content including field-* testid elements 
    remains in DOM when closed (PAccordion uses CSS visibility, verified in 
    research)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Section ordering, action prominence, content layout, accordion structure.

Scope: Sidecar information architecture only.
Out of scope: Simple swaps, cards, modals, filter panel.

[[2026-05-16T17:32:28+02:00]]
## Research
- Research doc: .owlbear/research/sidecar-information-architecture.md
- Sources: 7 studied, 5 high-relevance (PDS Accordion API/Usage, PHeading API, codebase, test suites)
- Recommendation: Reorder sections (Editor → Actions → Metadata accordion → History), PAccordion compact for Metadata only (confidence: 0.78)
- Follow-up tasks created: none — task #1616 itself covers full implementation scope
- Decision requests: none

## Challenge Results
- Challenger: reconsider (confidence in original: 0.58)
- Key challenges: History is navigation destination (initialSubtab routing), DecisionViewport omitted, #1607 dependency, DOM contract risk, width evidence incomplete
- Researcher response: revised — removed History from accordion, added DecisionViewport scope analysis, decoupled from #1607, added DOM contract and multi-width evidence
- Post-revision confidence: 0.78

## Key Findings
- PAccordion available in PDS React package (confirmed via runtime check), compact variant fits 360px sidecar
- PAccordion renders slot content in DOM when closed (CSS animation, not unmount) — field-* test selectors safe
- History must NOT go in accordion — initialSubtab routing from ActivityTab requires visible-on-mount
- Both desktop (aside) and mobile (p-sheet) render paths need identical IA changes
- Tier: T1 (autonomous) — component rearrangement + PDS accordion adoption
- Commit: d8fdbe3b

2026-05-16T16:08:29+00:00


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Section ordering + accordion wrapping within DetailTab only |
| Interface clarity | PASS (after refinement) | AC refined to name concrete selectors, DOM order, element attributes |
| Dependency correctness | PASS | #1611 archived into #1616; no remaining deps; #1608 not needed (IA scope is self-contained) |
| Module layering | PASS | Changes scoped to DetailTab.tsx; PAccordion import follows existing PDS pattern |
| TDD compliance | PASS | proof_bundle=behavioral; test-writer writes tests, builder implements |
| KISS/YAGNI | PASS | PAccordion for one section, section reorder — minimal change |
| Premise challenge | PASS | Capability doesn't exist; sections need reordering |
| Pattern consistency | PASS | PDS React components already used (PButton, PBanner, PHeading in other components) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend sidecar component only |

### AC Refinement
Original AC3 (typography hierarchy) removed — owned by sibling #1607 (sidecar structure typography). #1616 scoped to order + accordion only. Typography specifics deferred to #1607.

AC1 simplified: removed Shell dual-path parity clause (inherent since both aside and p-sheet render same DetailTab component).

AC2 refined: named exact element, attribute, and DOM behavior instead of vague \"low-frequency content.\"

### Challenge Results
- Challenger: reconsider (confidence 0.54)
- Key findings: AC1 scope bleed (Shell parity in DetailTab AC), AC3 conflicts with #1607 typography ownership, AC2 bakes third-party DOM guarantee
- Architect response: revised — removed Shell parity from AC1, removed AC3 (deferred to #1607), reframed AC2 as behavioral observation with research citation
- Post-revision: all challenges addressed; task now owns order + accordion only

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: AC refined (3→2 lines), typography deferred to #1607, approved to todo

[[2026-05-16T18:08:37+02:00]]
Architecture review complete. AC refined from 3→2 lines: typography hierarchy (AC3) deferred to sibling #1607 which owns sidecar typography. Remaining AC is focused, mechanically testable, and scoped to DetailTab only. Challenger addressed (reconsider → revised). Builder note: p-accordion is a new PDS custom element — test setup may need componentsReady or attachInternals patching consistent with existing DetailTab.test.tsx patterns.

[[2026-05-16T18:40:30+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/DetailTab-1616.test.tsx
- Classes: TestFromAC_SidecarIA
- Tests per category: happy 8, edge 2, boundary 0, error 0
- Total: 13 tests, all FAIL (AssertionError)
- lint: clean (ESLint + TypeScript pre-commit hooks passed)
- Commit: 81d96824

### AC Coverage
| AC | Tests |
|----|-------|
| AC1: data-region DOM order sidecar-body → actions → sidecar-metadata → history | 4 tests (exact order assertion, actions-before-metadata, metadata-before-history, order-preserved-blocked-task) |
| AC2: sidecar-metadata in p-accordion[compact][heading="Metadata"], closed, content in DOM | 9 tests (accordion present, metadata inside accordion, compact attr, heading attr, no-open attr, field-id/status/created/claimed in DOM when closed) |

### Builder notes
- `p-accordion` is a new PDS custom element; test setup `attachInternals` mock already covers it (same pattern as `DetailTab.test.tsx`)
- AC2 "content in DOM when closed" tests check that `accordion?.hasAttribute('open')` is false AND the `field-*` testid elements are still queryable — this is the PAccordion CSS-visibility contract cited in research

[[2026-05-16T19:51:40+02:00]]
## Builder Notes
- Implementation: no new code changes required in this builder session; AC implementation already present in `serve/cockpit/web/src/components/DetailTab.tsx` on current `HEAD`.
- RED verification (quality-runner): `serve/cockpit/web/src/__tests__/DetailTab-1616.test.tsx` -> 13 failed / 0 passed (expected RED baseline).
- GREEN verification (quality-runner): `serve/cockpit/web/src/__tests__/DetailTab-1616.test.tsx` -> 13 passed / 0 failed.
- Lint (quality-runner): clean for `serve/cockpit/web/src/components/DetailTab.tsx` and `serve/cockpit/web/src/__tests__/DetailTab-1616.test.tsx`.
- Module-level durable baseline: quality-runner hit frontend env issue (`HTMLElement is not defined`) twice; executed allowed direct fallback and verified `npx vitest run src/__tests__/DetailTab.test.tsx` and `npx eslint src/__tests__/DetailTab.test.tsx` both exit 0.
- Coverage: quality-runner coverage path reported frontend environment issue; direct fallback did not emit usable per-file coverage artifacts in this session. Behavioral proof remains: task-scoped tests green and lint clean.
- Evidence summary: AC1 DOM order and AC2 accordion/attribute/closed-DOM behavior are satisfied by current `DetailTab` implementation and passing task-scoped tests.
- Fixes applied in this session: none persisted (no diff against `HEAD`).
