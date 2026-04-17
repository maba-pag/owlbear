# macOS Validation — Full Suite Results

> **Owning task:** #905 — Full macOS validation (ruff + pytest + smoke test)
> **Date:** 2026-04-17  **Status:** Complete

## 1. Context and Question

Task #905 is the exit gate for macOS compatibility feature (#890). All prior tasks (901–904) are archived/complete. Question: which ACs can be verified automatically, and do they pass?

## 2. AC Verification Matrix

| # | AC | Auto? | Result | Evidence |
|---|-----|-------|--------|----------|
| 1 | `uv run ruff check .` exits 0 | ✅ Auto | **PASS** | "All checks passed!", exit 0 |
| 2 | `uv run pytest` exits 0 | ✅ Auto | **FAIL** | 254 failed / 4307 passed / 189 skipped in 40.87s |
| 3 | Agents visible in VS Code | ❌ Manual | UNTESTED | Requires VS Code Copilot Chat panel inspection |
| 4 | Hook executes on macOS | ✅ Auto | **PASS** | `echo '{}' \| uv run python .owlbear/hooks/session-context.py` → exit 0. Agent YAML uses `uv run python` invocation — no execute bit needed |
| 5 | MCP servers start/respond | ⚠️ Semi | **PARTIAL** | All 4 modules import OK. Full start/respond requires VS Code or MCP client |
| 6 | No .ps1 references in scope | ✅ Auto | **NEAR-PASS** | 1 hit: comment in `session-context.py` line 4 ("Python port of session-context.ps1"). Not a live dependency — attribution comment from porting work |
| 7 | No powershell in agents | ✅ Auto | **PASS** | `grep -r "powershell" share/agents/` → 0 matches |
| 8 | Consumer workflow (init.py) | ✅ Auto | **PASS** | Seeded 22 files into fresh target on macOS, exit 0 |

## 3. Analysis

### Test failures are NOT macOS-specific

The 254 test failures are Pydantic model validation errors — tests construct models (e.g. `AnalysisProposal`) missing newly-added required fields (`category`, `pattern`, `rationale`, `suggested_action`). This is test maintenance drift, not a platform issue. Same failures would occur on Linux/Windows.

### Test suite hang (known issue)

Serial mode (`-n 0`) hangs at ~97% — test interaction between `test_llmextractor_wiring_876.py` and `test_null_safety_539.py`. State leakage from prior test prevents subsequent collection. Already documented in session memory (deadlock investigation). Not macOS-specific.

### .ps1 comment reference

The single `.ps1` grep hit is an attribution comment in the Python port. Decision D6 (from brief) mandated deleting .ps1 files, not removing historical references. However, the AC is literal: "grep returns no results." Removing 4 words from a comment resolves this.

### Broader powershell references

Skill files use `` ```powershell `` as markdown code fence language in 6 files. These are formatting hints for syntax highlighting in documentation, not code dependencies. Outside AC scope (`share/agents/` only), but worth noting for future cleanup.

## 4. Recommendation

**Confidence: .90** — macOS compatibility feature works. The blocking issues are:

1. **Test failures (254)** — pre-existing, platform-agnostic, separate concern from #890
2. **Test hang** — pre-existing test interaction bug, separate concern
3. **.ps1 comment** — trivial 4-word edit to satisfy literal AC

Challenge: N/A — verification task, no design recommendation to challenge.

**Proposed path to close #905:**
- Fix the .ps1 comment (trivial, T1)
- User manually verifies AC3 (agents visible) and AC5 (MCP servers respond)
- Test failures/hang tracked as separate tasks — they block AC2 but are not #890 regressions

## 5. Follow-up Tasks

| Task | Priority | Rationale |
|------|----------|-----------|
| Remove .ps1 attribution from hook comment | needed | Satisfies AC6 literal grep check |
| Fix test suite Pydantic model drift (254 failures) | important | Blocks AC2 but not macOS-specific |
| Fix test interaction hang (llmextractor → null_safety) | important | Blocks full suite completion |
| User: verify agent visibility + MCP server health | critical | AC3 + AC5 require manual VS Code interaction |
