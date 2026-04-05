# Test: Setup Script Core Functions — Research

> **Owning task:** #92 — Test: setup script core functions (settings, mcp, kanban, idempotency)
> **Date:** 2026-03-28 **Status:** Complete

## 1. Context and Question

Task #92 is the TDD RED phase for #12's core setup functions (excluding project JSON, covered by #75). The test-writer needs: target function signatures, filesystem isolation strategy, JSON merge testing approach, and scope boundary clarification.

**Key questions:** What functions to test against? How to test JSON merge idempotency? How to test path auto-detection? Any missing test scenarios?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | pytest tmp_path fixture docs | <https://docs.pytest.org/en/stable/how-to/tmp_path.html> | .95 |
| 2 | pytest monkeypatch docs | <https://docs.pytest.org/en/stable/how-to/monkeypatch.html> | .90 |
| 3 | v1 test_project_workspace.py | `v1/tests/test_project_workspace.py` | .85 |
| 4 | #12 parent research doc | `docs/research/setup-script.md` | 1.0 |
| 5 | #75 sibling TDD research | `docs/research/test-project-json-generation.md` | .85 |
| 6 | v1 workspace.py scaffolder | `v1/src/owlbear/projects/workspace.py` | .80 |

## 3. Analysis

### 3.1 Target Function Signatures

From Source 4 (§3.1): single script, one function per artifact. Proposed signatures:

```python
# scripts/setup.py
def create_vscode_settings(project_dir: Path, owlbear_dir: Path) -> Path
def create_mcp_config(project_dir: Path, owlbear_dir: Path) -> Path
def create_kanban_dir(project_dir: Path, owlbear_dir: Path) -> None
def create_copilot_instructions(project_dir: Path, *, name: str | None = None) -> Path
def compute_owlbear_relpath(owlbear_dir: Path, project_dir: Path) -> str
def setup(project_dir: Path | None = None, ...) -> None  # orchestrator
```

Tests should assert behavior, not exact signatures — the architect may adjust during #12 AC refinement.

### 3.2 Test Isolation Strategy

| Technique | Use for | Source |
|-----------|---------|--------|
| `tmp_path` sibling dirs | All filesystem tests: `project_dir = tmp_path / "proj"`, `owlbear_dir = tmp_path / "owlbear"` | 1, 3 |
| `monkeypatch.chdir(project_dir)` | Path auto-detection (simulate CWD) | 2 |
| `monkeypatch.setattr` | Patch `Path(__file__).resolve()` for owlbear detection | 2 |
| `capsys` | Success message output verification | pytest builtin |

v1's test_project_workspace.py (Source 3) uses exactly this pattern: `tmp_path` for isolation, `MagicMock` for subprocess calls, direct filesystem assertions.

### 3.3 JSON Merge Test Strategy

Settings.json merge (Source 4, §3.3, §3.5) is the only non-trivial idempotency case:

1. **No existing file:** call function → assert all 3 location keys present
2. **Existing file with unrelated keys:** pre-write `{"editor.fontSize": 14}` → call → assert `editor.fontSize` preserved AND `chat.agent*` keys added
3. **Existing file with overlapping keys:** pre-write `{"chat.agentFilesLocations": {"old/path": true}}` → call → assert owlbear paths merged in

For mcp.json and kanban/config.yml, idempotency is simple: skip if exists.

### 3.4 Gap Analysis — Test Scenarios vs AC

| AC Item | Test Scenario | Status |
|---------|---------------|--------|
| settings.json with agentFilesLocations | Scenario 1 | Covered |
| settings.json with agentSkillsLocations | Scenario 1 | Covered |
| **settings.json with instructionsFilesLocations** | — | **MISSING** — add per Source 4 §3.3 |
| mcp.json with 3 servers | Scenario 3–4 | Covered |
| kanban/ with config.yml + tasks/ | Scenario 5–6 | Covered |
| data/knowledge/ directory | Scenario 7 | Covered |
| .github/copilot-instructions.md | Scenario 8 | Covered |
| Idempotent settings.json (merge) | Scenario 9 | Covered |
| Idempotent kanban/config.yml | Scenario 10 | Covered |
| Path auto-detection | Scenario 11 | Covered |
| Success message | Scenario 12 | Covered |
| **MCP server module names correct** | — | **ADD** — verify `mcp_kanban`, `mcp_knowledge`, `mcp_project` |
| **Idempotent mcp.json** | — | **ADD** — skip if exists |
| **Idempotent .github/copilot-instructions.md** | — | **ADD** — skip if exists |
| **kanban/setup.ps1 copied** | — | **ADD** — per Source 4 §3.6 |

Four gaps found. Recommend adding to AC before test-writer starts.

### 3.5 Dependency Analysis

| Dependency | Status | Required? |
|------------|--------|-----------|
| #12 (setup script) | backlog | **No** — RED phase tests fail by design; stub exists |
| #75 (project JSON tests) | backlog | **No** — parallel scope, no overlap |
| #68 (Pydantic model) | backlog | **No** — project JSON excluded from #92 |
| #7 (monorepo skeleton) | archived | **No** — `tests/` directory already exists |

**No `depends_on` needed.** The setup script is a 3-line stub. Test imports will raise `ImportError` — that's expected RED phase behavior.

## 4. Recommendation (.85 confidence)

The 12 test scenarios in #92 are sound. Add 4 missing scenarios (instructions locations, MCP module names, mcp.json idempotency, setup.ps1 copy) to the AC before dispatching the test-writer. Use `tmp_path` for isolation, `monkeypatch.chdir` for auto-detection, `capsys` for output, and `json.loads` for JSON assertions. No new dependencies needed. Follow the `TestFromAC_*` class naming convention per existing test patterns.

**Risks:**
- Function signatures may change during architect review — tests should assert behavior not signatures
- The owlbear kanban/config.yml must be accessible from tests for the "copied config" test — use `tmp_path` to create a mock owlbear dir with config.yml rather than referencing real project files
