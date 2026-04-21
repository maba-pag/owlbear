# Security Stance — Critic Dialogue Log

**Panelist:** The Skeptic (ideation-security)
**Critic model:** Internal adversarial reasoning (ideation-critic unavailable as subagent)
**Cycles completed:** 3

---

## Cycle 1

### Position Presented

"The claim identity drop (D11) is acceptable because the real concurrency risk is the absence of file-level locking on task writes, not the absence of an identity token. Both `claim_task` and `end_work` do unlocked read→mutate→write. Identity would add a check that narrows the race window but doesn't close it. The optimistic concurrency token (`updated`) is the real mitigation — if required on all mutations, a zombie agent's stale token fails the write."

### Critic Challenge

You're conflating two distinct failure modes. Mode A: two agents race on claim — both read `claimed_by=None`, both write their claim, last writer wins. Mode B: zombie agent calls `end_work` after orchestrator released its claim and a new agent claimed. In Mode B, the zombie doesn't race on claim — it races on *end_work*, which unconditionally clears `claimed_at`. With identity, `end_work` would check `claimed_by == self` and fail for the zombie. Without identity, it succeeds silently. You say the optimistic token mitigates this, but does `end_work` even accept an `updated` token today? If not, and Brief B doesn't add one, your mitigation doesn't exist.

### Response

Valid challenge. Checking the landscape: `end_work` does NOT accept an `updated` token today (only Cockpit's `edit_task` uses it). The mitigation I proposed doesn't exist unless Brief B explicitly adds `updated` to `end_work`. Without either identity OR an optimistic token, `end_work` is completely unguarded — any caller can clobber any active claim and write to the body.

**Revised position:** The identity drop is acceptable ONLY IF Brief B mandates the `updated` optimistic token on `end_work` (and `start_work`, which delegates to `claim_task`). Without the token, `end_work` is an unguarded write — the zombie scenario produces silent data corruption. The token is the minimum viable concurrency guard for a claim-identity-free system.

---

## Cycle 2

### Position Presented

"Optimistic concurrency tokens should be required on ALL engine mutations exposed to MCP: `edit_task`, `move_task`, `end_work`. This is the primary data integrity mechanism in the absence of file-level locks. Making tokens optional is a data integrity hole."

### Critic Challenge

You say "required on all mutations" but you haven't addressed `start_work` and `create_task`. `start_work` reads the task, checks claim state, writes — same unlocked pattern. If two agents call `start_work` on the same task simultaneously, last writer wins. Requiring a token on `start_work` means the agent must `show_task` first to get the token, which is an extra round trip on the happy path. Is that cost justified for a single-user laptop? Also, `create_task` uses the `next_id` lock — is its concurrency already solved?

### Response

`create_task` is safe — the `_exclusive_file_lock` on `next_id` serializes creation. No token needed.

`start_work`: two agents racing on the same task is the orchestrator's fault (it should dispatch one task to one agent). The token would catch it, but the cost is a mandatory `show_task` before every `start_work`. On a single-user laptop with a single orchestrator, the two-agent-same-task scenario requires orchestrator bug. I'll classify this as low-risk and recommend token as optional on `start_work` — the orchestrator is the concurrency gate here, not the engine.

`end_work` is different: the zombie scenario is a crash recovery path, not an orchestrator bug. Crashes happen. Token required.

**Revised position:** Required tokens on `edit_task`, `move_task`, `end_work`. Optional on `start_work` (orchestrator is the gate). Not applicable to `create_task` (file lock covers it).

---

## Cycle 3

### Position Presented

"The activity.jsonl log is not audit in any meaningful sense. On a single-user laptop, any process can tamper with or delete it. Brief B should rename it to 'diagnostic log' and explicitly prohibit any engine semantic from depending on its contents."

### Critic Challenge

D10 already says "audit-only, outside engine semantics." You're restating the locked decision. What's your actual security position beyond what D10 already establishes? Is there a residual risk D10 doesn't address?

### Response

Fair — D10 covers the semantic demotion. My position adds two things D10 doesn't address:

1. **Curation ownership.** D10 says audit-only but doesn't say who manages the file. Without rotation or size limits, it grows unboundedly. An agent writing thousands of mutations fills the disk — DoS against the user's laptop. Brief B should specify: activity.jsonl is caller-managed (the launching script or Cockpit may rotate), engine makes no guarantees about file size. Max-size or rotation is a Brief C concern.

2. **Naming honesty.** Calling it "audit" implies tamper-evidence. On a laptop filesystem, it has none. Brief B should document: "diagnostic log with no integrity guarantees. Not suitable as evidence of agent behavior." This prevents future features from treating it as a trust anchor.

**Position stands with these two additions.**

### Critic Assessment

Position is solid on activity.jsonl. The curation ownership and naming honesty points are concrete and not covered by D10.

---
