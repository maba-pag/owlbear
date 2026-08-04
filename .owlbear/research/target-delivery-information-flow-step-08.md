# Target Delivery Information Flow — Step 8: Pre-Admission Validation

> **Owning task:** none — target delivery information-flow walkthrough
> **Date:** 2026-08-02
> **Question:** Which claims must be checked immediately before admission, and which inherited gates
> add ceremony without protecting a distinct failure?

## 1. Status Quo And Evidence

Current Design parses the candidate, invokes one independent admission challenger, runs clean
baselines, assembles challenge and limit evidence, and calls `validate_change`. The challenger returns
one pass/warning/error judgment per declared identity. The validator checks that every declared
identity received a result, hashes the candidate, and derives initial jobs.

This proves coverage of what the candidate already contains, but not that automatic derivation
preserved every reviewed promise or architecture boundary. Current baseline guidance is proportional
but predates Step 6's trigger-based proof policy. The current challenger also mixes mapping fidelity,
source feasibility, and broad architecture judgment in one per-entity response.

Step 7 is now agent-only deterministic compilation. Step 8 must therefore verify the compiler output
and admission readiness. It must not ask the user to interpret the generated contract, redesign the
architecture already critiqued in Step 6, or treat current tests as proof of unimplemented behavior.

## 2. Decision D1 — Validate What Delivery Cannot Discover

Before admission, prove only that the generated contract is exactly reproducible from the reviewed
sources and matching semantic checkpoints; intent is `user-confirmed` and design is `reviewed`; every
typed protected commitment and promised outcome is represented or explicitly excluded; each active
outcome contains typed acceptance statements; and references and dependencies are valid and acyclic.
Initial admission must yield schedulable work. Revised admission may yield an empty new-work frontier
only when deterministic carry-forward preserves every outcome. When prior accepted results belong to
removed outcomes, validation joins those bindings and requires preserved behavior or an ordinary
removal/replacement outcome.

Deterministic validation judges representation, coverage, identity, and schedulability. It cannot
judge whether acceptance meaning is genuinely observable or sufficient; Step 6's forward critique
and Step 9's reverse review own that semantic question.

These checks prevent invisible omission and invalid work creation. Route a defect internally to its
owning intent, architecture, or derivation step and rerun only invalidated checks. Repository health,
implementation feasibility, detailed proof cases, and implementation correctness belong to exact-
context Planning and Building, which already have independent review and typed Design return.

## 3. Decision D2 — Delete The Inherited Gate Stack

Remove the per-entity admission challenger, pass/warning evidence, admission-time build/test
baselines, and repeated validation call. Step 3 already critiques intent, Step 6 critiques
architecture and source-grounded feasibility, and Step 7 deterministically compiles their reviewed
meaning. Another semantic review of generated output repeats those claims, while current baseline and
challenge evidence has no durable consumer.

Persist only source bindings, contract digest, accepted known limits, and frontier identities; the
empty tuple directly represents an empty revised-admission frontier.
A successful check needs no report; persistence of the admitted contract and
receipt proves it passed. Failed diagnostics remain transient unless their repair changes current
Specification meaning.

Implementation prerequisites are explicit: remove challenge and baseline fields from the admission
candidate; add exact source bindings and source-bound derivation; add typed normative coverage,
cycle detection, and non-empty-frontier validation; and replace warning-bearing receipt fields with
the minimal publication identity chosen in Step 9. Until these land, current `validate_change` does
not implement this decision. If Step 7 falls back to a separately authored contract, restore an
explicit contract review and replace derivation replay with reviewed source-to-contract comparison.

## 4. Step Completion

Step 8 is decided and is not a separate user-visible phase. Its deterministic checks run inside the
next authorization/admission boundary. Step 9 decides whether explicit user authorization remains
necessary before atomic publication and autonomous Delivery.