# Security Stance — Brief B: Kanban Engine API

**Panelist:** The Skeptic (ideation-security)
**Threat model:** Single-user laptop, single project, concurrent local agents via MCP, Cockpit on 127.0.0.1, no auth.
**Critic cycles:** 3 (see `stances/security-debate.md`)

---

## 1. Claim Identity Drop (D11) — What Fails Open

**Position: Acceptable ONLY if optimistic concurrency token is required on `end_work`.**

The zombie agent scenario is the concrete risk. Agent A claims task 42 and begins work. A becomes slow (not crashed — its process lives). Orchestrator times out A's claim, releases it. Agent B claims task 42. A's zombie process calls `end_work(42)`:

- **Without identity AND without token:** `end_work` succeeds. It clears B's `claimed_at`, overwrites `updated`, appends A's stale note to body. B's active work session is silently clobbered. B discovers the problem only when its next write fails or — worse — it doesn't discover it at all.
- **Without identity BUT with required token:** A's `end_work` carries a stale `updated` token (from before the release/re-claim cycle). `ConcurrencyError` rejects the write. B's claim is safe.

Code evidence: `end_work` at [engine.py L872-960](serve/kanban/src/owlbear_kanban/engine.py) does an unlocked read→mutate→write with no concurrency guard. `claim_task` at [engine.py L758-784](serve/kanban/src/owlbear_kanban/engine.py) likewise has no file lock. The `_exclusive_file_lock` exists only for `next_id` allocation in `create_task`.

The identity check would narrow the window (A checks `claimed_by == self`, fails if B claimed). But without file-level locking, even that check has a TOCTOU gap. The optimistic token is a stronger guard — it detects ANY intervening mutation, not just claim ownership changes.

**Verdict:** D11's identity drop is safe because the optimistic token is a strictly better concurrency gate. But this safety depends entirely on Q1's resolution: the token MUST be required on `end_work`. If Q1 makes tokens optional, D11 becomes a silent-corruption hole.

---

## 2. Role Views Without Runtime Guards (D9 + Q5)

**Position: Type-level contract is sufficient for this threat model. AST test is the enforcement mechanism.**

If a future Cockpit route accidentally calls `engine.start_work()` — e.g., someone imports `KanbanEngine` directly instead of using `engine.cockpit_view()` — the call succeeds silently. There's no runtime `PermissionError`. The engine doesn't know or care who's calling.

On a single-user laptop, this is a developer-error risk, not a security risk. The blast radius is one task getting an unexpected claim with `claimed_by="cockpit"`. No data leaves the machine; no privilege escalation occurs.

**Mitigation Brief B must specify:** An AST/import test that scans all Cockpit route files and verifies they access only `CockpitEngineView` methods. The landscape already notes ([red flag #12](landscape.md)) that Cockpit mutation routes bypass the adapter today — D21 rewires this, but without a CI-enforced test, it will regress.

The test already has a partial precedent: `test_cockpit_boundary.py` checks denied methods on the adapter. Brief B should extend this to verify that route source files never reference the full engine or `AgentEngineView`.

**Verdict:** No runtime guard needed. Type contract + AST test is proportionate to the threat model.

---

## 3. Optimistic Concurrency — Required vs Optional (Q1)

**Position: Required on `edit_task`, `move_task`, and `end_work`. Optional on `start_work`. Not applicable to `create_task`.**

This is the single most security-adjacent open question. Without file-level locks on task writes (confirmed: only `create_task` has the `_exclusive_file_lock`), the `updated` token is the ONLY mechanism preventing silent lost updates between concurrent agents.

| Operation | Token Required? | Rationale |
|-----------|----------------|-----------|
| `edit_task` | **Yes** | Arbitrary field mutation. Lost update = silent data reversion. |
| `move_task` | **Yes** | Status transition. Lost update = state machine corruption. |
| `end_work` | **Yes** | Writes body + clears claim + advances status. Zombie agent scenario (§1). |
| `start_work` | Optional | Two-agent race requires orchestrator bug. Orchestrator is the concurrency gate. Extra `show_task` round trip not justified for low-probability scenario. |
| `create_task` | N/A | `_exclusive_file_lock` on `next_id` serializes creation. |

**If Q1 resolves to "optional":** Two MCP agents editing the same task silently overwrite each other. The second write wins, the first write's changes vanish. On a single-user laptop, this happens when the orchestrator dispatches overlapping edits or when a human edits via Cockpit while an agent works. Neither scenario is exotic.

**Recommendation:** The MCP adapter should fetch `updated` from the engine response of the preceding operation (which agents already have from `show_task` or `start_work`) and pass it through. The cost is near-zero for well-behaved agents. The benefit is preventing a class of silent corruption that's undetectable after the fact.

---

## 4. `activity.jsonl` — Audit-Only (D10)

**Position: D10 is correct. Two gaps remain.**

D10 correctly demotes the log to outside engine semantics. The security stance adds:

1. **Curation ownership is unspecified.** Without rotation or size cap, an agent writing thousands of mutations fills the user's disk. This is a self-inflicted DoS — low severity but real. Brief B should specify: engine writes append-only; curation (rotation, truncation, deletion) is the launching script's or Cockpit's responsibility. Engine makes no file-size guarantees.

2. **"Audit" is a misleading name.** On a laptop filesystem, any process can truncate, edit, or delete `activity.jsonl`. There are no write-once guarantees, no checksums, no append-only filesystem semantics. Calling it "audit" implies tamper-evidence it cannot provide. Brief B should document: *"Diagnostic log with no integrity guarantees. Not suitable as evidence of agent behavior in any dispute or compliance context."* This prevents future features from treating it as a trust anchor.

**No engine semantic may read from `activity.jsonl` for correctness.** `list_sessions()` per D10 derives from task claim state. If a future feature needs reliable history, it must be stored as engine-semantic state (Brief C scope), not parsed from an unguarded log.

---

## 5. Error-Message Leakage (Landscape Red Flag #7)

**Position: Brief B's exception taxonomy must define a two-tier message policy.**

Current state: `ToolError(str(exc))` in the MCP adapter forwards raw Python exceptions to calling agents. This leaks:
- File paths (`/Users/markus/.owlbear/kanban/tasks/42-fix-something.md`)
- Config internals (`Valid options: ['backlog', 'todo', ...]`)
- Stack-adjacent details (`No task file matching {task_id}-*.md`)

On a single-user laptop, path leakage is not a confidentiality risk — the user owns the files. But it IS a problem because:
- **Agent confusion:** LLM agents parse error messages and may attempt to "fix" paths, creating phantom actions.
- **Brief A contract:** §4 specifies "no storage details leak into caller code." `ToolError(str(FileNotFoundError))` violates this.

**Required in Brief B:** Each exception class in the taxonomy carries:
- `user_message: str` — safe for the wire. Generic, storage-agnostic. Example: `"task 42 not found"`, not `"no file matching 42-*.md in /path/to/tasks/"`.
- `detail: str | None` — for logging/diagnostics only. Never forwarded to MCP or Cockpit HTTP responses.

MCP adapter maps: `raise ToolError(exc.user_message)`. Cockpit routes map: `HTTPException(status_code=..., detail=exc.user_message)`. Raw `str(exc)` must never reach the wire.

---

## 6. Cross-Reference Validation Timing

**Position: Accept the race. Specify the assumption. Harden the read path.**

Brief A requires write-time existence checks on `parent`, `depends_on`, `archival_refs`. Race condition: Agent A validates that task 50 exists, Agent B archives task 50, Agent A writes `depends_on=[50]`. Result: dangling reference.

On a single-user laptop, this requires two agents hitting the same task within the microsecond gap between validation and write. Probability: negligible but non-zero.

**Brief B should specify:**
1. **Write-time validation is best-effort.** Existence check at validation time; no distributed transaction.
2. **Read-path tolerance.** `dep_status` computation must handle missing deps gracefully — a dep that disappears between writes produces `dep_status="blocked"` (conservative), not a crash. The engine never raises on a dangling `depends_on` at read time.
3. **Assumption:** Storage operations are atomic at the single-task level (read or write completes fully or not at all). This is Brief C's obligation.

**Verdict:** The race is not worth preventing. The cost (per-task file locking on all writes) vastly exceeds the risk (sub-microsecond window, self-correcting via dep_status). Document it as a known limitation.

---

## 7. DoS via Long Body + Section Regex

**Position: Low risk. Operational cap, not security control.**

The landscape shows the clarity gate uses `^\s*(-\s|\d+\.\s)` — line-anchored, no backtracking risk. However, Brief B introduces section extraction (`show_task(section=...)`) which scans body text for `## Heading` matches. On a 100MB body, this is slow.

On a single-user laptop, a 100MB task body is self-inflicted. No external attacker can write task bodies (no auth ≠ no boundary — Cockpit is 127.0.0.1 only, and agents write through MCP which requires local process access).

**Recommendation:** Brief B should specify a **max body size** (e.g., 1MB) enforced at `edit_task`/`create_task` write time. This is an operational sanity cap, not a security control. Reject with `ValidationError` if body exceeds the limit. This also protects against accidental agent loops that append indefinitely.

---

## 8. ID Exhaustion / Wraparound

**Position: Non-issue. Validate input.**

Python integers have arbitrary precision — no overflow or wraparound. `next_id` is monotonic and file-lock-protected. The only risk is corruption: someone manually edits `.next_id` to a negative number or non-integer.

**Recommendation:** Brief B should specify: `next_id` must be a positive integer ≥ 1. `create_task` raises `CorruptionError` if the value fails this check. No max cap needed.

---

## 9. Symlink Attacks on tasks_dir / archive_dir

**Position: Low risk. Document the assumption.**

The engine uses `os.scandir()` on `tasks_dir` and `archive_dir`, following symlinks by default. A symlink in `tasks_dir` pointing outside the kanban directory would cause the engine to read/write an arbitrary file as if it were a task.

On a single-user laptop, creating such a symlink requires local filesystem access — which means either the user did it intentionally, or a compromised agent used a shell tool. MCP tools cannot create symlinks; only `create_task` writes new files, and it constructs the path from `tasks_dir / f"{task_id}-{slug}.md"`.

**Recommendation:** Brief B should state the assumption: *"tasks_dir and archive_dir contain only regular files and directories. Engine behavior when encountering symlinks, device files, or other non-regular entries is undefined."* Actual enforcement (e.g., `stat` check before read) is a Brief C storage concern.

---

## Risk Assessment Summary

| Risk | Severity | Probability | Verdict |
|------|----------|-------------|---------|
| Zombie agent clobbers active claim via `end_work` | **High** (silent data corruption) | Medium (any agent crash/timeout) | **Mitigate:** require `updated` token on `end_work` |
| Silent lost update on concurrent `edit_task` | **High** (silent data loss) | Medium (overlapping agent edits) | **Mitigate:** require `updated` token |
| Cockpit route bypasses role view | Low (developer error) | Low (caught in review) | **Mitigate:** AST test in CI |
| Error message leaks file paths | Low (no confidentiality risk) | High (every error today) | **Mitigate:** two-tier message policy |
| Cross-reference validation race | Low (dangling ref, self-correcting) | Very low (microsecond window) | **Accept.** Document assumption. |
| DoS via large body | Low (self-inflicted) | Low | **Mitigate:** max body size cap |
| activity.jsonl tampering | Very low (no security semantic) | N/A | **Accept.** Rename to diagnostic log. |
| Symlink in tasks_dir | Very low (requires local access) | Very low | **Accept.** Document assumption. |
| ID exhaustion | None (Python bigint) | None | **Accept.** Validate positive int. |

---

## Recommendations for Q1–Q9

| Question | Security Position |
|----------|------------------|
| **Q1 (optimistic token)** | **Required** on `edit_task`, `move_task`, `end_work`. This is the primary concurrency safety mechanism. Optional → silent corruption. |
| **Q2 (clarity gate predicate)** | No security impact. Tighter predicates reduce false dispatches but don't affect trust boundaries. |
| **Q3 (Section model)** | No security impact. Heading level preservation is a data fidelity concern. |
| **Q4 (exception taxonomy)** | **Security-adjacent.** Two-tier `user_message` / `detail` required. See §5 above. |
| **Q5 (pick_waves algorithm)** | No direct security impact. Deterministic ordering prevents scheduling starvation but not a trust boundary concern. |
| **Q6 (agent_map shape)** | No security impact. Single vs multi-agent is an operational design choice. |
| **Q7 (claim_timeout format)** | Minor operational risk. Validate at config-load time, not at first claim. Delayed validation = delayed failure = harder debugging. |
| **Q8 (wire format for body)** | No security impact. Structured vs string is a data fidelity concern. |
| **Q9 (sessions response scope)** | No security impact given D10. Narrowing to "running+stuck" is consistent with audit-demotion. |

---

## Warnings

1. **Q1 is a blocking security dependency for D11.** If tokens remain optional, the identity drop creates an unguarded write path on `end_work`. These two decisions are coupled — they must be resolved together.
2. **The exception taxonomy (Q4) is not optional polish.** Without it, Brief A's "no storage details leak" contract is unenforceable at the engine level. Every `ToolError(str(exc))` is a contract violation.
3. **`claim_timeout` validation at config load (Q7)** is a defense-in-depth concern: delayed validation means the first `claim_task` call after a config typo fails with an opaque parse error instead of a clear "invalid claim_timeout in config.yml" at startup. Brief B should specify eager validation.

## Confidence

**0.85.** High confidence on the core positions (token requirement, error taxonomy, role view enforcement). Moderate uncertainty on whether the zombie agent scenario justifies mandatory tokens on `end_work` given that the orchestrator *should* wait for confirmation before re-dispatching. The "should" is doing a lot of work — crash recovery is inherently messy.
