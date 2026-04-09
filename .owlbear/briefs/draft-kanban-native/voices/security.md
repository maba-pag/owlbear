# Security Voice — Kanban Native Engine

## Security Stance

The native Python board engine introduces a **filesystem-as-database** surface that inherits the full trust of Python's YAML and path-handling libraries. The system is heading toward distribution (clone = install), meaning a cloned repository with malicious task files or config becomes the primary threat vector. The engine MUST treat all on-disk data — config, task files, activity log — as **untrusted input** on every read.

The six security surfaces below are ordered by severity. Items 1–2 are non-negotiable prerequisites for shipping. Items 3–6 are hardening measures that should land in the same implementation pass but have more design latitude.

## Risk Assessment

### 1. YAML Deserialization — CRITICAL

**Risk:** PyYAML's `yaml.load()` with FullLoader or UnsafeLoader permits arbitrary Python code execution via crafted YAML tags (CWE-502). A malicious task file or config.yml in a cloned repo executes code on the recipient's machine the moment the engine loads the board.

**Requirements:**
- Use `yaml.safe_load()` / `yaml.SafeLoader` — or `ruamel.yaml` in safe round-trip mode — for ALL YAML parsing. No exceptions, no opt-out.
- Apply schema validation via Pydantic models after loading. Safe loading prevents code execution; schema validation prevents semantically invalid data from altering engine behavior.
- Models MUST use `extra="allow"` (or equivalent) to preserve unknown frontmatter fields through read-write cycles. The existing 700+ task corpus contains fields the engine doesn't manage (class, started, completed, assignee, due, estimate) — these must survive unchanged.
- Pin the YAML library version in `pyproject.toml`.
- Set YAML loader limits: reject documents exceeding reasonable depth (e.g., 50 levels) and disable alias expansion or cap alias count to prevent billion-laughs-style resource exhaustion.

**Config schema (safety-critical fields):**
- `version`: int
- `tasks_dir`: relative path string (see §2)
- `statuses`: list of dicts with required `name` key (string)
- `priorities`: list of strings
- `next_id`: positive integer
- `claim_timeout`: parseable duration string
- All other keys preserved without modification

**Task frontmatter schema (safety-critical fields):**
- `id`: positive integer
- `title`: string (see §5 for validation)
- `status`: string — validated against configured statuses + `archived` on write; accepted as-is on read
- `priority`: string — validated against configured priorities on write; accepted as-is on read
- `tags`: list of strings
- `parent`: int or null
- `depends_on`: list of ints
- `blocked`: boolean
- `block_reason`: string or null
- `claimed_by`: string or null
- `claimed_at`: ISO timestamp string or null — if present and malformed, treat claim as expired (fail-open for reclaimability)
- `created`, `updated`: ISO timestamp strings
- All other keys preserved without modification

### 2. Path Traversal & Filesystem Boundary — CRITICAL

**Risk:** Task filenames are `<id>-<slug>.md` where the slug derives from user-provided titles. `config.yml` specifies `tasks_dir`. Either vector can redirect reads/writes outside the kanban directory if unsanitized — including to system files, other users' data, or executable locations.

**Trust boundary:** The resolved `.owlbear/kanban/` directory. All filesystem operations MUST be contained within this boundary.

**Requirements:**
- **tasks_dir:** MUST be a relative path. After resolution against the kanban directory, the result MUST remain within `.owlbear/kanban/`. Reject absolute paths or paths that escape the boundary after normalization.
- **Title slugs:** Strict allowlist `[a-z0-9-]`. Maximum 80 characters (conservative for Windows MAX_PATH given variable checkout root lengths). Raw title preserved in frontmatter — slug is filename only.
- **Windows reserved names:** Reject slugs matching `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9` (case-insensitive).
- **Symlink resolution:** Before ANY read or write, resolve the target path via `Path.resolve()` and verify it is within the resolved boundary. If a file resolves outside the boundary, skip it on reads (with warning) and reject the operation on writes.
- **Hardlinks:** `Path.resolve()` cannot detect hardlinks. This is a **known limitation**. Hardlinks require pre-existing filesystem write access and cannot be introduced via a normal clone. Document this.
- **Pre-existing state validation:** On board load, validate task filenames match `<int>-<slug>.md`. Skip anomalous files with a logged warning. Do not crash on malformed boards.
- **ID uniqueness enforcement:** If two task files claim the same frontmatter `id`, the engine MUST raise an error — not silently shadow one. Duplicate IDs are a data integrity violation that can cause incorrect writes.
- **Filename–frontmatter ID consistency:** If a filename's numeric prefix disagrees with the frontmatter `id`, log a warning and prefer the frontmatter `id`. Do not write to files with inconsistent IDs.
- **TOCTOU:** Advisory file locks mitigate but cannot eliminate time-of-check/time-of-use gaps between path validation and file operation. This is a known residual risk, acceptable for the threat model (local multi-process, single user per machine).

### 3. File Locking & Atomicity — HIGH

**Risk:** Multiple consumers (MCP server, orchestrator CLI) access the board concurrently. Without locking: two creates can allocate the same `next_id`, simultaneous edits can clobber each other, crash during write can leave corrupt files, concurrent JSONL appends can interleave lines.

**Requirements:**
- **Atomic single-file writes:** All file mutations (task files, config.yml) MUST use write-to-temp-file + `os.replace()` in the same directory as the target. This prevents corrupt files from mid-write crashes and leverages the OS-level atomicity of rename.
- **config.yml locking:** Exclusive advisory lock (cross-platform via `portalocker` or manual `fcntl`/`msvcrt`) around every read-that-leads-to-write cycle. The critical section for `next_id` is: acquire lock → read config → increment → atomic-write config → release lock.
- **activity.jsonl locking:** Brief exclusive lock per append. Cross-platform is required (O4 — Windows support). POSIX `O_APPEND` atomicity for writes ≤ PIPE_BUF cannot be relied upon because Windows lacks this guarantee.
- **Create operation ordering:** Under config lock: allocate next_id → atomic-write config → atomic-write task file → locked-append activity log. If task file write fails after config update, the ID is "leaked" (gap in sequence) — benign, no data corruption.
- **Edit/move ordering:** Atomic-write task file → locked-append activity log. If activity append fails, the task state is correct but the log is incomplete — recoverable.
- **Multi-step operations (end_work):** Task edit + status change are a single task-file write. Archive is a separate file move/rename. If archive fails after edit, the task remains in its pre-archive status — safe, re-runnable. Document the recovery path.

### 4. Frontmatter / Body Boundary — MEDIUM

**Risk:** Task files are `---\n<YAML frontmatter>\n---\n<Markdown body>`. The body is NOT YAML — it is raw Markdown. Incorrect parsing or serialization can conflate the two sections.

**Requirements:**
- **Parsing:** Use a frontmatter-aware parser (e.g., `python-frontmatter` library) or implement proper document-marker splitting: identify the FIRST `---` line as frontmatter open and the SECOND `---` line as frontmatter close. Everything after the second marker is the body, verbatim.
- **Body content with `---`:** Markdown horizontal rules (`---`) in the body MUST NOT be misinterpreted as frontmatter delimiters. The parser must be tested for this case explicitly.
- **Serialization roundtrip:** When rewriting a task file, reconstruct as `---\n<serialized YAML>\n---\n<body>`. Body content is written verbatim — no YAML escaping, no transformation. Validate roundtrip fidelity in tests.
- **append_body / note injection:** Content appended to the body cannot corrupt frontmatter because the frontmatter section is delimited by the first two `---` markers only. Verify this invariant in tests.

### 5. Input Validation — MEDIUM

**Requirements:**
- **status:** Whitelist on mutation — must match a configured status name or `archived`. Accepted as-is on read for backward compatibility with legacy or unknown statuses.
- **priority:** Whitelist on mutation — must match a configured priority. Accepted as-is on read.
- **title:** Max 200 characters raw (stored in frontmatter). No NUL bytes. Slug derived separately (see §2).
- **task_id:** Positive integer validation at the API boundary.
- **tags:** Character set `[a-zA-Z0-9:._-]` per tag. Reject tags containing YAML-special sequences that could corrupt frontmatter serialization.
- **body / note:** Sanity cap of 1 MB to prevent resource exhaustion. Written verbatim to the markdown body section.
- **Config values on load:** Type-validate all fields. `tasks_dir` as relative path (see §2). `next_id` as positive integer. `claim_timeout` as parseable duration.
- **claimed_at:** If present, must parse as ISO 8601 timestamp. If malformed, treat the claim as expired — fail-open for reclaimability rather than fail-closed trapping the task.

### 6. Claim Identity — MEDIUM

**Risk:** Claim names are used in edit-retry authorization logic: when an edit is rejected with `TASK_CLAIMED`, the engine regenerates an agent name and checks if the current consumer is the claimant. This makes claim names a weak authorization token — collisions or impersonation grant unintended write access.

**Requirements:**
- **Session-stable identity:** The native engine MUST generate the agent name ONCE per consumer session (e.g., at MCP server lifespan start) and reuse it for all claim operations in that session. The current kanban-md behavior of generating a fresh name per `agent-name` call breaks retry logic — the generated name almost never matches the claim holder. This is a protocol design fix, not just a pool-size issue.
- **Name pool size:** Minimum 10,000 distinct combinations (e.g., adjective-animal pairs) to make same-session collisions practically impossible with ≤10 concurrent consumers.
- **Claim-timeout enforcement:** Compare `claimed_at` timestamp against current time. Expired claims are reclaimable regardless of name. Do not rely on name matching alone.
- **Not a security boundary:** Document explicitly that claims are concurrency coordination, not authentication. Any consumer with filesystem access can forge a claim name. If multi-user support is ever added, this surface needs real authentication.

## Compliance Implications

- **CWE-502 (Deserialization of Untrusted Data):** Direct applicability. YAML safe loading is the primary mitigation.
- **CWE-22 (Path Traversal):** Direct applicability. Boundary containment with symlink resolution.
- **CWE-362 (Race Condition):** Applicable for concurrent file access. Advisory locking + atomic writes.
- **Supply-chain risk via cloned repos:** OwlBear's distribution model means the repo IS the attack surface. All on-disk artifacts must be treated as untrusted input.

No regulatory compliance requirements apply (no PII, no network-facing service, no financial data). However, the distribution model means security posture must be robust enough that a user can safely clone and run an untrusted OwlBear project — at minimum, it must not execute arbitrary code from on-disk artifacts.

## Least-Privilege Recommendations

1. The engine should operate within a single directory boundary (`.owlbear/kanban/`). No filesystem access outside this tree.
2. File permissions on created files should use restrictive defaults (0o644 on POSIX). Not critical on Windows but important for Linux/Mac distribution.
3. Error messages should use relative paths only — never expose absolute filesystem paths in MCP responses or error outputs.
4. The YAML parser should have no access to the `!!python/` tag family or any constructor beyond safe scalars, sequences, and mappings.

## Warnings

1. **YAML safe loading is a hard gate.** If any code path uses `yaml.load()` without SafeLoader, the system is immediately exploitable via a crafted task file in any cloned repo. This is the single highest-impact vulnerability possible in this engine and must be verified in code review.
2. **Path traversal via `tasks_dir`** is a subtle attack vector. Most path-traversal reviews focus on user input (titles), but the config file itself is attacker-controlled in the distribution model. Validate `tasks_dir` the same way you validate slugs.
3. **Claim identity is NOT authentication.** Do not build features on top of claim names that assume verified identity. If claim names are ever exposed in user-facing UI or used for access control decisions beyond edit-retry, the design needs real identity infrastructure.
4. **The activity log is NOT tamper-resistant.** Any process with filesystem access can modify or truncate it. Do not build audit or compliance features on top of `activity.jsonl` without adding integrity mechanisms (signatures, write-once storage, or external log shipping).

## Confidence

0.88

Four Critic cycles completed. Positions hardened on: config-as-attack-surface, body/frontmatter boundary, claim identity protocol design, concurrent append correctness, ID uniqueness enforcement, schema-must-match-live-data, YAML resource limits. Residual uncertainty is in the hardlink limitation (no practical mitigation available) and the exact claim name pool size calibration.
