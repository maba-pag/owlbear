---
id: 702
title: 'Research: Audit GCP generative-ai repo for other reusable patterns (2025+)'
status: backlog
priority: important
created: 2026-03-08T18:40:33.5940382+01:00
updated: 2026-03-10T02:44:18.4067137+01:00
started: 2026-03-09T23:04:28.1434718+01:00
tags:
    - research
    - phase-research
    - scope:core
    - agent
class: standard
---

## Goal
Scan the broader GoogleCloudPlatform/generative-ai repo for other patterns, tools, or architectures that OwlBear could benefit from  but ONLY content from 2025-2026. The repo contains a mix of very recent and 2+ year old content; anything pre-2025 is likely outdated for our stack (March 2026).

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
- [ ] Repo cloned to docs/research/generative-ai/ (shared with task #700)
- [ ] Directory-level inventory with last-commit dates for relevant sections
- [ ] Shortlist of 2025+ patterns worth adopting (minimum: comparison table)
- [ ] For each shortlisted pattern: feasibility note and adaptation cost
- [ ] Research doc at docs/gcp-generative-ai-audit-research.md
- [ ] Follow-up kanban tasks for any patterns worth pursuing

[[2026-03-10]] Tue 02:44
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Repo cloned to docs/research/generative-ai/ | Path violates project convention (`docs/scratch/research/` per copilot-instructions.md). Moot now  research is complete, clone is ephemeral. | Fix path in AC to `docs/scratch/research/generative-ai/` |
| 2. Directory-level inventory with last-commit dates | Present in research doc §3  clear table with freshness flags. | None  verifiable |
| 3. Shortlist of 2025+ patterns (comparison table) | Present in §4.1  7-row comparison table with verdicts and confidence scores. | None  verifiable |
| 4. Feasibility note and adaptation cost per shortlisted pattern | Present in §4.3-4.4  adaptation path table with GCP-to-OwlBear mapping, cost estimate (~200 LOC). | None  verifiable |
| 5. Research doc at docs/gcp-generative-ai-audit-research.md | File exists, well-structured, status marked Complete. | None  verifiable |
| 6. Follow-up kanban tasks for any patterns worth pursuing | **NOT MET.** kanban-md create commands are documented in §6 of the research doc but were never executed. Zero `evaluation` tagged tasks on the board. | Researcher must execute the two `kanban-md create` commands from §6 |

### Architecture Notes
Research quality is strong. The freshness filter (2025+ only), systematic directory inventory, and SKIP rationale for Gemini-locked patterns are well-reasoned. The recommendation to adapt the agent behavioral eval pattern (not the Gemini SDK) is architecturally sound  it fills a real gap (no agent tool-selection testing) without adding vendor lock-in.

Note: #700 (always-on-memory-agent research) is still in `backlog`, but the research doc explicitly scopes #702 to exclude that subdirectory. No true dependency conflict.

### Changes Made
- No kanban edits yet  refinement needed from researcher.

### Dependencies
- #700 (GCP always-on-memory-agent): in backlog, no blocking dependency  #702 explicitly defers that subdirectory to #700.
- Follow-up tasks (not yet created): will depend on nothing in the current pipeline.
