# Data Person — Critic Debate Log

## Cycle 1

**My position:** Six initial positions covering YAML parsing (ruamel.yaml), next_id locking (config.yml only), activity.jsonl (single-writer, no lock), file naming (id-prefix slug), timestamp string preservation, timezone-aware ISO 8601.

**Critic challenges (5 critical, 1 moderate):**

1. **Activity log vocabulary mismatch (Critical).** I claimed "match existing Go format exactly" but listed action types (`archive`) that don't exist in the live log, and missed types that do (`handoff`, `unblock`). The `detail` field content varies by action — not rigid as I described.
   - **Accepted.** Audited live corpus to extract actual action vocabulary: create, edit, move, claim, release, block, unblock, handoff, delete. No "archive" action — archiving logs as `move`. Detail is freeform.

2. **Single-process assumption invalid (Critical).** MCP server, orchestrator, CLI, and test fixtures are separate consumers. "Single-writer, no locking for activity.jsonl" is wrong.
   - **Accepted.** Elevated to board-level lock for ALL mutations, not just config.yml.

3. **Transaction completeness (Critical).** Crash window between ID allocation, task write, and audit emission was unaddressed.
   - **Accepted.** Added crash model analysis with temp+rename per file. Acknowledged this is serialization, not ACID.

4. **Byte-stability overclaim (Moderate).** "Except for changed fields" doesn't hold when the engine mutates fields (title, tags, block_reason) that Go stored with specific quoting.
   - **Accepted.** Downgraded claim to "no data loss" — cosmetic quoting normalization on mutated fields is acceptable.

5. **Pydantic model divergence (Moderate).** MCP model uses str timestamps; orchestrator uses datetime. "Parse to datetime only in domain layer" is too vague.
   - **Accepted.** Formalized: engine canonical model uses str timestamps. Consumers project/coerce in their own layers.

6. **Timestamp coercion mechanism (Moderate).** How to disable timestamp resolver without breaking bool/int?
   - **Accepted.** Added explicit resolver removal strategy targeting only `tag:yaml.org,2002:timestamp`.

**Blind spots surfaced:** Agent-name generation, claim_timeout enforcement, rename semantics on title edit, compound audit operations.

**Outcome:** Position substantially revised. Moved from 6 positions to 7+.

---

## Cycle 2

**My position:** Expanded to board-level lock, corrected activity.jsonl vocabulary, added freeform detail, no file rename on title edit, explicit timestamp resolver removal, canonical TaskRecord model, claim invariants.

**Critic challenges (1 critical, 3 moderate):**

1. **Filename prefix as lookup key vs. security voice (Critical).** Security voice says if filename prefix and frontmatter id disagree, prefer frontmatter id and refuse writes. My position treated filename prefix as canonical lookup key.
   - **Accepted.** Corrected: frontmatter `id` is the source of truth. Filename prefix is a convenience for human navigation.

2. **Unlocked reader on activity.jsonl (Critical).** Windows append atomicity isn't guaranteed. A reader racing an append can hit partial JSON.
   - **Accepted.** Added reader resilience requirement: consumers must handle truncated last line.

3. **TaskRecord lifecycle fields too abstract (Moderate).** Need to explicitly define which fields are engine-managed vs. passthrough.
   - **Accepted.** Added explicit three-category field classification: identity, lifecycle (engine-managed), relational, content.

4. **Claim identity scope (Moderate).** `claimed_by` field storage doesn't address session-stable identity requirement.
   - **Deferred.** Noted as behavioral, not data. Revisited in Cycle 4.

**Blind spots surfaced:** Config.yml statuses shape (list of dicts, not list of strings).

**Outcome:** Position refined. Frontmatter id now canonical. Reader resilience formalized.

---

## Cycle 3

**My position:** Frontmatter id as truth with strict validation (hard error on mismatch/duplicate), no long-lived cache, per-session directory scan, tasks_dir boundary enforcement.

**Critic challenges (1 critical, 3 moderate):**

1. **ID validation inconsistency (Critical).** I claimed "build fresh index from directory scan" + "full frontmatter parsing on individual task load" + "detect duplicate frontmatter IDs as ERROR." These are contradictory — a filename-prefix-only scan can't detect duplicate frontmatter IDs.
   - **Accepted.** Resolved with two-tier strategy: filename prefix for fast single-task lookup, full frontmatter scan at initialization for integrity validation.

2. **Hard error on mismatch is a behavior change (Moderate).** kanban-md may have silently repaired mismatches. Hard error breaks "same behavioral contract" goal.
   - **Accepted.** Softened: mismatch → warning + prefer frontmatter id. Duplicate frontmatter ids → hard error (true ambiguity).

3. **Session-stable identity is board-layer concern (Moderate).** Engine "does not enforce session stability" leaves the invariant outside the layer that owns claim semantics.
   - **Accepted.** Engine now owns identity generation: one identity per engine instance, reused for all claim/release calls.

4. **Consumer contract change for orchestrator (Moderate).** TaskRecord with str timestamps + no class field is a breaking change for orchestrator's Task model.
   - **Rejected.** Consumer adaptation is expected — it's the point of the migration. The orchestrator's model is a projection that will be updated. Flagged as a known migration seam in Warnings.

**Blind spots surfaced:** Frontmatter/body boundary parsing (body containing `---`), YAML safety hardening (version pinning, loader limits), retro workflow truncation handling.

**Outcome:** ID validation model resolved. Claim identity moved to engine layer. Added migration warnings.

---

## Cycle 4

**My position:** Final nine-position stance incorporating all accepted challenges.

**Critic challenges (1 critical, 2 moderate):**

1. **Two-tier lookup still inconsistent (Critical).** The description combined claims that couldn't all be true simultaneously — "no long-lived cache" + "full frontmatter scan at initialization" + "per-session index."
   - **Accepted.** Clarified: integrity scan happens at engine initialization, builds validated index for the session. Not a long-lived cross-session cache — it's per-instance.

2. **Filename/frontmatter mismatch: hard error vs. warn (Moderate).** Security voice framed this as warn-and-prefer, not crash.
   - **Already resolved in Cycle 3.** Mismatch → warning, duplicate → error.

3. **Session-stable identity not fully specified (Moderate).** Engine "does not enforce session stability" contradicts the updated claim that engine generates identity once per instance.
   - **Accepted.** Clarified: engine instance IS the session boundary. Identity generated once at construction, reused throughout instance lifetime.

**Blind spots surfaced:** Frontmatter `---` delimiter in body content, YAML version pinning.

**Outcome:** Position internally consistent. Added ruamel.yaml version pinning and frontmatter delimiter parsing rules.

---

## Cycle 5 (Final)

**Not executed as a separate invocation.** Incorporated all remaining Cycle 4 feedback into the final position document directly.

**Remaining items addressed in final position:**
- Frontmatter/body boundary: first two `---` delimiters only
- YAML safety: version pinning in pyproject.toml, no unsafe loaders
- Retro workflow: flagged as migration task in Warnings
- `os.replace()` on Windows: flagged external file handle risk in Warnings

---

## Final Assessment

**Cycles completed:** 5 (4 explicit Critic invocations + 1 self-review integration pass)

**What changed from initial position:**
- Board-level lock scope expanded from config-only to all mutations
- activity.jsonl vocabulary corrected from theoretical to observed
- Crash model downgraded from "crash-consistent" to "writer-serialized"
- Byte-stability downgraded to no-data-loss
- Frontmatter id promoted to canonical identity (was filename prefix)
- ID mismatch: hard error → warning (duplicate ids remain hard error)
- Claim identity moved from consumer responsibility to engine-owned
- Config.yml shape preservation added (list-of-dicts, not list-of-strings)
- Reader resilience for activity.jsonl formalized as migration requirement

**What I held:**
- ruamel.yaml as the YAML library (challenged but no better alternative surfaced)
- Timestamps as strings in the engine model (consumer adaptation is migration scope)
- No file rename on title edit (simpler, no broken references)
- Freeform `detail` field in activity.jsonl (no rigid schema)
- Dropped Go fields survive in CommentedMap but not typed API
- `os.replace()` for atomic per-file writes (best available on cross-platform)
- Consumer contract changes (orchestrator model adaptation) are expected, not design flaws
