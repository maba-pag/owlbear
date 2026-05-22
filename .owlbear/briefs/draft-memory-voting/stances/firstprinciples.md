# First-Principles Stance — Memory Voting

## Irreducible Core

The actual problem reduces to one claim: **recall ordering should reflect post-hoc utility, not pre-hoc confidence.** Everything else in the framing is implementation structure, not necessity.

## Assumptions Challenged

### 1. "Voting" is the right feedback shape

The framing assumes a discrete vote event. But the irreducible need is a *usage signal* — evidence that a memory contributed to a successful outcome. A vote is one encoding of that signal, but it conflates two things:

- **Was this memory recalled?** (observable without any agent action)
- **Did it help?** (requires judgment)

The first is free. The second requires the agent to introspect accurately mid-task. The proposal bundles both into one explicit action and discards the free signal entirely. Challenge: **recall frequency alone** (memories that keep getting pulled but never voted on are already telling you something) may carry most of the ordering information without requiring any new tool.

### 2. Agents can meaningfully evaluate usefulness

This is the load-bearing assumption and the weakest one. An agent at end-of-task is evaluating whether a memory was helpful *to the task it just completed*. But:

- The agent may have used the memory without realizing it (absorbed framing)
- The agent may blame the memory for a failure caused by something else
- The agent cannot distinguish "this memory was irrelevant to me" from "this memory is bad"

The framing treats agent judgment as ground truth. It's actually a noisy proxy. The design needs to be robust to **vote quality being low**, not just vote quantity being low.

### 3. A single global score is sufficient

D2 chose global over per-agent scoring. The reasoning ("scope handles targeting") only works if scope assignment is correct. But scope assignment is also a human-curated static field. You're replacing one static proxy (confidence) with another (scope) as the guard against domain-mismatch voting. The framing assumes scope is solved; it isn't.

The deeper question: if a memory is scoped to `[builder, reviewer]` and the builder votes it down because it was irrelevant to a TypeScript task (but it's a Python convention memory), is that a legitimate signal or noise? Global pooling cannot distinguish these cases. The framing acknowledges this risk but proposes no mechanism to handle it.

### 4. Replacing confidence with votes as sort key

The framing proposes a *replacement* — once threshold is met, votes become the sort key. But confidence and votes measure different things:

- Confidence = "how sure are we this is true"
- Votes = "how often was this useful in practice"

A memory can be high-confidence and low-utility (true but irrelevant) or low-confidence and high-utility (uncertain but practically valuable). These are orthogonal axes. Replacing one with the other loses information. The framing conflates **truth** with **utility** by treating them as competing sort keys rather than independent dimensions.

### 5. End-of-task is the right moment

End-of-task voting assumes the agent remembers which memories it consumed and can attribute outcome to specific memories. In practice:

- Recall happens at task start
- Multiple memories are consumed
- The task may run for many tool calls
- Attribution is retrospective guesswork

The framing chose end-of-task over dual-signal (early relevance + late value) for simplicity. But it may have cut the *more informative* signal (early relevance — "did I actually use this?") and kept the *less informative* one (late value — "was my task successful?").

### 6. Cold-start threshold solves fairness

The cold-start design assumes the problem is "not enough votes yet." But the real fairness problem is **exposure**: new entries need to be recalled to be voted on, but recall ordering determines exposure. This is a classic explore-exploit problem. A threshold doesn't solve it — it only delays the problem. After threshold is reached, a new entry with 3 lukewarm votes competes against an old entry with 50 strong votes. The framing doesn't address the decay/recency dimension at all.

## What Might Be Simpler

1. **Recall-count decay**: Order by `recall_count * decay(age_since_last_recall)`. No new tool, no agent judgment, no vote quality problem. Memories that stop being recalled naturally sink.

2. **Negative-only signal**: Instead of voting on everything, let agents flag memories that were *actively harmful* (caused confusion or wrong action). Much easier to evaluate than "was this helpful?" — and the human curation workflow only needs to act on the flagged entries.

3. **Confidence decay with refresh**: Confidence decays over time unless a human or curation pass refreshes it. Achieves the "stale-high" fix without any new agent behavior.

## What Is Being Conflated

- **Ordering** and **filtering** — the framing treats them as one problem. But "stop showing me irrelevant memories" (scope/filter) is different from "show me the best ones first" (order).
- **Truth** and **utility** — confidence measures one, votes measure the other. The proposal replaces one with the other rather than composing them.
- **Agent feedback** and **system telemetry** — explicit votes vs. implicit usage signals. The proposal chose the expensive, noisy option and ignored the free, clean one.

## Hidden Risks

- **Herding**: Early votes create ordering that determines future exposure, which determines future votes. Positive feedback loop amplifies initial signal quality problems.
- **Domain contamination**: Cross-domain agents voting on scope-targeted memories creates systematic bias that global pooling cannot self-correct.
- **Cargo-cult voting**: If agents are instructed to vote, they will. The question is whether those votes carry real information or are compliance theater.

## Confidence

0.82 — The framing has real problems: it chose an expensive mechanism (explicit votes) over cheaper alternatives (implicit signals), conflates truth with utility, and underestimates the explore-exploit dynamics. The irreducible need (post-hoc utility ordering) is legitimate, but the proposed structure is significantly more complex than the minimum viable solution.
