# Security Stance — Cockpit Memory Tab

## Security Stance

The Memory tab introduces file-mutating API endpoints into a local-only cockpit with no authentication. The localhost binding limits the external attack surface, but does not eliminate risks from content injection (via compromised agents), file I/O mis-targeting, or state machine bypass. The trust boundary that matters most is: **memory content is agent-generated, agents process untrusted external sources, and the cockpit renders that content in a browser with full API access to all endpoints.**

## Risk Assessment

### 1. XSS / Content Rendering — HIGH

**Threat model:** Agents ingest external sources (web pages, docs, code) and may be influenced by prompt injection to embed script payloads in memory entry content or titles. If script executes in the cockpit origin (`127.0.0.1:8420`), the attacker gains full read/write access to all cockpit API endpoints — kanban mutations, memory mutations, any future endpoints. This is whole-origin compromise.

**Required mitigations:**
- Render markdown with a library that does NOT pass through raw HTML. Use React Markdown with `rehype-sanitize` or an explicit `allowedElements` whitelist.
- Strip `<script>`, `<iframe>`, `<object>`, `<embed>`, and all event handler attributes (`onerror`, `onload`, `onclick`, etc.).
- Block `javascript:` and `data:` protocols in rendered links.
- Title field: verify React JSX escaping handles it natively (no `dangerouslySetInnerHTML` anywhere).
- Separate concern (lower severity): block remote image `src` attributes to prevent outbound beacon exfiltration. This is a privacy concern, not equivalent to script execution.

### 2. File I/O & Path Containment — HIGH

**Threat model:** Mutation endpoints modify or delete files on disk. Since the API uses id-addressed routes (UUID path parameters), classical path traversal via filename is not the primary vector. The real risk is: (a) the id→path map associating a valid UUID with an out-of-bounds path (via symlink in the memory directory or a malformed/corrupted index), and (b) hard-delete permanently removing a file.

**Required mitigations:**
- Build the id→path map by scanning the memory directory. All mutations address entries by UUID only — never accept a filename, slug, or path from the client.
- After resolving any target path: `resolved_path.resolve().is_relative_to(memory_dir.resolve())`. This catches symlink escapes.
- Reject or skip symlinks during directory scan.
- Hard-delete (`Path.unlink()`) only after containment check passes and state confirms `pending`.
- Atomic writes via temp-file-plus-rename (already the pattern in the codebase).
- Bound file reads: reject files >8KB (frontmatter + 1024-char content + generous margin).

### 3. State Machine Integrity — MEDIUM-HIGH

**Threat model:** State transitions are trust-bearing. Approved entries become highest-trust retrieval candidates for all agents. Curated entries become visible to scoped agents. An unauthorized approve bypasses curation quality gates. An unauthorized delete removes institutional knowledge.

**Required mitigations:**
- Backend reads current file state and validates transition legality before writing.
- Canonical legal transitions:
  - `pending` → `curated` (auto-promote when scope_agents provided via edit/curate action)
  - `curated` → `approved` (explicit approve action, sets `approved_at`)
  - `approved` → `curated` (auto-downgrade on edit, clears `approved_at`)
  - `curated` / `approved` → `deleted` (soft-delete, file retained)
  - `pending` → hard-delete (file removed from disk)
  - `deleted` → nowhere (terminal, locked)
- Reject any transition not in the above table with 409 Conflict.
- Immutable fields (server-owned, never writable via API): `id`, `source_agent`, `created_at`, `updated_at`, `approved_at`, `state`. These are set by the backend as side-effects of actions.
- `state` is NEVER directly writable — only changed as a consequence of approve/delete/edit operations.

**Open contradiction:** The feature brief references "Approve (skip curate)" for pending entries, but the live MCP implementation enforces curated-only approval. The security stance requires the cockpit to match the engine's canonical path: `pending→curated→approved`. Any shortcut must be an explicit, documented decision — not an accidental bypass.

### 4. Cross-Origin / Loopback Reachability — MEDIUM

**Threat model:** No auth means a malicious web page (visited in the same browser) can attempt requests to `localhost:8420`. The browser's CORS preflight mechanism is the only gate for web-based attacks. Local processes and browser extensions are outside CORS entirely and considered inside the trust boundary of a no-auth localhost model.

**Required mitigations:**
- All mutation endpoints MUST require `Content-Type: application/json` and reject requests without it. This forces CORS preflight for cross-origin requests, which the browser blocks absent explicit CORS headers.
- Do NOT configure `Access-Control-Allow-Origin: *`. If CORS middleware exists, restrict to same-origin.
- Do not serve mutation endpoints that accept form-encoded or `text/plain` bodies.
- Accept that local processes are trusted peers in this access model — this is by design, not a gap.

### 5. YAML Parsing — MEDIUM

**Threat model:** Files on disk may be malformed (hand-edited, tool bugs, adversarially crafted content). The parser choice (PyYAML `safe_load` or ruamel.yaml safe mode) must be explicit. Unbounded frontmatter (not just content) is the parsing surface.

**Required mitigations:**
- Use safe loading mode exclusively. Never use `yaml.load()` without safe loader.
- Catch all parse errors and return 422 without stack traces or internal paths.
- Validate parsed frontmatter against expected Pydantic schema before acting on values.
- File size bound (8KB) as defense against YAML bombs in malformed files.
- Handle gracefully: duplicate YAML keys, non-object frontmatter, missing required fields.

### 6. Logic Drift Between Surfaces — MEDIUM

**Threat model:** The cockpit reimplements state machine logic independently from mcp-memory. If these diverge, one surface may permit transitions the other rejects, creating inconsistent trust states (e.g., cockpit approves an entry the MCP engine considers invalid).

**Required mitigations:**
- Document the canonical transition table as a single-source-of-truth spec (shared test fixtures or a specification file).
- Test both surfaces against the same transition matrix.
- Integration test: create entry via MCP, mutate via cockpit, verify state consistency.
- Accept this as a known maintenance cost — architecture extraction (shared `serve/memory/` package) is a scope decision, not a security requirement.

### 7. Input Validation — MEDIUM

**Required enforcement (beyond Pydantic type checking):**
- Content: ≤1024 characters. Reject longer.
- Confidence: `[0.7, 1.0]` inclusive.
- Categories: enum-only (`MemoryCategory` values). Reject unknown.
- `ConfigDict(extra="forbid")`: reject unknown request body fields.
- Title: non-empty, reasonable length (match existing model constraints).
- `scope_agents`: match existing model contract (supports `*` wildcard per current engine semantics). Do NOT introduce new validation grammar that breaks existing stored data.

### 8. Race Conditions / Concurrency — LOW

**Threat model:** Concurrent writes from cockpit and MCP tools on the same entry. Atomic writes (temp-file-plus-rename) already prevent partial corruption. The remaining risk is stale semantic overwrite.

**Required mitigations:**
- Include `updated_at` in GET responses. On mutation, read current `updated_at` from file and reject if it differs from a client-supplied precondition (optimistic concurrency).
- Accept that at single-user scale this is defense-in-depth, not critical-path.

## Compliance Implications

None material. This is a laptop-resident, single-user developer tool with no PII, no external network exposure, and no multi-tenancy. Standard software security hygiene applies but no regulatory framework is triggered.

## Least-Privilege Recommendations

1. The cockpit backend should have read/write access ONLY to the configured memory directory. No filesystem operations outside that boundary.
2. Hard-delete capability should be restricted to entries in `pending` state only — never expose a "force delete any file" path.
3. The frontend should never construct file paths or pass filesystem information to the backend.
4. Immutable fields enforce least-privilege at the data layer: the API cannot elevate its own entries' provenance.

## Warnings

1. **Do not use `dangerouslySetInnerHTML` anywhere in the Memory tab.** This is the single most likely vector for the highest-severity risk.
2. **Do not accept filename/path/slug from the client.** All mutations must be id-addressed.
3. **Do not skip state validation on the backend** — the frontend may enforce UI-level guards, but the backend is the authority.
4. **Do not introduce validation rules stricter than the existing engine contract** (e.g., scope_agents wildcard `*`) — this creates compatibility failures, not security improvements.

## Confidence

0.85 — High confidence on the core position. XSS and file containment are clearly the highest-impact risks. State machine integrity is well-understood. Minor uncertainty on whether the final implementation will use id-addressed routes (assumed) vs. any slug-based paths (would elevate path traversal further). The cross-origin position is calibrated for the localhost model but acknowledges the inherent limitations of no-auth.
