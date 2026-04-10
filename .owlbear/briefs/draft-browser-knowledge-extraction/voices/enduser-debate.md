# End-User Voice — Critic Debate Log

## Cycle 1

**My position**: Six-point UX stance covering onboarding (propose-confirm, max 2 questions), page review (categorized summaries), browser (one-time setup + auto-detect), progress (batch every 5–10 pages), attribution (enriched metadata), error recovery (non-blocking, per-page retry).

**Critic challenges**:
1. *Critical*: Position 1 hard-codes low friction where the brief requires user judgment. "Max 2 questions" compresses scope, cadence, boundary, and source-type decisions into one step.
2. *Moderate*: Position 2 makes review too lossy — category-level exclusion loses per-page signal.
3. *Moderate*: Position 3 mislabels CDP as "one-time setup" — it's a live session dependency.
4. *Moderate*: Position 4 — batch updates still leave long silence gaps at CDP speed.
5. *Moderate*: Position 5 — attribution is decorative rather than semantic; POLICY and meeting-note results would feel equally authoritative.
6. *Moderate*: Position 6 — "45/47 indexed" presents dynamic page set as fixed denominator.
7. *Moderate*: Position 6 — page-level retry is wrong granularity when failures are source-level (auth expiry).
8. *Blind spots*: No source removal UX, no one-off vs. monitored distinction, source-type differences flattened.

**My response**:
- **Accepted #1**: Expanded proposal to cover scope, cadence, domain boundaries as separate dimensions. Kept propose-confirm pattern but dropped "max 2 questions" constraint.
- **Accepted #3**: Reframed from "one-time setup" to "session-aware, live dependency."
- **Accepted #5**: Added knowledge-type influence on presentation weight.
- **Accepted #6, #7**: Added dynamic denominators and source-level diagnosis.
- **Accepted all blind spots**: Added source removal flow, explicit one-off vs. monitored modes, source-type-appropriate discovery.
- **Partially accepted #2**: Added sample titles per category, not just counts. File approach kept for large sets.
- **Partially accepted #4**: Switched to time-based minimum updates (every 30s) alongside batch counts.

## Cycle 2

**My position**: Refined six-point stance with structured propose-confirm (separate dimensions), tiered page review (summary → category → full list), session-aware browser framing, time-based heartbeat progress, authority-weighted attribution, source-level error diagnosis.

**Critic challenges**:
1. *Moderate*: Onboarding still concentrates too many low-confidence decisions before the user sees value.
2. *Moderate*: Category review plus optional file editing still too lossy for real review.
3. *Moderate*: "Does this scope look right?" with specifics is still weak evidence for usefulness.
4. *Moderate*: Chat overloaded as review surface, status console, fault console, and control plane simultaneously.
5. *Moderate*: File-based review introduces fragile mode switch from chat to manual editing.
6. *Moderate*: Lifecycle ambiguous between one-off and monitored paths.
7. *Moderate*: Authority-weighted presentation risks authority amplification from imperfect classification.
8. *Blind spots*: Source overlap detection absent, session interruption recovery absent, post-onboarding boundary visibility absent, removal graph impact unclear.

**My response**:
- **Accepted #4**: Separated concerns — milestones to chat, detail to log file. Chat is NOT a status console.
- **Accepted #6**: Made two-mode lifecycle explicit: "extract once" vs. "register source."
- **Accepted blind spots**: Added overlap detection, session interruption state file, boundaries in status.
- **Partially accepted #1**: Added "value before commitment" — sample extraction before scope decisions.
- **Partially accepted #2/#3**: Added representative titles in categories, honest acknowledgment of limits at scale.
- **Partially accepted #5**: File mode switch is real but best available in VS Code.
- **Partially accepted #7**: Knowledge type shown as metadata tag, not visual hierarchy.

## Cycle 3

**My position**: Two explicit lifecycle modes (managed/unmanaged), structured proposal from discovery metadata with sample extraction for value, tiered review with file for scale, session-aware browser with resumable state, milestones-to-chat + detail-to-log progress separation, provenance-not-authority attribution, source-level error diagnosis with MCP tool for status.

**Critic challenges**:
1. *Critical*: One-off path creates hidden lifecycle state — ingested content with no source object but Position 5 says every result carries source registration name.
2. *Critical*: "Value before commitment" extracts 2–3 sample pages before scope consent.
3. *Moderate*: Review still too lossy at scale (hundreds of pages).
4. *Critical*: Per-page chat updates reintroduce the noise problem.
5. *Moderate*: Source health dashboard is conceptual, not an interaction surface.
6. *Blind spots*: Refresh-time discovery governance absent, non-page assets absent, search-time trust calibration for managed vs. unmanaged absent.

**My response**:
- **Accepted #1**: Added "unmanaged" provenance tag for one-off extracts. Separate attribution fields for managed vs. unmanaged. Added inventory command spanning both.
- **Partially rejected #2**: User gave us the URL — previewing navigation/index pages is not a consent violation. Scoped sample to metadata-level discovery, not deep content extraction before consent. For unclear titles, offer sample extraction AFTER user confirms small initial scope.
- **Partially accepted #3**: Honest about limitation. For 200+ pages, user is making a scope decision, not per-page review. Agent says so explicitly.
- **Accepted #4**: Reverted to milestone-based chat updates (~25% or ~2 min), not per-page.
- **Accepted #5**: Source status surfaces via MCP tool call, not conceptual dashboard. Framed as pull-based (chat constraint).
- **Accepted blind spots**: Added refresh-time governance (auto-include within boundary, report all changes). Acknowledged non-page assets as future concern.

## Cycle 4

**My position**: Hardened seven-point stance with resolved lifecycle model, metadata-only discovery, honest scale acknowledgments, chat/log separation, pull-based status, refresh governance.

**Critic challenges**:
1. *Moderate*: Early lifecycle choice still carries too much weight — no natural promotion from unmanaged to managed.
2. *Critical*: "Metadata is enough to ground decisions" is the weakest assumption — titles are poor value proxies on corporate sites.
3. *Moderate*: File-based review for large sets externalizes the UX problem into hidden state.
4. *Moderate*: Source status tool is data access, not a user-facing surface discoverable in chat.
5. *Critical*: Refresh-time auto-inclusion has unstable automation boundary — "within boundary" and "new section" are system concepts, not reliably user concepts.
6. *Blind spots*: No inventory experience, no source naming model, no notification/interrupt semantics.

**My response**:
- **Accepted #1 (partial)**: Added promotion path — unmanaged extracts from same domain can be promoted to managed source. Reduces weight of early decision.
- **Partially rejected #2**: The alternative (extract before consent) was challenged in cycle 3. Metadata IS imperfect but is least-bad. Added sample extraction after initial scope confirmation for unclear titles.
- **Partially accepted #3**: Fundamental chat constraint. Acknowledged honestly. Agent tracks which surface is current.
- **Accepted #4**: Honest framing — in chat, status is pull-based. Agent proactively surfaces issues at next interaction.
- **Partially accepted #5**: Auto-inclusions are always reported at next interaction. Never silent. User can review.
- **Accepted blind spots**: Added inventory command, proactive surfacing of refresh events.

## Final Assessment

**Cycles completed**: 4
**What changed**: Major structural shifts in cycles 1–3 (lifecycle modes, consent ordering, progress separation, status surface). Cycle 4 refinements were incremental (promotion path, notification model).
**What I held**: Propose-confirm onboarding pattern (refined but maintained). Metadata-based scope decisions as least-bad option. File-based large-set review as best available in VS Code. Knowledge type as metadata tag not authority signal. Chat as primary but not sole surface (log files for detail).
**Key tension acknowledged but unresolved**: Chat interface is the binding constraint. Most remaining Critic challenges trace to the limitations of Copilot Chat as the only interaction surface.
