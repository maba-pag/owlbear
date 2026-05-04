# Research Notes — Agent & Skill SNR

## Verified Findings

### File ecosystem size

- **80 files total:** 35 skills, 26 agents, 7 instructions, 12 prompts
- **Top 5 by lines:** w-code-review (540), h-agent-structure (537), r-pipeline-protocol (381), w-ideation-discovery (369), w-doc-update (366)
- **Reviewer agent:** 192 lines. References r-pipeline-protocol (381 lines) + w-code-review (540 lines) as required reading = **1,113 lines loaded** for one agent's primary workflow

### Current agent-audit prompt (`.owlbear/prompts/agent-audit.prompt.md`)

- 7 audit dimensions: Structural, Duplication, Content Placement, Quality, Pipeline Integrity, SNR, Memory Governance
- D6 (SNR) is 4 positive probes + 1 negative-space probe. Shallow — asks "is there rationale?" not "is this sentence steering behavior?"
- Finding loop: one finding at a time, full approval cycle. Thorough but can't go deep into one file's full content.
- The prompt loads 4 standards first (h-agent-structure, h-memory-structure, r-pipeline-protocol, r-project-standards) before evaluating

### Noise categories observed (sample: w-code-review, 540 lines)

| Category | Example | Compression strategy |
|----------|---------|---------------------|
| **Verbose prose wrappers** | "Invoke Quality-Runner for lint if not already done in Step 2 report:" before a code block that's self-explanatory | Remove wrapper sentence |
| **Over-specified interpretation** | 30-line dirty-tree contamination check with full git command, interpretation table, and exact FAIL message template | Could be 5 lines: condition → action → message template |
| **Redundant conditional notes** | "Conditional: Skip when no TestFromAC_* classes exist" repeated before a section whose title already implies this | Remove note, section title is sufficient |
| **Prescriptive message templates** | Full multi-line FAIL message with exact markdown formatting prescribed | State the required fields; let the model format |
| **Cross-reference ceremony** | "See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`." as its own section header | Inline as parenthetical or remove if the agent's required_reading already loads it |

### What the deep-dive prompt must handle

1. **Structure-level questions:** Does this section need to exist? Is this the right file for this content?
2. **Paragraph-level questions:** Is this saying something the model wouldn't do on its own? Is it as terse as possible for the required signal?
3. **Constraint calibration:** Is this over-specified (kills creative latitude) or appropriately tight (must be followed exactly)?
4. **Cross-file awareness:** Is this repeated elsewhere? Should it be extracted or deleted here?
5. **Verification safety:** Would cutting this cause a pipeline regression? (Judgment-based, not ablation)

### What the improved broad audit must add

1. **Relative SNR scoring:** not just "this section is verbose" but "this file has the lowest signal density relative to its peers in the same category"
2. **Cross-file duplication detection:** same rule in 3+ places (beyond what D2 currently checks)
3. **Token budget awareness:** flag files that load >1000 lines of required reading (context pressure proxy)
4. **Category-level patterns:** "all workflow skills have this same issue" rather than one-at-a-time findings

### Existing agent-audit strengths to preserve

- The finding-loop pattern (one at a time, approval cycle) works well
- The 7-dimension structure is sound — D6 just needs depth
- "References, not restates" principle is correct
- Negative-space probes are powerful (what's MISSING?)

## Candidate Implications

- The deep-dive prompt probably needs a different **interaction model** than the broad audit. The broad audit does one-finding-at-a-time. The deep dive should probably present a full-file compression proposal (before/after diff) for approval, because sentence-level approval loops would be impractical.
- The broad audit's D6 dimension could be restructured as a **scoring pass** rather than individual findings — rate each file's signal density, rank them, then the user decides where to deep-dive.
- The "creative latitude" axis might be expressible as a **spectrum annotation**: sections marked [TIGHT] must be followed exactly; sections marked [GUIDE] allow creative interpretation. This would make the deep-dive's judgment explicit and auditable.
- A "token budget report" (file + its required_reading = total loaded context) would make the broad audit actionable for priority decisions.

## Open Research Questions

1. **Interaction model for deep-dive:** Full-file proposal vs. section-by-section vs. diff-based? What gives the user enough control without making it 80 approval clicks per file?
2. **How to encode "creative latitude" durably?** If the deep-dive removes over-specification, how does the file signal "this is intentionally loose" vs "this was just never specified"?
3. **Broad audit scoring mechanics:** Should D6 produce a ranked list of files by signal density? What's the rubric?
4. **Verification baseline:** Before compressing the reviewer, should we record current pipeline pass rates as a regression baseline? Or is that overkill given existing monitoring?
5. **Scope of "trivial knowledge":** Who decides what the model "already knows"? The deep-dive agent doing the compression? The user reviewing the proposal? Both?
