# approve_memory CLI Wrapper Design

> **Owning task:** #531 — Build approve_memory CLI wrapper for set_approval_state
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

Task #531 (from #528 curator-workflow research §3B) adds a CLI script
(`scripts/approve_memory.py`) wrapping the `set_approval_state` MCP tool for
user batch approval of memory entries. The script must call MCP tools (not
direct SQLite) and support interactive + batch modes.

**Key questions:** (1) How should a CLI script call MCP tools? (2) What
UX pattern for interactive approve/reject? (3) Where do curator
recommendations come from? (4) Are dependencies correctly specified?

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | Curator workflow research | `docs/research/curator-workflow-memory-mcp.md` §3B | .95 |
| S2 | set_approval_state design | `docs/research/set-approval-state-mcp-tool.md` | .95 |
| S3 | MCP Python SDK README | `github.com/modelcontextprotocol/python-sdk` README §Writing MCP Clients | .90 |
| S4 | MCP quickstart client | `modelcontextprotocol.io/quickstart/client` | .85 |
| S5 | Existing integration tests | `packages/mcp-kanban/tests/test_integration.py` | .90 |
| S6 | Existing migrate.py CLI | `packages/mcp-memory/src/owlbear_mcp_memory/migrate.py` | .80 |
| S7 | memory-mcp tools.py | `packages/mcp-memory/src/owlbear_mcp_memory/tools.py` | .95 |
| S8 | MCP SDK `mcp.shared.memory` | `mcp.shared.memory.create_connected_server-and_client_session` | .85 |

## 3. Analysis

### 3A. CLI-to-MCP Communication

| Criterion | A: stdio subprocess | B: In-memory transport |
|-----------|--------------------|-----------------------|
| MCP compliance | Full protocol | Full tool layer |
| Subprocess needed | Yes (`uv run -m owlbear_mcp_memory`) | No |
| Server coupling | None (black box) | Imports server module |
| Startup overhead | ~2s (uv resolve + Python) | ~50ms |
| Error handling | Protocol-level errors + exit codes | Python exceptions |
| KISS | Medium | High |
| Testability | Need subprocess mock | Same as integration tests (S5) |
| Prior art | MCP SDK docs (S3, S4) | Project integration tests (S5, S8) |

**Option A** uses `StdioServerParameters` + `stdio_client` to spawn the
server. Follows MCP client quickstart (S4). Clean boundary but adds subprocess
overhead and `uv` dependency resolution at runtime.

**Option B** uses `create_connected_server-and_client_session` (S8) to create
an in-process MCP session. Same API (`session.call_tool`) but no subprocess.
Already proven in integration tests (S5). Requires importing server and
constructing a custom lifespan (same pattern as S5).

### 3B. Interactive UX Pattern

| Approach | Deps | UX quality | KISS |
|----------|------|-----------|------|
| Plain `input()` + `print()` | None | Low | High |
| `argparse` + numbered list | None | Medium | High |
| `rich` tables + prompts | `rich` | High | Medium |
| `questionary` checkboxes | `questionary` | High | Low |

YAGNI says start with zero new dependencies. Numbered list with `input()`
for selection is sufficient for a batch-approval tool. The `migrate.py` CLI
(S6) uses `argparse` and `print` — follow the same pattern.

### 3C. Curator Recommendations Integration

AC requires: "Shows curator recommendations from curation report if available."

The curator writes its report to kanban Channel B (task body). No file-based
report exists today. Options:

| Approach | Complexity | Coupling |
|----------|-----------|----------|
| Read kanban task body via mcp-kanban | High | Cross-server dependency |
| Curator writes JSON report to `data/memory/` | Low | File convention |
| Skip if no report file exists | None | Graceful degradation |

Recommendation: Convention-based. If `data/memory/curation-report.json` exists,
read and display. If not, show entries without recommendations. The curator
update (#530) should add report-file output as an AC item.

### 3D. Dependency Gap

| Current dependency | Status | Provides |
|-------------------|--------|----------|
| #525 (base tools) | Archived | `list_entries`, `record_learning`, etc. |

| Missing dependency | Status | Provides |
|-------------------|--------|----------|
| #529 (`set_approval_state`) | Backlog | The tool the CLI wraps |

The CLI cannot function without `set_approval_state`. Add `depends_on: 529`.

### 3E. Implementation Skeleton

```
scripts/approve_memory.py
├── argparse CLI (--batch IDS, --interactive, --db-path)
├── async main()
│   ├── Create in-memory MCP session (Option B)
│   ├── list_entries(status="pending") → display table
│   ├── Load curation report if exists → annotate entries
│   ├── Interactive: numbered prompt → user selects approve/reject
│   ├── Batch: --approve/--reject + ID list from args
│   └── call set_approval_state for each selected entry
└── Run: uv run --project packages/mcp-memory scripts/approve_memory.py
```

## 4. Recommendation (.82 confidence)

**Option B (in-memory MCP client)** for server communication. Zero-dependency
interactive UX with `argparse` + `input()`. Convention-based curator report
(`data/memory/curation-report.json`, graceful skip if absent). Fix dependency
to #529.

The in-memory approach satisfies "calls MCP tool, not direct SQLite" while
keeping the CLI simple and fast. The project already uses this pattern in tests.
Runtime: `uv run --project packages/mcp-memory scripts/approve_memory.py`.

Challenge: FALLBACK — challenger agent not available in dispatch list.

## 5. Follow-up Tasks

Dependency fix (update #531 to depend on #529) executed inline. No new tasks
needed — #531 itself is the implementation task. Minor AC refinement: add
`data/memory/curation-report.json` convention to #530 as a follow-up.

```
kanban\kanban-md.exe create "Curator: write curation-report.json to data/memory/" --priority important --status ideation --tags "scope:agents,phase-2" --body "When curator completes a curation cycle, write a structured JSON report to data/memory/curation-report.json containing entry IDs with recommendations. Per docs/research/approve-memory-cli-wrapper.md §3C.\n\nAC:\n- [ ] Curator writes data/memory/curation-report.json after Step 5 (report)\n- [ ] Format: array of {entry_id, content_preview, recommendation, reason}\n- [ ] File is overwritten each cycle (latest report only)\n- [ ] approve_memory CLI reads this file for recommendation display" --depends-on 530
```
