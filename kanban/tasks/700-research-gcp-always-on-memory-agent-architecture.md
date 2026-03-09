---
id: 700
title: 'Research: GCP always-on-memory-agent architecture'
status: ideation
priority: important
created: 2026-03-08T18:40:03.8314136+01:00
updated: 2026-03-08T18:40:03.8314136+01:00
tags:
    - research
    - phase-research
    - scope:core
    - memory
    - knowledge
class: standard
---

## Goal
Analyze the gemini/agents/always-on-memory-agent section of GoogleCloudPlatform/generative-ai repo.

## Research Checklist

1. **Theoretical validity** - What is the always-on memory agent pattern? How does it maintain persistent memory across sessions? What abstractions does it use (memory layers, summarization, retrieval)?
2. **Prior art** - Clone the repo into docs/research/generative-ai/. Study the always-on-memory-agent code, architecture, and design docs. Note when this code was last updated (freshness check).
3. **Technical feasibility** - Could we adopt this pattern directly in Python 3.12 + PydanticAI? What Gemini-specific pieces would need replacement? Any hard dependencies on Google Cloud services?
4. **Architecture fit** - How does this compare to OwlBear's current knowledge layer (SQLite graph + Qdrant vectors + BGE-M3)? Is it a replacement, complement, or orthogonal concept?
5. **Implementation approach** - Document concrete integration paths: (a) use directly, (b) adapt as inspiration for new functionality, (c) integrate into existing memory/knowledge system with RAG/graph.

## Acceptance Criteria
- [ ] Repo cloned to docs/research/generative-ai/ and always-on-memory-agent code reviewed
- [ ] Architecture diagram or summary of the memory agent's design
- [ ] Freshness assessment: when was this code written/updated?
- [ ] Comparison table: always-on-memory-agent vs OwlBear knowledge layer
- [ ] Concrete recommendation: use directly / adapt / integrate / skip
- [ ] Research doc at docs/gcp-always-on-memory-agent-research.md
- [ ] Follow-up kanban tasks created for any recommended actions
