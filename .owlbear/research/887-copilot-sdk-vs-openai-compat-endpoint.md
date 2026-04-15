# Copilot SDK vs OpenAI-Compatible Endpoint for Knowledge Extraction LLM

> **Owning task:** #887 — Research: Copilot SDK vs OpenAI-compat endpoint for knowledge extraction LLM
> **Date:** 2026-04-15 **Status:** Complete

## 1. Context and Question

`LLMExtractor` (in `serve/knowledge/src/owlbear_knowledge/llm_extractor.py`) uses `openai.AsyncOpenAI` with `chat.completions.parse(response_format=ExtractionResult)` for structured entity/edge extraction. Today this requires an external OpenAI API key. Goal: replace that key requirement with the Copilot subscription already available.

Two candidate approaches: **(A)** GitHub Copilot SDK (`github-copilot-sdk` v0.2.2) and **(B)** OpenAI SDK pointed at the Copilot-internal endpoint via device-flow OAuth (as prototyped in Graphicator v1).

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `pypi.org/project/github-copilot-sdk/` — SDK README & API ref | PyPI | .95 |
| S2 | `github.com/github/copilot-sdk` — repo README + getting-started guide | GitHub | .95 |
| S3 | `github.com/ericc-ch/copilot-api` — reverse-eng OpenAI-compat proxy | GitHub | .85 |
| S4 | `.owlbear/research/copilot-auth.md` (task #30) — device-flow OAuth | Codebase | 1.0 |
| S5 | `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` | Codebase | 1.0 |
| S6 | `docs.github.com/en/copilot/concepts/billing/copilot-requests` | Docs | .80 |
| S7 | GitHub Copilot Acceptable Use Policies & ToS | Docs | .90 |

## 3. Analysis

### 3.1 Core Comparison

| Criterion | (A) Copilot SDK | (B) OpenAI SDK + Copilot endpoint |
|-----------|----------------|-----------------------------------|
| **Structured output (`response_format`)** | **Not supported.** SDK is agent/session-oriented — offers `session.send()` → text events. No completion-level `response_format` parameter. | **Supported.** `chat.completions.parse(response_format=ExtractionResult)` works at `api.individual.githubcopilot.com` (tested in Graphicator v1 — S4). |
| **Standalone Python process** | Requires Copilot CLI binary (bundled with pip install). Spawns subprocess via JSON-RPC. Heavy for a single extraction call (~200ms startup). | Yes — standard `AsyncOpenAI` client with `base_url` + `api_key` + editor headers. ~10 LOC delta from current code. |
| **ExtractionResult schema parsing** | Would require workaround: define a tool with ExtractionResult schema and instruct model to call it, then parse tool args. Fragile, over-engineered. | Direct via `response_format=ExtractionResult` — Pydantic model auto-converted to JSON schema. Already proven in task #875. |
| **Authentication** | Seamless — uses `copilot` CLI login, env vars (`COPILOT_GITHUB_TOKEN`, `GH_TOKEN`), or OAuth. Handles token refresh. | Device-flow OAuth → GitHub token → Copilot session token. Existing implementation in Graphicator (S4): `request_device_code` → `poll_for_access_token` → `exchange_for_copilot_token`. Requires faked editor headers (S4 §3.2). |
| **Rate limits** | Per Copilot subscription — premium request quotas. Each `session.send()` = 1 premium request × model multiplier. | Same Copilot quota. Each completion call = 1 premium request × model multiplier. |
| **Model availability** | All Copilot models via `list_models()` — GPT-4.1, GPT-5 mini, Claude Sonnet 4, etc. | Same models accessible at endpoint. GPT-4o-mini (current default) available. GPT-4.1 and GPT-5 mini are included (0× multiplier on paid plans). |
| **Official support** | **Official** — GitHub-maintained (8.4k stars), public preview. | **Unofficial** — reverse-engineered internal API. GitHub warns: "excessive automated use may trigger abuse-detection" (S3, S7). |
| **Code change delta** | Major rewrite — replace `AsyncOpenAI` with `CopilotClient`, rewrite to event-driven model, add CLI dependency. ~100+ LOC. | Minimal — add auth module (~120 LOC from Graphicator port), add editor headers to `AsyncOpenAI` constructor. `LLMExtractor` body unchanged. |
| **Dependency footprint** | `github-copilot-sdk` + Copilot CLI binary (~50MB). | `openai` (already present) + `httpx`/`truststore` (already present). |

### 3.2 Structured Output Feasibility Detail

| Approach | `response_format` native | Workaround | Reliability |
|----------|-------------------------|------------|-------------|
| (A) SDK session.send() | No | Tool-call hack: define tool with ExtractionResult schema, instruct model to call it | Low — model may not call tool, may add extra text |
| (A) SDK + BYOK reverse | N/A | Use SDK to start CLI, then bypass SDK and call endpoint directly | Defeats purpose of SDK |
| (B) OpenAI SDK direct | Yes | None needed | High — `parse()` guarantees schema-valid JSON |

### 3.3 Authentication Flow Comparison

| Step | (A) SDK | (B) Direct endpoint |
|------|---------|---------------------|
| Initial auth | `copilot` CLI login (interactive) or env var | Device-flow OAuth (interactive first time) |
| Token storage | Managed by CLI in `~/.copilot/` | Manual: `~/.owlbear/copilot_token.json` |
| Token refresh | Automatic (CLI handles) | Manual: check `expires_at`, re-exchange |
| Header requirements | None (SDK handles) | Must set: `Editor-Version`, `Editor-Plugin-Version`, `User-Agent`, `X-Github-Api-Version`, `Copilot-Integration-Id` (S4 §3.2–3.3) |

### 3.4 Risk Assessment

| Risk | (A) SDK | (B) Direct endpoint |
|------|---------|---------------------|
| API breakage | Low — official, versioned SDK | **High** — undocumented internal API, headers may change |
| ToS compliance | Compliant | **Uncertain** — faking editor headers may violate GitHub Acceptable Use Policy |
| Abuse detection | Low risk | **Medium** — automated bulk requests may trigger suspension (S3 warning, S7) |
| Maintenance burden | Low — SDK auto-updates | Medium — must track header/endpoint changes |

## 4. Recommendation (confidence: .65)

**Option B (OpenAI SDK + Copilot endpoint)** is the only technically viable approach for structured output extraction — but with significant caveats.

Option A (Copilot SDK) fails the primary AC requirement: it cannot provide `response_format`-based structured JSON output. The SDK is designed for agent workflows (send prompt → get text + tool calls), not raw completions. A tool-call workaround exists but is fragile and over-engineered for extraction.

Option B works technically — it's proven in Graphicator v1 and requires minimal code changes. However:

- **ToS risk**: Faking VS Code editor headers to impersonate an IDE client is a grey area. GitHub's abuse detection exists specifically for this pattern.
- **Fragility**: Internal API may change without notice. Header requirements have changed before.
- **No official migration path**: If GitHub detects and blocks the usage, there's no fallback except reverting to external API keys.

**Confidence is .65 (not .80+) because neither option is clearly safe.** The best path may be a third option not in the original scope: wait for the Copilot SDK to add a completions-level API (it's in public preview and rapidly evolving), or use `OWLBEAR_LLM_API_KEY` as-is (the current approach works).

Challenge: FALLBACK — challenger subagent not in available roster.

**Tier classification: T2 — Advisory.** Trade-off between functionality and ToS compliance. No T3 triggers (no architecture change proposed yet). Needs user decision on risk tolerance before implementation.

## 5. Follow-up Tasks

1. **If user accepts Option B risk**: Port Copilot device-flow auth from Graphicator — implement auth module + wire into `LLMExtractor` constructor.
2. **Monitor Copilot SDK**: Track `github/copilot-sdk` for raw completions/structured output API — re-evaluate when SDK exits preview.
3. **Fallback**: Keep `OWLBEAR_LLM_API_KEY` env var as primary path; Copilot endpoint as optional alternative.

---

## Monitoring Update — 2026-04-15 (Task #889)

### SDK Status: v0.2.2 (released 2026-04-10)

**Verdict: No change.** The SDK still does not support `response_format` or a completions-level API.

### Changelog Review (v0.2.0 → v0.2.2)

| Version | Date | Key Features | Structured Output? |
|---------|------|--------------|-------------------|
| v0.2.0 | 2026-03-20 | System prompt customization, telemetry, blob attachments, BYOK `wire_api`, agent pre-selection | No |
| v0.2.1 | 2026-04-03 | Commands + UI elicitation (all SDKs), `getMetadata`, `sessionFs` | No |
| v0.2.2 | 2026-04-10 | `enableConfigDiscovery` for auto MCP/skill loading | No |

### Open Feature Request

- **Issue #857** "Force structured output" — filed 2026-03-14, **still open**, no official response or milestone assignment observed.

### BYOK `wire_api` Note

The `ProviderConfig` for BYOK includes a `wire_api` field (`"completions"` or `"responses"`), but this only applies to custom providers with external API keys — it does not expose a completions API for Copilot's own models. Not a viable path for our use case.

### Recommendation

Original #887 recommendation (Option B with caveats, confidence .65) remains unchanged. Re-check in Q3 2026 or when SDK reaches v0.3.0 / GA. Watch issue #857 for movement.
