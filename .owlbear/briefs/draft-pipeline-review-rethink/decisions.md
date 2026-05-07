# Decisions — Pipeline Review Rethink

## Project Type

- **Chosen:** existing-feature/refactor
- **Rationale:** The pipeline exists and functions. The work is simplifying/refocusing the checking steps, not building new ones from scratch.

## Investment Tier

- **Chosen:** Shared
- **Rationale:** Multi-consumer artifact — changes propagate across most agents and skills. Needs full panel and research bridge, but not Critic-at-every-boundary Production weight.

## Architect Skip Path

- **Chosen:** Force all tasks through architect
- **Rejected:** Planner validates intent itself (keeps quality gate informal and inconsistent)
- **Rejected:** Defer to mediation (user has clear preference)
- **Rationale:** User's instinct: planner writes intent + best-effort AC, architect always reviews and refines. The current skip path means intent-vs-AC alignment goes unchecked until auditor — after all expensive work is done.

## Locked Outcomes (post early-challenge, M2 complete)

1. **Planner cannot create unchecked AC** — all tasks must route through architect
2. **Architect produces explicit, enumerated, observable AC** — named functions not concepts
3. **Reviewer batches all findings** — returns complete fix list, no gate-on-first-failure
4. **Reviewer stops re-running tests** — reads builder's quality-runner results
5. **Test lifecycle: structural separation** — task tests in `tests/` (deleted at archival), durable tests in `serve/*/tests/`, planner creates consolidation-test task per feature chain
6. **Test-writer defaults to exact-value assertions** — no substring/presence-only
7. **Auditor focuses on regression + intent** — full suite run, intent-vs-AC alignment, logic flaws
8. **Every agent gets role sharpening** — purer mandates, clear handoff contracts

## Reviewer Strategy

- **Chosen:** Batch all findings in one pass, return complete fix list
- **Rejected:** Gate on first critical finding (saves time per run but causes 5x partial runs vs 2x full — net 2.5x MORE expensive)
- **Rationale:** Archive analysis shows #1061 (10+ rounds), #1050 (8 rounds), #1053 (6+ rounds). Root cause: reviewer finds one issue, gates, task goes through full pipeline cycle, reviewer finds next issue. Batching ALL findings in one pass would cut most spirals to 1-2 rounds.

## Test Lifecycle Mechanism

- **Chosen:** Structural separation — task tests in `tests/` with `_{task_id}` naming (auto-deleted at archival), durable tests in `serve/*/tests/` (package-local, survive). Planner creates a "consolidation test" task at end of each feature chain.
- **Rejected:** Tagging (metadata requires discipline, drifts over time, adds infrastructure)
- **Rejected:** Builder tags temporary code (builder has no lifecycle visibility — that's a planner/architect judgment)
- **Rationale:** First-principles challenger argued structural separation has zero maintenance burden vs. tagging. Test files already carry `_{task_id}` naming — cleanup is `rm tests/test_*_{task_id}.py`. No metadata infrastructure needed.

## Test-Writer Independence

- **Chosen:** Keep test-writer as separate agent
- **Rejected:** Merge into builder (both already miss AC individually — merging worsens quality)
- **Rejected:** Merge into architect (conceptually sound — full AC context — but architect uses most expensive model; cost-prohibitive with per-usage pricing)
- **Rationale:** Empirical validation from user's experience.

## Reviewer + Auditor Separation

- **Chosen:** Keep as separate agents with purer mandates
- **Rejected:** Merge into one agent with two attention phases (attention contamination risk: seeing AC gaps in phase 1 biases correctness judgment in phase 2)
- **Rationale:** User decision + first-principles analysis of forced attention scoping as the value model. Reviewer = completeness (are all AC implemented?), Auditor = correctness + integration (do they work right? do they break anything?)

## Agent Scope

- **Chosen:** All agents in scope for role redefinition (planner, architect, test-writer, builder, reviewer, auditor)
- **Rejected:** Fix reviewer only (simplifier Pass 1 recommendation — user explicitly rejected)
- **Out of scope:** Doc-writer (needs separate rebuild)
- **Rationale:** User: "that these agents are in scope is non-negotiable. we need to enable the architect to write better AC, we need the planner to write better intent"
