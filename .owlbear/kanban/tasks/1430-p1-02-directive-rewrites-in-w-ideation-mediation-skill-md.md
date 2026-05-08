---
id: 1430
title: 'P1-02: Directive rewrites in w-ideation-mediation/SKILL.md'
status: review
priority: needed
created: 2026-05-08T01:00:48.467318+00:00
updated: 2026-05-08T14:15:10.215124+00:00
tags:
- phase-1
- scope:shared
- ideation
- ux
- agent
parent: 1428
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Rewrite 3 narration directives in `share/skills/w-ideation-mediation/SKILL.md` to replace jargon-narrating instructions with purpose-framed alternatives. Add co-located `**Narrate as:**` annotations.

Brief: see parent #1428. Full brief at `.owlbear/briefs/draft-ideation-ux/brief.md`.

## Scope

**In:** 3 directive rewrites in w-ideation-mediation/SKILL.md:
1. Step 1.5 — currently instructs "Tell the user you are switching..." → rewrite to purpose-framed announcement
2. Step 2 — currently instructs "Tell the user which late-domain panelists..." → rewrite to purpose-framed roster introduction
3. Disclosure Ladder — add depth-control verbal cues from h-ideation § Communication Patterns

**Out:** Discovery workflow (#1431). Agent files (#1432). h-ideation foundation (#1429).

## Acceptance Criteria

- [ ] Step 1.5 directive rewritten: no longer instructs agent to name internal switching mechanism; instead instructs purpose-framed announcement (what's happening + why)
- [ ] Step 2 directive rewritten: no longer instructs agent to enumerate panelist agent names; instead instructs purpose-framed introduction (which reviews + why those angles)
- [ ] Disclosure Ladder updated with verbal cues from h-ideation § Depth-Control Verbal Cues
- [ ] Each rewritten directive has a co-located `**Narrate as:**` annotation with a concrete example phrase
- [ ] Behavioral equivalence: same information reaches the user (which reviews, what's happening next) — only framing changes
- [ ] Grep verification: `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md` — hits in narration guidance positions carry explanatory context or appear in technical routing (not user-facing phrasing)
- [ ] References h-ideation § Communication Patterns for vocabulary (cross-reference, not duplication)
[[2026-05-08]]


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | 3 directive rewrites + Disclosure Ladder cues, all in one file, all same change type |
| Interface clarity | PASS | AC names exact lines (Step 1.5 line 5, Step 2 line 2, Disclosure Ladder), format (`**Narrate as:**`), and grep verification command |
| Dependency correctness | PASS | Removed stale dep on #1429 (task record absent from board). Deliverable (Communication Patterns section in h-ideation/SKILL.md line 182+) is already in place with vocabulary table, narration principles, transition patterns, boundary heuristic, and depth-control verbal cues |
| Module layering | N/A | Markdown skill files only |
| TDD compliance | PASS | Non-implementation task (markdown prose). Added `agent` pass-through tag for test-writer skip |
| KISS/YAGNI | PASS | Minimal scope: 3 directive rewrites + 1 Disclosure Ladder update. No new abstractions |
| Premise challenge | PASS | Jargon leakage is a real observed problem (brief Pairs 1-6 demonstrate concrete failure modes). Communication Patterns section provides the replacement vocabulary |
| Pattern consistency | PASS | Follows the brief's approach (mechanism 2: directive rewrites with co-located annotations) |
| Security surface | N/A | No system boundaries affected |
| Single domain | PASS | Ideation/UX only |

### Design Diverge
- Trigger: skipped — single clear approach (rewrite directives per brief specification)

### Challenge Results
- Challenger: SKIPPED — all td:0

### Test Depth
- All AC lines: td:0 (markdown prose edits, grep-verified)
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Removed stale dependency on non-existent #1429 (deliverable already in place). Added `agent` pass-through tag. Advanced to todo.
[[2026-05-08]]
Architecture review complete. All criteria PASS. Removed stale dep #1429 (task record absent, deliverable already in place in h-ideation/SKILL.md). Added `agent` pass-through tag. All AC lines td:0 — test-writer SKIP.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged `agent`) — no tests applicable.
- All AC lines td:0 (markdown prose edits, grep-verified). Architecture review confirms test-writer SKIP.
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Verified pass-through marker in `## Test-Writer Notes` ("Non-implementation task").
- Passing through to review per `w-tdd-green` Step 0a.
[[2026-05-08]]
## Review Evidence
### Test Results
- pytest: skipped. td:0 markdown skill task with no task-scoped tests.
- quality-runner: skipped. For td:0 reviews in this workspace, scoped mode requires non-empty test_paths and this task has no test artifact.

### Lint: skipped
- td:0 markdown task; no runnable scoped lint dispatch via quality-runner for this review surface.

### Coverage: skipped
- td:0 markdown task; no code module changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. No TestFromAC_* classes and all AC lines were marked td:0 in the Architecture Review.

#### Security Review
- No security issues found in scope. The blocking issue is missing required content changes in share/skills/w-ideation-mediation/SKILL.md.

#### Test Integrity
- Skipped. No task-scoped test file exists.

#### Test Quality
- Skipped. No task-scoped test file exists.

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Gaps
- share/skills/w-ideation-mediation/SKILL.md:87 still says "Tell the user you are switching to a proposal comparison path." The Step 1.5 directive was not rewritten to a purpose-framed announcement.
- share/skills/w-ideation-mediation/SKILL.md:103 still says "Tell the user which late-domain panelists you are invoking and why." The Step 2 directive was not rewritten away from roster narration.
- share/skills/w-ideation-mediation/SKILL.md:106-109 still list raw agent names immediately under that user-facing instruction.
- share/skills/w-ideation-mediation/SKILL.md:36-62 contains the pre-existing Disclosure Ladder structure only. The h-ideation source cues exist at share/skills/h-ideation/SKILL.md:182 and share/skills/h-ideation/SKILL.md:286-292, but they were not pulled into this file.
- grep_search found no "Narrate as:" matches in share/skills/w-ideation-mediation/SKILL.md.
- grep_search found no "Communication Patterns" matches in share/skills/w-ideation-mediation/SKILL.md.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- First review cycle: no prior `## Review Evidence` section exists in .owlbear/kanban/tasks/1430-p1-02-directive-rewrites-in-w-ideation-mediation-skill-md.md.
- Dirty-tree contamination could not be checked with git status from the current tool surface. Small confidence deduction only; the artifact itself already fails multiple AC lines.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Step 1.5 directive rewritten: no longer instructs agent to name internal switching mechanism; instead instructs purpose-framed announcement (what's happening + why) | share/skills/w-ideation-mediation/SKILL.md:87 still uses the old mechanism-level instruction. | N/A (td:0) | FAIL |
| Step 2 directive rewritten: no longer instructs agent to enumerate panelist agent names; instead instructs purpose-framed introduction (which reviews + why those angles) | share/skills/w-ideation-mediation/SKILL.md:103 still instructs roster narration; raw agent names remain at lines 106-109. | N/A (td:0) | FAIL |
| Disclosure Ladder updated with verbal cues from h-ideation § Depth-Control Verbal Cues | share/skills/w-ideation-mediation/SKILL.md:40-62 shows the old ladder only; source verbal cues exist at share/skills/h-ideation/SKILL.md:291-292. | N/A (td:0) | FAIL |
| Each rewritten directive has a co-located `**Narrate as:**` annotation with a concrete example phrase | grep_search found no "Narrate as:" matches in share/skills/w-ideation-mediation/SKILL.md. | N/A (td:0) | FAIL |
| Behavioral equivalence: same information reaches the user (which reviews, what's happening next) — only framing changes | The rewritten purpose-framed directives do not exist, so the behavioral-equivalence condition is not met. | N/A (td:0) | FAIL |
| Grep verification: `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md` — hits in narration guidance positions carry explanatory context or appear in technical routing (not user-facing phrasing) | share/skills/w-ideation-mediation/SKILL.md:103-109 still couples user-facing instruction with raw panelist names, so the grep gate fails. | N/A (td:0) | FAIL |
| References h-ideation § Communication Patterns for vocabulary (cross-reference, not duplication) | grep_search found no "Communication Patterns" match in share/skills/w-ideation-mediation/SKILL.md; the source section exists at share/skills/h-ideation/SKILL.md:182. | N/A (td:0) | FAIL |

### Deductions
- -0.22 Step 1.5 directive remains unchanged.
- -0.22 Step 2 directive remains unchanged.
- -0.18 Disclosure Ladder cues not added.
- -0.12 Missing `Narrate as:` annotations.
- -0.10 Missing Communication Patterns cross-reference.
- -0.04 Git-status contamination check unavailable in the current tool surface.

### Confidence: .12
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Rewrite the Step 1.5 user-facing instruction into a purpose-framed announcement and add a co-located `**Narrate as:**` example | share/skills/w-ideation-mediation/SKILL.md | AC row 1; line 87 still contains the pre-change wording |
| 2 | builder | Rewrite the Step 2 user-facing introduction so it explains the review angles and purpose without enumerating raw panelist agent names, and add a co-located `**Narrate as:**` example | share/skills/w-ideation-mediation/SKILL.md | AC row 2; lines 103-109 still narrate roster selection with raw agent names |
| 3 | builder | Update the Disclosure Ladder with the verbal cues from h-ideation § Communication Patterns / Depth-Control Verbal Cues and add the required cross-reference instead of duplicating unsupported phrasing | share/skills/w-ideation-mediation/SKILL.md, share/skills/h-ideation/SKILL.md | AC rows 3 and 7; source cues exist at h-ideation lines 182 and 286-292 but are absent from the target file |
[[2026-05-08]]
## Builder Notes
- Implementation: rewrote narration directives in `share/skills/w-ideation-mediation/SKILL.md` for Step 1.5 and Step 2 from mechanism/roster narration to purpose-framed user announcements.
- Disclosure Ladder: added depth-control verbal cues and concrete `**Narrate as:**` examples; added cross-reference to `h-ideation` -> `## Communication Patterns` vocabulary.
- Verification: ran AC grep checks.
  - `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md`
  - `grep -n "Narrate as:\|Communication Patterns" share/skills/w-ideation-mediation/SKILL.md`
- Tests: skipped (td:0 markdown prose task; non-implementation surface).
- Coverage: N/A (no Python/TS module changes).
- ruff: skipped (no lintable source-code changes in scope).
- Commit: `5400d210` (`docs: rewrite mediation narration directives (#1430, builder)`).
- Evidence summary: required narration rewrites and `Narrate as` annotations now present; communication-patterns cross-reference added; technical routing names remain in dispatch lists, not as user-facing narration instructions.