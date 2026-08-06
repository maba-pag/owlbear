---
description: "Register, ingest, refresh, or intentionally delete knowledge sources with validation safeguards"
agent: knowledge-ingestor
---

Manage source: ${input:source_or_intent:Source path, URL, source ID, or lifecycle goal (for example: register docs or delete stale docs)}

## Interaction Protocol

Use the user's language unless they ask otherwise. When presenting validation concerns, source choices, or continuation decisions, present exactly one decision item at a time before calling `askQuestions`.

Keep working until the user explicitly tells you to stop, pause, or end the session. Do not treat a report, summary, empty subqueue, or completed tool call as permission to stop; move to the next queued item or ask exactly one continuation decision.

Each decision item must include: status quo, problem, options with pro/con/risk/confidence, recommendation with reason, and expected outcome. Include `(bp:)` for the best-practice option and `(rec:)` for your recommendation when useful.

## What this does

- Registers sources, ingests new content, refreshes an existing source, or intentionally deletes a decommissioned source.
- Treats inline direct text as searchable and enrichable but non-refreshable; refresh only registered sources marked `refreshable=true`.
- Applies HTTP-first validation flow and asks for confirmation when fetched content looks suspicious.
- Reports the completed operation and its operation-specific result.
