# Test-Writer Agent: Adversarial Test Creation from AC

> **Owning task:** #683 — Test-writer agent: adversarial test creation from AC
> **Date:** 2026-03-08 **Status:** Complete

## 1. Context and Question

Currently the builder writes both tests and implementation. This creates two problems: (1) tests are biased toward the implementation the builder plans to write — it tests what it intends to build, not what the AC requires, and (2) test-writing instructions are buried in the builder's crowded context.

**Research questions:** Is splitting TDD red/green across two agents theoretically sound? How have others solved this? What's the handoff protocol? How does it fit our pipeline?

## 2. Sources Studied

| # | Source | URL | Relevance | What | Score |
|---|--------|-----|-----------|------|-------|
| 1 | AgentCoder (Huang et al., 2024) | <https://arxiv.org/abs/2312.13010> | Direct | 3-agent framework: programmer, test designer, test executor. Test designer generates independently. | .95 |
| 2 | ChatDev (Qian et al., 2024) | <https://arxiv.org/abs/2307.07924> | Partial | 7-agent pipeline: tester role exists but tests after coding (less adversarial). | .60 |
| 3 | MetaGPT (Hong et al., 2024) | <https://arxiv.org/abs/2308.00352> | Partial | Assembly-line with QA engineer. Tests after implementation, 79% accuracy. | .55 |
| 4 | Uncle Bob — The Cycles of TDD | <https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html> | TDD theory | Red/Green/Refactor cycle theory, Three Laws, Specific/Generic cycle. | .80 |
| 5 | Self-Collaboration (Dong et al., 2023) | <https://arxiv.org/abs/2304.07590> | Indirect | analyst → coder → tester, but tester uses LLM prediction (no execution). | .45 |

## 3. Analysis

### 3.1 Theoretical Validity: Separating Red from Green

TDD's Three Laws (Uncle Bob, source 4) require writing a failing test before production code. The Red/Green separation naturally maps to two agents — one specifying behavior from the contract, one implementing to satisfy it. Nothing in TDD theory requires the same person to do both phases. In pair programming, "ping-pong TDD" already separates these roles between two humans.

AgentCoder's RQ6 (source 1) empirically tested single-agent vs multi-agent test generation:

| Metric | Single Agent | Multi-Agent (separated) | Delta |
|--------|-------------|------------------------|-------|
| Test accuracy (HumanEval) | 61.0% | 87.8% | +26.8 |
| Test accuracy (MBPP) | 51.8% | 89.9% | +38.1 |
| Code coverage (HumanEval) | 72.5% | 87.5% | +15.0 |
| pass@1 (HumanEval) | 71.3% | 79.9% | +8.6 |

**Key finding:** "Tests generated immediately following the code in one conversation can be biased and affected by the code, losing objectivity and diversity." The test designer that never sees implementation produces higher-accuracy, higher-coverage tests.

**Verdict (.90 confidence):** Theoretically sound. Empirically validated by AgentCoder. The separation eliminates implementation bias from tests.

### 3.2 Prior Art Comparison

| Criterion | AgentCoder | ChatDev | MetaGPT | OwlBear (proposed) |
|-----------|-----------|---------|---------|-------------------|
| Tests before code? | Yes (independent) | No (after coding) | No (after coding) | Yes (from AC) |
| Test agent sees code? | No | Yes | Yes | No |
| Test agent modifiable by coder? | No (frozen) | N/A | N/A | Yes (grey model) |
| Reviewer compares? | N/A | N/A | N/A | Yes (test diff) |
| Token overhead | Low (3 agents) | High (7 agents) | Medium (5 agents) | Low (1 new agent) |
| Feedback loop | test executor → programmer | chat dialogue | SOP chain | builder BLOCK → architect |

OwlBear's "grey model" is novel: the builder CAN refine tests (unlike AgentCoder's frozen tests), but the reviewer explicitly compares original vs final. This combines AgentCoder's independence benefit with pragmatic flexibility.

### 3.3 Technical Feasibility: Handoff Protocol

**Builder marking test changes — three options:**

| Option | Mechanism | Reviewer diffability | Complexity |
|--------|-----------|---------------------|------------|
| A. Comment markers | `# builder-added` on each new test | Grep for marker | Low |
| B. Separate test class | `class TestBuilderDiscovered:` | Class-level scan | Low |
| C. Git diff | Compare test file before/after builder | Requires git tooling | Medium |

**Recommendation (.85): Option B (separate test class)** — cleanest separation, easy for reviewer to compare `class TestFromAC` vs `class TestBuilderDiscovered`. Comment markers (A) are fragile (easy to forget). Git diff (C) adds tooling complexity (YAGNI).

**BLOCK protocol when builder can't match test-writer's interface assumptions:**

1. Builder returns `BLOCK: {explanation}` — explains what interface the tests assume vs what's feasible
2. Orchestrator routes to architect (not back to test-writer directly)
3. Architect revises AC, test-writer re-generates tests from revised AC
4. This prevents oscillation between test-writer and builder (architect is the arbiter)

### 3.4 Architecture Fit

**Pipeline change (current → proposed):**

```
Current:  planner → builder(RED+GREEN) → reviewer → writer
Proposed: planner → test-writer(RED) → builder(GREEN) → reviewer → writer
```

**Orchestrator integration:** Add `"test-writer"` to dispatch table. Orchestrator dispatches test-writer before builder for implementation tasks. New gate check: "test-writer phase complete" before builder dispatch.

**Skill split:**

| Skill | Owner | Scope |
|-------|-------|-------|
| `tdd-red` (new) | test-writer | Read AC → write tests → verify they fail → write summary |
| `tdd-green` (renamed from tdd-workflow) | builder | Read tests → implement → verify pass → refactor |

**Test-writer tools needed:** read-only codebase access + file creation (test files only) + terminal (to verify tests fail). No edit tools for source code.

### 3.5 Implementation Approach: Grey Model

**Test-writer prompt structure:**

1. Read AC from kanban task
2. Read existing source files referenced in AC (understand interfaces, types, patterns)
3. Write tests covering: happy paths, edge cases, error paths, boundary conditions
4. Verify all tests FAIL (no implementation yet — import errors or assertion failures)
5. Append test summary to kanban task body

**What test-writer sees:** AC, existing source code (read-only), project test conventions.
**What test-writer does NOT see:** builder's future implementation.

**What builder sees:** AC, existing source code, test-writer's tests.
**Builder's new constraint:** Primary job is GREEN phase. May add tests in `TestBuilderDiscovered` class.

**Reviewer's new check:** Compare test-writer's original test assertions vs builder's final test file. Flag any weakened assertions (changed `==` to `in`, relaxed error types, removed edge cases).

## 4. Recommendation (.90 confidence)

Adopt the grey model with separate test class marking (Option B). This is empirically validated by AgentCoder, fits our existing dispatch model with minimal pipeline changes, and the grey model's reviewer check prevents the builder from gutting adversarial tests.

**Risks and mitigations:**

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Test-writer assumes wrong interface | Medium | BLOCK protocol → architect arbitration |
| Builder weakens test-writer's assertions | Medium | Reviewer explicitly compares; WEAK test quality = FAIL |
| Extra latency (one more agent hop) | Certain | Parallelizable with other pipeline stages |
| Test-writer generates incorrect tests | Low | Builder runs tests; wrong tests fail against correct impl |

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create test-writer.agent.md with RED phase persona and workflow" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --status backlog --body "AC:\n- [ ] test-writer.agent.md: persona is adversarial test specifier, reads AC + codebase, writes failing tests\n- [ ] Tools: read-only search + file creation (test files only) + terminal\n- [ ] Critical rules: never see implementation, never edit source, verify tests FAIL\n- [ ] Output format: test summary appended to kanban task body\n- [ ] Pipeline position: after planner, before builder\nSee docs/test-writer-agent-research.md"

kanban\kanban-md.exe create "Create tdd-red skill for test-writer agent (RED phase workflow)" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --status backlog --body "AC:\n- [ ] New skill tdd-red: Read AC -> plan test categories -> write tests -> verify FAIL -> append summary\n- [ ] Covers: happy paths, edge cases, error paths, boundary conditions\n- [ ] Test class naming: TestFromAC_{Feature} for test-writer tests\n- [ ] Verify step: all tests must FAIL (import error or assertion failure)\nSee docs/test-writer-agent-research.md"

kanban\kanban-md.exe create "Rename tdd-workflow to tdd-green skill, update builder for GREEN-only phase" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --status backlog --body "AC:\n- [ ] Rename tdd-workflow skill to tdd-green (or update content for GREEN phase focus)\n- [ ] Builder.agent.md: primary job is make tests pass, may add TestBuilderDiscovered class\n- [ ] Builder must mark all test additions with separate TestBuilderDiscovered class\n- [ ] BLOCK protocol: if interface assumed by tests is infeasible, return BLOCK explanation\nSee docs/test-writer-agent-research.md"

kanban\kanban-md.exe create "Update reviewer.agent.md for two-agent TDD test comparison" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --status backlog --body "AC:\n- [ ] Reviewer explicitly compares TestFromAC classes vs TestBuilderDiscovered classes\n- [ ] Flags weakened assertions (relaxed comparisons, removed edge cases, changed error types)\n- [ ] WEAK test quality on test-writer's original tests = automatic FAIL\n- [ ] New section in review output: 'Test Writer vs Builder Comparison'\nSee docs/test-writer-agent-research.md"

kanban\kanban-md.exe create "Update orchestrator.agent.md dispatch table for test-writer pipeline stage" --priority needed --tags "scope:copilot,agent,phase-agent-arch" --status backlog --body "AC:\n- [ ] Add test-writer to dispatch table and agent list\n- [ ] New gate: test-writer phase complete before builder dispatch (for impl tasks)\n- [ ] Pipeline: planner -> test-writer(RED) -> builder(GREEN) -> reviewer -> writer\n- [ ] BLOCK handling: route to architect for AC revision, not back to test-writer\nSee docs/test-writer-agent-research.md"
```

## 6. Attribution

See `docs/sources.md` — rows added under "Test-Writer Agent Research (Task #683)".
