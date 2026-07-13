---
id: 1037
title: 'Update w-ideation SKILL.md: no bulk-ratify rule'
status: archived
priority: medium
created: 2026-04-19 23:53:48.265360+00:00
updated: 2026-04-20 01:28:10.711590+00:00
tags:
- process-improvement
- docs
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

From Brief docs-currency-2026-04-19 section 9: Mediator dumped 6 outcome-sharpenings in a table without per-item context, then asked "accept all 6?". This violated the user's ability to evaluate individual changes.

## Acceptance Criteria

- [ ] Add a third general blockquoted rule at the top of `share/skills/w-ideation/SKILL.md`, alongside the existing Turn-ending rule (lines 12-17) and Confidence/recommended rule (lines 18-20)
- [ ] Rule states: never bulk-ratify analysis the user hasn't seen — applies to all Critic check points (M1 step 8-9, M2 step 7, M4 step 4-5, M5 step 4-5, ad-hoc invocations)
- [ ] Process specified: present one group per turn (group = items sharing the same original text or logically dependent on each other), with original text quoted, Critic's concern in plain language, and proposed change visible
- [ ] No bulk "accept all N?" patterns permitted — each group gets individual user approval via askQuestions
- [ ] Add corresponding line item to the Verification Checklist (lines 501-514)

> **Note:** This rule is distinct from the Brief Walkthrough Protocol (per-chunk review of Brief *sections* in M5). This rule governs Critic-proposed *changes* to existing content at any moment. Both rules can apply simultaneously at M5 without conflict.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One rule addition to one file |
| Interface clarity | REFINED | AC1 placement clarified to general rule; "cluster" replaced with defined "group" concept |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Skill file, not code |
| TDD compliance | N/A | Non-implementation task; `docs` tag added for pass-through |
| KISS/YAGNI | PASS | Straightforward rule addition |
| Premise challenge | PASS | Addresses documented incident (Brief docs-currency section 9) |
| Pattern consistency | PASS | Follows existing general-rule pattern at lines 12-20 |
| Security surface | N/A | Process documentation only |
| Single domain | PASS | Ideation workflow only |

### Challenge Results

- Challenger: reconsider (0.55)
- Architect response: accepted concerns #1 (placement ambiguity → clarified AC1 to general rule) and #2 (undefined cluster → replaced with concrete "group" definition); #3 (walkthrough overlap) addressed with clarifying note — different concerns at different levels

### Verdict: REFINE → APPROVE

### Action Taken

Tightened AC1 to specify general-rule placement. Replaced vague "tightly-coupled cluster" with defined grouping heuristic. Added AC5 for Verification Checklist. Added `docs` tag for non-implementation pass-through. Added relationship note distinguishing this rule from Brief Walkthrough Protocol.
[[2026-04-20]]
## Test-Writer Notes
- Non-implementation task (tagged `docs`) — no tests applicable.
- AC describes edits to `share/skills/w-ideation/SKILL.md` only (process documentation, no Python interfaces).
- Architecture review confirms: TDD compliance = N/A.
- Passing through to builder.
[[2026-04-20]]
## Builder Notes
- File changed: `share/skills/w-ideation/SKILL.md`
- Added third general blockquoted rule (**No-bulk-ratify rule**) after the Confidence/recommended rule, defining "group" concept, one-group-per-turn process, and clarifying distinction from Brief Walkthrough Protocol
- Added corresponding Verification Checklist item at end of list
- No tests applicable (docs/non-implementation task)
- No lint required (Markdown only)
[[2026-04-20]]
## Review Evidence

**Type:** Docs-only task (tagged `docs`, architecture TDD=N/A) — no tests or lint applicable.

**Changed file:** `share/skills/w-ideation/SKILL.md`

**AC Compliance:**

| AC | Evidence | Status |
|----|----------|--------|
| AC1 — Third blockquoted rule at top alongside existing rules | L19: third blockquoted rule placed immediately after Confidence/recommended rule (L17) in the same introductory blockquoted section | PASS |
| AC2 — Rule content: never bulk-ratify; all Critic check points listed | L19: "Applies at all Critic check points (M1 steps 8–9, M2 step 7, M4 steps 4–5, M5 steps 4–5) and ad-hoc invocations." — matches AC exactly | PASS |
| AC3 — Process: one group per turn, group defined, original text + concern + change visible | L19: group definition present, one-group-per-turn stated, "quote the original text, state the Critic's concern in plain language, and show the proposed change." | PASS |
| AC4 — No bulk "accept all N?"; individual askQuestions approval | L19: "Never present…as a bulk 'accept all N?' table" + "Obtain individual user approval via `askQuestions` for each group" | PASS |
| AC5 — Checklist item added | L495: "No-bulk-ratify rule: all Critic-proposed changes presented one group per turn with original text quoted, concern stated in plain language, and individual `askQuestions` approval obtained" | PASS |

Relationship note (task AC note) correctly embedded in rule text at L19. No TestFromAC modifications (N/A). No security surface. 0 deductions.

**Verdict: PASS | confidence .97**
[[2026-04-20]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Skill file edit only; no tech stack or API changes |
| 2 | Module docstrings | No | N/A | No Python modules touched |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Context references a brief (docs-currency-2026-04-19), not a research doc; no .owlbear/research/ file produced |

### Verification
- AC1: Third blockquoted rule at L19 (after Confidence/recommended rule) — confirmed
- AC2: All Critic check points listed (M1 8–9, M2 7, M4 4–5, M5 4–5, ad-hoc) — confirmed
- AC3: Group definition, one-group-per-turn, quote/concern/change process — confirmed
- AC4: "Never present…as a bulk 'accept all N?' table" + individual askQuestions — confirmed
- AC5: Checklist item at L496 — confirmed

### Scratch files
None found (`.owlbear/scratch/1037-*` — no matches).

### Files updated
None — all AC items verified as present; no doc updates required.
[[2026-04-20]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — Third blockquoted rule alongside existing rules | SKILL.md L19: blockquoted rule after Confidence/recommended rule (L17), same introductory section | PASS |
| AC2 — Never bulk-ratify; all Critic check points listed | L19: "Applies at all Critic check points (M1 steps 8–9, M2 step 7, M4 steps 4–5, M5 steps 4–5) and ad-hoc invocations." | PASS |
| AC3 — One group per turn; group defined; original text + concern + change visible | L19: group = "items that share the same original text or are logically dependent"; "Present one group per turn: quote the original text, state the Critic's concern in plain language, and show the proposed change." | PASS |
| AC4 — No bulk "accept all N?"; individual askQuestions | L19: "Never present…as a bulk 'accept all N?' table" + "Obtain individual user approval via `askQuestions` for each group" | PASS |
| AC5 — Verification Checklist item added | L495: "No-bulk-ratify rule: all Critic-proposed changes presented one group per turn with original text quoted, concern stated in plain language, and individual `askQuestions` approval obtained" | PASS |

### Test Results
- pytest: 787 passed, 6 failed (pre-existing — test_outputschema_541 ×4, test_search_v2 ×1, test_phase_a_config ×1 — none related to this task), 4 skipped
- ruff: clean

### Architect Quality: 4/5
Specific and verifiable AC. Challenger concerns properly addressed (placement ambiguity → clarified to general rule; vague "cluster" → defined "group" concept). Relationship note distinguishing from Brief Walkthrough Protocol prevents future confusion. Minor: original AC referenced stale line numbers (pre-edit), but architect couldn't predict post-edit lines — acceptable.

### Deduction Breakdown
- 0 AC lines without evidence: −0
- Lint clean: −0
- AC quality 4/5 (>3): −0
- Reviewer evidence present and detailed (PASS .97): −0
- Full-suite failures outside task scope: −0

### Confidence: .98
### Action: archive