---
id: 1356
title: 'P1-03: Evaluate SNR prompts on reviewer agent'
status: todo
priority: important
created: 2026-05-04T21:22:32.042665+00:00
updated: 2026-05-04T21:23:22.466750+00:00
tags:
- phase-1
- scope:prompts
- user-action
- snr
parent: 1353
depends_on:
- 1354
- 1355
blocked: true
block_reason: 'Blocked until #1354 and #1355 are complete — evaluation requires both
  prompts to exist'
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC4)\n\n**In scope:**\n- Run `agent-deep-audit.prompt.md` targeting the reviewer agent (192 lines + 1,113 lines required reading)\n- Rate proposal quality: measurable token reduction with per-section justification\n- Verify no pipeline regression after applying proposals (run reviewer on a known task)\n- Document findings: what worked, what was over-cut, what taxonomy categories appeared most\n\n**Out of scope:**\n- Actually applying all proposals permanently (this is evaluation only)\n- Modifying the prompts based on findings (separate follow-up if needed)\n\n**Pre-conditions:**\n- #1354 and #1355 must both be complete (prompts must exist)\n- This is a user-action task — requires human execution and judgment\n\n**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`