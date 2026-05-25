# First-Principles Stance — Knowledge Module Modularization

## Irreducible Claims Being Made

1. The knowledge system's interfaces are unstable because they were grown bottom-up
2. A top-down spec will stabilize them
3. Once stable, implementation/audit of submodules becomes independent
4. The domain is well-enough understood to write stable interfaces now

## Challenged Assumptions

### A. Interface instability vs. domain-model immaturity

If the domain model (which entities exist, what relationships are meaningful, what queries agents actually ask) isn't settled through real usage, a spec just codifies guesses. Guesses change. The question is: **has this system ever been used end-to-end by real consumer agents for real tasks?** If not, the interfaces SHOULD be changing — that's learning, not a bug.

A stable interface spec assumes you already know what the interfaces should be. But the 5+ audit cycles may indicate that this knowledge is still being discovered, not that it's known and just poorly documented.

### B. Spec-as-solution vs. spec-as-additional-stale-artifact

The kanban module works without a written interface spec because:
- Its domain is simple and stable (tasks move between columns)
- It was validated by real usage early

The knowledge system's domain is intrinsically more uncertain (what does "enrichment" even mean for each source type? what graph traversal patterns matter?). A spec adds maintenance load. When the spec needs changing, you now have TWO things to update instead of one.

**Question:** What would prevent the spec from becoming another thing that audits find wrong?

### C. Surface area vs. maturity

32 modules / 7700 LOC = ~240 LOC per module. That's extremely fine-grained. Each module boundary is a potential cascade point. The system may have **more internal boundaries than its domain understanding can support**.

Compare: If this were 4 modules at ~2000 LOC each with fat interfaces, changes would cascade less because there are fewer seams.

### D. Speculative features creating instability

Features like cross-source consolidation, graph-augmented retrieval, and the enrichment state machine — are these validated against real agent usage, or were they built speculatively from research? If the latter, their interfaces change because the requirements were never real.

## Diagnostic Test

Categorize the last 10 audit findings as:
- **(a) Shape mismatch** — caller expected X, callee provides Y (genuine interface problem)
- **(b) Speculative interface** — the feature was never validated by real load and its contract was a guess

If mostly (b), the fix is **"delete or shelve unvalidated features and build only what real usage demands"** — not "write better specs for speculative features."

## What the Real Problem Might Be

The stated problem is "interfaces shift causing cascading rework." But the root cause may be:

1. **No real consumer exists yet.** Without an agent actually querying this KB during real tasks, there's no demand signal to stabilize interfaces against.
2. **Premature decomposition.** 32 modules is too many boundaries for the current maturity. Coarser modules would cascade less.
3. **Building features before validating them.** Enrichment, consolidation, graph augmentation are intellectually appealing but may not have proven value yet.

If the real problem is #1, the fix is: get ONE consumer agent using ONE query interface for real work. That's the forcing function that stabilizes the interface.
