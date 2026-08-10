# MCP Memory Server — Tool Interface Assessment

Date: 2026-05-03  
Scope: `serve/mcp-memory/` tool definitions, descriptions, and runtime configuration  
Source: Hands-on discovery during startup debugging

---

## 1. Status Quo

The memory MCP server exposes 5 tools via FastMCP. They implement a 3-stage lifecycle:
`pending → curated → approved` (plus `→ deleted` from any state).

### Tools

| Tool | Purpose | Access control |
|------|---------|----------------|
| `store_learning` | Create entry (always pending) | None |
| `query_memory` | Filter + retrieve entries | None |
| `update_entry` | Partial update + state transition (pending→curated only) | curator-only |
| `delete_entry` | Soft-delete (idempotent) | curator-only |
| `approve_entry` | curated→approved promotion | user-only |

### Lifecycle state machine

```
pending ──(update_entry)──▶ curated ──(approve_entry)──▶ approved
   │                                                        │
   └──────────(delete_entry)──▶ deleted ◀───────────────────┘
```

### Valid categories (Literal enum, not exposed in schema)

knowledge, behaviour, pitfall, process, tool, goal, personality, preference, context

### Constraints (enforced by Pydantic, not exposed in schema)

- `confidence`: 0.7 ≤ x ≤ 1.0
- `categories`: min 1 item
- `title`: non-blank
- `id`: UUID v4 format

### Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Markdown file storage dir |
| `OWLBEAR_MEMORY_CALLER` | `unknown` | Caller identity for access control |
| `MEMORY_TOOLS_EXCLUDE` | — | Comma-separated tool names to hide |

---

## 2. Problems Found (grounded comparison)

### Critical — tools broken at runtime

| # | Tool(s) | Issue |
|---|---------|-------|
| 7 | `update_entry`, `delete_entry` | Require `OWLBEAR_MEMORY_CALLER=curator`. Current mcp.json sets NO env vars → caller is "unknown" → **always errors**. |
| 8 | `approve_entry` | Requires `OWLBEAR_MEMORY_CALLER=user`. Same issue → **always errors**. |

### High — agent fails on first call with unhelpful errors

| # | Tool | Issue |
|---|------|-------|
| 1 | `store_learning` | Valid categories not exposed in schema or description. Agent guesses wrong → cryptic Pydantic error. |
| 2 | `store_learning` | Confidence range (0.7–1.0) not in schema. Agent sends 0.5 → error. |
| 5 | `update_entry` | Only `pending→curated` allowed via state field. Not documented. |
| 6 | `update_entry` | Approved entries immutable. Not mentioned. |
| 9 | `approve_entry` | Only works on curated entries. Calling on pending errors with no useful guidance. |

### Medium — surprising/confusing behavior

| # | Tool | Issue |
|---|------|-------|
| 3 | `query_memory` | Default filter is `{"curated", "approved"}` when states=null. Pending entries invisible by default. |
| 11 | All | `scope_agents` purpose unclear from schema — it's a visibility-scoping tag, not authorship. |

### Low — nice-to-have clarity

| # | Tool | Issue |
|---|------|-------|
| 4 | `query_memory` | Sort order undocumented (state rank → confidence DESC → ID). |
| 10 | `delete_entry` | Idempotency not mentioned in description. |

---

## 3. Proposed Changes (pre-ideation)

### A. Runtime fix — caller identity

**Options:**
1. Add `"env": {"OWLBEAR_MEMORY_CALLER": "user"}` to `.vscode/mcp.json`
2. Remove access control entirely (single-user deployment makes roles theatrical)
3. Default caller to "user" when env var unset (code change)

### B. Description enrichment

Rewrite tool descriptions to include:
- Valid category values
- Confidence range
- State lifecycle and transitions per tool
- Default query behavior
- Role requirements

### C. Schema constraints

Expose Pydantic constraints in the JSON Schema sent to clients:
- `categories` items as `enum` array
- `confidence` as `minimum: 0.7, maximum: 1.0`
- `states` items as `enum` array

### D. Access control model (open question)

The curator/user split implies a multi-agent workflow:
- **Agent** stores learnings → pending
- **Curator agent** reviews → curated
- **Human user** approves → approved

Questions:
- Is this the intended workflow? If so, who is the curator in practice?
- Should there be a single `OWLBEAR_MEMORY_CALLER` per server instance, or should caller be per-request?
- If per-instance, should there be two server entries in mcp.json (one for curator, one for user)?

---

## 4. File references

- Server: `serve/mcp-memory/src/owlbear_mcp_memory/server.py`
- Tools: `serve/mcp-memory/src/owlbear_mcp_memory/tools.py`
- Models: `serve/mcp-memory/src/owlbear_mcp_memory/models.py`
- Engine: `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`
- MCP config: `.vscode/mcp.json`
- Prior brief: `.owlbear/briefs/draft-memory-module/`
