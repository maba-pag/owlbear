# claude-context-mode Feature Evaluation for OwlBear

> **Owning task:** #745 — Research mksglu/claude-context-mode for OwlBear
> **Date:** 2026-03-12 **Status:** Complete

## 1. Context and Question

Evaluate mksglu/claude-context-mode (Elastic-2.0, 3.4k+ stars, npm `context-mode`) for patterns that could improve OwlBear's context window efficiency and session continuity. The repo is an MCP server + hook system that sandboxes tool output (98% context savings claimed) and persists session state across context compaction.

Sub-questions: (1) Which features fill gaps vs what OwlBear already has? (2) What effort/value trade-off for each? (3) What's blocked by architectural differences (Node.js MCP server vs Python daemon)?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| mksglu/claude-context-mode (v1.0.18) | <https://github.com/mksglu/claude-context-mode> | 1.0 — primary target |
| context-mode BENCHMARK.md | (cloned repo) | .90 — quantitative claims |
| OwlBear openclaw-ecosystem.md | docs/research/openclaw-ecosystem.md | .85 — prior condenser/session research |
| OwlBear context-condenser.md | docs/research/context-condenser.md | .90 — existing condenser design |

## 3. Analysis

### 3a. Feature Inventory — context-mode

| Feature | Description | LOC (est.) |
|---------|-------------|------------|
| **Sandbox execution** | Spawn subprocesses, only return stdout to context | ~300 (executor.ts) |
| **FTS5 knowledge base** | Chunk markdown → SQLite FTS5 → BM25 search | ~400 (store.ts) |
| **Smart truncation** | Head 60% + tail 40%, line-boundary snapping | ~80 (truncate.ts) |
| **Session event capture** | Extract 13 event categories from tool calls | ~250 (session/extract.ts) |
| **Session snapshot** | Priority-tiered XML within 2KB budget | ~200 (session/snapshot.ts) |
| **PreToolUse routing** | Hook-based tool interception + redirect to sandbox | ~200 (hooks/) |
| **Security policies** | Deny-list patterns for commands and file paths | ~150 (security.ts) |
| **Exit classification** | Soft-fail for shell exit code 1 with stdout | ~30 (exit-classify.ts) |
| **Progressive throttling** | Degrade search results after repeated queries | ~20 (server.ts) |
| **Multi-platform adapters** | Claude Code, Gemini, Cursor, VS Code Copilot, Codex, OpenCode | ~500 (adapters/) |

### 3b. Gap Analysis — OwlBear vs context-mode

| Feature | OwlBear Current | context-mode | Gap? |
|---------|----------------|--------------|------|
| Output truncation | Head+tail 60KB (terminal), max_length (browser/web) | Head 60% + tail 40%, line-boundary aware | Minor — OwlBear has this |
| Context condenser | `SummarizingCondenser` — LLM summarization | N/A (relies on hooks + snapshot) | **OwlBear ahead** |
| Session persistence | `SessionStore` JSONL + `SessionMemoryHook` | SQLite events + FTS5-indexed resume | Comparable approach |
| Knowledge indexing | SQLite graph + Qdrant vectors + BGE-M3 | SQLite FTS5 + BM25 (simpler) | **OwlBear ahead** |
| Sandbox execution | `TerminalToolset` with workspace confinement | Polyglot executor (11 languages) | Comparable |
| Tool routing hooks | `HookRegistry` (PRE/POST_TOOL_USE, SESSION_*) | Platform-specific hook adapters | Comparable |
| Command security | `CommandSafetyGuard` blocklist | Glob-based deny/allow policies | Comparable |
| Content safety | `ContentInjectionGuard` + `wrap_untrusted_content` | N/A | **OwlBear ahead** |
| Exit classification | Not formal | Soft-fail for shell exit 1 | **Minor gap** |
| WIP continuity | `WipStore` per-task JSONL | Session resume snapshot | Comparable |
| Progressive throttle | None | Search result degradation after N calls | **Minor gap** |

### 3c. Candidate Features — Trade-off Matrix

| Feature | Value (.0–1.0) | Effort | KISS/YAGNI | Confidence |
|---------|---------------|--------|------------|------------|
| Smart truncation (line-boundary) | .55 | ~20 LOC | High KISS | .70 |
| Exit classify (soft-fail) | .40 | ~15 LOC | High KISS | .65 |
| Session event extraction | .30 | ~250 LOC | Low KISS, overlaps condenser | .40 |
| FTS5 knowledge base | .20 | ~400 LOC | Violates DRY — Qdrant+BGE-M3 exists | .25 |
| Sandbox executor (polyglot) | .15 | ~300 LOC | YAGNI — TerminalToolset covers this | .20 |
| Progressive throttling | .35 | ~20 LOC | Medium KISS | .55 |
| Platform adapters | .10 | ~500 LOC | YAGNI — OwlBear is standalone daemon | .15 |
| Priority-tiered snapshot | .45 | ~100 LOC | Medium KISS, complements condenser | .55 |

### 3d. Deeper Evaluation of Top Candidates

**1. Smart truncation — line-boundary snapping (.70 confidence)**

OwlBear's `_truncate()` in `terminal.py` splits at character boundaries, which can produce broken lines. context-mode's `smartTruncate()` snaps to line boundaries and uses 60/40 head/tail split. This is a ~20 LOC improvement to an existing function — minimal risk, immediate value.

Sources: context-mode `truncate.ts` L38–L75, OwlBear `terminal.py` L57–L70.

**2. Priority-tiered session snapshot (.55 confidence)**

context-mode's snapshot builder allocates a 2KB budget across priority tiers (P1: files/tasks/rules 50%, P2: errors/git/decisions 35%, P3-P4: tools/intent 15%). OwlBear's `SummarizingCondenser` does full LLM summarization — more powerful but more expensive. A lightweight structured snapshot could complement the condenser as a fallback when LLM summarization is unavailable or as a fast pre-compaction state capture. However, this is additive complexity and OwlBear's condenser may already cover this need. **Consider, don't adopt.**

**3. Exit classification (.65 confidence)**

Treating shell exit code 1 with non-empty stdout as "soft fail" (not an error) prevents false error reporting from commands like `grep` that exit 1 when matching nothing. Simple pattern, trivial to implement.

Sources: context-mode `exit-classify.ts` L1–L35, OwlBear `terminal.py`.

**4. Progressive throttling (.55 confidence)**

Degrading search results after repeated queries (1–3: full, 4–8: reduced, 9+: blocked with redirect) prevents the model from wasting context on repetitive searches. Could apply to OwlBear's knowledge query service. Low effort but unclear if OwlBear's usage patterns trigger this issue. **Consider, don't adopt.**

## 4. Recommendation (.70 confidence)

### Adopt (2 patterns)

| Pattern | Source | Effort | Rationale |
|---------|--------|--------|-----------|
| Line-boundary truncation | truncate.ts | ~20 LOC | Direct improvement to `_truncate()` — prevents broken lines |
| Soft-fail exit classification | exit-classify.ts | ~15 LOC | Prevents false errors from `grep`, `diff`, `find` |

### Consider for later (2 patterns)

| Pattern | Source | Confidence | Rationale |
|---------|--------|------------|-----------|
| Priority-tiered snapshot | session/snapshot.ts | .55 | Complement to condenser, but may be YAGNI |
| Progressive query throttle | server.ts | .55 | Prevents context waste, but usage patterns unclear |

### Reject (4 patterns)

| Pattern | Reason |
|---------|--------|
| FTS5 knowledge base | DRY violation — Qdrant+BGE-M3 is superior |
| Polyglot sandbox executor | YAGNI — TerminalToolset with sandbox_path covers this |
| Platform adapters | YAGNI — OwlBear is standalone daemon, not multi-platform MCP |
| Full session event extraction (13 categories) | OwlBear's condenser + session memory hook already covers this with less complexity |

### Key insight

context-mode solves a problem OwlBear largely doesn't have: it's designed for ephemeral chat-based coding agents (Claude Code, Gemini CLI) that lack persistent state. OwlBear already has a daemon architecture with persistent session stores, a knowledge graph, and LLM-based condensation. The two small patterns above (truncation, exit classification) are the highest-value, lowest-risk extractions.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Improve terminal output truncation with line-boundary snapping" --priority nice-to-have --tags "scope:core,tooling" --status backlog --body "Upgrade _truncate() in src/owlbear/tools/terminal.py to snap to line boundaries instead of splitting mid-line. Adopt 60/40 head/tail split ratio. Pattern from context-mode truncate.ts.\n\nSee docs/research/claude-context-mode.md S3d.1.\n\nAC:\n- [ ] _truncate() snaps to newline boundaries (never cuts mid-line)\n- [ ] Head gets 60% of budget, tail gets 40%\n- [ ] Truncation marker shows line/KB counts: [N lines / X.YKB truncated — showing first A + last B lines]\n- [ ] Existing tests updated\n- [ ] No behavior change for output under max_bytes"

kanban\kanban-md.exe create "Add soft-fail exit classification for terminal commands" --priority nice-to-have --tags "scope:core,tooling" --status backlog --body "Treat shell exit code 1 with non-empty stdout as soft failure (not error). Commands like grep, diff, find exit 1 for 'no matches' — not real errors. Pattern from context-mode exit-classify.ts.\n\nSee docs/research/claude-context-mode.md S3d.3.\n\nAC:\n- [ ] classify_exit() function in terminal.py (or standalone module)\n- [ ] Exit 1 + non-empty stdout = soft fail (return stdout, not error)\n- [ ] Other non-zero exits = real error (return combined stdout+stderr)\n- [ ] TerminalToolset.run_command() uses classify_exit()\n- [ ] Tests cover grep-no-match, diff-differences, real failures"
```
