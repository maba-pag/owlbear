---
id: 1425
title: 'P1-04: Revise doc-audit.prompt.md — TODO resolution + diagram ownership'
status: research
priority: important
created: 2026-05-08T00:32:24.572908+00:00
updated: 2026-05-08T00:32:58.369235+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on:
- 1423
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Revise `.owlbear/prompts/doc-audit.prompt.md`:

1. Add TODO marker batch resolution dimension — doc-audit resolves markers by fixing the underlying issue + removing the marker
2. Add diagram ownership section — doc-audit has full responsibility for diagram verification and creation
3. Include `describes`-based diagram verification (check diagram frontmatter `describes` field against actual content)
4. Remove or relax the one-finding-at-a-time constraint specifically for TODO marker batch resolution (markers can be processed in batch)
5. Retain existing structural conformance, duplication, placement, and audience-fitness dimensions

**In scope:** Prompt file only. Must pass assertions from #1422.
**Out of scope:** Skill rewrite (#1423), agent update (#1424).

Brief: see parent #1421