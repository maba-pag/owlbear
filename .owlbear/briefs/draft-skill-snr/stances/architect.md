# Architectural Stance — SNR Tool Pair Design

## Architectural Stance

The two-tool design is structurally sound. The broad audit and deep-dive serve genuinely different units of analysis (ecosystem vs. file-interior) that cannot be merged without quality collapse. The key structural decisions are:

1. The deep-dive's interaction model must adapt to file type — there is no single chunking strategy for a heterogeneous corpus.
2. The broad audit's scoring produces category-grouped rankings, not a global priority order.
3. The tools share a taxonomy by inline duplication (small enough to inline), not by runtime reference.
4. Universal files (applyTo: **) are a separate leverage class that transcends category-peer scoring.

## Structural Reasoning

### Deep-Dive: Adaptive Chunking with Multi-File Awareness

The corpus is structurally heterogeneous. Imposing a fixed "section-batch" model fails because:
- Agent files distribute behavioral intent across persona, boundaries, examples, and output format (sections are not semantically independent)
- Workflow skills have clear `##` sections that ARE natural review boundaries
- Short instruction stubs and launcher prompts are single-pass targets
- Long procedural prompts divide naturally by step-groups

**Design:** The deep-dive adapts its presentation strategy per file type:

| File type | Chunking strategy | Rationale |
|-----------|------------------|-----------|
| Workflow/handbook skills (100–540 lines) | Section-batch (one `##` section at a time) | Clear boundaries, sections are relatively independent |
| Agent contracts | Full-file proposal with per-region annotations | Distributed semantics require holistic evaluation |
| Short files (<100 lines) | Single-pass | Overhead of batching exceeds benefit |
| Long procedural prompts | Step-group batches (3–5 steps) | Natural procedure boundaries |

**Critical:** The deep-dive's *analysis scope* is broader than its *presentation scope*. For agent files, the tool loads the agent + its required_reading to judge cross-file dependencies. Compression proposals are file-local (that's where the edits happen), but safety evaluation is contract-wide. This prevents cuts that look safe in isolation but break distributed behavioral intent.

The interaction model uses askQuestions per chunk: original text → proposed compression → rationale → user approves/rejects/modifies.

### Broad Audit: Category-Grouped Ranking with Leverage Flagging

The ranking cannot be a single global priority list because scoring is peer-relative. A 200-line agent and a 540-line workflow skill aren't on the same scale. The audit produces:

**Per-category ranked tables** (one for skills, one for agents, one for prompts/instructions):

| Dimension | What it captures |
|-----------|-----------------|
| Absolute size (lines) | Raw volume baseline |
| Maximum context budget | Total tokens when this file activates via all documented load paths (required_reading, applyTo, companion, body-ref) |
| Noise indicator | Which of 5 noise categories are likely present, severity estimate |
| Connection profile | Typed edges: N regular consumers, M seldom, K applyTo triggers |

**Universal-file leverage class** (separate from categories): Files with `applyTo: **` or that appear in >50% of agents' required_reading get flagged as high-leverage targets regardless of category ranking. A 5% noise reduction in a universal file saves more total tokens than a 30% reduction in a single-consumer skill.

The ranking table is a **durable snapshot artifact** — written to a file with a date stamp. It becomes stale after significant edits to the scored files. The audit notes this explicitly.

**Important:** Context budget is session-contingent for some load paths (prompt-ref, organic). The metric represents *maximum potential* context cost, not guaranteed-always-loaded. This is acceptable because it's a prioritization heuristic, not an accounting system.

### Coupling: Inline Taxonomy, User-Bridged Routing

The noise taxonomy is 5 items:
1. Verbose prose wrappers
2. Over-specified interpretation
3. Redundant conditional notes
4. Prescriptive message templates
5. Cross-reference ceremony

This is small enough to inline in both prompts without creating drift risk. The broad audit is the canonical source — if the taxonomy evolves, it evolves there first and the deep-dive is updated to match.

**No automated pipeline.** The user reads the audit's ranking artifact, chooses a file, invokes the deep-dive. This is correct because:
- The audit runs incrementally (finding-loop, one-at-a-time) — completing it may take multiple sessions
- The user may have their own priorities that override the ranking
- Deep-dive should work on ANY file, including ones not yet audited

**Taxonomy is context-dependent.** "Prescriptive message templates" is noise in a handbook reference but may be essential signal in a workflow skill that MUST produce exact output. The categories name *patterns*, not universal judgments. The deep-dive applies constraint calibration per file type to determine whether a pattern instance is noise or signal in context.

## Key Trade-offs

| Trade-off | Choice | Cost |
|-----------|--------|------|
| Adaptive chunking vs. uniform model | Adaptive | Prompt complexity — must describe 4 strategies instead of 1 |
| Category-grouped vs. global ranking | Category-grouped | User must compare across tables manually; no single "worst file" answer |
| Inline taxonomy vs. reference-only | Inline both | Small duplication (5 items); must update both prompts when taxonomy changes |
| Multi-file analysis scope for deep-dive | Agent + linked skills loaded for evaluation | Larger context window usage during deep-dive; may hit limits on the heaviest agents |
| Durable artifact vs. conversational-only | Durable with freshness date | Extra write step at end of audit; file can go stale |

## Warnings

1. **Do not conflate presentation chunks with semantic boundaries.** The deep-dive presents in sections for user review but evaluates whole-contract impact. If implemented wrong (truly independent section analysis), it will propose cuts that break distributed agent behavior.

2. **The taxonomy is descriptive, not prescriptive.** A pattern appearing in a file doesn't automatically mean it's noise. "Over-specified interpretation" in a safety-critical boundary section is signal. The deep-dive must apply constraint calibration, not mechanical category → cut.

3. **Context budget is approximate.** Don't over-engineer the metric. The wiring model has conditional edges, organic connections, and documented drift. An 80% accurate heuristic is sufficient for prioritization. Precision theater (exact token counts per path) would be wasted effort.

4. **Universal files are the highest-leverage targets.** If the ranking table doesn't call them out separately, the user will waste deep-dive sessions on single-consumer files while universal noise persists.

## Confidence

0.76

Revised through two Critic cycles. Residual uncertainty: (a) whether the 4-strategy adaptive chunking adds too much prompt complexity for a .prompt.md file to carry clearly, (b) whether the "maximum potential context budget" metric is actionable enough given session-contingent load paths.
