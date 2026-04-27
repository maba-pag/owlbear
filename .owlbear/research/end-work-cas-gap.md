# end_work CAS gap: facade precheck vs raw-engine write race

> **Owning task:** #1129 — Research: end_work CAS gap — facade precheck vs raw engine write race
> **Date:** 2026-04-26 **Status:** Complete

## 1. Context and Question

This review re-checks TOCTOU exposure where a facade does read-time validation and then delegates to a separate mutation call. The scope includes both writer surfaces named in AC2:

- AgentView over MCP stdio (`serve/kanban/src/owlbear_kanban/engine.py`)
- Cockpit HTTP routes over uvicorn (`serve/cockpit/src/owlbear_cockpit/routes/mutation.py`)

Key question: does prior D2 risk acceptance still hold after Cockpit introduced an additional concurrent writer surface?

## 2. Sources Studied

| ID | Source | What was taken | Relevance |
|---|---|---|---|
| S1 | `serve/kanban/src/owlbear_kanban/engine.py` | AgentView precheck/delegate flows; raw engine OCC on `end_work` with `expected_updated`; `release_task` behavior. | 0.98 |
| S2 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Cockpit route precheck/delegate flow for move/edit/release, including move OCC pass-through and remaining edit/release gaps. | 0.98 |
| S3 | `tests/test_engine_cockpit_view_1078.py` | CockpitView contract requiring OCC token for edit/move and stale-token behavior. | 0.92 |
| S4 | `.owlbear/briefs/draft-kanban-web-gui-prep/decisions.md` | D2 baseline: accepted single-user concurrent overwrite risk. | 0.90 |
| S5 | `.owlbear/briefs/draft-cockpit/voices/data-debate.md` | Release-path TOCTOU called out as known limitation in Cockpit deliberation. | 0.86 |
| S6 | `.owlbear/briefs/draft-cockpit/decisions.md` | D12 confirms release endpoint trusts request shape and active claim presence. | 0.84 |
| S7 | `serve/kanban/src/owlbear_kanban/models.py` | `claimed_by` is projection-only (`exclude=True`), not persisted on disk. | 0.98 |
| S8 | `tests/test_cockpit_mutation_race_1131.py` | Proof that Cockpit HTTP release returns 409 even after a genuine claim (`test_release_returns_409_even_when_task_is_genuinely_claimed`). | 0.95 |

## 3. Analysis

### 3.1 AgentView method map (AC1)

| Method/path | Read precheck | Write delegate | Current OCC posture |
|---|---|---|---|
| `AgentView.edit_task` | `show_task` | `engine.edit_task(..., source="agent")` | No `expected_updated` passed by facade; precheck/write split remains (S1). |
| `AgentView.move_task` | `show_task` + predicate validation | `engine.move_task(..., source="agent")` | No `expected_updated` passed by facade; precheck/write split remains (S1). |
| `AgentView.start_work` | `show_task` archived check | `engine.start_work(...)` | Split precheck exists, but downstream claim path uses CAS semantics (S1). |
| `AgentView.end_work` (non-release) | `show_task` claim/predicate checks | `engine.end_work(..., expected_updated=before.updated)` | OCC-guarded branch; stale conflict is handled (S1). |
| `AgentView.end_work` (`outcome="release"`) | `show_task` claimed check | `engine.release_task(...)` | No OCC token; uses plain read-mutate-write release primitive (S1). |

### 3.2 Cockpit writer-surface map (AC2)

| Route | Read precheck | Mutation call | Residual race property |
|---|---|---|---|
| `POST /tasks/{id}/move` | `show_task` + transition check + stale snapshot check (`req.updated`) | `engine.move_task(..., expected_updated=req.updated)` | OCC-guarded at route and engine layers; no remaining move-specific CAS gap (S2). |
| `POST /tasks/{id}/edit` | `show_task` + route timestamp compare | `engine.edit_task(...)` | Stale check is route-local; engine CAS token is not threaded through (S2). |
| `POST /tasks/{id}/release` | `show_task` + `claimed_by` guard | `engine.release_task(...)` | On current new-schema boards this route is effectively unreachable: `claimed_by` is projection-only (`exclude=True`) and is not persisted, so post-read it is `None` and route returns 409 before mutation (S2, S7, S8). |

Shared primitive note: residual shared unguarded surfaces are edit (Cockpit HTTP route-level precheck without engine CAS token) and release (`engine.release_task(...)` without CAS). `CockpitView.release_task` delegates to `engine.release_task(...)` after a separate `show_task` precheck on `claimed_at`, and `AgentView.end_work` release branch also delegates there, so the live release race is rooted in the raw release primitive used by multiple facades rather than the current HTTP route path (S1, S2, S3, S7, S8).

### 3.3 Practical exploitability assessment (AC2)

| Surface | Practical likelihood | Practical impact | Notes |
|---|---|---|---|
| AgentView over stdio MCP (edit/move) | Low to medium | Mostly stale-validation semantics | Server process is effectively serialized, but cross-process writers still exist (S1). |
| AgentView over stdio MCP (`end_work` release branch) | Low to medium | Can clear a fresher claim through unguarded release primitive | Branch-specific gap exists despite non-release end_work OCC (S1). |
| Cockpit HTTP routes | Medium | Stale overwrite on edit path | Separate process boundary increases interleaving opportunities; move is OCC-threaded, edit still bypasses engine CAS token, and release is currently route-dormant on new-schema boards due to `claimed_by` guard behavior (S2, S7, S8). |

Conclusion: the dominant root issue is the shared unguarded `engine.release_task` primitive plus route-level OCC bypass on Cockpit edit (not move). Cockpit HTTP release is currently dormant on new-schema boards, but release-race exposure remains live through AgentView and CockpitView delegation into the same primitive (S1, S2, S3, S7, S8).

### 3.4 Mitigation trade-off matrix (AC3)

| Option | Summary | Pros | Cons | Confidence |
|---|---|---|---|---|
| A. Keep accepted risk | Preserve current behavior. | No implementation cost. | Leaves known route-level races on edit/release and shared release primitive exposure. | 0.32 |
| B. Cockpit-first OCC hardening | Require/propagate OCC tokens on Cockpit edit path; separately repair release route semantics and then add compare-and-release there. | Small blast radius; immediate risk reduction on active HTTP writer path; aligns routes with tested CockpitView OCC patterns. | Does not remove AgentView/CockpitView release branch exposure until engine primitive is hardened. | 0.74 |
| C. Engine-primitive-first release CAS + cockpit wiring | Add `expected_updated` CAS support to `engine.release_task`, then thread tokens from AgentView/CockpitView and any repaired HTTP release route. | Fixes shared root primitive once; closes release branch gap across live facades. | Requires coordinated signature and call-site updates across engine and cockpit layers. | 0.88 |
| D. Coarse locking | File/process locks around precheck+write. | Can prevent interleavings without token plumbing. | Operational complexity, lock contention, and failure-mode overhead. | 0.40 |

## 4. Recommendation and D2 Re-evaluation (AC4)

Recommendation: **Fix now via Option C (engine-primitive-first release CAS + cockpit wiring), then complete route-level OCC parity on edit/release.**

Why:

1. `AgentView.end_work` is mixed: non-release is OCC-guarded, but `outcome="release"` still delegates to unguarded `engine.release_task` (S1).
2. `engine.release_task` is a shared primitive used by AgentView release flow, CockpitView release flow, and Cockpit HTTP release route, so hardening it first removes the common root race (S1, S2, S3).
3. Cockpit edit still needs route-level OCC parity after release CAS hardening because it bypasses token-threaded engine writes; move already forwards `expected_updated`, and HTTP release is currently route-dormant on new-schema boards due to `claimed_by` guard behavior (S2, S7, S8).

Priority re-score note: removing HTTP release from the current live route inventory does not weaken Option C; it strengthens it, because remaining live release exposure is concentrated in the shared engine primitive reached by AgentView and CockpitView.

D2 re-evaluation:

- **D2 remains partially valid** for the earlier single-user baseline and serialized MCP flow assumptions.
- **D2 is no longer sufficient as-is** for current multi-surface writer reality (MCP + Cockpit HTTP in separate processes) plus shared unguarded release primitive.
- Therefore: preserve D2 history, but supersede it operationally with engine-primitive-first release CAS and cockpit route OCC parity.

Challenge: **block** — confidence in original defer recommendation: **0.36**. Main challenge accepted: release-path impact was understated; recommendation revised from defer to engine-primitive-first fix.

## 5. Follow-up Tasks (AC5)

Fix is recommended, so implementation follow-ups were created:

- **#1130** — Implement cockpit mutation OCC parity decomposition (research parent)
	Affected modules/methods:
	- `.owlbear/research/cockpit-mutation-occ-parity.md` (decomposition record)
	- Child implementation tasks: #1133 (engine release CAS), #1132 (cockpit route wiring)
- **#1131** — Add cockpit mutation race tests for stale-precheck interleavings (characterization baseline)
	Affected test modules:
	- `tests/test_cockpit_mutation_api.py`
	- `tests/test_engine_cockpit_view_1078.py`
	- `tests/test_cockpit_mutation_race_1131.py`

Scope coherence note after live-code recheck:

- `POST /move` is already OCC-complete in `mutation.py` (`MoveRequest.updated` + `expected_updated` forwarding), so follow-up execution scope should be interpreted as edit/release hardening, not move OCC introduction.
- In #1130, the older key-finding line "POST /move has no OCC" is stale against live code; keep #1130's active implementation trajectory on #1133 (engine release CAS) and #1132 (route wiring for edit/release parity).
- In #1131, AC2 is still useful as an OCC contrast/proof test (move forwards CAS), but any inherited wording that treats move as an open gap should be treated as stale.
- In #1131, inherited wording that points to #1136 should be treated as stale because #1136 was superseded by #1133 in the active follow-up chain.
