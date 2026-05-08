---
id: 1424
title: 'P1-03: Update doc-writer.agent.md — remove diagram responsibility'
status: research
priority: important
created: 2026-05-08T00:32:21.566488+00:00
updated: 2026-05-08T00:41:32.343802+00:00
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

Update `share/agents/doc-writer.agent.md`:

1. Remove all references to diagrams, Excalidraw, `.excalidraw` files from persona, critical_rules, and any other sections
2. Align critical_rules with new w-doc-update behavior (4-item checklist, convention mapping, TODO markers)
3. Persona remains focused on fact-checking/verification identity — no diagram editor role
4. No functional regressions: tools list, pipeline_position, agents section, output_format remain structurally intact

**In scope:** Agent definition file only. Must pass assertions from #1422.
**Out of scope:** Skill rewrite (#1423), prompt revision (#1425).

Brief: see parent #1421


**AC #2 clarification:** "Align critical_rules" means: rules must reference the 4-item checklist (README Verification, External Attribution, Research Doc, Deletion Detection), convention-based mapping, TODO marker insertion, and gate-blocking on unverified task content. No diagram/excalidraw language may remain anywhere in the file.