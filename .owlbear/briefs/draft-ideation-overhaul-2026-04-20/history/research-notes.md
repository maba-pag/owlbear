# Research Notes — Ideation Overhaul M3 Landscape

## Source files read directly by Mediator (raw evidence)

### Current ideation system files
- `share/agents/ideator.agent.md` — Mediator agent (mode instructions, ~120 lines)
- `share/skills/w-ideation/SKILL.md` — Canonical 6-moment workflow (~600 lines)
- `share/skills/h-ideation-panel/SKILL.md` — Panel handbook (~300 lines)
- `share/agents/ideation-critic.agent.md` — Adversarial critic (read-only, GPT-5.4)
- `share/agents/ideation-pragmatist.agent.md` — Neutral synthesizer
- `share/agents/ideation-architect.agent.md`, `ideation-data.agent.md`, `ideation-enduser.agent.md`, `ideation-security.agent.md` — Domain panelists (~60 lines each, all use Claude Opus 4.7, all hooked via `allow-stances-only.py`)
- `share/instructions/agent-common.instructions.md` — applyTo `share/agents/**` (~70 lines, pipeline-only content irrelevant to ideator)

## Critical findings about current system

### F1 — Contradiction in ideator.agent.md
Lines 21–35 of `ideator.agent.md` simultaneously state:
- "Transparent by default. At every decision point... narrate what you are doing and why."
- "Single user-facing voice throughout. Never expose internal deliberation. Summarize; never relay raw panelist output."

These are not separable behaviors — "transparent about decision-making" and "never expose internal deliberation" actively conflict when subagent feedback shapes a Mediator decision. This is the structural opacity Critic identified.

### F2 — agent-common.instructions.md is dead weight for ideator
File applies to all `share/agents/**` but content is Channel B + kanban verdict tokens + per-agent section mapping for **pipeline agents only**. The ideator never uses Channel B (it writes to `.owlbear/briefs/`, not kanban task bodies). ~70 lines auto-loaded into ideator context with zero relevance.

### F3 — Critic compression to M4/M5 is cosmetic
Each domain panelist has its own embedded Critic loop (≤5 cycles per panelist) per `h-ideation-panel/SKILL.md`. With 4 panelists, that's up to 20 Critic invocations *inside* deliberation, plus 4 standalone Mediator Critic invocations (M1/M2/M4/M5). Compressing standalone Critic to M4/M5 only reduces 4→2 — saves ~2 invocations out of ~22. Negligible.

**Implication for V4:** O14 (within-moment drift visibility) is the real Critic outcome. The "Critic compresses to M4/M5" framing in V4 should be deleted or restated.

### F4 — Hooks are already part of the architecture
`allow-stances-only.py` (PreToolUse hook on all panelists), `deny-writes.py` (on Critic). These are file-write safety hooks, not behavioral hooks.

**Implication for V4 / O9 design principle:** "No hooks" was overbroad. Sharp version: *no new compliance hooks layered on Mediator behavior*. Existing safety hooks stay. This distinction matters for M4 design.

### F5 — Each panelist's Critic loop produces a debate log
Per panelist: `stances/{name}.md` (final position) + `stances/{name}-debate.md` (full Critic dialogue). This is precedent for "raw debate captured to file, only synthesis surfaces to Mediator." Reusable for the new idea panel (O6).

## Sizing the attention-budget leak

Mediator auto-loaded context (before user input or any reads):
- `ideator.agent.md` mode instructions: ~120 lines
- 5 auto-loaded `.instructions.md` files (agent-common, owlbear-system, frontend, python, agents-and-skills, research-docs): ~400+ lines combined, mostly irrelevant to ideator
- User memory (auto-loaded first 200 lines)
- Workspace info, instruction stubs, tool descriptions

Plus on-demand: `w-ideation/SKILL.md` (~600), `h-ideation-panel/SKILL.md` (~300), `h-agent-structure/SKILL.md`.

**Estimated baseline static load: 2000+ lines before user input.** This is the attention-budget leak the design principle targets.

## Prior art for outcomes

### O2 — Single append-only working log
- `serve/kanban/src/owlbear_kanban/activity_log.py` — single-function append-only JSONL, ~30 LOC. Closest structural precedent.
- `serve/orchestrator/src/owlbear/audit/log.py` — `AuditLog` class, append-only JSONL.
- `serve/orchestrator/src/owlbear_orchestrator/error_journal.py` — `ErrorJournal` with bounded rotation.
- `.owlbear/research/jsonl-store-base-class.md` — DRY proposal for `JsonlStore[T]` Pydantic base.
- `.owlbear/research/wip-continuity-store.md` — append-only vs latest-wins comparison.

**All existing patterns are JSONL (machine-event).** O2 is markdown narrative — must design schema from scratch. KISS implies plain markdown with date-stamped sections, not JsonlStore complexity (which would re-introduce the "register for the olympic games" pattern user rejected).

### O13 — Selective filter/synthesizer agents
- `share/agents/ideation-pragmatist.agent.md` — canonical (consume all stances → one synthesis).
- `share/agents/memory-curator.agent.md` + `share/skills/w-mem-curation/SKILL.md` — production "consume verbose stream → emit condensed artifact."
- `share/agents/test-curator.agent.md` — post-pipeline test-suite consolidator.
- `share/agents/code-reader.agent.md` — produces 8-section structured report consumed by reviewer (different shape: structured-for-another-agent, not condensed).
- `share/agents/scribe.agent.md` — anti-pattern reference: explicit verbatim transcriber, forbidden from summarizing.

### O6 — Idea panel agents
- Panelist agent template (~60 lines) is well-established across the 4 existing domain agents.
- `h-ideation-panel/SKILL.md` documents Stance Reasoning Cycle, parallel batch, sequential deep-dive.
- Insertion-point precedent: `.owlbear/research/997-skill-preflight-ideation-m1.md` shows how to insert a new step into an existing moment.
- Model assignment precedent: domain panelists use Claude Opus 4.7; Critic uses GPT-5.4 (model diversity rationale documented in `.owlbear/research/critic-voice-agent.md`).

### Decision-record patterns (relevant context, not for reuse)
- `.owlbear/decisions/` DR system — agent↔user decision protocol (not relevant to ideation working log).
- Per-brief Working Directory `decisions.md` — current pattern, being replaced by O2.

## Panel-related research findings
- `.owlbear/research/council-debate-system.md` and `council-protocol-c-validation.md` — parallel-then-synthesize "Protocol C" with moderator agent and structured Pydantic output. Useful pattern reference for O6 + O13.
- `.owlbear/research/challenger-subagent-design.md` and `challenger-arch-review-integration.md` — adversarial pre-decision subagent pattern (not a synthesizer; relevant for O6 panel structure).

## Implications for M4 design

1. **Strip ideator's auto-loaded instruction surface** — at minimum, remove `agent-common.instructions.md` from ideator's applyTo scope; consider similar stripping for other inapplicable instructions.
2. **Resolve transparency-vs-opacity contradiction in ideator.agent.md** — pick one (transparency wins given V4 outcomes).
3. **Drop "Critic compresses to M4/M5" claim from V4** — it's cosmetic. Keep O14 (within-moment drift visibility) as the real Critic-related outcome.
4. **O9 design principle wording** — distinguish "no new compliance hooks on Mediator behavior" from "existing safety hooks stay."
5. **O2 schema** — plain markdown with date-stamped per-turn sections; no JSONL/JsonlStore; user explicitly rejected formal-registry patterns.
6. **O6 implementation path** — three new agent files following the `share/agents/ideation-{name}.agent.md` template; insertion at end of M2 per `997-skill-preflight-ideation-m1.md` precedent; model assignment to be decided (mixed-model adds diversity but increases tooling complexity).
7. **O13 implementation path** — filter agents follow `ideation-pragmatist` template; per-subagent application rules need to be designed.
