# First-Principles Stance

**Challenge 1: Wrong abstraction boundary.** The real problem is that manual assignment bypasses all validation, not just dep_status. Fixing dep_status alone creates a false sense of safety while leaving other invariants (task already claimed, task in wrong column, missing AC) equally unguarded at the same entry point. The irreducible problem is "unvalidated entry to start_work," and dep_status is one symptom.

**Challenge 2: Guidance compliance is ungrounded.** The proposal assumes agents will read guidance text and change behavior. No mechanism in the codebase enforces agent compliance with guidance directives. This is hope-driven design. If the risk genuinely warrants intervention, a hard block (return error, refuse to claim) is the honest choice — simpler and deterministic. If the risk doesn't warrant a hard block, it probably doesn't warrant the code change at all.

**Challenge 3: Phantom risk.** This has never caused harm. The primary dispatch path (`pick_tasks`) already filters dep-blocked tasks. The secondary path (manual assignment) is human-initiated — the human presumably chose the task deliberately. The honest probability of real damage is very low, and blast radius is bounded (agent does wasted work, user notices).

**Challenge 4: Simpler intervention exists.** The orchestrator already decides what to assign. A pre-assignment dep check at the orchestrator level solves the problem upstream with zero engine changes. This keeps validation at the decision point rather than distributing it across the claim API.

**Irreducible core:** If you must guard against stale-dep starts, a hard block in `start_work` is simpler and honest. Guidance-as-directive is a soft intervention pretending to be a hard one. But the strongest move is upstream validation at assignment time, making the engine change unnecessary.

**Confidence: 0.82**
