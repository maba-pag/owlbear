---
name: owlbear-findings
description: "Review judgment: what counts as evidence, where defects hide, and which findings are worth reporting"
user-invocable: false
---

# Findings

Use when you judge someone else's diff, plan or brief and report findings. `owlbear-acceptance` owns which proof
a criterion needs; this skill owns how you judge the evidence and what you report.

## Evidence

- Judge the exact version your message names and the code it depends on. Summaries, commit messages, earlier
  reports and passing checks are claims: confirm a cited path, line or command result before you rely on it. An
  unconfirmed claim is not a finding, in either direction.
- Evidence proves only the boundary it exercises. A passing test covers its own assertions, inputs, path and
  environment: enough for a narrow claim about exactly that contract, not for the integration, security or
  usability around it. Mocks, injected dependencies and counts do not prove an unexercised command or journey.
- For a claim that crosses modules, confirm each boundary exists in the current code and that the proof would
  fail if the claimed path were bypassed. Inputs and outputs that occur together do not prove control.
- Where a route needs a tool, command or capability, confirm it exists, or that its absence fails visibly.
- Ask for the cheapest evidence that would fail if the claim were false. One focused proof may cover several
  criteria; never demand one test per criterion, broad coverage or end-to-end proof by default.

## Where Defects Hide

- **One frame up.** Before you report a problem inside a function, read its callers: one may already check,
  reject or recover from it. Report it only where no caller handles it.
- **Fallbacks that hide failures.** A default value, an empty result, a swallowed error or a silent retry that
  turns a failure into apparent success is a finding: name what fails and why the caller never learns of it.
- **State changes in order.** Where several calls change the same state, trace them in the order they run. A
  later call that overwrites, resets or undoes what an earlier one set, or a read before the write it needs,
  is a finding.

## Operating Context

Judge each finding in the context of the work: who and what acts on it or feeds it, how far each is trusted,
what reaches it from outside that set, and what a failure costs. The brief states it; otherwise use the
narrowest context the evidence supports.

A plausible trigger is an action by an actor or input inside that context, likely enough to matter for the
stakes. A concern that needs an actor the context excludes, such as a deliberately hostile agent, an attacker
who already is the user, or a coincidence of independent timings, is not a finding. If the context itself looks
wrong, say so once; do not turn it into defects.

## Finding Quality

Asked to find problems, a judge almost always finds something, and each further round reaches for less likely
cases. That a finding exists is no evidence that anything must change.

- Report only findings with a plausible trigger, a concrete consequence and evidence. Name the actor or input,
  what it does, the consequence, and the cheapest adequate response: a small fix, a documented limit, a check
  that fails safely, or nothing.
- Style, taste, another way to build the same thing and unsupported doubt are not findings.
- Marginal findings are not harmless: each costs repair work, permanent complexity and another round.
- Prefer the smallest fix. A fix that adds a mechanism invites findings about that mechanism; when one area keeps
  producing findings, say that its design needs simplifying instead of proposing another layer.
- The brief and the owner's answers are settled. When evidence shows one no longer serves the outcome, the
  finding names the decision, its evidence and the options; it never assumes a silent change.
- No findings is a complete and valuable result.
