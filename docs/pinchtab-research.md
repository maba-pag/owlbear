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

## 4. Recommendation (.75 confidence)

**Adopt selectively:** Two patterns are worth implementing as OwlBear enhancements.

1. **Token-efficient browser snapshots** (.85) — Add accessibility-tree extraction to OwlBear's `BrowserManager`. Playwright's `page.accessibility.snapshot()` already exists, so the implementation effort is low. Expose as a `browser_snapshot` tool alongside existing `share_screenshot`.

2. **Tiered extraction strategy** (.80) — Adopt PinchTab's token-cost-aware approach: default to text extraction (~800 tokens), use interactive-only a11y snapshot for actions, full snapshot only when needed. Agent prompt should include this cost table.

**Not recommended:**

- Single-tool design — OwlBear's multi-tool approach is more discoverable for agents.
- Strategy registry pattern — already exists in OwlBear's codebase.
- Human input simulation — too niche; Playwright's slow_mo and built-in waits suffice.
- Web dashboard — OwlBear uses Slack/CLI channels, adding a web dashboard violates YAGNI.
- Semantic element recovery — compelling concept but premature; OwlBear's browser automation needs stability before optimization.

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add accessibility-tree snapshot to BrowserManager" --priority needed --tags "phase-browser,scope:core,browser" --body "**Source:** docs/pinchtab-research.md S4.1\n\nAdd a `snapshot()` method to BrowserManager that returns Playwright's `page.accessibility.snapshot()` as a flat ref list. Filter modes: interactive-only, full, text-only.\n\n**AC:**\n- [ ] BrowserManager.snapshot() returns parsed a11y tree\n- [ ] Filter parameter: interactive | full | text\n- [ ] Output format matches PinchTab's ref schema (id, role, text, selector)\n- [ ] Tests with mocked Playwright page"

kanban\kanban-md.exe create "Add browser_snapshot tool to VisualFeedbackToolset" --priority important --tags "phase-browser,scope:core,browser" --depends-on "Add accessibility-tree snapshot to BrowserManager" --body "**Source:** docs/pinchtab-research.md S4.1\n\nExpose BrowserManager.snapshot() as a `browser_snapshot` tool. Include token-cost guidance in tool description so agents prefer cheap extraction.\n\n**AC:**\n- [ ] browser_snapshot tool registered in VisualFeedbackToolset\n- [ ] Tool description includes token cost guide (text ~800, interactive ~3600, full ~10500)\n- [ ] Agents can request filter=interactive for action-oriented tasks\n- [ ] Tests verify tool output schema"
```

## 6. What Was NOT Useful

- Go-specific implementation (not applicable to Python stack)
- Multi-instance orchestrator (OwlBear uses single browser instance)
- OpenClaw/SMCP plugin contract (OwlBear has its own toolset system)
- Docker/npm packaging (different distribution model)
