# Conditional Design-Diverge for Architecture Review

> **Owning task:** #1149 — Add conditional design-diverge to architecture review
> **Date:** 2026-04-27 **Status:** Complete

## 1. Context and Question

When the architect evaluates a task and detects multiple valid approaches (none
clearly dominant), the current flow offers no structured way to explore alternatives
before the challenger runs. The architect must pick one approach using intuition
alone. The question: can we add a conditional parallel-exploration step that
produces structured design analyses for comparison before selection?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Ousterhout — "A Philosophy of Software Design" | pragmaticengineer.com/p/the-philosophy-of-software-design | 0.95 — foundational "Design It Twice" concept |
| 2 | mattpocock/design-an-interface (17.6K stars) | github.com/mattpocock/skills | 0.90 — VS Code skill implementing parallel divergent design with 3+ sub-agents |
| 3 | w-code-review Step 2.5 (in-repo) | share/skills/w-code-review/SKILL.md | 0.85 — parallel fan-out precedent with explicit contract + fallback |
| 4 | h-ideation-panel parallel batch (in-repo) | share/skills/h-ideation-panel/SKILL.md | 0.70 — multi-agent parallel dispatch with convergence step |
| 5 | Architect review of parent #1147 (in-repo) | task body #1147 | 0.80 — prior objections: KISS/YAGNI mixed, pattern consistency mixed |

## 3. Analysis

### 3.1 Concept Validity

Ousterhout's "Design It Twice" (source 1): generate radically different designs,
compare on explicit criteria, then select or hybridize. mattpocock (source 2)
operationalizes this in VS Code: 3+ sub-agents each constrained to optimize a
different axis, structured output, comparison on interface simplicity / flexibility /
implementation efficiency / depth.

Both sources confirm the core premise: first designs are rarely optimal, and
structured comparison produces better outcomes than single-pass intuition.

### 3.2 Trade-Off Matrix

| Criterion | In favor | Against | Weight |
|-----------|----------|---------|--------|
| Design quality | Structured comparison avoids premature convergence | Adds complexity to a skill file that is already ~200 lines | High |
| Token cost | Conditional — zero overhead on clear-cut reviews | 2-3 parallel subagents when triggered = significant token spend | Medium |
| Pattern precedent | w-code-review fan-out exists in-repo | Fan-out precedent has tighter contracts (see §3.3) | Medium |
| KISS/YAGNI | Step is fully optional, no new agent files | Introduces generative-design pattern not yet in arch-review | Medium |
| Reliability | General Purpose resolves at any depth | No failure path defined yet (challenger concern) | High |
| Downstream clarity | Structured output aids reviewer reading | Output format unspecified (challenger concern) | High |

### 3.3 Challenger Findings (Addressed)

| Challenge | Severity | Response |
|-----------|----------|----------|
| Trigger not operationally defined | Critical | **Accepted.** AC must include operational trigger: e.g., Step 2 criteria split across approaches (some PASS on approach A, different ones PASS on B), and architect cannot resolve without deeper analysis. |
| Precedent mismatch — fan-out has explicit contracts | Moderate | **Partially accepted.** Structural parallel dispatch is the relevant precedent, but output contract must be explicit (like code-reader's 8-section format). Recommend a 5-field output contract per subagent. |
| Missing failure path | Moderate | **Accepted.** Must define fallback: if any subagent errors, architect proceeds with single-design evaluation (skip design-diverge). Matches existing challenger fallback pattern. |
| Pattern not yet settled (parent #1147 objections) | Moderate | **Partially accepted.** Parent's objections were about unspecified output + Step 2.5 interaction. This research resolves both: output contract defined, Step 2.5 runs on selected/hybrid design only. |
| Ideation analogy overstated | Minor | **Accepted.** Ideation uses named panelists + pragmatist convergence. The closer precedent is w-code-review fan-out + mattpocock's constraint-driven prompts. |

## 4. Recommendation

**Proceed with AC refinements** (confidence: 0.78).

The concept is well-grounded in both software design literature and agent-ecosystem
practice. The existing codebase supports parallel subagent dispatch. Key refinements
needed before implementation:

1. **Operational trigger definition** — Replace "no single approach dominates" with
   measurable guidance tied to the 13-criteria evaluation.
2. **Explicit output contract** — Each subagent returns 5 structured fields:
   approach summary, structural choices, trade-offs, failure modes, codebase fit.
3. **Fallback behavior** — If any subagent errors/times out, skip design-diverge
   and proceed with single-pass evaluation. Note in Channel B.
4. **Selection procedure** — Architect builds a comparison matrix from subagent
   outputs, selects or hybridizes, documents rationale.

These are AC tightening issues for the architect phase, not concept blockers.

Challenge: reconsider — confidence in original: 0.68. Revised to 0.78 after
addressing challenger's valid structural concerns in the AC refinements above.

## 5. Follow-up Tasks

No additional tasks needed. Task #1149 is self-contained (all changes are to
`w-arch-review/SKILL.md`). The AC refinements above should be incorporated during
the architect's REFINE verdict when #1149 reaches backlog.
