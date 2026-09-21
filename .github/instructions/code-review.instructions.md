---
description: "Review criteria for GitHub's built-in Copilot pull-request reviewer"
applyTo: "**"
excludeAgent: "cloud-agent"
---

# GitHub Copilot Code Review

Applies only to GitHub's built-in pull-request code review. Do not apply this review procedure
to local IDE editing, Copilot Chat or cloud-agent implementation sessions.

- Evaluate the changed behavior against the requested outcome and relevant acceptance criteria.
  Read the owning implementation and necessary callers/tests, not just the PR's claims.
- For a Delivery package PR, use its identified package plan and named phase when available.
  Do not infer a phase from an example in the cloud guide or demand implementation of later phases.
  For other PRs, review the actual change; do not require a package plan, phase or Delivery record.
- Review planning-only changes for feasible dependencies, complete contracts and discriminating
  acceptance evidence. Do not report unimplemented planned features as code defects.
- Prioritize concrete correctness, security, data-loss, custody, stale-approval and replay failures.
  Explain the plausible trigger and consequence; avoid speculative redesign or stylistic preferences.
- Check whether tests exercise the real behavior and meaningful negative cases. Passing counts,
  mocks above the behavior under review and worker summaries do not prove end-to-end acceptance.
- Distinguish source inspection, reported test results and checks actually executed. Missing proof
  is not proof of a bug; request additional evidence only for a concrete unresolved claim.
- Recheck earlier findings against the current code. A resolved thread is not proof of a fix, and
  an outdated comment is not proof that the defect still exists. Do not repeat disproved findings.
- If execution is available and needed, use the smallest affected check. Never run the whole
  OwlBear suite, MegaLinter, `uv run megalint`, `uv run quality`, or heavy aggregate wrappers.
- Missing editor tools, OwlBear MCP or managed-host access is expected. Use available source and
  in-process test evidence; do not request live services, credentials or wider permissions.
  Do not equate cloud fixtures with actual host termination, authentication or activation proof.
- Keep live state and external systems unchanged. Do not edit source, merge, relax branch rules,
  or infer user permission from a plan approval. Existing review/merge settings remain authoritative.
- Absence of findings is not full package acceptance or proof that all required checks ran.
  Do not claim a particular review model, fresh context or a check result without evidence.

Use the native review interface. These instructions guide analysis, not GitHub's comment format,
overview, model selection or approval behavior. Repairs are a separate user-requested cloud task.
