---
id: 996
title: Fix ideator/w-ideation askQuestions instruction conflict
status: archived
priority: important
created: 2026-04-18T21:26:18.176169+00:00
updated: 2026-04-19T12:56:59.654202+00:00
tags:
- type:improvement
- scope:agents
- scope:skills
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem

The ideator agent's critical_rules state "askQuestions for decisions ... never stop to wait for a plain-text reply when a structured question can capture the input" with examples (tier selection, approach choice, panelist veto, Brief approval, moment transitions). The w-ideation skill describes M1 (Understanding) as natural investigative dialogue and only mandates askQuestions for the inter-M1/M2 tier check.

These conflict. When executing M1 probes, the model can plausibly read the skill's narrative as "M1 is dialogue, not a decision point" and end a turn with prose questions. This causes a silent stall.

## Fix

1. Tighten `share/agents/ideator.agent.md` critical_rules: "askQuestions is the only way to end a turn that requires a user reply, including investigative probes. Use `allowFreeformInput: true` when there are no fixed options."
2. Update `share/skills/w-ideation/SKILL.md` Step 1 to explicitly say "every M1 probe ends with askQuestions."
3. Add a worked askQuestions-with-freeform example to one or both files.

## Acceptance Criteria

- ideator.agent.md critical_rules contains the unambiguous "askQuestions is the only way to end a user-facing turn" clause.
- w-ideation Step 1 has the explicit "every probe ends with askQuestions" instruction.
- One worked askQuestions example with `allowFreeformInput: true` exists in either file.
- No remaining conflict between the two documents.

## Context

Surfaced during ideation session for #973. See `.owlbear/briefs/draft-blocked-task-dr-enforcement/context.md`.

## Extension (added from ideation session for #984 — agent-audit prompt rewrite)

### Additional fix

The "use confidence (0.0–1.0) and one `recommended` choice when trade-offs exist" rule lives in `ideator.agent.md` critical_rules but is mentioned only briefly in `w-ideation` Step 4 and not at all in Step 5 walkthroughs or other askQuestions calls. Mediator agents trained to follow the skill (not the agent file) will miss it.

### Additional acceptance criteria

- `w-ideation` Step 4 contains a worked askQuestions example showing 3-4 options with **explicit per-option confidence (0.0–1.0)** and one option marked `recommended: true`.
- `w-ideation` Step 5 (Brief approval and walkthrough) contains a worked example or explicit instruction that any options-bearing askQuestions during walkthrough MUST carry per-option confidence when genuine trade-offs exist (not for procedural "next/back" choices).
- The rule is stated in `w-ideation` itself, not only in the agent file (skills are the authority per `r-pipeline-protocol`).

### Context

During ideation session for #984, Mediator presented a 4-option decision (scope/decomposition smell handling) without confidence scores. User had to explicitly call this out: *"whats your recommendation and your confidence in each option? (when done we need to improve your workflow, i am missing these info)"*. The rule existed in the agent file but not in the skill the Mediator was nominally following.
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/996-ideator-askquestions-conflict.md (updated)
- Sources: 6 studied, 4 high-relevance
- Original 4 AC: all met (validated in v1)
- Extension 3 AC: 3 gaps remain — confidence/recommended worked examples missing from w-ideation Steps 4–5; rule stated only in agent file
- Recommendation: one follow-up task to add worked examples + standalone rule to w-ideation (confidence: 0.90)
- Follow-up tasks created: #1012 at research
- Decision requests: none (T1 — docs-only improvement)
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Original askQuestions conflict fix only; extension AC properly split to #1012 |
| Interface clarity | PASS (with guidance) | AC #2 says "Step 1" but AC #4 ("no remaining conflict") requires M2/M3 coverage too — see builder guidance below |
| Dependency correctness | PASS | No deps; #1012 correctly depends_on this task |
| Module layering | N/A | Agent/skill markdown files only |
| TDD compliance | PASS | Non-implementation task; needs `agent` pass-through tag (see below) |
| KISS/YAGNI | PASS | Minimal targeted fix |
| Premise challenge | PASS | Real silent-stall failure observed in ideation session for #973 |
| Pattern consistency | PASS | Follows existing agent/skill annotation patterns |
| Security surface | PASS | No security implications |
| Single domain | PASS | Agents/skills domain only |

### Challenge Results

- Challenger: **block** (confidence 0.45)
- Architect response: **partially accepted, revised approach**
  - C1 (M2/M3 gap): **Accepted.** Valid finding — the Turn-ending rule is M1-scoped but agent file promises M1–M3. Builder must fix this.
  - C2 (pass-through tag): **Accepted.** `agent` tag must be added. Architect lacks `edit_task` tool — noted as mandatory pre-requisite for test-writer.
  - C3 (extension AC in body): **Accepted.** Extension AC are #1012's scope. Builder/test-writer should focus on original 4 AC only. Extension section in body is context, not in-scope AC.
  - Alternative (file-level preamble): **Accepted as recommended approach.** Structurally superior to per-step annotations.

### Builder Guidance

**Scope clarification:** The original 4 AC are in-scope. The "Extension" section and "Additional acceptance criteria" are tracked in #1012 — do not implement those here.

**M2/M3 gap (AC #4 fix):** The Turn-ending rule in `w-ideation/SKILL.md` Step 1 is scoped to "every M1 step." The agent file (`ideator.agent.md` critical_rules) says "M1–M3 probes." This conflict must be resolved. Recommended approach:

1. Promote the Turn-ending rule from Step 1 to a **file-level preamble** (after the frontmatter, before Step 0). Reword: "Every turn that elicits a user reply ends with `askQuestions`. Use `allowFreeformInput: true` for open probes; use structured `options` for decisions."
2. Remove the M1-scoped Turn-ending rule paragraph from Step 1 (the file-level rule supersedes it; keep the per-step `→ end with askQuestions (freeform)` annotations on steps 2-5 as reminders).
3. Add `→ end with askQuestions (freeform)` annotations to Step 2 items 2-3 (M2 probes).
4. Step 3 M3 is subagent-driven; the panelist veto already mentions askQuestions. No change needed.

**Files to modify:**

- `share/skills/w-ideation/SKILL.md` — promote Turn-ending rule to preamble, annotate M2 steps
- `share/agents/ideator.agent.md` — verify alignment (current text is already correct, no changes expected)

**Pass-through tag:** This task modifies agent/skill markdown files only — no testable Python code. The `agent` tag MUST be added before the test-writer processes this task. The orchestrator or test-writer should add it.

### Verdict: APPROVE

### Action Taken: Advanced to todo with architecture guidance for M2/M3 gap fix and pass-through tag requirement

[[2026-04-19]]

## Test-Writer Notes

- Non-impl pass-through: AC references only `.agent.md` and `SKILL.md` files — no testable Python interfaces exist.
- Scanned AC keywords: no `implement`, `function`, `class`, `src/`, `.py`, `endpoint`, or `API` references found.
- Files in scope: `share/agents/ideator.agent.md`, `share/skills/w-ideation/SKILL.md` — markdown documents only.
- Architecture review explicitly flags this as non-implementation; `agent` tag was recommended by architect but absent from task tags. Pass-through proceeds per Step 2a heuristic.
- No test file created.
[[2026-04-19]]

## Builder Notes

### Files changed

- `share/skills/w-ideation/SKILL.md` — 3 surgical edits:
  1. Added file-level Turn-ending rule preamble (blockquote) after intro paragraph, before Step 0, with worked `allowFreeformInput: true` example
  2. Added "→ Items 2–5 are investigative probes — each ends with `askQuestions` using `allowFreeformInput: true`" annotation to Step 1
  3. Added "→ end with askQuestions (freeform)" inline to Step 2 items 2 and 3
- `share/agents/ideator.agent.md` — 1 surgical edit:
  - Changed `**askQuestions for decisions.**` critical rule to `**askQuestions for all user-facing turns.**`; added "including investigative probes", "askQuestions is the only way to end a turn that requires a user reply", and "Use `allowFreeformInput: true` when there are no fixed options"

### AC Evidence

- AC #1 (agent file unambiguous clause): ✅ — "askQuestions is the only way to end a turn that requires a user reply — including investigative probes"
- AC #2 (Step 1 explicit instruction): ✅ — "→ Items 2–5 are investigative probes — each ends with `askQuestions` using `allowFreeformInput: true`"
- AC #3 (worked freeform example): ✅ — preamble blockquote contains full inline example with `allowFreeformInput: true`
- AC #4 (no remaining conflict): ✅ — preamble is file-level (M1–M6), agent file says M1–M3 probes; both now consistent; Step 2 annotations cover M2 probes

### M2/M3 gap fix (per architect builder guidance)

- Preamble promotes Turn-ending rule to file-level scope — covers all moments including M2/M3
- Step 2 items 2–3 annotated per builder guidance
- Step 3 unchanged (subagent-driven; panelist veto already mentions askQuestions)

### Test results

Non-implementation pass-through. No Python code changed. No test suite applicable.

### Lint

Markdown files only. No ruff/tsc scope.
[[2026-04-19]]

## Review Evidence

### Test Results

Non-implementation pass-through — markdown agent/skill files only. No Python/TS test suite applicable. No `TestFromAC_*` classes exist. Quality-Runner not invoked (no testable code).

### Lint Results

Markdown files only. No ruff/tsc scope. No lint applicable.

### Coverage

N/A — no source code touched.

### AC Compliance

| AC | Evidence | Status |
|----|----------|--------|
| #1 — ideator.agent.md unambiguous clause | "askQuestions is the only way to end a turn that requires a user reply — including investigative probes" (critical_rules, line ~42) | PASS |
| #2 — w-ideation Step 1 explicit instruction | "→ Items 2–5 are investigative probes — each ends with `askQuestions` using `allowFreeformInput: true`" (Step 1 annotation) | PASS |
| #3 — worked example with allowFreeformInput: true | Preamble blockquote contains full inline example: `askQuestions(title="Tell me more", questions=[{id: "q1", question: "What happened recently that made this feel urgent?", allowFreeformInput: true}])` | PASS |
| #4 — no remaining conflict | Preamble scoped to "all six moments — M1–M3 investigative probes and M4–M6 facilitated decisions alike"; agent file says "all user-facing turns including investigative probes" — documents consistent | PASS |

### Architect Guidance Compliance

- File-level preamble added (after intro paragraph, before Step 0) ✅
- M1-scoped Turn-ending rule replaced with Step 1 annotation ✅
- Step 2 items 2–3 annotated with `→ end with askQuestions (freeform)` ✅
- Step 3 unchanged (subagent-driven; panelist veto already mentions askQuestions) ✅

### TestFromAC Comparison

Not applicable — no TestFromAC classes.

### Security Review

Markdown prose only — no code paths, no secrets, no injection surface, no OWASP concerns.

### Deductions

0 deductions.

### Verdict

Confidence: .97 → **PASS**

### Action

Advancing to docs.
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Agent/skill markdown files only; copilot-instructions.md covers tech stack, not individual agent definitions |
| 2 | Module docstrings | No | N/A | No Python modules touched |
| 3 | External attribution | No | N/A | All sources in research doc are internal workspace files; no external repos or articles |
| 4 | CLI changes | No | N/A | No CLI commands changed |
| 5 | Research doc | Yes | Verified | `.owlbear/research/996-ideator-askquestions-conflict.md` exists, linked in task body, follow-up #1012 created |

### AC Verification (against actual file content)

- AC #1 ✅ — `ideator.agent.md` critical_rules contains: "askQuestions is the only way to end a turn that requires a user reply — including investigative probes"
- AC #2 ✅ — `w-ideation/SKILL.md` Step 1 annotation: "→ Items 2–5 are investigative probes — each ends with `askQuestions` using `allowFreeformInput: true`"
- AC #3 ✅ — SKILL.md preamble blockquote has full worked example with `allowFreeformInput: true`
- AC #4 ✅ — SKILL.md preamble scoped to "all six moments — M1–M3 investigative probes and M4–M6 facilitated decisions alike"; agent file says "all user-facing turns including investigative probes" — documents consistent, no remaining conflict

### Files Updated

- None (modified files are the documentation; no secondary docs require updates)

### Scratch Files Cleaned

- None found (`.owlbear/scratch/996-*` — no matches)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| #1 -- agent file unambiguous clause | Verified in ideator.agent.md critical_rules: "askQuestions is the only way to end a turn that requires a user reply -- including investigative probes" | PASS |
| #2 -- Step 1 explicit instruction | Verified in w-ideation/SKILL.md Step 1: "Items 2-5 are investigative probes -- each ends with askQuestions using allowFreeformInput: true" | PASS |
| #3 -- worked freeform example | Verified in w-ideation/SKILL.md preamble blockquote: askQuestions(title="Tell me more", questions=[{id: "q1", question: "What happened recently that made this feel urgent?", allowFreeformInput: true}]) | PASS |
| #4 -- no remaining conflict | Preamble scoped to "all six moments -- M1-M3 investigative probes and M4-M6 facilitated decisions alike"; agent file says "all user-facing turns including investigative probes" -- documents consistent | PASS |

### Test Results

- pytest: 664 passed, 6 failed (all 6 in serve/mcp-knowledge -- unrelated to task scope)
- ruff: clean

### Architect Quality: 4/5

Specific AC, clear scope boundary (extension split to #1012), builder guidance provided after challenger feedback. Minor gap: M2/M3 issue caught by challenger, not architect initial review -- but architect adapted well and provided detailed guidance.

### Deduction Breakdown

- 4 AC lines with specific file evidence: 0
- Lint clean: 0
- AC quality 4/5 (above threshold): 0
- Reviewer evidence section present, detailed, PASS at .97: 0
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge, unrelated)

### Confidence: 1.00

### Action: archive
