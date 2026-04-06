# Rename Kanban Status "ideation" → "research"

> **Owning task:** #641 — P4-01: Rename kanban status "ideation" to "research"
> **Date:** 2026-04-06 **Status:** Complete

## 1. Context and Question

Phase-4 prerequisite #1 (thinking-companion-framework spec, Section 13): the term "ideation" must be freed for the new ideator agent. "research" more accurately describes what the researcher agent does at this pipeline stage.

**Question:** What is the full blast radius of renaming the `ideation` kanban status to `research`, and what is the safest implementation approach?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|---------------|
| 1 | `.owlbear/kanban/config.yml` | 1.0 | Status definition, default status |
| 2 | `serve/mcp-kanban/src/.../server.py` | 1.0 | Hardcoded `_STATUSES`, `_PICK_STATUS_RANK`, `move_to` default |
| 3 | `serve/orchestrator/src/.../selector.py` | 1.0 | `STATUS_RANK`, `STATUS_AGENT_MAP`, `_TARGET_STATUS` |
| 4 | `serve/orchestrator/src/.../gates.py` | 0.8 | Comment reference, `_NON_IMPL_TAGS` uses "research" as tag |
| 5 | `.owlbear/research/thinking-companion-framework.md` §13 | 0.9 | Rationale for rename |
| 6 | Codebase-wide grep for "ideation" | 1.0 | 330+ references across all file types |

## 3. Analysis

### Blast Radius by Category

| Category | Files | References | Breaking if missed? |
|----------|-------|------------|---------------------|
| Config (main + seed) | 2 | 4 | **Yes** — CLI reads statuses from here |
| Python source (server.py) | 1 | 3 locations | **Yes** — enum schema, rank map, default param |
| Python source (selector.py) | 1 | 4 locations | **Yes** — rank, agent map, target status |
| Python source (gates.py) | 1 | 1 comment | No — prose only |
| Agent `.agent.md` files | 3 | ~10 | **Partial** — agents mis-route if not updated |
| Skill `SKILL.md` files | 12+ | ~30 | **Partial** — instructions say wrong status |
| Instruction `.instructions.md` | 1 | 1 | **Partial** — pipeline diagram |
| Test files | 10+ | ~40 | **Yes** — assertions fail |
| Research/decision/task docs | 50+ | 150+ | No — historical prose |

### Risk: Tag Collision

"research" already exists as a **tag** in `_NON_IMPL_TAGS` (gates.py L23, server.py L533). Tags and statuses occupy separate namespaces — no technical conflict. A task could have `status: research` and tag `research` simultaneously. Semantically acceptable; both refer to the research phase.

### Risk: Migration Ordering

The rename must follow this sequence:
1. Update `config.yml` (statuses + default)
2. Migrate existing task files (`status: ideation` → `status: research`)
3. Update Python source (hardcoded lists + defaults)
4. Update tests
5. Update agent/skill/instruction prose

If step 3 runs before step 1, the MCP server's lifespan loader reads the old config and the hardcoded list disagrees. If step 2 runs before step 1, kanban-md rejects the unknown status. **Sequence is critical.**

### Implementation Approach

| Approach | Pros | Cons | Score |
|----------|------|------|-------|
| A: Single atomic commit | No intermediate broken state | Large diff, harder to review | 0.75 |
| B: Phased (config → code → docs) | Easier review per phase | Intermediate state may break tests | 0.60 |
| **C: Two phases (functional + prose)** | Functional changes atomic; prose update separate | Slight delay on prose alignment | **0.85** |

**(rec:) Approach C** — one task for all functional changes (config, Python, tests, agent/skill files), one follow-up task for historical prose in research/decision/task docs.

## 4. Recommendation

Advance #641 to backlog as the primary implementation task covering all functional changes. Create one follow-up task for prose cleanup in historical documents.

**Confidence: 0.88** — straightforward rename, well-defined blast radius, no architectural risk.

Challenge: FALLBACK — challenger subagent not invoked (trivial config rename, no design alternatives to challenge).

## 5. Follow-up Tasks

- **#641** (existing) → backlog: all functional changes (config, Python, tests, agents, skills, instructions)
- **New task** → ideation: update historical prose references in `.owlbear/research/`, `.owlbear/decisions/`, task body files
