# Extending ChannelPlugin Protocol for Rich Capabilities

> **Owning task:** #482 — Extend ChannelPlugin protocol for rich capabilities
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

`ChannelPlugin` defines only `name`, `send`, `receive`. `SlackChannel` adds `send_blocks`, `send_image`, `register_action`. `CLIChannel` adds `send_file`. Consumers use `hasattr` duck-typing in 3 locations:

| Location | Check | Purpose |
|---|---|---|
| `safety/gate.py:100` | `hasattr(channel, "send_blocks")` | Slack Block Kit vs plain text approval |
| `tools/screenshot.py:60` | `hasattr(channel, "send_image")` | Deliver screenshot as image |
| `tools/screenshot.py:62` | `hasattr(channel, "send_file")` | Deliver screenshot as file path |

Additionally, `screenshot.py` types its channel parameter as `object` instead of `ChannelPlugin`.

**Goal:** eliminate all `hasattr` channel checks; every capability must be protocol-defined.

## 2. Sources Studied

| Source | What | Relevance |
|---|---|---|
| PEP 544 (Protocols: Structural subtyping) | Protocol semantics: default bodies, inheritance, `runtime_checkable` | 1.0 — authoritative spec |
| mypy Protocol docs (mypy.readthedocs.io/en/stable/protocols.html) | Default method bodies in Protocols, mixin pattern, Protocol inheritance | 0.9 — canonical type checker docs |
| OwlBear `channels/base.py` | Current `ChannelPlugin` protocol with 3 methods | 1.0 — our codebase |
| OwlBear `docs/architecture-audit.md` §ARC-10 | "Define `RichChannelPlugin` or add optional methods with defaults" | 1.0 — prior audit |
| OwlBear `docs/integration-audit.md` §INT-06 | Channel method matrix showing capability gaps | 1.0 — prior audit |

## 3. Current Channel Method Matrix

| Method | `ChannelPlugin` | `CLIChannel` | `SlackChannel` | Consumers |
|---|---|---|---|---|
| `name` | ✅ | ✅ | ✅ | everywhere |
| `send` | ✅ | ✅ | ✅ | everywhere |
| `receive` | ✅ | ✅ | ✅ | gate, ask_user |
| `send_file` | ❌ | ✅ | ❌ | screenshot.py |
| `send_blocks` | ❌ | ❌ | ✅ | gate.py |
| `send_image` | ❌ | ❌ | ✅ | screenshot.py |
| `register_action` | ❌ | ❌ | ✅ | (unused) |

## 4. Approach Analysis

### Option A: Widen `ChannelPlugin` with default no-ops (.85 confidence)

Add `send_file`, `send_blocks`, `send_image` to `ChannelPlugin` with default implementations that delegate to `send()`. Every channel inherits sensible fallbacks.

| Criterion | Assessment |
|---|---|
| KISS | **Best.** One protocol, no hierarchy, no type narrowing anywhere |
| Breaking change | None — existing channels already satisfy the wider protocol structurally. Channels that don't implement a method get the fallback |
| Consumer impact | Delete all `hasattr` checks. Just call the method — fallback is built in |
| Type safety | Consumers type as `ChannelPlugin` everywhere. No `object` annotations |
| Testing | Mock one protocol. No conditional test paths |
| PEP 544 compat | ✅ Protocols can have default method bodies (PEP 544 §default-method-bodies). Structural subtyping still works — concrete classes that define the method use theirs; those that don't get the Protocol's default only if they inherit from it explicitly |

**Key PEP 544 nuance:** Default bodies in a Protocol work as real defaults only for classes that explicitly inherit `ChannelPlugin`. For purely structural (non-inheriting) classes, mypy still checks the method exists. Since both `CLIChannel` and `SlackChannel` can explicitly inherit `ChannelPlugin`, this is fine. We should make both channels inherit from `ChannelPlugin` directly.

**Default implementations:**
- `send_file(path, caption)` → `await self.send(f"[{caption}] {path}")`
- `send_blocks(blocks, text_fallback)` → `await self.send(text_fallback)`
- `send_image(file_or_bytes, caption)` → `await self.send(caption or "[image]")`

### Option B: Separate `RichChannelPlugin(ChannelPlugin, Protocol)` (.50 confidence)

| Criterion | Assessment |
|---|---|
| KISS | **Worse.** Two protocols. Every consumer must decide which to accept |
| Consumer impact | `isinstance(channel, RichChannelPlugin)` replaces `hasattr` — same branching, different spelling |
| Type safety | Consumers accepting `ChannelPlugin` can't call rich methods without narrowing |
| Testing | Two protocol specs to mock, conditional paths remain |

**Verdict:** Trades `hasattr` for `isinstance` checks — doesn't solve the fundamental problem.

### Option C: ABC mixin with defaults (.40 confidence)

| Criterion | Assessment |
|---|---|
| KISS | **Worst.** Mixin + Protocol + inheritance = 3 concepts |
| PEP 544 compat | ABCs and Protocols don't mix cleanly — can't be `runtime_checkable` and ABC |
| Consumer impact | Must inherit from mixin, losing structural subtyping benefits |

**Verdict:** Over-engineered. Violates YAGNI.

## 5. Recommendation (.85 confidence)

**Option A: Widen `ChannelPlugin` with default fallback implementations.**

Concrete changes:

1. Add `send_file`, `send_blocks`, `send_image` to `ChannelPlugin` protocol with default bodies that delegate to `send()`.
2. Make `CLIChannel` and `SlackChannel` explicitly inherit from `ChannelPlugin` (enables default inheritance for any missing methods).
3. Remove all 3 `hasattr` checks in `gate.py` and `screenshot.py` — just call the method directly.
4. Retype `screenshot.py:deliver(channel: object)` → `channel: ChannelPlugin`.
5. Do NOT add `register_action` to the protocol — it has zero consumers in production code and is Slack-specific interactive plumbing.

**Risks:**
- `SlackChannel` lacks `send_file` — gets the fallback `send(f"[{caption}] {path}")`. Acceptable: Slack can render file paths as text. If upload is desired later, `SlackChannel` can override.

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add send_file/send_blocks/send_image defaults to ChannelPlugin" --priority needed --status backlog --tags "audit,refactor,channels" --body "Widen ChannelPlugin protocol in channels/base.py with 3 method defaults that delegate to send(). Make CLIChannel and SlackChannel explicitly inherit ChannelPlugin. See docs/research/channel-protocol-extension.md §5. AC: (1) ChannelPlugin defines send_file, send_blocks, send_image with default fallbacks. (2) CLIChannel and SlackChannel inherit ChannelPlugin. (3) All existing tests still pass."

kanban\kanban-md.exe create "Remove hasattr channel duck-typing from production code" --priority needed --status backlog --tags "audit,refactor,channels" --depends-on 482 --body "Replace 3 hasattr checks with direct method calls now that ChannelPlugin has defaults. See docs/research/channel-protocol-extension.md §5. AC: (1) Zero hasattr.*channel matches in src/. (2) screenshot.py deliver() typed as ChannelPlugin, not object. (3) gate.py calls channel.send_blocks() directly. (4) All tests pass, ruff clean."
```
