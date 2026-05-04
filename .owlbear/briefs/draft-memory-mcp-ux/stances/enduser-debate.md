# End-User Debate Log — Memory MCP Tool UX (Full Design)

## Cycle 1

### Draft Position Summary

1. Tool naming: Strong Approve — save_memory/recall_memory are discoverable, consistent verb_noun pattern.
2. Hidden 1KB limit: Strong Oppose — recreates the exact UX defect the brief set out to fix.
3. recall_memory body-only return: Accept With Warning — design intent is sound but creates stale-knowledge debt.
4. Undocumented "*" wildcard: Oppose — hidden-but-functional is worst UX state.
5. Auto-downgrade on any edit: Accept for v1 — simplicity worth occasional re-approval friction.
6. Parameter discoverability: Strong Approve (conditional on schema inclusion of enums/ranges).
7. Guidance hints: Strong Approve — expand beyond D20's single case.

Overall confidence: 0.79

### Critic Challenges

**Challenge 1 — recall_memory discoverability overstated (severity: moderate):**
Evidence for "recall" as a high-probability search term is weaker than for "save." Current pipeline still teaches `query_memory`. The "Strong Approve" doesn't account for rename/docs debt. Agents searching "query", "get", "fetch" would not find "recall" via keyword matching.

**Challenge 2 — Body-only recall discards critical interpretability signal (severity: critical):**
D27 removes confidence, categories, state, and timestamps — not just IDs. An agent receiving contradicting recalled entries has zero signal about which is more reliable. The synthesis records the earlier enduser expectation as a structured payload. Current shipped code returns full entry objects. "Accept with Warning" understates a major UX regression in interpretability.

**Challenge 3 — Tool registration scope is the primary isolation failure (severity: critical):**
If rollout uses `ob-memory/*` in agent tools: arrays, the tool-level `agent` parameter is secondary — all 7 tools would be visible to all agents regardless. The security stance explicitly warned about this. Focus on the `"*"` parameter missed the structural exposure vector. The agent validator treats `/*` as a whole-server wildcard.

**Challenge 4 — Auto-downgrade is a full contract inversion (severity: moderate):**
Current shipped behavior rejects ALL mutations on approved entries (tests enforce this). D20/D29 reverses this entirely. The size of semantic change is larger than "acceptable friction." D21 clears `approved_at` on downgrade — intentionally erases approval timing history.

**Challenge 5 — First-call failure surface broader than schema (severity: moderate):**
Seven affected consumers still describe the old 5-tool surface and old write signature. Even perfect JSON Schema doesn't neutralize instruction drift across pipeline skills, handbooks, and tests. D15 removes write-time `scope_agents`, D21 adds required `source_agent` — these are breaking changes for consumers.

**Blind spots identified:**
- Consumer instruction updates are part of the UX agents actually encounter (7 affected artifacts).
- Activation risk for a dormant system is unaddressed — zero production usage, only 2 agents wired.
- Curator agent currently lacks MCP tools — the design assumes a wiring that doesn't exist yet.

**Critic confidence in draft position: 0.55 | Pressure level: high**

### Refinement Decisions

**Challenge 1 — Partially accepted.**
Downgraded from "Strong Approve" to "Approve with note." "recall" depends on semantic matching (which tool_search uses), not keyword matching. Added caveat that consumer docs must update atomically.

**Challenge 2 — Fully accepted.**
Upgraded from "Accept with Warning" to "Conditional Accept." Body-only is too aggressive — agents NEED confidence to weight contradicting entries. This is interpretability signal, not management metadata. Added minimum viable format showing confidence per entry.

**Challenge 3 — Fully accepted.**
Expanded scope of position 4 to cover BOTH registration-level isolation (explicit tool names, not wildcards) AND parameter-level isolation (block or document the `"*"` wildcard). Registration is the primary control.

**Challenge 4 — Acknowledged, position maintained.**
The contract inversion IS larger than initially stated. But the new behavior is better UX than the status quo — a curator who can't fix typos without delete+recreate is worse. The semantic change is justified even if large. Maintained "Accept for v1."

**Challenge 5 — Fully accepted.**
Expanded position 6 to require atomic consumer updates as part of first-call success. JSON Schema alone is insufficient when seven artifacts teach the old interface.

**Blind spots — All incorporated:**
- Added new position 8 (activation sequencing) addressing the dormant→active transition.
- Expanded position 6 to explicitly name consumer update atomicity.
- Added warning about curator not existing in required form yet.

### Resolution

Three of five challenges resulted in position changes. Two blind spots became new stance sections. Confidence revised upward to 0.80 (incorporated gaps strengthen the position's completeness).

---

## Final Assessment

The Critic's strongest contribution was Challenge 2: revealing that body-only recall discards interpretability signal that agents need for knowledge consumption, not just management. This shifted my position from "it's fine, just note the risk" to "this needs fixing — include confidence at minimum."

The second-strongest was Challenge 3: reframing the isolation question from a parameter-level concern to a registration-level architectural dependency. This broadened my position's scope appropriately.

Challenge 4 was overstated — calling the auto-downgrade a "contract inversion" implies it's risky, but the new behavior is objectively better UX than the immutability it replaces. A contract change that improves UX is not a defect.

Exit condition: Position is solid after one cycle. The Critic's challenges were incorporated where valid and rebutted where overstated. No further cycling needed.
