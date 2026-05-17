# End User Debate Log — Cockpit Decisions Tab

## Critic Cycle 1

### Challenges Received

1. **Positions 1 & 2 undercut locked V1 scope (critical).** Draft argued for inline detail as future fix, but P2 outcomes explicitly include full body + resolution controls. The stance was retreating to current pattern rather than evaluating the locked design.

2. **Position 6 & 7 contradict task-centered workflow (critical).** Removing sidecar DRs breaks the existing flow where task cards surface "Decision pending" and the sidecar provides immediate action. DRs arise inside kanban work, not outside it. The "separate workspace" framing ignores this.

3. **Position 2 overstates modal as action-forcing (moderate).** ResolveModal already supports read-and-leave: submit requires explicit selection, cancel/escape/dismiss close without mutation. "Resolve-or-dismiss binary" was inaccurate.

4. **Position 3 treats zero as noise without addressing current system (moderate).** Existing DRStatusIndicator always renders and announces count even at zero. No evidence that nav-rail badge should erase zero while status bar keeps it.

5. **Position 4 invents hybrid timestamp rule breaking consistency (moderate).** Cockpit already uses elapsed-time labels everywhere. Mixed relative/absolute model was unjustified.

6. **Position 1 assumes inline body is "free" without evidence (moderate).** Backend emits 200-char preview; full-body surface is the modal. Specific 400+ char and inline-body prescriptions were unsupported.

### Blind Spots Surfaced

- Stance barely engaged the pathfinder infrastructure purpose
- Kanban-to-Decisions handoff gap: task cards say "Decision pending" but cross-nav sender is out of scope
- Notification surfaces treated as independent questions when they're actually a linked chain

### Revisions Made

- **Position 1:** Removed inline-body prescription. Refocused on generous item rendering within the 200-char preview constraint. List's job is triage; modal's job is reading.
- **Position 2:** Dropped "problematic binary" framing. Acknowledged modal supports read-and-leave. Reframed trade-off as spatial context loss, not forced resolution.
- **Position 4:** Dropped hybrid timestamp model. Adopted relative-only with recommendation to standardize granularity across surfaces.
- **Position 6:** Reversed from "stop showing DRs" to "retain minimal DR presence in sidecar on kanban view." Acknowledged the notification chain.
- **Position 7:** Added cross-linking language and acknowledged that DRs arise inside kanban work.
- **New Position 8:** Added pathfinder acknowledgment but framed it as requiring genuine UX improvement, not just routing validation.

## Critic Cycle 2

### Challenges Received

1. **Modal state loss on close (critical).** Closing the modal discards in-progress response and notes (local state lost on unmount). "Close and reopen quickly" understated the real cost — draft work is destroyed.

2. **Loss of concurrent task context (critical).** Current sidecar shows DR list alongside task Detail and Activity. Tab+modal removes this concurrent access. Framing modal trade-off as only "DR-to-DR comparison loss" was too narrow — the larger regression is losing blocked-task context during resolution.

3. **Position 6 overstates "dead end" (moderate).** Sidecar is already collapsible; status-bar indicator provides alternative path. "Removing any link creates a dead end" was stronger than product constraints support.

4. **Timestamp inconsistency baseline (moderate).** Existing surfaces already disagree (DecisionViewport: minutes/hours/days; DRStatusIndicator: hours only). Claiming "maintain consistency" when no consistency exists was inaccurate.

5. **Badge distinction asserted not demonstrated (moderate).** Current DRStatusIndicator is also count-bearing and interactive, weakening the argument that the two surfaces naturally justify different zero-state conventions.

6. **Pathfinder rationale doing too much argumentative work (critical).** Leaning on infrastructure validation to justify low UX ambition undershoots the stated user problem (decisions are secondary, embedded in small widgets, lacking dedicated workspace).

### Blind Spots Surfaced

- Mobile viewport behavior absent from all positions
- Live queue mutation via SSE not considered (DR list can change during interaction)
- Positions assume present shell capability that doesn't exist yet (one button, one route)

### Revisions Made

- **Position 2:** Added explicit warning about modal state loss as the primary V1 UX cost. Added secondary trade-off about losing concurrent task context.
- **Position 3:** Maintained position but acknowledged the tension with DRStatusIndicator explicitly.
- **Position 4:** Acknowledged the existing inconsistency and reframed as opportunity to standardize.
- **Position 6:** Softened from "dead end" to "degradation." Acknowledged sidecar collapsibility and status-bar alternative.
- **Position 8:** Reversed from "consistency over innovation" to "must genuinely improve decision handling." Set bar: user should prefer tab over sidecar.
- **Warnings:** Added live queue mutation, mobile viewport, and sidecar gap as explicit warnings.
