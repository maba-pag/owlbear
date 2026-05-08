---
id: 1422
title: 'P1-01: Test — verify doc-writer quality redesign AC'
status: research
priority: needed
created: 2026-05-08T00:32:15.467895+00:00
updated: 2026-05-08T00:32:58.317792+00:00
tags:
- phase-1
- scope:shared
- brief:doc-writer-quality
parent: 1421
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

Write `tests/test_doc_writer_quality_1422.py` — a pytest suite that verifies all 5 AC items from the brief:

1. `w-doc-update/SKILL.md` contains: convention mapping table (serve/{pkg} → README pattern), 4-item checklist with NO diagram items, verification procedure section with grep + LLM editorial layers, TODO marker insertion rules with visible blockquote format, gate-blocking rule distinguishing task-content vs pre-existing
2. `doc-writer.agent.md` contains NO references to diagrams, Excalidraw, or `.excalidraw` files
3. `doc-audit.prompt.md` includes: TODO marker batch resolution dimension, diagram ownership section, `describes`-based diagram verification
4. No references to old "item 5" or "item 6" (diagram maintenance/creation) remain in w-doc-update
5. TODO marker format grep pattern works: `> **TODO:** {category} — {description} [#{id}]`

**In scope:** Test file only. File-content assertions using `pathlib.Path.read_text()` and regex/string matching.
**Out of scope:** Implementing the actual skill/agent/prompt changes (that is #1423–#1425).

Brief: see parent #1421