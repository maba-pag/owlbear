# First-Principles Stance — DR Script Replacement

## Irreducible Core

Any solution to "human must authorize agent decisions" requires exactly three primitives:

1. **Signal** — agent communicates "I'm stuck, need human input" (with structured context)
2. **Store** — the request persists until the human responds (survives restarts, crashes)
3. **Effect** — the response propagates back to the blocked workflow (unblock + body write)

Everything beyond these three is accidental structure.

## Assumptions Challenged

### C1: "Scribe adds no value — it's purely mechanical"

**Verdict: Mostly true, but the framing hides the real cost.**

The scribe does two things: (a) filesystem I/O with YAML frontmatter, and (b) validation logic (duplicate detection, decision-field mismatch → needs-info reclassification). Both are deterministic. An LLM adds zero value here.

However, "purely mechanical" underplays the **validation gate** in resolve mode — the scribe checks that `decision:` matches an actual option heading and reclassifies to needs-info if not. This is the only non-trivial logic. If you move to engine functions, this validation must survive. It's currently an LLM interpreting "does this look like a meta-comment?" — which is judgment, not mechanism.

**What would falsify:** If the scribe ever exercises judgment beyond string-matching (interpreting ambiguous user notes, deciding which DR covers "the same concern"). Evidence: the skill says "covers the same concern" — that's fuzzy matching an LLM might do better than exact task_id lookup. But the implementation only matches on `task_id`, so it's already mechanical.

**Confidence: 0.85** — the claim holds. The one gray area (concern-matching) is already reduced to task_id equality.

### C2: "Calling agents can provide full DR body"

**Verdict: True but creates a coupling inversion.**

Currently the skill defines the DR format, and the scribe enforces it. Moving body generation to calling agents means every pipeline agent must know the DR schema. That's N agents coupling to a format vs. 1 intermediary coupling to it.

**Hidden assumption:** "The DR format is stable." If it changes (which this very brief proposes — dropping fields, adding timestamps), every calling agent's skill text must update simultaneously. With a scribe, only one skill updates.

**What would falsify:** If calling agents already produce the full body markdown today. Evidence: they don't — they pass `concern` (a string) and `request_type`, and the scribe generates the file. So the plan adds work to calling agents that didn't exist before.

**Mitigation the brief already implies:** A new skill replaces `w-decision-routing` and tells agents the format. Acceptable — the coupling moves from "runtime intermediary" to "build-time skill text." This is strictly better if the format is simple enough for a template.

**Confidence: 0.70** — true in principle, but the brief should explicitly address who generates the Options section, Context paragraph, and recommended-option markup. If agents must produce that, their prompts grow.

### C3: "pick_tasks should auto-resolve"

**Verdict: Questionable coupling.**

`pick_tasks` is a read-query ("what should I work on next?"). Adding resolve as a side-effect makes a read operation also a write operation. This violates CQS (Command-Query Separation) and means:

- You can't query available tasks without triggering state changes
- Testing requires accounting for mutation side-effects on every read
- The orchestrator can't introspect the board without altering it

**Alternative:** A separate `resolve_drs` function called explicitly before `pick_tasks`. Same ordering guarantee, no side-effect coupling. Cost: one extra function call per cycle. The brief already lists `resolve_drs` as an MCP tool — so the auto-resolve in `pick_tasks` is redundant with that tool.

**What would falsify:** If there's a hard requirement that resolution happens even when the orchestrator forgets. But the orchestrator skill already mandates "resolve before pick" — making it automatic is a safety net for a problem that shouldn't exist.

**Confidence: 0.75** — the side-effect coupling is real and unnecessary given `resolve_drs` already exists in the plan.

### C4: "Files should stay as persistence"

**Verdict: True and load-bearing, but needs justification beyond inertia.**

The irreducible reason files work: users can respond by editing a file in their editor without any running server. This is the "Cockpit is down" fallback. It also means `git diff` shows DR history.

**Hidden assumption:** "Users actually edit these files." Evidence from the resolved/ folder: 35 resolved DRs exist. The format includes `# >>` comment instructions, suggesting file-editing IS the primary interaction today. If Cockpit replaces it, the file format's user-friendliness stops mattering — it becomes a machine serialization format.

**Tension:** If files are just machine persistence, they could be JSON. The brief keeps YAML+markdown "because files stay" — but the *reason* for human-readable files (direct editing) is being deprecated by Cockpit. The brief should decide: are files for humans or machines?

**Confidence: 0.80** — files are the right persistence (git-trackable, no DB dependency), but the "simplified format" should simplify *for machines*, not humans, if Cockpit is the primary path.

### C5: "Cockpit is the natural user interaction path"

**Verdict: Assumed, not proven.**

The Cockpit exists for task board visualization. DR resolution is a different interaction pattern: read a question with context, pick an option, optionally write notes. This is closer to a PR review than a task board.

**What would falsify:** User data showing most DR responses are simple approvals (just set `response: approved`). If true, a Cockpit badge + one-click resolve is justified. But if most responses require writing notes or choosing between nuanced options with context… a full-page markdown file in the editor might actually be the better UX.

**Evidence gap:** No usage data presented. The 35 resolved DRs could be examined to see response patterns, but the brief doesn't.

**Confidence: 0.55** — plausible but ungrounded. The brief should audit resolved DRs to validate that most are simple approvals before committing to Cockpit as primary.

### C6: "The format should be simplified (drop urgency, decision_type, impact_tier, auto-resolve)"

**Verdict: Partially true, partially destroying useful signal.**

- `urgency`: Always "blocking" — dead field. **Drop: correct.**
- `decision_type`: Categorization that no consumer reads programmatically. **Drop: correct.**
- `impact_tier`: Controls auto-resolve behavior (T2 auto-resolves after 5 days, T3 never). **Drop: destroys the only timeout mechanism.**

If you drop `impact_tier` AND auto-resolve, every pending DR blocks forever until the user responds. Is that acceptable? The 5-day auto-resolve exists because users forget. Removing it means forgotten DRs permanently stall pipelines.

**What would falsify:** If no DR has ever actually been auto-resolved (all get human responses within 5 days). Check `resolve-summary.json` or resolved files for `response: auto-approved`. If zero exist, auto-resolve was dead code anyway.

**Confidence: 0.65** — dropping fields is correct for dead ones, but dropping the timeout mechanism needs evidence that it was never needed.

## Reframing Challenge

### Is the problem correctly framed?

The brief frames this as "scribe is mechanical, replace with code." But the deeper question is: **why do 35 DRs exist?**

If agents create DRs because they're uncertain, the fix might be:
- Better AC (fewer ambiguous situations)
- Higher agent confidence thresholds (decide more autonomously)
- Fewer T3 "must ask human" gates

Replacing the scribe optimizes the DR *transport* layer. But if the real problem is DR *volume*, the transport optimization is a local maximum.

### What if the real problem is the orchestrator cycle tax?

The brief's strongest motivation is "dispatch scribe every cycle." That's one LLM call per orchestrator loop doing nothing (0 pending DRs right now). The cheapest fix: **don't dispatch scribe when `pending/` is empty.** One `ls` check, zero LLM calls. The orchestrator skill could add a conditional.

That's a 5-line fix vs. a multi-package refactor. If the primary pain is latency/cost per cycle, the 5-line fix eliminates it.

## Summary

| Claim | Holds? | Risk if wrong |
|-------|--------|---------------|
| Scribe is mechanical | Yes | Low — validation gate must transfer |
| Agents provide full body | Partially | Medium — schema coupling to N agents |
| pick_tasks auto-resolve | Unnecessary | Low — but CQS violation is technical debt |
| Files as persistence | Yes | Low |
| Cockpit is natural path | Unproven | High — building UI for unvalidated assumption |
| Simplify format | Partially | Medium — timeout removal needs evidence |

**Overall confidence: 0.68** — the direction is sound but the brief has locked outcomes before validating two key assumptions: (1) Cockpit is actually better UX for DR resolution, and (2) auto-resolve/timeout is dead code.
