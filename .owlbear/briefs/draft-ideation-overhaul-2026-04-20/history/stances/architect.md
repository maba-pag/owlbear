# Architectural Stance — Ideation System Overhaul

**Panelist:** Architect
**Critic cycles:** 5 (see `stances/architect-debate.md`)
**Confidence:** 0.82

---

## Architectural Stance

The overhaul is a **consolidation**, not an expansion. The current system's failures stem from instruction scatter and artifact fragmentation. Every design decision below reduces file count, narrows read scopes, and keeps authority in fewer places. Where the current system has 6+ files competing for the Mediator's attention budget, the target has 2 authoritative sources: `ideator.agent.md` (identity + subagent roster) and `w-ideation/SKILL.md` (everything else).

---

## 1. Working Log Schema (O2)

### Design

A single `working-log.md` replaces both `context.md` and `decisions.md` in the Working Directory. Pure append-only — no edits to earlier content.

#### Per-Turn Section Format

```markdown
### Turn {n} — M{x} — {type}

{content}
```

**Turn types:** `user-input`, `mediator-proposal`, `subagent-result`, `user-decision`, `critic-challenge`, `drift-check`

**Content rules by type:**
- `user-input` — verbatim, no paraphrase (O1)
- `mediator-proposal` — uses the fixed O11 format (context/problem/proposals/pro-con-risk-confidence/recommendation)
- `user-decision` — chosen option + each rejected option with rationale (replaces decisions.md)
- `subagent-result` — source attribution + summary (for domain panel, this is the pragmatist synthesis reference; for idea panel, the challenge summaries)
- `critic-challenge` — standalone Critic findings at moment boundaries
- `drift-check` — moment + turn count + current focus + exit criteria remaining (O14)

#### Moment-Boundary Checkpoints

At the end of each moment, the Mediator appends a checkpoint — a self-contained state snapshot:

```markdown
---
## Checkpoint — End of M{x}

**Problem:** {curated statement}
**Tier:** {tier}
**Outcomes:** {numbered list — present from M2 onward}
**Landscape:** {summary — present from M3 onward}
**Key Decisions:** {numbered list — present from M4 onward}
---
```

Checkpoints are **appended** (not edited), so the append-only contract holds. Each checkpoint supersedes the previous one. Panelists and subagents read the **latest checkpoint** as their entry context — equivalent to reading the old `context.md` + `decisions.md` but from one file, one location.

**Estimated checkpoint size:** ~80-120 lines by M4 — comparable to today's `context.md` + `decisions.md` combined.

#### What the Working Log Does NOT Replace

| File | Stays | Reason |
|------|-------|--------|
| `stances/*.md` | Yes | Different ownership (panelists write, Mediator/pragmatist read) |
| `synthesis.md` | Yes | Pragmatist output for domain panel |
| `research-notes.md` | Yes | Explore subagent output |
| `brief.md` | Yes | Final deliverable |
| `input/*` | Yes | User reference materials |

#### Revised Working Directory Layout

```
.owlbear/briefs/draft-{name}/
  input/                  ← User reference materials
  working-log.md          ← Append-only conversation record (replaces context.md + decisions.md)
  research-notes.md       ← Explore subagent findings
  stances/
    first-principles.md   ← Idea-panel stances (NEW — O6)
    simplifier.md
    outsider.md
    architect.md           ← Domain-panel stances (existing)
    data.md
    enduser.md
    security.md
    *-debate.md            ← Critic debate logs for each
  synthesis.md            ← Pragmatist synthesis of domain panel
  brief.md                ← Final Brief
```

**Net file change:** `context.md` + `decisions.md` → `working-log.md`. Two files become one.

---

## 2. Mediator Instruction-Surface Reduction

### F2 — Kill Dead Instruction Load

**Change:** Modify `share/instructions/agent-common.instructions.md` line 3:

```yaml
# Current
applyTo: "share/agents/**"

# Target
applyTo: "share/agents/!(ideation*|ideator*).agent.md"
```

If VS Code glob negation isn't supported, the fallback is an explicit list of pipeline agent filenames. Either way, the result is: `agent-common.instructions.md` no longer loads into any ideation agent context. **~70 lines of pipeline-only content removed from every ideation session.**

Verify: All 7 ideation agents (`ideator`, `ideation-critic`, `ideation-pragmatist`, `ideation-architect`, `ideation-data`, `ideation-enduser`, `ideation-security`) plus the 3 new idea-panel agents must be excluded.

### F1 — Resolve Transparency Contradiction

**Change:** In `share/agents/ideator.agent.md`, the persona section contains two conflicting directives:
- "Transparent by default. At every decision point... narrate what you are doing and why."
- "Single user-facing voice throughout. Never expose internal deliberation."

**Resolution:** Delete the opacity directive. Replace with:

> Single user-facing voice throughout. When surfacing panelist findings, attribute positions to panelists by name (e.g., "[Architect] warns...") but present them in your own narrative voice — don't relay raw panelist text.

This preserves the "one voice" UX while honoring O11's attribution requirement. The Mediator speaks coherently but doesn't hide who said what.

### W-ideation Self-Containment

**Change:** Inline the Mediator-relevant subset of `h-ideation-panel` into `w-ideation/SKILL.md`:
- Panelist selection matrix (already partially duplicated — canonicalize in w-ideation)
- Parallel vs. sequential invocation decision
- Pragmatist invocation trigger ("after all domain panelists complete")

**What stays in `h-ideation-panel`:** The Critic-loop protocol, stance reasoning cycle, max rounds, exit conditions — these are panelist-facing rules that the Mediator doesn't need. Panelists read `h-ideation-panel`; the Mediator reads only `w-ideation`.

**Result:** The Mediator's required skill reads drop from 2 (w-ideation + h-ideation-panel) to 1 (w-ideation). h-ideation-panel becomes a panelist-only reference.

### Estimated Attention-Budget Savings

| Source | Lines Removed from Mediator Context |
|--------|-------------------------------------|
| agent-common.instructions.md | ~70 |
| h-ideation-panel (no longer read by Mediator) | ~300 |
| Opacity/transparency contradiction (confusion cost) | Qualitative |
| **Total** | **~370 lines + reduced ambiguity** |

---

## 3. O6 Idea Panel — Three New Agents

### Agents to Create

| Agent | File | Persona | Focus |
|-------|------|---------|-------|
| First-Principles | `share/agents/ideation-first-principles.agent.md` | Strips assumptions to axioms — "what is actually true vs. inherited?" | Challenge the problem's premises |
| Simplifier | `share/agents/ideation-simplifier.agent.md` | Complexity hunter — "what if we did 10% of this?" | Challenge scope and complexity |
| Outsider | `share/agents/ideation-outsider.agent.md` | Domain-naive questioner — "why does anyone care?" | Challenge relevance and framing |

### Template

Each agent follows the existing panelist template (~60 lines):

```yaml
---
name: ideation-{name}
description: "{Role} idea-panel agent — ..."
argument-hint: "{Name}: {working directory path}"
user-invocable: false
disable-model-invocation: true
tools: [edit/createDirectory, edit/createFile, edit/editFiles, read/readFile, ...]
agents: [ideation-critic]
hooks:
  PreToolUse:
    - type: command
      command: uv run python .owlbear/hooks/allow-stances-only.py
---
```

- **Model:** Claude Opus 4.6 (same as existing domain panelists — no reason to diverge)
- **Hook:** `allow-stances-only.py` (reuse existing safety hook)
- **Critic loop:** Mandatory, ≤5 cycles (same as domain panelists)
- **Read scope:** `working-log.md` (latest checkpoint), optionally `research-notes.md`
- **Write scope:** `stances/{name}.md` + `stances/{name}-debate.md`

### Insertion Point in w-ideation

New section: **Idea Challenge Phase** at end of M2, before M3.

```
M2 outcomes locked
  ↓
Mediator → [parallel batch]
  ideation-first-principles → stances/first-principles.md
  ideation-simplifier        → stances/simplifier.md
  ideation-outsider          → stances/outsider.md
  ↓
Mediator reads all 3 stances directly (no pragmatist)
  ↓
Mediator presents numbered challenges to user
  ↓
User decides: adjust M1/M2 outputs, or proceed to M3
```

### Why No Pragmatist for Idea Panel

The idea panel produces *challenges*, not *domain analyses*. Three short challenge documents don't need convergence/divergence synthesis — they need to be presented as "here are three angles of attack on your problem/outcomes." The Mediator reads them directly (~1-2 pages each). This is a justified exception to the "Mediator reads only summaries" rule.

The pragmatist remains exclusive to domain-panel synthesis (M3→M4), where 4 overlapping domain analyses genuinely need consolidation.

### Ideator Agent Update

Add the 3 new agents to `ideator.agent.md` frontmatter:

```yaml
agents:
  - ideation-critic
  - ideation-pragmatist
  - ideation-architect
  - ideation-data
  - ideation-enduser
  - ideation-security
  - ideation-first-principles   # NEW
  - ideation-simplifier          # NEW
  - ideation-outsider            # NEW
  - planner
  - Explore
```

---

## 4. O13 Selective Filter Agents

### Position

No new filter agents are needed. The existing pattern is sufficient:

| Subagent Output | Filter Applied | Rationale |
|-----------------|---------------|-----------|
| Domain panel (4 parallel stances) | `ideation-pragmatist` → `synthesis.md` | Overlapping domain analyses need consolidation |
| Idea panel (3 parallel challenges) | None — Mediator reads directly | Challenge documents are compact and non-overlapping |
| Standalone Critic | None | Already compact and targeted |
| Explore research | None | Already returns summary to Mediator |

### Application Rules (for w-ideation)

Filter agents are applied when:
1. **3+ parallel subagents** produce output on the **same question** (domain overlap creates redundancy)
2. **Total output exceeds ~10 pages** (raw volume exceeds Mediator attention budget)

Filter agents are NOT applied when:
1. Subagent output is a focused challenge or critique (inherently compact)
2. Subagent already produces a summary (Explore, standalone Critic)
3. Fewer than 3 parallel outputs on the same question

### Template for Future Filter Agents

If a future subagent pattern produces verbose parallel output, the filter agent follows `ideation-pragmatist` exactly:
- Reads specific stances + context
- Writes a single synthesis file
- Never advocates, only consolidates
- Disagreements attributed, not resolved

---

## 5. O14 Within-Moment Drift Visibility

### Mechanism

**Drift-check protocol** in w-ideation: After every 3 turns within a single moment, the Mediator appends a drift-check turn to the working log AND includes it in the user-facing message:

```markdown
### Turn {n} — M{x} — drift-check

> **Drift check (M{x}, turn {n}):** Working on {current focus}.
> Exit criteria remaining: {what's left before moment closes}.
> Turns in this moment: {count}.
```

### Properties

- **No hooks.** Pure protocol in w-ideation — a single paragraph, not a complex rule.
- **Visible in log.** Turn numbers make skipped drift checks evident to any reader.
- **User-triggerable.** "Where are we?" from the user produces a drift check at any time.
- **Tier-gated.** At Scratch/Tool tier, drift checks are every 5 turns (lower ceremony). At Studio/Production, every 3.

### Honest Warning

Drift checks are **discretionary protocol**. The Mediator can forget them — that's the same failure mechanism #1 (discretionary compliance) we diagnosed. The mitigation is structural:
1. One rule in one file (vs. scattered across 6)
2. The working log makes absence visible (turn 7 with no drift check at turn 3/6 is self-evident)
3. The user can always trigger manually

This reduces drift *visibility*, not drift itself. It's the best achievable outcome without compliance hooks, which the design principle forbids.

---

## 6. Phasing

### Phase 1 — Sprint Task (Pre-flight Cleanup)

**Not a Brief.** A single kanban task with clear AC.

| Change | File | AC |
|--------|------|----|
| Kill F2 dead load | `share/instructions/agent-common.instructions.md` | Ideation agents no longer load pipeline instructions |
| Fix F1 contradiction | `share/agents/ideator.agent.md` | Opacity directive removed; attribution directive added |
| W-ideation self-containment | `share/skills/w-ideation/SKILL.md` | Mediator-relevant panel rules inlined; Mediator no longer needs to read h-ideation-panel |
| H-ideation-panel scope | `share/skills/h-ideation-panel/SKILL.md` | Add note: "This file is a panelist reference. The Mediator reads w-ideation, not this file." |

**Estimated effort:** 1-2 hours. **Risk:** Near-zero (removing dead content, resolving a documented contradiction).

**Why first:** Reduces baseline attention budget by ~370 lines. Validates the root-cause hypothesis (if compliance improves, the diagnosis was correct). Creates a cleaner foundation for Phase 2.

### Phase 2 — Studio Brief (Structural Overhaul)

**This IS the Brief.** Depends on Phase 1 completion.

| Outcome | Implementation |
|---------|---------------|
| O1 (verbatim preservation) | Working log `user-input` turn type |
| O2 (single append-only log) | `working-log.md` schema + checkpoints |
| O4 (challenge by default) | Mediator persona update + idea panel |
| O6 (idea panel) | 3 new agent files + w-ideation insertion |
| O10 (6 moments preserved) | No structural change needed |
| O11 (fixed question format) | Already partially in w-ideation; canonicalize |
| O12 (always-brownfield) | w-ideation M1 update: research subagent runs by default |
| O13 (selective filters) | Application rules documented in w-ideation |
| O14 (drift visibility) | Drift-check protocol in w-ideation |

**Files created:** 3 (`ideation-first-principles.agent.md`, `ideation-simplifier.agent.md`, `ideation-outsider.agent.md`)
**Files modified:** 3 (`ideator.agent.md`, `w-ideation/SKILL.md`, `h-ideation-panel/SKILL.md`)
**Files deleted:** 0

---

## Key Trade-Offs

| Decision | Accepted Cost | Rejected Alternative |
|----------|--------------|---------------------|
| Working log replaces context.md + decisions.md | Panelists must scan to latest checkpoint | Keeping separate summary file (re-introduces multi-file fragmentation) |
| No pragmatist for idea panel | Mediator reads 3 extra files at M2 | Forcing pragmatist into challenge synthesis (wrong shape, adds confusion) |
| Drift checks are discretionary | Mediator can still forget | Compliance hooks on Mediator (violates design principle) |
| Two phases (Sprint + Brief) | Adds coordination overhead | Single Brief (delays quick wins behind heavier work) |
| Claude Opus 4.6 for idea panel | No model diversity in idea panel | Mixed models (adds tooling complexity for unclear benefit) |

---

## Warnings

1. **Drift checks are not enforcement.** O14 is the weakest outcome structurally. The design principle forbids hooks, so drift visibility is the ceiling. If the Mediator ignores drift checks, the failure mode is the same as today — just more visible in the log. The user must understand this is a *detection* improvement, not a *prevention* mechanism.

2. **Working log size at Scale.** For Production-tier ideation sessions (rare but possible), the working log could grow past 300 turns. The checkpoint mechanism handles panelist reads, but the Mediator itself re-reads earlier turns for continuity. At extreme scale, the Mediator will still face attention-budget pressure from its own log. Mitigation: the Brief walkthrough at M5 doesn't need the full log — it synthesizes from the latest checkpoint + the M4/M5 turns. But this is a known pressure point.

3. **Idea panel at end of M2 could feel interruptive.** Users who want to race to landscape research will hit a "hold on, let me challenge your framing first" gate. This is intentional (O6 specifies this placement) but may cause friction. The Mediator should frame it as a 2-minute challenge round, not a blocking gate.

4. **The Mediator's role is smaller but not simpler.** Shrinking the Mediator to "capture/append/present/invoke" is a clear scope reduction. But the working log's checkpoint discipline and the idea-panel integration add new coordination duties. The net complexity may be comparable; the nature of the complexity shifts from "remember scattered rules" to "maintain one structured artifact."

---

## Confidence: 0.82

High confidence on the structural proposals (working log, instruction reduction, idea panel template, phasing). Moderate confidence on O14 (drift checks are inherently limited by the no-hooks constraint). The architectural direction is sound — consolidation reduces the attack surface for attention-budget failures — but O14 will need monitoring after deployment to see if discretionary drift checks actually get produced.
