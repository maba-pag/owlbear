---
name: w-knowledge-enrichment
description: "Workflow: Knowledge enrichment — extract entities and relationships from ingested documents"
user-invocable: true
---

# Knowledge Enrichment

Process pending knowledge chunks through entity and relation extraction. The enrichment worker reads each chunk, identifies entities such as people, technologies, processes, concepts, organizations, and tools, then persists source-grounded relationships between them.

## Overview

The knowledge system stores ingested documents as chunks in SQLite, with a Qdrant vector index for retrieval. Enrichment builds the knowledge graph on top of this by extracting entities and intra-document edges from individual chunks.

The extraction is agent-driven: the MCP server provides batching and persistence tools, but the actual extraction logic runs in the agent's context.

## MCP Tools

All enrichment operations use the `ob-knowledge` MCP server tools:

| Tool | Purpose |
|------|---------|
| `knowledge_stats` | Check enrichment pipeline status — chunks pending, enriched, failed |
| `claim_enrichment_batch` | Claim up to N pending chunks for enrichment (returns chunk text + metadata) |
| `retry_enrichment` | Reset failed chunks to pending after correcting the cause |
| `store_enrichment` | Persist extracted entities and edges for a chunk |

## Step 1 — Assess Pipeline Status

Call `knowledge_stats` to understand the current state:

- `chunks_claimable`: Number of pending or stale-claimed chunks currently claimable
- `chunks_pending`: Number of chunks waiting for enrichment
- `chunks_claimed`: Number of chunks currently leased by workers
- `chunks_failed`: Number of chunks that failed and require review/reset
- `chunks_enriched`: Number of chunks already processed

If `chunks_failed` is non-zero, inspect the failure cause before retrying. If no chunks are claimable or failed, enrichment is complete.

## Step 2 — Entity and Edge Extraction

Process chunks in batches of 5–10 using `claim_enrichment_batch`.

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
- `claim_token`: Batch correlation identifier returned by the current server; it is informational and does not fence writes
- `claimed_at`: Lease timestamp

### 2b — Extract Entities

Identify significant entities mentioned in the chunk text. Each entity needs:

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Stable local reference within this chunk payload | `azure-devops` |
| `name` | Canonical name (consistent across chunks) | "Azure DevOps", "CI/CD Pipeline" |
| `entity_type` | Category | concept, document, event, location, metric, organization, person, process, product, standard, technology, tool |
| `description` | One-sentence description from context | "Organization's primary source control and work tracking platform" |
| `confidence` | Extraction confidence from 0.0–1.0 | 0.9 for explicit identification, 0.5 for inferred identity |
| `metadata` | Additional source-grounded context | `{"alias": "AzDO"}` |

**Entity quality rules:**

- Assign each entity a unique local `id`; edges in this payload refer to it
- Normalize names: "Azure DevOps Server" and "AzDO" should both map to "Azure DevOps"
- Skip generic terms that aren't domain-meaningful: "the system", "this document", "the user"
- Prefer the most specific name available: "JIRA Service Desk" over "ticketing system"
- Set confidence from the strength of the source evidence, not the entity's importance

### 2c — Extract Edges

Identify relationships between entities found in the same chunk:

| Field | Description | Example |
|-------|-------------|---------|
| `source_id` | Local `id` of the source entity in this payload | `ci-cd-pipeline` |
| `target_id` | Local `id` of the target entity in this payload | `azure-devops` |
| `relation` | Relationship type | "belongs_to", "depends_on", "manages", "implements", "requires" |
| `weight` | Relationship strength from 0.0–1.0 | 0.8 for a primary dependency, 0.4 for a weak association |
| `confidence` | Extraction confidence from 0.0–1.0 | 0.9 for explicit statements, 0.5 for inferred relationships |
| `metadata` | Additional source-grounded context | `{"context": "Pipeline defined in AzDO YAML"}` |

**Edge quality rules:**

- Only create edges between entities in the same chunk payload
- Resolve both endpoints through entity `id` values present in that payload
- Use specific relation types from `h-knowledge-ops` Domain Reference, not generic "related_to"
- Keep weight (relationship strength) distinct from confidence (evidence strength)

### 2d — Store Results

Call `store_enrichment` with the chunk_id, entities list, and edges list:

```
store_enrichment(
    chunk_id="<chunk_id>",
    entities=[
        {
            "id": "azure-devops",
            "name": "Azure DevOps",
            "entity_type": "technology",
            "description": "Source control and work tracking platform",
            "confidence": 0.9,
            "metadata": {"alias": "AzDO"},
        },
        {
            "id": "ci-cd-pipeline",
            "name": "CI/CD Pipeline",
            "entity_type": "process",
            "description": "Build and deployment pipeline hosted in Azure DevOps",
            "confidence": 0.9,
            "metadata": {},
        },
    ],
    edges=[
        {
            "source_id": "ci-cd-pipeline",
            "target_id": "azure-devops",
            "relation": "belongs_to",
            "weight": 0.7,
            "confidence": 0.9,
            "metadata": {},
        },
    ]
)
```

Repeat for all chunks in the batch, then call `claim_enrichment_batch` for the next batch. If a store call fails, the server records diagnostics and applies the queue retry policy; inspect `knowledge_stats`, correct the payload or extraction issue, and call `retry_enrichment` only when the chunk has reached `failed`.

## Step 3 — Verify

Call `knowledge_stats` again. Confirm:

- `chunks_pending` is 0
- `chunks_claimable` is 0
- `chunks_failed` is 0, or failures are intentionally deferred with a recorded reason

## Batch Size Guidance

| Document count | Batch size | Reason |
|----------------|-------------------|--------|
| 1–5 documents | 10 chunks/batch | Small corpus, process quickly |
| 5–20 documents | 5 chunks/batch | Balance thoroughness with progress |
| 20+ documents | 5 chunks/batch | Prevent context overflow; many entities to track |

## Known Pitfalls

- **Entity name drift**: Same concept gets different names across batches. Before extracting, review recently stored entities (visible in prior batch results) and reuse canonical names.
- **Over-extraction**: Not every noun is a meaningful entity. Skip generic terms and focus on domain-specific concepts that would help an agent answer questions.
- **Stale claims**: If enrichment is interrupted, claimed chunks become stale after 10 minutes and are automatically reclaimed by the next `claim_enrichment_batch` call.
- **Claim ownership**: `claim_token` is currently informational; `store_enrichment` does not validate it. Run one enrichment worker at a time so a stale claim cannot be reassigned while the original worker is still writing.
- **Failed chunks**: Chunks that exhaust the store retry policy stay in `failed` until `retry_enrichment` resets them. Do not blindly reset; fix the cause first.
- **Empty chunks**: Some chunks may contain only boilerplate (headers, footers, navigation). Store an empty entities/edges list to mark them as enriched rather than leaving them pending.
