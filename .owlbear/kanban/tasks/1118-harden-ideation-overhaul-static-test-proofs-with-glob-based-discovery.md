---
id: 1118
title: Harden ideation-overhaul static test proofs with glob-based discovery
status: research
priority: important
created: 2026-04-24T11:10:50.379753+00:00
updated: 2026-04-24T11:10:50.379753+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Replace curated hardcoded file lists in `tests/test_ideation_overhaul_static.py` with glob-based dynamic discovery to prevent silent proof bypass when new ideation agent files are added.

Research doc: `.owlbear/research/1115-ideation-test-proof-hardening.md`

## Acceptance Criteria

1. Negative scans for `model:` field use `_REPO_ROOT.glob("share/agents/ideation-*.agent.md")` instead of curated lists
2. Negative scans for `working-log.md`/`checkpoint` use glob-based discovery across the full ideation surface (agents + skills + briefs README)
3. Both glob helpers assert `len(files) >= N` (min-count guard against empty-glob false pass)
4. The split test pairs are merged: `test_role_files_do_not_use_model_field_as_contract` + `test_late_panelist_files_do_not_use_model_field_as_contract` into one test; `test_no_working_log_or_checkpoint_contract_reappears` + `test_late_panelist_files_have_no_working_log_or_checkpoint` into one test
5. Forbidden-term check for `checkpoint` is case-insensitive
6. `test_phase_split_files_exist` existence check covers the 4 late-domain panelists (architect, data, enduser, security)
7. All existing tests that use semantic subsets (critic narrow contract, context/decisions paired contract) remain unchanged
8. Full suite passes: `uv run pytest tests/test_ideation_overhaul_static.py -q`

## Affected Files

- `tests/test_ideation_overhaul_static.py`
