# End-User Debate Log — Knowledge Engine Activation

## Cycle 1

### Draft Position (Pre-Critic)

Eight concerns presented as equal-weight UX gaps:

1. Worker count is implementation leaking into UX — should be hidden
2. Two-phase enrichment is confusing — should collapse to one action
3. Preview validation is weak — needs richer display (rendered markdown, 500-1000 chars)
4. Progress feedback is absent — needs progress indicators
5. Search result presentation is undefined — graph relationships invisible
6. No browse/explore capability — user can't see KB shape
7. Error recovery paths are vague — multiple failure modes unaddressed
8. Source saving should be default, not optional

### Critic Challenges (Cycle 1)

**Critical:** Position quietly changes the project from activation into a richer product UI without defending the scope change. Items §§3-6 demand rendered previews, progress indicators, explainable graph presentation, and browse/explore — beyond an activation/refactor brief.

**Moderate:** Worker count exposure is intentional per D3/D7 (session coupling, visible costs). "Hide it" ignores the design's own rationale.

**Moderate:** Two-phase objection treats naming as the problem but erases a real semantic split. D7 and D14 define different jobs, pull queues, and completion semantics.

**Moderate:** Preview critique is anecdotal. Fetch_method persistence means one-time validation; no evidence that larger excerpts materially reduce false confirmations.

**Moderate:** Search results are defined as graph-augmented (D11) — the gap is presentation detail, not absence.

**Moderate:** `list_sources` and `get_stats` exist. "No browse capability" is inaccurate.

**Moderate:** Error recovery bundles handled and unhandled cases, making the gap seem broader than evidence supports.

**Moderate:** Not every ingest is meant to be durable corpus membership. Optional saving is a valid design choice.

**Blind spots identified:** Pipeline agents as co-users ignored. No activation vs. polish distinction. 548-source operational lifecycle unaddressed. Entity schema uncertainty affects UX trust arguments.

**Critic confidence:** 0.56 | **Pressure:** medium

### Revisions After Cycle 1

- Introduced activation blocker / risk / polish taxonomy
- Worker count: moderated from "hide" to "default with guidance" — preserves D3/D7 intent
- Two-phase: moderated from "collapse" to "keep phases, add system-guided transitions"
- Preview: downgraded from blocker to post-activation polish — one-time validation + persistence mitigates risk
- Browse/explore: reframed from "no capability" to "thin capability insufficient at 548-source scale"
- Error recovery: separated handled cases (validation, browser fallback, refresh) from genuinely missing (delete, re-enrich)
- Added pipeline agent requirements as distinct user class
- Added startup auth loop as prerequisite UX concern

---

## Cycle 2

### Refined Position (Pre-Critic)

Four activation blockers (A1-A4), four product polish items (P1-P4), agent-as-user section. Confidence 0.75.

### Critic Challenges (Cycle 2)

**Critical:** Several blockers (A1, A2, A4) are evaluated against tool contracts (get_next_batch, store_enrichment, get_consolidation_candidates) that don't exist in implementation yet — they're aspirational design. Positions are judged against interfaces that are still being designed.

**Critical:** P2 (source management as polish) is not convincing. 548 sources already exist. `list_sources` returns only name/source_type/scope; `get_stats` returns only aggregate counts. At that scale, source management is basic trustworthiness, not polish. → **Promoted to blocker B2.**

**Critical:** A4 (search provenance) is framed too softly. Current implementation returns title/score/snippet/entity_type — no graph data at all. This is a contract contradiction, not a presentation detail. → **Strengthened to B1.**

**Moderate:** A1's "default to 4" is numerically speculative — no measured throughput data supports that number. → **Removed specific number, recommended Brief-determined default.**

**Moderate:** A2's "47 cross-source candidates found" assumes get_stats exposes candidate count, which isn't in the current contract. → **Acknowledged gap, recommended adding candidate count to get_stats.**

**Moderate:** P4 (delete source) is weaker than presented. Refresh doesn't handle wrong/duplicate/accidentally persisted sources. With sources.yaml as rebuild source of truth, no delete path is a real gap. → **Promoted to risk R4.**

**Blind spots identified:** Startup (auth loop) is the actual first UX — before any other concern applies. Source saving determines rebuild survivability, not a flow refinement. Entity type examples anchor on an unfinalised taxonomy.

**Critic confidence:** 0.52 | **Pressure:** high

### Revisions After Cycle 2

- Promoted source management from polish to blocker (B2) — 548-source scale demands inspection
- Strengthened search provenance to top blocker (B1) — contract contradiction, not presentation gap
- Removed speculative throughput numbers from worker count recommendation
- Acknowledged get_stats contract gap for candidate count
- Promoted delete source from polish to risk (R4)
- Strengthened source saving from flow refinement to risk (R3) — rebuild survivability
- Added startup auth loop as Warning #2 (prerequisite for all other UX)
- Added entity schema uncertainty caveat on provenance examples
- Added 548-source rebuild as operational cliff warning

---

## Position Evolution Summary

| Concern | Cycle 0 | After Cycle 1 | After Cycle 2 (Final) |
|---------|---------|---------------|----------------------|
| Search provenance | Undefined (§5) | Blocker A4 (moderate) | **Blocker B1** (strengthened — contract contradiction) |
| Source management | No capability (§6) | Polish P2 | **Blocker B2** (promoted — 548-source scale) |
| Ingest error feedback | Vague (§7) | Blocker A3 | **Blocker B3** (held) |
| Worker count | Hide it (§1) | Blocker A1 (default to 4) | **Risk R1** (default with guidance, no speculative numbers) |
| Phase transitions | Collapse (§2) | Blocker A2 (system guidance) | **Risk R2** (system-guided handoff, acknowledged get_stats gap) |
| Source saving | Default (§8) | Polish P3 | **Risk R3** (rebuild survivability) |
| Delete source | Missing (§7) | Polish P4 | **Risk R4** (promoted — refresh insufficient) |
| Preview validation | Weak (§3) | Polish P1 | **Polish P1** (held — one-time + persistence mitigates) |
| Progress feedback | Absent (§4) | Folded into A2/get_stats | Folded into B2/R2 |
| Browse/explore | No capability (§6) | Reframed (thin, not absent) | **Polish P2** (cockpit integration) |

**Final confidence:** 0.78
