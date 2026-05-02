# Simplifier Stance — Dead Code Sweep

## Key Challenges

1. **"Opportunistic cleanup" is unbounded.** The locked outcomes include "bounded list of any other dead code spotted opportunistically" — but the boundary isn't defined. This is a scope trap that turns a 30-minute mechanical deletion into an open-ended archaeology expedition.
2. **Three unrelated concerns share one brief.** Orchestrator removal is certain and mechanical. `owlbear-project.json` needs investigation. "Other dead code" is speculative. Bundling them forces all three to the same delivery cadence.
3. **Pydantic AI appears in context but not in outcomes.** The context lists it as an abandoned direction, then the outcomes explicitly exclude research docs. This creates ambiguity about whether non-research Pydantic AI references are in scope.

## Simplification Opportunities

- **Split into two tasks, not one brief.** Task 1: delete `serve/orchestrator/` + all references (mechanical, zero investigation needed — just grep and rm). Task 2: investigate and resolve `owlbear-project.json`. Drop "opportunistic cleanup" entirely — if something else surfaces during Task 1, file it as a separate task.
- **Orchestrator removal needs no brief.** It's a deletion with a grep-verify step. A single kanban task with AC "no imports, no references, tests green" is sufficient. Elevating this to Brief-level ideation is over-process.
- **Skip doc-index regeneration as a separate outcome.** It's a single command (`uv run doc-index`) run at the end. Listing it as a locked outcome inflates perceived complexity.

## Risks of Over-Scoping

- The "opportunistic" clause will expand work 2–3× if the builder starts hunting for stale patterns beyond the two named targets.
- Bundling investigation (`owlbear-project.json` consumers?) with known-dead removal (orchestrator) blocks the easy win behind the uncertain one.

## Recommendation

**Decompose, don't brief.** Create two atomic tasks directly on the board: (1) remove orchestrator + references, (2) investigate and remove `owlbear-project.json`. Kill the "opportunistic" scope entirely. Neither task needs a full Brief — both are bounded deletions with grep-verifiable completeness. Confidence: **0.85**.
