# RichChannel Protocol for Approval Gate — Design Decision

> **Owning task:** #558 — Consider RichChannel protocol for approval gate
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

ARC-07 flags that `ApprovalGateToolset.call_tool()` uses `hasattr(self.channel, "send_blocks")` at runtime to dispatch between Slack Block Kit and plain text approval prompts. The question: should we introduce a `RichChannel` protocol, keep the `hasattr` pattern, or take a different approach?

## 2. Sources Studied

| Source | What | Relevance |
|---|---|---|
| PEP 544 (python.org/pep-0544) | Protocol default bodies, rejected "optional members" proposal | 1.0 |
| mypy Protocol docs (mypy.readthedocs.io) | `isinstance()` with protocols "can be surprisingly slow"; `hasattr` is pragmatic alternative | 0.9 |
| OwlBear `docs/channel-protocol-extension-research.md` (#482) | Full analysis of 3 options with trade-off matrix; recommends widening ChannelPlugin | 1.0 |
| OwlBear `docs/architecture-audit.md` §ARC-07 | Original finding: minor duck-typing in gate.py | 1.0 |
| OwlBear `docs/integration-audit.md` §INT-06 | Same issue scoped broader: 3 `hasattr` sites across gate.py + screenshot.py | 1.0 |

## 3. Analysis

### Checklist item 1: Is `hasattr` acceptable duck-typing?

**Yes, conditionally.** PEP 544 explicitly rejected optional protocol members — Python's type system has no native way to say "this method may or may not exist." The mypy docs even note that `isinstance()` with `@runtime_checkable` protocols "can be surprisingly slow" and suggest `hasattr` as a pragmatic alternative. However, `hasattr` bypasses static type checking entirely — Pylance/mypy can't verify the method signature, and callers need `# type: ignore[attr-defined]` annotations. The pattern is acceptable for a handful of sites but scales poorly.

### Checklist item 2: Prior art — capability-based dispatch

| Pattern | Used by | Assessment |
|---|---|---|
| `hasattr()` duck-typing | CPython stdlib (e.g., `copy.copy`), Django middleware | Works, but no static typing benefit |
| Separate narrower Protocols | typing stdlib (`SupportsAbs`, `SupportsFloat`) | Clean for single-method capabilities; verbose for multiple |
| Protocol with default bodies | PEP 544 §defining-a-protocol (explicitly supported) | **Best fit** — one protocol, fallback behavior built in |
| ABC mixin | zope.interface, older Django | Over-engineered for this use case |

### Checklist item 3: Technical feasibility

The `hasattr` pattern appears in exactly 3 sites (gate.py:100, screenshot.py:60, screenshot.py:62). A `RichChannel` protocol would replace `hasattr` with `isinstance` checks — same branching, different spelling, no real improvement. Widening `ChannelPlugin` with defaults eliminates branching entirely.

### Checklist item 4: Architecture fit — RichChannel adds no value

| Criterion | RichChannel protocol | Widen ChannelPlugin (Option A from #482) |
|---|---|---|
| KISS | Two protocols, consumers must choose | One protocol, no branching |
| Consumer impact | `isinstance(ch, RichChannel)` replaces `hasattr` — same branching | Delete all `hasattr` checks — call methods directly |
| Type safety | Better than `hasattr`, but still requires narrowing | Full static typing on one protocol |
| Testing | Two mocks, conditional branches remain | One mock, no conditionals |
| YAGNI | Extra abstraction for 1 consumer (gate.py) | Minimal addition to existing protocol |

### Checklist item 5: Implementation approach

**This task is a duplicate of #482.** The channel-protocol-extension research already analyzed all three options and recommended widening `ChannelPlugin` with `.85` confidence. The specific changes needed are documented in `docs/channel-protocol-extension-research.md` §5.

## 4. Recommendation (.90 confidence)

**Do not create a `RichChannel` protocol.** Instead, proceed with #482 (widen `ChannelPlugin` with default fallback implementations). This eliminates all `hasattr` duck-typing, including the ARC-07 finding, in a single change that is simpler, more testable, and fully type-safe.

**Rationale:**

- A `RichChannel` protocol replaces `hasattr` with `isinstance` — same branching, no real improvement
- PEP 544 explicitly supports default method bodies in Protocols — this is the idiomatic solution
- The existing research (#482) already covers this with a concrete implementation plan
- KISS and YAGNI both point to widening the existing protocol, not adding a new one

## 5. Follow-up Tasks

No new tasks needed — #482 already covers the implementation. This task (#558) should be closed as a duplicate with a reference to #482.

## 6. Disposition

Task #558 is subsumed by #482 ("Extend ChannelPlugin protocol for rich capabilities"). The ARC-07 finding will be resolved when #482 is implemented. Mark #558 as done with a note pointing to #482.
