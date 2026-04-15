# Copilot Device-Flow Auth Port — Feasibility & Implementation Research

> **Owning task:** #888 — Port Copilot device-flow auth from Graphicator for LLMExtractor
> **Date:** 2026-04-15 **Status:** Complete

## 1. Context and Question

Task #888 proposes porting Graphicator's device-flow OAuth into `serve/knowledge/` so `LLMExtractor` can use Copilot without an external API key. Prerequisite research (#887) recommended Option B (OpenAI SDK + Copilot endpoint) as the only technically viable path but flagged ToS risk at .65 confidence. This research validates the #887 findings are current, assesses implementation feasibility, and defines the decision boundary.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `.owlbear/research/887-copilot-sdk-vs-openai-compat-endpoint.md` | Codebase | 1.0 |
| S2 | `.owlbear/research/copilot-auth.md` (task #30) | Codebase | 1.0 |
| S3 | `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` | Codebase | 1.0 |
| S4 | `serve/knowledge/pyproject.toml` — current deps | Codebase | .90 |
| S5 | `pypi.org/project/github-copilot-sdk/` — v0.2.2 API ref (Apr 10, 2026) | PyPI | .95 |
| S6 | `github.com/github/copilot-sdk` — README, features, BYOK docs | GitHub | .95 |
| S7 | `github.com/ericc-ch/copilot-api` — reverse-eng proxy, warnings | GitHub | .85 |

## 3. Analysis

### 3.1 SDK Update Validation (v0.2.2, Apr 10, 2026)

| Capability | v0.2.2 Status | Impact on #888 |
|-----------|---------------|----------------|
| `response_format` / structured output | **Still absent.** API is `session.send()` events only. | SDK path (Option A) remains infeasible |
| BYOK / Custom Provider | Added. Routes through CLI subprocess via JSON-RPC. | Does not expose raw completions — still event-driven |
| `wire_api: "completions"` | Internal format between SDK and CLI, not user-facing | No change to structured output gap |
| Auth methods | GitHub OAuth, env vars, BYOK | BYOK bypasses Copilot entirely (uses own keys) |

**Conclusion:** #887 analysis is current. No re-evaluation needed. Option B remains sole path.

### 3.2 Implementation Feasibility

| Criterion | Assessment |
|-----------|------------|
| Code delta from Graphicator | ~120 LOC auth module (S2 §4.1), ~10 LOC LLMExtractor change |
| Dependency additions | `httpx>=0.27` (already in `intake` extra), `truststore` (new, ~50KB) |
| Token management | File-based JSON cache at `~/.owlbear/copilot_token.json` (S2 §5) |
| LLMExtractor integration | Add `default_headers` to `AsyncOpenAI` constructor — body unchanged |
| Test coverage | 13 tests from Graphicator as template (S2 §6), all mockable |
| Architecture fit | Clean — new module in `serve/knowledge/`, no cross-package deps |

### 3.3 Implementation Approach (if user approves)

```
serve/knowledge/src/owlbear_knowledge/copilot_auth.py  (NEW, ~120 LOC)
├── Constants: CLIENT_ID, URLs, EDITOR_HEADERS, INTEGRATION_HEADER
├── _ssl_context() / _http_client()
├── request_device_code() / poll_for_access_token() / exchange_for_copilot_token()
├── derive_base_url()
├── save_token() / load_token()
└── get_copilot_token()  (cache-first entry point)

serve/knowledge/src/owlbear_knowledge/llm_extractor.py  (MODIFY, ~10 LOC)
└── __init__(): accept optional default_headers dict, pass to AsyncOpenAI

serve/knowledge/pyproject.toml  (MODIFY)
└── Add optional dep group: copilot = ["httpx>=0.27", "truststore"]

serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py  (MODIFY)
└── Lifespan: try copilot auth when OWLBEAR_LLM_API_KEY not set
```

### 3.4 Risk Matrix

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| ToS violation — faking editor headers | High | Medium | User accepts risk; Copilot-only, low-volume extraction |
| Abuse detection — automated access suspended | High | Medium | Rate-limit extraction; graceful fallback to no-op |
| API breakage — headers/endpoint change | Medium | Medium | Make headers configurable; monitor copilot-api project |
| Token security — cached credentials | Low | Low | File permissions, `~/.owlbear/` user-scoped |
| SDK adds completions API — work becomes obsolete | Low | Low | Task #889 monitors; port is ~120 LOC, low sunk cost |

### 3.5 copilot-api Proxy Warning (S7)

The copilot-api proxy (3.7k stars) now carries prominent warnings:
> "Excessive automated or scripted use of Copilot may trigger GitHub's abuse-detection systems. You may receive a warning from GitHub Security, and further anomalous activity could result in temporary suspension of your Copilot access."

This confirms the risk #887 identified is actively enforced, not theoretical.

## 4. Recommendation (confidence: .70)

**Proceed with implementation ONLY after explicit user approval of ToS risk.** Implementation itself is straightforward (.90 confidence on technical feasibility), but the ToS/abuse-detection risk keeps overall confidence at .70.

Three options for the user:

| Option | Description | Risk | Effort |
|--------|------------|------|--------|
| **A: Proceed** | Port auth, wire into LLMExtractor as optional fallback | ToS grey-area, abuse detection possible | ~2 tasks |
| **B: Wait** | Monitor SDK (#889) for structured output API | Zero risk, unknown timeline | None now |
| **C: Status quo** | Keep `OWLBEAR_LLM_API_KEY` as-is | Zero risk | None |

**(rec:) Option A with safeguards** — if user accepts risk: rate-limit extraction calls, use `Copilot-Integration-Id: vscode-chat` (matches legitimate usage), graceful fallback on auth failure.

**(bp:) Option C** — safest. External API key works. No ToS exposure.

**Tier: T3 — Mandatory decision.** Triggers: adds new capability, alters security posture (token management + impersonating IDE client), changes user-facing behavior (extraction without API key). Blocking DR required before implementation.

Challenge: FALLBACK — challenger subagent not in available roster.

## 5. Follow-up Tasks

- **#888** (this task) — advance to backlog, awaits T3 decision before implementation
- **#889** (exists) — monitor SDK for structured output support
- DR needed: ToS compliance decision — scribe unavailable, documented in task body
