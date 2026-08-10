# Decisions — Knowledge Source Lifecycle Ownership

## D0 — 2026-05-17 — Project Type

**Status quo:** No prior project-type decision for this ideation.
**Decision to make:** Classify work as net-new, existing-feature/refactor, or uncertain.

**Options considered:**

- A: Net-new — treating source lifecycle as a new feature
- B: Existing-feature/refactor — the data model, store, and partial tool surface exist; this decides ownership and fills gaps

**Chosen:** B (existing-feature/refactor)

**Rejected:**

- A because the KnowledgeSource model, KnowledgeSourceStore CRUD, manifest loader, and partial MCP tool surface already exist. This is about deciding which surfaces own lifecycle operations and filling the gaps, not building from scratch.

**Source inputs:**

- Codebase: `models.py`, `source_store.py`, `refresh.py`, `loader.py`, `server.py` all exist with working source management primitives.
- Prior briefs: Knowledge Activation and Browser Knowledge Extraction both assumed source management exists.

## D1 — 2026-05-17 — Investment Tier

**Status quo:** No tier decision yet.
**Decision to make:** Calibrate depth of ideation analysis.

**Options considered:**

- A: Scratch — quick spike
- B: Tool — standard depth, single user
- C: Shared — full panel, research bridge, thorough analysis
- D: Production — maximum rigor

**Chosen:** C (Shared)

**Rejected:**

- A, B because the decisions shape the tool surface consumed by multiple agents and the operator. Multi-consumer, external integration complexity (authenticated corporate sources).
- D because this is an internal system, not external-facing. Shared rigor is sufficient.

**Source inputs:**

- User confirmed Shared tier.

## D2 — 2026-05-17 — Scope After Early Challenge

**Status quo:** Original framing asked "where does source lifecycle belong: MCP tools, manifest, Cockpit, or hybrid?"
**Decision to make:** Accept the challengers' narrow reframing or stick with the broader lifecycle management framing.

**Options considered:**

- A: Narrow scope — fix bugs (refresh honesty, direct-ingest semantics), expose hidden health data in `list_sources`, add `remove_source` tool. ~4 focused tasks.
- B: Medium scope — A plus a `register_source` tool and a plan for manifest/file-based source declaration.
- C: Full lifecycle management system — formal register/edit/toggle/inspect/remove tools, manifest format, Cockpit UI plan.

**Chosen:** A (narrow scope)

**Rejected:**

- B because `ingest_document` already creates source records. A separate `register_source` tool is premature at 10-50 sources.
- C because both challengers (simplifier @ 0.85 confidence, first-principles @ 0.80) independently concluded the real problems are 3 bugs/gaps, not a missing management system. Enterprise lifecycle patterns don't apply at this scale.

**Source inputs:**

- Simplifier stance: "the gap is consistency, not ceremony"
- First-principles stance: "the ownership question dissolves" when you fix bugs and expose data
- User: accepted narrow scope

## D3 — 2026-05-18 — Refresh Timestamp Semantics (T2)

**Status quo:** `last_refreshed_at` is unconditionally bumped — meaningless as health signal.
**Decision to make:** Single field with one semantic, or two fields with distinct meanings?

**Options considered:**

- A: Single field "last verified" — bump when refreshed + partial + skipped > 0
- B: Single field "last acquired" — bump only when refreshed > 0 or partial > 0
- C: Two-field split — `last_checked_at` (new, any non-zero counter) + `last_refreshed_at` (existing, content acquisition only)

**Chosen:** C (two-field split, corrected after Critic to bump `last_checked_at` on ANY non-zero counter including `failed`)

**Rejected:**

- A because it conflates "confirmed current" with "content changed" — operator needs both signals
- B because stable sources that skip every refresh look perpetually stale

**Source inputs:**

- User: "we need both. we need last checked and last updated."
- Critic correction: pure-failure refreshes must also bump `last_checked_at` (system IS watching)

## D4 — 2026-05-18 — Direct-Ingest Source Typing (T1)

**Status quo:** Direct-ingest HTTP sources typed `AUTHENTICATED_WEB` with `fetch_method="http"` — works but misleading.
**Decision to make:** Retype, document, or defer?

**Options considered:**

- A: Retype to `URL_LIST` — change `_direct_source_config` for new sources only
- B: Keep and document — add code comment, no behavior change
- C: Defer to separate task — exclude from Brief

**Chosen:** A (retype to URL_LIST)

**Rejected:**

- B because semantic debt remains and agents can't trust source_type
- C because user chose to include in scope

**Source inputs:**

- Architect stance: URL_LIST has its own simpler handler, eliminates spurious content-fetcher dependency
- Data stance (dissenting): changes runtime handler dispatch, not just label — acknowledged as risk
- AC gate: handler equivalence must be verified; O3 drops from work package if equivalence fails

## D5 — 2026-05-18 — Enrich in SourceInfo (T3)

**Status quo:** `enrich` boolean not exposed in `list_sources`.
**Decision to make:** Include in expanded health response?

**Options considered:**

- A: Include — low cost, operationally useful
- B: Exclude — processing config, not health signal

**Chosen:** B (exclude)

**Rejected:**

- A because the expanded response already has 9 fields; `enrich` is a config toggle, not a health signal

## D6 — 2026-05-18 — Dry-Run for remove_source (T4)

**Status quo:** No `remove_source` tool exists.
**Decision to make:** Include dry-run preview parameter?

**Options considered:**

- A: Include dry-run — defense-in-depth preview before commit
- B: Post-execution counts only — destructiveHint + counts + audit log

**Chosen:** B (post-execution counts only)

**Rejected:**

- A because destructiveHint is the real safety gate; re-ingestion recovers from mistakes at this scale; adds ~30% implementation effort

## D7 — 2026-05-18 — Error Sanitization (Critic C3)

**Status quo:** `_update_source_record` joins raw error strings from handlers.
**Decision to make:** Sanitize `last_error` at write-time or store as-is?

**Options considered:**

- A: Sanitize at write-time — error class + safe context only
- B: Store raw — consistent with existing `refresh_source` response contract

**Chosen:** B (store raw)

**Rejected:**

- A because laptop-resident single-user system; raw errors are the most useful diagnostic signal; sanitization creates three inconsistent error surfaces (sanitized writes + raw refresh_source + raw legacy values)

## D8 — 2026-05-18 — O4 Failure Model (Critic C-R1)

**Status quo:** No `remove_source` tool exists.
**Decision to make:** How should the tool handle Qdrant being unreachable during cascade delete?

**Options considered:**

- A: Vectors-first, abort on failure — attempt Qdrant cleanup first, abort entire operation if vectors can't be deleted, source stays intact
- B: Proceed with warning — delete SQLite data regardless, warn about orphaned vectors

**Chosen:** A (vectors-first, abort on failure)

**Rejected:**

- B because half-deleted state is worse than no deletion; at 10-50 sources on a laptop, Qdrant unavailability is transient
