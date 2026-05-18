# Security Stance — Knowledge Source Lifecycle Fixes

## Security Stance

The four proposed outcomes (O1–O4) operate within a system that already exposes sensitive data through existing MCP tool surfaces. The security analysis must account for the current exposure baseline, not treat O1/O4 as net-new attack surface creation.

### O1 — Exposing Health in `list_sources`

**Risk: Information disclosure via `last_error` — MEDIUM, not HIGH.**

`last_error` contains unsanitized `str(exc)` from HTTP failures, which can include internal hostnames, URL paths, and authentication error details. However, the Critic correctly identified that `refresh_source` already returns raw `errors` and `warnings` lists to MCP callers (server.py L1508-1509). O1 widens discoverability from "active refresh caller" to "any agent calling list_sources," but does not create the first tool-surface exposure.

The real risk change is **passive vs. active**: today an agent must trigger a refresh to see errors; after O1, stale error details persist and are visible to any `list_sources` caller without action.

**Recommendation:** Sanitize `last_error` at write time in `_update_source_record`. Strip exception messages to error class + safe context (e.g., "HTTP 401 for host corporate.internal" not the full response body). Apply the same sanitization to `refresh_source` error payloads — the existing browser-fetcher sanitization pattern (server.py L63-65) proves the codebase already distinguishes controlled from uncontrolled error text.

**`config` field:** Must NOT be added to the `list_sources` response. Contains full URLs that may embed credentials or internal endpoints. However, note that `search_knowledge` already serializes `source.url` from `config` into result metadata (server.py L985-997). The `config` exclusion in O1 is correct but does not fully close URL exposure. A separate pass should audit `search_knowledge` source metadata serialization.

**`enabled` and `fetch_method`:** Safe to expose. No sensitive data. These are operational metadata.

### O2 — Fix Refresh Honesty

**Security posture: NET POSITIVE, with a caveat.**

Preserving stale `last_refreshed_at` on failure prevents false-freshness signals that could mask compromised or unreachable sources. This is the correct security behavior — timestamps should reflect successful data acquisition, not attempted contact.

**Caveat:** The fix alone does not distinguish four operationally distinct states: never-refreshed, failed-recently, unsupported-fetch-method, and stale-but-last-success-known. From a security perspective, "never refreshed" and "all attempts failed" have different implications — the former may indicate a misconfigured source, the latter may indicate an authentication revocation or network policy change. The implementation should ensure `last_error` captures enough context to differentiate these states without leaking sensitive details (per O1 sanitization recommendation).

### O3 — Direct-Ingest Source Semantics

**Security posture: LOW RISK.**

Retyping direct-ingest HTTP sources from `AUTHENTICATED_WEB` to a more accurate type (e.g., `URL_LIST`) is primarily a correctness concern. The security-relevant observation: `AUTHENTICATED_WEB` currently routes to `HttpxContentFetcher` via `fetch_method="http"`, which works but semantically implies authentication capabilities the source doesn't require. Mislabeling could cause an operator to over-trust the source's access model.

No trust boundary or access control issue. The type change doesn't affect what data is exposed or who can access it.

### O4 — `remove_source` MCP Tool

**Risk: Irreversible data destruction — MEDIUM.**

`delete_cascade` removes source → pages → documents → entities → edges → chunks → document_status in a single SQLite transaction. Wiring this as an MCP tool creates a path for agents to irreversibly remove all downstream data for a source.

**Context correction:** The Critic correctly noted that destructive mutation already exists — `ingest_document` has replace-on-change semantics that delete prior document data. O4 escalates from per-document replacement to whole-source removal, which is a larger blast radius but not a wholly new class of destructive power.

**Agent access scoping:** The repo scopes tool access per agent via `.agent.md` files and supports `KNOWLEDGE_TOOLS_EXCLUDE` for server-side tool exclusion. Not every agent would have access to `remove_source`. However, agent scoping is advisory in the VS Code Copilot model — it controls default tool lists, not privilege boundaries.

**`destructiveHint=True` assessment:** Necessary but not sufficient as the sole safeguard. In the VS Code + Copilot stdio model, `destructiveHint=True` surfaces a user confirmation dialog. This is the correct primary gate for a single-user laptop-resident system. The "all hosts may ignore the hint" concern is theoretical — the actual deployment model is VS Code stdio, where the hint is respected.

**Recommendations (ordered by priority):**
1. **`destructiveHint=True`** — required, and sufficient as the user-facing gate for the actual deployment model.
2. **Audit logging** — log `(source_id, source_name, timestamp, cascade_counts)` before commit. This enables post-incident diagnosis if a deletion was unintended. Low implementation cost.
3. **Qdrant vector cleanup** — `delete_cascade` must clean up persisted Qdrant vectors for deleted documents. In persisted-path deployments (`.owlbear/knowledge/vectors`), orphaned vectors from deleted corporate documents constitute a data-remanence concern. This is a **pre-condition for O4**, not a nice-to-have.
4. **Soft-delete is over-engineering for this context.** At 10-50 sources on a single-user system with git-backed project state, `enabled=false` toggle plus `destructiveHint` confirmation is sufficient. Git history provides the recovery path for manifests; SQLite backups cover the data layer.

## Risk Assessment

| Outcome | Risk Level | Primary Concern | Mitigation |
|---------|-----------|----------------|------------|
| O1 `last_error` | Medium | Unsanitized error text widens passive disclosure | Sanitize at write time; apply to `refresh_source` too |
| O1 `config` | N/A (excluded) | Already partially exposed via `search_knowledge` | Audit existing URL exposure surfaces separately |
| O2 | Low (positive) | State ambiguity between failure modes | Ensure `last_error` differentiates states |
| O3 | Low | Semantic mislabeling, no access control impact | Correctness fix, not security fix |
| O4 cascade delete | Medium | Irreversible whole-source removal | `destructiveHint=True` + audit log + Qdrant cleanup |
| O4 enumeration | Low | `list_sources` → `remove_source` loop | Agent scoping + `destructiveHint` confirmation per call |

## Compliance Implications

None material. This is a single-user, laptop-resident system with no multi-tenant boundaries, no regulated data handling requirements, and no external API surface. The data retention concern (Qdrant vector orphaning) is a data-integrity issue, not a compliance obligation — but it should be treated as a hard requirement for O4 because "remove source" must mean "remove all traces of source data."

## Least-Privilege Recommendations

1. **Scope `remove_source` to the `knowledge-ingestor` agent only.** Do not grant it to `knowledge-enricher` or general-purpose agents by default.
2. **Do not expose `config` in any read-only tool response.** The URL exposure in `search_knowledge` source metadata should be audited separately.
3. **Sanitize error text at the boundary** — in `_update_source_record` and in the `refresh_source` return path. The browser-fetcher pattern (stripping source URLs from error messages) is the right model to extend.

## Warnings

1. **Sanitization scope is broader than O1.** The `refresh_source` tool already returns raw error strings. Any sanitization applied to `last_error` for O1 should also be applied to `refresh_source` error payloads. Fixing one surface without the other creates inconsistency.
2. **Qdrant cleanup is a hard gate for O4.** Shipping `remove_source` without vector cleanup means "delete" doesn't actually delete — corporate document embeddings persist in the vector store after the user believes the source was removed.
3. **`search_knowledge` source URL serialization** is an existing exposure surface not addressed by O1-O4. Flag for separate audit.

## Confidence

0.82 — High confidence in the risk assessment and recommendations. The Critic correctly identified that the pre-O1 baseline already includes significant exposure through `refresh_source` and `search_knowledge`, which recalibrates O1 from "creates new attack surface" to "widens existing passive discoverability." The core recommendations (sanitize errors, gate O4 with destructiveHint + audit + Qdrant cleanup) are well-grounded in codebase evidence.
