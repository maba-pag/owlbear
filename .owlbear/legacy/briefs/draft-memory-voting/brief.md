# Brief: Memory Voting — Forced Assessment Scoring

## Problem

Memory recall ordering is static. Entries are sorted by `confidence` (set at creation, never updated). No feedback loop from consuming agents exists. High-confidence entries persist at the top regardless of practical value. Lower-confidence entries with genuine practical value remain buried. The system cannot self-improve.

## Solution

Forced assessment scoring — agents categorize all recalled entries at end-of-task into four quality buckets. Scores update based on assessment evidence only. No time-based decay. Recall ordering becomes self-improving: outstanding entries rise, mediocre entries drift down, dead entries get blocked for human review.

### Core Mechanism

1. **Recall** delivers 20 entries: 16 by score + 2 explore (lowest total assessments) + 2 challenge (lowest outstanding count)
2. **Assessment** at end-of-task: agent categorizes all 20 into buckets:
   - **Outstanding** ("this was genuinely great") → score +X
   - **Used but unremarkable** ("I applied this, it was fine") → score -Y (where Y << X)
   - **Didn't use** ("didn't apply / out of scope") → no score change
   - **Factually wrong** ("this is incorrect") → enters confirmation cycle
3. **Score** replaces confidence as the recall sort key
4. **Slot-efficiency block** catches persistently-unused entries at 50× threshold
5. **Confirmation cycle** for "factually wrong" prevents single-vote nuclear blocks

### Key Design Properties

- **No time-based decay.** Score moves only on assessment evidence. Dormancy-safe.
- **Quality over popularity.** "Outstanding" is a quality judgment by agents who applied the guidance. Exposure frequency doesn't inflate scores.
- **Opaque bucketing.** Agents don't know which buckets affect scores — no gaming incentive.
- **Proven mediocrity sinks; unknown stays neutral.** Used-but-never-great entries drift down. Never-used entries are safe until slot-efficiency catches them.

## Scope

### In scope (V1)

- New model fields: `outstanding_count` (int), `unremarkable_count` (int), `didnt_use_count` (int), `score` (float)
- New states: `contested`, `disputed`, `stale`
- Score computation: `score = initial_confidence + (outstanding_count × X) - (unremarkable_count × Y)`
- Recall ordering: sort by `(state_rank, -score, id)` replacing `(state_rank, -confidence, id)`
- Reserved slot logic: 16 regular + 2 explore (lowest total assessments) + 2 challenge (lowest outstanding count)
- New MCP tool: `assess_memories` (batch: list of entry_id → bucket assignments)
- Slot-efficiency check: `didnt_use_count > 50 × max(outstanding_count + unremarkable_count, 1)` → state `stale`
- Confirmation cycle: first "factually_wrong" → `contested`; second confirmation → `disputed`
- Migration: existing entries get `score = confidence`, all counters = 0
- Pipeline instruction update: assessment framing in end_work protocol

### Out of scope (follow-on)

- Cockpit UI surfacing assessment signal
- +X/-Y magnitude tuning
- Confidence field deprecation
- Per-agent score variants
- Assessment analytics/dashboards
- Automated scope-narrowing suggestions

## Acceptance Criteria

### AC1 — Score field and computation

Memory entries have a `score` field (float). Score = `initial_confidence + (outstanding_count × X) - (unremarkable_count × Y)` where X > Y. Recall sorts by `(state_rank, -score, id)`. Initial values: X=0.1, Y=0.01 (10:1 ratio, conservative start). X and Y are named constants, not magic numbers.

### AC2 — Assessment MCP tool

`assess_memories` tool accepts a list of `{entry_id, bucket}` pairs where bucket ∈ {outstanding, unremarkable, didnt_use, factually_wrong}. Updates counters and score atomically per entry. Returns success/failure per entry. Validates: entry exists, entry is in voteable state (approved/curated/contested), bucket is valid enum value.

### AC3 — Reserved slot allocation

`recall_memory` returns exactly `limit` entries (default 20): `limit - 4` highest-score within scope, 2 with lowest total assessment count `(outstanding_count + unremarkable_count + didnt_use_count)`, 2 with lowest `outstanding_count`. Deduplication: if an entry qualifies for multiple pools, it occupies only one slot (priority: explore > challenge > regular). If fewer entries exist than `limit`, return all available.

### AC4 — Slot-efficiency binary block

After each `assess_memories` call, the system checks assessed entries: if `didnt_use_count > 50 × max(outstanding_count + unremarkable_count, 1)`, entry state transitions to `stale`. Stale entries are excluded from recall. State transition is logged.

### AC5 — Factually-wrong confirmation cycle

First "factually_wrong" assessment → entry state becomes `contested`. Contested entries remain in recall (still voteable). If a subsequent assessment from a different task (not the same task that contested it) marks the same entry "factually_wrong" → state becomes `disputed`. Disputed entries are excluded from recall.

### AC6 — State machine additions

States `contested`, `disputed`, and `stale` are added to the memory model. `contested` entries are recalled normally (state_rank unchanged). `disputed` and `stale` entries are excluded from recall (highest state_rank, sorted below everything). All three are resolvable by human curator (existing curation tools).

### AC7 — Migration

Existing entries: `score = confidence`, all assessment counters = 0, state unchanged. No data loss. Recall ordering is identical to pre-migration until first assessments arrive. Migration is idempotent (safe to re-run).

### AC8 — Instruction integration

Pipeline end_work protocol includes assessment instruction. Framing text:

> For each recalled memory entry, categorize your experience:
> - **Outstanding** — this entry's guidance was genuinely great for this task
> - **Used but unremarkable** — I applied or referenced this entry's guidance and it was adequate
> - **Didn't use** — I didn't apply or reference this entry's guidance
> - **Factually wrong** — this entry contains incorrect information
>
> "Apply or reference" includes: following guidance, avoiding a warned pitfall, or confirming your approach was correct.

No explanation of scoring mechanics in agent-facing instructions.

## Dependencies

- `serve/memory/` — model changes, score computation, state machine extensions
- `serve/mcp-memory/` — new `assess_memories` tool, modified `recall_memory` sorting and slot logic
- `share/instructions/pipeline-agents.instructions.md` — end_work assessment protocol
- `share/skills/r-pipeline-protocol/SKILL.md` — post-task reflection assessment integration

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents categorize lazily (everything "didn't use") | Medium | Score signal is noise; system doesn't improve | Opaque bucketing removes gaming incentive; clear framing emphasizes "apply or reference" boundary |
| +X/-Y magnitude wrong | High | Ordering changes too fast or too slow | Conservative initial values (X=0.1, Y=0.01); tunable constants; follow-on tuning task |
| Contested entries never get second opinion | Low | Entries stuck in contested indefinitely | Contested entries remain in recall; second opinion comes naturally. Follow-on cockpit task surfaces stuck entries |
| 50× threshold too conservative | Medium | Dead entries linger in slots | Threshold is a named constant; follow-on tuning task adjusts empirically |
| Reserved slots degrade recall quality | Low | 4 of 20 entries suboptimal | By design (exploration investment); challenge slots accelerate demotion which improves future regular slots |

## Decisions Record

| # | Decision | Chosen | Key rejected alternative |
|---|----------|--------|------------------------|
| D1 | Project type | Existing feature/refactor | New product / pure refactor |
| D2 | Score scope | Global (pooled across agents) | Per-agent scoring |
| D3 | Investment tier | Shared (full panel) | Quick / Standard |
| D4 | V1 scope | Ordering must change | Data collection only |
| D5 | Scoring approach | Forced assessment buckets | Time-based decay; accumulative voting |
| D6 | "Didn't use" bucket count | One | Two (out-of-scope vs. in-scope-irrelevant) |
| D7 | Slot-efficiency model | Binary threshold block | Scaled deterioration |
| D8 | Gaming mitigation | Opaque bucketing + framing | Ratio monitoring |
| D9 | Cold-start | Reserved explore + challenge slots | Random sampling; scope reliance only |
| D10 | Slot allocation | 16+2+2=20 | Higher totals; aggressive exploration |
| D11 | Block trigger | 50× ratio | Lower thresholds; dual condition |
| D12 | Blocked states | Two: disputed + stale | Single blocked state with reason enum |
| D13 | Instruction framing | "Apply or reference" (incl. avoidance/confirmation) | "Inform your work" (broader) |
| D14 | Factually-wrong handling | Confirmation cycle (contested → disputed) | Single-vote block; quorum without prompt |

## Follow-On Tasks

### Follow-On A: Assessment Magnitude Tuning

**Blocked until:** 2-4 weeks of agent work with the scoring system live.

**Background:**
The memory scoring system uses forced assessment buckets. Agents categorize recalled entries as outstanding (+X to score), unremarkable (-Y to score), didn't-use (no change), or factually-wrong (block). Initial values are X=0.1, Y=0.01. These values determine how fast the system converges — too aggressive and scores swing wildly on few assessments; too conservative and the system barely moves.

**What to check:**
1. Score distribution: run `recall_memory` and examine score values across entries. Are they differentiated (spread from ~0.5 to ~1.5) or clustered (all between 0.68 and 0.72)?
2. Assessment counts: look at entries' outstanding/unremarkable/didnt_use counters. What's the typical ratio? If most entries have 50+ unremarkable and 0 outstanding, either the agents aren't using "outstanding" or nothing is actually outstanding.
3. Score deltas: compare an entry's current score to its initial confidence. Has the ordering actually changed? If entries with high confidence are still at the top despite never being "outstanding," X might be too low.
4. Stale threshold: any entries approaching the 50× ratio? How far are typical entries from triggering?
5. Contested entries: are any stuck in contested state? How long?

**Why adjust:**
- If scores haven't moved after 2 weeks: X and Y are both too small. Double them.
- If ordering has changed dramatically (top entries are completely different from the original confidence ordering): X is too large. Halve it.
- If everything is drifting down (average score << average initial confidence): Y is too large relative to how often agents rate "outstanding." Either reduce Y or investigate whether agents are actually using the outstanding category.
- If nothing ever hits stale: 50× threshold might be too conservative. Consider 30× if entries are clearly dead but not reaching threshold.

**How to adjust:**
- X and Y are named constants in the memory engine scoring module. Change values, re-run tests, deploy.
- The 50× stale threshold is also a named constant.
- Score recomputation: scores can be recalculated from counters + initial confidence at any time (they're derived values). Changing X/Y and recomputing all scores is safe and non-destructive.

### Follow-On B: Cockpit Assessment Visibility

**Blocked until:** Memory voting V1 is complete AND magnitude tuning (Follow-On A) has been done at least once.

**Background:**
The memory system now tracks per-entry assessment counts (outstanding, unremarkable, didnt_use) and has three special states (contested, disputed, stale). The cockpit memory curation UI needs to surface this signal so human curators can make informed decisions.

**What to build:**
1. Display assessment counts per entry in the memory curation view
2. Highlight "thriving" entries (high outstanding count, high score)
3. Highlight "at risk" entries (high unremarkable count, approaching stale threshold)
4. Surface `contested` entries prominently (waiting for confirmation or human override)
5. Surface `disputed` and `stale` entries in a review queue (these are blocked from recall and need human action: fix content, narrow scope, or confirm deletion)

**Design constraints:**
- Assessment counts are integers on the model: `outstanding_count`, `unremarkable_count`, `didnt_use_count`
- Score is a float derived from: `initial_confidence + (outstanding_count × X) - (unremarkable_count × Y)` where X and Y are engine constants
- States: `pending`, `approved`, `curated`, `contested`, `disputed`, `stale`, `deleted`
- The existing cockpit memory API (`GET /api/memories`) needs to include the new fields
- Cockpit uses Porsche Design System (PDS) React components

**Why this matters:**
Without cockpit visibility, the human curator can only resolve disputed/stale entries via MCP tools (command-line style). The cockpit should make it obvious which entries need attention and what action to take.

### Follow-On C: Confidence Field Deprecation Assessment

**Blocked until:** 4-8 weeks of agent work with scoring system live AND Follow-On A completed.

**Background:**
The memory model originally used `confidence` (0.7-1.0, set at creation) as the recall sort key. The voting system replaced this with `score` (derived from confidence + assessments). Confidence now serves only as the initial seed value for score. The question is whether confidence should remain as a visible field or be fully absorbed into score.

**What to check:**
1. Is `confidence` still being set meaningfully by `save_memory`? Or do all entries default to the same value?
2. Does the initial confidence value actually correlate with eventual quality (high-confidence entries tend to become outstanding)? If not, confidence was never a good quality proxy and the initial seed could just be a constant (e.g., 0.8 for all entries).
3. Are there downstream consumers of `confidence` beyond the recall sort? (Cockpit display, curation logic, etc.)
4. If confidence were removed from the model, what migration is needed? (Just drop the field and use a constant initial score instead.)

**Decision to make:**
- Keep confidence as initial seed (status quo)
- Replace confidence with a constant initial score (simplification)
- Keep confidence as a separate display field but remove from scoring entirely
