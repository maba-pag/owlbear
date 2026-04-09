# Security Voice — Critic Debate Log

## Cycle 1

**My position:** Initial assessment across six surfaces — YAML deserialization (CRITICAL), path traversal via title slugs (HIGH), file locking/atomicity (HIGH), input validation (MEDIUM), claim identity (LOW), activity log integrity (LOW).

**Critic challenges:**
1. Path traversal model too narrow — only covers title-derived slugs, not `tasks_dir` from config.yml or symlink attacks. Severity: critical.
2. Atomicity stops at single files, but engine invariants are cross-file (next_id + task file + activity log). Severity: high.
3. Safe YAML loading doesn't prevent semantically invalid data from altering engine behavior — need schema validation. Severity: moderate.
4. Claim identity is used in edit-retry authorization logic, not just administrative labeling. Collisions grant unintended write access. Severity: moderate.
5. Activity log concern is concurrent append correctness, not tamper resistance. Interleaved writes produce corrupt JSON lines. Severity: high.

**Blind spots surfaced:** Untrusted config semantics, pre-existing malicious board state, referential integrity, Windows path length, resource exhaustion.

**My response:**
- **Accepted (1):** Expanded path traversal to cover tasks_dir validation, symlink resolution, pre-existing state validation.
- **Accepted (2):** Expanded atomicity to cover cross-file ordering and partial-failure recovery.
- **Accepted (3):** Added Pydantic schema validation after YAML loading.
- **Accepted (4):** Upgraded claim identity from LOW to MEDIUM. Acknowledged authorization role.
- **Accepted (5):** Upgraded activity log from LOW to MEDIUM. Added locking requirement for appends.
- **Rejected:** Referential integrity (cycles in depends_on) — data consistency, not security.

---

## Cycle 2

**My position:** Refined with config validation, schema models, explicit trust boundary, three-surface path traversal, cross-file atomicity ordering.

**Critic challenges:**
1. Config schema still doesn't match real format — statuses are `[{name: str}]` not `[str]`, version/board.name/tui fields omitted. Severity: critical.
2. Body/note is Markdown after frontmatter, not a YAML field — wrong parser surface in validation section. Severity: critical.
3. Status `archived` is a current valid state, not a legacy exception — whitelist rule too strict. Severity: critical.
4. Read path boundary relaxation ("warn, don't crash") contradicts the strict boundary statement. Severity: critical.
5. Claim identity protocol deeper than pool size — agent-name generates new name per call, so retry logic is broken by design. Severity: moderate.
6. Schema omits engine-managed fields: created, updated, parent, depends_on, claimed_by, claimed_at. Severity: moderate.

**Blind spots surfaced:** Duplicate task IDs, malformed claimed_at handling, oversized body/note inputs.

**My response:**
- **Accepted (1):** Fixed config schema to match actual YAML structure.
- **Accepted (2):** Separated frontmatter/body boundary as its own security surface. Clarified body is Markdown, not YAML.
- **Accepted (3):** Added `archived` as valid engine state alongside configured statuses.
- **Accepted (4):** Removed read-path relaxation. Reads also enforce boundary strictly — skip files outside boundary.
- **Accepted (5):** Identified that native engine must persist agent name per session, not regenerate per call.
- **Accepted (6):** Expanded schema to include all engine-managed frontmatter fields.
- **Accepted blind spots:** Added duplicate ID detection, claimed_at malformed handling, body/note size caps.

---

## Cycle 3

**My position:** Further refined with correct config schema, body/frontmatter separation, session-stable claim identity, full field coverage, strict boundary enforcement.

**Critic challenges:**
1. Claim identity scope still ambiguous — "once at lifespan start (OR per start_work)" are incompatible scopes. Severity: critical.
2. ID anomaly policy permits ambiguous resolution — "prefer frontmatter ID" doesn't prevent task shadowing. Severity: critical.
3. Schema "preserved unknowns" doesn't define whether legacy fields are valid data or tolerated baggage. Severity: moderate.
4. "Permissive on read" has operational implications for dispatch and end_work routing. Severity: moderate.

**Blind spots surfaced:** Frontmatter YAML resource limits (alias explosion), archived visibility defaults, degraded-board observability.

**My response:**
- **Accepted (1):** Clarified: agent name generated once per consumer session (MCP lifespan for servers, per-invocation for CLI). Same session = same name for all operations.
- **Accepted (2):** Strengthened: duplicate frontmatter IDs → engine error, not silent resolution. Filename-frontmatter ID mismatch → warning + reject writes.
- **Rejected (3):** Level of detail is implementation design, not security. Security position needs: validate safety-critical fields, preserve everything else. Exact typing of `started` is a compatibility question.
- **Rejected (4):** How planner routes unknown statuses is a feature concern. Security concern is: can a malformed status cause injection/traversal/execution? No — it's a string. Validate on write, preserve on read.
- **Accepted blind spot:** Added YAML depth/alias limits for resource exhaustion prevention.
- **Rejected blind spots:** Archived visibility defaults and degraded-board observability are operational design decisions, not security.

---

## Cycle 4

**Critic challenges:**
1. Claim identity scope ambiguity refined but CLI one-shot consumers still unspecified. Severity: critical (downgraded by me to moderate — CLI one-shots don't need retry logic).
2. ID ambiguity can shadow tasks — detection alone is insufficient. Severity: critical (accepted — hardened to error on duplicates).
3. "Preserved unknowns" looseness for compatibility. Severity: moderate (rejected — design, not security).
4. "Permissive on read" operational behavior. Severity: moderate (rejected — design, not security).

**Blind spots surfaced:** Frontmatter/config YAML resource limits, archived default visibility, degraded-board observability.

**Not run as formal cycle** — Critic was drifting into implementation design territory. Accepted the two security-material points (claim scope for CLI, ID uniqueness as hard error), rejected the rest as out of scope.

---

## Final Assessment

- **Cycles completed:** 4 (3 formal + 1 evaluation pass)
- **What changed:** Path traversal expanded from title-only to config+symlink+pre-existing state. Atomicity expanded from single-file to cross-file ordering. Body/frontmatter separated as its own surface. Claim identity upgraded from LOW to MEDIUM with protocol-level fix identified. Activity log upgraded from LOW to MEDIUM. YAML resource limits added. ID uniqueness hardened from warning to error.
- **What I held:** Referential integrity (dependency cycles) is not a security concern. Operational routing of unknown statuses is not a security concern. Archived visibility defaults are not a security concern. Exact schema typing of legacy fields is a compatibility concern, not security.
- **Final confidence:** 0.88
