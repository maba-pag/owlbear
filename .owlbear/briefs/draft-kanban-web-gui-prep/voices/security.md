# Security Voice — Kanban Engine Restructuring

## Security Stance

The restructuring is architecturally sound from a security perspective. The engine should remain consumer-agnostic with **no runtime authorization logic**. Trust boundaries are enforced through the **adapter pattern**: each consumer (MCP server, future GUI) controls which engine methods it exposes. The critical invariant — **humans must never claim tasks** — is an adapter-layer responsibility, not an engine concern.

The primary security work in this restructuring is: (a) adding consumer identity to the engine constructor and audit trail, (b) documenting agent-only operations clearly in the engine API, and (c) capturing deferred concurrency constraints in engine documentation so they aren't lost in the handoff to the GUI project.

## Risk Assessment

### Trust Boundary: GUI Adapter → Engine

| Risk | Severity | Mitigation |
|------|----------|------------|
| GUI adapter exposes `claim_task`, `start_work`, `release_task`, or `pick_tasks` to humans | **High** | Architectural enforcement — GUI adapter omits these methods. Agent-only operations clearly marked in engine API docs. Runtime guards rejected as disproportionate to single-developer threat model. |
| `agent_name` is self-asserted — GUI user could impersonate an agent | **Low** | Accepted trust assumption. Single-laptop, single-user system. Document as a trust boundary that must be revisited if deployment model changes. |

### Data Integrity

| Risk | Severity | Status |
|------|----------|--------|
| Partial file writes corrupt task YAML | **Mitigated** | `write_task()` uses `tempfile.mkstemp()` + `Path.replace()` — atomic on all target platforms. Moves with engine. No change needed. |
| Path traversal / null-byte injection in task filenames | **Mitigated** | `validate_path_containment()` handles null bytes, `..` traversal, Windows reserved names, resolved-path verification. Moves with engine. No change needed. |
| `next_id` race condition — two concurrent `create_task` calls allocate same ID → filename collision → silent file overwrite | **Deferred** | Not active with single consumer (MCP). Becomes real when GUI arrives. Requires advisory file lock on `config.yml` during `create_task`. Flagged for GUI brief. |
| TOCTOU on read-modify-write cycles — concurrent edit + claim loses one write | **Deferred** | Accepted risk per D2. `modified_since` timestamp guard recommended for GUI project. Not a risk of this restructuring (single consumer post-restructure). |

### Attack Surface

| Risk | Severity | Status |
|------|----------|--------|
| Future GUI exposes localhost HTTP — reachable by any local process, browser tabs, extensions | **Deferred** | Out of scope. Flagged for GUI brief: requires CSRF protection, Origin header validation. |
| Config file (`config.yml`) has no integrity protection | **Low** | Accepted. Single-laptop, single-user. Filesystem permissions are sufficient. |

## Compliance Implications

None for current deployment model (single-laptop, personal dev tool). If OwlBear is ever shared across users or exposed to a network, the following become relevant:

- Authentication and authorization on the GUI HTTP API
- Encrypted transport (TLS) for any non-localhost traffic
- Tamper detection on activity log (currently append-only but unsigned)
- Role-based access to claim operations

## Least-Privilege Recommendations

1. **Consumer identity on `KanbanEngine.__init__`** — Each adapter passes a `consumer` (or `source`) string at construction time. This binds the engine instance to a single consumer identity, immutable for the session. Activity log entries include this field. Constructor scope (not per-call) prevents identity confusion.

2. **Agent-only operations documented in engine API** — `claim_task()`, `start_work()`, `release_task()`, and `pick_tasks()` (when extracted to engine) must be clearly marked as agent-only in docstrings. The GUI adapter must not expose these.

3. **GUI adapter surface is read + write, not dispatch** — The GUI should expose: `list_tasks`, `show_task`, `create_task`, `edit_task`, `move_task`. It should NOT expose: `claim_task`, `start_work`, `release_task`, `pick_tasks`, `end_work`. The `end_work` exclusion is because it compounds claim+move+note — operations that are agent workflow semantics, not human board operations.

4. **Activity log includes consumer source** — Every `log_activity()` call must include which consumer initiated the action (e.g., `"mcp-agent"`, `"gui-human"`). This is a requirement of the restructuring, not a deferral.

## Warnings

1. **Documentation is the load-bearing wall.** The decision to enforce boundaries architecturally (adapter pattern + docs) rather than at runtime means the security of the claim restriction depends entirely on the GUI adapter being correctly implemented. If the engine documentation on agent-only operations is skipped during restructuring, the constraint exists only in this brief — which is insufficient.

2. **Deferred concurrency controls must be tracked.** The `next_id` race condition and TOCTOU lost-write risks are accepted for single-consumer operation but become data-loss scenarios with two concurrent consumers. These must be captured in the engine package's documentation (a `SECURITY.md`, docstring section, or inline comments) — not just in this brief. The GUI project must close these before shipping.

3. **`write_task` atomicity is platform-dependent.** `Path.replace()` is atomic on POSIX and atomic on Windows (NTFS `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`). This should be noted in the engine docs as a verified property, not an assumption.

## Confidence

**0.88** — High confidence in the position. The threat model is well-scoped (single-laptop, single-developer). The adapter-pattern boundary is architecturally clean. The main uncertainty is whether deferred items will be tracked and closed before the GUI ships — that's an execution risk, not a design risk.
