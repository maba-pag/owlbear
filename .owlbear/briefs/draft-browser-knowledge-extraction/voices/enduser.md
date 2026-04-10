# End-User Voice — Authenticated Content Pipeline

## User Experience Stance

The pipeline should present two clear lifecycle modes (managed source vs. one-time extract), use discovery metadata to ground scope decisions before any content extraction, separate status detail from the chat interaction surface, and be ruthlessly honest about the constraints of a chat-based interface for large-scale review and long-running operations.

The core UX principle: **show the user what the system will do, let them adjust, then execute — and never hide state behind abstractions the user can't inspect.**

## Usability Reasoning

### 1. Two Lifecycle Modes — Managed Sources and Unmanaged Extracts

Two entry points with honest lifecycle differences:

- **"Extract this page"** — unmanaged. Content ingested with provenance tag: source URL, extraction date, "one-time extract" marker. No refresh, no status tracking, no source object. At search time, results carry the marker so the user knows freshness isn't maintained. Content ages naturally.
- **"Add this as a source"** — managed. Full lifecycle: discovery, review, scheduled refresh, status, clean removal.

**Promotion path**: Unmanaged extracts from the same domain can be promoted: "You've extracted 5 pages from this SharePoint site. Want to register it as a managed source?" This avoids forcing a governance decision at the moment of least knowledge.

**Inventory command**: "List my sources" returns both managed sources (with health status) and unmanaged extracts (grouped by domain, with extraction dates). This is the answer to "what has been ingested and how is it governed?"

### 2. Source Onboarding — Structured Proposal From Discovery Metadata

For managed sources:

a) Agent classifies source type (SharePoint site / Confluence space / standalone / GitHub)
b) Runs type-appropriate discovery — collects titles and structure only, no content extraction yet
c) Presents structured proposal with sample titles per category:
   - "SharePoint site: 47 pages in 5 sections — Security Policies (12) e.g. 'Data Classification Policy'; Architecture (8) e.g. 'Solution Blueprint v3'..."
   - Suggested cadence (weekly default)
   - Domain boundary (URL prefix scope)
   - Recommended exclusions with reasoning
d) User confirms scope → extraction begins

**Metadata limitation acknowledged**: Titles and hierarchy are imperfect proxies for value, especially on corporate sites with generic naming. For sources where titles are unclear, the agent offers a sample extraction of 3–5 pages after the user confirms a small initial scope: "Want me to extract 3 pages from Security Policies so you can see what the content looks like before committing to the full set?"

For 200+ page sources, the agent is honest: "This is a large source. Realistically, you're making a scope decision, not reviewing individual pages. I suggest ingesting the full site — you can prune sections later after seeing what's valuable. Or start with specific sections."

### 3. Page Review — Summary Default, File For Scale

Scale-appropriate review:

- **< 15 pages**: Full list in chat. Confirm directly.
- **15–50**: Categories with 3–4 sample titles each. Agent recommends exclusions. User can drill into any category.
- **50+**: Category summary in chat + full list in `.owlbear/scratch/source-review-{name}.md`. File is canonical once generated — agent confirms file state before acting: "Using page list from source-review-security.md: 42 include, 5 exclude. Proceed?"

**Overlap detection**: "3 pages already indexed from [other source]. Skip duplicates?"

**Honest about file review**: The file-based approach is a context switch. There is no better option in VS Code Copilot Chat for reviewing 50+ items. The alternative — a 50-line chat message — is worse. The agent makes the switch explicit and tracks which surface is current.

### 4. Browser Dependency — Session-Aware, Honest, Resumable

The browser is a live operational dependency, not a one-time setup:

- **Pre-flight**: Verify Edge CDP reachable + test auth before every extraction run
- **Mid-flight diagnosis**: Pattern detection at source level — "Auth appears expired — 5 consecutive login redirects" not "5 individual URL failures"
- **EDR/security awareness**: If CDP connection fails in patterns suggesting security software, name the possibility
- **Session interruption**: State file (`.owlbear/scratch/extraction-state-{id}.json`) tracks progress. "Interrupted extraction: 23/47 complete. Resume?"
- **Honest framing**: "This uses your live browser session. Edge must be open, logged in, and running with remote debugging."

### 5. Progress — Milestones to Chat, Detail to Log

Chat is not a status console. Separate the streams:

- **Chat**: Phase transitions + periodic checkpoints (~every 25% or ~2 min). "Extraction: 12/47 (26%). Continuing..."
- **Chat**: Action-required moments are visually distinct: "⚠ ACTION NEEDED: Auth expired. Re-authenticate in Edge."
- **Log file**: `.owlbear/scratch/extraction-log-{source}-{date}.md` — per-page detail, timing, entities, errors. Persistent record.
- **Final summary**: Always in chat. "Done. 45/47 extracted, 2 failed. 312 entities, 28 cross-source links. Full log: extraction-log-security-20260410.md"
- **Batching for large sources**: "180 pages — batches of 40? Review results between batches."

### 6. Source Attribution — Provenance, Not Authority

- **Managed results**: Source name, URL, system tag, knowledge type label (POLICY/REQUIREMENT/etc.), refresh date
- **Unmanaged results**: URL, extraction date, "one-time extract" tag — clearly distinguished from managed
- **Knowledge type is a metadata tag, not visual hierarchy**: "tagged: POLICY" — the system classifies, the user decides trust
- **Staleness as fact**: "Last refreshed 62 days ago (expected: weekly)"
- **Cross-source convergence**: "Referenced in 3 sources" — shows convergence without claiming authority

### 7. Error Recovery & Source Lifecycle

- **Source status on demand**: Agent responds to "status of my sources?" with current state from the underlying MCP tool. In a chat interface, there is no persistent dashboard — status is pull-based. The agent can also proactively surface issues: "FYI: Weekly refresh for Security SharePoint failed yesterday."
- **Source-level diagnosis first**: Multiple failures → "auth expired" not individual retry offers
- **Tiered recovery**: Source fix → batch retry → individual retry
- **Clean removal with impact**: "Remove this source? 45 docs, 312 entities deleted. 28 cross-links broken — shared entities keep other connections."
- **Domain boundaries persist in status**: Visible on demand, not just at onboarding
- **Refresh-time discovery**: When refresh finds new pages, they appear in a summary at the user's next interaction: "Last refresh added 5 new pages to Security SharePoint: [titles]. Auto-included because they're within your existing scope boundary. Review?" All auto-inclusions are reported — never silent corpus expansion.

## Key Trade-offs

| This approach costs... | But avoids... |
|---|---|
| Scope decisions based on titles/metadata rather than content | Extracting content before the user confirms scope |
| File-based review for large sets (context switch) | 50+ item chat lists that are unreadable and unreviewable |
| Pull-based status (user asks, agent answers) | Building a dashboard UI that doesn't exist in the platform |
| Batching large extractions (slower end-to-end) | 30-minute chat-blocking extraction runs |
| Two lifecycle modes (managed/unmanaged complexity) | False simplicity that hides governance gaps |
| Metadata-only provenance tags (not visual authority) | Authority amplification from imperfect classification |

## Warnings

1. **Chat interface is the binding constraint.** Many UX tensions (review at scale, progress visibility, status discoverability) trace back to Copilot Chat being the only interaction surface. Every proposed mitigation is a workaround, not a solution. If the pipeline grows to dozens of managed sources, chat-only management will strain.

2. **Metadata-based scope decisions are a known weak point.** For corporate sites with generic page names, titles alone don't convey value. The sample-extraction-after-initial-scope pattern partially mitigates this, but users will sometimes ingest low-value content and prune later.

3. **Refresh-time auto-inclusion needs careful boundary definition.** "Within your existing scope boundary" is straightforward for URL-prefix boundaries but ambiguous for Confluence spaces where hierarchy changes. Over time, silent auto-inclusions could expand the corpus beyond user expectations if boundaries aren't precisely defined.

4. **Browser dependency is a fragile operational requirement.** CDP + Edge + SSO + potential EDR interference creates a multi-point dependency chain. Every point can fail independently. The UX can diagnose and surface clearly, but cannot make the dependency less fragile.

5. **One-time extracts will accumulate.** Without a managed lifecycle, unmanaged content will grow stale indefinitely. The "promotion" path helps for frequently used domains, but the user needs periodic nudges: "You have 23 unmanaged extracts older than 90 days. Review or purge?"

## Confidence

0.78 — Position is well-hardened after 4 Critic cycles. Remaining uncertainty is structural (chat interface constraints) and inherent to the problem (metadata-based decisions), not in the approach itself. The Critic's later challenges were increasingly about inherent platform constraints rather than reasoning flaws.
