# Data Stance — Critic Debate Log

## Cycle 1

### Initial Position (Confidence: 0.50)

Core claim: The redesign is a presentation concern with one critical data-integrity boundary — task-state signals (blocked, priority, dependencies) must never be hidden or ambiguously rendered. Formatting happens at the display boundary via pure utility functions.

Key assertions:
- Timestamps formatted to relative/human-readable
- Enums mapped from internal strings (blocked, rejected, stuck) to display labels
- Tags parsed from comma-separated strings into typed chips
- Empty fields suppressed with rules (hiding blocked:false safe, blocked:true dangerous)
- Card face: title, ID, priority badge, blocked icon, 2-3 tags
- Sidecar: "shows everything, formatted"

### Critic Challenges (Pressure: high, Confidence in position: 0.38)

1. **CRITICAL — Integrity boundary misdrawn.** `updated` is a write-safety token (optimistic concurrency), not just a display timestamp. Formatting it for mutations would corrupt data. The draft never distinguished canonical values from display values.

2. **CRITICAL — `computeSignal` is domain logic at the display boundary.** Precedence chain (decision-pending > blocked > claimed > deps-unmet > ready) already exists. The draft called everything "formatting" — this is wrong. Domain logic exists at the boundary and must be acknowledged.

3. **CRITICAL — Signal set incomplete.** Draft named only blocked, priority, dependencies. Actual availability signals include claimed and decision-pending as first-class states. Hiding those is equally dangerous.

4. **MODERATE — Wrong enum vocabulary.** Draft grouped "blocked, rejected, stuck" as task-level enums. Actually "stuck" and "rejected" are session-derived states, not task summary fields. Blending two data domains.

5. **MODERATE — Tags are already arrays.** Draft proposed parsing comma-separated strings. API already delivers string arrays. Solving a problem that doesn't exist.

6. **CRITICAL — Validation asserted but undefined.** Draft said "input validation checks the API response shape" but current frontend does unchecked TypeScript casts. No validator exists. No recovery model specified.

7. **CRITICAL — Sidecar is a write surface.** Draft treated sidecar as read-only ("shows everything, formatted"). Actually includes TaskFieldsEditor and TaskActions — display transforms sit adjacent to canonical write values.

8. **CRITICAL — Malformed data policy contradicts non-ambiguity.** For critical fields, "—" placeholder is still ambiguous about whether the task is actionable. Position never resolves this.

9. **MODERATE — Card may need recency.** Draft excluded timestamps from card face, but current card already renders update recency for triage.

### Modeler Response

All challenges accepted. Major revisions:
- Introduced canonical vs. display value partition as the core organizing principle
- Acknowledged `computeSignal` as domain logic, not formatting
- Expanded signal set to full precedence chain
- Corrected tags from comma-separated to arrays
- Separated task states from session states
- Added "unknown" signal state for malformed critical fields
- Acknowledged sidecar as read-write surface with adjacency rules
- Restored update recency on card face

## Cycle 2

### Revised Position (Confidence: 0.75)

Core claim: The cockpit is a read-write mutation surface. Display transforms operate on a strict partition: canonical values (for mutations) stay untouched; display values (for humans) get formatted. Three data streams with independent freshness. Signal is cross-stream domain logic. Unknown state needed for malformed inputs.

### Critic Challenges (Pressure: high, Confidence in position: 0.42)

1. **CRITICAL — SSE freshness model misstated.** SSE delivers invalidation mtimes, not task payloads. Board refetches off that signal. Sidecar detail lives in separate state and refetches on selection/nonce, not on tasks-changed event. Three stores with genuinely independent freshness.

2. **CRITICAL — Stale-write risk is in interaction layer, not formatting.** The current write path snapshots `updated` into drag/context-menu state and may reuse a stale token. This is outside the formatting boundary. Position overclaims mutation safety by constraining only the formatting layer.

3. **CRITICAL — Validation gap exists before formatters run.** Frontend does `task.tags.slice()`, boolean checks etc. before any formatter is involved. Malformed payloads can crash components upstream of formatting. The formatter-level null-safety doesn't cover the actual render path.

4. **CRITICAL — Enum vocabularies are config-driven.** Board API delivers `statuses[]` and `priorities[]` dynamically. Task priority is not fixed P1-P4. `archived` is a special move target, not a configured status. Session states include `running`, `released`, `expired` — `active` is a UI filter label, not a canonical state.

5. **MODERATE — Signal is computed client-side from cross-stream join.** List-task payload doesn't carry a `signal` field. Card signal computed by joining task data with pending-DR IDs from separate endpoint. Cross-stream dependency at the display boundary.

6. **MODERATE — dep_status vocabulary broader than claimed.** Can be `blocked`, `ok`, `redirect`, or `null`. Current logic treats only `blocked` as signal; `redirect` falls through to ready. May be deliberate UX collapse.

7. **MODERATE — Canonical field set still incomplete.** Write APIs also include `parent`, `depends_on`, `body`, `block_reason`, `archival_reason`, `archival_refs`. Tags not passive — `block:user` is system-coupled.

### Modeler Response

All challenges accepted with scope-honest responses:
- Corrected SSE model to invalidation-based with three independent freshness stores
- Narrowed mutation-safety claim: acknowledged stale-write is pre-existing interaction-layer concern, not formatting. Redesign's responsibility is "don't make it worse"
- Honest about validation scope: redesign should not add runtime schema validation (scope creep), but formatters must be null-safe and signal must have unknown state
- Made enum formatting config-aware with dynamic lookup
- Acknowledged cross-stream signal computation and DR freshness lag
- Added system-coupled tag awareness (block:user)

## Outcome

Position hardened from initial 0.50 to final 0.80. The two Critic cycles forced three fundamental corrections:
1. From "presentation concern" to "read-write mutation surface with canonical/display partition"
2. From hardcoded enum vocabulary to config-driven dynamic formatting
3. From overclaiming mutation safety to honestly scoping what this redesign owns vs. pre-existing concerns

Key residual uncertainty: edge cases in three-stream freshness model and whether unknown signal state surfaces in practice.
