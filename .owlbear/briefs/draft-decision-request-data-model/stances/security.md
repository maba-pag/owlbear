# Security Stance — Decision Request Data Model

## Threat Model

Two adversary classes for this single-user, laptop-resident system:

**Primary — Buggy LLM agents.** A hallucinating or confused agent produces malformed, oversized, or structurally unexpected content. Defense posture: protect data integrity and human oversight visibility from agent errors. This is the high-frequency threat.

**Secondary — Cross-origin browser attacks.** The Cockpit runs on localhost:8420, auto-opens in a browser, and exposes mutating REST endpoints. A malicious site in another tab can attempt cross-origin requests. Defense: mutation endpoints require `Content-Type: application/json`, which triggers CORS preflight. Absent permissive CORS headers, browsers block the request. This boundary is thin but real — it must be maintained as an explicit invariant, not an implicit absence of configuration.

**Non-threats (for this system):**
- Remote network attackers (localhost-bound, no port forwarding)
- Insider threats / privilege escalation (single user owns everything)
- Supply-chain attacks on decision files (clone=install, user trusts their own repo)

## Agent-Created Content: Validation Requirements

### Engine-Controlled Serialization

Agents submit structured data via MCP tools (Pydantic-validated). The engine serializes to YAML frontmatter. **Agents never write raw YAML to disk.** This eliminates YAML injection at the serialization boundary.

### Field-Level Validation (Engine Authority)

| Field | Constraint | Rationale |
|-------|-----------|-----------|
| `title` | string, 1–120 chars | Display safety, prevents bloat |
| `summary` | string, 0–500 chars | Bounded context |
| `option_id` | `^[a-z0-9][a-z0-9-]*$`, max 64 chars | Slug-safe: no path traversal, no YAML key injection, URL-safe |
| `option.label` | string, 1–200 chars | Display safety |
| `option.rationale` | string, 0–1000 chars | Bounded agent explanation |
| `option.confidence` | float 0.0–1.0 | Bounded numeric |
| `option.recommended` | boolean | Type-safe |
| `body` | markdown string, max 10000 chars | Prevents unbounded agent output |
| `kind` | enum: `decision` \| `action` | Closed set |

### Option-Set Integrity

- **Uniqueness:** option_ids must be unique within a request. Engine rejects duplicates at creation.
- **Count bounds:** Decisions require 2–8 options. Actions have no options.
- **Immutability:** Options are frozen after creation. No modification — only resolution against the existing set.

### Markdown Body

Stored as-is. Markdown is the intended format — sanitization at storage time is inappropriate. **However**, this content propagates to task bodies on resolution (see Propagation Boundary below).

## MCP Resolve Tool: Strong No

**Position:** Agents MUST NOT have a resolve tool in the default MCP surface.

**Enforcement mechanism:** The MCP tool surface is the access control boundary. Agents interact with the system exclusively through exposed MCP tools. They do not have arbitrary HTTP access to the Cockpit API. If no `resolve_request` MCP tool exists, agents cannot resolve. This is tool-level access control — stronger than auth, because the capability simply doesn't exist.

**Why:** Decision requests exist to force human attention on blocking choices. If agents can self-resolve, the system degrades from "human-in-the-loop oversight" to "agent-to-agent messaging that humans might notice." The blocking mechanism loses its purpose.

**If added later (gate conditions):**
- Separate, explicitly-named tool (not same as `create_request`)
- `resolver_agent` field, must differ from creating agent (no self-resolution)
- `allow_agent_resolution: true` must be set on the request at creation time (opt-in)
- Resolution marked `resolved_by: agent:{name}` — distinguishable from human resolution
- Auditable: different resolution path in engine, different SSE event type

## Resolution Write-Back Safety

### Engine Controls Output

The resolver submits structured data: `selected_option_id` (nullable), `free_text` (nullable, max 2000 chars), `resolved_by`, `resolved_at`. The engine formats a canonical summary and appends it to the task body.

### option_id as Lookup Key

The engine validates `selected_option_id` against the request's actual option list. Invalid IDs are **rejected** (error response), never echoed as content. This prevents a confused or malicious option_id from injecting arbitrary text.

### Write-Back Format

The appended summary uses a machine-identifiable delimiter:

```markdown
<!-- dr-resolution:{request_id} -->
## Decision: {title}

> **Selected:** {option.label}
> **Rationale:** {option.rationale}
> **Notes:** {free_text or "—"}
```

The HTML comment marker allows downstream consumers to identify resolution blocks without fragile regex. Agent instructions should treat resolution blocks as read-only context, not authoritative commands.

### Atomicity

Resolution must use rename-as-check: attempt `rename(pending/{id}.md, resolved/{id}.md)` as the commit step. If the source file is gone (already resolved or deleted), the rename fails atomically. Perform task-body write-back and unblock only after successful rename. This eliminates the TOCTOU race where two callers both observe "pending."

## Malformed Request Observability

**Problem:** If a buggy agent creates a file that fails YAML parse, the task stays `blocked=True` but the DR is invisible in Cockpit. This is a denial-of-service on the task — the primary adversary can trigger the primary failure mode with no human visibility.

**Requirements:**
1. Engine's `list_requests()` MUST return parse-failed entries as error objects (not silently skip them).
2. Error objects carry: filename, parse error message, and best-effort extracted `task_id` (attempt partial parse of frontmatter even on failure).
3. Cockpit renders these as "malformed request" cards with: filename, error summary, link to blocked task (if task_id recovered), and manual recovery actions (delete file, unblock task).
4. If task_id cannot be recovered from a UUID-only filename, the card still appears with the filename as identifier. Human can inspect the file directly (clone=install — it's just a file on disk).

## Filesystem Safety

### UUID4 Filenames (New Design)

Per D3, request_id is UUID4 and filename is `{request_id}.md`. No agent-controlled components in the path. Path traversal eliminated by construction — `uuid4()` output contains only hex and hyphens.

### Atomic Creation

`O_EXCL` flag on file creation (existing pattern). Prevents overwrite of existing request.

### Directory Path Trust

The `decisions/pending/` and `decisions/resolved/` paths are configured at engine initialization from a trusted config source, not derived from request content. No agent input influences directory selection.

### Symlink Attacks

Not defended. In a single-user system, a symlink attack is self-sabotage. The blast radius is the user's own filesystem, which they already fully control. Noting for completeness; not recommending defense.

## CORS as Explicit Invariant

**Requirement:** The Cockpit server MUST NOT add permissive CORS middleware (`Access-Control-Allow-Origin: *` or broad origin lists). This must be a documented invariant, not the implicit absence of configuration.

**Implementation:** Either (a) add a test that asserts no CORS middleware is registered on mutation routes, or (b) add an explicit restrictive CORS policy that allowlists only the served origin.

**Rationale:** The secondary threat model (cross-origin browser attack) is defended entirely by CORS preflight. If a future contributor adds CORSMiddleware for debugging convenience, the defense evaporates silently.

## Validation Boundary Placement

| Layer | Validates | Purpose |
|-------|-----------|---------|
| **MCP tools** | Required fields present, correct types, string length limits | Fast rejection with clear error messages to agents. Interface contract enforcement. |
| **Cockpit API** | Pydantic request schema, request size limit, field allowlisting (reject unexpected fields), ID format | Boundary-local structural integrity. Protects engine from malformed HTTP payloads. |
| **Engine** | All business invariants: option uniqueness, count bounds, slug format, kind-specific rules, state transitions | Authority. Invalid data never reaches disk. |

Each layer validates what it is responsible for. This is not redundant — MCP validates the agent contract, Cockpit validates the HTTP contract, engine validates the domain contract. Boundary-local rejection provides fast, specific error messages without requiring a full engine round-trip.

## What's Security Theater for This System

| Control | Why it's theater |
|---------|-----------------|
| Full AuthN/AuthZ on localhost API | Single user, localhost-bound. No unauthorized party can reach the endpoints. |
| Encryption at rest for decision files | User's own disk. Full disk encryption is an OS concern, not an application one. |
| Rate limiting | Single user, single machine. Self-DoS is not a threat to defend against. |
| Input sanitization beyond type/length | Markdown is the intended content. HTML-sanitizing markdown at storage time destroys legitimate content. |

## What's NOT Theater

| Control | Why it matters |
|---------|---------------|
| CORS restriction (no wildcard) | Real cross-origin attack surface from browser tabs |
| Engine-level Pydantic validation | Protects data integrity from buggy agents (primary threat) |
| Slug validation on option_id | Prevents structural corruption across filesystem, URL, and YAML boundaries |
| Human-only resolution (no MCP resolve tool) | Protects the oversight guarantee that justifies the blocking mechanism |
| Malformed-DR observability | Prevents invisible DoS on blocked tasks from primary threat |
| Write-back format control | Prevents corruption propagation from DR files into task state |
| Resolution atomicity (rename-as-check) | Prevents duplicate resolution and inconsistent state |
| Boundary-local structural checks | Fast rejection, clear errors, defense against interface-level bugs |

## Least-Privilege Recommendations

1. **MCP tool surface:** Expose `create_request`, `list_requests`, `show_request` only. No `resolve_request` in default agent tooling.
2. **File permissions:** Engine writes to `decisions/` only. No agent has direct filesystem write to this directory.
3. **Cockpit mutation scope:** Resolve endpoint accepts only the fields it needs (`selected_option_id`, `free_text`). Reject extra fields.
4. **Option immutability:** No update path for options after creation. Modification requires cancel + recreate (if cancel is ever added).

## Warnings

1. **CORS regression risk.** The cross-origin defense is one middleware addition away from collapse. Make it a tested invariant.
2. **Write-back propagation.** Agent-generated text in DR body/rationale permanently enters task state. If downstream agents treat task-body content as authoritative commands, a confused agent's rationale text could influence subsequent agent behavior. The delimiter format mitigates but doesn't eliminate this.
3. **Malformed file accumulation.** If agents repeatedly fail to create valid requests, malformed files accumulate and create noise. Consider a staleness policy (auto-surface files older than N days for cleanup).
4. **Future MCP resolve tool.** If ever added without the gating conditions above, it silently removes the human-in-the-loop guarantee. This must be a conscious, documented decision — not a convenience addition.

## Confidence

**0.82**

Refined through two Critic cycles. Remaining uncertainty: (a) exact write-back format is a design detail that needs implementation validation, (b) malformed-file partial-parse reliability is an engineering question, (c) downstream task-body consumer behavior is not fully enumerated. Core positions on trust boundaries, validation placement, and human-only resolution are solid.
