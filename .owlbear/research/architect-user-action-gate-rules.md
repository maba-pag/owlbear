# Architect User-Action Gate Rule and Post-AR Fast-Path

> **Owning task:** #664 — Add architect user-action gate rule and post-AR fast-path to w-arch-review
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

The `type:user-action` convention is fully designed (#661 research) and documented (#663: r-pipeline-protocol §5, agent-common detection table, r-project-standards tag). The w-arch-review skill is the architect's procedural guide but contains no user-action handling. Without explicit rules, the architect may approve user-action tasks into the pipeline — recreating the #597 loop.

**Question:** What specific additions to w-arch-review/SKILL.md implement the architect's mandatory gate, deterministic detection heuristics, and post-completion fast-path?

## 2. Sources Studied

| Source | Path/URL | Relevance |
|--------|----------|-----------|
| #661 research doc | .owlbear/research/user-action-required-pipeline-handling.md | 1.0 |
| r-pipeline-protocol §5 User-Action Tasks | share/skills/r-pipeline-protocol/SKILL.md L203-243 | 1.0 |
| agent-common detection table | share/instructions/agent-common.instructions.md L24-36 | 1.0 |
| w-arch-review SKILL.md (current) | share/skills/w-arch-review/SKILL.md (250 lines) | 1.0 |
| #663 task body | kanban (done) — convention docs completed | 1.0 |
| #597 task body | empirical evidence of the gap | .90 |

## 3. Analysis

### Current w-arch-review structure

| Step | Content | User-action gap |
|------|---------|----------------|
| Step 0 — Setup | Claim, pre-flight, decomposition detection | No user-action fast-path |
| Step 1 — Codebase context | Search, read code, check deps | N/A |
| Step 2 — Evaluate (12 criteria) | SR, interface, deps, layering, TDD, KISS, premise, pattern, security, domain, failure-map, DR-verify | No detection criterion |
| Step 2.5 — Challenge | Challenger for APPROVE | N/A (BLOCK skips challenge) |
| Step 3 — Decide | 5 verdicts: APPROVE/REFINE/SPLIT/MERGE/REJECT | No BLOCK verdict |
| Verification checklist | 8 items | No user-action item |

### Proposed insertions (4 locations)

| # | Location | Content | AC |
|---|----------|---------|-----|
| 1 | Step 0, after "Decomposition detection" | User-action fast-path paragraph | AC3 |
| 2 | Step 2, new criterion 13 | Deterministic detection heuristics | AC2, AC4 |
| 3 | Step 3, new BLOCK row in verdict table | BLOCK verdict + action | AC1 |
| 4 | Verification checklist | New checkbox item | Quality |

### Deterministic detection heuristics (AC4)

The r-pipeline-protocol §5 heuristics are signal-based ("Physical-action verbs in AC"). For deterministic application, the architect needs a formal rule:

**Rule: A task is `type:user-action` if BOTH mandatory criteria AND ≥1 signal are met, AND no counter-signal is present.**

| Category | ID | Criterion | Test |
|----------|----|-----------|------|
| Mandatory | M1 | No testable Python interface | AC defines no function signatures, importable modules, or assertion targets |
| Mandatory | M2 | Human observation required | Completion can only be verified by a person (not by running code) |
| Signal | S1 | Physical-action verbs | AC uses: Open, Click, Navigate, Verify (visual), Configure (GUI), Deploy (manual) |
| Signal | S2 | External-system reference | AC names: Teams, Azure portal, GitHub UI, browser, external URLs, dashboards |
| Signal | S3 | Manual checkbox steps | AC lists steps the user must physically perform |
| Counter | C1 | Python interface present | AC includes a function/class to implement → NOT user-action |
| Counter | C2 | Test assertions present | AC includes expected test outcomes → NOT user-action |
| Counter | C3 | Conflicting type tag | Task already tagged `type:test` or `type:config` → NOT user-action |

**Application order:** Check C1-C3 first (fast exit). Then check M1+M2 (both required). Then check S1-S3 (≥1 required). Binary outcome.

### Post-AR fast-path placement

Two candidate locations: Step 0 (before any evaluation) or a new Step 0.5. Step 0 is better — it's the pre-flight check, and the fast-path is conceptually a "this task is already resolved" check, similar to the decomposition detection already in Step 0.

## 4. Recommendation (confidence: .90)

Add 4 content blocks to w-arch-review/SKILL.md at the identified insertion points. The deterministic heuristic rule (M1+M2+S+C) ensures AC4 compliance — counter-signals prevent false positives, mandatory criteria prevent false negatives, and the application order is mechanical.

Challenge: SKIPPED — trivial documentation task completing a fully-designed convention (#661 research, .78 confidence, challenger-revised). No novel architectural decisions.

## 5. Follow-up Tasks

None — this task IS the final implementation piece. After #664 is built, the full #661 feature is complete (all 5 decomposed tasks resolved: #665 test, #662 code, #666 skill docs, #663 convention docs, #664 architect rules).
