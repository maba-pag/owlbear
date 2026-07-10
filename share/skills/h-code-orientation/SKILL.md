---
name: h-code-orientation
description: "Handbook: Locate unfamiliar code and patterns without confusing discovery with proof"
user-invocable: false
---

# Code Orientation

Use Semble to identify a small set of plausible owners or analogous implementations when no credible file, symbol, or module anchor is known. It is an orientation tool, not evidence.

## When Semble Earns A Call

Use it for a focused question such as:

- Which module likely owns this behavior?
- Where is a similar validation, concurrency, cache, or API pattern implemented?
- What implementation should be read first to understand this unfamiliar area?

Do not use it when a known file or symbol already provides an adequate starting point. Do not repeat a Semble query after it returns a usable location.

## Invocation

Run OwlBear's shared CLI from the current project:

```text
uv run --project {owlbear-root} semble search "behavior or symbol" . --top-k 5
uv run --project {owlbear-root} semble find-related path/to/file.py 42 . --top-k 5
```

For an approved external-repository clone, replace `.` with its path under `.owlbear/scratch/research/`. The research workflow controls clone approval, acquisition, recording, and cleanup.

## Discovery Is Not Proof

1. Treat results as candidates. Read the returned source directly before making a claim or editing.
2. Use `rg`, language-server references, direct reads, or focused tests for literal or exhaustive claims: every caller, every implementation, absence, exact configuration use, and affected tests.
3. Cite the actual source or command result in task evidence, never a Semble ranking or savings metric.
4. Stop after one or two focused searches. If ownership remains unclear, follow the caller's role boundary instead of broadening the search indefinitely.

## Role Boundaries

| Role | Permitted use | If orientation remains insufficient |
|------|---------------|-------------------------------------|
| Shaper | Find owners, precedents, and architecture seams before shaping. | Refine, research, or request the missing decision. |
| Builder | Recover a missing implementation anchor or find a narrow analogous pattern. | Reject to shape when ambiguity affects AC, architecture, or scope. |
| Verifier | Test a concrete concern against an analogous implementation or adjacent invariant. | Reject to build or reshape; do not become a second builder. |

Collector and challengers do not use Semble by default: their work is closure or bounded cross-checking, not open-ended source discovery.