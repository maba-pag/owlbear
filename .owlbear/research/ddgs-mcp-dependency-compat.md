# ddgs[mcp] Dependency Compatibility Verification

> **Owning task:** #706 — Verify ddgs[mcp] dependency compatibility with workspace mcp SDK
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Challenger concern from #686 arch review: `ddgs[mcp]` may pull a transitive `mcp[cli]` pin that conflicts with `serve/` mcp SDK `>=1.26`. This task verifies compatibility before downstream implementation tasks proceed.

## 2. Sources Studied

| Source | URL/Path | Relevance | What |
|--------|----------|-----------|------|
| PyPI JSON API — ddgs 9.13.0 | pypi.org/pypi/ddgs/json | .95 | `requires_dist`: `"mcp>=1.26.0; extra == \"mcp\""` |
| Workspace pyproject.toml | pyproject.toml | .95 | Root dev deps — no mcp pin at root level |
| serve/ pyproject.toml files | serve/mcp-*/pyproject.toml | .95 | All 4 MCP servers pin `mcp[cli]>=1.26` |
| uv pip show mcp | local env | .95 | Currently installed: mcp 1.27.0 |
| uv pip install --dry-run | local env | 1.0 | Resolver confirms no conflict, 3 new packages |
| PyPI JSON API — primp 1.2.2 | pypi.org/pypi/primp/json | .80 | Rust binary wheel, zero Python runtime deps |

## 3. Analysis

### 3.1 Version Compatibility Matrix

| Component | mcp Requirement | Conflict? |
|-----------|----------------|-----------|
| serve/mcp-kanban | `mcp[cli]>=1.26` | No |
| serve/mcp-knowledge | `mcp[cli]>=1.26` | No |
| serve/mcp-memory | `mcp[cli]>=1.26` | No |
| serve/mcp-project | `mcp[cli]>=1.26` | No |
| ddgs v9.13.0 [mcp] extra | `mcp>=1.26.0` | No |
| Currently installed | mcp 1.27.0 | Satisfies all |

Both ddgs and serve/ packages use the same `>=1.26` lower bound with no upper bound. The `[mcp]` extra on ddgs and `[cli]` extra on serve/ are different extras of the same package — they coexist.

### 3.2 Resolver Dry-Run Results

```
uv pip install --dry-run "ddgs[mcp]>=9.13,<10"
→ Resolved 34 packages in 582ms
→ Would install 3 packages:
  + ddgs==9.13.0
  + lxml==6.0.2
  + primp==1.2.2
```

mcp is NOT in the install list — already satisfied by v1.27.0. No version conflict errors.

### 3.3 New Dependency Footprint

| Package | Type | Size (wheel) | Runtime Deps | Risk |
|---------|------|-------------|-------------|------|
| ddgs 9.13.0 | Pure Python | ~46KB | click, primp, lxml | Low |
| primp 1.2.2 | Rust binary | ~4MB | None | Low — same author as ddgs |
| lxml 6.0.2 | C extension | ~8MB | None | Low — well-established |

Total: 3 new packages, 0 additional transitive Python deps beyond these three.

## 4. Recommendation (.95 confidence)

**No conflict exists.** `ddgs[mcp]>=9.13,<10` is fully compatible with the workspace's mcp SDK. Downstream tasks (#707–#711) can proceed without modification.

**Tier classification: T1 (autonomous)** — verification confirms compatibility, no decisions needed.

Challenge: skipped (info-only verification, no recommendation to challenge).

## 5. Follow-up Tasks

None needed — downstream subtasks #707–#711 already exist on the board and are unblocked by this verification.
