# Context — Memory Voting

## Problem

The memory system's recall ordering relies on a single static field (confidence) that is set at creation, manually adjusted during curation, and then frozen as the permanent sort key. This creates two failure modes:

1. **Stale-high:** Entries with high confidence remain at the top of recall indefinitely, even when they are no longer relevant or were never practically useful — just confidently authored.
2. **Buried-good:** Genuinely valuable entries with lower initial confidence never surface because they cannot compete on confidence alone.

The only corrective mechanism is human curation, which doesn't scale. There is no feedback loop from the agents that consume memories back to the memory store.

## Proposed Direction

Introduce a voting signal that allows agents to express whether a recalled memory was useful. The voting score is global (pooled across all voting agents), separate from confidence. Once enough votes accumulate (cold-start threshold), the voting score replaces confidence as the recall sort key. New entries without sufficient votes are surfaced to scoped agents so they can accumulate signal.

This creates a self-correcting system: useful memories persist and rise; unhelpful or aged-out memories naturally drop below the recall cap without requiring active deletion.

## Project Type

Existing feature / refactor — extends the memory engine, model, and MCP tools.

## Expectation Signal

**What are we actually trying to give the user?**
A self-improving memory system where recall ordering reflects practical agent experience over time. Agents vote on memories they encounter; the accumulated signal becomes the primary recall sort key, replacing the static confidence guess.

**What would make it feel worth using?**
- The system self-improves: useful memories rise, unhelpful ones sink — without human intervention
- New memories get a fair trial period (cold start) before being subject to vote-based ordering
- The voting signal gives humans clarity: the cockpit/curation workflow shows what's thriving and what should be deleted
- The vote tool is lightweight enough that agents use it without extra prompting

**First Useful Step:**
MCP vote tool + vote field on model + recall ordering changes immediately based on votes. Even a few votes must shift the recall sequence. The ordering formula (exponential decay or similar) is part of V1, not deferred. Cold-start fairness is load-bearing — new entries must get fair exposure.

**What remains after First Useful Step:**
- Cockpit UI surfacing the voting signal to humans (what's thriving, what should be deleted)
- Half-life / vote-boost tuning based on real data
- Potential formal deprecation of confidence as a sort key (confidence may become initial temperature only)
- Long-term observation of context-dependent voting patterns (design mitigations only if bias is real)

**What would be technically done but still wrong?**
- One type of entries (old or new) pushes out the other without votes being the reason — cold-start placement too high or too low
- Signal difference too low to make a real difference between entries
- Few votes lead to entries being pushed out too quickly due to context mismatch (e.g., Python test memories voted bad because the current task is TypeScript testing)
- Voting data is collected but recall ordering never actually changes

**What did the user knowingly give up?**
- Per-agent scoring (global score only, scope handles targeting)
- Automatic deletion/promotion without human confirmation (hybrid: system marks, human confirms)
- Dual-signal voting (early relevance + late value) — simplified to one end-of-task vote

## Active Tensions (post-challenge)

1. **Positive-only vs. positive+negative:** Negative votes risk domain-mismatch bias (voting down valid entries because current task is in a different domain). Positive-only avoids this but creates "rich get richer" — old entries with many votes permanently outrank new unvoted ones.
2. **Replace confidence vs. layer on top:** Replacing confidence loses the truth/quality signal. Layering adds math complexity the user isn't confident is worth it. Need a simple formula.
3. **Vote quality:** Agents may not accurately attribute outcomes to specific memories. The system must be robust to noisy/low-quality votes.
4. **Cold start:** New entries need exposure to accumulate votes. Pure vote-count ordering creates a chicken-and-egg problem. Need a mechanism that doesn't require complex math.
