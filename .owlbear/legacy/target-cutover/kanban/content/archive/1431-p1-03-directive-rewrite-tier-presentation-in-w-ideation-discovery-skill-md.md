---
id: 1431
title: 'P1-03: Directive rewrite + tier presentation in w-ideation-discovery/SKILL.md'
status: archived
priority: medium
created: 2026-05-08T01:00:48.482707+00:00
updated: 2026-05-08T14:32:14.164937+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
- agent
parent: 1428
depends_on:
- 1429
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Rewrite 1 narration directive in `share/skills/w-ideation-discovery/SKILL.md`: Step 3 handoff instruction + Step 1.5 tier presentation. Replace jargon-narrating instructions with purpose-framed alternatives.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** Directive rewrites in w-ideation-discovery/SKILL.md:
1. Step 3 — currently instructs "End Phase 1 by naming @ideation-mediator..." → rewrite to purpose-framed handoff (what completed + what opens next + how to start)
2. Step 1.5 — tier presentation currently uses raw "Investment Tier: X" → rewrite to conversational calibration ("This feels like a [tier] problem — [plain meaning]. Sound right?")

**Out:** Mediation workflow (#1430). Agent files (#1432). h-ideation foundation (#1429).

## Acceptance Criteria

- [ ] Step 3 handoff directive rewritten: no longer instructs agent to name @ideation-mediator by handle; instead instructs purpose-framed handoff (what's done, what's next, invocation command)
- [ ] Step 1.5 tier presentation rewritten: uses conversational calibration pattern from h-ideation § Transition Patterns
- [ ] Co-located `**Narrate as:**` annotation with concrete example phrase for handoff
- [ ] Behavioral equivalence: user still receives handoff artifacts location and invocation command — only framing changes
- [ ] Grep verification: `grep -n "@ideation-mediator\|Investment Tier:" share/skills/w-ideation-discovery/SKILL.md` — hits in narration guidance carry purpose framing, not bare protocol references
- [ ] References h-ideation § Communication Patterns for vocabulary
[[2026-05-08]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, two related directive rewrites (both jargon→purpose in same skill) |
| Interface clarity | PASS | All 6 AC lines specify exact changes with grep verification |
| Dependency correctness | PASS | #1429 archived — Communication Patterns + vocabulary table exist in h-ideation |
| Module layering | PASS | w-ideation-discovery references h-ideation (workflow→handbook direction) |
| TDD compliance | PASS | Prose-only; `agent` pass-through tag added |
| KISS/YAGNI | PASS | Minimal scope — two directive rewrites + verification checklist updates |
| Premise challenge | PASS | Parent brief documents real jargon leakage; before/after Pair 5 grounds the handoff rewrite |
| Pattern consistency | PASS | Follows same co-located `**Narrate as:**` pattern as sibling #1430 |
| Security surface | PASS | No system boundaries — markdown skill file only |
| Single domain | PASS | Ideation agent instructions |

### Builder Guidance
- Step 3 rewrite scope includes verification checklist line 142 (`@ideation-mediator` reference) — AC5 grep covers it
- Step 1.5: section heading can retain "Investment Tier" for navigability; narration instructions must use conversational calibration from h-ideation § Transition Patterns
- Verification checklist line 137 should align with the conversational framing (e.g., "depth calibration confirmed" rather than raw "Investment Tier confirmed")
- Before/After Pair 5 in the brief (`.owlbear/briefs/draft-ideation-ux/brief.md`) is the primary behavioral spec for the handoff rewrite

### Test Depth
- AC1: td:0 (prose rewrite)
- AC2: td:0 (prose rewrite)
- AC3: td:0 (prose annotation)
- AC4: td:0 (behavioral equivalence — reviewer/grep verified)
- AC5: td:0 (grep verification)
- AC6: td:0 (reference check)
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Added `agent` pass-through tag. Advancing to todo.
[[2026-05-08]]
Architecture review complete. All 10 criteria PASS. Prose-only task (all td:0), test-writer SKIP. Added `agent` pass-through tag. Challenger skipped per td:0 rule.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All 6 AC lines also annotated `td:0` (prose rewrites, grep verification, reference checks — no testable Python interfaces).
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Files changed: `share/skills/w-ideation-discovery/SKILL.md`
- Fixes applied:
  - Rewrote Step 1.5 tier presentation to conversational depth calibration using `h-ideation` `Communication Patterns` wording.
  - Rewrote Step 3 handoff guidance to purpose-framed language (what is complete, what opens next, and how to start).
  - Added co-located `**Narrate as:**` handoff example phrase with concrete `/ideation-mediate` invocation.
  - Updated verification checklist to require purpose-framed handoff instead of handle-based reference.
- Behavioral equivalence evidence:
  - Handoff still includes explicit Phase 2 command and artifact-path expectations; only narration framing changed.
- Grep evidence:
  - `@ideation-mediator|Investment Tier:` in `share/skills/w-ideation-discovery/SKILL.md` => no matches.
- Quality evidence (quality-runner scoped):
  - Tests: 0 passed, 0 failed (no task-scoped tests for prose-only change)
  - Lint: clean=true, violations=[]
  - Coverage: N/A (no Python module touched)
- Local diagnostics:
  - VS Code errors for changed file: none
- Commit:
  - `29341853` `feat: rewrite discovery narration directives (#1431, builder)`
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner: tests not applicable for this td:0 markdown-only change; no task-scoped tests exist.

### Lint Results
- quality-runner: no applicable local lint runner for markdown skill files in the standard toolkit.
- VS Code diagnostics: no errors in `share/skills/w-ideation-discovery/SKILL.md`.

### Coverage
- N/A (markdown-only td:0 task).

### Changed-File Scope
- Reconstructed from builder notes and commit presence in `.git/logs/refs/heads/dev:2116` / `.git/logs/HEAD:2295` for commit `29341853` (`feat: rewrite discovery narration directives (#1431, builder)`).
- Live artifact reviewed: `share/skills/w-ideation-discovery/SKILL.md`.
- Dirty-tree contamination check was not executable in this tool surface because shell access was unavailable; confidence reduced slightly.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| Step 3 handoff directive rewritten without `@ideation-mediator`; purpose-framed handoff includes what is complete, what opens next, and how to start | `share/skills/w-ideation-discovery/SKILL.md:95`, `:100`, `:103`, `:105`; grep for `@ideation-mediator|Investment Tier:` returned no matches in this file | PASS |
| Step 1.5 tier presentation uses conversational calibration pattern from `h-ideation` Transition Patterns | `share/skills/w-ideation-discovery/SKILL.md:54` matches the tier-calibration pattern in `share/skills/h-ideation/SKILL.md:275` | PASS |
| Co-located `**Narrate as:**` annotation with concrete handoff phrase | `share/skills/w-ideation-discovery/SKILL.md:103` | PASS |
| Behavioral equivalence preserved: user still gets the Phase 2 command and artifact-path handoff context | `share/skills/w-ideation-discovery/SKILL.md:90-92`, `:100`, `:146` | PASS |
| Grep verification for `@ideation-mediator|Investment Tier:` shows no bare protocol references remaining | grep on `share/skills/w-ideation-discovery/SKILL.md` returned no matches | PASS |
| References `h-ideation` Communication Patterns for vocabulary | `share/skills/w-ideation-discovery/SKILL.md:105`; referenced section exists at `share/skills/h-ideation/SKILL.md:182` | PASS |

### Informational Notes
- `share/skills/w-ideation-discovery/SKILL.md:54` cites `Communication Patterns` while using the exact sentence shape documented under `Transition Patterns` (`share/skills/h-ideation/SKILL.md:275`). This does not break the AC because the required user-facing calibration pattern is present, but the internal section attribution could be tightened in a future cleanup.

### Deductions
- `-0.03` quality-runner could not provide executable lint/test evidence for a markdown-only skill change.
- `-0.02` dirty-tree contamination check could not be executed because shell access was unavailable; changed-file scope was reconstructed from task notes plus git-log evidence.

### Verdict
- PASS
- Confidence: 0.93

### Action
- Advancing to `docs`. 
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Sole changed file is `share/skills/w-ideation-discovery/SKILL.md` — OUT of scope (agent-executable); no IN-scope prose doc references discovery-skill narrative directives |
| 2 | Module docstrings | No | N/A | No Python modules changed |
| 3 | External attribution | No | N/A | Internal prose rewrite; no external patterns used |
| 4 | Research doc | No | N/A | No research phase; prose rewrite from existing brief |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index consulted; no diagram describes-match for this skill file |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/w-ideation-discovery/SKILL.md | OUT (agent-executable SKILL.md) | N/A |

**No docs impact.** All 7 items N/A — the sole changed file is an OUT-of-scope agent-executable.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1431-* scratch files existed)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 3 handoff rewritten without @ideation-mediator; purpose-framed | SKILL.md:90-105 shows purpose-framed handoff with what-complete/what-next/how-to-start structure | PASS |
| Step 1.5 tier presentation uses conversational calibration | SKILL.md:54 matches h-ideation Communication Patterns calibration shape | PASS |
| Co-located Narrate-as annotation with concrete example phrase | SKILL.md:103 contains Narrate-as block with /ideation-mediate command | PASS |
| Behavioral equivalence: user still gets handoff artifacts and invocation | SKILL.md:100 provides fenced code block with exact Phase 2 command | PASS |
| Grep verification: no bare @ideation-mediator or Investment Tier: references | grep returns zero matches (verified independently) | PASS |
| References h-ideation Communication Patterns for vocabulary | SKILL.md:105 references Communication Patterns; section confirmed at h-ideation/SKILL.md:182 | PASS |

### Test Results
- pytest: 2968 passed, 172 failed, 4 skipped, 6 errors (all pre-existing; markdown-only change cannot cause Python failures)
- ruff: 12 violations in unrelated files (tools, knowledge packages); zero in task scope

### Architect Quality: 4/5
Specific, grep-verifiable AC lines with clear builder guidance. Minor gap: AC6 cites Communication Patterns but implementation follows Transition Patterns shape (reviewer informational note). Overall: clean path.

### Deduction Breakdown
- All 6 AC lines verified with specific evidence: no deduction
- Lint violations not in task scope: no deduction
- Full suite failures not attributable to markdown change: no deduction
- AC quality 4/5: no deduction
- Reviewer evidence section present and detailed (6/6 PASS): no deduction
- Commit 29341853 verified in git log: no deduction
- Dirty-tree check: file clean (resolved reviewer uncertainty)

### Confidence: .98
(.02 deducted for reviewer's noted section-attribution imprecision in AC6: references Communication Patterns but behavioral pattern comes from Transition Patterns subsection. Informational only, does not affect correctness.)

### Action: archive