# Fix-Attempt Delegation in Builder TDD Workflow

> **Owning task:** #319 — Add fix-attempt delegation to builder tdd-workflow
> **Date:** 2026-04-05 **Status:** Complete (validation pass)

## 1. Context and Question

Task #319 requires updating the builder's `w-tdd-green` skill to delegate to `fix-attempt` after 2 verify failures, and updating the builder's `agents:` array. The question: **is the AC implementable, and are there gaps?**

**Finding:** Implementation already exists (commit `c2b93a9`, refined in `1d05a86`). Sibling tasks #318 (agent file) and #320 (tests) are archived. This research is a **validation pass** confirming the existing implementation satisfies all AC items.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `share/skills/w-tdd-green/SKILL.md` Steps 6.1–6.3 (current) | 1.0 — contains the delegation logic |
| S2 | `share/agents/builder.agent.md` L10 | 1.0 — `agents: [scribe, fix-attempt, quality-runner]` |
| S3 | `share/agents/fix-attempt.agent.md` Input/Output Contract | 1.0 — 5-field input, FIXED/FAILED output |
| S4 | `.owlbear/research/fresh-context-retry-builder.md` §3d-3e | .95 — parent design for integration flow |
| S5 | `.owlbear/research/fix-attempt-agent-design.md` §3a | .90 — AC validation for #318 |
| S6 | `tests/test_fix_attempt_delegation_320.py` (9 tests) | 1.0 — contract tests all pass |
| S7 | Git commit `c2b93a9` (2026-04-04) | 1.0 — builder commit for #319 |
| S8 | Git commit `1d05a86` (2026-04-04) | .95 — refinement by #320 builder |

## 3. Analysis

### 3a. AC Verification Against Current State

| AC | Evidence | Satisfied | Confidence |
|----|----------|-----------|------------|
| AC1: tdd-workflow updated with delegation | Step 6.3 "Delegate to fix-attempt" — retry_hint construction + subagent invocation (S1) | ✓ | .95 |
| AC2: Builder agents array includes fix-attempt | `agents: [scribe, fix-attempt, quality-runner]` (S2) | ✓ | 1.0 |
| AC3: Retry_hint with Reflexion-style feedback | Step 6.3 documents: "extract specific errors…Reflexion-style verbal diagnosis" (S1, S4) | ✓ | .95 |
| AC4: FIXED → commit, FAILED → blocks | FIXED → re-verify → Step 7; FAILED → `end_work(outcome="reject")` with routing (S1) | ✓* | .90 |
| AC5: 2 retries total cap | "exactly 2 failures (not 1, not 3)" with mandatory sequence (S1) | ✓ | .95 |

*AC4 note: Implementation uses `reject` with routing (to `todo` or `backlog`) instead of `block`. This is an improvement — reject feeds the task back into the pipeline at the correct point, while block would stall it pending manual intervention. The #320 auditor noted this as a minor refinement (-.01 deduction). Substantively equivalent.

### 3b. Test Coverage

9/9 contract tests pass (run verified 2026-04-05):

| Test Class | Tests | Coverage |
|------------|-------|----------|
| TestFromAC_RetryHintConstruction | 2 | AC1 error extraction + failing test ID |
| TestFromAC_InputContractValidation | 1 | AC2 cross-reference to fix-attempt.agent.md |
| TestFromAC_DelegationThreshold | 1 | AC3 exactly 2 failures |
| TestFromAC_FixedResultHandling | 3 | AC4 pytest + ruff + explicit reject |
| TestFromAC_FailedResultHandling | 1 | AC5 Channel B names both attempt sources |
| TestFromAC_BuilderWiring | 1 | AC2 prerequisite documentation |

### 3c. Board Sync Gap

| Task | Status | Implementation | Sync |
|------|--------|---------------|------|
| #318 | archived | fix-attempt.agent.md (commit `02a4207`) | ✓ |
| #319 | ideation | w-tdd-green Step 6.3 (commit `c2b93a9`) | ✗ — task not advanced |
| #320 | archived | test refinements (commit `1d05a86`) | ✓ |

#319 was implemented and committed but the kanban task was never advanced. Both sibling tasks completed the full pipeline.

## 4. Recommendation (.92 confidence)

**No new implementation needed.** All 5 AC items are satisfied by the existing code. The task should advance directly to `backlog` for pipeline verification (architect → fast-track to review → audit).

The one minor interpretation difference (AC4 "blocks" vs implementation "reject with routing") was reviewed and accepted by the #320 auditor at .97 confidence.

Challenge: SKIPPED — validation pass on existing implementation, no new recommendation to challenge.

## 5. Follow-up Tasks

No follow-up tasks needed. Implementation exists (commit `c2b93a9`), tests exist and pass (9/9), and sibling tasks are archived.
