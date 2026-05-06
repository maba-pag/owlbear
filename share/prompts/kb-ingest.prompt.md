---
description: "Ingest or refresh knowledge sources with validation safeguards"
agent: knowledge-ingestor
---

Ingest: ${input:source_or_intent:Source path, URL, or short ingest goal (for example: refresh stale docs)}

## What this does

- Ingests new content or refreshes an existing source.
- Applies HTTP-first validation flow and asks for confirmation when fetched content looks suspicious.
- Reports knowledge-base status so you can decide whether to start enrichment.
