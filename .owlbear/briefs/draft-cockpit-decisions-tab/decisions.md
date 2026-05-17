# Decisions — Cockpit Decisions Tab

## D1 — 2026-05-17 — Project Type

**Status quo:** No project type recorded.
**Decision to make:** Classify this work for research scoping.

**Options considered:**

- A: net-new — build decisions UI from scratch
- B: existing-feature/refactor — elevate existing decisions infrastructure to first-class tab

**Chosen:** B — existing-feature/refactor. Backend routes, frontend hooks (`usePendingDRs`), components (`DecisionViewport`, `DRStatusIndicator`, `ResolveModal`), and SSE events already exist. The work extends and restructures rather than creates from zero.

**Rejected:**

- A because substantial decisions code already exists on both sides of the stack.

## D2 — 2026-05-17 — Investment Tier

**Status quo:** No tier set.
**Decision to make:** Calibrate depth for this brief.

**Options considered:**

- A: Shared — multi-consumer, pattern-setting
- B: Production — full panel + Critic at every boundary

**Chosen:** B — Production. The tab system infrastructure is a prerequisite for at least Memory and Ideas Notebook tabs. The tab architecture decisions have high downstream impact and warrant maximum rigor.

**Rejected:**

- A because the pathfinder nature of the tab system raises the stakes beyond typical shared work.

## D3 — 2026-05-17 — Task Context Panel

**Status quo:** Input doc proposed three-column layout with task context alongside DR.
**Decision to make:** Include task context panel or drop it?

**Options considered:**

- A: Include task context panel (20% list / 40% DR / 40% task)
- B: Drop task context panel (list + detail only)

**Chosen:** B — Drop. DRs are self-contained; user rarely needs to read the task to resolve a DR. Task context is noise, not signal.

**Rejected:**

- A because DRs are self-contained by design.

## D4 — 2026-05-17 — Resolved DRs Timing

**Status quo:** Only pending DRs visible. Input doc included resolved DR browsing.
**Decision to make:** V1 or fast-follow?

**Options considered:**

- A: Include resolved DRs in V1 (new backend endpoint, mixed-state list, sort logic)
- B: Defer to fast-follow (pending-only for V1, simpler list rendering)

**Chosen:** B — Defer. Core pain is pending visibility. Resolved browsing is secondary, adds backend work and UI complexity. Fast-follow once the tab works.

**Rejected:**

- A because resolved DR browsing is an unvalidated need (no named actor/trigger), and deferring it cuts scope cleanly.

**Source inputs:**

- User: confirmed "core pain is pending visibility — resolved is nice-to-have"
- Simplifier: recommended cut for scope reduction
- First-principles: flagged as unvalidated

## D5 — 2026-05-17 — P1/P2 Decomposition

**Status quo:** Single deliverable covering tab infra + decisions content.
**Decision to make:** Split into two sequential deliverables?

**Options considered:**

- A: Single deliverable
- B: P1 tab shell + P2 decisions content

**Chosen:** B — Split. P1 validates the tab system (nav-rail + routes, kanban in tab slot, skeleton decisions page). P2 fills in decisions content. This lets the pathfinder question ("does the tab system work?") be answered first, and unblocks other tab modules to implement in parallel after P1.

**Rejected:**

- A because bundling delays validation and blocks parallel work on other tabs.

**Source inputs:**

- User: "this way the other modules can start implementing at the same time, after P1 is done"
- Simplifier: proposed the decomposition

## D6 — 2026-05-17 — Deep-Link Receiver

**Status quo:** Input doc included deep-link receiver. Kanban-side sender scoped out.
**Decision to make:** Build deep-link receiver or defer?

**Options considered:**

- A: Build receiver in V1 (route param, auto-select DR on arrival)
- B: Defer (route param is free infrastructure from React Router, not an explicit outcome)

**Chosen:** B — Defer. No sender means no user path triggers it. React Router gives `/decisions/:id` for free as an implementation detail. Not an outcome worth testing.

**Rejected:**

- A because a receiver with no sender is dead code. Trivially added when the sender ships.

**Source inputs:**

- Simplifier: "deep-link receiver with no sender is speculative infrastructure"
- First-principles: "either include the sender or drop the receiver"
