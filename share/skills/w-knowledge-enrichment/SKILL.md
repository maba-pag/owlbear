---
name: w-knowledge-enrichment
description: "Workflow: Knowledge enrichment — extract entities and relationships from ingested documents"
user-invocable: true
---

# Knowledge Enrichment

Process pending knowledge chunks through two enrichment phases: Phase 1 extracts entities and intra-document edges from individual chunks; Phase 2 discovers cross-source relationships between entities that share names across different knowledge sources.

## Overview

The knowledge system stores ingested documents as chunks in SQLite, with a Qdrant vector index for retrieval. Enrichment builds the knowledge graph on top of this by:

1. **Phase 1 — Intra-document extraction**: Read each chunk, identify entities (people, systems, processes, concepts, roles, teams, tools) and relationships between them within the same document.
2. **Phase 2 — Cross-source consolidation**: Find entities with matching names across different knowledge sources and establish edges linking them.

Both phases are agent-driven: the MCP server provides batching and persistence tools, but the actual extraction logic runs in the agent's context.

## MCP Tools

All enrichment operations use the `ob-knowledge` MCP server tools:

| Tool | Purpose |
|------|---------|
| `get_stats` | Check enrichment pipeline status — chunks pending, enriched, consolidation candidates |
| `get_next_batch` | Claim up to N pending chunks for Phase 1 enrichment (returns chunk text + metadata) |
| `store_enrichment` | Persist extracted entities and edges for a chunk (Phase 1) or consolidation candidate (Phase 2) |
| `get_consolidation_candidates` | Retrieve cross-source entity pairs for Phase 2 |

## Step 1 — Assess Pipeline Status

Call `get_stats` to understand the current state:

- `chunks_pending_enrichment`: Number of chunks waiting for Phase 1
- `chunks_enriched`: Number of chunks already processed
- `consolidation_candidates_remaining`: Number of cross-source pairs waiting for Phase 2

If no chunks are pending and no consolidation candidates exist, enrichment is complete.

## Step 2 — Phase 1: Entity and Edge Extraction

Process chunks in batches of 5–10 using `get_next_batch`.

For each chunk in the batch:

### 2a — Read the Chunk

Each chunk includes:

- `chunk_id`: Unique identifier (use this when storing results)
- `text`: The chunk content
- `doc_title`: Parent document title
- `section_path`: Section heading hierarchy (if available)
- `source_name`: Knowledge source name
- `document_id`: Parent document ID
- `source_id`: Knowledge source ID

### 2b — Extract Entities

Identify significant entities mentioned in the chunk text. Each entity needs:

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Canonical name (consistent across chunks) | "Azure DevOps", "CI/CD Pipeline" |
| `entity_type` | Category | concept, system, process, person, role, team, tool, policy, standard |
| `description` | One-sentence description from context | "Organization's primary source control and work tracking platform" |
| `importance` | 0.0–1.0 weight | 0.9 for core domain concepts, 0.3 for passing mentions |

**Entity quality rules:**

- Normalize names: "Azure DevOps Server" and "AzDO" should both map to "Azure DevOps"
- Skip generic terms that aren't domain-meaningful: "the system", "this document", "the user"
- Prefer the most specific name available: "JIRA Service Desk" over "ticketing system"
- Set importance based on how central the entity is to the chunk's topic (mentioned once in passing = 0.2, central topic = 0.8+)

### 2c — Extract Edges

Identify relationships between entities found in the same chunk:

| Field | Description | Example |
|-------|-------------|---------|
| `source_name` | Entity name (source end) | "CI/CD Pipeline" |
| `target_name` | Entity name (target end) | "Azure DevOps" |
| `relation` | Relationship type | "runs_on", "depends_on", "manages", "implements", "part_of" |
| `weight` | Confidence 0.0–1.0 | 0.8 for explicitly stated, 0.4 for inferred |
| `properties` | Additional context | `{"context": "Pipeline defined in AzDO YAML"}` |

**Edge quality rules:**

- Only create edges between entities in the SAME chunk (cross-chunk edges are Phase 2)
- Use specific relation types from `h-knowledge-ops` Domain Reference, not generic "related_to"
- Weight reflects how explicitly the relationship is stated in the text

### 2d — Store Results

Call `store_enrichment` with the chunk_id, entities list, and edges list:

```
store_enrichment(
    chunk_id="<chunk_id>",
    entities=[
        {"name": "Azure DevOps", "entity_type": "system", "description": "...", "importance": 0.8},
        ...
    ],
    edges=[
        {"source_name": "Azure DevOps", "target_name": "CI/CD Pipeline", "relation": "hosts", "weight": 0.7},
        ...
    ]
)
```

Repeat for all chunks in the batch, then call `get_next_batch` for the next batch.

## Step 3 — Phase 2: Cross-Source Consolidation

After Phase 1 is complete (no more pending chunks), process consolidation candidates.

Call `get_consolidation_candidates` to get pairs of entities with the same name from different knowledge sources.

For each candidate:

### 3a — Evaluate the Pair

Each candidate includes:

- `candidate_id`: Opaque identifier for this pair
- `entity_name`: The shared entity name
- `source_a` / `source_b`: The two knowledge source IDs
- `source_a_name` / `source_b_name`: Human-readable source names
- `source_a_chunk` / `source_b_chunk`: Context text from each source

### 3b — Decide and Store

Read both context chunks. Determine if the entities refer to the same real-world concept:

- **Same entity**: Create a "same_as" edge with high weight
- **Related but distinct**: Create an appropriate edge ("extends", "replaces", "similar_to") with moderate weight
- **Unrelated homonyms**: Create no edges — store an empty edges list to mark the candidate as reviewed

```
store_enrichment(
    candidate_id="<candidate_id>",
    edges=[
        {"source_id": "<entity_id_a>", "target_id": "<entity_id_b>", "relation": "same_as", "weight": 0.9}
    ]
)
```

## Step 4 — Verify

Call `get_stats` again. Confirm:

- `chunks_pending_enrichment` is 0
- `consolidation_candidates_remaining` is 0

## Batch Size Guidance

| Document count | Phase 1 batch size | Reason |
|----------------|-------------------|--------|
| 1–5 documents | 10 chunks/batch | Small corpus, process quickly |
| 5–20 documents | 5 chunks/batch | Balance thoroughness with progress |
| 20+ documents | 5 chunks/batch | Prevent context overflow; many entities to track |

## Known Pitfalls

- **Entity name drift**: Same concept gets different names across batches. Before extracting, review recently stored entities (visible in prior batch results) and reuse canonical names.
- **Over-extraction**: Not every noun is a meaningful entity. Skip generic terms and focus on domain-specific concepts that would help an agent answer questions.
- **Stale claims**: If enrichment is interrupted, claimed chunks become stale after 10 minutes and are automatically reclaimed by the next `get_next_batch` call.
- **Empty chunks**: Some chunks may contain only boilerplate (headers, footers, navigation). Store an empty entities/edges list to mark them as enriched rather than leaving them pending.
