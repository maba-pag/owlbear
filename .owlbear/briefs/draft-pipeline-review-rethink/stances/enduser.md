# End User Stance — Pipeline Review Rethink

## User Experience Stance

The pipeline's operator is someone who writes intent, watches agents execute, and intervenes when things go wrong. The proposal's locked outcomes are mechanically sound but under-specify the operator's experience at three critical moments: (1) before implementation begins, (2) when a reviewer returns findings, and (3) when a task starts spiraling. The design should optimize for these moments explicitly.

**Governing principle:** The user intervenes at *decision boundaries* (intent verification, scope changes, direction pivots) and delegates within boundaries (implementation, mechanical verification). Automation handles the predictable; the user handles the ambiguous.

## Usability Reasoning

### 1. Batching is generally better UX — with an escape valve

Batching all findings into one FAIL is the right default. Serial gating creates uncertainty anxiety: the user sees a FAIL, waits through a full pipeline cycle, sees another FAIL, and has no idea when it ends. Batching gives scope clarity in one read — the user can gauge "3 small fixes" vs. "fundamentally wrong approach."

However, "strictly better" is overclaimed. Path-dependent discovery means some issues only surface after earlier ones are fixed. And latency matters: if the first finding reveals the task is fundamentally misdirected, an early signal saves the user time rather than making them wait for a comprehensive 3x-cost pass that produces a long list of findings on wrong-direction code.

**Position:** Batch by default. But if the reviewer encounters a finding that invalidates the task's premise (not just a gap, but a contradiction), it should escalate immediately rather than completing the full pass. The user's time is the scarcest resource.

### 2. AC checkpoint before implementation is high-leverage

The most expensive failure mode in this pipeline is intent misinterpretation — the user writes intent, planner converts to AC, and nobody verifies the conversion until after implementation, testing, and review. Archive analysis shows this pattern drives the worst spirals (vague AC wording in 5/5 worst tasks).

With mandatory architect routing (Locked Outcome #1), the architect now reviews every task's AC. This creates a natural checkpoint: the architect-approved AC is the contract that drives all downstream work. The user should see this contract and have a moment to confirm "yes, this is what I meant" before expensive work begins.

This is not about trusting the architect's judgment — the checker-first architect flow may produce lightweight validations, not deep rewrites. The checkpoint value is the *user seeing what's about to be built.* Whether the architect rewrote heavily or rubber-stamped, the user's need is the same: verify the interpretation before sinking cost into it.

**Position:** After architect approval, surface the finalized AC to the user as a visible checkpoint. This doesn't mean blocking on user approval for every task — it means making the AC prominent in the task body so the user can spot-check before the builder starts. For high-stakes or complex tasks, the user should explicitly confirm.

### 3. Consolidation-test tasks: visible, automatic, overridable

The planner creating a consolidation-test task at the end of a feature chain should require zero user action. But it must be visible on the board — the user should see this commitment exists, not discover it (or its absence) after the fact.

The timing risk is real: "last implementation task" is fluid when proof-scope creep creates follow-up work. The user needs the ability to defer or retrigger this task. Planner creates it at best judgment; the user can override.

**Position:** Consolidation-test tasks appear on the board like any other task. Fully automatic creation, but the user can move, defer, or retrigger them. If the planner misjudges timing, the user corrects — this is a decision boundary.

### 4. Batch findings must distinguish blockers from improvement candidates

The Critic exposed the sharpest UX gap in the batching design: a "complete list" conflates true blockers with proof-scope creep. Archive analysis confirms the reviewer raises concerns not in any AC, consuming architect-override cycles. A long undifferentiated list creates false urgency — the operator thinks everything must be fixed now when some items are follow-up quality work.

**Position:** The reviewer's batched findings must categorize each item as **blocking** (AC not met, test unsound) vs. **follow-up** (improvement opportunity, proof depth enhancement). The user reads the blocking list to understand current-task scope; the follow-up list becomes input for future tasks, not current-task pressure.

### 5. Spiral detection needs proactive surfacing with category context

If a task has been through reviewer 3+ times, the user discovers this by watching — no proactive signal. An iteration counter is valuable as an attention trigger but lossy as a diagnostic. "3 cycles" means very different things when caused by AC ambiguity vs. proof-depth escalation vs. fixture weakness.

**Position:** Surface iteration count with a category hint (e.g., "Review 3 — proof depth" or "Review 4 — AC ambiguity"). Raw count triggers attention; category guides intervention. This doesn't require new infrastructure — the reviewer already knows why it's failing.

### 6. Observability: signals for decision boundaries, not dashboards

The user needs to see:
- **Task stage** — already available via kanban
- **What checker caught** — summary, not full evidence. Evidence tables are for intervention-time reading
- **Iteration history with category** — how many cycles, why
- **Spiral flags** — proactive alert when iteration threshold is crossed

The user does NOT need routinely: confidence scores, code-reader analysis, full evidence tables, per-check breakdowns. These are valuable when the user decides to intervene — they should be accessible, not surfaced by default.

**Position:** Minimal routine observability. Rich detail available on demand. The principle: surface signals that indicate *decision boundaries* (intent mismatch, scope change, spiraling); hide mechanical detail that represents *within-boundary* execution.

## Key Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| Batch by default | Scope clarity, fewer cycles | Latency increase per review pass; may miss path-dependent issues |
| AC checkpoint | Catches intent misinterpretation before expensive work | Adds a user attention cost per task (mitigated by spot-check model) |
| Blocker/follow-up distinction | Prevents false urgency from scope creep | Requires reviewer judgment on categorization (new cognitive work) |
| Minimal observability | Reduces operator cognitive load | Risk of opaque labels if surfaced signals are too compressed |
| Consolidation-test auto-creation | Zero user burden for test lifecycle | Timing may be wrong; requires user override capability |

## Warnings

1. **The batch findings categorization (blocker vs. follow-up) is load-bearing.** If this distinction isn't implemented, batching could make the operator experience *worse* — a long undifferentiated list is more overwhelming than serial discovery. This is not optional polish; it's a prerequisite for batching to deliver its UX promise.

2. **"Architect-approved" is not the same as "user-verified."** The proposal's checker-first architect flow may produce lightweight validations. The AC checkpoint only works if the user actually sees the AC in a prominent, scannable format — not buried in task body prose. Format matters as much as process.

3. **Spiral detection without category context creates false alarms.** A raw iteration count will cause the user to intervene on tasks where the reviewer is correctly deepening proof (legitimate cycles) and ignore tasks where the reviewer is chasing AC ambiguity (waste cycles). Category context is not a nice-to-have.

## Confidence

0.74 — The core positions (batching, AC checkpoint, blocker/follow-up distinction) are well-grounded in the archive analysis and research notes. Lower confidence on consolidation-test timing and observability granularity — these depend on implementation details not yet specified. The Critic forced material improvements to the batch-list design and the governing principle; the position is stronger for having been challenged.
