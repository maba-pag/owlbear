---
name: w-knowledge-enrichment
description: "Workflow: Knowledge enrichment — extract entities and relationships from ingested documents"
user-invocable: true
---

# Knowledge Enrichment

Process pending knowledge chunks through entity and relation extraction. The enrichment worker reads each chunk, identifies entities (people, systems, processes, concepts, roles, teams, tools) and relationships between them, then persists the graph data.

## Overview

The knowledge system stores ingested documents as chunks in SQLite, with a Qdrant vector index for retrieval. Enrichment builds the knowledge graph on top of this by extracting entities and intra-document edges from individual chunks.

The extraction is agent-driven: the MCP server provides batching and persistence tools, but the actual extraction logic runs in the agent's context.

## MCP Tools

All enrichment operations use the `ob-knowledge` MCP server tools:

| Tool | Purpose |
|------|---------|
| `knowledge_stats` | Check enrichment pipeline status — chunks pending, enriched, failed |
| `knowledge_enrichment_claim_batch` | Claim up to N pending chunks for enrichment (returns chunk text + metadata) |
| `knowledge_enrichment_retry` | Reset failed chunks to pending after correcting the cause |
| `knowledge_enrichment_store` | Persist extracted entities and edges for a chunk |

## Step 1 — Assess Pipeline Status

Call `knowledge_stats` to understand the current state:

- `chunks_claimable`: Number of pending or stale-claimed chunks currently claimable
- `chunks_pending`: Number of chunks waiting for enrichment
- `chunks_claimed`: Number of chunks currently leased by workers
- `chunks_failed`: Number of chunks that failed and require review/reset
- `chunks_enriched`: Number of chunks already processed

If `chunks_failed` is non-zero, inspect the failure cause before retrying. If no chunks are claimable or failed, enrichment is complete.

## Step 2 — Entity and Edge Extraction

Process chunks in batches of 5–10 using `knowledge_enrichment_claim_batch`.

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
- `scope`: Knowledge scope
- `claim_token`: Lease token for this batch claim; required when storing results
- `claimed_at`: Lease timestamp

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

Call `knowledge_enrichment_store` with the chunk_id, entities list, and edges list:

```
knowledge_enrichment_store(
    chunk_id="<chunk_id>",
    claim_token="<claim_token>",
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

Repeat for all chunks in the batch, pairing each `chunk_id` with the exact `claim_token` returned by `knowledge_enrichment_claim_batch`, then call `knowledge_enrichment_claim_batch` for the next batch. If a store call fails for the current claim, the server records diagnostics and moves that chunk to `failed`; correct the payload/extractor issue before calling `knowledge_enrichment_retry`.

## Step 3 — Verify

Call `knowledge_stats` again. Confirm:

- `chunks_pending` is 0
- `chunks_claimable` is 0
- `chunks_failed` is 0, or failures are intentionally deferred with a recorded reason

## Batch Size Guidance

| Document count | Phase 1 batch size | Reason |
|----------------|-------------------|--------|
| 1–5 documents | 10 chunks/batch | Small corpus, process quickly |
| 5–20 documents | 5 chunks/batch | Balance thoroughness with progress |
| 20+ documents | 5 chunks/batch | Prevent context overflow; many entities to track |

## Known Pitfalls

- **Entity name drift**: Same concept gets different names across batches. Before extracting, review recently stored entities (visible in prior batch results) and reuse canonical names.
- **Over-extraction**: Not every noun is a meaningful entity. Skip generic terms and focus on domain-specific concepts that would help an agent answer questions.
- **Stale claims**: If enrichment is interrupted, claimed chunks become stale after 10 minutes and are automatically reclaimed by the next `knowledge_enrichment_claim_batch` call.
- **Lease tokens**: Store every Phase 1 chunk with the `claim_token` returned by `knowledge_enrichment_claim_batch`. Missing or stale tokens are rejected so parallel workers cannot overwrite one another.
- **Failed chunks**: Failed Phase 1 writes stay in `failed` until `knowledge_enrichment_retry` resets them. Do not blindly reset; fix the cause first.
- **Empty chunks**: Some chunks may contain only boilerplate (headers, footers, navigation). Store an empty entities/edges list to mark them as enriched rather than leaving them pending.
