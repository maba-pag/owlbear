---
id: 1430
title: 'P1-02: Directive rewrites in w-ideation-mediation/SKILL.md'
status: archived
priority: medium
created: 2026-05-08T01:00:48.467318+00:00
updated: 2026-05-08T15:33:53.964838+00:00
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
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner: not dispatched. td:0 markdown task with no task-scoped test artifact; this workspace's td:0 review path skips quality-runner because scoped mode requires non-empty `test_paths`.
- pytest: skipped for the same reason.

### Lint: skipped
- td:0 markdown skill task; no runnable scoped lint surface through quality-runner.

### Coverage: skipped
- td:0 markdown skill task; no code module changed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
- Skipped. No `TestFromAC_*` classes exist and all AC lines were marked td:0 by Architecture Review.

#### Security Review
- No security issues in scope. The change surface is markdown narration guidance only.

#### Test Integrity
- Skipped. No task-scoped test file exists.

#### Test Quality
- Skipped. No task-scoped test file exists.

#### Data Safety
- No issues found in scope.

#### Implementation-Aware Gaps
- No issues found. The previously missing rewrites are now present in `share/skills/w-ideation-mediation/SKILL.md`:
  - Disclosure Ladder now cross-references `h-ideation -> ## Communication Patterns` at line 40 and includes verbal cues / concrete `Narrate as:` examples at lines 50, 59-61, and 68-70.
  - Step 1.5 now requires a user-benefit announcement at line 97 with a co-located example at line 99.
  - Step 2 now requires a purpose-and-angle introduction at line 115 with a co-located example at line 117.
  - Raw internal names remain only in technical routing lists at lines 101-104 and 120-123, not in the user-facing narration examples.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- One prior `## Review Evidence` section exists in the task body; the current file state resolves the previously reported content gaps.
- Builder commit `5400d210` is present in `.git/logs/refs/heads/dev` and `.git/logs/HEAD`; direct diff inspection was not available from this tool surface, so changed-file scope was reconstructed from the task scope, builder notes, and direct artifact reads.
- Dirty-tree contamination could not be checked without git-status access. Small confidence deduction only.
- Step 2 line 118 still says "State the signal and selected roster explicitly." Brief Pair 2 treats explicit roster disclosure as acceptable when surfaced as user-visible review labels with purpose; current user-facing narration at line 117 satisfies that bar, so this remains informational rather than blocking.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Step 1.5 directive rewritten: no longer instructs agent to name internal switching mechanism; instead instructs purpose-framed announcement (what's happening + why) | `share/skills/w-ideation-mediation/SKILL.md:97` rewrites the instruction to a user-benefit announcement and `:99` provides the concrete `Narrate as:` example. This aligns with the result-only wording in `.owlbear/briefs/draft-ideation-ux/brief.md:136-143` and `share/skills/h-ideation/SKILL.md:259-261`. | N/A (td:0) | PASS |
| Step 2 directive rewritten: no longer instructs agent to enumerate panelist agent names; instead instructs purpose-framed introduction (which reviews + why those angles) | `share/skills/w-ideation-mediation/SKILL.md:115` instructs introduction by purpose and angle and `:117` gives the concrete example. User-facing narration uses review labels, while raw agent names sit only in technical routing at `:120-123`. This matches brief Pair 2 at `.owlbear/briefs/draft-ideation-ux/brief.md:144-150`. | N/A (td:0) | PASS |
| Disclosure Ladder updated with verbal cues from h-ideation § Depth-Control Verbal Cues | `share/skills/w-ideation-mediation/SKILL.md:40` cross-references `h-ideation -> ## Communication Patterns`; `:59` and `:68` add the verbal cues; `:50`, `:61`, and `:70` add concrete `Narrate as:` phrasing. Source cues exist at `share/skills/h-ideation/SKILL.md:286-292`. | N/A (td:0) | PASS |
| Each rewritten directive has a co-located `**Narrate as:**` annotation with a concrete example phrase | Disclosure Ladder `:50`, `:61`, `:70`; Step 1.5 `:99`; Step 2 `:117`. | N/A (td:0) | PASS |
| Behavioral equivalence: same information reaches the user (which reviews, what's happening next) — only framing changes | Step 1.5 `:99` still tells the user what happens next and why; Step 2 `:117` still tells the user which reviews run and what each checks. The framing changes from internal mechanism / roster narration to purpose-first language. | N/A (td:0) | PASS |
| Grep verification: `grep -n "M3.5\|O15\|ideation-architect\|ideation-security" share/skills/w-ideation-mediation/SKILL.md` — hits in narration guidance positions carry explanatory context or appear in technical routing (not user-facing phrasing) | Internal-name hits in `share/skills/w-ideation-mediation/SKILL.md:101-104` and `:120-123` are dispatch lists. User-facing `Narrate as:` lines at `:99` and `:117` use explanatory context rather than raw internal names. `O15` and `M3.5` hits remain in section headers / technical instructions, not user-facing narration. | N/A (td:0) | PASS |
| References h-ideation § Communication Patterns for vocabulary (cross-reference, not duplication) | `share/skills/w-ideation-mediation/SKILL.md:40` explicitly references `h-ideation -> ## Communication Patterns`; the source section exists at `share/skills/h-ideation/SKILL.md:182`. | N/A (td:0) | PASS |

### Deductions
- -0.03 Dirty-tree contamination could not be checked with the available tool surface.
- -0.02 Exact commit diff was not accessible; commit presence was verified via `.git/logs` and the scoped artifact was read directly.
- -0.01 Step 2 retains "selected roster explicitly" wording at `share/skills/w-ideation-mediation/SKILL.md:118`, but the surrounding narration and brief guidance keep it within the allowed user-visible-review framing.

### Confidence: .94
### Verdict: PASS
[[2026-05-08]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are SKILL.md (agent-executable, OUT of scope). No IN-scope prose docs reference the directive phrasing. |
| 2 | Module docstrings | No | N/A | No Python modules changed. |
| 3 | External attribution | No | N/A | No external repo patterns used; changes draw from existing h-ideation vocabulary. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc produced by this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/ideation.excalidraw` has `describes: share/skills/w-ideation-mediation/**, share/skills/h-ideation/**` — both changed files match. Footer updated to `Last verified: 2026-05-08 (a7a9a679)`. Commit: f72650aa. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| share/skills/w-ideation-mediation/SKILL.md | OUT (agent-executable SKILL.md) | N/A — not edited by doc-writer |
| share/skills/h-ideation/SKILL.md | OUT (agent-executable SKILL.md) | N/A — not edited by doc-writer |
| share/diagrams/ideation.excalidraw | IN (share/diagrams/*.excalidraw) | Footer updated (Item 5 describes-match) |

### Files Updated
- share/diagrams/ideation.excalidraw (footer: 331993d7 → a7a9a679)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1430-*` files existed)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Step 1.5 directive rewritten | w-ideation-mediation/SKILL.md:97 purpose-framed announcement; :99 Narrate as example | PASS |
| Step 2 directive rewritten | :115 purpose-and-angle introduction; :117 Narrate as example; raw names only in dispatch routing :120-123 | PASS |
| Disclosure Ladder updated with verbal cues | :40 cross-ref to h-ideation Communication Patterns; :50, :59-61, :68-70 verbal cues and Narrate as examples | PASS |
| Each directive has Narrate as annotation | :50, :61, :70, :99, :117 — five co-located annotations | PASS |
| Behavioral equivalence | Step 1.5 still communicates what happens next + why; Step 2 still communicates which reviews + purpose. Framing changed, info preserved. | PASS |
| Grep verification | All hits in section headers, dispatch routing lists, or technical instructions — none in user-facing narration lines | PASS |
| References h-ideation Communication Patterns | :40 explicit cross-reference; source at h-ideation/SKILL.md:182 | PASS |

### Test Results
- pytest: 2972 passed, 178 failed (background debt — memory model, engine accessor, import errors), 0 attributable to this markdown-only task
- vitest: 1109 passed, 0 failed
- ruff: 12 violations (background debt in copilot_auth.py, test_root.py, test_test_root.py — none in task scope)
- eslint: 4 violations (background — usePolling.ts, unused vars)

### Architect Quality: 5/5
Excellent AC: named exact lines to rewrite, specified the format (`**Narrate as:**`), provided a concrete grep verification command, and explicitly scoped behavioral equivalence. Clean implementation path with zero ambiguity.

### Deduction Breakdown
- No AC lines without evidence: 7/7 PASS → no deduction
- No lint in task scope → no deduction
- AC quality 5/5 → no deduction
- Reviewer evidence present and detailed (PASS, .94) → no deduction
- No task-scope test failures → no deduction
- Builder commit 5400d210 verified → no deduction

### Confidence: .98
### Action: archive