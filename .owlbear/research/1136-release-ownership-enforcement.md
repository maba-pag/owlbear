# Release Route Ownership Enforcement — Design Conflict Analysis

> **Owning task:** #1136 — Add ownership check to cockpit release route
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

Task #1136 (from #1131 research §G3) proposes adding ownership verification to the cockpit release route — the route currently clears any agent's claim without checking identity. **Question:** What enforcement model should be used, and does this conflict with existing design contracts?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` L212–229 | 1.0 | Release route: checks `claimed_by` presence, not identity |
| S2 | `.owlbear/briefs/draft-cockpit/decisions.md` D12 | 1.0 | "release_task allows release unconditionally… backend trusts the request because it cannot meaningfully second-guess from data alone" |
| S3 | `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md` §3.6 | 1.0 | "release_task (Cockpit-only) — admin force-release" |
| S4 | `serve/kanban/src/owlbear_kanban/models.py` L262–263 | 0.9 | `claimed_by` is `Field(exclude=True)` — in-memory projection alias, never persisted |
| S5 | Task #1133 — Add `expected_updated` CAS to `engine.release_task` | 0.9 | Already covers stale-snapshot protection via OCC |
| S6 | `.owlbear/research/cockpit-mutation-occ-parity.md` | 0.8 | Prior analysis: release CAS = `expected_updated`, not identity check |
| S7 | `serve/kanban/src/owlbear_kanban/engine.py` L1266–1319 | 0.8 | Core `release_task`: no ownership check, no OCC param |
| S8 | Brief B §3.6 D11 reference | 0.7 | "No `claimed_by` (D11). No identity check." |

## 3. Analysis

### 3.1 Design Contract Conflict

The core AC ("Release route rejects attempts to clear a claim owned by a different actor") **directly contradicts** two authoritative design decisions:

| Decision | Source | Statement |
|----------|--------|-----------|
| D12 | `draft-cockpit/decisions.md` | "release_task allows release unconditionally… backend trusts the request because it cannot meaningfully second-guess from data alone" |
| Brief B §3.6 | `draft-kanban-engine-b/brief.md` | "release_task (Cockpit-only) — admin force-release" |

The cockpit is an admin management tool. Releasing stuck agent claims is a primary use case. Restricting release to "own claims" defeats the admin purpose since the cockpit engine runs with `agent_name="cockpit"` — it never owns agent claims.

### 3.2 Two Concerns Conflated

The #1131 research (§G3) identified "actor-agnostic release" as a gap. But there are two distinct concerns:

| Concern | Problem | Correct fix |
|---------|---------|-------------|
| **Stale-snapshot release** | UI loads task (claimed by A, updated=T1). A releases, B claims (updated=T2). User clicks Unclaim → releases B's claim, not A's. | OCC via `expected_updated` token — **already covered by #1133** |
| **Ownership enforcement** | Route doesn't verify caller identity matches claim owner | Conflicts with D12 admin-release contract; `claimed_by` is a projection alias, not identity proof |

OCC fully addresses the real safety scenario: if the claim changed between load and release, the `updated` timestamp changes → stale token → 409. The user reloads, sees the new claimant, and makes an informed decision.

### 3.3 Enforcement Model Evaluation

| Option | Description | Solves stale? | Solves ownership? | D12 compatible? | Complexity |
|--------|-------------|---------------|-------------------|-----------------|------------|
| A: Client `claimed_by` token | ReleaseRequest body with `claimed_by`; reject on mismatch | No | Weak — `claimed_by` is projection-only, unspoofable only by absence of auth (which is the norm) | **No** — overturns D12 | Low |
| B: Engine `agent_name` check | `release_task` verifies `claimed_by == self._agent_name` | No | Yes, server-side | **No** — cockpit engine is always `agent_name="cockpit"`, never the claim owner | Medium |
| C: OCC `updated` token | ReleaseRequest with `updated`; precheck or engine CAS | **Yes** | No (and shouldn't per D12) | **Yes** | Low |
| D: A + C combined | Both tokens | Yes | Weak (same A caveats) | **No** | Medium |

### 3.4 Why `claimed_by` Is Not an Ownership Token

- `claimed_by` is `Field(default=None, exclude=True)` in the Task model (S4) — it's an in-memory projection alias, never persisted to disk.
- The engine computes it from `claimed_at` + agent_name at runtime.
- Using a non-persisted projection field as a client-side ownership proof is semantically incorrect.

## 4. Recommendation (confidence: 0.88)

**Close #1136 as superseded by #1133.** The AC conflicts with D12 (admin force-release). The real safety concern (stale-snapshot release) is fully addressed by #1133's OCC approach. No ownership enforcement is needed or desirable for the admin cockpit.

If the user wants to override D12 and add ownership enforcement, that is a T3 design decision (changes user-facing behavior of an existing contract).

Challenge: `reconsider` → `block on D12 conflict` — confidence in original Option A: 0.34. Challenger correctly identified that the task's AC overturns an existing design contract. Revised to closure recommendation.

## 5. Follow-up Tasks

- No new implementation tasks needed — #1133 covers the real concern.
- Advisory T2 DR created via scribe to document the D12 conflict for user awareness.
