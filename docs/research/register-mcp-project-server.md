# Register owlbear-project server in .vscode/mcp.json

> **Owning task:** #577 — Register owlbear-project server in .vscode/mcp.json
> **Date:** 2026-04-03 **Status:** Complete

## 1. Context and Question

The OwlBear workspace `.vscode/mcp.json` registers only two custom MCP servers
(`owlbear-kanban`, `owlbear_knowledge`), but `setup.py` generates entries for four
servers in consumer projects (kanban, knowledge, memory, project). The `mcp-project`
skill already documents the server as registered. Should we add it, and in what form?

## 2. Sources Studied

| Source | URL | What | Relevance |
|--------|-----|------|-----------|
| `.vscode/mcp.json` (workspace) | local | Current server registrations — 2 of 4 custom servers present | 1.0 |
| `scripts/setup.py` L48–95 | local | Consumer project mcp.json generation — defines all 4 entries | 1.0 |
| `packages/mcp-project/src/owlbear_mcp_project/__main__.py` | local | Entry point confirming `mcp.run()` invocation | 0.9 |
| `skills/mcp-project/SKILL.md` | local | Skill doc claims server is registered as `owlbear-project` | 0.9 |
| VS Code MCP docs | https://code.visualstudio.com/docs/copilot/chat/mcp-servers | stdio server registration format | 0.8 |

## 3. Analysis

### Current vs expected registrations

| Server | In mcp.json? | In setup.py? | `__main__.py` exists? | Skill exists? |
|--------|-------------|-------------|----------------------|--------------|
| owlbear-kanban | Yes | Yes | Yes | Yes (mcp-kanban) |
| owlbear_knowledge | Yes | Yes | Yes | Yes (knowledge-ops) |
| owlbear-project | **No** | Yes | Yes | Yes (mcp-project) |
| owlbear-memory | **No** | Yes | Yes | No |

### Naming convention difference

The OwlBear workspace uses hyphenated names (`owlbear-kanban`), while `setup.py`
uses camelCase for consumer projects (`owlbearKanban`). The workspace convention
should continue using hyphenated names for consistency.

### Entry format (matching existing pattern)

```json
"owlbear-project": {
  "type": "stdio",
  "command": "uv",
  "args": ["run", "python", "-m", "owlbear_mcp_project"]
}
```

The workspace entries use `"uv", "run", "python", "-m", ...` (no `--project` flag
since uv runs from the workspace root). Consumer project entries in setup.py add
`--project {rel}` because they run from a different directory.

### Risk assessment

- **Risk:** None. Adding a server entry is additive; if no agent references the
  tools, the server simply won't be started by VS Code until a tool call matches.
- **KISS/YAGNI:** The package exists, is tested, has a skill. Registration is the
  missing wiring step. Not speculative.

## 4. Recommendation (.95 confidence)

Add the `owlbear-project` entry to `.vscode/mcp.json` matching the existing pattern.
Also add `owlbear-memory` — same gap, same fix, separate follow-up task.

Challenge: FALLBACK — trivial config task, challenge not warranted per workflow rules.

## 5. Follow-up Tasks and Dedup

- **#578** is an exact duplicate of #577 (same scope). Recommend merging.
- **#570** already covers the owlbear-memory gap (in backlog, architect claimed).
- **#579** was created as follow-up during this research but is duplicate of #570;
  moved to done.
- No new tasks needed — existing board coverage is complete.
