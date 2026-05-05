---
id: 1354
title: 'P1-01: Write agent-broad-audit.prompt.md'
status: in-progress
priority: needed
created: 2026-05-04T21:22:32.017764+00:00
updated: 2026-05-05T09:13:07.117006+00:00
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

## AC (from Brief AC1 + AC3 broad side)

**In scope:**
- Create `share/prompts/agent-broad-audit.prompt.md` that replaces `.owlbear/prompts/agent-audit.prompt.md`
- Preserve all existing audit dimensions (D1-D5, D7) with finding-loop interaction model
- Strengthen D6 (SNR): scan for 6-category noise-taxonomy patterns, emit attention flags, highlight universal files (`applyTo: **`) as highest-leverage
- Add end-of-run ranked report: dual-axis scoring (noise density relative to category peers × context-budget weight)
- Inline the shared 6-category noise taxonomy (matching definitions used in #1355)
- Delete the old `.owlbear/prompts/agent-audit.prompt.md` after new prompt is verified

**Out of scope:**
- Per-sentence compression proposals (that's the deep-dive's job)
- Automated pipeline between broad and deep-dive
- Actually running the audit on all files

**6-category noise taxonomy (inline in prompt):**
1. Verbose prose wrappers
2. Over-specification
3. Redundant conditionals
4. Prescriptive message templates
5. Cross-reference ceremony
6. Stale institutional memory

**Key input:** Read `.owlbear/prompts/agent-audit.prompt.md` (existing, being replaced) to understand current D1-D7 structure.

**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`
[[2026-05-05]]
## Test-Writer Notes
- Non-implementation task (tagged `prompt`) — no tests applicable.
- AC describes creating `share/prompts/agent-broad-audit.prompt.md` and deleting `.owlbear/prompts/agent-audit.prompt.md`. These are markdown prompt files with no testable Python interfaces.
- Passing through to builder.