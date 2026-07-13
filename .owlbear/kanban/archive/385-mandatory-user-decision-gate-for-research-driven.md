---
id: 385
title: Mandatory user-decision gate for research-driven features and 
  architectural changes
status: archived
priority: medium
created: 2026-03-30 20:56:31.651150+02:00
updated: 2026-03-31 08:38:16.775382+02:00
started: 2026-03-31 08:38:13.095432+02:00
completed: 2026-03-31 08:38:13.095432+02:00
tags:
- research
- ' scope:agents'
- ' process'
- ' quality'
class: standard
archival_reason: completed
archival_refs: []
---

## Context

Research findings and follow-up tasks currently bypass user decision-making. Agents can research a topic and create follow-up implementation tasks directly at `ideation`, which then flow through the pipeline (architect, test-writer, builder) without the user ever approving the direction. The decision-request skill exists but is optional — agents use it only "when multiple valid options exist." This creates a gap: single-option research conclusions (which are the majority) skip user oversight entirely.

The user wants mandatory human-in-the-loop approval for all wide-ranging decisions, especially when research leads to new features or architectural changes.

## Acceptance Criteria

- [ ] Audit the current decision-request workflow (`skills/decision-requests/SKILL.md`) and identify gaps where research conclusions bypass user approval
- [ ] Determine which research outcomes MUST create a decision request vs which can proceed autonomously (e.g., bug fix research vs new feature research vs architectural change)
- [ ] Design a classification system for research outcomes: "proceed autonomously" vs "requires user decision" — with clear triggers for each
- [ ] Propose changes to the researcher agent instructions and research-workflow skill to enforce mandatory decision requests for feature-impacting findings
- [ ] Propose changes to the architect agent to verify that research-driven tasks have an approved decision request before advancing past backlog
- [ ] Address the 5-day auto-timeout in the current decision-request skill — should high-impact decisions auto-resolve? Propose alternatives (e.g., block indefinitely, escalate, or auto-resolve only for low-impact)
- [ ] Create a decision request with the proposed classification system for user approval before implementation
- [ ] Create follow-up implementation tasks at ideation for agreed changes

[[2026-03-30]] Mon 21:28
## Research
[[2026-03-30]] Mon 21:28
Doc: docs/research/mandatory-user-decision-gate.md
Decision: docs/decisions/pending/385-research-outcome-classification.md

Key findings: 5 gaps in current workflow. Proposed 3-tier classification (T1 autonomous, T2 advisory, T3 mandatory) with deterministic triggers. T3 blocks indefinitely. 4 follow-up tasks pending decision approval.

[[2026-03-31]] Tue 03:40
## Research (completed)
Doc: docs/research/mandatory-user-decision-gate.md
Decision: docs/decisions/pending/385-research-outcome-classification.md (approved: Option A)

Key findings: 5 gaps in current workflow (G1-G5). Proposed 3-tier classification (T1 autonomous, T2 advisory, T3 mandatory) with deterministic triggers. T3 blocks indefinitely. Auto-timeout Option A selected (.85 confidence).

Follow-up tasks created:
- #459: Update decision-requests skill with impact_tier field
- #460: Update researcher agent and research-workflow with tier classification
- #461: Add decision-request verification to architect backlog gate
- #462: Update agent-common defer-to-user boundary with tier classification

Sources logged in docs/sources/overview.md.

[[2026-03-31]] Tue 04:45
## Architecture Review
**Verdict:** Approve
**DR Verification:** docs/decisions/resolved/385-research-outcome-classification.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Audit decision-request workflow | Complete: research doc S3 identifies 5 gaps (G1-G5) | Verified |
| Determine mandatory vs autonomous outcomes | Complete: deterministic T3 triggers (6 factual conditions) | Verified |
| Design classification system | Complete: T1/T2/T3 with deterministic triggers in S4 | Verified |
| Propose researcher agent changes | Complete: S6 C2+C3 | Verified |
| Propose architect agent changes | Complete: S6 C4 | Verified |
| Address 5-day auto-timeout | Complete: Option A selected (T2 keeps 5d, T3 blocks indefinitely) | Verified |
| Create decision request | Complete: docs/decisions/resolved/385-research-outcome-classification.md, user-approved | Verified |
| Create follow-up tasks at ideation | Complete: #459, #460, #461, #462 (all now at todo after arch review) | Verified |

### Architecture Notes
Pure research/design task. All 8 AC items are deliverables (audit, design, propose, create), not implementation. Research doc is thorough: 9 sources, 5 identified gaps, deterministic classification triggers (not judgment-based). Decision request was approved (Option A: 3-tier). Four atomic follow-up tasks properly cover all 5 required changes (C2+C3 combined in #460 since they target the same agent workflow). No code produced, no TDD needed. Single concern: user-decision gate process.

Verified gaps exist in current files: decision-requests skill has no impact_tier field, researcher agent has no tier classification, uniform 5-day auto-resolve applies to all urgencies.

### Changes Made
- Verified all 8 AC items against research doc and kanban board
- Verified decision request approved at docs/decisions/resolved/
- Verified follow-up tasks #459-#462 exist and are properly scoped
- Approved to todo

### Dependencies
- Verified: Follow-ups #459-#462 all at todo (already architect-reviewed)
- Verified: #464 (dispatch-planning tier-aware auto-resolve) created by #459 research

[[2026-03-31]] Tue 06:04
## Test-Writer Notes
- Non-implementation task (tagged research, quality) — no tests applicable.
- Architecture Review confirmed: "No code produced, no TDD needed."
- Passing through to builder.

[[2026-03-31]] Tue 06:16
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.

[[2026-03-31]] Tue 07:53
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure design task; implementation in follow-ups #459-#462 |
| 2 | Python docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | Yes | Updated | Duplicate simpler section (line 2551) removed; complete entry at line 3387 retained; not committed in isolation due to other tasks uncommitted changes in same file |
| 4 | README.md CLI changes | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/mandatory-user-decision-gate.md exists and linked |

### Files Updated
- docs/sources/overview.md (duplicate section removed)

### Scratch Files Cleaned
- None

[[2026-03-31]] Tue 07:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Pure design task; T1/T2/T3 implementation in follow-ups #459-#462 |
| 2 | Python docstrings | No | N/A | No Python modules changed |
| 3 | docs/sources/overview.md | Yes | Updated | Duplicate simpler entry (line 2551) removed; complete entry at line 3387 retained |
| 4 | README.md CLI changes | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/mandatory-user-decision-gate.md exists and linked |

### Files Updated
- docs/sources/overview.md (duplicate section removed; not committed in isolation due to other uncommitted changes in same file from other tasks)

### Scratch Files Cleaned
- None (no 385-* scratch files found)

[[2026-03-31]] Tue 08:38
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Audit decision-request workflow gaps | Research doc S3: 5 gaps (G1-G5) identified | PASS |
| Determine mandatory vs autonomous outcomes | Research doc S4: deterministic T3 triggers (6 factual conditions) | PASS |
| Design classification system | Research doc S4: T1/T2/T3 tiers with deterministic triggers | PASS |
| Propose researcher agent changes | Research doc S6 C2+C3 | PASS |
| Propose architect agent changes | Research doc S6 C4 | PASS |
| Address 5-day auto-timeout | Research doc S5 Option A selected (T2 keeps 5d, T3 blocks indefinitely) | PASS |
| Create decision request | docs/decisions/resolved/385-research-outcome-classification.md approved: true | PASS |
| Create follow-up tasks at ideation | #459, #460, #461, #462 all created and progressed through pipeline | PASS |

### Research Task Checklist
- Research doc exists: docs/research/mandatory-user-decision-gate.md (committed 5e96e18)
- Decision request approved: docs/decisions/resolved/385-research-outcome-classification.md
- Follow-up tasks reference research doc: all 4 verified
- Follow-up tasks created: #459 (done), #460 (done), #461 (done), #462 (archived)

### Test Results
- pytest: 1927 passed, 267 failed, 1 error (all failures from other tasks, none in #385 scope)
- ruff: N/A (no Python code produced)

### AC Quality Score: 5/5
8 specific, verifiable AC items. No improvisation needed by downstream agents.

### Deduction breakdown
- -.02 missing reviewer evidence section (no Review Evidence in task body)

### Confidence: .98
### Action: archive
