# First-Principles Stance — Knowledge Source Lifecycle

## Irreducible Core

Three things are actually broken:

1. **Health data is hidden.** The model stores `last_error`, `last_refreshed_at`, `enabled` — the API returns 4 of 13 fields. This is a bug, not a missing feature.
2. **Refresh lies.** Browser-sourced refresh silently no-ops when the fetcher isn't wired, then marks the source as refreshed. Agents trust this signal. This is a correctness defect.
3. **Direct-ingest conflates two intents.** A one-shot "here's a document" import creates a source record shaped like a managed recurring source. These are different things: provenance tracking vs. refresh-managed source.

Everything else in the framing is inherited structure built on top of these three.

## Assumptions Challenged

### "Sources need full lifecycle management via MCP tools"

At 10–50 sources with rare churn, source registration is a **configuration activity**, not a runtime operation. You set up sources when you onboard a knowledge domain; you don't dynamically register and deregister them during agent work. A YAML manifest edited by the operator (which already exists as `kb-load`) covers this. The question to answer: when would an agent autonomously decide to register or remove a knowledge source? If the answer is "the operator tells it to," you've reinvented a config file with extra steps.

Register and remove as MCP tools solve a problem that hasn't been demonstrated. Refresh already exists. The gap is visibility and correctness, not CRUD surface.

### "Three creation paths is the problem"

Three paths serving different intents is not inherently broken. Manifest handles bulk setup. Direct-ingest handles ad-hoc documents. Browser onboarding handles interactive discovery. The problem is that direct-ingest **pretends its output is the same kind of record** as a manifest-declared source. The fix is a type distinction (managed vs. one-shot provenance), not path unification.

### "The model exists, therefore the management surface should exist"

The 13-field `KnowledgeSource` model was designed for internal bookkeeping. The framing assumes that because the model is rich, a correspondingly rich user-facing management surface is warranted. This is cargo-culting. The model can stay rich for internal use while the user-facing surface stays narrow: see health, trigger refresh, flag broken things.

## What Happens If You Do Nothing

- Direct-ingest keeps creating ambiguous records → mild mess at 10–50 scale, no operational failure
- `list_sources` stays blind to health → agents can't detect stale sources → **real problem**, they make decisions on data they assume is fresh
- Browser refresh keeps lying → **real problem**, false freshness corrupts agent trust in knowledge quality
- No register/remove MCP tools → operator uses existing CLI/YAML → **workable**

The system doesn't collapse. But items 2 and 3 silently degrade knowledge quality, which undermines the core value prop (authenticated + public sources with cross-source relationships). If agents can't trust freshness, cross-source mapping is unreliable.

## Reframing

The framing presents this as "build a source lifecycle management system." The irreducible problem is: **agents can't tell when knowledge is stale or broken, and one refresh path lies about success.**

O2 (health visibility) is the real problem. O3 (clean semantics for direct-ingest records) is a data modeling clarification worth doing. O1 (full lifecycle CRUD) is premature — it solves an administrative convenience problem that barely exists at this scale.

Minimum viable fix:
1. `list_sources` returns health fields (trivial — data already exists)
2. Refresh fails loudly when browser isn't wired (bug fix)
3. Direct-ingest records get a flag distinguishing them from managed sources (schema tweak)

None of these require designing a lifecycle management system.

## Confidence

**0.82** — High confidence that O1 is premature and the real problems are narrower. Moderate uncertainty about whether the operator will eventually want MCP-driven registration (possible, but not yet demonstrated as a need vs. a nice-to-have).
