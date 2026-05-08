---
id: 1423
title: 'P1-02: Rewrite w-doc-update skill — 4-item checklist + verification layers'
status: research
priority: needed
created: 2026-05-08T00:32:18.617094+00:00
updated: 2026-05-08T00:32:58.345066+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on:
- 1422
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Full rewrite of `share/skills/w-doc-update/SKILL.md` implementing the doc-writer quality redesign:

1. Convention mapping table mapping code path patterns to documentation files (serve/{pkg}/src/** → serve/{pkg}/README.md, etc.)
2. 4-item checklist: README Verification, External Attribution, Research Doc, Deletion Detection — no diagram items
3. Verification layers section: Layer 1 (grep for removed symbols) + Layer 2 (LLM full-file editorial read)
4. TODO marker format and insertion rules: `> **TODO:** {category} — {description} [#{id}]` with categories stale|inaccurate|missing|unverified
5. Gate-blocking rules: unverified on task-introduced content blocks; unverified on pre-existing passes
6. No-impact fast path: if changed files map to no READMEs, advance with evidence
7. Attribution rules for task-caused (fix inline) vs pre-existing (TODO marker)

**In scope:** SKILL.md content only. Must pass test assertions from #1422.
**Out of scope:** Agent file changes (#1424), prompt file changes (#1425).

Brief: see parent #1421