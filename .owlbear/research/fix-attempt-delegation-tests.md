# Fix-Attempt Delegation Flow — Testing Strategy

> **Owning task:** #320 — Tests for fix-attempt delegation flow
> **Date:** 2026-04-04 **Status:** Complete

## 1. Context and Question

Task #320 requires tests for the builder→fix-attempt delegation flow. The delegation logic (#319, backlog) will update `w-tdd-green/SKILL.md` with steps for constructing a `retry_hint`, delegating to fix-attempt after 2 failures, and handling FIXED/FAILED results. The question: **what testing strategy validates this flow, given that the delegation is LLM-driven from Markdown skill instructions rather than Python code?**

Dependencies: #318 (done — fix-attempt.agent.md exists), #319 (backlog — delegation logic not yet in skill file). Decision 228 approved (Option A: threshold=2).

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `tests/test_fix_attempt_agent_318.py` (27 tests) | .95 — established pattern: contract-level structural tests on agent .md files via regex + string presence |
| S2 | `tests/test_quality_runner_wiring.py` (AC1-8) | .95 — established pattern: skill SKILL.md content validation + agent wiring tests combined |
| S3 | `.github/skills/w-tdd-green/SKILL.md` (current) | 1.0 — the file #319 will modify; Steps 0-8 with no delegation logic currently |
| S4 | `docs/research/fresh-context-retry-builder.md` §3d-3e | .90 — input contract format, retry_hint structure, integration flow after Step 6 |
| S5 | `.github/agents/fix-attempt.agent.md` | 1.0 — input/output contracts, 9-tool assign set, max 1 retry, no kanban |
| S6 | `.github/agents/builder.agent.md` | 1.0 — current `agents: [scribe]`, 20 tools, w-tdd-green skill reference |

## 3. Analysis

### 3a. What is the testable unit?

In this architecture, Markdown skill files are the executable contracts that LLM agents follow. The builder→fix-attempt delegation is:
- **Described in Markdown** (w-tdd-green SKILL.md, post-#319)
- **Executed by the LLM** (not Python code — no `retry_hint` builder function exists)
- **Not part of the Python orchestrator** (orchestrator dispatches to agents; builder→fix-attempt is intra-agent)

The testable unit is the **skill file specification**. Testing it validates instruction correctness and contract compliance.

### 3b. Testing approach comparison

| Approach | Codebase consistency | Behavioral coverage | Complexity | Confidence |
|----------|---------------------|---------------------|------------|------------|
| **A: Contract tests on skill/agent files** | High (.90) — matches S1, S2 | Medium — tests spec, not runtime | Low | **.80** |
| B: Python helper module + contract tests | Low (.50) — no precedent | High — tests code | Medium | .65 |
| C: AcpClient mock integration tests | Low (.40) — wrong layer | Low — can't reach LLM | High | .50 |

### 3c. AC-to-test mapping

| AC | Target artifact | Test approach | Class name |
|----|----------------|---------------|------------|
| AC1: retry_hint from error output | w-tdd-green SKILL.md | Verify delegation step documents retry_hint construction with error-mapping guidance (Reflexion verbal feedback pattern) | `TestFromAC_RetryHintConstruction` |
| AC2: input contract validation | w-tdd-green SKILL.md + fix-attempt.agent.md | Cross-reference builder dispatch format fields against fix-attempt input contract (5 fields: task_id, test_file, source_files, retry_hint, error_summary) | `TestFromAC_InputContractValidation` |
| AC3: exactly 2 failures threshold | w-tdd-green SKILL.md | Parse skill for threshold=2 with exclusionary language (not after 1st, not after 3rd). NB: validates instruction unambiguity, not LLM runtime enforcement | `TestFromAC_DelegationThreshold` |
| AC4: FIXED → verify + continue | w-tdd-green SKILL.md | Verify skill documents FIXED handling path: final verify then continue to commit/advance | `TestFromAC_FixedResultHandling` |
| AC5: FAILED → BLOCK | w-tdd-green SKILL.md | Verify skill documents FAILED handling path: block task, report to orchestrator | `TestFromAC_FailedResultHandling` |
| AC6: no kanban tools | fix-attempt.agent.md + builder delegation | Partially covered by #318; extend with builder agents-array wiring (gate prerequisite) | `TestFromAC_NoKanbanTools` |

### 3d. Testing patterns to use (from S1, S2)

- **Regex alternation** for flexible matching: `r"\b2\s+failure|\bsecond\s+failure|\bthreshold.*2\b"`
- **String presence** for verdicts and field names: `"FIXED" in body`, `"retry_hint" in body`
- **Frontmatter extraction** via `---` markers for agents-array wiring checks
- **Cross-file validation** for contract compatibility (builder dispatch → fix-attempt input)
- **Gate pattern** (S2): assert agent wiring first, then assert skill content

### 3e. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| AC3 behavioral gap — contract tests can't verify LLM follows threshold | Medium | Maximize instruction clarity in #319; test for both threshold value AND exclusionary language |
| Tests written before #319 — speculative about exact wording | Low | Use flexible regex patterns, not exact strings; test for semantic content not formatting |
| Step numbering may shift in #319 | Low | Reference steps by name/content, not number |
| Cross-agent contract drift | Medium | Cross-reference tests check both files simultaneously |

## 4. Recommendation (.80 confidence)

**Option A: Pure contract-level structural tests** on w-tdd-green SKILL.md + builder.agent.md, cross-referenced with fix-attempt.agent.md.

Six `TestFromAC_*` classes, one per AC item, following the established patterns from S1 (regex/string assertions) and S2 (skill content + agent wiring combined). Test file: `tests/test_fix_attempt_delegation_320.py`.

Builder `agents: [scribe, fix-attempt]` wiring is included as a gate prerequisite in AC6 tests, consistent with S2's compound gate pattern.

Challenge: proceed — confidence in original: .80. Key challenge accepted: AC3 validates instruction unambiguity, not runtime enforcement. This is the testing ceiling for LLM-driven behavior.

## 5. Follow-up Tasks

No new follow-up tasks needed. #320 itself is the implementation task with concrete AC. Dependencies #318 (done) and #319 (backlog) are correctly sequenced.
