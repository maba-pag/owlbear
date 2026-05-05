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
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## AC (from Brief AC4)

**In scope:**
- Run `agent-deep-audit.prompt.md` targeting the reviewer agent (192 lines + 1,113 lines required reading)
- Rate proposal quality: measurable token reduction with per-section justification
- Verify no pipeline regression after applying proposals (run reviewer on a known task)
- Document findings: what worked, what was over-cut, what taxonomy categories appeared most

**Out of scope:**
- Actually applying all proposals permanently (this is evaluation only)
- Modifying the prompts based on findings (separate follow-up if needed)

**Pre-conditions:**
- #1354 and #1355 must both be complete (prompts must exist)
- This is a user-action task — requires human execution and judgment

**Brief:** see parent #1353 → `.owlbear/briefs/draft-skill-snr/brief.md`