---
id: 1355
title: 'P1-02: Write agent-deep-audit.prompt.md'
status: todo
priority: needed
created: 2026-05-04T21:22:32.030360+00:00
updated: 2026-05-04T21:23:22.457065+00:00
tags:
- phase-1
- scope:prompts
- prompt
- snr
parent: 1353
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC2 + AC3 deep side)\n\n**In scope:**\n- Create `share/prompts/agent-deep-audit.prompt.md` (new file)\n- Two scope modes: agent mode (agent + all referenced skills) and skill mode (skill + all consumer agents)\n- Pre-analysis: map full dependency cluster, load files, understand unit before evaluating\n- Core analysis: correctness, completeness, naming/structure, value-per-instruction, signal-to-noise (per-sentence), cross-file coherence\n- Output: single structured proposal per target — structural proposals first, compression proposals second, issues third\n- Interaction model: section-by-section approval via `askQuestions` (grouped by file), batch-approve escape hatch\n- Conservative bias: lean toward keeping when uncertain; procedural sequences and institutional memory get extra protection\n- Inline the shared 6-category noise taxonomy (matching definitions used in #1354)\n- For universal skills (`applyTo: **`): pragmatic sampling — top 3-5 heaviest consumers\n\n**Out of scope:**\n- Ecosystem-wide coherence checks (that's the broad audit's job)\n- Automated pipeline from broad audit findings\n- Actually running the deep-dive on all files\n\n**6-category noise taxonomy (inline in prompt):**\n1. Verbose prose wrappers\n2. Over-specification\n3. Redundant conditionals\n4. Prescriptive message templates\n5. Cross-reference ceremony\n6. Stale institutional memory\n\n**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`