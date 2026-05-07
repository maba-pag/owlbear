# AC Quality Skill — Two-Tier, Six-Rule Schema

> **Owning task:** #1404 — A1: h-ac-quality skill — unified two-tier, six-rule AC schema
> **Date:** 2026-05-08 **Status:** Complete

## 1. Context and Question

The pipeline's 5 worst tasks (by iteration count) all trace to vague AC wording. #1061 spiraled through 10+ rounds, 6 FAILs, 3 loop-breakers. Root cause: AC with naked quantifiers ("match exactly," "all modes") that are infinitely divisible — every reviewer pass finds a new interpretation.

**Question:** Is the proposed two-tier, six-rule AC quality schema (from Brief #1403) sound, feasible, and well-grounded in prior art? Does it fit the existing skill ecosystem without duplication?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | OwlBear `w-task-decomposition` — AC durability principles | Codebase | 0.9 — current AC drafting rules |
| S2 | OwlBear `w-arch-review` — test-depth annotation, AC refinement | Codebase | 0.9 — current AC validation rules |
| S3 | OwlBear `w-task-verification` — AC quality scoring 1–5 | Codebase | 0.8 — downstream AC quality assessment |
| S4 | NextGenAnalysts — "How to Write Clear and Concise AC" (2025) | Web | 0.7 — 5 components: specific, testable, independent, user-focused, clear DoD |
| S5 | Atlassian — "What is Acceptance Criteria?" (2026) | Web | 0.7 — "testable statements focused on positive customer results" |
| S6 | AltexSoft — "AC: Purposes, Formats, Best Practices" (2023) | Web | 0.6 — "each AC must be independently testable with clear pass/fail" |
| S7 | OwlBear archive analysis — 5 worst tasks by iteration count | Codebase | 1.0 — empirical evidence of vague-AC failure modes |

## 3. Analysis

### 3.1 Current State: AC Rules Scattered Across 7+ Locations

| Location | AC Content | Gap |
|----------|-----------|-----|
| `w-task-decomposition` | Durability principles (testable, behavior-first, no-HOW) | No banned words, no tier distinction |
| `w-arch-review` | Test-depth annotation (td:0–2), user-action detection (M/S/C) | No systematic AC quality validation |
| `w-task-verification` | Quality scoring 1–5, vague-AC flagging | Post-hoc; doesn't prevent vague AC |
| `r-pipeline-protocol` | "Concrete AC required," test-depth routing table | One-line rule, no schema |
| `w-code-review` | "Note every AC line" for verification | Consumer, not definer |
| `w-research` | "Follow-up tasks without AC" check | Entry gate only |
| `w-tdd-red` | "Write failing tests from AC" | Consumer, not definer |

**Finding:** No single skill defines what constitutes a well-formed AC line. Rules are scattered, incomplete, and post-hoc. The planner drafts AC without a quality schema; the architect refines without a systematic checklist; the auditor scores quality after the damage is done.

### 3.2 Proposed Schema vs. Prior Art

| Rule | OwlBear Proposed | Prior Art Alignment |
|------|-----------------|---------------------|
| Meta-rule (independent verifiability) | "Every AC line must be independently verifiable by a downstream agent without access to the author's intent" | S4: "independently verifiable"; S6: "independently testable with clear pass/fail" |
| B1 (function-scoped) | Name the function/endpoint/command under test | S4: "specific and measurable conditions" — our variant scopes to code artifacts |
| B2 (input→output pairs) | Concrete input condition + expected observable output | S4: "define testable conditions"; S5: "testable statements" |
| B3 (banned words) | 7 banned words: all, every, correctly, properly, exactly, valid, appropriate | S4: "vague terms like 'user-friendly,' 'efficient,' 'intuitive'" — we extend to quantifiers |
| P1 (agent-scoped) | Name the agent, skill, or pipeline stage | Novel — no prior art for AI-agent pipeline AC |
| P2 (observable artifact) | Before→after difference in artifact/state | S4: "clear definition of done" |
| P3 (verification method) | Artifact inspection, stage-transition audit, etc. | S6: "objectively verifiable" — we make the method explicit |

**Finding:** B1–B3 are well-grounded in standard AC best practices, adapted for code-scoped verification. P1–P3 are novel extensions for process/workflow AC in AI agent pipelines — no direct prior art exists, but they follow the same principles (scope, testability, verification).

### 3.3 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| B3 banned words are too strict for legitimate use | Low | Low | "Unless followed by exhaustive enumeration" escape hatch |
| P3 verification method produces boilerplate | Medium | Low | Monitor first 10 process AC; drop P3 if consistently unhelpful (per brief) |
| Schema rigidity for edge-case tasks | Medium | Medium | Meta-rule as fallback — rules are floors, not ceilings |
| Overlap with existing `w-task-decomposition` durability principles | Low | Low | A2 (#1405) will reconcile; h-ac-quality becomes the authority, `w-task-decomposition` references it |

## 4. Recommendation

**Proceed as specified in the brief.** Create `h-ac-quality` skill with the two-tier, six-rule schema.

- **Confidence: 0.90** — Schema is empirically grounded (archive analysis), aligns with prior art, and fills a clear gap in the skill ecosystem.
- **Challenge: SKIP** — Schema was already validated through ideation panel deliberation (Brief #1403). This research validates feasibility and fit, not option selection.

**Implementation notes for the builder:**
- Category: `h-` (Handbook) — loaded on-demand by planner (drafting) and architect/challenger (validation)
- Target: ~120–150 lines. Concise enough to load in full context.
- Structure: meta-rule → Tier 1 (B1–B3) → Tier 2 (P1–P3) → two-pass validation → bad→good examples → checklist
- The skill defines the schema. It does NOT update consumers — A2 (#1405) and A3 (#1406) handle that.

## 5. Follow-up Tasks

Already on board:
- **#1405** — A2: Planner skill update (reference h-ac-quality for drafting) — `depends_on: [1404]`
- **#1406** — A3: Architect/challenger skill update (AC validation via h-ac-quality) — `depends_on: [1404]`

No additional follow-ups needed.
