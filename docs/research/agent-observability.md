# Agent Observability: PydanticAI, Logfire, and Alternatives

> **Owning task:** #141 — Research: PydanticAI web UI and Logfire for agent observability
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

OwlBear uses PydanticAI agents with a rich hook system (`HookRegistry`, `HookedToolset`) and JSONL-based `UsageTracker` for token/cost tracking. Task #141 asks: should we add Logfire, OTel, or a custom observability layer?

**Key constraint:** OwlBear is a single-laptop daemon, not a distributed system. YAGNI applies heavily — we need *useful visibility*, not enterprise observability.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI Logfire docs | <https://ai.pydantic.dev/logfire/> | .95 | OTel instrumentation, `Agent.instrument_all()`, `send_to_logfire=False` pattern |
| Logfire pricing page | <https://pydantic.dev/pricing/> | .80 | Free tier: 10M spans/mo, 30-day retention; self-hosted: enterprise-only |
| Logfire self-hosted docs | <https://logfire.pydantic.dev/docs/reference/self-hosted/overview/> | .75 | Requires Kubernetes + Postgres + S3 + Dex IDP |
| otel-tui (OTel terminal UI) | <https://github.com/ymtdzzz/otel-tui> | .70 | Local OTel viewer via Docker, zero accounts needed |
| OwlBear hook system | `src/owlbear/core/hooks.py`, `tools/hooked.py` | .95 | Existing lifecycle events + HookedToolset pattern |
| OwlBear UsageTracker | `src/owlbear/memory/usage.py` | .90 | Existing JSONL token/cost tracking with time-windowed queries |

## 3. Analysis

### 3.1 What we already have

OwlBear's existing observability surface is broader than it might seem:

- **HookRegistry** — 9 lifecycle events (session start/end, pre/post tool, message, error, subagent, task, question)
- **HookedToolset** — wraps any toolset with pre/post hooks
- **UsageTracker** — per-request token counts, cost estimates, time-windowed aggregation
- **5 hook implementations** — CommandSafetyGuard, AutoLintHook, ContextInjectionHook, NotificationHook, URLSafetyGuard

**Gap:** no timing data on operations, no trace visualization, no structured event log queryable after the fact. Hooks fire-and-forget; `UsageTracker` captures cost but not *what happened*.

### 3.2 Options comparison

| Criterion | Logfire Cloud (.40) | Self-hosted Logfire (.15) | Raw OTel SDK (.55) | Hook-based structured log (.85) |
|-----------|-------------------|-----------------------|-------------------|---------------------------------|
| New deps | `logfire` (bundled) | Helm chart + K8s + PG + S3 | `opentelemetry-sdk`, exporter | 0 |
| Setup effort | Account + auth + project | Days of infra work | ~20 LOC config | ~80 LOC new hook |
| Data stays local | No (cloud) | Yes | Yes (local collector) | Yes (JSONL file) |
| Trace visualization | Excellent web UI | Same web UI, self-hosted | Needs separate viewer | Flat file (grep, jq) |
| PydanticAI integration | Native (2 lines) | Native | Native (`Agent.instrument_all()`) | Manual (hook callbacks) |
| KISS score | Medium | Very Low | Medium | High |
| YAGNI risk | High (enterprise features) | Extreme (K8s for a laptop) | Medium (extra deps, collector) | Low |
| Ongoing cost | Free tier likely sufficient | Infra + enterprise license | Free | Free |

### 3.3 Key insight: PydanticAI OTel is free to enable

`Agent.instrument_all()` uses the global OTel `TracerProvider`. With no provider configured, it's a no-op with zero overhead. This means we can unconditionally enable it and only pay the cost when a user configures an OTel backend. The `logfire` SDK is already bundled with `pydantic-ai`.

The `send_to_logfire=False` pattern lets us use the Logfire SDK purely as an OTel convenience layer — it auto-configures TracerProvider, OTLP exporter, and HTTPX instrumentation without sending anything to Logfire cloud.

## 4. Recommendation (.85 confidence)

**Layered approach: structured logging hook now + opt-in OTel later.**

### Layer 1 (build now): `ObservabilityHook`

A new hook registered on multiple lifecycle events that writes structured JSON events to a JSONL file (same pattern as `UsageTracker`). Each event captures:

- Timestamp, event type, duration (for pre/post pairs)
- Agent name, tool name, session ID
- Success/failure, error details
- Token usage snapshot (if available)

This gives immediate queryable visibility (`jq`, `grep`, or future CLI commands) with zero new dependencies.

### Layer 2 (build now, ~5 LOC): Unconditional `Agent.instrument_all()`

Call `Agent.instrument_all()` in `OwlBearAgent.__init__` or at daemon startup. Zero cost without a configured TracerProvider. When a user later wants OTel traces, they just set `OWLBEAR_OTEL_ENDPOINT`.

### Layer 3 (defer): Optional OTel backend config

Add `OWLBEAR_OTEL_ENDPOINT` config field. When set, configure the Logfire SDK with `send_to_logfire=False` pointing at the user's collector (otel-tui, Jaeger, etc.). This is ~15 LOC in config/daemon bootstrap.

### What NOT to do

- **Don't adopt Logfire Cloud** — sends data offsite, requires account management, most features irrelevant for single-user laptop daemon.
- **Don't self-host Logfire** — Kubernetes + Postgres + S3 for a laptop tool is absurd.
- **Don't add `structlog` or `loguru`** — Python stdlib `logging` + JSON is sufficient. KISS.

## 5. Follow-up Tasks

1. **ObservabilityHook** — new hook class writing structured JSONL events for all lifecycle events, with duration tracking for pre/post tool pairs
2. **Enable `Agent.instrument_all()`** — unconditional at daemon startup, zero-cost no-op by default
3. **Optional OTel endpoint config** — `OWLBEAR_OTEL_ENDPOINT` in `OwlBearSettings`, conditional TracerProvider setup in daemon bootstrap
