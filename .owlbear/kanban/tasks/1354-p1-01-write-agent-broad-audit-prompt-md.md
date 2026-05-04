---
id: 1354
title: 'P1-01: Write agent-broad-audit.prompt.md'
status: todo
priority: needed
created: 2026-05-04T21:22:32.017764+00:00
updated: 2026-05-04T21:23:22.454225+00:00
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

## AC (from Brief AC1 + AC3 broad side)\n\n**In scope:**\n- Create `share/prompts/agent-broad-audit.prompt.md` that replaces `.owlbear/prompts/agent-audit.prompt.md`\n- Preserve all existing audit dimensions (D1-D5, D7) with finding-loop interaction model\n- Strengthen D6 (SNR): scan for 6-category noise-taxonomy patterns, emit attention flags, highlight universal files (`applyTo: **`) as highest-leverage\n- Add end-of-run ranked report: dual-axis scoring (noise density relative to category peers × context-budget weight)\n- Inline the shared 6-category noise taxonomy (matching definitions used in #1355)\n- Delete the old `.owlbear/prompts/agent-audit.prompt.md` after new prompt is verified\n\n**Out of scope:**\n- Per-sentence compression proposals (that's the deep-dive's job)\n- Automated pipeline between broad and deep-dive\n- Actually running the audit on all files\n\n**6-category noise taxonomy (inline in prompt):**\n1. Verbose prose wrappers\n2. Over-specification\n3. Redundant conditionals\n4. Prescriptive message templates\n5. Cross-reference ceremony\n6. Stale institutional memory\n\n**Key input:** Read `.owlbear/prompts/agent-audit.prompt.md` (existing, being replaced) to understand current D1-D7 structure.\n\n**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`