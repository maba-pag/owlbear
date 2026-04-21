# Modeler — Data Quality Stance

**Panelist:** The Modeler (ideation-data)
**Subject:** Data architecture for the ideation system overhaul — working log schema, file survival, subagent contracts, validation
**Confidence:** 0.82
**Critic cycles:** 5 (exited: position is solid)

---

## Data Quality Stance

The working log (O2) must be a **structured markdown document with rigid section grammar** — not free-form prose, not JSONL. Schema discipline comes from header conventions and required sections, enforced by process discipline rather than formal validation tooling. The key data invariant: **append-only with no mutable sections.** Any mutable state lives in a separate file (`context.md`), with an explicit canonicality rule that the log wins on conflict.

---

## 1. Working Log Schema (O2)

### Filename

`working-log.md` in the Working Directory.

### Turn Structure

Each turn is a completed interaction cycle. The Mediator writes the turn after it concludes (turns are historical records, never in-progress drafts).

```markdown
### Turn {N} — {YYYY-MM-DD HH:MM} [{Moment}]

#### User Input

> {verbatim, blockquoted — O1 compliance}

#### Mediator Proposal

**Context:** {status quo — 1-2 sentences}
**Problem:** {what needs deciding}

| Option | Pro | Con | Risk | Confidence |
|--------|-----|-----|------|------------|
| A      | ... | ... | ...  | 0.8        |
| B      | ... | ... | ...  | 0.5        |

**Recommended:** A — {1-line reason}

#### Subagent Feedback

{Summary of subagent outputs relevant to this turn.
 If panel ran: "See stances/*.md for full panelist positions."
 If Explore ran: "See research-notes.md for full findings."}

#### Decision

**Chosen:** {option label}
**Rationale:** {user's words, verbatim where possible}
**Rejected:**
- {option} — {reason for rejection}
```

### Required vs. Optional Sections

| Section             | Required? | Notes |
|---------------------|-----------|-------|
| Turn header         | **Yes**   | Must include turn number, ISO timestamp, moment marker `[MX]` |
| User Input          | **Yes**   | Every turn has user input. Blockquoted verbatim. |
| Mediator Proposal   | No        | Present when the Mediator proposes options. Absent for informational/acknowledgment turns. |
| Subagent Feedback   | No        | Present when subagents ran during this turn. |
| Decision            | No        | Present when the user decided. Absent for informational turns. |

### Decision States

The Decision section's presence/absence carries semantic weight:

- **Present with Chosen** → user decided.
- **Present with `**Deferred:** {what and why}`** → user explicitly deferred a decision.
- **Absent** → no decision was required in this turn (informational exchange).

No `open` state. Turns are completed records.

### Moment Transition Entries

When a moment ends, the Mediator appends a **moment-transition entry** — a lightweight checkpoint that enables state retrieval without re-reading the full log.

```markdown
### Moment Transition — M{X} → M{X+1} — {YYYY-MM-DD HH:MM}

**Decisions from M{X}:**
- D1: {one-line summary} (Turn {N})
- D2: {one-line summary} (Turn {N})
- Deferred: {what} (Turn {N})

**Entering M{X+1} with:** {1-sentence framing of what the next moment addresses}
```

This is append-only (a new entry, not an edit). It's the cheapest way for the Mediator to recover moment-level state: jump to the last transition entry, read the bullet list.

### Write Discipline

- **Single writer:** Mediator only. No subagent writes to the working log.
- **Append-only:** No edits to prior turns or transition entries. Only new entries appended at the end.
- **No deletions.** If a turn contains an error, the Mediator appends a correction turn referencing the original (e.g., "Correction to Turn N: ...").
- **Ordering:** Turns are numbered sequentially starting at 1. Moment transitions are unnumbered but timestamped.

### State Retrieval

The Mediator does NOT need to re-read the entire log each turn. Retrieval strategy:

1. **Immediate context:** Read the last 1-2 turns.
2. **Moment-level context:** Jump to the most recent moment-transition entry for a summary of prior-moment decisions.
3. **Specific lookup:** Search by turn number or moment marker when a particular decision is needed.

This is cheaper than re-reading and doesn't require a mutable index.

---

## 2. Markdown vs. JSONL Trade-off

**Position: Markdown with rigid grammar. Not JSONL.**

Justification:
- All existing append-only prior art (`activity_log.py`, `AuditLog`, `ErrorJournal`) is JSONL — machine-event logs. The working log is a **discussion record**, not a machine-event stream. Different data, different shape.
- User explicitly rejected formal-registry patterns (D3, D4). JSONL + Pydantic would re-introduce that rigidity.
- KISS constraint: markdown is human-readable without tooling.

Schema discipline that keeps markdown navigable:
- **Rigid headers.** Turn headers follow exact format: `### Turn {N} — {timestamp} [{Moment}]`. Machine-scannable via regex `^### Turn \d+`.
- **Fixed subsection names.** `#### User Input`, `#### Mediator Proposal`, `#### Subagent Feedback`, `#### Decision`. No synonyms, no variations.
- **No free-form prose between turns.** Everything lives inside a turn's subsections or a transition entry.
- **Blockquote convention** for verbatim user input (O1).
- **Decision micro-format** with fixed field names (Chosen, Rationale, Rejected, Deferred).

This gives navigability without JSONL rigidity. A `grep "^### Turn"` produces a table of contents. A `grep "^#### Decision"` produces a decision index.

---

## 3. Decision Artifact Integrity (O11)

Every decision point has TWO data moments:

**The Proposal** (Mediator → User, O11 format):
- Context/status-quo
- Problem statement
- Options table with per-option Pro/Con/Risk/Confidence
- Recommended option with 1-line justification

**The Decision** (User → Log, recorded by Mediator):
- Chosen option
- User's rationale (verbatim where possible)
- Rejected options, each with a rejection reason
- OR Deferred with what/why

The proposal and decision are adjacent subsections in the same turn. No information evaporates: the proposal has the full option analysis (including the Mediator's recommendation and confidence), the decision records the user's choice and the fate of every option. This closes Failure Mechanism 3 (lossy decision artifacts).

---

## 4. Subagent Output Contracts

### Domain Panelists (Architect, Modeler, End User, Skeptic)

**Existing format, formalized:**

```markdown
## {Panelist Name} Stance

{1-3 sentence position statement}

## Reasoning

{The argument — structured however the panelist needs}

## Trade-offs

{What's gained and lost — OPTIONAL}

## Warnings

{Risks the panelist sees — OPTIONAL}

## Confidence

{0.0-1.0} — {calibration note}
```

**Required sections:** Stance, Reasoning, Confidence.
**Optional sections:** Trade-offs, Warnings.

Output file: `stances/{name}.md`
Debate file: `stances/{name}-debate.md`

### Idea Panel (O6: First-Principles, Simplifier, Outsider)

**Same stance structure as domain panelists.** They ARE panelists — earlier in the process (end of M2, covering problem + outcomes) and with different domain focus (challenging the idea itself, not implementation), but the output shape is identical.

Output files: `stances/first-principles.md`, `stances/simplifier.md`, `stances/outsider.md`
Debate files: `stances/{name}-debate.md`

Rationale: same Critic loop protocol (≤5 cycles), same Mediator consumption path (Pragmatist synthesizes), same Pragmatist input expectations. Different shape would force Pragmatist to handle multiple formats — unnecessary complexity.

### Filter/Synthesis Agents (O13: Pragmatist as canonical)

**Existing synthesis.md format, unchanged:**

```markdown
## Summary
{1-3 sentence frame — no advocacy}

## Convergences
- {Item}: {panelists} agree that...

## Disagreements (User Decision Required)
- {Item}: {Panelist A} says X because... {Panelist B} warns Y because...

## Recommendations
{Only if all panelists converge; omitted if any disagreement remains}
```

**Required sections:** Summary, Convergences, Disagreements.
**Optional sections:** Recommendations (convergent cases only).

This is NOT the panelist stance shape. Filter agents synthesize, they don't advocate. No Confidence field — confidence is attributed to the source panelists, not to the synthesizer.

---

## 5. File Survival Map

| File | Fate | Writer | Discipline | Rationale |
|------|------|--------|-----------|-----------|
| `working-log.md` | **NEW** | Mediator | Append-only | O2 — the sequential discussion record |
| `context.md` | **SURVIVES** | Mediator | Mutable (updated at moment boundaries) | Panelists need a clean reference. Not part of the log. |
| `decisions.md` | **ABSORBED** | — | — | Decisions are inline per-turn in the working log |
| `stances/*.md` | **SURVIVES** | Panelists | Write-once per invocation | Subagent isolated outputs |
| `synthesis.md` | **SURVIVES** | Pragmatist | Write-once per invocation | Filter agent output |
| `research-notes.md` | **SURVIVES** | Explore / Mediator | Overwritable per M3 cycle | Referenced from log turn; too bulky for inline |
| `brief.md` | **SURVIVES** | Mediator | Written at M5/M6 | Final deliverable, compiled from log + stances + synthesis |

### Canonicality Rule

**The working log is the source of truth for decisions and discussion history.** `context.md` is a Mediator-maintained snapshot of agreed state (problem, outcomes, landscape). If context.md and the log disagree, the log wins.

context.md is NOT mechanically derived from the log. The Mediator hand-updates it. This is a maintenance burden — acknowledged and accepted under the KISS constraint. Mechanical derivation would require tooling that adds complexity without proportional value. The mitigation: the Mediator writes the moment-transition entry first, then immediately updates context.md. The transition entry serves as the fallback if context.md goes stale.

---

## 6. Validation / Schema-Drift Defenses

### What We Validate (Without Tooling)

| Check | What | How | Who |
|-------|------|-----|-----|
| Turn header format | `### Turn \d+ — \d{4}-\d{2}-\d{2} \d{2}:\d{2} \[M\d\]` | Regex-scannable | Mediator (self-check before appending next turn) |
| User Input presence | Every turn has `#### User Input` with blockquoted content | Mediator self-validates | Mediator |
| Decision completeness | If `#### Decision` present, must have `Chosen` or `Deferred` | Mediator self-validates | Mediator |
| Stance contract | `stances/*.md` must contain Stance, Reasoning, Confidence headings | Pragmatist flags missing sections before synthesizing | Pragmatist |
| Append-only discipline | No prior turns modified | Sequential turn numbers; no gaps; no edits | Observable via diff |

### What We Don't Validate

- **No Pydantic models.** No formal schema validation tooling. The log is markdown, not a data pipeline.
- **No pre-commit hooks on log format.** Per O9 design principle: no new compliance hooks on Mediator behavior.
- **No automated stale-context.md detection.** Process discipline only.

### Malformed Entry Response

- **Working log:** If the Mediator detects a malformed prior turn (during self-check), it appends a correction turn. It does not edit the malformed turn.
- **Stance file:** If the Pragmatist encounters a stance missing required sections, it flags the gap in `synthesis.md` under Disagreements and notes which panelist's output was incomplete. The Mediator surfaces this to the user and may re-invoke the panelist.
- **Silent corruption (nobody catches it):** The append-only discipline and sequential numbering make corruption discoverable after the fact via git diff. Not real-time detection, but a safety net.

---

## Key Trade-offs

1. **Dual-artifact maintenance** (context.md + working log) trades single-source-of-truth purity for panelist usability. Panelists need a clean snapshot, not a 200-turn log.

2. **Markdown over JSONL** trades machine-parseable structure for human-readability and KISS compliance. Regex-scannable headers are "good enough" for navigation; JSONL's benefits (typed fields, Pydantic validation) are not worth the rigidity tax.

3. **Process discipline over automated enforcement** for validation. Consistent with the design principle ("do not fix attention failures by adding more rules") but introduces human-process failure modes.

4. **Moment-transition entries** add protocol surface (one more thing the Mediator writes) in exchange for cheap state retrieval. Net positive: avoids full-log re-read, which is the attention-budget problem.

---

## Warnings

1. **context.md staleness is the most likely data failure.** The Mediator must update it immediately after writing a moment-transition entry. If this discipline lapses mid-session, panelists in the next moment get stale context. There is no automated detection. The moment-transition entry in the log is the fallback, but panelists don't read the log.

2. **Working log will grow large.** A Studio-tier session may produce 30-50 turns + 5-6 transition entries. At ~30 lines per turn, that's 1000-1500 lines. The Mediator must NOT re-read the full log routinely — only the last turn + the most recent transition entry. If the Mediator falls back to full re-read, the attention-budget problem resurfaces.

3. **Stance contract enforcement is trust-based.** A panelist that omits the Confidence section produces a degraded stance. The Pragmatist may or may not catch it. There's no hard gate. This is acceptable for the current system (panelists are authored by us), but would be a risk if panelist agents were externally contributed.
