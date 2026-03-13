---
id: 702
title: 'Research: Audit GCP generative-ai repo for other reusable patterns (2025+)'
status: todo
priority: important
created: 2026-03-08T18:40:33.5940382+01:00
updated: 2026-03-10T17:30:37.2851809+01:00
started: 2026-03-09T23:04:28.1434718+01:00
tags:
    - research
    - phase-research
    - scope:core
    - agent
claimed_by: test-writer
claimed_at: 2026-03-10T17:30:37.2851809+01:00
class: standard
---

## Goal
Scan the broader GoogleCloudPlatform/generative-ai repo for other patterns, tools, or architectures that OwlBear could benefit from -- but ONLY content from 2025-2026. The repo contains a mix of very recent and 2+ year old content; anything pre-2025 is likely outdated for our stack (March 2026).

## Research Checklist

1. **Theoretical validity** - What categories of content does the repo contain? (agents, RAG, function calling, multimodal, safety, evaluation, etc.)
2. **Prior art** - Identify sections/examples updated in 2025-2026 by checking git blame/log dates. Focus on gemini/agents/, gemini/function-calling/, and any evaluation or safety tooling.
3. **Technical feasibility** - For each promising find: is it Gemini-locked or model-agnostic? Could it work with our Copilot OAuth + PydanticAI stack?
4. **Architecture fit** - Would any of these patterns fill gaps in OwlBear's current capabilities (approval gates, tool use, evaluation, safety)?
5. **Implementation approach** - For each candidate, note: use directly / adapt / skip, with rationale.

## Freshness Filter
- Check commit dates with git log. SKIP anything last touched before 2025-01-01.
- Note: the repo is large. Focus on directories that look relevant to our agent/memory/tool/safety concerns.

## Acceptance Criteria
- [x] Repo cloned to docs/scratch/research/generative-ai/ (ephemeral, shared with #700)
- [x] Directory-level inventory with last-commit dates for relevant sections
- [x] Shortlist of 2025+ patterns worth adopting (comparison table)
- [x] For each shortlisted pattern: feasibility note and adaptation cost
- [x] Research doc at docs/research/gcp-generative-ai-audit-research.md
- [x] Follow-up kanban tasks for patterns worth pursuing: #719, #720

[[2026-03-10]] Tue 17:11
## Architecture Review (2nd pass)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Repo cloned to docs/scratch/research/ | Ephemeral artifact, gitignored. Path corrected from docs/research/ to docs/scratch/research/ per convention. | FIXED path in AC |
| 2. Directory inventory with dates | Present in research doc section 3: 8-row table with freshness flags. | MET |
| 3. Shortlist comparison table | Present in section 4.1: 7-row table with verdicts and confidence scores. | MET |
| 4. Feasibility + adaptation cost | Present in section 4.3-4.4: adaptation path table, ~200 LOC estimate. | MET |
| 5. Research doc | Exists at docs/research/gcp-generative-ai-audit-research.md. Fixed path in AC (was docs/gcp-...). | FIXED path in AC |
| 6. Follow-up kanban tasks | Previously NOT MET. Created #719 (eval harness) and #720 (eval dataset) per section 6 spec. | FIXED -- tasks created |

### Architecture Notes
- Research quality is strong (.80 confidence). Freshness filter (2025+ only) is well-applied.
- SKIP rationale for 5 of 7 patterns is sound: existing OwlBear capabilities cover them.
- ADAPT recommendation for agent behavioral eval is architecturally valid: fills a real gap (no tool-selection testing) without vendor lock-in.
- Attribution verified in docs/sources/overview.md (3 entries under section 702).
- No code, no module layering concerns. TDD not applicable (research task).

### Changes Made
- Created #719: Design agent tool-trajectory evaluation harness (backlog, nice-to-have)
- Created #720: Create eval dataset: orchestrator routing test cases (backlog, nice-to-have, depends_on #719)
- Fixed AC #1 path: docs/research/ -> docs/scratch/research/ (convention)
- Fixed AC #5 path: docs/gcp-... -> docs/research/gcp-... (actual location)
- Marked all 6 ACs as complete

### Dependencies
- #700 (always-on-memory-agent research): no blocking dependency, #702 explicitly defers that directory.
- Created: #719, #720 (follow-up evaluation tasks, both at backlog).
