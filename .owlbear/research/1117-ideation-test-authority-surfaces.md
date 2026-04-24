# Ideation Test Authority-Surface Hardening

> **Owning task:** #1117 — Ideation overhaul test proof hardening
> **Date:** 2026-04-24 **Status:** Complete

## 1. Context and Question

The #1039 review cycles (3 reviewer FAILs) identified that `TestFromAC_IdeatorRouterContract` and `TestFromAC_EarlyChallengeLane` only assert against a single authority surface each, when the contracts span multiple files. The implementation is correct — these are test-depth gaps only.

**Question:** What exact assertions are missing, and how should they be added to close the authority-surface gaps without weakening the existing 31 tests?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `share/agents/ideator.agent.md` (critical_rules + routing logic) | 1.0 | Post-discovery mediator handoff gate: 3 artifacts, name-paths-explicitly rule, askQuestions rule |
| 2 | `share/skills/w-ideation-discovery/SKILL.md` (Step 2, lines 72-83) | 1.0 | Authoritative early-challenge roster: always simplifier/firstprinciples, conditional outsider, bounded output |
| 3 | `share/skills/h-ideation-panel/SKILL.md` (Early Challenge Lane) | 1.0 | Critic-exclusion clause, default roster table, bounded-output rule |
| 4 | `tests/test_ideation_overhaul_static.py` (current 31 tests) | 1.0 | Current coverage map: 4 tests in IdeatorRouterContract, 4 tests in EarlyChallengeLane |
| 5 | `.owlbear/research/1115-ideation-test-proof-hardening.md` | 0.7 | Sibling research — glob-based discovery (#1118); no overlap with authority-surface gaps |

## 3. Analysis

### Gap Map

| AC | Gap | Current State | Required State |
|----|-----|---------------|----------------|
| AC 1 | IdeatorRouterContract misses mediator handoff gate | 4 tests: non-performer, discoverer route, mediator route, disable-model-invocation | Add: 3 artifact files (context.md, decisions.md, research-notes.md) referenced in mediator route; "Name the artifact paths explicitly" rule; "askQuestions ends every user-facing turn" rule |
| AC 2 | EarlyChallengeLane tests h-ideation-panel only | 4 tests all against `h-ideation-panel/SKILL.md` | Add: parallel assertions against `w-ideation-discovery/SKILL.md` Step 2 — default roster, conditional outsider, bounded output |
| AC 3 | Critic-exclusion rule is handbook-only | 1 test in h-ideation-panel | Add: explicit assertion that w-ideation-discovery roster is positively simplifier+firstprinciples (implicitly excludes critic), with comment explaining dual-surface rationale |

### Exact Assertions Needed

**AC 1 — IdeatorRouterContract additions (3 new tests):**

1. `test_ideator_mediator_route_names_three_artifacts` — assert `context.md`, `decisions.md`, and `research-notes.md` all appear in ideator.agent.md
2. `test_ideator_names_artifact_paths_explicitly` — assert `"Name the artifact paths explicitly"` in ideator.agent.md
3. `test_ideator_askquestions_every_turn` — assert `"askQuestions ends every user-facing turn"` in ideator.agent.md

**AC 2 — EarlyChallengeLane additions (3 new tests):**

4. `test_discovery_always_invokes_simplifier_and_firstprinciples` — assert `always: \`ideation-simplifier\`` and `always: \`ideation-firstprinciples\`` in w-ideation-discovery/SKILL.md
5. `test_discovery_outsider_is_conditional` — assert `conditional: \`ideation-outsider\`` in w-ideation-discovery/SKILL.md
6. `test_discovery_early_challenger_output_bounded` — assert `"Keep early challenger output bounded"` in w-ideation-discovery/SKILL.md

**AC 3 — Critic-exclusion dual-surface (1 new test):**

7. `test_critic_exclusion_dual_surface` — assert w-ideation-discovery Step 2 lists only simplifier, firstprinciples, and outsider (no `ideation-critic` in the roster), with a comment explaining that the explicit exclusion clause lives in h-ideation-panel while discovery uses positive roster specification

### Approach Comparison

| Criterion | A: Add tests only | B: Modify implementation + tests | C: Parametrize existing tests |
|-----------|-------------------|----------------------------------|-------------------------------|
| Scope | Minimal — 7 new tests | Adds implementation changes (out of scope) | Restructures existing test shape |
| Risk to existing 31 | None — additive only | Risk of breaking existing assertions | Medium — parametrize can introduce regressions |
| Clarity | Each gap = one test | Conflates test and impl work | Harder to read parametrized contract tests |
| Aligns with AC | Yes — AC 4 says "no test weakening" | AC says "test-depth refinement only" | Acceptable but unnecessary |

## 4. Recommendation (confidence: .90)

**Approach A — Add 7 new tests to existing test classes.** Purely additive. Each AC gap gets dedicated test(s). No modification to existing tests, no risk to the passing 31. Total: 38 tests after implementation.

This is high-confidence because: (a) all assertion targets exist in the codebase and are stable, (b) the approach is additive-only so AC 4 (no weakening) is trivially satisfied, (c) exact needle strings are verified against live files.

Challenge: FALLBACK — T1-autonomous test-depth refinement with no architecture, capability, or security implications. Confidence .90 does not warrant challenger invocation.

## 5. Follow-up Tasks

- Task at `todo` (implementation-ready, no further research needed): add 7 tests to `tests/test_ideation_overhaul_static.py` per the exact assertion map above.
