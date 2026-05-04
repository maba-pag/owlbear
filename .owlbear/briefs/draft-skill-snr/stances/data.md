# Data Quality Stance — SNR Measurement Tools

## Position Summary

The SNR tooling problem is fundamentally a **classification reliability** problem. Both tools classify content — the broad audit classifies files into attention-priority tiers, the deep-dive classifies passages into content-function × signal-adequacy labels. The design must optimize for classification quality: clear schemas, explicit uncertainty, and appropriate validation boundaries.

## 1. Signal Density Is a Triage Ranking, Not a Quality Score

The broad audit produces a **comparative attention-priority ranking** — files ordered by likelihood of benefiting from deep-dive compression. This is not a quality score and must not be presented as one.

Ranking heuristics (acknowledged as imperfect triage indicators):

- Token volume of loaded chain (file + required_reading = exposure cost)
- Prose density relative to category peers (workflow skills benchmarked against workflow skills, not agent files)
- Cross-file repetition rate (same imperative in 3+ places)

These heuristics conflict with each other. A file can be high-volume but high-signal, or low-volume but pure noise. The ranking optimizes for **expected compression yield** — files where deep-dive effort is most likely to reclaim tokens without cutting signal. When heuristics conflict, volume-of-loaded-chain dominates because it directly maps to context pressure.

**Critical constraint:** The ranking is the de facto gate on deep-dive attention. Acknowledge this honestly rather than hiding behind "advisory." Mitigation: the broad audit is designed to be re-runnable cheaply, so rankings update as the ecosystem changes.

## 2. Classification Schema: Two Orthogonal Axes

The deep-dive operates on a two-axis classification:

**Axis 1 — Content Function** (what role does this passage play?):

| Function | Description | Example |
|----------|-------------|---------|
| Behavioral constraint | Imperative rule that steers agent action | "Never commit without running tests" |
| Procedural sequence | Ordered steps where order is load-bearing | "Read AC → write test → run → verify" |
| Factual anchor | Operational reference (path, tool name, routing cue) | "Quality-runner is the lint subagent" |
| Institutional memory | Encodes a past failure or hard-won lesson | "Don't retry identical commands — loop detection" |
| Emphasis anchor | Deliberate repetition for attention salience | Critical rule restated in summary section |
| Cross-reference pointer | Navigation to related content | "See h-mcp-kanban § Agent Lifecycle" |

**Axis 2 — Signal Adequacy** (for this file's consumers, does this passage steer behavior the model wouldn't produce alone?):

- **Essential** — removal would change agent behavior on representative tasks
- **Reinforcing** — removal probably wouldn't change behavior but adds robustness
- **Redundant** — information available elsewhere in the loaded context chain
- **Inert** — no behavioral steering; pure filler or over-explanation

This is NOT binary. A passage carries both a function label and an adequacy judgment. "Institutional memory" + "essential" = keep. "Cross-reference pointer" + "inert" = cut candidate.

## 3. Error Model: Asymmetric but Both Sides Have Real Cost

| Error | Consequence | Feedback speed | Mitigation |
|-------|-------------|----------------|------------|
| False positive (cutting signal) | Pipeline regression | Fast — breaks show immediately | Conservative bias on procedural sequences and institutional memory |
| False negative (keeping noise) | Attention dilution, silent degradation | None — no feedback signal | Broad audit resurfaces high-noise files in future runs |

**Bias rules:**

- Lean conservative on: procedural sequences, institutional memory, emphasis anchors
- Lean aggressive on: cross-reference pointers to content already in required_reading chain, verbose prose wrappers around self-explanatory code blocks
- Lean cautious (not aggressive) on: factual anchors — these are often operational (exact paths, tool names, routing cues). Only cut when the fact is provably available at point-of-use via the loaded context chain

The silent-degradation problem (false negatives) has no natural feedback loop. The correct mitigation is periodic re-audit, not a single-pass aggressive cut.

## 4. Taxonomy Design: Fixed Core + Emergent Extension

The compression-pattern taxonomy (what's wrong with a passage when signal adequacy is low):

**Fixed core** (baked into the prompt):

1. Verbose wrapper — prose around self-explanatory content
2. Over-specification — excessive detail where summary suffices
3. Redundant conditional — information implied by structure
4. Prescriptive template — full format where required fields suffice
5. Ceremonial cross-reference — pointer adding no navigational value
6. Stale institutional memory — encodes a failure that's been architecturally prevented

**Emergent extension:** The agent can flag passages that don't fit and propose a new pattern label. New labels are surfaced to the user but do NOT automatically enter the fixed core. Promotion to core requires seeing the same pattern in 3+ files.

**Why not fully emergent:** Emergent-only taxonomies drift across audit sessions. An agent might call the same pattern "verbose wrapper" in one file and "over-explanation" in another. Fixed core ensures consistency; emergent extension ensures completeness.

## 5. Consumer-Context Resolution Is Mandatory for Procedural Content

Classification reliability depends on knowing who consumes the content:

| Content function | Consumer context required? | Why |
|-----------------|---------------------------|-----|
| Behavioral constraint | Yes — check who loads this file | Same constraint may be essential for one consumer, redundant for another |
| Procedural sequence | Yes — always | Sequence correctness is consumer-specific |
| Factual anchor | Conditional — only when considering cuts | "Use uv run" is universal; "quality-runner is available" is consumer-specific |
| Institutional memory | Yes — need to know if the failure is still possible for this consumer | |
| Emphasis anchor | Yes — attention decay depends on total loaded context length | |
| Cross-reference pointer | No — can evaluate navigation value structurally | |

The deep-dive MUST resolve `applyTo` patterns and `required_reading` references before classifying signal adequacy on procedural content. Skipping this step is a data integrity violation — it produces classifications without ground truth.

## 6. "Trivial Knowledge" Bounded by Behavioral Testability

**Operational definition:** Content is trivial if removing it would not change the agent's behavior on representative tasks within the current model family.

This is imperfect but constrains the judgment:

- Bounded to current models (not future-proofing — that's the user's call in the interactive loop)
- Bounded to behavioral change (not "does the model know the fact" but "does the model need the instruction to act correctly")
- Validated by interactive loop (agent classifies → user confirms/rejects)

**What the prompt must surface per classification:**

- The specific claim: "Model already knows X because Y"
- Confidence: high/medium/low
- Risk if wrong: what specific behavior would degrade

This structure makes user validation efficient — scan confidence levels, drill into low-confidence or high-risk items, rubber-stamp high-confidence low-risk items.

**Acknowledged weakness:** "Behavioral testability" is testable-in-principle but not tested-in-practice during the audit. The audit is a judgment call, not an experiment. The interactive loop is the validation boundary, not a substitute for it.

## 7. Scope Boundaries Between Tools

| Dimension | Broad Audit | Deep-Dive |
|-----------|-------------|-----------|
| Finds noise | Yes (flags files) | Yes (classifies passages) |
| Finds missing signal | Yes (negative-space probes, coverage gaps) | No — compression only |
| Unit of analysis | File | Section (structural) / Paragraph (adequacy) |
| Output | Ranked priority list + ecosystem patterns | Compression proposal with per-passage justification |
| Data flow | Does NOT propagate scores into deep-dive | Starts fresh with own consumer-context resolution |

The deep-dive may propose structural reorganization (splitting sections, moving content to a different file) — it is not confined to compression within existing boundaries.

## Key Trade-offs

1. **Conservative bias → slower noise reduction.** Accepting this because pipeline stability is more valuable than token savings.
2. **Consumer-context resolution → more expensive deep-dive.** Required for reliability; cannot be shortcut without producing garbage classifications.
3. **Fixed taxonomy → may miss novel patterns.** Mitigated by emergent extension, but novel patterns won't get consistent labeling until promoted to core.
4. **No experimental validation → classification is judgment, not measurement.** The interactive loop is the only real validation. This is honest but means audit quality depends on user engagement.

## Warnings

- **Silent degradation has no natural correction.** If the tools bias too conservative, noise accumulates silently. The only mitigation is periodic re-audit discipline.
- **Peer-group definition matters.** "Repetition across peers" requires explicit peer-group boundaries (workflow skills vs. handbook skills vs. agent files). Without this, the broad audit will produce meaningless comparisons.
- **The ranking IS the gate.** Calling it "advisory" does not change that low-ranked files won't get deep-dived. Design the heuristics knowing this.
- **Factual anchors are dangerous to cut.** Exact paths, tool names, and routing cues look like "trivial facts" but are often the most operationally critical content. The aggressive-cut bias must NOT apply to operational anchors.

## Confidence

0.72

Confident on: schema structure, error model, consumer-context requirement, taxonomy design.
Less confident on: whether the behavioral-testability framing is operational enough for prompting, whether the broad audit's ranking heuristics will produce useful orderings in practice.
