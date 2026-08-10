# Decisions — Memory Voting

*Append-only log of chosen and rejected options with rationale.*

## D1 — 2026-05-22 — Project Type

**Chosen:** Existing feature / refactor
**Rationale:** This extends the memory engine, model, MCP tools, and recall ordering. No new subsystem needed.

## D2 — 2026-05-22 — Vote Score Scope

**Chosen:** Global score (pooled across all voting agents)
**Rejected:** Per-agent score (track votes per agent×entry pair)
**Rationale:** Global is significantly simpler (one field vs. a matrix). Scope_agents already handles targeting — if an entry is irrelevant to a specific agent, scope correction is the right fix, not a per-agent score. Global score reflects "is this useful to the agents who are supposed to see it?"

## D3 — 2026-05-22 — Investment Tier

**Chosen:** Shared
**Rationale:** Multi-consumer artifact. Every pipeline agent is a voter. Changes touch memory model, MCP tools, recall logic, and cockpit UI. Requires full panel and research bridge.

## D4 — 2026-05-22 — Ordering Change in V1

**Chosen:** First Useful Step must include recall ordering change (not just data collection)
**Rejected:** Simplifier's "collect votes first, decide ordering later" — user explicitly identified "voting data collected but ordering never changes" as technically-done-but-still-wrong
**Rationale:** Self-improving means ordering actually changes. Even a few votes must shift recall sequence. Data collection without ordering effect is instrumentation, not a feature.
