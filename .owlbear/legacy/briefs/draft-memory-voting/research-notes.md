# Research Notes — Memory Voting

## Verified Findings

### Current recall ordering
```python
sort_key = (state_rank[entry.state], -entry.confidence, entry.id)
# approved > curated; higher confidence first; id tiebreaker
```
- Confidence range: 0.7–1.0 (Pydantic-enforced)
- Recall cap: 20 entries per request (hardcoded in `recall_memory`)
- No vote fields, no decay, no implicit signal tracking

### Proven scoring approaches (cold-start + positive-only + simple)

**1. Exponential Decay + Positive-Only Votes** (recommended)
- Formula: `score = e^(-λ * age_hours) + votes * boost`
- λ = ln(2) / half_life_hours
- Proven: Hacker News (story ranking)
- Solves: cold-start (freshness window), self-correcting (unused entries fade), positive-only (no downvotes needed)
- Tuning: half_life_hours + vote_boost magnitude
- Risk: one tunable parameter (half_life) determines behaviour heavily; requires empirical tuning

**2. Threshold-Based Hybrid (Confidence → Wilson Score)**
- Logic: sort by confidence until vote_threshold reached, then switch to Wilson lower bound
- Wilson formula: statistically sound, handles small samples, no rounding errors
- Proven: Stack Overflow, Yelp
- Solves: cold-start (confidence-driven until matured), positive-only compatible
- Risk: artificial cliff at threshold boundary; no decay (old entries never fade)

**3. Reddit Formula (Positive-Only Variant)**
- Formula: `score = log10(upvotes + 1) - age_seconds / decay_tuning`
- Proven: Reddit at scale
- Solves: quality + freshness in one formula, no threshold cliff
- Risk: more tuning, harder to explain, log(0) edge case

### Implicit signals (alternative to explicit voting)
- Recall frequency: how often an entry is returned — free telemetry, no new tool needed
- Reference rate: did the agent use concepts from the entry? — requires instrumentation
- Content reflection: cosine similarity between entry and agent output — expensive
- Trade-off: no new tool, no agent behavior change, but delayed and hard to diagnose

### Key math properties
- Wilson score with 0 votes → score ≈ 0; 1 vote → ≈ 0.21; 10 votes → ≈ 0.72 (no rounding issues)
- Exponential decay: base Python math.exp/math.log, no external deps
- Bayesian approach: requires scipy (betaincinv) — too heavy

## Candidate Implications

1. **Exponential decay is the simplest formula that solves all four constraints** (cold-start, positive-only, simple, self-correcting). It avoids the threshold cliff and doesn't need the confidence→votes handoff.

2. **Confidence could become the initial "temperature"** — a high-confidence new entry starts slightly warmer than a low-confidence one, then votes and decay take over. This preserves confidence's information without it being the permanent sort key.

3. **The vote tool can be extremely simple**: one MCP tool, one argument (list of entry IDs the agent found useful). No negative votes, no rating scale. Just "these helped me."

4. **Vote storage is cheap**: a single integer field (`vote_count`) on the memory entry, incremented by the vote tool. No separate vote log needed for V1.

5. **Decay eliminates the "rich get richer" problem** — old entries with many votes still fade if they stop receiving new votes. New entries compete on freshness + any votes they receive.

## Open Research Questions

1. **What half-life is appropriate for memory entries?** Unlike HN stories (hours), memories may be useful for weeks or months. Half-life of 7-14 days? Needs empirical tuning.
2. **What is the right vote_boost magnitude relative to decay?** If boost is too small, votes don't matter. Too large, one vote immediately dominates freshness.
3. **Should there be a "last voted at" timestamp** that resets the decay clock? (i.e., an entry that keeps getting voted on never fully decays.) This would make votes act as a freshness signal too.
4. **How does this interact with the state machine?** Should only approved/curated entries be voteable? Should votes affect state transitions?
5. **MCP tool ergonomics:** Do agents vote on individual entries or batch-vote at end of task? Batch is simpler for the agent but the attribution question (which entries actually helped?) remains.
