# Synthesis — Authenticated Content Pipeline

## Convergences

### 1. Browser CDP Is the Correct Extraction Mechanism
All four voices accept Edge CDP with SSO session reuse as the transport. Architect frames it as infrastructure; Security accepts the trust model ("functionally equivalent to the user operating the browser manually"); End-User builds UX around the browser dependency; Data treats it as a given and focuses on what happens after extraction. No voice proposed an API-first or alternative approach for Phase 1.

### 2. Separate Browser Package, Protocol-Based Integration
Architect and Security converge on keeping browser infrastructure out of the knowledge package. Architect specifies `owlbear_browser` as a standalone library with lazy import in mcp-knowledge. Security reinforces this via least-privilege (CDP connection only during active extraction, not persistent). Data and End-User are silent on package structure but neither contradicts it.

### 3. User Approval Is the Primary Source-Scope Control
All voices place the user as the gate for what gets ingested. Architect: "no automation of the 'what's valuable' decision." Security (Hard Requirement #2): source configs must require explicit user approval. End-User: structured proposal → user confirmation, with tiered review by source size. Data: doesn't challenge this — focuses on post-approval quality.

### 4. New Entity Types via Direct Enum Extension
Architect and Data agree on adding REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD to `EntityType` and GOVERNS/SUPERSEDES_VERSION to `RelationType`. Both agree on direct StrEnum extension (no plugin system). Data adds that the extraction prompt guidance text must be updated with corporate examples or everything collapses into CONCEPT. Architect notes the prompt update as an execution detail.

### 5. Content Safety: IDPI + Untrusted Wrapping Required Before Go-Live
Security (Hard Requirement #3) and Architect (Warning #1) converge: untrusted web content wrapping and IDPI scanning must be in place before browser extraction goes live. Architect further specifies that the guard predicate should be inverted (wrap everything except known-safe types). No voice disagrees.

### 6. Discovery and Extraction Are Separate Phases
Architect: discovery populates the KnowledgeSource record; extraction consumes it. End-User: discovery is a conversational agent interaction; extraction runs as pipeline batch. The KnowledgeSource record is the agreed boundary between conversational (agent-interactive) and mechanical (pipeline-batch) operations.

### 7. Fail-Fast on Authentication Failure
Architect and Security converge on fail-fast semantics: if auth fails on URL N, abort remaining URLs (they'll all fail the same way). End-User reinforces with source-level diagnosis ("5 consecutive login redirects" not "5 individual failures"). Data doesn't address directly but the hash-stability concern is downstream of successful extraction.

### 8. Pre-Flight Validation Before Every Extraction Run
End-User and Security converge: verify Edge CDP reachable and test auth before extraction. Security specifies this as part of least-privilege (CDP only during active extraction). End-User specifies honest framing about the dependency chain.

### 9. Phased Delivery
All voices implicitly or explicitly support phased delivery. Architect provides the explicit phase plan (Phase 1: browser + source type + entity types → Phase 2: discovery + graph builder → Phase 3: API parallel path).

## Disagreements

### D1. HTML Cleaning Must Precede Any Ingestion (Data) vs. Phase 1 Scope (Architect)
- **Data Voice** identifies HTML cleaning boundary and hash-on-cleaned-content as **critical prerequisites** (Gaps 1 and 2) — without them, every weekly refresh destroys and rebuilds entities, corrupting cross-source edges and wasting LLM tokens. Data asserts these must be resolved "before corporate content can produce trustworthy knowledge graph entities."
- **Architect Voice** scopes Phase 1 as "browser + source type + entity types" without explicitly addressing the cleaning boundary or hash computation order. The content normalizer and hash reordering are not mentioned in the architect's structural design.
- **Nature of tension:** Data says the pipeline is not ready to receive web content without foundational quality fixes. Architect proposes the extraction infrastructure first. If Phase 1 ships without Data's Gaps 1–2, the first refresh cycle will corrupt the graph.

### D2. Browser MCP Tool Surface: Read-Only vs. Interactive (Security vs. Architect/End-User)
- **Security Voice** (Least-Privilege Recommendation #3): v2 browser MCP server should expose only `navigate`, `read_text`, `snapshot` — do NOT expose `click`, `type`, `select` in the extraction pipeline.
- **Architect Voice**: explicitly designs two consumption paths — agent-interactive (discovery: navigate, click, read_text) and pipeline-mechanical (extraction: content-fetcher protocol). The discovery path requires interactive tools.
- **End-User Voice**: source onboarding involves the agent navigating, discovering child pages (BFS), and presenting candidates — implying interactive browser tools.
- **Nature of tension:** Security wants a minimal read-only tool surface. Architect and End-User need interactive tools for the discovery workflow. Security may intend the restriction only for the extraction pipeline (not discovery), but the boundary between "discovery MCP tools" and "extraction MCP tools" is unresolved.

### D3. Unmanaged "One-Time Extract" Mode (End-User — Unaddressed by Others)
- **End-User Voice** proposes two lifecycle modes: managed sources (full lifecycle) and unmanaged one-time extracts (no refresh, no status, promotion path available).
- **Architect, Data, Security** all address only the managed source model. None propose or reject one-time extracts.
- **Nature of tension:** Not a direct conflict, but a scope question. One-time extracts add UX surface area and a governance gap (stale content without refresh). If included, Data's quality controls still apply but the source attribution metadata differs.

### D4. URL Guard Enforcement Layer (Security vs. Architect)
- **Security Voice** (Warning #2): HookRegistry swallows exceptions — URL guards implemented as `PRE_TOOL_USE` hooks will log `BlockedURLError` but navigation **will still proceed**. URL guards must be enforced at the tool implementation level, inside the navigate function.
- **Architect Voice**: does not address hook enforcement reliability. The v1 design used HookRegistry.PRE_TOOL_USE for URL guards.
- **Nature of tension:** Security identifies a concrete vulnerability in the hook-based approach that Architect's design inherits. This needs resolution before the navigate tool is built.

### D5. Refresh-Time Auto-Inclusion of New Pages (End-User vs. Security Implicit)
- **End-User Voice**: when refresh discovers new pages within scope boundaries, auto-include them and report to user at next interaction.
- **Security Voice** (Hard Requirement #2): source configurations must require explicit user approval. No auto-approved source additions.
- **Nature of tension:** Auto-inclusion of new pages within an already-approved scope boundary is arguably within the user's prior approval. But Security's hard requirement is unambiguous: no auto-approved additions. The question is whether "within existing scope boundary" counts as pre-approved or requires re-approval.

### D6. Entity Metadata Propagation (Data — Unaddressed by Others)
- **Data Voice** (Warning #5): `source_system` reaches Document.metadata but is NOT propagated to Entity.metadata. Agents querying entities won't know the source system without joining back to the document.
- **No other voice addresses this.** Architect's design flows metadata through IntakeResult but doesn't specify entity-level propagation.
- **Nature of tension:** Technical implementation detail, but affects agent UX for knowledge queries.

## Approach Options

### Option A: Pipeline-First — Fix Quality Gaps, Then Add Browser
Ship Data's Gaps 1–3 (HTML cleaner, hash-on-cleaned, canonical names) as Phase 0. Then deliver Architect's Phase 1 (browser package, source type, entity types) as Phase 1. Discovery and agent UX follow in Phase 2.

| **Pro** | **Con** |
|---------|---------|
| First ingestion produces clean, stable graph | Delays the headline feature (browser extraction) |
| No rework from graph corruption | Quality fixes are speculative until real web content exercises them |
| Data voice's critical gaps addressed early | Browser package development could proceed in parallel |

### Option B: Infrastructure-First — Browser + Source Type, Then Quality Hardening
Ship Architect's Phase 1 (browser package, AUTHENTICATED_WEB source type, entity types) with a minimal cleaning step (strip `<script>`/`<style>`, basic DOM→text). Defer full HTML normalizer, hash reordering, and canonicalization to Phase 1.5.

| **Pro** | **Con** |
|---------|---------|
| Delivers extraction capability sooner | First refresh cycle may have entity churn (D1 tension) |
| Real web content informs quality tuning | Technical debt on hash computation |
| Browser package and quality work can be taskified independently | Requires accepting temporary graph instability |

### Option C: Parallel Tracks — Browser Infrastructure + Pipeline Quality Simultaneously
Two independent workstreams: (1) browser package + MCP server + source type, (2) HTML cleaner + hash reordering + entity canonicalization. Both converge at integration: first authenticated ingestion uses the full cleaned pipeline.

| **Pro** | **Con** |
|---------|---------|
| Fastest path to correct end state | Higher coordination cost |
| No graph corruption, no delayed extraction | Integration testing requires both tracks complete |
| Matches natural code boundaries (different packages) | Risk of interface mismatch between tracks |

### Option D: Minimal Viable Pipeline — Browser + Cleaning + Hash, Defer Canonicalization and Discovery
Combine Architect's browser infrastructure with Data's critical Gaps 1–2 only (cleaning boundary, hash-on-cleaned). Ship entity types but defer canonicalization (Gap 3), rich metadata propagation, and interactive discovery. Source URLs are manually provided (no BFS discovery agent).

| **Pro** | **Con** |
|---------|---------|
| Smallest scope that avoids graph corruption | No interactive discovery UX |
| Entity canonicalization can be tuned on real data later | Manual URL curation for initial sources |
| Security hard requirements achievable in this scope | End-User voice's managed/unmanaged modes deferred |

## Recommendation

**Option C (Parallel Tracks)** with Option D as the fallback if single-agent execution makes parallelism impractical.

The four voices converge strongly on what needs to be built — the disagreements are primarily about **sequencing and scope**, not direction. The architecture (separate browser package, protocol injection, AUTHENTICATED_WEB source type, direct enum extension) is uncontested. The data quality gaps are real and well-argued — shipping browser extraction without at least the cleaning boundary and hash fix (Data Gaps 1–2) will produce a graph that corrupts itself on every refresh cycle.

Concrete first actions:
1. **Resolve D1 explicitly** — cleaning boundary and hash-on-cleaned must ship with or before first authenticated ingestion. Non-negotiable per Data's analysis.
2. **Resolve D2** — define whether the browser MCP server has one tool set or two (read-only for extraction, interactive for discovery). Security's least-privilege principle and Architect's two-path design are reconcilable but need an explicit decision.
3. **Resolve D4** — URL guards must be at tool-implementation level per Security's finding about HookRegistry exception swallowing. This is a concrete vulnerability.
4. **Defer D3 and D5** — unmanaged extracts and auto-inclusion are valuable UX features but not Phase 1 critical. Both can be added after the core pipeline works.

Security's five hard requirements are non-negotiable gates. Content safety (IDPI + wrapping) must be verified before go-live.

**Confidence: 0.82**

Strong alignment on architecture, extraction mechanism, entity model, user approval model, and content safety requirements. Confidence reduced by unresolved sequencing tension (D1), tool surface ambiguity (D2), and the hook enforcement gap (D4) — all resolvable but requiring explicit user decisions.

## Open Questions

1. **Phase scope for cleaning boundary (D1):** Does the HTML cleaner and hash-on-cleaned ship as part of the browser phase, or as a prerequisite? Data Voice argues prerequisite; Architect Voice scopes it outside Phase 1. The user must decide sequencing. *(Data vs. Architect)*

2. **Browser tool surface split (D2):** Should the browser MCP server expose interactive tools (click, type) for the discovery agent, or should discovery use a separate mechanism? If interactive tools are exposed, how are they gated from the extraction pipeline? *(Security vs. Architect/End-User)*

3. **URL guard enforcement layer (D4):** Should URL allowlist enforcement move from HookRegistry hooks to tool-implementation-level checks? Security's finding that hooks swallow exceptions is a concrete vulnerability. *(Security — unaddressed by Architect)*

4. **Refresh-time auto-inclusion (D5):** Do new pages discovered within an approved scope boundary during refresh count as pre-approved, or do they require explicit re-approval? *(End-User vs. Security)*
