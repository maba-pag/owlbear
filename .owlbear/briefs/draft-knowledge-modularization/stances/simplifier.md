# Simplifier Stance — Knowledge Module Modularization

## Cuts and Decompositions

### 1. Kill the spec document as a standalone artifact

The pain is interface instability causing cascading rework, not missing requirements documentation. Replace the proposed "design specification document" with **typed Protocol contracts at the 3 boundaries that actually cascade**: retrieval, ingest, enrich. Protocols ARE the spec — they're testable, enforceable, and live in code.

**Risk of ignoring:** The spec becomes another stale artifact that drifts from code, adding maintenance cost without preventing the underlying problem.

### 2. Slice the engine "first useful step" thinner

"Engine layer as first step" encompasses 6 stages and ~25 modules. That's the entire system minus transport — it IS the monolith with a different name. Decompose into 3 independently-lockable contract sets:

- **Retrieval contract** (query → results): what goes in, what comes out, what guarantees
- **Ingest contract** (source → stored chunks + embeddings): what goes in, what's persisted, what can fail
- **Enrich contract** (stored chunks → entities + edges): what triggers it, what it produces, what it claims

Each can be validated independently. Each has a clear "before" and "after" state.

### 3. Drop the 5-actor model

Five named actors (consumer, ingestor, enricher, human, cockpit) add naming ceremony over what is operationally 3 operations:
- **Read** (consumer agent + cockpit both just query)
- **Write** (ingestor does it, human triggers it)
- **Enrich** (enricher does it, human triggers it)

The MCP tools already ARE the actor interfaces. Don't create a meta-layer above them.

### 4. Don't sequence what's parallel

The proposed delivery sequence (engine → MCP → agents → cockpit API → cockpit UI) assumes serial dependencies. But:
- Retrieval contract is independent of ingest contract
- MCP is thin on top of each contract
- Cockpit reads the same data MCP does

Lock contracts simultaneously, build surfaces in parallel.

## Summary Recommendation

Replace "write a big spec" with "define 3 Protocol classes (retrieve, ingest, enrich), validate those against real agent usage, and treat the protocols as the living spec."
