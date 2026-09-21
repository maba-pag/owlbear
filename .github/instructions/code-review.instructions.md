---
description: "Review criteria for GitHub's built-in Copilot pull-request reviewer"
applyTo: "**"
excludeAgent: "cloud-agent"
---

# GitHub Copilot Code Review

Scope: GitHub's built-in pull-request reviewer. In other environments, follow that environment's
review or implementation instructions.

- Evaluate the changed behavior against the requested outcome and relevant acceptance criteria.
  Use plans referenced by the task to establish its scope. Read the owning implementation and
  necessary callers/tests; distinguish the requested work from any future work in those plans.
- Review planning-only changes for feasible dependencies, complete contracts and discriminating
  acceptance evidence. Do not report unimplemented planned features as code defects.
- Prioritize concrete correctness, security, data-loss, custody, stale-approval and replay failures.
  Explain the plausible trigger and consequence; avoid speculative redesign or stylistic preferences.
- Check whether tests exercise the real behavior and meaningful negative cases. Passing counts,
  mocks above the behavior under review and worker summaries do not prove end-to-end acceptance.
- Distinguish source inspection, reported test results and checks actually executed. Missing proof
  is not proof of a bug; request additional evidence only for a concrete unresolved claim.
- Recheck earlier findings against the current code before retaining or dismissing them.
- If execution is available and needed, use the smallest affected check. Never run the whole
  OwlBear suite, MegaLinter, `uv run megalint`, `uv run quality`, or heavy aggregate wrappers.
- Use available source and in-process test evidence. Record unavailable checks and their limits;
  fixture results establish only the behavior and environment they exercise. Keep credentials,
  live services and permissions unchanged.
- Keep live state and external systems unchanged. Do not edit source, merge, relax branch rules,
  or infer user permission from a plan approval. Existing review/merge settings remain authoritative.
- Absence of findings is not acceptance of the entire change or proof that all required checks ran.
  Do not claim a particular review model, fresh context or a check result without evidence.

Use the native review interface. These instructions guide analysis, not GitHub's comment format,
overview, model selection or approval behavior. Repairs are a separate user-requested cloud task.
