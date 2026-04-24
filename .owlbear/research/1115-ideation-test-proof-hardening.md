# Ideation Overhaul Test Proof Hardening

> **Owning task:** #1115 — Ideation overhaul test proof hardening
> **Date:** 2026-04-24 **Status:** Complete

## 1. Context and Question

Task #1040 shipped `tests/test_ideation_overhaul_static.py` (31 tests) to lock ideation-overhaul contracts. The reviewer pass at .86 and subsequent .95 identified proof weaknesses: negative scans use curated hardcoded file lists instead of dynamic discovery, making it possible for new ideation agent files to silently bypass contract enforcement. The reviewer accepted the current state as "covered for existing surface" but flagged the structural weakness as informational.

**Question:** How should the test suite be hardened so that AC-scoped negative scans are durable against surface expansion?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | `tests/test_ideation_overhaul_static.py` (current, 31 tests) | 1.0 | 6 curated file lists across tests; split test pairs for same contract |
| 2 | `tests/test_package_boundary.py` (glob pattern) | 0.9 | `serve_root.glob("*/src")` pattern — dynamic file discovery with assertions |
| 3 | `tests/test_cockpit_boundary.py` (rglob pattern) | 0.8 | `src_root.rglob("*.py")` pattern with list comprehension filtering |
| 4 | Task #1040 reviewer evidence (Pass 1 + Pass 2) | 1.0 | Exact gaps: AC 1 and AC 5 partial coverage, case-sensitivity, curated-vs-glob concern |
| 5 | Repo memory `review-negative-scan-glob-completeness.md` | 0.9 | "Derive files dynamically when AC forbids a token across a whole file glob" |

## 3. Analysis

### Identified Proof Gaps

| # | Gap | Severity | Evidence |
|---|-----|----------|----------|
| G1 | Curated file lists don't catch new ideation agent files | HIGH | Adding `ideation-foo.agent.md` bypasses all negative scans silently |
| G2 | Split tests for same contract (model-free: 7+4, forbidden-terms: 13+4) | MEDIUM | Maintenance burden; arose from iterative reviewer fixes, not design |
| G3 | `test_phase_split_files_exist` omits 4 late-domain panelists | MEDIUM | architect, data, enduser, security not in existence check |
| G4 | Case-insensitive forbidden terms (`checkpoint`) | LOW | Only lowercase checked; `Checkpoint` would pass green |
| G5 | Empty-glob false pass risk | LOW | Dynamic glob on broken path returns [] — all-pass on zero files |

### Approach Comparison

| Criterion | A: Full glob refactor | B: Curated + guard test | C: Hybrid (shared helper) |
|-----------|----------------------|------------------------|--------------------------|
| Catches new files | Yes (automatic) | Yes (guard test fails) | Yes (automatic) |
| Eliminates duplication | Yes | No — adds a layer | Yes |
| Merge split tests | Yes | No | Yes |
| Complexity | Medium — restructures tests | Low — adds 1 test | Medium — extracts helpers |
| Empty-glob safety | Needs min-count guard | N/A | Needs min-count guard |
| Aligns with repo patterns | Yes (`test_package_boundary.py`) | Partially | Yes |
| Risk of false pass | Low with min-count | Very low | Low with min-count |

### Detailed Design (Approach C — recommended)

1. **Shared discovery helpers** at module level:
   - `_ideation_agent_files()` → `sorted(_REPO_ROOT.glob("share/agents/ideation-*.agent.md"))` with `assert len(files) >= 11`
   - `_ideation_surface_files()` → agents + skills + briefs README, also with min-count guard
2. **Merge split tests**: Combine `test_role_files_do_not_use_model_field_as_contract` + `test_late_panelist_files_do_not_use_model_field_as_contract` → one test using `_ideation_agent_files()`
3. **Merge forbidden-term scans**: Combine `test_no_working_log_or_checkpoint_contract_reappears` + `test_late_panelist_files_have_no_working_log_or_checkpoint` → one test using `_ideation_surface_files()`
4. **Update existence check**: Add late panelists to `test_phase_split_files_exist` OR replace with glob + min-count
5. **Case-insensitive forbidden terms**: Use `.lower()` on file content before checking
6. **Keep curated subsets**: `test_critic_keeps_narrow_context_only_contract` and `test_ideation_surfaces_keep_context_and_decisions_contract` keep semantic subsets where the contract is intentionally narrower

## 4. Recommendation (confidence: .82)

**Approach C — Hybrid shared helpers.** Extract glob-based discovery helpers with min-count guards. Merge the 4 split tests into 2. Add case-insensitive forbidden-term matching. This aligns with established patterns (`test_package_boundary.py`), eliminates list duplication, and automatically catches surface expansion.

Estimated scope: ~40 lines changed in `tests/test_ideation_overhaul_static.py`. No new files needed.

Challenge: FALLBACK — task is T1-autonomous test refactor with no architecture or capability change; challenger invocation not warranted for a sub-.85 confidence internal test maintenance task.

## 5. Follow-up Tasks

- **Task: Harden ideation-overhaul static test proofs** — Replace curated file lists with glob-based discovery helpers, merge split test pairs, add case-insensitive forbidden-term checks, add min-count guards. File: `tests/test_ideation_overhaul_static.py`.
