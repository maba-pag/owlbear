---
# >> Your action: set response to approved, needs-info, or rejected
response: approved
decision: "A: Amend AC to include panelist agent file updates"
notes: ""
# >> Agent metadata
task_id: 1148
agent: architect
created: 2026-04-27
urgency: blocking
decision_type: scope-decision
impact_tier: 2
---

# Decision: AC scope amendment — panelist agent file contract conflicts

## Context

Design direction for panelist agent ecosystem was architect-reviewed in #1147 and approved. M3.5 research (`.owlbear/research/1148-m3-5-proposal-round.md` Section 3.3) identified three contract conflicts between task AC and agent file definitions that require minor updates to existing agent files:

1. **Panelist output restriction gaps:** Agent files don't list `stances/{name}-proposal.md` in output paths, but propose mode generates them
2. **Propose-mode Critic behavior:** Propose mode has generative intent, but panelist agent files only define converge/denoise as Critic loop modes
3. **Pragmatist agent mode gap:** Pragmatist agent file only documents converge/denoise modes, but research proposes a mode=compare for cross-option ranking

Current AC explicitly marks "Panelist .agent.md changes" as out-of-scope. This amendment would:
- Add proposal output paths to 4 panelist agent files (panelist, challenger, ideation-critic, pragmatist)
- Document propose-mode Critic behavior in panelist agent files
- Add mode=compare documentation to pragmatist agent file

Scope is **surgical** — only updates to existing agent file docs and output restrictions, no new behavioral code.

## Options

### A: Amend AC to include panelist agent file updates — (rec:) recommended
- Effort: ~30 min (4 `.agent.md` files, 3 doc sections)
- Trade-off: Brief scope expands from design handoff to include agent-file contract harmonization
- Risk: Low — design is already locked; this is documentation alignment only
- Confidence: 0.92

### B: Keep AC unchanged; raise as post-delivery issue
- Effort: Zero now, but agent files ship with incomplete contracts
- Trade-off: Consumers of the agent ecosystem will have gaps in documented behavior
- Risk: High — panelist agent files will contradict actual behavior; output paths are live schema
- Confidence: 0.45

### C: Defer; research feasibility of contract-harmonization as separate task
- Effort: Add to backlog
- Trade-off: Unblocks current task; delays alignment
- Risk: Medium — panelist task stays on delivery track while agent files remain stale; post-delivery sync gets deferred
- Confidence: 0.50

## Recommendation

**0.92 confidence** — Approve option A. The design is architect-locked; this amendment is documentation and schema alignment only. Agent files are live contract definitions, and gaps here directly affect downstream panelist consumers. The effort is minimal (~30 min), and the risk of skipping it (option B) is publishing incomplete schema. Schedule this as part of task #1148 finalization.

## Impact of Deferral

Panelist task ships with agent files containing incomplete output restrictions and undocumented mode behaviors. Downstream consumers of the panelist agent ecosystem encounter:
- Missing `stances/{name}-proposal.md` in output restrictions (causes false validation gaps)
- Undocumented Critic loop behavior in propose mode
- Incomplete mode documentation in pragmatist agent

If rejected, return to #1147 for design re-review or reclassify task as architecture-review-only (design shipped, agent files untouched).
