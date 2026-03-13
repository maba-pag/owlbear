# PinchTab Research

> **Owning task:** #595 — Research: pinchtab/pinchtab
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

Evaluate [pinchtab/pinchtab](https://github.com/pinchtab/pinchtab) for reusable patterns in browser automation, local dashboarding, tab management, and developer workflows. OwlBear already has Playwright + CDP browser automation; the question is whether PinchTab offers architectural patterns worth adopting.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| pinchtab/pinchtab repo (cloned to `docs/research/pinchtab/`) | Primary — full source analysis | .85 |
| pinchtab README.md | Architecture overview, feature list, token cost guide | .80 |
| `internal/semantic/` package (matcher.go, combined_matcher.go, intent_cache.go, recovery.go) | Semantic element matching + self-healing pattern | .90 |
| `plugins/pinchtab/cli.py` + `plugin/index.ts` | MCP plugin + single-tool plugin design | .75 |
| `skill/pinchtab/SKILL.md` + `TRUST.md` | Skill definition + security model documentation | .70 |
| `internal/strategy/` + `internal/allocation/` | Pluggable strategy registry + allocation policies | .65 |
| `dashboard/` (Vite/React + SSE) | Real-time agent monitoring dashboard | .60 |

## 3. Analysis

### 3a. What PinchTab Is

A 12MB Go binary (MIT license) that wraps Chrome via chromedp, exposing browser control as an HTTP API + CLI. Key design choices: accessibility-tree snapshots instead of screenshots/DOM, stable element refs (`e0`, `e5`), token-efficient extraction (~800 tokens/page vs ~10,500 full).

### 3b. Patterns Relevant to OwlBear

| Pattern | Description | OwlBear relevance | Confidence |
|---------|-------------|-------------------|------------|
| **Accessibility-tree snapshots** | Extracts flat ref list from a11y tree; 5-13x cheaper than screenshots | High — OwlBear browser tools lack token-efficient page representation | .85 |
| **Semantic element recovery** | Intent cache stores what agent wanted; on stale refs, re-matches semantically against new snapshot | High — self-healing makes browser automation robust | .80 |
| **Combined matcher** | Lexical (Jaccard) + embedding (feature-hashing) fusion with configurable weights (0.6/0.4 default) | Medium — useful if OwlBear adds natural-language element targeting | .70 |
| **Single-tool plugin** | One `pinchtab` tool with `action` param covers all browser ops; minimizes LLM context bloat | Medium — contrasts with OwlBear's multi-tool approach | .65 |
| **TRUST.md** | Separate security/trust documentation per tool | Medium — aligns with OwlBear's safety-first approach | .60 |
| **Strategy registry** | `strategy.Register(name, factory)` + `OrchestratorAware` interface injection | Low — OwlBear already has similar patterns | .40 |
| **Auto-restart with backoff** | Exponential backoff crash recovery (3 max restarts, 2s initial, 5m stable reset) | Low — Playwright manages its own lifecycle | .35 |
| **Human input simulation** | Bézier curve mouse movement + timing jitter for stealth | Low — niche, Playwright has built-in alternatives | .30 |
| **Embedded dashboard + SSE** | Vite/React app embedded in Go binary via `go:embed`, SSE for real-time events | Low — OwlBear uses Slack/CLI channels, not a web dashboard | .25 |

### 3c. Token Cost Model (from SKILL.md)

| Method | Tokens | When to use |
|--------|--------|-------------|
| `/text` | ~800 | Reading page content |
| `/snapshot?filter=interactive&format=compact` | ~56-64% less than full | Finding clickable elements |
| `/snapshot?diff=true` | varies | Multi-step workflows (only changes) |
| `/snapshot` (full) | ~10,500 | Full page understanding |
| `/screenshot` | ~2K (vision) | Visual verification |

This tiered approach — default to cheapest, escalate only when needed — is the most transferable pattern.

### 3d. Hashing Embedder (Zero-Dep Matching)

PinchTab's `HashingEmbedder` uses feature-hashing (FNV hash + char n-grams) to produce fixed-dim vectors without any ML model. Combined with Jaccard lexical scoring, it achieves usable element matching with zero external dependencies. This is clever for a self-contained binary but inferior to real embeddings for OwlBear (which already has BGE-M3).

### 3e. IDPI — Indirect Prompt Injection Defense

PinchTab implements a 3-layer defense against indirect prompt injection in `internal/idpi/`:

1. **Domain whitelisting** (`domain.go`) — block navigation to non-approved domains
2. **Content scanning** (`content.go`) — detect ~40 known injection phrases in extracted page content (case-insensitive: "ignore previous instructions", "you are now a", "execute the following command", "exfiltrate", etc.)
3. **Content wrapping** — wrap plain-text output in `<untrusted_web_content>` delimiters with a safety advisory for downstream LLMs

The `CheckResult` struct returns: `Threat` (bool), `Blocked` (bool, only in strict mode), `Reason` (human-readable), `Pattern` (matched string).

**OwlBear gap:** OwlBear has `URLSafetyGuard` (equivalent to layer 1) but **no content-level injection scanning** (layer 2) and **no untrusted content wrapping** (layer 3). Web-extracted content flows directly into LLM context without sanitization markers. This is a security gap for any agent that browses untrusted sites.

## 4. Recommendation (.80 confidence)

**Adopt selectively:** Three patterns are worth implementing as OwlBear enhancements.

1. **IDPI content scanning** (.85) — Port PinchTab's prompt injection phrase detection to OwlBear's `browser_read_text` and `extract_content` output paths. Implement as a configurable hook/guard. The ~40 builtin patterns are a strong starting list.

2. **Untrusted content wrapping** (.90) — Wrap all web-extracted text in `<untrusted_web_content>` delimiters before passing to LLM context. Simple, zero-cost defense-in-depth.

3. **Token-efficient browser snapshots** (.85) — Add accessibility-tree extraction to OwlBear's `BrowserManager`. Playwright's `page.accessibility.snapshot()` already exists, so the implementation effort is low. Expose as a `browser_snapshot` tool alongside existing `share_screenshot`.

4. **Tiered extraction strategy** (.80) — Adopt PinchTab's token-cost-aware approach: default to text extraction (~800 tokens), use interactive-only a11y snapshot for actions, full snapshot only when needed. Agent prompt should include this cost table.

**Not recommended:**

- Single-tool design — OwlBear's multi-tool approach is more discoverable for agents.
- Strategy registry pattern — already exists in OwlBear's codebase.
- Human input simulation — too niche; Playwright's slow_mo and built-in waits suffice.
- Web dashboard — OwlBear uses Slack/CLI channels, adding a web dashboard violates YAGNI.
- Semantic element recovery — compelling concept but premature; OwlBear's browser automation needs stability before optimization.

## 5. Follow-up Tasks

Created on the kanban board:

- **#724** — Add IDPI content scanning to browser content extraction (needed, security)
- **#725** — Add untrusted content wrapping for web-extracted text (needed, security)
- **#726** — Add accessibility-tree snapshot to BrowserManager (important)
- **#727** — Add browser_snapshot tool to BrowserToolset (important, depends on #726)

## 6. What Was NOT Useful

- Go-specific implementation (not applicable to Python stack)
- Multi-instance orchestrator (OwlBear uses single browser instance)
- OpenClaw/SMCP plugin contract (OwlBear has its own toolset system)
- Docker/npm packaging (different distribution model)
