# End User — Critic Debate Log

## Cycle 1: Fixed question format applies universally — or does it?

### Position presented
O11 format (context/status-quo + problem + proposals + per-proposal pro/con/risk/confidence + recommendation) should apply to all turns but scale naturally: when there's only one framing, it's one proposal with reasoning. The format doesn't "degrade gracefully" — it scales. An M1 probe is "I think the problem is X. Here's my reasoning. Do you agree or reframe?" — that IS the format with one proposal.

### Critic challenge
"You're re-introducing the Critic's rejected split with different words. The user rejected 'O11 scope to decision turns only.' Saying 'some turns have one proposal' means some turns have no pro/con comparison — which is the split by another name. If a probe has one framing, there's no 'con' column. You've gutted the comparative structure."

### Response
The Critic misidentifies the user's rejection. The user rejected *exempting* early turns from the format — not the idea that different turns produce different amounts of content within the format. Every turn gets context + reasoning + recommendation. A single-framing probe still has: context (what I know so far), problem (what I need to understand), proposal (my current read), reasoning (why I read it this way), recommendation (agree or push back). The comparative structure is present — it's "my framing vs. your potential reframe." The user's words: "the chain has to be helpful — recommendations are not anchoring when the user actively steers." The chain is always present. The number of proposals varies with the turn's nature. This is not the split; it's the format doing its job.

**Outcome:** Position refined — clarified that every turn has the full chain, but the number of competing proposals is a function of the question, not a rule-exception.

---

## Cycle 2: Filter transparency is de facto opacity

### Position presented
When filter agents are applied, the Mediator should include a one-line attribution per panelist alongside the synthesis. "[Architect: favors X] [Data: warns about schema drift] [End User: comprehension concern] [Security: no material objection]. Synthesis: ..." Full stances available in files as fallback.

### Critic challenge
"'stances/*.md are there if you want them' is technically transparent but practically useless — the user won't open 4 files mid-conversation. You're offering de jure transparency with de facto opacity. A headline per panelist is better, but how does the user know if the synthesis *missed* something versus the panelist not raising it? The headline might itself be filtered."

### Response
Valid escalation. Refine: The per-panelist headline must come from the panelist's own stance file, not from the synthesis. The Mediator reads the synthesis AND pulls the first line (position summary) from each `stances/{name}.md` directly. That way the headline is unfiltered — it's the panelist's own summary, not the Pragmatist's characterization. If the user sees a headline that doesn't map to anything in the synthesis, that's the signal to pull the full file. The synthesis covers convergences and disagreements; the per-panelist headlines are the audit trail. The user gets both views without reading 4 full files.

**Outcome:** Position hardened — per-panelist headlines sourced from raw stance files, not from synthesis. Two independent views: headlines (raw) + synthesis (filtered). Discrepancy = signal to dig deeper.

---

## Cycle 3: Critic-listening discipline has no structural prevention

### Position presented
D4 is enforced through O11: Critic findings go through the same format as everything else. Each Critic point gets its own O11 question. "Reject the Critic" is a first-class option with its own reasoning. Working log makes adoption visible.

### Critic challenge
"O11 is a presentation format. It doesn't prevent the Mediator from already having internalized the Critic's position before presenting. The Mediator reads Critic output, forms an opinion, then presents the question. Anchoring happens before the question reaches the user. What structural mechanism prevents pre-adoption?"

### Response
Nothing can fully prevent cognitive anchoring in an LLM that has read an adversarial argument. That's a fundamental limit, not a design failure. The mitigation stack is:
1. **Per-point presentation** (O11) forces the user to engage with each Critic finding individually — no bulk adoption.
2. **Working log** (O2) captures what the Critic said verbatim alongside the Mediator's presented question — makes anchoring auditable after the fact.
3. **Formatting discipline** — the "reject" option in each O11 question must have its own genuine reasoning, not be a vestigial "or don't" afterthought. This is verifiable: if the reject reasoning is thin, the user catches it.
4. **D4 as system instruction** — "Bulk adoption of Critic recommendations is the same anti-pattern as ignoring Critic" is embedded in the Mediator's instructions, not just a principle. It fires at read-time, the moment the Mediator processes Critic output.

Perfect prevention is impossible. The design reduces blast radius and makes adoption visible. The user — who is technical and engaged — is the actual check. The system makes the user's job easier, not unnecessary.

**Outcome:** Position hardened — acknowledged the structural limit honestly. The system enables user detection, not prevention. That matches the user's own model: they want agency, not automation.

---

## Cycle 4: Panel output dump creates attention overload

### Position presented
Present panel output all at once with attributed positions so the user can scan the full landscape before reacting.

### Critic challenge
"Three panelists' attributed positions plus a synthesis is 4 blocks of content dumped at once. For a user in a long session (Q7), this is an attention overload event — the very thing the design principle targets."

### Response
Good catch. Refine: Use the synthesis-first pattern. The Pragmatist synthesis comes first (2-3 sentences: convergences and disagreements). Then the Mediator offers a choice: "Want me to walk through each position, or proceed with the synthesis?" This is the M5 walkthrough pattern applied to panel output — the user already knows it. Fast path: take the synthesis. Thorough path: step through each voice. Full stances available if they want to read directly.

This avoids the dump while preserving the "see the full landscape" capability — the landscape is the synthesis, the details are on-demand.

**Outcome:** Position refined — synthesis-first with walkthrough offer. User controls depth. Dump avoided.

---

## Cycle 5: Working log growth becomes its own attention burden

### Position presented
The working log is the fatigue mitigation: external memory so the user doesn't have to remember decisions from 2 hours ago. The Mediator references it by section.

### Critic challenge
"The log is append-only and grows. At Turn 40, it's huge. How does the Mediator reference efficiently? You haven't addressed retrieval. You're replacing multi-file confusion with single-file-too-long confusion."

### Response
Fair. The log needs lightweight structure for navigation — not a manifest (user rejected that) but consistent section headers: `## Turn N — [Moment] — [Topic]`. Grep-friendly, scan-friendly. The Mediator's attention strategy for the log: read the *current moment's* section fully + reference specific prior decisions by turn number when needed. Not the whole log every turn. The user explicitly wanted a "sequential discussion record" — that's compatible with headers. The log doesn't replace the Mediator's working memory; it supplements it. When the Mediator says "Per your M1 decision (Turn 8)..." the user can verify without scrolling through everything.

The single-file model is still better than multi-file for retrieval: one file to search vs. figuring out which of 6 files has the decision. Length is managed by structure, not by splitting.

**Outcome:** Position refined — log needs consistent headers for navigation. Mediator reads selectively, references by section. Single long file > multiple scattered files for a technical user with search tools.
