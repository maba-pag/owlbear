# Context — Decision Request Data Model

## Problem

Decision requests store meaning in unstructured markdown body text. Three consumers need richer structure:
- **Agents creating requests** — need to express intent (kind, options, confidence) without crafting prose
- **Cockpit rendering resolvers** — needs to render adapted controls from data, not body-text heuristics
- **Agents consuming answers** — need machine-readable resolution (selected_option_id, not prose scraping)

## Project Type

`existing-feature/refactor` — extends the existing DR system across four layers.

## Scope

Full cross-layer: storage format → kanban engine API → MCP tools → Cockpit frontend → agent instructions.

## Key Constraints

- **No backward compatibility required.** Clean break; old files don't need migration.
- **No external direct readers.** All consumption mediated by engine.
- **Storage format:** YAML frontmatter (structured) + markdown body. Human-readable.
- **Clone = install** — plain text files, no database.
- **Multiple requests per task:** Sequential safe; parallel allowed but blocking semantics unspecified.
- **Request ID:** UUID4, canonical identity (reuse memory engine pattern).
- **Single unified data model** for both kinds across the full lifecycle.

## Expectation Signal

### Promise

A real choice system. Agents create structured requests with options. Cockpit renders adapted controls (option cards, done/blocked, free text). Users select without typing. Resolution flows back mechanically (task body + unblock).

### First Useful Step

Data model + engine + MCP/API interfaces. **Remaining:** Cockpit resolver UI, Cockpit list rendering from structured fields, agent instruction updates.

### Technically Wrong

Model exists but Cockpit still renders raw text; options exist but free text blocked; resolution doesn't flow back; regex extraction anywhere; consumers use internal interfaces; dead/missing API fields; agent instructions outdated.

## Active Tensions for Phase 2

- `kind` enum: 2 values confirmed (decision + action). Does `kind` add anything over option-presence detection alone? (Answer: yes — action requests have different resolution semantics.)
- Filename: UUID4-as-filename vs task-id-prefixed with UUID in frontmatter.
- Sweep vs inline resolution: keep batch sweep as manual-edit escape hatch, or fully replace?
- Action resolution states: what structured states beyond the decision-like flow?
- MCP resolve tool: should agents be able to resolve requests, or only humans?

## Investment Tier

Shared — full panel, research bridge required, complete Brief.
