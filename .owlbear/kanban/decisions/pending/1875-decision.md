---
task_id: 1875
agent: researcher
request_type: decision
created: '2026-05-25'
response: pending
---

## AC/Protocol Discrepancies — Resolution Needed

The task AC conflicts with the authoritative EnrichmentStore protocol in 3 ways:

| AC Item | Protocol | Discrepancy |
|---------|----------|-------------|
| State: CLAIMED | EnrichmentState.IN_PROGRESS | Naming mismatch |
| fail_chunk(batch_id, chunk_id, error) → always FAILED | mark_failed(chunk_id, error) → retry if attempts < max_retries | Different semantics + signature |
| release_claim(batch_id) | Not defined | Missing from protocol |

Per ARCHITECTURE.md Spec Amendment Process: "Method signature changes or semantic obligation changes require a new CP entry."

### Options

1. **(rec:) Implement protocol as-is, add release_claim as non-protocol extension** — Protocol's mark_failed with retry logic is superior design. release_claim is additive (non-breaking). Amend AC to match protocol.
2. **Amend protocol to match AC** — Requires new CP entry. Would lose retry semantics. Gains batch-ownership verification on fail_chunk.
3. **Hybrid** — Keep protocol's mark_failed retry logic but add batch_id parameter. Add release_claim to protocol. Rename IN_PROGRESS → CLAIMED. Requires CP entry.

Recommendation: Option 1 (simplest, non-breaking, preserves retry logic). Architect can amend AC during architecture review.