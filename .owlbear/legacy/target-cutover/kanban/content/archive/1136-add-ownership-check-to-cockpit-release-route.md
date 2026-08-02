---
id: 1136
title: Add ownership check to cockpit release route
status: archived
priority: medium
created: 2026-04-26T16:00:48.060978+00:00
updated: 2026-04-26T16:57:38.576204+00:00
tags:
- cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

Objective: Prevent the cockpit release route from clearing a claim owned by a different actor.

Context: The release route checks `task.claimed_by` presence (409 if unclaimed) but does not verify WHO owns the claim. The existing happy-path test already demonstrates this: task 2 is claimed by "seed" agent, but the cockpit route (running as "cockpit") releases it successfully. This is an actor-isolation gap, not just a timing race.

Note: This requires a design decision on the enforcement model — should the route:
  (a) Accept a `claimed_by` token and reject if it doesn't match?
  (b) Use the engine's `agent_name` to verify the caller owns the claim?
  (c) Accept an `updated` token for OCC (like edit)?
  Needs decomposition: design decision on enforcement model before implementation.

Acceptance Criteria:
- [ ] Release route rejects attempts to clear a claim owned by a different actor
- [ ] 409 response includes stable detail explaining the ownership mismatch
- [ ] Release of own claim still works (happy path preserved)
- [ ] Existing tests updated to reflect ownership enforcement
- [ ] New race test from #1131 passes with the fix

Likely files:
- serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- tests/test_cockpit_mutation_api.py

See: .owlbear/research/1131-cockpit-mutation-race-tests.md § G3

[[2026-04-26]]
## Research
- Research doc: .owlbear/research/1136-release-ownership-enforcement.md
- Sources: 8 studied (all codebase-internal), 4 high-relevance
- Recommendation: Close #1136 as superseded by #1133 — OCC covers the real safety concern; ownership enforcement contradicts D12 (confidence: 0.88)
- Follow-up tasks created: none (no new implementation needed)
- Decision requests: 1 created (T2 advisory — D12 contract conflict)

## Challenge Results
- Challenger: block (confidence in original Option A: 0.34)
- Revised analysis: Task AC overturns D12 (admin force-release) and Brief B §3.6. The stale-snapshot scenario is fully addressed by #1133 (OCC CAS on release). `claimed_by` is a projection-only alias (`exclude=True`), not an identity proof.

## Key Findings
1. D12 (draft-cockpit/decisions.md): "release_task allows release unconditionally… backend trusts the request"
2. Brief B §3.6: "release_task (Cockpit-only) — admin force-release"
3. Task #1133 already adds `expected_updated` CAS to engine.release_task — covers stale-snapshot safety
4. `claimed_by` is `Field(default=None, exclude=True)` — in-memory projection, never persisted, unsuitable as ownership token
5. Cockpit engine runs as `agent_name="cockpit"` — it can never "own" an agent's claim
[[2026-04-26]]
## Decision Resolved

**Decision:** A: Close #1136 as superseded by #1133

**User Notes:** OCC timestamp comparison (#1133) is the correct mechanism. Admin force-release stays unconditional per D12. Ownership enforcement is not wanted.
[[2026-04-26]]
## Research (validation pass)\nDecision resolved: Close #1136 as superseded by #1133.\n\nResearch doc validated — findings still hold:\n- D12 mandates unconditional admin release; ownership enforcement contradicts this\n- #1133 (OCC CAS on release_task) covers the real stale-snapshot safety concern\n- `claimed_by` is a projection alias (`exclude=True`), not an identity proof\n- No new implementation tasks needed\n\nResearch doc: .owlbear/research/1136-release-ownership-enforcement.md\nChallenger: block → revised to closure recommendation (confidence: 0.88)\nAction: Close at backlog — no further pipeline stages needed.
[[2026-04-26]]
## Decision Resolved\nOption A approved: Close #1136 as superseded by #1133. OCC timestamp comparison is the correct mechanism. Admin force-release stays unconditional per D12.