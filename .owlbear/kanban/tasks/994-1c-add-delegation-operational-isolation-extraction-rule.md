---
id: 994
title: '1c: Add delegation / operational-isolation extraction rule'
status: research
priority: needed
created: 2026-04-18T21:23:32.421869+00:00
updated: 2026-04-18T21:39:20.231455+00:00
tags:
- type:docs
- scope:skills
parent: 984
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #984

## Objective
Add a rule defining markers for "when to extract a dedicated agent or subagent" to an appropriate authority skill. Location TBD by architect — likely `h-agent-structure` (if about agent structure) or `r-pipeline-protocol` (if about pipeline operations). Precedent: `quality-runner` exists because test-running has many failure modes despite a one-line prose description.

## Content
- Extraction markers (complexity signals, failure-mode count, reuse frequency)
- Operational-isolation criteria (when shared execution context becomes a liability)
- Reference to `quality-runner` as worked example

## Acceptance Criteria
- [ ] Rule is placed in the architecturally appropriate skill file (decided by architect).
- [ ] Defines concrete extraction markers (not vague guidelines).
- [ ] References quality-runner as precedent.
- [ ] Future audits can objectively flag missed extraction opportunities against this rule.
- [ ] No rules duplicated from other skills.

## Files
- `share/skills/h-agent-structure/SKILL.md` OR `share/skills/r-pipeline-protocol/SKILL.md` (architect decides)
[[2026-04-18]]
## Architecture Review

### Verdict: REJECT (Duplicate)

Task #994 is a pre-split duplicate of #1002 ("Add agent-extraction markers to h-agent-structure"), which was created during the architecture review of parent Brief #984. The post-split task #1002 supersedes #994 with:

- Tighter AC (concrete marker counts, format requirements, counter-markers)
- Proper `depends_on: [1000]` (prevents file-conflict with sibling editing the same SKILL.md)
- Correct `agent` tag for pipeline pass-through

The full pre-split set (#992, #993, #994, #995) is superseded by the post-split set (#1000, #1001, #1002, #1003). Recommend archiving all pre-split children to avoid confusion.