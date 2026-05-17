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

## D7 — 2026-05-17 — P2 Layout Pattern

**Status quo:** Three candidate patterns: full-page list + modal, master-detail split, inline expandable rows.
**Decision to make:** Which layout pattern for the decisions tab content?

**Options considered:**

- A: Full-page list + modal — single-column list, click opens ResolveModal overlay
- B: Master-detail split — permanent two-column with list left, detail right
- C: Inline expandable rows — single-column list with click-to-expand body + form

**Chosen:** A — Full-page list + modal. Content density (1–5 pending DRs) makes a permanent split wasteful. ResolveModal is reusable as-is (no decomposition needed). Users already know the modal pattern from the sidecar. Simplest path with lowest rework.

**Rejected:**

- B because 1–5 items leave the list panel 80% empty, and requires decomposing ResolveModal into an inline form (meaningful rework for no UX gain)
- C because long DR bodies (400+ words) push other items off screen, and also requires form decomposition + expand/collapse state management

**Source inputs:**

- Codebase evidence: DecisionViewport renders 5–7 lines per item; ResolveModal is self-contained overlay; DR bodies range 70–500+ words
- Layout proportionality analysis from Phase 2 M3 drill-in

## D8 — 2026-05-17 — Sidecar DR Presence After Tab Ships

**Status quo:** DecisionViewport renders in kanban sidecar, providing "see blocked task → resolve DR" proximity.
**Decision to make:** What happens to sidecar DR list once the decisions tab exists?

**Options considered:**

- A: Keep full DecisionViewport in kanban sidecar
- B: Reduce to pending count + "View decisions" link
- C: Remove DecisionViewport from sidecar entirely

**Chosen:** C — Remove. Clean separation, KISS. DRStatusIndicator in the status bar remains as global notification. No duplicate rendering paths to maintain. **Timing: P2** (not P1) — removal happens when the decisions tab content provides the replacement. P1 is purely additive.

**Rejected:**

- A because maintaining two full DR renderers is unnecessary duplication
- B because even a link adds sidecar complexity for minimal value when the status-bar indicator already provides awareness

**Source inputs:**

- Architecture review: single ResolveModal at Shell level, sidecar becomes route-conditional
- UX review: acknowledged loss of proximity flow but accepted status-bar indicator as sufficient

## D9 — 2026-05-17 — Draft Persistence Scope

**Status quo:** Closing ResolveModal loses in-progress response and notes.
**Decision to make:** How much draft persistence for V1?

**Options considered:**

- A: Snapshot DR into modal-local state on open (SSE guard only)
- B: Full localStorage persistence with invalidation logic

**Chosen:** A — Snapshot only. Prevents involuntary SSE-triggered data loss. Deliberate close is a conscious user action. localStorage adds complexity (invalidation, stale drafts) unwarranted for radio button + short notes.

**Rejected:**

- B because stale-draft invalidation logic and cleanup add implementation complexity for marginal gain when the form is just a radio + textarea

**Source inputs:**

- Data review (G1): SSE refetch nullifies selectedDR mid-edit
- UX review: flagged both SSE and deliberate-close loss, accepted snapshot as sufficient for V1

## D10 — 2026-05-17 — Host Header Validation

**Status quo:** No Host header validation on Cockpit backend. DNS rebinding theoretically possible.
**Decision to make:** Fix, defer, or accept?

**Options considered:**

- A: Bundle Host header middleware in P1
- B: Create separate security-hardening task
- C: Accept as risk — no action

**Chosen:** C — Acceptable risk for a laptop-local project. Not worth fixing.

**Rejected:**

- A because scope creep for a localhost-only tool
- B because even creating a task implies it needs fixing — it doesn't

**Source inputs:**

- Security review: flagged as pre-existing, recommended separate task
- User: "acceptable risk for a laptop-local project"

## D11 — 2026-05-17 — Mobile Layout

**Status quo:** Shell has responsive breakpoints but this is a laptop-resident tool.
**Decision to make:** Explicit mobile design or inherit patterns?

**Options considered:**

- A: Desktop-only design, no mobile spec
- B: Inherit current responsive patterns with testing
- C: Explicit mobile spec

**Chosen:** A — Desktop-only design. Mobile patterns are leftover over-compliance from earlier work. Don't need removal but don't need new investment.

**Rejected:**

- B/C because mobile is not a target for this tool

**Source inputs:**

- User: "desktop only design. any mobile patterns/spec are leftovers from overcompliance"

## D12 — 2026-05-17 — Timestamp Format

**Status quo:** DecisionViewport uses relative timestamps ("3h ago", "2d ago").
**Decision to make:** Keep relative or switch to absolute?

**Chosen:** Keep relative timestamps — already implemented, natural for a "pending items" list where age matters.

**Rejected:**

- Absolute dates because relative is more scannable for pending items

## D13 — 2026-05-17 — Critic Validation (O15)

**Critic pass:** Post-synthesis consistency review. 5 challenges received.

**Triaged:**

- Finding 1 (sidecar listed as open+closed): **minor** — stale synthesis text, no design change
- Finding 2 (cross-route modal undeclared): **material** — Brief must declare dual entry paths (nav-rail tab primary, status-bar indicator secondary)
- Finding 3 (desktop-only vs breakpoints): **material** — D11 clarified to mean "no new mobile design" not "ignore existing breakpoints"; implementation handles existing responsive behavior without regression
- Finding 4 (P1/P2 timing for sidecar removal): **material** — D8 timing moved to P2; P1 is purely additive
- Finding 5 (CockpitProvider framing): **minor** — rhetorical, no design change

**Changes applied:** D8 timing clarified (P2), Brief will declare dual entry paths, D11 intent clarified.

## D14 — 2026-05-17 — Critic Pass 2 + Process Decision

**Critic pass 2:** Result critic — challenges design's value delivery. 5 challenges received.

**Triaged:**

- Finding 1 (tab is lateral move): **material** — value proposition reframed: tab infrastructure is primary purpose, DR workspace is secondary. Honest framing in Brief.
- Finding 2 (pathfinder inflated): **minor** — P1 includes route-conditional sidecar (highest-risk work). Simple ≠ no value.
- Finding 3 (mandatory list not disciplined): **material** — see process decision below.
- Finding 4 (badge duplication): **minor** — standard UI pattern.
- Finding 5 (P1 has no user value): **minor** — applies consumer-product thinking to personal dev tool. Developer is the user.

**Process decision — Brief completeness model:**

The mandatory/recommended tier distinction is removed. The Brief defines the complete feature — everything listed is a requirement. The planner handles implementation sequencing (what depends on what), not scoping (what to include). If something shouldn't be built, it doesn't appear in the Brief.

Applied to this Brief: modal snapshot, Pydantic response model, and notes cap are all requirements. No "recommended" tier.
