# End User Stance — Ideation System Overhaul

**Panelist:** End User (UX practitioner)
**Confidence:** 0.82
**Critic cycles completed:** 5

---

## User Experience Stance

The redesigned ideation system's conversation experience must serve one user: a technical maintainer who steers hard, remembers what they said, and resents having their words flattened or their decisions made for them. Every UX proposal below is calibrated to that user — not a hypothetical audience.

---

## 1. Fixed Question Format (O11) — Scales, Not Degrades

**Position:** O11 applies to every Mediator turn. No exemptions, no branching rule. The format *scales* naturally with the turn's content.

An M1 investigative probe with one framing is still the format: context (what the Mediator knows so far) → problem (what it needs to understand) → single proposal (its current read of the situation) → reasoning (why) → recommendation ("I think the problem is X — agree or reframe?"). The comparative structure is present — it's the Mediator's framing vs. the user's potential reframe.

A decision turn in M4 with three design options fills every slot. The format is the same; the density varies.

**Why no split:** The user rejected scoping O11 to decision turns: *"exact reason why we should avoid the critic in m1 and m2"* (D4). The Critic was over-engineering a distinction the user doesn't experience. The user's test: *"the chain has to be helpful — recommendations are not anchoring when the user actively steers."* The chain is always helpful because context before question reduces cognitive load, and a recommendation gives the user something to push against. Both apply equally to probes and decisions.

**Concrete UX rule:** The Mediator never asks a bare question. Every question has at minimum: (a) what it knows, (b) what it's asking about, (c) what it thinks, (d) why. The number of competing proposals is a function of the question, not a format mode.

**Risk:** Format fatigue if the Mediator pads simple questions with unnecessary context. Mitigation: the context section should be proportional — one sentence for a simple follow-up, a paragraph for a moment-boundary decision. Brevity within structure.

---

## 2. Idea Panel Placement (O6) — Synthesis-First, Walkthrough On Demand

**Position:** The three-voice idea panel (First-Principles, Simplifier, Outsider) output should be presented as **synthesis first, attributed voices on demand**.

**Presentation sequence:**
1. Pragmatist synthesis arrives first: 2-3 sentences covering convergences and flagged disagreements. This is the user's landscape view.
2. Mediator offers: "Three voices weighed in. [Synthesis]. Want me to walk through each position, or proceed with the synthesis?"
3. If the user wants detail: step through each panelist's position headline (pulled from their raw `stances/{name}.md`, not the Pragmatist's characterization) with the option to dig deeper into any one.
4. Full stance files remain available for direct reading.

**Why not dump all at once:** The user is already in a long session by end of M2. Three attributed positions plus synthesis is 4 content blocks — an attention overload event that contradicts the design principle (*"structure artifacts so re-reading is cheap"*). The M5 walkthrough pattern already proves that chunk-and-choose works for this user.

**The "fix M1 based on panel finding" flow:** Panel surfaces a gap → Mediator presents gap with full attribution (which panelist, what they said, why) → Mediator asks: "This challenges your M1 problem statement. Reopen M1 to address it, or note it and proceed?" → User decides. Reopening M1 means the specific finding becomes context for the re-entry, not a redo from scratch.

**Follow-up on individual voices:** The user can ask "what did First-Principles actually say?" and get the raw position — not the Pragmatist's version. This is the transparency O13 demands.

---

## 3. Drift Visibility (O14) — Structured Self-Report

**Position:** When the Mediator changes direction within a moment, it issues an explicit structured admission in the conversation flow:

> "I changed direction. Previously: [heading toward X because reason]. Now: [heading toward Y because new input/realization]. This is shift #N this moment."

**Three components, all mandatory:**
- **Previous direction** — what the user thought was happening.
- **New direction + reason** — what changed and why.
- **Shift counter** — cumulative within the current moment. A moment with 4 shifts is a quality signal the user should notice.

**What it's not:** Not a diff (too technical, breaks flow). Not a counter alone (insufficient — *what* shifted matters more than *how often*). Not auto-corrected (the user explicitly rejected that: *"made visible to the user (not auto-corrected)"*).

**Working log integration:** Each drift marker is captured in the log as a distinct entry — tagged so the M5 walkthrough can flag moments with high drift counts. The walkthrough can then ask: "M2 had 3 direction shifts. Want to review whether the final direction is coherent?"

---

## 4. Filter Agent Transparency (O13) — Dual-View: Raw Headlines + Filtered Synthesis

**Position:** When a filter agent is applied, the user gets two independent views:

1. **Per-source headline** — one sentence per subagent, pulled directly from the subagent's own output (e.g., the first line of each `stances/{name}.md`). Not the Pragmatist's characterization. Not the Mediator's summary. The subagent's own words.
2. **Synthesis** — the filter agent's consolidated output (convergences, disagreements, recommendations).

The Mediator presents both: headlines first (gives the user the audit trail), then synthesis (gives the user the actionable summary).

**Why dual-view:** If the user sees a headline that doesn't map to anything in the synthesis, that's the signal something was dropped or flattened. They can then pull the full raw file. This preserves agency without drowning the user in raw output — the headlines are a scan-level check, not a full read.

**The naming rule:** The Mediator always names the filter agent: "Pragmatist synthesized 4 panelist positions" — never "here's what the panel thinks" (which hides the filtering layer). The user should always know when they're reading filtered output.

**Risk acknowledged:** Headlines can themselves be misleading if the panelist's summary line is poor. Mitigation: panelist stance files already have a structured format with a clear position statement at the top. This is a convention, not a new mechanism.

---

## 5. Walkthrough Preservation — Survives, Adapts Source

**Position:** The M5 walkthrough protocol (5 chunks, 6-slot commentary, fidelity/readiness/risk metrics) is the most mature UX pattern in the system. It survives intact.

**Adaptation needed:** The source of truth shifts from multi-file blackboard to working log. The walkthrough should reference specific log sections: "Turn 14: you decided X — this maps to Brief §Y. Fidelity check: does the Brief accurately reflect your decision?"

**The 6-slot commentary and metrics don't change.** They work because they give the user a structured framework to evaluate each chunk. The framework is independent of where the source data lives.

**New capability from the log:** The working log enables a richer fidelity check because every user decision is captured with its rejected alternatives and rationale. The walkthrough can flag: "Brief §Y reflects your decision from Turn 14. You rejected Z because [reason]. The Brief doesn't mention Z — is that intentional or an omission?"

---

## 6. Critic-Listening Discipline (D4) — Structural Enablement, Not Prevention

**Position:** No system design can prevent an LLM from being cognitively anchored by what it reads. The system should make anchoring *visible and auditable*, not pretend to prevent it.

**Structural mechanisms (layered):**

1. **Per-point presentation (O11).** Each Critic finding gets its own O11 question. No bulk "the Critic raised 5 points, here's what I recommend" — that's the adoption anti-pattern. Each point: context (what Critic said) → problem (what this challenges) → options (accept / reject / modify) → reasoning for each → recommendation. The "reject" option must have genuine reasoning, not a vestigial "or don't."

2. **Working log audit trail (O2).** The log captures what the Critic said verbatim alongside the Mediator's presented question. The user (or a future M5 walkthrough) can compare and spot silent adoption.

3. **D4 as system instruction.** The rule *"bulk adoption of Critic recommendations is the same anti-pattern as ignoring Critic"* is embedded in the Mediator's instructions. It fires at the moment the Mediator processes Critic output — before the question is formed.

4. **User as the actual check.** The user said it themselves: *"we earlier listened to the critic and followed its advice and that's WHY we landed on our face in M5, not because we skipped it. we listened too much."* This user catches adoption. The system's job is to make catching easy.

**Honest limit:** The Mediator will be influenced by what it reads. Anchoring is reduced, not eliminated. The design makes the user's detection job trivial (per-point questions, working log, raw Critic output available). Perfect prevention would require not showing the Mediator the Critic output at all — which defeats the purpose.

---

## 7. Long-Session Fatigue — The Log Is the Relief Valve

**Position:** The working log (O2) is the primary fatigue mitigation. It externalizes memory so the user doesn't have to carry context from 2 hours ago in their head.

**Three fatigue-reduction mechanisms:**

1. **Progress markers.** Simple, persistent: "M2 locked. 3 of 6 moments complete. Next: M3 Landscape." The user always knows where they are. No need to ask "wait, what moment are we in?"

2. **The log as external memory.** The Mediator references prior decisions by section: "Per your M1 decision (Turn 8), we established X. Does that still hold?" The user can verify without re-reading the whole log. The Mediator doesn't rely on the user remembering — it cites.

3. **Graceful pause/resume.** The log is the resumption artifact. A new session starts by reading the log and presenting a status summary: "Here's where we left off. M1-M2 locked. M3 landscape in progress. Last active question: [X]." No separate session-state file.

**Log growth management:** The log needs consistent section headers — `## Turn N — [Moment] — [Topic]` — for scan-friendly navigation. Not a table of contents (user rejected manifests) but enough structure for grep. The Mediator reads selectively: current moment's section fully, prior decisions by reference. Not the whole log every turn.

**Single file > multiple files** for a technical user with search tools. One file to `⌘F` vs. figuring out which of 6 files has the decision you remember making but can't locate. The user's own words: *"the failure mode is lost navigation / stale files, NOT lack of granularity"* — single file with structure solves both.

---

## Key Trade-offs

| Trade-off | Position | Risk accepted |
|-----------|----------|---------------|
| O11 everywhere vs. format fatigue | Everywhere, with proportional brevity | Some turns will feel over-structured for simple follow-ups |
| Panel dump vs. synthesis-first | Synthesis-first with walkthrough offer | User might always skip to synthesis and miss important dissent |
| Drift self-report vs. automatic correction | Self-report with counter | Mediator may fail to notice its own drift (detection depends on self-awareness) |
| Filter transparency vs. attention load | Dual-view (headlines + synthesis) | Headlines add ~3-5 lines per filtered event |
| Critic adoption prevention vs. detection | Detection (audit trail + per-point questions) | Cannot prevent anchoring, only make it visible |
| Log length vs. navigability | Structured headers, selective reading | Log becomes long; user must trust search over scroll |

---

## Warnings

1. **Drift self-report depends on Mediator self-awareness.** An LLM that drifts may not realize it drifted. The shift counter is only as good as the Mediator's ability to detect its own direction changes. Consider: should the working log itself make drift detectable by a downstream reviewer (M5 walkthrough), even if the Mediator missed it in-moment?

2. **O11 universality will be tested hardest in M1.** The first 3-4 turns of a new ideation session are the most exploratory and least structured. If the Mediator over-formats these turns (long context blocks for a simple "what's on your mind?"), the user will experience the format as friction, not support. Proportional brevity is the discipline.

3. **The idea panel is a new attention event at a vulnerable moment.** End of M2 means the user has already done problem definition + outcome negotiation (potentially with multiple revisions, as in this session). Introducing 3 new voices at that point is a fatigue risk. The synthesis-first pattern mitigates but doesn't eliminate — the user still needs to engage with panel findings before M3.

4. **Filter agent dual-view relies on panelist output having good summary lines.** If a panelist buries their key insight in paragraph 3 instead of their opening line, the headline will be misleading. This is a convention dependency, not a structural guarantee.
