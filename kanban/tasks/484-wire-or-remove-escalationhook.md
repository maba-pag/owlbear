---
id: 484
title: Wire or remove EscalationHook
status: backlog
priority: important
created: 2026-03-04T07:38:01.1970371+01:00
updated: 2026-03-06T19:26:41.4864849+01:00
started: 2026-03-06T19:26:41.4864849+01:00
tags:
    - audit
    - yagni
    - hooks
    - scope:core
class: standard
---

YAGNI-02/INT-03: EscalationHook is fully implemented and tested but never imported or registered in bootstrap.py. Orphan code.

**Research complete** (2026-03-06): See docs/escalation-hook-research.md

**Recommendation (.85 confidence): DELETE.** _recover_from_error in daemon.py is the established error authority (classified recovery, backoff, auth refresh, journaling). Wiring EscalationHook creates a dual-prompt conflict (ARC-21) and requires fixing a data shape mismatch. No ROI.

**Research checklist:**
1. Theoretical validity: Sound concept, but redundant with existing daemon recovery
2. Prior art: OwlBear's own _recover_from_error already covers all error categories
3. Technical feasibility: Could be wired, but ARC-21 dual-prompt conflict blocks it
4. Architecture fit: Conflicts with daemon error handling authority
5. Implementation approach: Delete escalation.py + test_escalation.py + clean refs
6. Testing strategy: Verify no import errors, ruff clean, all remaining tests pass
7. Findings documented: docs/escalation-hook-research.md

AC: no dead production code for this feature.
