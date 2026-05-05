---
id: 1355
title: 'P1-02: Write agent-deep-audit.prompt.md'
status: in-progress
priority: needed
created: 2026-05-04T21:22:32.030360+00:00
updated: 2026-05-05T09:53:32.550771+00:00
tags:
- phase-1
- scope:prompts
- prompt
- snr
parent: 1353
depends_on: []
blocked: true
block_reason: postponed
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC2 + AC3 deep side)

**In scope:**
- Create `share/prompts/agent-deep-audit.prompt.md` (new file)
- Two scope modes: agent mode (agent + all referenced skills) and skill mode (skill + all consumer agents)
- Pre-analysis: map full dependency cluster, load files, understand unit before evaluating
- Core analysis: correctness, completeness, naming/structure, value-per-instruction, signal-to-noise (per-sentence), cross-file coherence
- Output: single structured proposal per target — structural proposals first, compression proposals second, issues third
- Interaction model: section-by-section approval via `askQuestions` (grouped by file), batch-approve escape hatch
- Conservative bias: lean toward keeping when uncertain; procedural sequences and institutional memory get extra protection
- Inline the shared 6-category noise taxonomy (matching definitions used in #1354)
- For universal skills (`applyTo: **`): pragmatic sampling — top 3-5 heaviest consumers

**Out of scope:**
- Ecosystem-wide coherence checks (that's the broad audit's job)
- Automated pipeline from broad audit findings
- Actually running the deep-dive on all files

**6-category noise taxonomy (inline in prompt):**
1. Verbose prose wrappers
2. Over-specification
3. Redundant conditionals
4. Prescriptive message templates
5. Cross-reference ceremony
6. Stale institutional memory

**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`
[[2026-05-05]]
## Test-Writer Notes
- Non-impl pass-through: AC references only `.prompt.md` file creation — no Python interfaces, no testable contract.
- Passing through to builder.