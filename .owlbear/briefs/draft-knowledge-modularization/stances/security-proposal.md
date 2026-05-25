# Security Proposal — Knowledge Module Decomposition

## Design Summary

This proposal decomposes the knowledge subsystem along **trust boundaries** as the primary structural axis. The decomposition yields 6 engine modules plus a thin MCP interface layer, with explicit security contracts at each boundary crossing. The key insight: the system has exactly three trust transitions (external→validated, validated→persisted, persisted→served), and each transition maps to a module boundary with named validation responsibilities.

The design eliminates the current "god module" problem in `server.py` by enforcing that **no module above the engine layer may hold direct storage access**. All data access flows through typed protocol interfaces that enforce access scope at the type level.

---

## 1. Trust Boundary Map

```
┌─────────────────────────────────────────────────────────────────────┐
│ EXTERNAL (Untrusted Content, Trusted Auth)                          │
│   SharePoint, Confluence, Jira, PDS docs                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ TB1: Content Ingress
                             │ Validates: URL allowlist (SSRF), content sanitization,
                             │           size limits, content-type enforcement
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ BROWSER/AUTH ZONE (Highest Privilege)                                │
│   Edge CDP sessions, SSO tokens, Playwright automation              │
│   ISOLATED: no persistence, no content processing                   │
│   Output: raw content bytes + metadata (URL, timestamp, status)     │
└────────────────────────────┬────────────────────────────────────────┘
                             │ TB2: Auth → Processing Boundary
                             │ Validates: content received, auth tokens NOT forwarded,
                             │           content wrapped in safety envelope
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CONTENT PROCESSING ZONE (Medium Privilege — Write Path)             │
│   Chunking, embedding, entity extraction, sanitization              │
│   Input: sanitized content blobs                                    │
│   Output: validated domain objects (IngestResult, entities, edges)  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ TB3: Processing → Persistence Boundary
                             │ Validates: schema conformance, referential integrity,
                             │           source_id attribution, no raw HTML in store
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PERSISTENCE ZONE (Write-Restricted)                                 │
│   SQLite (metadata, graph), Qdrant (vectors)                        │
│   Write access: only via engine protocols                           │
│   Read access: only via QueryService protocol                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ TB4: Storage → Consumer Boundary
                             │ Validates: query scope enforcement, result sanitization,
                             │           provenance attribution, no source URLs in output
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CONSUMER ZONE (Read-Only)                                           │
│   MCP tools, Cockpit API, Agent queries                             │
│   Access: read-only query results with provenance                   │
│   MUST NOT: receive auth tokens, source credentials, raw URLs       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Classification

| Data Class | Sensitivity | Where It Lives | Who May Access | Retention |
|-----------|------------|----------------|----------------|-----------|
| **Auth sessions/tokens** | CRITICAL | Browser process memory only | Browser module only | Session-lived, never persisted |
| **Source URLs (internal infra)** | HIGH | Source registry (SQLite) | Ingestor, Refresh orchestrator | Until source removed |
| **Corporate content (raw)** | HIGH | Never persisted raw — only chunked/processed | Content processing zone | Transient (in-memory during processing) |
| **Processed chunks + embeddings** | MEDIUM-HIGH | SQLite + Qdrant (local) | Write: Ingestor/Enricher. Read: QueryService | Until source refreshed |
| **Entity/relationship graph** | MEDIUM | SQLite graph tables | Write: Enricher. Read: QueryService | Until enrichment re-run |
| **Source metadata (name, type, status)** | MEDIUM | Source registry | All engine modules, Cockpit (read-only) | Until source removed |
| **Query results** | MEDIUM | Transient (returned to agent) | Consumer agent, Cockpit | Not persisted separately |
| **Embeddings (vectors)** | LOW-MEDIUM | Qdrant (local) | QueryService only | Mirrors chunk lifecycle |

**Key constraint:** Auth tokens MUST NOT escape the browser module boundary. Source URLs SHOULD NOT appear in consumer-facing query results (use source _names_ and provenance references instead).

---

## 3. Module Decomposition (Security-Centric)

Six engine modules + one interface layer, cut along trust boundaries:

### Module 1: `source-registry`
**Responsibility:** Owns source definitions, health state, refresh scheduling.
**Trust level:** Medium (holds internal URLs).
**Boundary justification:** Source URLs are sensitive infrastructure data. Isolating them means the query path never touches URL storage directly.

### Module 2: `browser-auth` (existing `serve/browser/`)
**Responsibility:** Authenticated content fetching via Edge CDP.
**Trust level:** Critical (holds live auth sessions).
**Boundary justification:** Already isolated — the strongest boundary in the system. Content exits as sanitized bytes; auth tokens never leave.

### Module 3: `content-pipeline`
**Responsibility:** Intake validation, chunking, embedding generation, content sanitization.
**Trust level:** Medium-High (processes untrusted external content).
**Boundary justification:** This is where untrusted content becomes validated domain objects. Failure here means injection into persistence. Must be the strictest validation point.

### Module 4: `knowledge-graph`
**Responsibility:** Entity extraction, relationship mapping, consolidation, cross-source linking.
**Trust level:** Medium (operates on already-validated content).
**Boundary justification:** Enrichment is the least validated feature. Isolating it means a broken enricher cannot corrupt the content store — it can only produce bad entities that are separately queryable and deletable.

### Module 5: `persistence` (internal, not directly exposed)
**Responsibility:** SQLite schema management, Qdrant collection management, storage protocols.
**Trust level:** Low (passive storage, no business logic).
**Boundary justification:** Storage has no opinion about content. It enforces schema constraints but not business rules. Separating it means storage migrations don't cascade into processing logic.

### Module 6: `query-service`
**Responsibility:** Read-only retrieval, result composition, provenance attribution.
**Trust level:** Medium (serves external consumers, must sanitize output).
**Boundary justification:** The consumer-facing boundary. Must enforce: no source URLs in output, provenance attribution on every result, scope-limited queries.

### Interface Layer: `mcp-knowledge`
**Responsibility:** MCP tool definitions, request routing, DI composition.
**Trust level:** Low (thin routing, no business logic).
**Boundary justification:** MUST NOT contain domain logic, SQL, or direct storage access. Currently violates this (1100 LOC god module). Fixing this is the highest-priority security improvement.

---

## 4. Isolation Requirements

| Must Be Isolated From | Reason | Enforcement |
|----------------------|--------|-------------|
| `browser-auth` ↔ everything else | Auth token containment | Import boundary (separate package, no shared state) |
| Source URLs ↔ query results | Internal infrastructure exposure | QueryService protocol never returns URLs; uses source names |
| Raw external content ↔ persistence | Injection prevention | Content-pipeline validates before storage accepts |
| Enrichment ↔ content store | Blast radius of unvalidated feature | Knowledge-graph writes to separate tables; corruption doesn't affect chunk retrieval |
| MCP layer ↔ storage | Prevent god-module regression | No SQL imports in MCP package; engine protocols only |
| Write-path modules ↔ read-path modules | Principle of least privilege per actor | Ingestor never instantiates QueryService; consumer never instantiates pipeline |

---

## 5. Input Validation Boundaries

| Entry Point | What Enters | Validation Required | Validator |
|------------|------------|--------------------:|-----------|
| **Browser → Content-pipeline** | Raw HTML/JSON from corporate sources | Content-type check, size limit, encoding validation, HTML sanitization | `content_safety.py` (existing) |
| **Source config (YAML)** | Source definitions (URLs, types, scopes) | URL allowlist (`_ssrf.py`), schema validation, no path traversal in scope patterns | Source-registry module |
| **MCP tool calls (consumer)** | Query strings, scope filters, entity IDs | Input length limits, allowed characters, SQL injection prevention (parameterized only) | MCP layer + QueryService protocol |
| **MCP tool calls (ingestor)** | Source IDs, refresh triggers | Source ID existence check, human-trigger gate verification | MCP layer + source-registry protocol |
| **Cockpit API** | Read-only requests | No write mutation accepted, session validation | Cockpit routes (existing FastAPI) |
| **Enrichment input** | Chunks for entity extraction | Already-validated (from persistence); re-validate entity output schema | Knowledge-graph module |

---

## 6. Access Control Per Module

| Module | Consumer Agent | Ingestor Agent | Enricher Agent | Cockpit | Human |
|--------|:---:|:---:|:---:|:---:|:---:|
| source-registry | — | RW | R | R | RW |
| browser-auth | — | Invoke | — | — | Authenticate |
| content-pipeline | — | Invoke | — | — | Trigger |
| knowledge-graph | R (entities/edges) | — | RW | R | Full |
| persistence | — | — | — | — | Full (via tooling) |
| query-service | R | — | R | R | R |
| mcp-knowledge | R (5 query tools) | W (3 ingest tools) | W (3 enrichment tools) | — | Full |

**R** = read, **W** = write, **RW** = read+write, **Invoke** = can trigger execution, **—** = no access.

**Key enforcement:** The MCP layer presents different tool sets to different actors. Consumer agents see only query tools. Ingestor agents see ingest tools. This is enforced by tool registration (only expose relevant tools per MCP session), not by runtime auth checks — since all actors run locally as the same OS user.

---

## 7. Interface Contracts (Security Properties)

### TB1: External → Browser-Auth
| Property | Guarantee |
|----------|-----------|
| URL allowlist | Only pre-approved domains fetched (SSRF protection) |
| Auth containment | Tokens never serialized to disk or forwarded to content-pipeline |
| Timeout enforcement | Fetches timeout after configured limit (DoS protection against slow sources) |

### TB2: Browser-Auth → Content-Pipeline
| Property | Guarantee |
|----------|-----------|
| Content envelope | All content wrapped in `SafeContent` type (marks provenance, prevents raw use) |
| No auth leakage | Return type contains content bytes + metadata only; no cookies/tokens/headers |
| Size bound | Content larger than configured limit rejected before processing |

### TB3: Content-Pipeline → Persistence
| Property | Guarantee |
|----------|-----------|
| Schema conformance | Only typed domain objects (`IngestResult`, `ChunkRecord`, `Entity`, `Edge`) accepted |
| Parameterized storage | All SQL is parameterized; no string interpolation in queries |
| Referential integrity | Source ID must exist in registry before content stored against it |
| No raw HTML | Persistence layer rejects content containing unprocessed HTML tags |

### TB4: Persistence → Query-Service → Consumer
| Property | Guarantee |
|----------|-----------|
| Result sanitization | Query results contain text, provenance reference, confidence — never source URLs or internal IDs |
| Scope enforcement | Queries scoped to declared source scope; no cross-scope leakage |
| Provenance attribution | Every returned chunk carries source name + location reference |
| Injection resistance | Results are plain text; no executable content in responses |

### MCP Tool Contract
| Property | Guarantee |
|----------|-----------|
| No direct SQL | MCP layer calls engine protocols only; zero SQL imports |
| Input validation | All tool parameters validated against Pydantic models before engine dispatch |
| Error opacity | Internal errors returned as generic failure messages; no stack traces or SQL in error responses |

---

## 8. Content Safety Model

### Threat: Prompt Injection via Ingested Content

Corporate documents could contain text that, when retrieved and presented to an LLM agent, acts as a prompt injection.

**Mitigation:**
- Content stored as **attributed text blocks** with explicit provenance markers
- Query results wrapped in system-level framing: `"[Source: {name}, Section: {ref}]: {text}"`
- MCP tool responses include metadata that agents can use to distinguish retrieved content from instructions
- Content-pipeline strips known injection patterns during sanitization (defense-in-depth, not primary control)

### Threat: Cross-Source Contamination

Entity consolidation could merge entities from different sources incorrectly, creating false relationships.

**Mitigation:**
- Knowledge-graph maintains **source attribution on every entity and edge**
- Consolidation is a separate, auditable operation (not automatic during ingest)
- Consumer queries can filter by source, receiving only single-source or explicitly-linked results
- Enrichment errors are contained: bad entities don't corrupt the chunk store

### Threat: Data Exfiltration via Agent Queries

A compromised or confused agent could extract bulk corporate data through repeated queries.

**Mitigation:**
- Query results are **bounded** (max chunks per query, max total per session — configurable)
- All queries are human-observable (VS Code Copilot shows tool calls)
- No bulk export tool exists; queries return relevant snippets, not full documents
- Rate limiting is possible at MCP level but low-priority given single-user laptop context

### Threat: Stale/Revoked Content Served

Content from revoked sources or updated policies could be served as current.

**Mitigation:**
- Source-registry tracks refresh timestamps; stale sources are flagged
- Query results include freshness metadata (last refresh date)
- Source removal cascades to content deletion (chunks, entities, edges)
- Human approval gate for source removal prevents accidental data loss

---

## 9. Risk Assessment

### Risks RESOLVED by This Decomposition

| Risk | Current State | Resolved By |
|------|--------------|-------------|
| Auth token leakage into content store | Implicit (no enforcement) | Explicit browser-auth isolation; return type cannot carry tokens |
| MCP god-module bypasses engine validation | Active (direct SQL in server.py) | Architectural prohibition: MCP layer has no SQL imports |
| Enrichment corruption cascades to search | Possible (shared storage) | Separate knowledge-graph module; chunk store unaffected by enrichment bugs |
| Source URLs exposed to agents | Possible (no output sanitization contract) | QueryService protocol guarantees: no URLs in results |
| Unvalidated content reaches persistence | Possible (no explicit gate) | Content-pipeline is the named validation boundary; persistence rejects non-domain-objects |

### Risks CREATED by This Decomposition

| Risk | Severity | Mitigation |
|------|----------|-----------|
| More module boundaries = more interface surface to secure | Medium | Typed Protocols enforce contracts at compile time; fewer than 6 public symbols per boundary |
| Separation could create performance pressure to bypass boundaries | Low | Boundaries are in-process (no network); function call overhead is negligible |
| Enrichment isolation might delay integration testing | Low | Integration tests compose modules explicitly; isolation doesn't prevent end-to-end testing |

### Residual Risks (Accepted)

| Risk | Rationale for Acceptance |
|------|-------------------------|
| Same-OS-user access (no inter-module auth) | Laptop-resident, single-user system. OS-level isolation is the trust boundary. Adding inter-process auth would be over-engineering. |
| Local storage unencrypted at rest | SQLite + Qdrant files are user-owned. Disk encryption is an OS responsibility (FileVault). Application-level encryption adds complexity without threat model justification for single-user local. |
| No network exposure controls | System is localhost-only (stdio MCP, no HTTP endpoints for knowledge). Cockpit binds to 127.0.0.1. No mitigation needed beyond existing posture. |

---

## Key Structural Choices

1. **Trust boundaries as module cuts.** Modules are not organized by pipeline stage or code similarity — they follow where trust level changes. This means `content-pipeline` exists as a module specifically because it's where untrusted content becomes trusted domain objects.

2. **Browser-auth remains a separate package.** The existing `serve/browser/` isolation is the strongest boundary in the system. This decomposition preserves and reinforces it rather than absorbing it.

3. **Enrichment quarantined.** The knowledge-graph module is isolated specifically because enrichment is unvalidated. Its blast radius is contained: it can produce bad entities but cannot corrupt chunk retrieval.

4. **MCP layer is a routing shell.** Zero business logic, zero SQL. This is the single most important security improvement over the current architecture. The god-module problem is a trust-boundary violation that must not recur.

5. **No runtime auth between modules.** This is a deliberate acceptance of the single-user, single-OS-process threat model. Inter-module isolation is enforced at the import/type level, not at runtime.

6. **Output sanitization as a protocol guarantee.** QueryService's return type physically cannot contain URLs or internal IDs because the result Pydantic model doesn't have fields for them. Security by construction, not by runtime check.

---

## Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| 6 modules (not 3, not 32) | Clear ownership, bounded blast radius | More packages to maintain, more protocol definitions |
| No runtime auth | Simplicity, no performance overhead | Relies on import discipline; a careless import could bypass |
| Enrichment isolation | Protects core search from unvalidated feature | Enrichment cannot directly annotate chunks; must go through protocol |
| Source URLs hidden from consumers | Prevents infrastructure exposure | Agents can't tell users "go to this URL" (acceptable — they give source names) |
| Typed Protocol enforcement | Compile-time boundary checking | Protocol drift requires explicit migration; can't silently add fields |

---

## Domain Rationale

The security-centric decomposition aligns with the project's stated needs because:

1. **Cascade localization** (D2 finding #4) is achieved by trust boundaries: a failure in enrichment cannot cascade to content retrieval because they are separate modules with separate storage paths.

2. **The MCP god-module** (F7) is the system's primary active vulnerability. Decomposing it into a thin routing layer with protocol-only access is the highest-value security improvement.

3. **Domain maturity uncertainty** (D2 finding #2) is addressed by isolating the least-validated subsystem (enrichment) so it can evolve without destabilizing validated subsystems (chunking, search).

4. **The existing browser boundary** (F3) proves that trust-boundary-aligned isolation works in this codebase. This decomposition extends the same principle to internal boundaries.

5. **Consumer demand scenarios** (D3) require cross-source retrieval with provenance — which is exactly what the QueryService contract guarantees while preventing source URL leakage.

---

## Confidence

**0.85**

High confidence that trust boundaries are correctly identified and that the module cuts resolve the stated security concerns (god-module, auth leakage, enrichment blast radius). Moderate uncertainty about whether 6 modules is the right granularity vs. 4-5 — the source-registry might fold into content-pipeline without security loss. The enrichment isolation is the strongest recommendation; the exact boundary between content-pipeline and persistence is the weakest (could be one module with internal layering).
