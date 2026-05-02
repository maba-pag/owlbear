# Security Proposal — Memory Module Restructure

## Design Summary

A markdown+frontmatter memory store at `.owlbear/memory/` with defense-in-depth against agent-injected content, path traversal, privilege escalation, and state corruption. The design assumes **agents are untrusted input sources** — they operate autonomously, can be manipulated by prompt injection in upstream context, and must not be granted implicit trust over the data they produce.

The system is local-first, single-operator, git-committed. The threat model is not network attackers — it is **misguided or manipulated agents** writing poisoned entries, escaping storage boundaries, or escalating their own content to approved status.

---

## Key Structural Choices

### 1. Input Validation — Frontmatter Injection & Content Sanitization

**Threat:** An agent writes content containing YAML frontmatter delimiters (`---`) or crafted values that, when re-parsed, alter metadata fields (confidence, approval_state, category).

**Design:**

- **Strict Pydantic model at the write boundary.** Every `record_learning` call passes through a Pydantic model with:
  - `category`: `Literal["preference", "knowledge", "context", "behavior", "goal"]` — enum, not freetext
  - `confidence`: `float` constrained to `[0.7, 1.0]` via `Field(ge=0.7, le=1.0)`
  - `approval_state`: ALWAYS set to `"pending"` on creation — never caller-controlled
  - `content`: `str` with max length 4096 characters (no entry should exceed this for agent learnings)
  - `source`: `str` with max length 256, validated against `^[a-zA-Z0-9_\-./: ]+$` pattern
  - `scope_agent`: optional `str`, validated against `^[a-zA-Z0-9_\-]+$`

- **YAML serialization uses safe roundtrip.** The storage layer serializes frontmatter from the validated Pydantic model — never from raw input strings. Content goes in the markdown body (below the closing `---`), never inside frontmatter.

- **Content body sanitization:** Strip any leading `---` lines from content before writing the body. A content field containing `\n---\ncategory: approved\n---\n` must not be parseable as a second frontmatter block. The parser must use **first-occurrence-only** frontmatter extraction (stop at first closing `---`), and the writer must strip/escape `---` at line boundaries in content.

- **Deserialization uses `yaml.safe_load` only.** Never `yaml.load` with `FullLoader` or `UnsafeLoader`. The `ruamel.yaml` YAML instance must have `typ="safe"` or equivalent restricted tag set. No custom tag constructors.

### 2. Path Traversal — Filename Generation

**Threat:** An agent provides content or source strings that, when used in filename generation, escape `.owlbear/memory/` (e.g., `../../etc/passwd`, null bytes, or excessively long names).

**Design:**

- **Filenames are UUID-based, never derived from content.** Entry ID is `uuid4().hex` (32 hex chars). Filename is `{id}.md`. Period.
  - No slug generation from content or category
  - No user-controlled path components
  - This eliminates the entire class of traversal attacks via crafted content

- **`validate_path_containment` guard** (reuse from kanban module) on every write and read:
  ```python
  validate_path_containment(memory_dir, target_path)
  ```
  - Resolves symlinks before comparison
  - Rejects null bytes
  - Rejects paths that resolve outside the memory directory

- **No subdirectory creation from input.** The storage directory is flat: `.owlbear/memory/*.md`. No category subdirectories, no agent-scoped subdirectories. Categories and scopes live in frontmatter, never in the filesystem hierarchy.

### 3. State Integrity — Trust Model & Privilege Boundaries

**Threat:** An agent promotes its own entries to `approved`, deletes others' entries, or bypasses the curation workflow.

**Design:**

- **Write privilege model:**
  | Operation | Who can invoke | Constraint |
  |-----------|---------------|------------|
  | `record_learning` | Any agent | Always creates with `approval_state: pending` |
  | `set_approval_state` | Curator agent only | Enforced by tool registration — only exposed in curator's MCP config |
  | `mark_for_deletion` | Curator agent only | Same — tool-level access control |
  | `get_knowledge` | Any agent | Read-only, filters out `deleted` |
  | `list_entries` | Any agent | Read-only |

- **No self-promotion.** `record_learning` NEVER accepts `approval_state` as a parameter. The field is hardcoded to `"pending"` in the tool implementation. Even if an agent passes it, the Pydantic model's write-path strips it.

- **State machine enforcement:**
  ```
  pending → approved  (curator only)
  pending → deleted   (curator only)
  deleted → pending   (curator only, recovery path)
  approved → deleted  (curator only)
  ```
  Invalid transitions raise `ToolError`. The engine validates before write.

- **Immutable fields after creation:** `id`, `created_at`, `source`, `scope_agent` cannot be modified after initial write. `edit` operations (if added) can only modify `content`, `confidence`, `category`. The storage layer rejects any write that would change an immutable field by comparing against the existing file.

- **Caveat — filesystem access:** Since entries are plain `.md` files in a git repo, any agent with terminal access could theoretically edit them directly. This is accepted as an operational risk mitigated by:
  - Git diff visibility (PR review catches unauthorized changes)
  - Pre-commit hook option: validate all `.owlbear/memory/*.md` files against the Pydantic model
  - The MCP boundary is the trust surface; filesystem bypass is out-of-scope for this module (same as kanban)

### 4. Information Disclosure — Content Restrictions

**Threat:** Agents store secrets, tokens, or paths to sensitive files in memory entries, which then get committed to git.

**Design:**

- **Content scanning on write:** Before persisting, scan content for:
  - Patterns matching secrets: `(ghp_|gho_|github_pat_|sk-|AKIA[A-Z0-9]{16}|xox[bpras]-)`
  - Absolute paths outside the workspace: reject content containing paths starting with `/Users/`, `/home/`, `/etc/`, `C:\\` unless they match the workspace root
  - Bearer tokens, API keys, connection strings (regex pattern list)
  
  On match: reject the write with a clear error message. Do NOT log the rejected content.

- **Frontmatter never contains sensitive data by design** — all fields are controlled enums, UUIDs, timestamps, or short identifiers.

- **`.gitignore` considerations:** The memory directory itself SHOULD be committed (that's the point — git-native, visible in PRs). But:
  - Add `.owlbear/memory/.tmp-*` to `.gitignore` (atomic write temp files)
  - The secret-scanning gate makes gitignoring the directory unnecessary
  - If a future compliance requirement demands non-committed memory, the entire directory can be gitignored without code changes

### 5. Git Exposure — Commit Hygiene

**Threat:** Memory entries contain context that shouldn't be in git history (internal discussions, draft strategies, or information about other projects).

**Design:**

- **Scope isolation:** `scope_project` field allows entries to be project-specific. When a memory entry has `scope_project: "other-project"`, it should NOT be committed to this repo. However, since all entries live in one directory per workspace, this is an operational constraint, not a code one.

- **Recommended practice:** The memory directory lives in `.owlbear/memory/` — inside the ops-data namespace that's already understood as "workspace operational state." This is the same pattern as `.owlbear/kanban/`.

- **Git history is permanent.** Once committed, data persists in history even if deleted. The secret-scanning gate (§4) is the primary defense. Additionally:
  - `mark_for_deletion` sets `approval_state: deleted` and `deleted_at` timestamp but KEEPS the file (soft delete)
  - Hard purge (file removal) should be a separate manual operation, not an MCP tool — to prevent agents from erasing the audit trail
  - Agents cannot hard-delete entries; they can only soft-delete via `mark_for_deletion`

### 6. Denial of Service — Entry Flooding

**Threat:** A misbehaving or manipulated agent calls `record_learning` in a loop, creating thousands of entries, exhausting disk space, or making retrieval unusably slow.

**Design:**

- **Hard cap: 500 entries maximum.** `record_learning` checks `len(list(memory_dir.glob("*.md")))` before writing. If at cap, reject with clear error. This is well above the stated ~200 ceiling and provides headroom without allowing unbounded growth.

- **Per-session rate limit: 20 entries per MCP session.** Track in-memory counter (resets on server restart). After 20 writes in one session, reject further writes. This prevents single-session floods while allowing normal operation across sessions.

- **Content size cap: 4096 characters.** Prevents individual entries from being weaponized as disk-fill vectors.

- **No recursive directory creation.** The storage layer only writes to the one flat directory. An agent cannot create nested structures.

- **Monitoring:** `list_entries` returns total count. Curator agent should alert/compact when count exceeds 200 (operational threshold vs. hard cap at 500).

### 7. Atomic Write Safety — Corruption Prevention

**Threat:** Partial writes from crashes, or concurrent writes to the same file, leave corrupted state.

**Design:**

- **Reuse kanban's `atomic_write` primitive directly:**
  1. `mkstemp` creates `.tmp-{random}.md` in `.owlbear/memory/`
  2. Write content, `fsync` fd
  3. `os.replace(tmp, target)` — atomic rename (POSIX guarantee)
  4. `fsync` parent directory (POSIX only)
  5. On error: unlink temp file, re-raise

- **Concurrency model:** Single-writer assumed (one MCP server instance). If two VS Code windows somehow invoke the same server:
  - Different entries (different IDs) → safe, no conflict
  - Same entry → last writer wins (acceptable at this scale; OCC could be added later if needed)
  - UUID4 collision probability is negligible

- **Read-during-write safety:** Readers may see the old file or the new file, never a partial file (atomic rename guarantee). This is sufficient for the single-operator model.

- **Temp file cleanup:** On startup, scan for and delete any orphaned `.tmp-*.md` files in the memory directory (crash recovery).

### 8. YAML Deserialization — Safe Loading

**Threat:** Crafted frontmatter exploits YAML deserialization to execute code, instantiate objects, or cause resource exhaustion.

**Design:**

- **`yaml.safe_load` ONLY.** This restricts YAML to basic types: strings, numbers, booleans, lists, dicts, null, timestamps. No Python object instantiation, no `!!python/object` tags, no custom constructors.

- **If using `ruamel.yaml`:** Instantiate with `YAML(typ="safe")`. Never use `typ="unsafe"` or `typ="full"`.

- **Pydantic as second gate:** Even if `safe_load` admits unexpected types (e.g., a nested dict where a string is expected), the Pydantic model validation catches type mismatches and rejects them.

- **Recursive depth limit:** YAML bombs (deeply nested structures) are mitigated by:
  - Pydantic model has flat structure (no nested objects)
  - Any parsed value that isn't a simple scalar is rejected by Pydantic before it reaches application logic
  - File size cap (4096 chars content + ~500 chars frontmatter max) limits parse complexity

- **Timestamp handling:** YAML auto-parses date-like strings (`2026-05-02`) as `datetime` objects. The storage layer must:
  - Serialize timestamps as quoted strings in frontmatter (`created_at: "2026-05-02T..."`)
  - Or handle the Pydantic model receiving `datetime` objects for string fields gracefully

---

## Trade-offs

| Decision | Benefit | Cost |
|----------|---------|------|
| UUID filenames (no slugs) | Eliminates path traversal entirely | Less human-readable in file browser |
| Flat directory (no categories/) | No traversal via subdirectory creation | Slightly worse organization for manual browsing |
| Hard entry cap (500) | Prevents unbounded growth | Needs explicit purge workflow when approaching cap |
| Secret scanning on write | Prevents committed secrets | Minor write latency; regex maintenance burden |
| Curator-only promotion | Prevents self-promotion attacks | Requires curator agent to be operational for entries to reach "approved" |
| Soft delete only via MCP | Audit trail preserved in git | Manual intervention needed for hard purges |
| Per-session rate limit (20) | Stops flooding | May require tuning if legitimate batch operations arise |
| Content `---` stripping | Prevents frontmatter injection | Content containing literal triple-dash must be escaped |

---

## Domain Rationale

This design applies **defense-in-depth** appropriate for a local-first, agent-operated system:

1. **Trust boundary is the MCP tool interface.** Agents interact through 5 MCP tools — not the filesystem directly. Every tool validates input through Pydantic before any I/O occurs.

2. **Agents are untrusted.** They write autonomously, can be influenced by prompt injection in documents they process, and have no inherent identity verification. The design treats every `record_learning` call as potentially adversarial input.

3. **Git is the audit trail, not a security boundary.** Once committed, data is visible. The pre-commit defenses (secret scanning, content validation) exist to prevent the wrong data from entering. Git history is the detection layer, not the prevention layer.

4. **Blast radius is bounded.** The worst case for a fully compromised agent writing through MCP tools is: 20 pending entries per session, capped at 500 total, each ≤4096 chars, all soft-deletable by curator, all visible in git diff. No filesystem escape, no privilege escalation, no secret exposure.

5. **The kanban module proves this pattern.** `validate_path_containment`, `atomic_write`, Pydantic validation, and YAML safe loading are all battle-tested in the kanban engine. Reuse eliminates novel risk.

---

## Confidence

**0.90** — High confidence. The threat model is well-scoped (local-first, single-operator), the mitigation patterns are proven (kanban module reuse), and the constraints are realistic (~200 entries, agent-generated content). The remaining 0.10 uncertainty is:
- Secret-scanning regex coverage may have gaps (iterative improvement)
- The "curator-only" enforcement relies on MCP tool registration, which has no cryptographic identity — it's configuration-level, not code-level
- Future multi-workspace or multi-operator scenarios would require revisiting the trust model
