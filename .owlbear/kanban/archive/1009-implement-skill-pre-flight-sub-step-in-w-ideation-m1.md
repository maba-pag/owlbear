---
id: 1009
title: Implement skill pre-flight sub-step in w-ideation M1
status: archived
priority: medium
created: 2026-04-18 21:57:35.239825+00:00
updated: 2026-04-19 16:40:39.540051+00:00
tags:
- type:improvement
- scope:skills
parent:
depends_on:
- 997
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Problem
w-ideation M1 lacks a skill pre-flight check. Existing conventions in skill files may contradict assumptions made during problem narrowing, only surfacing at M3 when decisions are locked.

## Fix
Insert a "Skill Pre-Flight" sub-step in `share/skills/w-ideation/SKILL.md` Step 1 (M1), between current steps 5 and 6 (after narrowing, before writing Problem Statement).

## Acceptance Criteria
- [ ] w-ideation Step 1 includes a "Skill Pre-Flight" sub-step between "catch disguised solutions" (step 5) and "write Problem Statement" (step 6)
- [ ] Sub-step lists: extract 2-3 keywords → grep `share/skills/` and `share/instructions/` → skim matched sections → surface conflicts as M1 probes
- [ ] Sub-step includes 3+ keyword → skill examples (e.g., blocking → `r-pipeline-protocol`; kanban → `h-mcp-kanban`; agents → `agent-common.instructions.md`)
- [ ] Sub-step explicitly states: "1-2 minutes, not a substitute for M3 Explore"
- [ ] Verification Checklist updated to include skill pre-flight completion check
- [ ] No new tooling required — uses Mediator's existing `textSearch`/`fileSearch`

## Research
See `.owlbear/research/997-skill-preflight-ideation-m1.md`
[[2026-04-19]]
## Architecture Review

### AC Refinements (architect additions — binding)

The original AC is sound but missing two items surfaced by challenge:

- [ ] **AC-7 (new):** M1 turn-ending rule reference "steps 2–5 below" updated to include the new pre-flight step (probes from pre-flight also require `askQuestions` with `allowFreeformInput: true`)
- [ ] **AC-8 (new):** Sub-step includes empty-result path: "If no relevant matches → continue normally"

Additionally, the "1-2 minutes" scope bound (AC-4) should be complemented with an actionable call-count bound (e.g., "2-3 search calls + skim headlines") since time budgets are unenforceable for LLM agents. The existing precedent pre-flights (Knowledge Pre-flight, Research Pre-Flight) use step counts, not time.

### Builder Guidance

- This is a **markdown-only skill file edit** — no Python code. The test-writer should pass through.
- The M1 exit criteria ("Problem Statement written; Investment Tier set; Critic check passed") do NOT need updating — the pre-flight is a means to a better Problem Statement, not an exit criterion. The Verification Checklist update (AC-5) is the tracking mechanism.
- Consider whether `share/agents/` should also be a grep target (conventions also live in agent personas/tool allowlists), but the current scope (`share/skills/` + `share/instructions/`) is the primary convention surface and avoids noise.
- For noisy keywords (e.g., "task", "pipeline"), the builder should include a "skim top matches" bound in the sub-step text rather than exhaustive reads.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One sub-step in one file |
| Interface clarity | PASS (after refinement) | 8 AC lines cover location, workflow, examples, scope, checklist, cross-refs |
| Dependency correctness | PASS | #997 archived (research complete) |
| Module layering | N/A | Skill file, not code |
| TDD compliance | N/A | No Python code — pass-through tag needed (`docs`) |
| KISS/YAGNI | PASS | Minimal scope, follows existing pre-flight pattern |
| Premise challenge | PASS | Research doc cites concrete #973 loop-back as evidence |
| Pattern consistency | PASS | Follows Knowledge Pre-flight and Research Pre-Flight structural precedent |
| Security surface | PASS | No system boundaries |
| Single domain | PASS | Skills/ideation domain only |

### Challenge Results

- Challenger: **reconsider** (confidence 0.60)
- Material findings accepted: C1 (askQuestions scope ref) → added AC-7; C2 (empty-result path) → added AC-8
- C3 (unchallenged research insertion point): rebutted — architect independently confirms Option A over B/C: keywords clear at step 5, Problem Statement not yet locked, Option C requires loop-back
- C4 (M1 exit criteria): noted — exit criteria are the destination, pre-flight is a means; Verification Checklist update (AC-5) is sufficient
- B1–B3 (blind spots): noted as builder guidance, non-blocking

### Non-Implementation Note

This task produces no testable Python code. It requires pass-through tag `docs` for the test-writer pipeline stage. Tag not added (edit_task unavailable) — test-writer and orchestrator should treat `scope:skills` + this architecture note as pass-through signal.

### Verdict: APPROVE (after refinement)
### Action Taken: Advanced to todo with 2 additional AC lines (AC-7, AC-8) and builder guidance appended
[[2026-04-19]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `share/skills/w-ideation/SKILL.md` — no Python interfaces, no testable implementation.
- Architect note in task body explicitly confirms: "produces no testable Python code — pass-through signal: scope:skills".
- Step 2a heuristic: AC files are `.md` / `SKILL.md` only; no `implement`, `function`, `class`, `src/`, `.py` keywords present.
- No tests written, no test file created.
[[2026-04-19]]
## Builder Notes

**Files changed:** `share/skills/w-ideation/SKILL.md` (1 file, markdown-only edit)

**Changes applied:**
- AC-1/AC-2: Inserted Step 6 "Skill Pre-Flight" sub-step between step 5 (catch disguised solutions) and old step 6 (write Problem Statement). Old steps 6→7, 7→8, 8→9.
- AC-3: Sub-step lists keywords → `textSearch`/`fileSearch` → skim headers → surface as probes. Three examples provided: "blocking" → `r-pipeline-protocol`; "kanban" → `h-mcp-kanban`; "agents" → `agent-common.instructions.md`.
- AC-4 + architect refinement: Scope bound "1–2 minutes, 2–3 search calls + skim headlines — not a substitute for M3 Explore" (time + call-count bound combined per architect guidance).
- AC-5: Verification Checklist M1 entry updated to include pre-flight completion check.
- AC-6: No new tooling — uses Mediator's existing `textSearch`/`fileSearch`.
- AC-7: Turn-ending rule updated from "steps 2–5 below" → "steps 2–6 below"; sub-step 6d explicitly notes conflicts require `askQuestions` with `allowFreeformInput: true`.
- AC-8: Empty-result path added as step 6e: "If no relevant matches → continue normally."

**Test results:** No Python code — pass-through (scope:skills, markdown-only). No pytest run required.

**Lint status:** N/A (markdown file).

**Commit:** 64ce40c9
[[2026-04-19]]
## Review Evidence

**Scope:** Markdown-only edit — `share/skills/w-ideation/SKILL.md`. No Python code, no tests required (pass-through: `scope:skills`).

**Tests:** N/A — pass-through confirmed by test-writer and architect notes. No pytest run required.
**Lint:** N/A — markdown file.
**Coverage:** N/A.

**AC Compliance:**

| AC | Evidence | Status |
|----|----------|--------|
| AC-1: Pre-flight sub-step between step 5 and write-Problem-Statement | Step 6 "Skill Pre-Flight" sits between step 5 (catch disguised solutions) and step 7 (write Problem Statement) | PASS |
| AC-2: keywords → grep skills + instructions → skim → surface probes | Steps 6a–6d match workflow exactly | PASS |
| AC-3: 3+ keyword → skill examples | "blocking" → `r-pipeline-protocol`; "kanban" → `h-mcp-kanban`; "agents" → `agent-common.instructions.md` (3 verbatim examples) | PASS |
| AC-4: "1-2 minutes, not a substitute for M3 Explore" | Step 6 header: "*(1–2 minutes, 2–3 search calls + skim headlines — not a substitute for M3 Explore)*" | PASS |
| AC-5: Verification Checklist updated | Line 482 M1 entry: "Skill Pre-Flight run (keywords extracted, share/skills/ + share/instructions/ scanned, conflicts surfaced or empty-result path confirmed)" | PASS |
| AC-6: No new tooling — existing textSearch/fileSearch | Step 6b: "Use `textSearch` / `fileSearch` to grep" | PASS |
| AC-7 (arch): Turn-ending rule updated to include step 6; conflicts require askQuestions freeform | "steps 2–6 below" in turn-ending rule; step 6d: "end with `askQuestions` (`allowFreeformInput: true`)" | PASS |
| AC-8 (arch): Empty-result path | Step 6e: "If no relevant matches → continue normally." | PASS |

**Pass 1 Critical Checks:**
- 5.0 TestFromAC: No TestFromAC_* classes — SKIP (pass-through)
- 5.1 Security: Markdown-only, no system boundaries — PASS
- 5.2–5.5: N/A — pass-through
- 5.7 Builder Loop: Single builder notes section, clean first pass — PASS

**Deductions:** 0

**Verdict:** PASS — confidence .96
**Action:** Advance to docs
[[2026-04-19]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → `copilot-instructions.md` | No | N/A | Skill content changed internally; `.github/copilot-instructions.md` has no w-ideation entry; skill name/description unchanged |
| 2 | Python module docstrings | No | N/A | Markdown-only edit — no `.py` files touched (confirmed by builder notes + review evidence) |
| 3 | External attribution | No | N/A | All research sources are internal codebase files only |
| 4 | CLI changes → `README.md` | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | `.owlbear/research/997-skill-preflight-ideation-m1.md` exists; referenced in task body; #1009 is the documented follow-up task |

**Files updated:** None required.
**Scratch files:** No `.owlbear/scratch/1009-*` files found — nothing to clean.
**Commit:** No docs commit needed (deliverable was the skill file edit itself, committed as `64ce40c9` by builder).
[[2026-04-19]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-1: Pre-flight sub-step between step 5 and write-Problem-Statement | SKILL.md L49: Step 6 "Skill Pre-Flight" between step 5 (disguised solutions) and step 7 (write Problem Statement) | PASS |
| AC-2: keywords → grep skills + instructions → skim → surface probes | SKILL.md L50–54: Steps 6a–6d match workflow | PASS |
| AC-3: 3+ keyword → skill examples | SKILL.md L50: "blocking" → r-pipeline-protocol; "kanban" → h-mcp-kanban; "agents" → agent-common.instructions.md | PASS |
| AC-4: "1-2 minutes, not a substitute for M3 Explore" | SKILL.md L49: "*(1–2 minutes, 2–3 search calls + skim headlines — not a substitute for M3 Explore)*" | PASS |
| AC-5: Verification Checklist updated | SKILL.md L482: M1 entry includes "Skill Pre-Flight run (keywords extracted, share/skills/ + share/instructions/ scanned, conflicts surfaced or empty-result path confirmed)" | PASS |
| AC-6: No new tooling — existing textSearch/fileSearch | SKILL.md L51: "Use `textSearch` / `fileSearch` to grep" | PASS |
| AC-7 (arch): Turn-ending rule updated; conflicts require askQuestions freeform | SKILL.md L42: "steps 2–6 below"; L53: step 6d ends with askQuestions (allowFreeformInput: true) | PASS |
| AC-8 (arch): Empty-result path | SKILL.md L54: "If no relevant matches → continue normally." | PASS |

### Test Results
- pytest: 685 passed, 6 failed (all in mcp-knowledge — pre-existing, outside task scope)
- ruff: clean

### Architect Quality: 5/5
Specific, complete, 8 AC lines with clear location/content/verification paths. Challenger findings properly integrated as AC-7/AC-8. Builder guidance actionable (call-count bound, pass-through note). Follows existing pre-flight precedent.

### Deduction Breakdown
- AC lines with no evidence: 0 → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: No (5/5) → no deduction
- Missing reviewer evidence: No (detailed, PASS .96) → no deduction
- Full-suite failures in task scope: 0 → no deduction

### Confidence: .98
### Action: archive